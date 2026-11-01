"""Gemini（無料枠）で文章を作る。モデル名は固定せず、使えるものを自動で探す"""
import json, os, re, time
import requests

BASE = "https://generativelanguage.googleapis.com/v1beta"
_EXCLUDE = re.compile(r"image|tts|live|audio|embedding|vision|thinking-exp|native", re.I)
_model_cache = None


def _key():
    k = os.getenv("GEMINI_API_KEY")
    if not k:
        raise RuntimeError("GEMINI_API_KEY が設定されていません")
    return k


def _candidates():
    global _model_cache
    if _model_cache:
        return _model_cache
    r = requests.get(f"{BASE}/models", params={"pageSize": 200},
                     headers={"x-goog-api-key": _key()}, timeout=30)
    r.raise_for_status()
    names = []
    for m in r.json().get("models", []):
        name = m["name"].split("/")[-1]
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        if not re.search(r"flash", name, re.I) or _EXCLUDE.search(name):
            continue
        names.append(name)
    # 新しい版を先に、lite は後回し
    names.sort(key=lambda n: (("lite" in n), "preview" in n, [-int(x) for x in re.findall(r"\d+", n)][:2]))
    _model_cache = names or ["gemini-2.5-flash"]
    return _model_cache


def ask_json(prompt: str) -> dict:
    """プロンプトを送ってJSONで受け取る。混雑・上限なら別モデルや待機で粘る"""
    last = None
    for model in _candidates()[:4]:
        for attempt in range(2):
            try:
                r = requests.post(
                    f"{BASE}/models/{model}:generateContent",
                    headers={"x-goog-api-key": _key(), "Content-Type": "application/json"},
                    json={"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                          "generationConfig": {"temperature": 0.9,
                                               "responseMimeType": "application/json"}},
                    timeout=90)
                if r.status_code in (404, 400):
                    last = f"{model}: {r.status_code}"
                    break  # 次のモデルへ
                if r.status_code in (429, 500, 503):
                    last = f"{model}: {r.status_code}"
                    time.sleep(20 * (attempt + 1))
                    continue
                r.raise_for_status()
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
                return json.loads(text)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                last = f"{model}: 返事の形が変 ({e})"
                continue
    raise RuntimeError(f"Geminiで文章を作れませんでした（{last}）")

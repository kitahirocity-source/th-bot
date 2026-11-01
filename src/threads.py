"""Threads API（公式・無料）で投稿と反応の取得"""
import os, time
import requests

API = "https://graph.threads.net/v1.0"


def _token():
    t = os.getenv("THREADS_ACCESS_TOKEN")
    if not t:
        raise RuntimeError("THREADS_ACCESS_TOKEN が設定されていません")
    return t


def _uid():
    return os.getenv("THREADS_USER_ID") or "me"


def post(text: str, reply_to: str | None = None) -> str:
    params = {"media_type": "TEXT", "text": text, "access_token": _token()}
    if reply_to:
        params["reply_to_id"] = reply_to
    r = requests.post(f"{API}/{_uid()}/threads", params=params, timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"投稿の準備に失敗 {r.status_code}: {r.text[:300]}")
    cid = r.json()["id"]
    time.sleep(5)  # Meta推奨：公開前に少し待つ
    for attempt in range(3):
        r = requests.post(f"{API}/{_uid()}/threads_publish",
                          params={"creation_id": cid, "access_token": _token()}, timeout=60)
        if r.status_code < 300:
            return r.json()["id"]
        time.sleep(15)
    raise RuntimeError(f"公開に失敗 {r.status_code}: {r.text[:300]}")


def insights(media_id: str) -> dict:
    r = requests.get(f"{API}/{media_id}/insights", timeout=60,
                     params={"metric": "views,likes,replies,reposts,quotes", "access_token": _token()})
    if r.status_code >= 300:
        return {}
    out = {}
    for m in r.json().get("data", []):
        v = m.get("total_value", {}).get("value")
        if v is None and m.get("values"):
            v = m["values"][0].get("value")
        out[m["name"]] = v or 0
    return out

"""1回の実行: ① 反応の計測 → ② 商品紹介（本文＋リプ欄に楽天リンク）か、共感・お役立ち投稿"""
import json, os, random, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import config

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
HIST = ROOT / "data" / "history.json"
DRY_RUN = os.getenv("DRY_RUN") == "1"
MOCK = os.getenv("MOCK") == "1"


def now():
    return datetime.now(JST)


def load():
    return json.loads(HIST.read_text(encoding="utf-8")) if HIST.exists() else []


def save(h):
    HIST.write_text(json.dumps(h[-1000:], ensure_ascii=False, indent=1), encoding="utf-8")


def update_metrics(history):
    if DRY_RUN or MOCK:
        return
    from threads import insights
    t = now()
    n = 0
    for h in history:
        if h.get("id") and not h.get("metrics") and \
                timedelta(hours=24) <= t - datetime.fromisoformat(h["posted_at"]) <= timedelta(days=7):
            m = insights(h["id"])
            if m:
                h["metrics"] = m; n += 1
    if n:
        print(f"[計測] {n}件の反応を記録")


def pick_genre(history):
    """今の月に合うジャンル × 過去に反応の良かったジャンルを選びやすく"""
    month = now().month
    keys = [k for k, (_, months) in config.GENRES.items() if month in months]
    last = [h.get("genre") for h in history[-2:]]
    keys = [k for k in keys if k not in last] or keys
    score = {}
    for h in history:
        if h.get("kind") == "product" and h.get("metrics"):
            score.setdefault(h["genre"], []).append(h["metrics"].get("views", 0) + h["metrics"].get("likes", 0) * 20)
    w = [(sum(score[k]) / len(score[k]) if k in score else 300) + 50 for k in keys]
    return random.choices(keys, weights=w)[0] if random.random() > 0.2 else random.choice(keys)


def do_product(history):
    genre = pick_genre(history)
    since = now() - timedelta(days=config.NO_REPEAT_DAYS)
    used = {h.get("item_code") for h in history if datetime.fromisoformat(h["posted_at"]) >= since}
    if MOCK:
        item = {"code": "mock:1", "name": "【ふるさと納税】北海道産 ほたて貝柱 1kg 訳あり", "price": 12000,
                "url": "https://hb.afl.rakuten.co.jp/hgc/xxxx/", "reviews": 5321, "rating": 4.6,
                "shop": "北海道○○町", "caption": "大きさ不揃いの訳あり品。冷凍でお届け。"}
        d = {"main": "【PR】ふるさと納税、まだ枠が残ってる人へ。\n\n年末はみんな駆け込むので、\n人気の返礼品から先に品切れになりがちです。\n\n北海道のほたては、普段使いしやすくて\nレビューも多い定番。\n\nリンクはリプ欄に置いておきます👇",
             "reply": "北海道産ほたて貝柱1kg（訳あり）。12,000円の寄付で、レビュー5,321件\n※価格は11/1時点\nhttps://hb.afl.rakuten.co.jp/hgc/xxxx/"}
    else:
        from rakuten import search
        from writer import write_product
        kws = config.GENRES[genre][0][:]
        random.shuffle(kws)
        item = None
        for kw in kws:
            item = search(kw, used)
            if item:
                break
        if not item:
            print(f"[情報] {genre} で条件に合う商品がなかったので、共感投稿にします")
            return do_talk(history)
        d = write_product(item, genre, history)
    print("── 本投稿 ──\n" + d["main"] + "\n── リプ欄 ──\n" + d["reply"])
    mid = rid = None
    if not (DRY_RUN or MOCK):
        from threads import post
        mid = post(d["main"])
        rid = post(d["reply"], reply_to=mid)
        print(f"[投稿] 本投稿 {mid} / リプ {rid}")
    history.append({"kind": "product", "id": mid, "reply_id": rid, "posted_at": now().isoformat(),
                    "genre": genre, "item_code": item["code"], "item": item["name"][:60],
                    "price": item["price"], "text": d["main"]})


def do_talk(history):
    if MOCK:
        d = {"main": "雪国の人に聞きたいです。\n\n冬の車、スノーブラシは\n「伸びるやつ派」と「短いやつ派」どっちですか？\n\n除雪の仕事してると、ここ地味に好みが分かれるんですよね。", "theme": "質問"}
    else:
        from writer import write_talk
        d = write_talk(history)
    print("── 共感投稿 ──\n" + d["main"])
    mid = None
    if not (DRY_RUN or MOCK):
        from threads import post
        mid = post(d["main"])
        print(f"[投稿] {mid}")
    history.append({"kind": "talk", "id": mid, "posted_at": now().isoformat(),
                    "theme": d["theme"], "text": d["main"]})


def write_report(history):
    since = now() - timedelta(days=30)
    rec = [h for h in history if datetime.fromisoformat(h["posted_at"]) >= since and h.get("id")]
    rows = {}
    for h in history:
        if h.get("kind") == "product" and h.get("metrics"):
            rows.setdefault(h["genre"], []).append(h["metrics"])
    out = [f"# Threads楽天bot レポート（{now():%Y/%m/%d %H:%M} 更新）", "",
           f"- 直近30日: 商品紹介 {sum(1 for h in rec if h['kind']=='product')}件 / 共感投稿 {sum(1 for h in rec if h['kind']=='talk')}件",
           "- 費用: 0円（Threads API・Gemini無料枠・楽天API・GitHub Actions）", "",
           "## ジャンル別の平均反応（表示が多い順）", "", "| ジャンル | 件数 | 平均表示 | 平均いいね |", "|---|---|---|---|"]
    for g, ms in sorted(rows.items(), key=lambda kv: -sum(m.get("views", 0) for m in kv[1]) / len(kv[1])):
        out.append(f"| {g} | {len(ms)} | {sum(m.get('views',0) for m in ms)/len(ms):,.0f} | {sum(m.get('likes',0) for m in ms)/len(ms):.1f} |")
    out += ["", "※売上（クリック・成果）は楽天アフィリエイトの管理画面で確認してください"]
    (ROOT / "data" / "report.md").write_text("\n".join(out), encoding="utf-8")


def main():
    history = load()
    try:
        update_metrics(history)
    except Exception as e:
        print(f"[注意] 計測に失敗: {e}")
    if now().hour in config.QUIET_HOURS and os.getenv("FORCE") != "1":
        print(f"[お休み] {now():%H}時は投稿しない時間です")
    elif os.getenv("MODE") == "talk" or (os.getenv("MODE") != "product" and random.random() > config.PRODUCT_RATIO):
        do_talk(history)
    else:
        do_product(history)
    if not (MOCK or DRY_RUN):
        save(history)
        write_report(history)


if __name__ == "__main__":
    sys.exit(main())

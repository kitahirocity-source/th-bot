"""投稿文を作る（商品紹介＝本文＋リプ欄にリンク／共感・お役立ち＝リンクなし）"""
import random, re
from datetime import datetime, timedelta, timezone
from config import PERSONA, TALK_THEMES
from gemini import ask_json

JST = timezone(timedelta(hours=9))
URL_RE = re.compile(r"https?://\S+|www\.\S+")

RULES = """
# 必ず守るルール
- 使ってみた・食べてみた等の体験談は書かない（実際に使ったとは限らないため）
- 商品について書いてよい事実は「商品名・価格・レビュー件数・評価・商品説明」に書いてあることだけ
- 「絶対」「最強」「必ず痩せる」等の誇大表現、効果効能の断定は禁止
- ポイント倍率・キャンペーン・在庫・送料など、変わりやすい情報は書かない
- 本文にURLは書かない
- ハッシュタグは使わない
"""


def _recent(history):
    return "\n".join(f"- {h['text'][:40]}" for h in history[-12:]) or "（まだありません）"


def _good(history, kind):
    done = [h for h in history if h.get("kind") == kind and h.get("metrics")]
    done.sort(key=lambda h: h["metrics"].get("likes", 0) * 20 + h["metrics"].get("views", 0), reverse=True)
    return "\n".join(f"- {h['text'][:120]}" for h in done[:3]) or "（まだありません）"


def write_product(item: dict, genre: str, history: list) -> dict:
    now = datetime.now(JST)
    prompt = f"""あなたは次の人物としてThreads（スレッズ）に投稿します。
{PERSONA}
今日は{now:%Y年%m月%d日}です。

# 紹介する楽天の商品（ジャンル: {genre}）
商品名: {item['name']}
価格: {item['price']:,}円
レビュー: {item['reviews']:,}件 / 評価 {item['rating']}
ショップ: {item['shop']}
商品説明（抜粋）: {item['caption']}

# 反応が良かった過去の投稿（参考）
{_good(history, 'product')}

# 最近の投稿（同じ書き出しは避ける）
{_recent(history)}
{RULES}
# 作るもの
1. main: 本投稿（150文字以内）。1行目は【PR】で始め、2行目で「わかる」「知らなかった」と思わせる。
   季節や生活の悩みから入り、最後は「リンクはリプ欄に置いておきます👇」で締める。改行で読みやすく。
2. reply: リプ欄の文（60文字以内）。商品を一言で紹介し、価格とレビュー件数を入れる。URLは書かない。

# 出力（JSONのみ）
{{"main": "...", "reply": "..."}}"""
    for _ in range(3):
        d = ask_json(prompt)
        main = URL_RE.sub("", d.get("main", "")).strip()
        reply = URL_RE.sub("", d.get("reply", "")).strip()
        if main and reply and len(main) <= 300:
            if not main.startswith("【PR】"):
                main = "【PR】\n" + main
            reply = f"{reply[:120]}\n※価格は{now:%-m/%-d}時点\n{item['url']}"
            return {"main": main, "reply": reply}
        prompt += "\n\n※前回は長すぎるか形が違いました。"
    raise RuntimeError("商品紹介の文が作れませんでした")


def write_talk(history: list) -> dict:
    now = datetime.now(JST)
    theme = random.choice(TALK_THEMES)
    prompt = f"""あなたは次の人物としてThreads（スレッズ）に投稿します。
{PERSONA}
今日は{now:%Y年%m月%d日}（{now:%H}時ごろ）です。テーマ: {theme}

# 反応が良かった過去の投稿（参考）
{_good(history, 'talk')}

# 最近の投稿（同じ話題・同じ書き出しは避ける）
{_recent(history)}
{RULES}
- 「昨日お客さんが〜」のような具体的な出来事の作り話も禁止。一般論や考え方として書く
# 書き方
- 150文字以内、改行で読みやすく。共感されて返信したくなる終わり方に

# 出力（JSONのみ）
{{"main": "..."}}"""
    d = ask_json(prompt)
    text = URL_RE.sub("", d.get("main", "")).strip()[:450]
    if not text:
        raise RuntimeError("投稿文が空でした")
    return {"main": text, "theme": theme}

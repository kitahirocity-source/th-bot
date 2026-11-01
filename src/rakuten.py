"""楽天市場の商品検索（2026年の新仕様: accessKey と Referer が必須）"""
import os, random
import requests
from config import RAKUTEN_AFFILIATE_ID, MIN_REVIEWS, MIN_RATING

ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"


def search(keyword: str, exclude_codes: set) -> dict | None:
    r = requests.get(ENDPOINT, timeout=30,
                     headers={"Referer": os.getenv("RAKUTEN_REFERER", "")},
                     params={"applicationId": os.getenv("RAKUTEN_APP_ID"),
                             "accessKey": os.getenv("RAKUTEN_ACCESS_KEY"),
                             "affiliateId": RAKUTEN_AFFILIATE_ID, "keyword": keyword,
                             "hits": 30, "availability": 1, "sort": "-reviewCount",
                             "formatVersion": 2})
    if r.status_code != 200:
        print(f"[注意] 楽天APIエラー {r.status_code}: {r.text[:200]}")
        return None
    items = [i.get("Item", i) for i in r.json().get("Items", [])]
    ok = [i for i in items
          if i.get("affiliateUrl") and i.get("itemCode") not in exclude_codes
          and i.get("reviewCount", 0) >= MIN_REVIEWS and (i.get("reviewAverage") or 0) >= MIN_RATING]
    if not ok:
        return None
    pick = random.choice(ok[:8])  # 上位から少しばらつかせる
    return {"code": pick["itemCode"], "name": pick["itemName"], "price": int(pick["itemPrice"]),
            "url": pick["affiliateUrl"], "reviews": pick.get("reviewCount", 0),
            "rating": pick.get("reviewAverage", 0), "shop": pick.get("shopName", ""),
            "caption": (pick.get("itemCaption") or "")[:400]}

"""推薦（いつ・どこで思い出させるか）を作る。AI（Gemini / xAI Grok）があれば AI、なければルールで考える。

  推薦日・推薦理由 … 期間・締切・発売日・給料日・季節・お店の場所から考える（AI が使えなければ timing.py のルール）
  近くのお店      … places.py（既定はダミーのお店）で探し、通知の一言を AI に考えてもらう（だめならルールの文）
"""

from datetime import datetime

from app.models import Item
from app.services import ai, llm, places, timing
from app.services.genres import osm_tags_for

PERIOD_FIELDS = ["period_start", "period_end", "deadline", "release_date"]


def _item_values(item: Item) -> dict:
    return {f: getattr(item, f) for f in ["title", "genre", "price", *PERIOD_FIELDS]}


def store_for(item: Item, lat: float | None, lng: float | None) -> dict | None:
    """欲しいものを買えそうな場所。登録した地点があればそこ、なければ近くのお店（既定はダミー）。"""
    loc_lat = lat if lat is not None else places.DEFAULT_LOCATION["lat"]
    loc_lng = lng if lng is not None else places.DEFAULT_LOCATION["lng"]
    if item.place_lat is not None and item.place_lng is not None:
        return {"name": item.place_name or "登録した場所", "area": "登録した場所", "lat": item.place_lat, "lng": item.place_lng,
                "distanceM": round(places.distance_m(loc_lat, loc_lng, item.place_lat, item.place_lng))}
    if not (item.place_name or osm_tags_for(item.genre)):
        return None
    return places.nearest_store(loc_lat, loc_lng, item.place_name, osm_tags_for(item.genre))


def recommend_for_item(item: Item, now: datetime, lat: float | None = None, lng: float | None = None) -> tuple[list[dict], str, dict | None]:
    """(推薦 [{"remindAt", "reason", "basis"}], 考えたもの "gemini"/"xai"/"rules", 理由に使ったお店) を返す。"""
    store = store_for(item, lat, lng)
    hints = timing.suggest(_item_values(item), now)
    if llm.enabled():
        context = {"payday": timing.next_payday(now.astimezone(timing.TZ).date()), "hints": hints, "store": store}
        try:
            return ai.recommend_dates(_item_values(item), context, now), llm.provider(), store
        except Exception as err:
            print(f"AI で推薦を作れませんでした。ルールで作ります: {err!r}")

    recs = [{"remindAt": h["remindAt"], "reason": h["reason"], "basis": h["source"] if h["source"] in ai.BASIS else "other"}
            for h in hints]
    if store and recs:  # ルールのときも、お店が分かれば理由にそえる
        where = f"{store['name']}（{store['area']}）" if store.get("area") != "登録した場所" else store["name"]
        for r in recs:
            if r["basis"] in ("payday", "weekend", "week_later", "other", "release_date", "period_start"):
                r["reason"] += f" {where}で買えます。"
    return recs, "rules", store


def nearby_matches(items: list[Item], lat: float, lng: float) -> list[dict]:
    """今いる場所の近くで買える・行ける欲しいもの（理由の文つき・近い順）。"""
    matches = []
    rest = []
    for item in items:  # 1. 登録した地点の半径に入ったもの
        if item.place_lat is not None and item.place_lng is not None:
            d = places.distance_m(lat, lng, item.place_lat, item.place_lng)
            if d <= item.place_radius_m:
                label = item.place_name or "登録した場所"
                matches.append({"item": item, "placeName": label, "distanceM": round(d),
                                "reason": f"{label}の近くです。保存した「{item.title or '欲しいもの'}」を思い出して！"})
                continue
        if item.place_name or item.place_category:
            rest.append(item)

    # 2. お店の名前・種類だけのもの → 近くにそのお店があるか（既定はダミーのお店）
    tags = {tag for item in rest if not item.place_name for tag in osm_tags_for(item.genre)}
    names = {item.place_name for item in rest if item.place_name}
    shops = places.find_shops(lat, lng, tags, names) if rest else []
    for item in rest:
        found = [s for s in shops if places.shop_matches(s, item.place_name, osm_tags_for(item.genre))]
        if found:
            near = min(found, key=lambda s: places.distance_m(lat, lng, s["lat"], s["lng"]))
            d = round(places.distance_m(lat, lng, near["lat"], near["lng"]))
            matches.append({"item": item, "placeName": near["name"], "distanceM": d,
                            "reason": f"近くに{near['name']}があります（約{d}m）。「{item.title or '欲しいもの'}」を見ていきませんか？"})
    matches.sort(key=lambda m: m["distanceM"])

    source = "rules"
    if matches and llm.enabled():  # 通知の一言を AI に考えてもらう
        try:
            texts = ai.nearby_reasons([{"itemId": m["item"].id, "title": m["item"].title, "genre": m["item"].genre,
                                        "placeName": m["placeName"], "distanceM": m["distanceM"]} for m in matches])
            for m in matches:
                if m["item"].id in texts:
                    m["reason"] = texts[m["item"].id]
            source = llm.provider()
        except Exception as err:
            print(f"AI で通知の文を作れませんでした。ルールの文を使います: {err!r}")
    for m in matches:
        m["source"] = source
    return matches

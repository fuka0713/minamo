"""場所と結びつける：欲しいものを買えるお店がどこにあるか・今いる場所の近くにあるかを調べる。

お店の情報のとり方（POI_PROVIDER）：
  dummy    … （既定）下の DUMMY_STORES（新宿・渋谷・池袋あたりの、仮のお店）を使う。外部には問い合わせない
  overpass … 地図（OpenStreetMap の Overpass API）で調べる。送るのは「約100mに丸めた位置」と「お店の種類・名前」だけ
  none     … 調べない（登録した地点だけを使う）
"""

import math
import os
import re

import httpx

POI_PROVIDER = os.environ.get("POI_PROVIDER", "dummy")  # dummy / overpass / none
OVERPASS_URL = os.environ.get("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
SEARCH_RADIUS_M = int(os.environ.get("NEARBY_SEARCH_RADIUS_M", "300"))  # お店を探す範囲


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """2点の距離（メートル）。地球を球とみなす計算（ハバーサインの公式）。"""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _query(lat: float, lng: float, tags: set[tuple[str, str]], names: set[str]) -> str:
    """Overpass に送る問い合わせ文を作る。"""
    around = f"around:{SEARCH_RADIUS_M},{lat},{lng}"
    parts = [f'nwr({around})["{k}"="{v}"];' for k, v in sorted(tags)]
    if names:
        pattern = "|".join(re.escape(n).replace('"', "") for n in sorted(names))
        parts.append(f'nwr({around})["name"~"{pattern}",i];')
        parts.append(f'nwr({around})["brand"~"{pattern}",i];')
    return f"[out:json][timeout:8];({''.join(parts)});out center 50;"


# ---- ダミーのお店（位置はだいたい。画面の確認・発表用。本物のデータではない） ----
DEFAULT_LOCATION = {"lat": 35.6896, "lng": 139.7006, "area": "新宿駅"}  # 現在地がわからないときに使う場所
DUMMY_STORES = [
    {"name": "IKEA 新宿", "area": "新宿", "lat": 35.6935, "lng": 139.7033, "tags": {"shop": "furniture", "brand": "IKEA"}},
    {"name": "ニトリ 新宿店", "area": "新宿", "lat": 35.6918, "lng": 139.7046, "tags": {"shop": "furniture", "brand": "ニトリ"}},
    {"name": "マツモトキヨシ 新宿東口店", "area": "新宿", "lat": 35.6912, "lng": 139.7019,
     "tags": {"shop": "chemist", "brand": "マツモトキヨシ マツキヨ"}},
    {"name": "ユニクロ 新宿店", "area": "新宿", "lat": 35.6903, "lng": 139.7029, "tags": {"shop": "clothes", "brand": "ユニクロ UNIQLO"}},
    {"name": "ビックカメラ 新宿西口店", "area": "新宿", "lat": 35.6915, "lng": 139.6981, "tags": {"shop": "electronics", "brand": "ビックカメラ"}},
    {"name": "紀伊國屋書店 新宿本店", "area": "新宿", "lat": 35.6923, "lng": 139.7040, "tags": {"shop": "books", "brand": "紀伊國屋書店"}},
    {"name": "アニメイト 新宿", "area": "新宿", "lat": 35.6930, "lng": 139.7018, "tags": {"shop": "anime", "brand": "アニメイト"}},
    {"name": "ロフト 渋谷店", "area": "渋谷", "lat": 35.6612, "lng": 139.6990, "tags": {"shop": "gift", "brand": "ロフト LOFT"}},
    {"name": "ちいかわらんど 原宿店", "area": "原宿", "lat": 35.6715, "lng": 139.7050, "tags": {"shop": "toys", "brand": "ちいかわらんど"}},
    {"name": "ポケモンセンター メガトウキョー", "area": "池袋", "lat": 35.7289, "lng": 139.7193,
     "tags": {"shop": "toys", "brand": "ポケモンセンター"}},
    {"name": "らーめん ダミー屋 新宿", "area": "新宿", "lat": 35.6908, "lng": 139.7001, "tags": {"amenity": "restaurant"}},
    {"name": "カフェ ダミー 渋谷", "area": "渋谷", "lat": 35.6595, "lng": 139.7004, "tags": {"amenity": "cafe"}},
]


def find_shops(lat: float, lng: float, tags: set[tuple[str, str]], names: set[str], radius_m: int | None = None) -> list[dict]:
    """近くのお店を [{"name", "area", "lat", "lng", "tags"}] で返す。使わない設定・失敗したときは []。"""
    radius = radius_m or SEARCH_RADIUS_M
    if POI_PROVIDER == "dummy":
        return [dict(s) for s in DUMMY_STORES if distance_m(lat, lng, s["lat"], s["lng"]) <= radius]
    if POI_PROVIDER != "overpass" or not (tags or names):
        return []
    # 位置は約100mに丸めてから送る（細かい位置を外に出さない）
    q = _query(round(lat, 3), round(lng, 3), tags, names)
    try:
        res = httpx.post(OVERPASS_URL, data={"data": q}, timeout=10, headers={"User-Agent": "minamo-prototype"})
        res.raise_for_status()
        elements = res.json().get("elements", [])
    except (httpx.HTTPError, ValueError) as err:
        print(f"近くのお店を調べられませんでした: {err!r}")
        return []
    shops = []
    for e in elements:
        center = e.get("center", e)
        if "lat" in center and "lon" in center:
            t = e.get("tags", {})
            shops.append({"name": t.get("name") or t.get("brand") or "お店", "area": "近く", "lat": center["lat"],
                          "lng": center["lon"], "tags": t})
    return shops


def nearest_store(lat: float, lng: float, place_name: str | None, tags: list[tuple[str, str]], radius_m: int = 5000) -> dict | None:
    """欲しいものを買えそうなお店のうち、いちばん近いもの（distanceM つき）。なければ None。"""
    shops = [s for s in find_shops(lat, lng, set(tags), {place_name} if place_name else set(), radius_m)
             if shop_matches(s, place_name, tags)]
    if not shops:
        return None
    best = min(shops, key=lambda s: distance_m(lat, lng, s["lat"], s["lng"]))
    return {**best, "distanceM": round(distance_m(lat, lng, best["lat"], best["lng"]))}


def shop_matches(shop: dict, place_name: str | None, tags: list[tuple[str, str]]) -> bool:
    """お店が、商品の「お店の名前」か「お店の種類」に合っているか。"""
    t = shop["tags"]
    if place_name:
        key = place_name.lower()
        name, brand = str(t.get("name", shop.get("name", ""))).lower(), str(t.get("brand", "")).lower()
        return key in name or key in brand or (bool(brand) and any(b and b in key for b in brand.split()))
    return any(t.get(k) == v for k, v in tags)

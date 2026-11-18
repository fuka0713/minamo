"""場所と結びつける：今いる場所の近くに、欲しいものを買えるお店があるかを調べる。

2つのやり方：
  1. 商品に「場所（緯度・経度）」を登録してある → その場所から半径〇m以内に入ったら知らせる（外部に問い合わせない）
  2. 商品に「お店の名前・種類」だけがある → 地図（OpenStreetMap の Overpass API）で、近くにそのお店があるか調べる
     POI_PROVIDER=overpass のときだけ使う。送るのは「だいたいの位置（約100mに丸めたもの）」と「お店の種類・名前」だけ
"""

import math
import os
import re

import httpx

POI_PROVIDER = os.environ.get("POI_PROVIDER", "none")  # overpass / none
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


def find_shops(lat: float, lng: float, tags: set[tuple[str, str]], names: set[str]) -> list[dict]:
    """近くのお店を [{"name", "lat", "lng", "tags"}] で返す。使わない設定・失敗したときは []。"""
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
            shops.append({"name": t.get("name") or t.get("brand") or "お店", "lat": center["lat"], "lng": center["lon"], "tags": t})
    return shops


def shop_matches(shop: dict, place_name: str | None, tags: list[tuple[str, str]]) -> bool:
    """お店が、商品の「お店の名前」か「お店の種類」に合っているか。"""
    t = shop["tags"]
    if place_name:
        key = place_name.lower()
        return key in str(t.get("name", "")).lower() or key in str(t.get("brand", "")).lower()
    return any(t.get(k) == v for k, v in tags)

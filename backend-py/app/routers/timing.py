"""解析の結果から「いつ・どこで」思い出させるか。

  GET  /api/screenshots/{id}/reminder-suggestions … リマインドの候補（理由つき・最大3つ）
  POST /api/screenshots/{id}/reminders            … 候補から選んだ（または自分で決めた）リマインドを入れる
  PUT  /api/screenshots/{id}/place                … 場所（お店・緯度経度・半径）を登録する
  POST /api/screenshots/nearby                    … 今いる場所の近くに、欲しいものを買える場所があるか
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import item as item_crud
from app.database import get_db
from app.deps import current_user
from app.models import Item
from app.schemas import ErrorResponse, ItemOut, ReminderOut
from app.schemas.timing import NearbyIn, NearbyOut, PlaceIn, ReminderIn, SuggestionList
from app.services import places
from app.services.genres import osm_tags_for

router = APIRouter(prefix="/api/screenshots", tags=["いつ・どこで思い出す"])
NOTIFY_COOLDOWN = timedelta(hours=24)  # 同じ商品を、場所で知らせるのは24時間に1回まで
ERRORS = {401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}


def _own_item(db: Session, user_id: int, item_id: int) -> Item:
    item = item_crud.get_item(db, user_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="見つかりません")
    return item


@router.get("/{item_id}/reminder-suggestions", response_model=SuggestionList, responses=ERRORS,
            summary="リマインドの候補を見る",
            description="解析で読み取った期間（開催期間・締切・発売日）・ジャンル・給料日（仮：毎月25日）から、"
            "いつ思い出させるとよいかを理由つきで最大3つ返す。過去の日時は返さない。")
def reminder_suggestions(item_id: int, user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    return {"suggestions": item_crud.suggestions_for(_own_item(db, user_id, item_id))}


@router.post("/{item_id}/reminders", status_code=201, response_model=ReminderOut,
             responses={**ERRORS, 400: {"model": ErrorResponse}}, summary="リマインドを入れる",
             description="候補から選んだ日時（または自分で決めた日時）でリマインドを入れる。自動で入っていたリマインドは取り消す。")
def add_reminder(item_id: int, body: ReminderIn, user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    item = _own_item(db, user_id, item_id)
    if body.remindAt.tzinfo is None:
        raise HTTPException(status_code=400, detail="日時にはタイムゾーンをつけてください（例：+09:00）")
    if body.remindAt <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail="過去の日時は選べません")
    r = item_crud.add_user_reminder(db, item, body.remindAt, body.reason)
    return {"id": r.id, "remindAt": r.remind_at, "reason": r.reason, "status": r.status, "source": r.source}


@router.put("/{item_id}/place", response_model=ItemOut, responses={**ERRORS, 400: {"model": ErrorResponse}},
            summary="場所を登録する",
            description="「ここを通ったら知らせて」の場所を登録する。lat・lng はブラウザの現在地などから送る。"
            "送った項目だけ変わる（null を送ると消す）。お店の名前・種類を直すと、再解析では上書きしない。")
def set_place(item_id: int, body: PlaceIn, user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    item = _own_item(db, user_id, item_id)
    values = body.model_dump(exclude_unset=True)
    for key in ("radiusM", "visible"):  # この2つは空にできない
        if key in values and values[key] is None:
            del values[key]
    lat = values.get("lat", item.place_lat)
    lng = values.get("lng", item.place_lng)
    if (lat is None) != (lng is None):
        raise HTTPException(status_code=400, detail="緯度（lat）と経度（lng）は、両方そろえて送ってください")
    return item_crud.to_out(db, item_crud.set_place(db, item, values))


@router.post("/nearby", response_model=NearbyOut, responses={401: {"model": ErrorResponse}},
             summary="近くに欲しいものがあるか調べる",
             description="画面（スマホ）が今いる場所を送ると、近くで買える・行ける欲しいものを返す。"
             "登録した場所の半径内に入ったもの、近くに同じお店（名前・種類）があるものが対象。"
             "同じ商品は24時間に1回まで。送った位置は保存しない。")
def nearby(body: NearbyIn, user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    now = datetime.now(UTC)
    candidates = item_crud.place_candidates(db, user_id, now, NOTIFY_COOLDOWN)
    matches, notified = [], []

    # 1. 登録した場所（緯度・経度）の半径に入ったもの（外部に問い合わせない）
    rest = []
    for item in candidates:
        if item.place_lat is not None and item.place_lng is not None:
            d = places.distance_m(body.lat, body.lng, item.place_lat, item.place_lng)
            if d <= item.place_radius_m:
                label = item.place_name or "登録した場所"
                matches.append((item, label, d, f"{label}の近くです。保存した「{item.title or '欲しいもの'}」を思い出して！"))
                continue
        if item.place_name or item.place_category:
            rest.append(item)

    # 2. お店の名前・種類だけのもの → 近くにそのお店があるか地図で調べる（POI_PROVIDER=overpass のときだけ）
    tags = {tag for item in rest if not item.place_name for tag in osm_tags_for(item.genre)}
    names = {item.place_name for item in rest if item.place_name}
    shops = places.find_shops(body.lat, body.lng, tags, names) if rest else []
    for item in rest:
        found = [s for s in shops if places.shop_matches(s, item.place_name, osm_tags_for(item.genre))]
        if not found:
            continue
        nearest = min(found, key=lambda s: places.distance_m(body.lat, body.lng, s["lat"], s["lng"]))
        d = places.distance_m(body.lat, body.lng, nearest["lat"], nearest["lng"])
        what = item.place_name or item.place_category or "お店"
        matches.append((item, nearest["name"], d, f"近くに{what}（{nearest['name']}）があります。「{item.title or '欲しいもの'}」を見ていきませんか？"))

    for item, _, _, _ in matches:
        notified.append(item)
    item_crud.mark_place_notified(db, notified, now)
    return {"matches": [
        {"itemId": item.id, "title": item.title, "imageUrl": f"/api/items/{item.id}/image", "placeName": label,
         "distanceM": round(d), "reason": reason}
        for item, label, d, reason in sorted(matches, key=lambda m: m[2])
    ]}

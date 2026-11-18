"""解析 API の側：欲しいもの1件のリマインドと場所を、自分で決める。

  POST /api/screenshots/{id}/reminders … 自分で決めた日時でリマインドを入れる
  PUT  /api/screenshots/{id}/place     … 場所（お店・緯度経度・半径）を登録する

いつ・どこで思い出させるかの「推薦」は、推薦 API（routers/recommendations.py）が担当する。
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import item as item_crud
from app.database import get_db
from app.deps import current_user
from app.models import Item
from app.services.timeutil import to_utc
from app.schemas import ErrorResponse, ItemOut, ReminderOut
from app.schemas.timing import PlaceIn, ReminderIn

router = APIRouter(prefix="/api/screenshots", tags=["解析：リマインドと場所"])
ERRORS = {400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}


def own_item(db: Session, user_id: int, item_id: int) -> Item:
    item = item_crud.get_item(db, user_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="見つかりません")
    return item


@router.post("/{item_id}/reminders", status_code=201, response_model=ReminderOut, responses=ERRORS,
             summary="リマインドを自分で入れる", description="自分で決めた日時でリマインドを入れる。自動で入っていたリマインドは取り消す。")
def add_reminder(item_id: int, body: ReminderIn, user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    item = own_item(db, user_id, item_id)
    if body.remindAt.tzinfo is None:
        raise HTTPException(status_code=400, detail="日時にはタイムゾーンをつけてください（例：+09:00）")
    if body.remindAt <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail="過去の日時は選べません")
    r = item_crud.add_user_reminder(db, item, body.remindAt, body.reason)
    return {"id": r.id, "remindAt": to_utc(r.remind_at), "reason": r.reason, "status": r.status, "source": r.source}


@router.put("/{item_id}/place", response_model=ItemOut, responses=ERRORS, summary="場所を登録する",
            description="「ここを通ったら知らせて」の場所を登録する。lat・lng はブラウザの現在地などから送る。"
            "送った項目だけ変わる（null を送ると消す）。お店の名前・種類を直すと、再解析では上書きしない。")
def set_place(item_id: int, body: PlaceIn, user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    item = own_item(db, user_id, item_id)
    values = body.model_dump(exclude_unset=True)
    for key in ("radiusM", "visible"):  # この2つは空にできない
        if key in values and values[key] is None:
            del values[key]
    lat, lng = values.get("lat", item.place_lat), values.get("lng", item.place_lng)
    if (lat is None) != (lng is None):
        raise HTTPException(status_code=400, detail="緯度（lat）と経度（lng）は、両方そろえて送ってください")
    return item_crud.to_out(db, item_crud.set_place(db, item, values))

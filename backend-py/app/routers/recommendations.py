"""推薦 API：いつ・どこで思い出させるか（通知のもとになる）。解析 API とは分けている。

  POST /api/recommendations/items/{id}  … 推薦日と推薦理由を作る（AI があれば AI、なければルール）。1つを自動でリマインドにする
  GET  /api/recommendations/items/{id}  … その欲しいものの推薦
  GET  /api/recommendations             … ホーム用：見直すとよい欲しいもの（商品ごとに一番近い推薦）
  POST /api/recommendations/{rid}/accept … 推薦をリマインドにする（自分で選んだ扱い）
  POST /api/recommendations/nearby       … 今いる場所の近くで買える欲しいもの（理由つき）
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud import item as item_crud
from app.crud import recommendation as rec_crud
from app.database import get_db
from app.deps import current_user
from app.routers.timing import own_item
from app.services.timeutil import to_utc
from app.schemas import ErrorResponse, ReminderOut
from app.schemas.recommendation import Location, NearbyIn, NearbyOut, RecommendationList
from app.services import recommend

router = APIRouter(prefix="/api/recommendations", tags=["推薦（通知のもと）"])
NOTIFY_COOLDOWN = timedelta(hours=24)  # 同じ商品を、場所で知らせるのは24時間に1回まで
ERRORS = {401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}


@router.post("/nearby", response_model=NearbyOut, responses={401: {"model": ErrorResponse}},
             summary="近くで買える欲しいものを調べる",
             description="今いる場所を送ると、近くで買える・行ける欲しいものを推薦理由つきで返す。"
             "お店の情報は POI_PROVIDER で決まる（既定 dummy＝新宿・渋谷・池袋あたりの仮のお店）。"
             "同じ商品は24時間に1回まで。送った位置は保存しない。")
def nearby(body: NearbyIn, user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    now = datetime.now(UTC)
    matches = recommend.nearby_matches(item_crud.place_candidates(db, user_id, now, NOTIFY_COOLDOWN), body.lat, body.lng)
    item_crud.mark_place_notified(db, [m["item"] for m in matches], now)
    return {"matches": [
        {"itemId": m["item"].id, "title": m["item"].title, "imageUrl": f"/api/items/{m['item'].id}/image",
         "placeName": m["placeName"], "distanceM": m["distanceM"], "reason": m["reason"], "source": m["source"]}
        for m in matches
    ]}


@router.post("/items/{item_id}", response_model=RecommendationList, responses=ERRORS, summary="推薦を作る",
             description="解析した項目（期間・締切・発売日・ジャンル・価格）・給料日（仮：毎月25日）・お店の場所から、"
             "いつ知らせるとよいか（推薦日）と理由（推薦理由）を最大3つ作る。GEMINI_API_KEY か XAI_API_KEY があれば AI が考え、"
             "なければ（失敗したら）ルールで作る。1つを自動でリマインドにする（自分で選んだリマインドがあれば入れない）。"
             "body に今いる場所を入れると、近いお店を理由に使う（なければ新宿駅のまわりで探す）。")
def create(item_id: int, body: Location | None = None, user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    item = own_item(db, user_id, item_id)
    loc = body or Location()
    recs, source, store = recommend.recommend_for_item(item, datetime.now(UTC), loc.lat, loc.lng)
    rows = rec_crud.replace_for_item(db, item, recs, source, store)
    return {"recommendations": [rec_crud.to_out(r) for r in rows]}


@router.get("/items/{item_id}", response_model=RecommendationList, responses=ERRORS, summary="欲しいものの推薦を見る")
def list_for_item(item_id: int, user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    own_item(db, user_id, item_id)
    return {"recommendations": [rec_crud.to_out(r) for r in rec_crud.list_for_item(db, item_id)]}


@router.get("", response_model=RecommendationList, responses={401: {"model": ErrorResponse}},
            summary="見直すとよい欲しいもの（ホーム用）",
            description="欲しい・保留の欲しいものごとに、いちばん近い推薦を1つずつ、日時の早い順に返す（item つき）。")
def list_home(limit: int = Query(4, ge=1, le=20), user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    return {"recommendations": [rec_crud.to_out(rec, item) for rec, item in rec_crud.list_for_user(db, user_id, limit)]}


@router.post("/{rec_id}/accept", status_code=201, response_model=ReminderOut, responses={**ERRORS, 400: {"model": ErrorResponse}},
             summary="推薦をリマインドにする", description="この推薦の日時と理由で、リマインドを入れる（自動のリマインドは取り消す）。")
def accept(rec_id: int, user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    found = rec_crud.get_own(db, user_id, rec_id)
    if not found:
        raise HTTPException(status_code=404, detail="見つかりません")
    rec, item = found
    at = to_utc(rec.recommend_at)
    if at <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail="この推薦の日時は過ぎています。推薦を作り直してください")
    r = item_crud.add_user_reminder(db, item, at, rec.reason)
    rec.status = "accepted"
    db.commit()
    return {"id": r.id, "remindAt": to_utc(r.remind_at), "reason": r.reason, "status": r.status, "source": r.source}

"""P1 欲しいもの：スクショの登録（解析つき）・一覧・詳細・画像・修正・削除・ジャンル。"""

from typing import Literal

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app import config
from app.crud import item as item_crud
from app.crud import lifestyle as lifestyle_crud
from app.database import get_db
from app.deps import current_user
from app.errors import ApiError, ErrorEnvelope, not_found
from app.schemas.item import GenreList, ItemOut, ItemPage, ItemPatch, ItemStatus
from app.services import analysis, storage
from app.services.genres import GENRE_NAMES
from app.services.ids import new_id
from app.services.suggestions import suggestions_for
from app.services.timeutil import now_utc

router = APIRouter(tags=["Items"])
ERRORS = {400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}}


@router.post("/api/items", status_code=201, response_model=ItemOut, summary="スクショを解析して商品候補を登録", responses=ERRORS,
             description="フォームの `image` に画像を1枚（PNG・JPEG・WebP、10MBまで）。複数枚なら1枚ずつ呼ぶ。"
             "商品を特定できなくても、スクショは保存して、仮の名前の候補を返す。リマインドの日時も自動で決めて入れる。")
def create_item(image: UploadFile = File(description="スクショ1枚"), user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    if image.content_type not in config.ALLOWED_IMAGE_TYPES:
        raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "PNG・JPEG・WebP の画像を選んでください。")
    data = image.file.read(config.MAX_IMAGE_BYTES + 1)
    if len(data) > config.MAX_IMAGE_BYTES:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", "10MB 以下の画像にしてください。")
    if not data:
        raise ApiError(400, "EMPTY_IMAGE", "画像が空です。")

    now = now_utc()
    image_key = f"users/{user_id}/{new_id('img')}"
    storage.save_image(image_key, data, image.content_type)  # 1. 画像を保存
    result = analysis.analyze(data, image.content_type, now)  # 2. 解析（Gemini か、OCR とルール）
    item = item_crud.create(db, user_id, image_key, result)  # 3. 欲しいものとして登録

    # 4. リマインドの日時を自動で決める（期間と生活スタイルから、いちばん早い候補）
    payday, preferences = lifestyle_crud.payday_and_preferences(db, user_id)
    suggestions = suggestions_for(item, payday, preferences, now)
    if suggestions:
        first = suggestions[0]
        item_crud.add_reminder(db, item, first["remindAt"], first["reason"], "auto")
    return item_crud.to_out(item)


@router.get("/api/items", response_model=ItemPage, summary="自分の欲しいものを検索・一覧", responses=ERRORS)
def list_items(
    genre: str | None = Query(None, description="ジャンルで絞り込み"),
    keyword: str | None = Query(None, description="商品名・ブランド・メモ・読み取った文字から探す"),
    status: ItemStatus | None = Query(None, description="状態で絞り込み"),
    sort: Literal["createdAt", "remindAt", "price"] = Query("createdAt"),
    order: Literal["asc", "desc"] = Query("desc"),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, description="前のページの nextCursor"),
    user_id: str = Depends(current_user), db: Session = Depends(get_db),
):
    try:
        offset = int(cursor) if cursor else 0
    except ValueError as err:
        raise ApiError(400, "INVALID_CURSOR", "cursor が正しくありません。") from err
    items, more = item_crud.list_page(db, user_id, genre=genre, keyword=keyword, status=status,
                                      sort=sort, order=order, limit=limit, offset=max(offset, 0))
    return {"items": [item_crud.to_out(i) for i in items], "nextCursor": str(offset + limit) if more else None}


@router.get("/api/items/{id}", response_model=ItemOut, summary="商品詳細", responses=ERRORS)
def get_item(id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    item = item_crud.get_own(db, user_id, id)
    if item is None:
        raise not_found()
    return item_crud.to_out(item)


@router.patch("/api/items/{id}", response_model=ItemOut, summary="指定した商品項目だけ更新", responses=ERRORS)
def patch_item(id: str, body: ItemPatch, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    item = item_crud.get_own(db, user_id, id)
    if item is None:
        raise not_found()
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise ApiError(400, "EMPTY_PATCH", "変更する項目を1つ以上送ってください。")
    if "genre" in changes and changes["genre"] not in GENRE_NAMES:
        raise ApiError(400, "INVALID_GENRE", "ジャンルが正しくありません。/api/genres のどれかにしてください。")
    if "name" in changes and not (changes["name"] or "").strip():
        raise ApiError(400, "INVALID_NAME", "商品名を入れてください。")
    return item_crud.to_out(item_crud.update(db, item, changes))


@router.delete("/api/items/{id}", status_code=204, summary="商品と関連画像を削除", responses=ERRORS)
def delete_item(id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    item = item_crud.get_own(db, user_id, id)
    if item is None:
        raise not_found()
    image_key = item.image_key
    item_crud.delete(db, item)
    try:
        storage.delete_image(image_key)
    except Exception as err:  # 画像が消せなくても、データは消えているので続ける
        print(f"画像を消せませんでした（{image_key}）: {err!r}")


@router.get("/api/items/{id}/image", summary="商品スクリーンショット画像", response_class=Response, responses=ERRORS)
def get_image(id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    item = item_crud.get_own(db, user_id, id)
    if item is None:
        raise not_found()
    try:
        data, content_type = storage.load_image(item.image_key)
    except Exception as err:
        raise not_found() from err
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "private, max-age=86400"})


@router.get("/api/genres", response_model=GenreList, summary="公開ジャンル一覧")
def list_genres():
    return {"genres": GENRE_NAMES}

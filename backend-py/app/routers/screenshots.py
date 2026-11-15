"""スクショの登録と解析。

  POST /api/screenshots               … 登録（登録した日と画像だけを入れる）
  POST /api/screenshots/{id}/analyze  … 解析（OCR などで、埋められる項目を埋める）
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.crud import item as item_crud
from app.database import get_db
from app.deps import current_user
from app.schemas import ErrorResponse, ItemOut
from app.services import analyzer, ocr, storage

router = APIRouter(prefix="/api/screenshots", tags=["スクショ"])

MAX_SIZE = 10 * 1024 * 1024  # 1枚 10MB まで


@router.post(
    "",
    status_code=201,
    response_model=list[ItemOut],
    summary="スクショを登録する",
    description="画像を保存して、「登録した日」と「画像」だけを入れる。ほかの項目は、解析 API で埋める。",
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
)
def register(files: list[UploadFile], user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    # 先に全部のファイルを確かめる（1枚でもおかしければ、何も登録しない）
    images = []
    for file in files:
        data = file.file.read()
        if not (file.content_type or "").startswith("image/"):
            raise HTTPException(status_code=400, detail=f"画像ではありません：{file.filename}")
        if len(data) > MAX_SIZE:
            raise HTTPException(status_code=400, detail=f"10MB より大きい画像です：{file.filename}")
        images.append((data, file.content_type))

    created = []
    for data, content_type in images:
        image_key = f"users/{user_id}/{uuid.uuid4()}"  # 人ごとにフォルダを分ける
        storage.save_image(image_key, data, content_type)
        item = item_crud.create_item(db, user_id, image_key)
        created.append(item_crud.to_out(db, item))
    return created


@router.post(
    "/{item_id}/analyze",
    response_model=ItemOut,
    summary="スクショを解析して、項目を埋める",
    description="画像の文字を読み取り、商品名・説明文・価格・ジャンル・場所のうち、埋められるところを埋める。"
    "ユーザーが直した項目は上書きしない（force=true のときだけ上書きする）。失敗したら analysis.status が failed になり、もう一度呼べばやり直せる。",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def analyze(item_id: int, force: bool = False, user_id: int = Depends(current_user), db: Session = Depends(get_db)):
    item = item_crud.get_item(db, user_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="見つかりません")

    try:
        image = storage.load_image(item.image_key)  # 1. 画像を読む
        text = ocr.read_text(image)  # 2. 文字を読み取る
    except Exception as err:  # 読み取れなかったら「失敗」を記録して返す
        print(f"解析に失敗しました（id={item_id}）: {err}")
        item = item_crud.mark_analysis_failed(db, item)
        return item_crud.to_out(db, item)

    values = analyzer.analyze(text)  # 3. 文字から項目を取り出す
    item = item_crud.apply_analysis(db, item, text, values, force=force)  # 4. 埋めて保存
    return item_crud.to_out(db, item)

"""欲しいもの（items テーブル）の読み書き。"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Item, Reminder

# 解析で埋める項目（ユーザーが直した項目は、再解析で上書きしない）
ANALYZED_FIELDS = ["title", "description", "price", "genre", "place_category", "place_name"]


def create_item(db: Session, user_id: int, image_key: str) -> Item:
    """登録：登録した日と画像だけを入れて保存する（ほかの項目は解析で埋める）。"""
    item = Item(user_id=user_id, image_key=image_key)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_item(db: Session, user_id: int, item_id: int) -> Item | None:
    """自分の欲しいものを1件読む（他の人のものは None）。"""
    return db.scalar(select(Item).where(Item.id == item_id, Item.user_id == user_id))


def list_reminders(db: Session, item_id: int) -> list[Reminder]:
    """商品のリマインド日を、日時の早い順に読む。"""
    return list(db.scalars(select(Reminder).where(Reminder.item_id == item_id).order_by(Reminder.remind_at)))


def apply_analysis(db: Session, item: Item, ocr_text: str, values: dict, force: bool = False) -> Item:
    """解析の結果で、埋められる項目を埋める。

    ユーザーが直した項目（edited_fields）は、force=True でないかぎり上書きしない。
    """
    for field in ANALYZED_FIELDS:
        if force or field not in item.edited_fields:
            setattr(item, field, values.get(field))
    if force or "genre" not in item.edited_fields:
        item.genre_source = "auto"
    item.ocr_text = ocr_text
    item.analysis_status = "done"
    item.analyzed_at = datetime.now(UTC)
    db.commit()
    db.refresh(item)
    return item


def mark_analysis_failed(db: Session, item: Item) -> Item:
    """解析に失敗したことを記録する（画像は残るので、あとでやり直せる）。"""
    item.analysis_status = "failed"
    item.analyzed_at = datetime.now(UTC)
    db.commit()
    db.refresh(item)
    return item


def to_out(db: Session, item: Item) -> dict:
    """データベースの1件を、API で返す形（schemas.ItemOut）にする。"""
    return {
        "id": item.id,
        "createdAt": item.created_at,
        "imageUrl": f"/api/items/{item.id}/image",
        "analysis": {"status": item.analysis_status, "analyzedAt": item.analyzed_at},
        "title": item.title,
        "description": item.description,
        "price": {"value": item.price, "visible": item.price_visible},
        "wishStatus": item.wish_status,
        "genre": item.genre,
        "place": {"category": item.place_category, "name": item.place_name, "visible": item.place_visible},
        "reminders": [
            {"id": r.id, "remindAt": r.remind_at, "reason": r.reason, "status": r.status}
            for r in list_reminders(db, item.id)
        ],
    }

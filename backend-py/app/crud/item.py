"""欲しいもの（items テーブル）の読み書き。"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Item, Reminder
from app.services import timing
from app.services.timeutil import to_utc

# 解析で埋める項目（ユーザーが直した項目は、再解析で上書きしない）
ANALYZED_FIELDS = ["title", "description", "price", "genre", "place_category", "place_name"]
PERIOD_FIELDS = ["period_start", "period_end", "deadline", "release_date"]  # 期間（まとめて「period」として扱う）


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


def apply_analysis(db: Session, item: Item, ocr_text: str, values: dict, force: bool = False, analyzer: str = "rules") -> Item:
    """解析の結果で、埋められる項目を埋める。

    ユーザーが直した項目（edited_fields）は、force=True でないかぎり上書きしない。
    """
    for field in ANALYZED_FIELDS:
        if force or field not in item.edited_fields:
            setattr(item, field, values.get(field))
    if force or "genre" not in item.edited_fields:
        item.genre_source = "auto"
    if force or ("period" not in item.edited_fields and item.period_source != "user"):
        for field in PERIOD_FIELDS:
            setattr(item, field, values.get(field))
        item.period_source = "auto"
    item.ocr_text = ocr_text
    item.analyzer = analyzer
    item.analysis_status = "done"
    item.analyzed_at = datetime.now(UTC)
    db.commit()
    db.refresh(item)
    return item


# ---------------- リマインド ----------------

def suggestions_for(item: Item, now: datetime | None = None) -> list[dict]:
    """ルールで作るリマインド候補（理由つき・最大3つ）。AI が使えないときの推薦と、AI へのヒントに使う。"""
    values = {field: getattr(item, field) for field in ["title", "genre", *PERIOD_FIELDS]}
    return timing.suggest(values, now or datetime.now(UTC))


def add_user_reminder(db: Session, item: Item, remind_at: datetime, reason: str | None) -> Reminder:
    """ユーザーが選んだ（推薦を受け入れた）リマインドを入れる（自動のリマインドは取り消す）。"""
    for r in list_reminders(db, item.id):
        if r.source == "auto" and r.status == "scheduled":
            r.status = "canceled"
    reminder = Reminder(item_id=item.id, remind_at=to_utc(remind_at), reason=reason or "自分で決めた日時です。", source="user")
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


# ---------------- 場所 ----------------

def set_place(db: Session, item: Item, values: dict) -> Item:
    """場所を登録・変更する（送った項目だけ）。お店の名前・種類を変えたら、再解析で上書きしない。"""
    for key, column in [("name", "place_name"), ("category", "place_category"), ("lat", "place_lat"),
                        ("lng", "place_lng"), ("radiusM", "place_radius_m"), ("visible", "place_visible")]:
        if key in values:
            setattr(item, column, values[key])
            if column in ANALYZED_FIELDS and column not in item.edited_fields:
                item.edited_fields = [*item.edited_fields, column]
    db.commit()
    db.refresh(item)
    return item


def place_candidates(db: Session, user_id: int, now: datetime, cooldown: timedelta) -> list[Item]:
    """場所で知らせてよい商品（欲しい・保留で、最近は場所で知らせていないもの）。"""
    items = db.scalars(select(Item).where(Item.user_id == user_id, Item.wish_status != "not_want"))
    out = []
    for item in items:
        last = item.place_notified_at
        if last and last.tzinfo is None:  # SQLite はタイムゾーンを持たないので UTC とみなす
            last = last.replace(tzinfo=UTC)
        if last and now - last < cooldown:
            continue
        if item.place_lat is not None or item.place_name or item.place_category:
            out.append(item)
    return out


def mark_place_notified(db: Session, items: list[Item], now: datetime) -> None:
    for item in items:
        item.place_notified_at = now
    db.commit()


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
        "analysis": {"status": item.analysis_status, "analyzedAt": item.analyzed_at, "analyzer": item.analyzer},
        "title": item.title,
        "description": item.description,
        "price": {"value": item.price, "visible": item.price_visible},
        "wishStatus": item.wish_status,
        "genre": item.genre,
        "place": {"category": item.place_category, "name": item.place_name, "visible": item.place_visible,
                  "lat": item.place_lat, "lng": item.place_lng, "radiusM": item.place_radius_m},
        "period": {"start": item.period_start, "end": item.period_end, "deadline": item.deadline,
                   "release": item.release_date, "source": item.period_source},
        "reminders": [
            {"id": r.id, "remindAt": to_utc(r.remind_at), "reason": r.reason, "status": r.status, "source": r.source}
            for r in list_reminders(db, item.id)
        ],
    }

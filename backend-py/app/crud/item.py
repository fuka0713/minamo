"""欲しいもの（items）とリマインド（reminders）の読み書き。"""

from datetime import datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Item, Reminder
from app.services.analyzer import to_datetime
from app.services.ids import new_id
from app.services.suggestions import TZ
from app.services.timeutil import as_utc

ACTIVE = ("wanted", "hold")


# ---------------- 欲しいもの ----------------

def create(db: Session, user_id: str, image_key: str, analysis: dict) -> Item:
    """解析の結果から、欲しいものを1件作る。"""
    period = analysis.get("period")
    item = Item(
        id=new_id("itm"), user_id=user_id, image_key=image_key,
        name=analysis["name"], brand=analysis["brand"], genre=analysis["genre"],
        price=analysis["price"], currency=analysis["currency"], shop=analysis["shop"], url=analysis["url"],
        memo=analysis["memo"], identification=analysis["identification"], confidence=analysis["confidence"],
        analyzer=analysis["analyzer"], ocr_text=analysis["ocr_text"], limited_kind=analysis.get("limited_kind"),
        period_type=period["type"] if period else None,
        period_start_at=to_datetime(period["start"], 0, TZ) if period else None,
        period_end_at=to_datetime(period["end"], 0, TZ) if period else None,
    )
    db.add(item)
    db.commit()
    return item


def get_own(db: Session, user_id: str, item_id: str) -> Item | None:
    """自分の欲しいものだけを読む（他の人のものは None）。"""
    return db.scalar(select(Item).where(Item.id == item_id, Item.user_id == user_id))


def list_page(db: Session, user_id: str, *, genre: str | None, keyword: str | None, status: str | None,
              sort: str, order: str, limit: int, offset: int) -> tuple[list[Item], bool]:
    """一覧を1ページ分読む。2つ目の値は「続きがあるか」。"""
    query = select(Item).where(Item.user_id == user_id)
    if genre:
        query = query.where(Item.genre == genre)
    if status:
        query = query.where(Item.status == status)
    if keyword:
        like = f"%{keyword}%"
        query = query.where(or_(Item.name.ilike(like), Item.brand.ilike(like), Item.memo.ilike(like), Item.ocr_text.ilike(like)))
    column = {"createdAt": Item.created_at, "remindAt": Item.remind_at, "price": Item.price}[sort]
    ordered = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()
    query = query.order_by(ordered, Item.id.desc()).offset(offset).limit(limit + 1)
    rows = list(db.scalars(query))
    return rows[:limit], len(rows) > limit


def count_recent(db: Session, user_id: str, since: datetime) -> int:
    """since より後に登録した数（送りすぎを止めるため）。"""
    return db.scalar(select(func.count()).select_from(Item).where(Item.user_id == user_id, Item.created_at >= since)) or 0


def count(db: Session, user_id: str) -> int:
    return db.scalar(select(func.count()).select_from(Item).where(Item.user_id == user_id)) or 0


def update(db: Session, item: Item, changes: dict) -> Item:
    """送られてきた項目だけを変える（changes には、送られた項目だけが入っている）。"""
    if "limitedKind" in changes:
        item.limited_kind = changes.pop("limitedKind")
    for key in ("name", "brand", "genre", "price", "currency", "shop", "url", "memo", "repeat"):
        if key in changes:
            setattr(item, key, changes[key])
    if "period" in changes:
        period = changes["period"]
        item.period_type = period["type"] if period else None
        item.period_start_at = period.get("startAt") if period else None
        item.period_end_at = period.get("endAt") if period else None
    if "status" in changes:
        item.status = changes["status"]
        if item.status not in ACTIVE:  # 買った・いらない → 予定のリマインドは取り消す
            cancel_all_reminders(db, item)
    db.commit()
    return item


def delete(db: Session, item: Item) -> None:
    db.delete(item)
    db.commit()


def to_out(item: Item) -> dict:
    """データベースの1件を、API で返す形（schemas.ItemOut）にする。"""
    period = None
    if item.period_type:
        period = {"type": item.period_type, "startAt": as_utc(item.period_start_at), "endAt": as_utc(item.period_end_at)}
    return {
        "id": item.id, "name": item.name, "brand": item.brand, "genre": item.genre,
        "price": float(item.price) if item.price is not None else None, "currency": item.currency,
        "shop": item.shop, "url": item.url, "period": period,
        "identification": item.identification, "confidence": item.confidence, "status": item.status,
        "memo": item.memo, "createdAt": as_utc(item.created_at), "remindAt": as_utc(item.remind_at),
        "imageUrl": f"/api/items/{item.id}/image", "reminderReason": item.reminder_reason, "repeat": item.repeat,
        "limitedUntil": limited_until(item), "limitedKind": item.limited_kind,
    }


def limited_until(item: Item) -> datetime | None:
    """期間限定・締切の終わり（その日の 23:59:59、利用者のタイムゾーン）。開催期間か締切の「終わり」があるときだけ。"""
    if item.period_type not in ("event_period", "deadline") or not item.period_end_at:
        return None
    end = as_utc(item.period_end_at).astimezone(TZ).date()
    return datetime.combine(end, time(23, 59, 59), tzinfo=TZ)


# ---------------- リマインド ----------------

def add_reminder(db: Session, item: Item, remind_at: datetime, reason: str, source: str) -> Reminder:
    reminder = Reminder(id=new_id("rmd"), item_id=item.id, user_id=item.user_id, remind_at=remind_at, reason=reason, source=source)
    db.add(reminder)
    db.flush()
    refresh_remind_at(db, item)
    db.commit()
    return reminder


def list_reminders(db: Session, item_id: str) -> list[Reminder]:
    return list(db.scalars(select(Reminder).where(Reminder.item_id == item_id).order_by(Reminder.remind_at)))


def get_own_reminder(db: Session, user_id: str, reminder_id: str) -> Reminder | None:
    return db.scalar(select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id))


def cancel_reminder(db: Session, reminder: Reminder) -> None:
    reminder.status = "cancelled"
    db.flush()
    item = db.get(Item, reminder.item_id)
    if item:
        refresh_remind_at(db, item)
    db.commit()


def cancel_all_reminders(db: Session, item: Item) -> None:
    for reminder in list_reminders(db, item.id):
        if reminder.status == "scheduled":
            reminder.status = "cancelled"
    item.remind_at, item.reminder_reason = None, None


def refresh_remind_at(db: Session, item: Item) -> None:
    """商品の remindAt を「いちばん早い予定のリマインド」にする（予定がなければそのまま）。"""
    scheduled = [r for r in list_reminders(db, item.id) if r.status == "scheduled"]
    if scheduled:
        first = min(scheduled, key=lambda r: as_utc(r.remind_at))
        item.remind_at, item.reminder_reason = first.remind_at, first.reason


def reminder_out(reminder: Reminder) -> dict:
    return {"id": reminder.id, "itemId": reminder.item_id, "remindAt": as_utc(reminder.remind_at),
            "reason": reminder.reason, "status": reminder.status}


def later_time(now: datetime, hour: int, days: int = 3) -> datetime:
    """「あとで」と答えたときの、次に知らせる日時（days 日後の決まった時刻）。"""
    d = now.astimezone(TZ).date() + timedelta(days=days)
    return datetime.combine(d, time(hour), tzinfo=TZ)

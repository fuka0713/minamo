"""推薦（recommendations テーブル）の読み書きと、推薦から自動のリマインドを入れること。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.item import list_reminders
from app.models import Item, Recommendation, Reminder
from app.services.timeutil import to_utc

# 自動で入れるリマインドに優先して使う「一番の理由」（締切や期間に間に合うことを優先する）
PRIORITY = ["deadline", "period_end", "release_date", "period_start"]


def replace_for_item(db: Session, item: Item, recs: list[dict], source: str, store: dict | None) -> list[Recommendation]:
    """商品の推薦を作り直す（前の「提案中」は replaced にする）。"""
    for old in db.scalars(select(Recommendation).where(Recommendation.item_id == item.id, Recommendation.status == "suggested")):
        old.status = "replaced"
    rows = [
        Recommendation(item_id=item.id, recommend_at=to_utc(r["remindAt"]), reason=r["reason"], basis=r["basis"], source=source,
                       place_name=store["name"] if store else None, place_lat=store["lat"] if store else None,
                       place_lng=store["lng"] if store else None)
        for r in recs
    ]
    db.add_all(rows)
    db.flush()
    schedule_auto_reminder(db, item, rows)
    db.commit()
    return rows


def schedule_auto_reminder(db: Session, item: Item, rows: list[Recommendation]) -> None:
    """推薦の中から1つを、自動のリマインドとして入れ直す（ユーザーが選んだリマインドがあれば何もしない）。"""
    if item.wish_status == "not_want" or not rows:
        return
    reminders = list_reminders(db, item.id)
    if any(r.source == "user" and r.status == "scheduled" for r in reminders):
        return
    for r in reminders:
        if r.source == "auto" and r.status == "scheduled":
            r.status = "canceled"
    best = next((r for basis in PRIORITY for r in rows if r.basis == basis), rows[0])
    db.add(Reminder(item_id=item.id, remind_at=best.recommend_at, reason=best.reason, source="auto"))


def list_for_item(db: Session, item_id: int) -> list[Recommendation]:
    return list(db.scalars(select(Recommendation).where(Recommendation.item_id == item_id, Recommendation.status != "replaced")
                           .order_by(Recommendation.recommend_at)))


def list_for_user(db: Session, user_id: int, limit: int) -> list[tuple[Recommendation, Item]]:
    """ホーム用：欲しい・保留の商品ごとに、いちばん近い推薦を1つずつ（日時の早い順）。"""
    rows = db.execute(
        select(Recommendation, Item).join(Item, Item.id == Recommendation.item_id)
        .where(Item.user_id == user_id, Item.wish_status != "not_want", Recommendation.status == "suggested")
        .order_by(Recommendation.recommend_at)
    ).all()
    seen, out = set(), []
    for rec, item in rows:
        if item.id not in seen:
            seen.add(item.id)
            out.append((rec, item))
    return out[:limit]


def get_own(db: Session, user_id: int, rec_id: int) -> tuple[Recommendation, Item] | None:
    row = db.execute(select(Recommendation, Item).join(Item, Item.id == Recommendation.item_id)
                     .where(Recommendation.id == rec_id, Item.user_id == user_id)).first()
    return (row[0], row[1]) if row else None


def to_out(rec: Recommendation, item: Item | None = None) -> dict:
    out = {"id": rec.id, "itemId": rec.item_id, "recommendAt": to_utc(rec.recommend_at), "reason": rec.reason, "basis": rec.basis,
           "source": rec.source, "status": rec.status,
           "place": {"name": rec.place_name, "lat": rec.place_lat, "lng": rec.place_lng} if rec.place_name else None}
    if item is not None:
        out["item"] = {"id": item.id, "title": item.title, "genre": item.genre, "imageUrl": f"/api/items/{item.id}/image"}
    return out

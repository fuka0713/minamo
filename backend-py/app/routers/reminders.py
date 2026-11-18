"""P3 気づかせる：生活スタイル・リマインド・掲示板・通知・Web プッシュ。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import item as item_crud
from app.crud import lifestyle as lifestyle_crud
from app.database import get_db
from app.deps import current_user
from app.errors import ApiError, ErrorEnvelope, not_found
from app.models import Item, Notification, PushSubscription, Reminder
from app.schemas.lifestyle import DiagnosisInput, LifestyleOut, LifestylePatch, QuestionList
from app.schemas.reminder import (
    AnswerInput, BoardList, NotificationList, NotificationOut, PushInput, PushOut, ReminderInput, ReminderList, ReminderOut,
    SuggestionList,
)
from app.services.ids import new_id
from app.services.lifestyle import QUESTIONS, diagnose
from app.services.suggestions import board_score, preferred_hour, suggestions_for
from app.services.timeutil import as_utc, now_utc

router = APIRouter(tags=["Reminders"])
ERRORS = {400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}}


# ---------------- 生活スタイル ----------------

@router.get("/api/lifestyle/questions", response_model=QuestionList, summary="生活習慣診断の質問5問")
def questions():
    return {"questions": QUESTIONS}


@router.post("/api/lifestyle/diagnosis", response_model=LifestyleOut, summary="診断回答を保存し結果を返す", responses=ERRORS)
def save_diagnosis(body: DiagnosisInput, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    answers = [a.model_dump() for a in body.answers]
    try:
        payday, preferences = diagnose(answers)
    except ValueError as err:
        raise ApiError(400, "INVALID_ANSWER", str(err)) from err
    lifestyle = lifestyle_crud.save(db, user_id, payday=payday, preferences=preferences, answers=answers, source="diagnosed")
    return lifestyle_crud.out(lifestyle)


@router.get("/api/lifestyle", response_model=LifestyleOut, summary="生活スタイル（未回答時は暫定値、給料日25日）", responses=ERRORS)
def get_lifestyle(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    return lifestyle_crud.out(lifestyle_crud.get(db, user_id))


@router.put("/api/lifestyle", response_model=LifestyleOut, summary="診断結果の一部を更新", responses=ERRORS)
def put_lifestyle(body: LifestylePatch, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise ApiError(400, "EMPTY_PATCH", "変更する項目を1つ以上送ってください。")
    current = lifestyle_crud.out(lifestyle_crud.get(db, user_id))
    preferences = {**current["preferences"], **(changes.get("preferences") or {})}
    lifestyle = lifestyle_crud.save(db, user_id, payday=changes.get("payday") or current["payday"],
                                    preferences=preferences, answers=None, source="manual")
    return lifestyle_crud.out(lifestyle)


# ---------------- リマインド ----------------

def _own_item(db: Session, user_id: str, item_id: str) -> Item:
    item = item_crud.get_own(db, user_id, item_id)
    if item is None:
        raise not_found()
    return item


@router.get("/api/items/{id}/reminder-suggestions", response_model=SuggestionList, summary="期間・生活スタイルから理由付き候補",
            responses=ERRORS)
def reminder_suggestions(id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    item = _own_item(db, user_id, id)
    payday, preferences = lifestyle_crud.payday_and_preferences(db, user_id)
    return {"suggestions": suggestions_for(item, payday, preferences, now_utc())}


@router.post("/api/items/{id}/reminders", status_code=201, response_model=ReminderOut, summary="商品にリマインドを登録",
             responses=ERRORS)
def add_reminder(id: str, body: ReminderInput, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    item = _own_item(db, user_id, id)
    reminder = item_crud.add_reminder(db, item, as_utc(body.remindAt), body.reason or "", "user")
    return item_crud.reminder_out(reminder)


@router.get("/api/items/{id}/reminders", response_model=ReminderList, summary="商品リマインド一覧", responses=ERRORS)
def list_reminders(id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    item = _own_item(db, user_id, id)
    return {"reminders": [item_crud.reminder_out(r) for r in item_crud.list_reminders(db, item.id)]}


@router.delete("/api/reminders/{id}", status_code=204, summary="リマインド取消", responses=ERRORS)
def cancel_reminder(id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    reminder = item_crud.get_own_reminder(db, user_id, id)
    if reminder is None:
        raise not_found()
    item_crud.cancel_reminder(db, reminder)


# ---------------- 掲示板 ----------------

@router.get("/api/board", response_model=BoardList, summary="ホーム掲示板のおすすめ", responses=ERRORS)
def board(limit: int = Query(5, ge=1, le=20), user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    now = now_utc()
    items = db.scalars(select(Item).where(Item.user_id == user_id, Item.status.in_(item_crud.ACTIVE)))
    scored = sorted(((board_score(i, now), i) for i in items), key=lambda x: (x[0][0], as_utc(x[1].created_at)), reverse=True)
    out = []
    for (_, reason), item in scored[:limit]:
        release = as_utc(item.period_start_at).date() if item.period_type == "release_date" and item.period_start_at else None
        out.append({"itemId": item.id, "name": item.name, "imageUrl": f"/api/items/{item.id}/image",
                    "releaseDate": release, "reason": reason})
    return {"items": out}


# ---------------- 通知 ----------------

def _deliver_due(db: Session, user_id: str) -> None:
    """時刻が来たリマインドを、通知にする（アプリを開いて一覧を読んだときに作る）。"""
    settings = lifestyle_crud.get_settings(db, user_id)
    if not settings.push_enabled:
        return
    now = now_utc()
    due = db.scalars(select(Reminder).where(Reminder.user_id == user_id, Reminder.status == "scheduled"))
    for reminder in due:
        if as_utc(reminder.remind_at) > now:
            continue
        item = db.get(Item, reminder.item_id)
        reminder.status = "sent"
        if item is None or item.status not in item_crud.ACTIVE:
            continue
        message = f"「{item.name}」のことを思い出す時間です。{reminder.reason}".strip()
        db.add(Notification(id=new_id("ntf"), user_id=user_id, item_id=item.id, reminder_id=reminder.id, message=message))
    db.commit()


def _notification_out(n: Notification, item: Item | None = None) -> dict:
    return {"id": n.id, "itemId": n.item_id, "message": n.message, "status": n.status, "answer": n.answer,
            "createdAt": as_utc(n.created_at), "item": item_crud.to_out(item) if item else None}


@router.get("/api/notifications", response_model=NotificationList, summary="ログインユーザーへの通知一覧", responses=ERRORS)
def notifications(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    _deliver_due(db, user_id)
    rows = db.scalars(select(Notification).where(Notification.user_id == user_id)
                      .order_by(Notification.created_at.desc(), Notification.id.desc()).limit(50))
    return {"notifications": [_notification_out(n) for n in rows]}


@router.post("/api/notifications/{id}/answer", response_model=NotificationOut, summary="通知へ回答", responses=ERRORS,
             description="bought（買った）・unwanted（いらない）は商品の状態を変えて、通知の対象から外す。"
             "later（あとで）は3日後に、もう一度知らせる。")
def answer(id: str, body: AnswerInput, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    note = db.scalar(select(Notification).where(Notification.id == id, Notification.user_id == user_id))
    if note is None:
        raise not_found()
    item = item_crud.get_own(db, user_id, note.item_id)
    if item is not None:
        if body.answer == "later":
            _, preferences = lifestyle_crud.payday_and_preferences(db, user_id)
            item_crud.add_reminder(db, item, item_crud.later_time(now_utc(), preferred_hour(preferences)),
                                   "「あとで」と答えたので、もう一度お知らせします。", "later")
        else:
            item_crud.update(db, item, {"status": body.answer})
    note.status, note.answer = "answered", body.answer
    db.commit()
    return _notification_out(note, item)


@router.post("/api/push-subscriptions", status_code=201, response_model=PushOut, summary="Web Push購読先登録", responses=ERRORS,
             description="ブラウザの購読情報を保存する。実際に Web プッシュを送るには、サーバーに VAPID 鍵の設定が必要（未実装）。")
def push_subscribe(body: PushInput, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if sub is None:
        sub = PushSubscription(id=new_id("psh"), user_id=user_id, endpoint=body.endpoint, keys=body.keys.model_dump())
        db.add(sub)
    elif sub.user_id != user_id:
        raise ApiError(409, "CONFLICT", "この購読先は別のアカウントで登録されています。")
    else:
        sub.keys, sub.active = body.keys.model_dump(), True
    db.commit()
    return {"id": sub.id, "active": sub.active}

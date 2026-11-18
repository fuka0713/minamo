"""生活スタイルと設定の読み書き。"""

from sqlalchemy.orm import Session

from app.models import Lifestyle, Setting

DEFAULT_PAYDAY = 25


def get(db: Session, user_id: str) -> Lifestyle | None:
    return db.get(Lifestyle, user_id)


def out(lifestyle: Lifestyle | None) -> dict:
    """まだ診断していなければ、仮の値（給料日25日）を source=default で返す。"""
    if lifestyle is None:
        return {"payday": DEFAULT_PAYDAY, "source": "default", "preferences": {}}
    return {"payday": lifestyle.payday, "source": lifestyle.source, "preferences": lifestyle.preferences or {}}


def payday_and_preferences(db: Session, user_id: str) -> tuple[int, dict]:
    data = out(get(db, user_id))
    return data["payday"], data["preferences"]


def save(db: Session, user_id: str, *, payday: int, preferences: dict, answers: list | None, source: str) -> Lifestyle:
    lifestyle = get(db, user_id) or Lifestyle(user_id=user_id)
    lifestyle.payday, lifestyle.preferences, lifestyle.source = payday, preferences, source
    if answers is not None:
        lifestyle.answers = answers
    db.add(lifestyle)
    db.commit()
    return lifestyle


def get_settings(db: Session, user_id: str) -> Setting:
    setting = db.get(Setting, user_id)
    if setting is None:
        setting = Setting(user_id=user_id, push_enabled=True, privacy_mode=False)
        db.add(setting)
        db.commit()
    return setting

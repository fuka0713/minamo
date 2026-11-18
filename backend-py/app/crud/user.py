"""アカウント・ログイン中の印の読み書き。"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models import LoginSession, User
from app.services.ids import new_id
from app.services.security import hash_password, new_token
from app.services.timeutil import as_utc, now_utc


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create(db: Session, email: str, password: str) -> User:
    user = User(id=new_id("usr"), email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    return user


def create_guest(db: Session) -> User:
    """デモ用のゲスト。ログインには使えないメールアドレスと、使えないパスワードにする（このブラウザのクッキーだけで入る）。"""
    user_id = new_id("usr")
    user = User(id=user_id, email=f"{user_id}@guest.invalid", password_hash=hash_password(new_token()))
    db.add(user)
    db.commit()
    return user


def create_session(db: Session, user_id: str) -> str:
    token = new_token()
    db.add(LoginSession(token=token, user_id=user_id))
    db.commit()
    return token


def user_id_for_token(db: Session, token: str) -> str | None:
    login = db.get(LoginSession, token)
    if not login:
        return None
    # クッキーが残っていても、サーバー側でも30日を過ぎたログインは無効にする
    if as_utc(login.created_at) + timedelta(seconds=config.SESSION_MAX_AGE) < now_utc():
        db.delete(login)
        db.commit()
        return None
    return login.user_id


def delete_session(db: Session, token: str) -> None:
    login = db.get(LoginSession, token)
    if login:
        db.delete(login)
        db.commit()

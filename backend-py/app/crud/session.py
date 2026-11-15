"""ログイン中の印（sessions テーブル）の読み書き。"""

from sqlalchemy.orm import Session

from app.models import LoginSession


def get_user_id(db: Session, token: str) -> int | None:
    """クッキーの合言葉から、ログインしている人の ID を返す（いなければ None）。"""
    login = db.get(LoginSession, token)
    return login.user_id if login else None

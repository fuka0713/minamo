"""いろいろな API で使う共通の部品。"""

from fastapi import Depends
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.crud import user as user_crud
from app.database import get_db
from app.errors import ApiError

# Swagger の「Authorize」に、ログインのクッキー（session）として表示される
session_cookie = APIKeyCookie(name="session", auto_error=False, description="ログインすると自動で入るクッキー")


def current_user(token: str | None = Depends(session_cookie), db: Session = Depends(get_db)) -> str:
    """ログインしている人の ID。ログインしていなければ 401。"""
    user_id = user_crud.user_id_for_token(db, token) if token else None
    if user_id is None:
        raise ApiError(401, "UNAUTHORIZED", "ログインしてください。")
    return user_id

"""いろいろな API で使う共通の部品。"""

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import session as session_crud
from app.database import get_db


def current_user(session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> int:
    """クッキー「session」から、ログインしている人の ID を返す。いなければ 401。

    ログイン（クッキーの発行）は Express の backend が行っている。
    """
    user_id = session_crud.get_user_id(db, session) if session else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="ログインしてください")
    return user_id

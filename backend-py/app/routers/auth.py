"""P2 アカウント：登録・ログイン・ログアウト・ログインしている人。"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app import config
from app.crud import user as user_crud
from app.database import get_db
from app.deps import current_user, session_cookie
from app.errors import ApiError, ErrorEnvelope
from app.models import User
from app.schemas.auth import Credentials, UserOut
from app.services.security import check_password

router = APIRouter(prefix="/api/auth", tags=["Auth"])
ERRORS = {400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope}}


def _login(response: Response, db: Session, user_id: str) -> None:
    token = user_crud.create_session(db, user_id)
    # SameSite=Lax：他のサイトからの書き込み（POST など）にはクッキーが付かない（CSRF 対策）
    response.set_cookie("session", token, max_age=config.SESSION_MAX_AGE, httponly=True, samesite="lax",
                        secure=config.COOKIE_SECURE, path="/")


@router.post("/signup", status_code=201, response_model=UserOut, summary="アカウント登録とログイン", responses=ERRORS)
def signup(body: Credentials, response: Response, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if "@" not in email or len(email) > 254:
        raise ApiError(400, "INVALID_EMAIL", "メールアドレスを入れてください。")
    if len(body.password) < 8:
        raise ApiError(400, "WEAK_PASSWORD", "パスワードは8文字以上にしてください。")
    if user_crud.get_by_email(db, email):
        raise ApiError(409, "EMAIL_TAKEN", "このメールアドレスはもう登録されています。")
    user = user_crud.create(db, email, body.password)
    _login(response, db, user.id)
    return {"id": user.id, "email": user.email}


@router.post("/login", response_model=UserOut, summary="ログイン", responses=ERRORS)
def login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    user = user_crud.get_by_email(db, body.email.strip().lower())
    if user is None or not check_password(body.password, user.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "メールアドレスかパスワードが違います。")
    _login(response, db, user.id)
    return {"id": user.id, "email": user.email}


@router.post("/guest", status_code=201, response_model=UserOut, summary="ゲストで入る（デモ）", responses={403: {"model": ErrorEnvelope}},
             description="メールアドレスとパスワードなしで、このブラウザだけのアカウントを作ってログインする。"
             "ログアウトすると、同じゲストには戻れない。ALLOW_GUEST=false のときは 403。")
def guest(response: Response, db: Session = Depends(get_db)):
    if not config.ALLOW_GUEST:
        raise ApiError(403, "GUEST_DISABLED", "ゲストでは入れません。メールアドレスで登録してください。")
    user = user_crud.create_guest(db)
    _login(response, db, user.id)
    return {"id": user.id, "email": user.email}


@router.post("/logout", status_code=204, summary="ログアウト")
def logout(response: Response, token: str | None = Depends(session_cookie), db: Session = Depends(get_db)):
    if token:
        user_crud.delete_session(db, token)
    response.delete_cookie("session", path="/")


@router.get("/me", response_model=UserOut, summary="ログインユーザー", responses=ERRORS)
def me(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    return {"id": user.id, "email": user.email}

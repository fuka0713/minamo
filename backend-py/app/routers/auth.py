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


def _out(user: User) -> dict:
    return {"id": user.id, "username": user.email, "email": user.email}


@router.post("/signup", status_code=201, response_model=UserOut, summary="アカウント登録とログイン", responses=ERRORS,
             description="ユーザー名とパスワードだけで登録する（デモ用の簡単なもの）。ユーザー名は1〜50文字、パスワードは4文字以上。"
             "登録すると、そのままログインした状態になる。")
def signup(body: Credentials, response: Response, db: Session = Depends(get_db)):
    name = body.username.strip().lower()
    if not name or len(name) > 50 or any(c.isspace() for c in name):
        raise ApiError(400, "INVALID_USERNAME", "ユーザー名は、空白なしの1〜50文字にしてください。")
    if len(body.password) < 4:
        raise ApiError(400, "WEAK_PASSWORD", "パスワードは4文字以上にしてください。")
    if name == config.DEMO_USERNAME or name.endswith(".invalid") or user_crud.get_by_email(db, name):
        raise ApiError(409, "USERNAME_TAKEN", "このユーザー名はもう使われています。別の名前にしてください。")
    user = user_crud.create(db, name, body.password)
    _login(response, db, user.id)
    return _out(user)


@router.post("/login", response_model=UserOut, summary="ログイン", responses=ERRORS,
             description="ユーザー名とパスワードでログインする。デモでは「test / test」でも入れる（みんなで同じアカウントを使う）。")
def login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    name = body.username.strip().lower()
    if config.ALLOW_GUEST and name == config.DEMO_USERNAME and body.password == config.DEMO_PASSWORD:
        user = user_crud.get_by_email(db, config.DEMO_EMAIL) or user_crud.create(db, config.DEMO_EMAIL, user_crud.random_password())
        _login(response, db, user.id)
        return _out(user)
    user = user_crud.get_by_email(db, name)
    if user is None or not check_password(body.password, user.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "ユーザー名かパスワードが違います。")
    _login(response, db, user.id)
    return _out(user)


@router.post("/guest", status_code=201, response_model=UserOut, summary="ゲストで入る（デモ）", responses={403: {"model": ErrorEnvelope}},
             description="メールアドレスとパスワードなしで、このブラウザだけのアカウントを作ってログインする。"
             "ログアウトすると、同じゲストには戻れない。ALLOW_GUEST=false のときは 403。")
def guest(response: Response, db: Session = Depends(get_db)):
    if not config.ALLOW_GUEST:
        raise ApiError(403, "GUEST_DISABLED", "ゲストでは入れません。メールアドレスで登録してください。")
    user = user_crud.create_guest(db)
    _login(response, db, user.id)
    return _out(user)


@router.post("/logout", status_code=204, summary="ログアウト")
def logout(response: Response, token: str | None = Depends(session_cookie), db: Session = Depends(get_db)):
    if token:
        user_crud.delete_session(db, token)
    response.delete_cookie("session", path="/")


@router.get("/me", response_model=UserOut, summary="ログインユーザー", responses=ERRORS)
def me(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    return _out(db.get(User, user_id))

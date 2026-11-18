"""すくしょっぷ API（FastAPI）の入口。

フォルダの役割：
  models/   … データベースのテーブル（SQLAlchemy）
  schemas/  … API の入出力の形（Pydantic）
  crud/     … データベースの読み書き
  routers/  … API の URL ごとの処理（auth / items / reminders / settings）
  services/ … 解析（OCR・ルール・Gemini）・画像の保存・リマインド候補・パスワード

Swagger（説明ページ）：/api/docs
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app import config, errors
from app.database import create_tables
from app.routers import auth, items, reminders, settings
from app.services import storage

DESCRIPTION = """
スクショから「欲しい」を整理するアプリ **すくしょっぷ** の API です。

- ログインが必要な API は、`/api/auth/signup` か `/api/auth/login` を先に呼ぶと、クッキー `session` が自動で付きます
- エラーはすべて `{"error": {"code", "message", "requestId"}}` の形
- 日時は ISO 8601（UTC）。分からない値は `null`（解析で値を作り出さない）
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動したとき：データベースとストレージの準備ができるまで、2秒ずつ待ちながら試す
    for _ in range(30):
        try:
            create_tables()
            storage.create_bucket()
            break
        except Exception as err:
            print(f"データベースとストレージの起動を待っています…（{err.__class__.__name__}）")
            time.sleep(2)
    yield


app = FastAPI(
    title="すくしょっぷ API",
    version="0.2.0",
    description=DESCRIPTION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Items", "description": "P1：欲しいもの"},
        {"name": "Auth", "description": "P2：アカウント"},
        {"name": "Reminders", "description": "P3：気づかせる"},
        {"name": "Settings", "description": "P4：設定"},
    ],
    swagger_ui_parameters={"persistAuthorization": True, "displayRequestDuration": True},
)
errors.install(app)


@app.middleware("http")
async def check_origin(request: Request, call_next):
    """（任意）TRUSTED_ORIGINS を設定したときだけ、書き込み系の API の Origin を確かめる（CSRF 対策の追加）。"""
    if config.TRUSTED_ORIGINS and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        if origin and origin not in config.TRUSTED_ORIGINS:
            from fastapi.responses import JSONResponse
            rid = getattr(request.state, "request_id", "req_unknown")
            return JSONResponse(status_code=403, content={"error": {"code": "FORBIDDEN", "message": "許可されていない送信元です。", "requestId": rid}})
    return await call_next(request)


app.include_router(items.router)
app.include_router(auth.router)
app.include_router(reminders.router)
app.include_router(settings.router)


@app.get("/api/health", summary="動作確認", tags=["Settings"])
def health():
    return {"ok": True}

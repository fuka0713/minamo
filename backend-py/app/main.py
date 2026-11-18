"""FastAPI の API サーバーの入口。

フォルダの役割：
  models/   … データベースのテーブル（SQLAlchemy）
  schemas/  … API の入出力の形（Pydantic）
  crud/     … データベースの読み書き
  routers/  … API の URL ごとの処理
  services/ … OCR・画像の保存・解析のルール

説明ページ：/api/docs
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_tables
from app.routers import recommendations, screenshots, timing
from app.services import storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動したとき：データベースとストレージの準備ができるまで、2秒ずつ待ちながら試す
    for _ in range(30):
        try:
            create_tables()
            storage.create_bucket()
            break
        except Exception:
            print("データベースとストレージの起動を待っています…")
            time.sleep(2)
    yield


app = FastAPI(
    title="minamo API（FastAPI）",
    description="スクショ欲しいものリマインドアプリの API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.include_router(screenshots.router)  # 解析 API
app.include_router(timing.router)  # 解析 API：リマインドと場所
app.include_router(recommendations.router)  # 推薦 API


@app.get("/api/py/health", summary="動作確認", tags=["その他"])
def health():
    return {"ok": True}

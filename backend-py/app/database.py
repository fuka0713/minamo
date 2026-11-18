"""データベース（PostgreSQL）への接続。"""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _url() -> str:
    # 「postgresql://...」を、SQLAlchemy で psycopg を使う形「postgresql+psycopg://...」にする
    url = os.environ.get("DATABASE_URL", "sqlite://")
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


engine = create_engine(_url())
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """すべてのテーブル（models）の親。"""


def get_db():
    """API の処理ごとに、データベースとの接続を1つ渡して、終わったら閉じる。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# すでにあるテーブルに、あとから足した列を追加する（なければ足す）。
# Express の backend と同じテーブルを使っているので、両方の列をここでそろえる。
MIGRATIONS = [
    "ALTER TABLE items ALTER COLUMN title DROP NOT NULL",
    "ALTER TABLE items ALTER COLUMN genre DROP NOT NULL",
    """ALTER TABLE items
         ADD COLUMN IF NOT EXISTS user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
         ADD COLUMN IF NOT EXISTS description     TEXT,
         ADD COLUMN IF NOT EXISTS price_visible   BOOLEAN NOT NULL DEFAULT FALSE,
         ADD COLUMN IF NOT EXISTS wish_status     TEXT    NOT NULL DEFAULT 'want',
         ADD COLUMN IF NOT EXISTS place_category  TEXT,
         ADD COLUMN IF NOT EXISTS place_name      TEXT,
         ADD COLUMN IF NOT EXISTS place_visible   BOOLEAN NOT NULL DEFAULT FALSE,
         ADD COLUMN IF NOT EXISTS analysis_status TEXT    NOT NULL DEFAULT 'pending',
         ADD COLUMN IF NOT EXISTS analyzed_at     TIMESTAMPTZ,
         ADD COLUMN IF NOT EXISTS edited_fields   JSON    NOT NULL DEFAULT '[]',
         ADD COLUMN IF NOT EXISTS period_start    DATE,
         ADD COLUMN IF NOT EXISTS period_end      DATE,
         ADD COLUMN IF NOT EXISTS deadline        DATE,
         ADD COLUMN IF NOT EXISTS release_date    DATE,
         ADD COLUMN IF NOT EXISTS period_source   TEXT    NOT NULL DEFAULT 'auto'""",
    # 場所と結びつける（feat/analysis-api）
    """ALTER TABLE items
         ADD COLUMN IF NOT EXISTS place_lat         DOUBLE PRECISION,
         ADD COLUMN IF NOT EXISTS place_lng         DOUBLE PRECISION,
         ADD COLUMN IF NOT EXISTS place_radius_m    INTEGER NOT NULL DEFAULT 200,
         ADD COLUMN IF NOT EXISTS place_notified_at TIMESTAMPTZ""",
    # リマインドが「自動」か「ユーザーが選んだ」か
    "ALTER TABLE reminders ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'auto'",
]


def create_tables() -> None:
    """テーブルがなければ作り、足りない列を足す。"""
    from app import models  # noqa: F401  （テーブルの定義を読み込むため）

    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            for sql in MIGRATIONS:
                conn.execute(text(sql))

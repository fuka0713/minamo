"""データベース（PostgreSQL）への接続。"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app import config


def _url() -> str:
    # 「postgresql://...」を、SQLAlchemy で psycopg を使う形にする
    return config.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)


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


def create_tables() -> None:
    """テーブルがなければ作る。"""
    from app import models  # noqa: F401  （テーブルの定義を読み込むため）

    Base.metadata.create_all(engine)
    # あとから足した列（すでにあるテーブルに足す）
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE items ADD COLUMN IF NOT EXISTS limited_kind TEXT"))

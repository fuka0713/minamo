"""テストの共通の準備。

データベースはテスト用の SQLite（メモリの中）。ストレージ・OCR は「にせもの」に差し替え、Gemini は使わない。
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config, main
from app.database import Base, get_db
from app.services import ocr, storage

OCR_TEXT = "ちいかわ×〇〇カフェ 限定アクスタ\nコラボグッズ 受注締切 12/5\n開催期間 11/1〜11/30\n¥1,650"


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    def test_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    images = {}
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(storage, "create_bucket", lambda: None)
    monkeypatch.setattr(storage, "save_image", lambda key, data, ctype: images.update({key: (data, ctype)}))
    monkeypatch.setattr(storage, "load_image", lambda key: images[key])
    monkeypatch.setattr(storage, "delete_image", lambda key: images.pop(key))
    monkeypatch.setattr(ocr, "read_text", lambda image: OCR_TEXT)
    monkeypatch.setattr(main, "create_tables", lambda: None)
    main.app.dependency_overrides[get_db] = test_db

    with TestClient(main.app) as c:
        c.images = images
        c.db = TestSession
        yield c
    main.app.dependency_overrides.clear()


def signup(client, email="a@example.com", password="password1") -> dict:
    res = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    return res.json()


def upload(client, name="a.png", ctype="image/png", data=b"fake-image") -> dict:
    res = client.post("/api/items", files={"image": (name, data, ctype)})
    assert res.status_code == 201, res.text
    return res.json()

"""登録 API と解析 API のテスト。

データベースはテスト用の SQLite（メモリの中）、ストレージと OCR は「にせもの」に差し替える。
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db
from app.models import LoginSession, User
from app.services import ocr, storage

OCR_TEXT = "限定アクスタ\nちいかわ×〇〇カフェ\n開催期間 11/1〜11/30\n¥1,650"


@pytest.fixture
def client(monkeypatch):
    # テスト用のデータベース
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    def test_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    # ユーザー2人と、それぞれのログイン中の印
    with TestSession() as db:
        db.add_all([User(id=1, email="a@example.com", password_hash="x"), User(id=2, email="b@example.com", password_hash="x")])
        db.add_all([LoginSession(token="token-a", user_id=1), LoginSession(token="token-b", user_id=2)])
        db.commit()

    # ストレージと OCR のにせもの
    images = {}
    monkeypatch.setattr(storage, "create_bucket", lambda: None)
    monkeypatch.setattr(storage, "save_image", lambda key, data, ctype: images.update({key: data}))
    monkeypatch.setattr(storage, "load_image", lambda key: images[key])
    monkeypatch.setattr(ocr, "read_text", lambda image: OCR_TEXT)
    monkeypatch.setattr(main, "create_tables", lambda: None)
    main.app.dependency_overrides[get_db] = test_db

    with TestClient(main.app) as c:
        c.images = images
        yield c
    main.app.dependency_overrides.clear()


def register(client, token="token-a"):
    client.cookies.set("session", token)
    return client.post("/api/screenshots", files=[("files", ("a.png", b"fake-png", "image/png"))])


def test_登録すると登録した日と画像だけが入る(client):
    res = register(client)
    assert res.status_code == 201
    item = res.json()[0]
    assert item["createdAt"] is not None
    assert item["imageUrl"] == f"/api/items/{item['id']}/image"
    assert item["analysis"]["status"] == "pending"
    assert item["title"] is None
    assert item["genre"] is None
    assert item["price"] == {"value": None, "visible": False}
    assert item["wishStatus"] == "want"
    assert list(client.images)[0].startswith("users/1/")  # ユーザーごとのフォルダ


def test_解析すると埋められる項目が埋まる(client):
    item_id = register(client).json()[0]["id"]
    res = client.post(f"/api/screenshots/{item_id}/analyze")
    assert res.status_code == 200
    item = res.json()
    assert item["analysis"]["status"] == "done"
    assert item["title"] == "限定アクスタ"
    assert item["description"].startswith("キャラクター・グッズ｜")
    assert item["genre"] == "goods"
    assert item["price"] == {"value": 1650, "visible": False}  # 価格は読み取るが、表示はしない
    assert item["place"]["category"] == "キャラクターショップ・コラボ会場"
    assert item["place"]["visible"] is False


def test_ユーザーが直した項目は再解析で上書きしない(client):
    from app.models import Item

    item_id = register(client).json()[0]["id"]
    db = next(main.app.dependency_overrides[get_db]())
    item = db.get(Item, item_id)
    item.title, item.edited_fields = "自分でつけた名前", ["title"]
    db.commit()

    assert client.post(f"/api/screenshots/{item_id}/analyze").json()["title"] == "自分でつけた名前"
    assert client.post(f"/api/screenshots/{item_id}/analyze?force=true").json()["title"] == "限定アクスタ"


def test_読み取りに失敗したらfailedになり_やり直せる(client, monkeypatch):
    item_id = register(client).json()[0]["id"]

    def broken(image):
        raise ocr.OcrError("だめでした")

    monkeypatch.setattr(ocr, "read_text", broken)
    assert client.post(f"/api/screenshots/{item_id}/analyze").json()["analysis"]["status"] == "failed"

    monkeypatch.setattr(ocr, "read_text", lambda image: OCR_TEXT)
    assert client.post(f"/api/screenshots/{item_id}/analyze").json()["analysis"]["status"] == "done"


def test_他の人のスクショは解析できない(client):
    item_id = register(client, "token-a").json()[0]["id"]
    client.cookies.set("session", "token-b")
    assert client.post(f"/api/screenshots/{item_id}/analyze").status_code == 404


def test_画像でないファイルは断る(client):
    client.cookies.set("session", "token-a")
    res = client.post("/api/screenshots", files=[("files", ("a.txt", b"hello", "text/plain"))])
    assert res.status_code == 400


def test_ログインしていなければ401(client):
    client.cookies.clear()
    assert client.post("/api/screenshots", files=[("files", ("a.png", b"x", "image/png"))]).status_code == 401

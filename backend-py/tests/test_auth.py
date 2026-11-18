"""P2 アカウント。"""

from tests.conftest import signup


def test_登録するとログインした状態になる(client):
    user = signup(client, "New@Example.com")
    assert user["email"] == "new@example.com" and user["username"] == "new@example.com"
    assert user["id"].startswith("usr_")
    assert client.get("/api/auth/me").json() == user


def test_登録のエラーは決まった形で返る(client):
    res = client.post("/api/auth/signup", json={"username": "a b", "password": "password1"})
    assert res.status_code == 400
    body = res.json()["error"]
    assert body["code"] == "INVALID_USERNAME"
    assert body["requestId"].startswith("req_")
    assert client.post("/api/auth/signup", json={"username": "yuka", "password": "abc"}).json()["error"]["code"] == "WEAK_PASSWORD"
    signup(client)
    assert client.post("/api/auth/signup", json={"email": "a@example.com", "password": "password1"}).status_code == 409
    assert client.post("/api/auth/signup", json={"username": "test", "password": "test1"}).json()["error"]["code"] == "USERNAME_TAKEN"


def test_ユーザー名とパスワードだけで登録できる(client):
    user = client.post("/api/auth/signup", json={"username": "Yuka", "password": "pass"}).json()
    assert user["username"] == "yuka"
    client.post("/api/auth/logout")
    client.cookies.clear()
    assert client.post("/api/auth/login", json={"username": "yuka", "password": "pass"}).status_code == 200


def test_ログインとログアウト(client):
    signup(client)
    client.post("/api/auth/logout")
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "nope-nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "A@example.com", "password": "password1"}).status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_ログインしていなければ401(client):
    res = client.get("/api/items")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_30日を過ぎたログインは無効(client):
    from datetime import UTC, datetime, timedelta

    from app.models import LoginSession

    signup(client)
    with client.db() as db:
        for s in db.query(LoginSession).all():
            s.created_at = datetime.now(UTC) - timedelta(days=31)
        db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_ゲストで入れる(client, monkeypatch):
    from app import config

    res = client.post("/api/auth/guest")
    assert res.status_code == 201 and res.json()["email"].endswith("@guest.invalid")
    assert client.get("/api/auth/me").json() == res.json()
    client.cookies.clear()
    monkeypatch.setattr(config, "ALLOW_GUEST", False)
    assert client.post("/api/auth/guest").json()["error"]["code"] == "GUEST_DISABLED"


def test_デモはtestとtestで入れる(client, monkeypatch):
    from app import config

    first = client.post("/api/auth/login", json={"email": "test", "password": "test"})
    assert first.status_code == 200 and first.json()["email"] == "test@demo.invalid"
    client.cookies.clear()
    again = client.post("/api/auth/login", json={"email": "TEST", "password": "test"}).json()
    assert again["id"] == first.json()["id"]  # 同じアカウント
    assert client.post("/api/auth/login", json={"email": "test", "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "test@demo.invalid", "password": "test"}).status_code == 401
    client.cookies.clear()
    monkeypatch.setattr(config, "ALLOW_GUEST", False)
    assert client.post("/api/auth/login", json={"email": "test", "password": "test"}).status_code == 401

"""P1 欲しいもの。"""

from tests.conftest import signup, upload


def test_スクショを登録すると解析して候補が返る(client):
    signup(client)
    item = upload(client)
    assert item["id"].startswith("itm_")
    assert item["name"] == "ちいかわ×〇〇カフェ 限定アクスタ"
    assert item["price"] == 1650 and item["currency"] == "JPY"
    assert item["brand"] is None and item["shop"] is None  # 書いていないものは作らない
    assert item["identification"] == "unidentified"
    assert 0 <= item["confidence"] <= 0.6
    assert item["status"] == "wanted"
    assert item["period"]["type"] == "event_period"
    assert item["remindAt"] is not None and item["remindAt"].endswith("Z")
    assert item["reminderReason"]
    assert item["imageUrl"] == f"/api/items/{item['id']}/image"


def test_画像の形式と大きさ(client):
    signup(client)
    assert client.post("/api/items", files={"image": ("a.gif", b"x", "image/gif")}).status_code == 415
    big = b"x" * (10 * 1024 * 1024 + 1)
    assert client.post("/api/items", files={"image": ("a.png", big, "image/png")}).status_code == 413


def test_一覧の絞り込みとページ送り(client):
    signup(client)
    for _ in range(3):
        upload(client)
    page = client.get("/api/items?limit=2").json()
    assert len(page["items"]) == 2 and page["nextCursor"] == "2"
    rest = client.get(f"/api/items?limit=2&cursor={page['nextCursor']}").json()
    assert len(rest["items"]) == 1 and rest["nextCursor"] is None
    assert len(client.get("/api/items?keyword=アクスタ").json()["items"]) == 3
    assert len(client.get("/api/items?keyword=ラーメン").json()["items"]) == 0
    assert len(client.get("/api/items?status=bought").json()["items"]) == 0


def test_自分のものしか見えない(client):
    signup(client, "a@example.com")
    item = upload(client)
    client.cookies.clear()
    signup(client, "b@example.com")
    assert client.get("/api/items").json()["items"] == []
    for method, url in [("get", f"/api/items/{item['id']}"), ("get", f"/api/items/{item['id']}/image"),
                        ("delete", f"/api/items/{item['id']}")]:
        assert getattr(client, method)(url).status_code == 404
    assert client.patch(f"/api/items/{item['id']}", json={"name": "x"}).status_code == 404


def test_送った項目だけ更新し_決まり以外は400(client):
    signup(client)
    item = upload(client)
    res = client.patch(f"/api/items/{item['id']}", json={"name": "ミニショルダーバッグ", "price": 3980, "brand": None,
                                                           "genre": "ファッション", "repeat": "weekly"})
    updated = res.json()
    assert res.status_code == 200
    assert (updated["name"], updated["price"], updated["genre"], updated["repeat"]) == ("ミニショルダーバッグ", 3980, "ファッション", "weekly")
    assert updated["memo"] == item["memo"]  # 送っていない項目はそのまま
    assert client.patch(f"/api/items/{item['id']}", json={"color": "red"}).status_code == 400
    assert client.patch(f"/api/items/{item['id']}", json={"genre": "ラーメン"}).json()["error"]["code"] == "INVALID_GENRE"
    assert client.patch(f"/api/items/{item['id']}", json={"url": "javascript:alert(1)"}).status_code == 400
    assert client.patch(f"/api/items/{item['id']}", json={}).status_code == 400
    period = client.patch(f"/api/items/{item['id']}", json={"period": {"type": "release_date", "startAt": "2026-12-20T00:00:00Z"}}).json()
    assert period["period"] == {"type": "release_date", "startAt": "2026-12-20T00:00:00Z", "endAt": None}
    assert client.patch(f"/api/items/{item['id']}", json={"period": None}).json()["period"] is None


def test_買ったにすると予定のリマインドが消える(client):
    signup(client)
    item = upload(client)
    done = client.patch(f"/api/items/{item['id']}", json={"status": "bought"}).json()
    assert done["status"] == "bought" and done["remindAt"] is None
    reminders = client.get(f"/api/items/{item['id']}/reminders").json()["reminders"]
    assert all(r["status"] == "cancelled" for r in reminders)


def test_削除すると画像も消える(client):
    signup(client)
    item = upload(client)
    assert client.get(f"/api/items/{item['id']}/image").content == b"fake-image"
    assert client.delete(f"/api/items/{item['id']}").status_code == 204
    assert client.images == {}
    assert client.get(f"/api/items/{item['id']}").status_code == 404


def test_ジャンル一覧(client):
    assert client.get("/api/genres").json()["genres"][0] == "コスメ"


def test_期間限定の終わりと種類を返す(client):
    signup(client)
    item = upload(client)  # 「コラボグッズ 受注締切 12/5」「開催期間 11/1〜11/30」
    assert item["limitedKind"] == "collab"
    assert item["limitedUntil"].endswith("T14:59:59Z")  # 日本時間 11/30 23:59:59
    assert item["limitedUntil"].startswith(item["period"]["endAt"][:4])
    changed = client.patch(f"/api/items/{item['id']}", json={"limitedKind": "sale", "period": None}).json()
    assert changed["limitedKind"] == "sale" and changed["limitedUntil"] is None
    assert client.patch(f"/api/items/{item['id']}", json={"limitedKind": "なぞ"}).status_code == 400


def test_短い間にたくさん送ると429(client, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "UPLOAD_LIMIT_PER_10MIN", 2)
    signup(client)
    upload(client)
    upload(client)
    res = client.post("/api/items", files={"image": ("a.png", b"x", "image/png")})
    assert res.status_code == 429 and res.json()["error"]["code"] == "TOO_MANY_UPLOADS"

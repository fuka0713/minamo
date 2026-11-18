"""「いつ・どこで思い出す」API のテスト（データベース・ストレージ・OCR は test_screenshots.py のにせものを使う）。"""

from datetime import UTC, datetime, timedelta

from app.services import ocr, places
from tests.test_screenshots import client, register  # noqa: F401  （fixture を使い回す）

SHINJUKU = {"lat": 35.6909, "lng": 139.7003}


def analyzed(client, token="token-a"):  # noqa: F811
    item_id = register(client, token).json()[0]["id"]
    return client.post(f"/api/screenshots/{item_id}/analyze").json()


def test_解析すると期間を読み取り_リマインドが1つ自動で入る(client):  # noqa: F811
    item = analyzed(client)
    assert item["period"]["start"].endswith("-11-01") and item["period"]["end"].endswith("-11-30")
    scheduled = [r for r in item["reminders"] if r["status"] == "scheduled"]
    assert len(scheduled) == 1 and scheduled[0]["source"] == "auto"
    assert scheduled[0]["reason"]


def test_再解析しても自動のリマインドは1つだけ(client):  # noqa: F811
    item = analyzed(client)
    again = client.post(f"/api/screenshots/{item['id']}/analyze").json()
    assert sum(r["status"] == "scheduled" for r in again["reminders"]) <= 1


def test_候補を見て_選んだ日時でリマインドを入れる(client):  # noqa: F811
    item = analyzed(client)
    suggestions = client.get(f"/api/screenshots/{item['id']}/reminder-suggestions").json()["suggestions"]
    assert 1 <= len(suggestions) <= 3 and all(s["reason"] for s in suggestions)

    at = (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0)
    res = client.post(f"/api/screenshots/{item['id']}/reminders", json={"remindAt": at.isoformat(), "reason": "週末に見る"})
    assert res.status_code == 201 and res.json()["source"] == "user"

    # ユーザーが選んだあとは、自動のリマインドは取り消され、再解析しても入らない
    again = client.post(f"/api/screenshots/{item['id']}/analyze").json()
    scheduled = [r for r in again["reminders"] if r["status"] == "scheduled"]
    assert [r["source"] for r in scheduled] == ["user"]


def test_リマインドの日時がおかしければ400(client):  # noqa: F811
    item = analyzed(client)
    url = f"/api/screenshots/{item['id']}/reminders"
    assert client.post(url, json={"remindAt": "2020-01-01T20:00:00+09:00"}).status_code == 400  # 過去
    assert client.post(url, json={"remindAt": "2030-01-01T20:00:00"}).status_code == 400  # タイムゾーンなし


def test_場所を登録し_その近くを通ったら知らせる(client):  # noqa: F811
    item = analyzed(client)
    res = client.put(f"/api/screenshots/{item['id']}/place", json={"name": "IKEA 新宿", **SHINJUKU, "radiusM": 300})
    assert res.status_code == 200
    assert res.json()["place"]["lat"] == SHINJUKU["lat"] and res.json()["place"]["radiusM"] == 300

    far = client.post("/api/screenshots/nearby", json={"lat": 35.6812, "lng": 139.7671}).json()  # 東京駅（約6km）
    assert far["matches"] == []
    near = client.post("/api/screenshots/nearby", json={"lat": 35.6915, "lng": 139.7008}).json()  # 約80m
    assert len(near["matches"]) == 1
    m = near["matches"][0]
    assert m["itemId"] == item["id"] and m["placeName"] == "IKEA 新宿" and m["distanceM"] < 300 and m["reason"]
    # 24時間は、同じ商品をもう一度知らせない
    assert client.post("/api/screenshots/nearby", json={"lat": 35.6915, "lng": 139.7008}).json()["matches"] == []


def test_お店の種類だけなら_近くにそのお店があるか地図で調べる(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(ocr, "read_text", lambda image: "ウォータリーティント リップ\n¥1,650")
    item = analyzed(client)
    assert item["place"]["category"] == "ドラッグストア"
    asked = {}

    def fake_find(lat, lng, tags, names):
        asked.update(tags=tags, names=names)
        return [{"name": "サンプル薬局", "lat": lat + 0.001, "lng": lng, "tags": {"shop": "chemist", "name": "サンプル薬局"}}]

    monkeypatch.setattr(places, "find_shops", fake_find)
    m = client.post("/api/screenshots/nearby", json=SHINJUKU).json()["matches"]
    assert ("shop", "chemist") in asked["tags"]
    assert len(m) == 1 and m[0]["placeName"] == "サンプル薬局" and 100 < m[0]["distanceM"] < 120


def test_いらないものは場所で知らせない(client):  # noqa: F811
    from app.database import get_db
    from app.main import app
    from app.models import Item

    item = analyzed(client)
    client.put(f"/api/screenshots/{item['id']}/place", json=SHINJUKU)
    db = next(app.dependency_overrides[get_db]())
    db.get(Item, item["id"]).wish_status = "not_want"
    db.commit()
    assert client.post("/api/screenshots/nearby", json=SHINJUKU).json()["matches"] == []


def test_場所は自分のものだけ_緯度経度は両方そろえる(client):  # noqa: F811
    item = analyzed(client, "token-a")
    assert client.put(f"/api/screenshots/{item['id']}/place", json={"lat": 35.0}).status_code == 400
    client.cookies.set("session", "token-b")
    assert client.put(f"/api/screenshots/{item['id']}/place", json=SHINJUKU).status_code == 404
    assert client.get(f"/api/screenshots/{item['id']}/reminder-suggestions").status_code == 404
    client.cookies.clear()
    assert client.post("/api/screenshots/nearby", json=SHINJUKU).status_code == 401


def test_地図の問い合わせは丸めた位置だけ送る(monkeypatch):
    sent = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"elements": [{"lat": 35.691, "lon": 139.7, "tags": {"name": "IKEA 新宿", "shop": "furniture"}}]}

    def fake_post(url, data, timeout, headers):
        sent["q"] = data["data"]
        return FakeResponse()

    monkeypatch.setattr(places, "POI_PROVIDER", "overpass")
    monkeypatch.setattr(places.httpx, "post", fake_post)
    shops = places.find_shops(35.690912, 139.700345, set(), {"IKEA"})
    assert "35.691,139.7" in sent["q"] and "35.690912" not in sent["q"]
    assert shops[0]["name"] == "IKEA 新宿"
    assert places.find_shops(35.0, 139.0, set(), set()) == []

"""解析 API（リマインド・場所）と推薦 API のテスト（DB・ストレージ・OCR は test_screenshots.py のにせものを使う）。"""

from datetime import UTC, datetime, timedelta

import pytest

from app.services import llm, ocr, places
from tests.test_screenshots import client, register  # noqa: F401  （fixture を使い回す）

SHINJUKU = {"lat": 35.6909, "lng": 139.7003}


@pytest.fixture(autouse=True)
def no_ai(monkeypatch):
    """ふだんは AI を使わない（ルールで推薦する）。ダミーのお店を使う。"""
    for k in ("GEMINI_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(places, "POI_PROVIDER", "dummy")


def analyzed(client, token="token-a"):  # noqa: F811
    item_id = register(client, token).json()[0]["id"]
    return client.post(f"/api/screenshots/{item_id}/analyze").json()


def test_解析だけでは推薦もリマインドも作らない(client):  # noqa: F811
    item = analyzed(client)
    assert item["analysis"]["analyzer"] == "rules"
    assert item["period"]["start"].endswith("-11-01") and item["period"]["end"].endswith("-11-30")
    assert item["reminders"] == []


def test_推薦を作ると_理由つきで最大3つ_1つが自動でリマインドになる(client):  # noqa: F811
    item = analyzed(client)
    recs = client.post(f"/api/recommendations/items/{item['id']}").json()["recommendations"]
    assert 1 <= len(recs) <= 3 and all(r["reason"] and r["source"] == "rules" for r in recs)
    assert recs == sorted(recs, key=lambda r: r["recommendAt"])
    detail = client.post(f"/api/screenshots/{item['id']}/analyze").json()  # 解析し直しても推薦は消えない
    scheduled = [r for r in detail["reminders"] if r["status"] == "scheduled"]
    assert len(scheduled) == 1 and scheduled[0]["source"] == "auto"
    assert client.get(f"/api/recommendations/items/{item['id']}").json()["recommendations"] == recs


def test_お店の場所を推薦理由に使う_ダミーのお店(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(ocr, "read_text", lambda image: "北欧風ソファ\nIKEA 限定カラー\n¥39,900")
    item = analyzed(client)
    assert item["place"]["name"] == "IKEA"
    recs = client.post(f"/api/recommendations/items/{item['id']}", json=SHINJUKU).json()["recommendations"]
    assert all(r["place"]["name"] == "IKEA 新宿" for r in recs)
    assert any("IKEA 新宿（新宿）で買えます" in r["reason"] for r in recs)


def test_推薦を作り直すと前の提案は消え_自動リマインドは1つのまま(client):  # noqa: F811
    item = analyzed(client)
    client.post(f"/api/recommendations/items/{item['id']}")
    again = client.post(f"/api/recommendations/items/{item['id']}").json()["recommendations"]
    assert client.get(f"/api/recommendations/items/{item['id']}").json()["recommendations"] == again
    detail = client.post(f"/api/screenshots/{item['id']}/analyze").json()
    assert sum(r["status"] == "scheduled" for r in detail["reminders"]) == 1


def test_推薦をリマインドにすると_自動のものは取り消す(client):  # noqa: F811
    item = analyzed(client)
    recs = client.post(f"/api/recommendations/items/{item['id']}").json()["recommendations"]
    res = client.post(f"/api/recommendations/{recs[-1]['id']}/accept")
    assert res.status_code == 201 and res.json()["source"] == "user" and res.json()["reason"] == recs[-1]["reason"]
    detail = client.post(f"/api/screenshots/{item['id']}/analyze").json()
    assert [r["source"] for r in detail["reminders"] if r["status"] == "scheduled"] == ["user"]
    # 自分で選んだあとは、推薦を作り直しても自動のリマインドは入らない
    client.post(f"/api/recommendations/items/{item['id']}")
    detail = client.post(f"/api/screenshots/{item['id']}/analyze").json()
    assert [r["source"] for r in detail["reminders"] if r["status"] == "scheduled"] == ["user"]


def test_ホームの推薦は商品ごとに1つ_いらないものは出さない(client):  # noqa: F811
    from app.database import get_db
    from app.main import app
    from app.models import Item

    a, b = analyzed(client), analyzed(client)
    for it in (a, b):
        client.post(f"/api/recommendations/items/{it['id']}")
    home = client.get("/api/recommendations").json()["recommendations"]
    assert sorted(r["itemId"] for r in home) == sorted([a["id"], b["id"]]) and home[0]["item"]["imageUrl"]
    db = next(app.dependency_overrides[get_db]())
    db.get(Item, b["id"]).wish_status = "not_want"
    db.commit()
    assert [r["itemId"] for r in client.get("/api/recommendations").json()["recommendations"]] == [a["id"]]


def test_自分でリマインドを入れる_日時がおかしければ400(client):  # noqa: F811
    item = analyzed(client)
    url = f"/api/screenshots/{item['id']}/reminders"
    at = (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0)
    assert client.post(url, json={"remindAt": at.isoformat(), "reason": "週末に見る"}).json()["source"] == "user"
    assert client.post(url, json={"remindAt": "2020-01-01T20:00:00+09:00"}).status_code == 400
    assert client.post(url, json={"remindAt": "2030-01-01T20:00:00"}).status_code == 400


def test_登録した場所の近くを通ったら知らせる(client):  # noqa: F811
    item = analyzed(client)
    res = client.put(f"/api/screenshots/{item['id']}/place", json={"name": "コラボカフェ", **SHINJUKU, "radiusM": 300})
    assert res.status_code == 200 and res.json()["place"]["radiusM"] == 300
    assert client.post("/api/recommendations/nearby", json={"lat": 35.6812, "lng": 139.7671}).json()["matches"] == []  # 東京駅
    m = client.post("/api/recommendations/nearby", json={"lat": 35.6915, "lng": 139.7008}).json()["matches"]
    assert len(m) == 1 and m[0]["placeName"] == "コラボカフェ" and m[0]["distanceM"] < 300 and m[0]["source"] == "rules"
    assert client.post("/api/recommendations/nearby", json={"lat": 35.6915, "lng": 139.7008}).json()["matches"] == []  # 24時間は1回


def test_近くのダミーのお店で知らせ_AIが理由の文を考える(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(ocr, "read_text", lambda image: "ウォータリーティント リップ\n¥1,650")
    item = analyzed(client)
    assert item["place"]["category"] == "ドラッグストア"
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai.nearby_reasons", lambda matches: {matches[0]["itemId"]: "マツキヨまで約80m。リップを試してみる？"})
    m = client.post("/api/recommendations/nearby", json={"lat": 35.6912, "lng": 139.7019}).json()["matches"]
    assert m[0]["placeName"] == "マツモトキヨシ 新宿東口店" and m[0]["distanceM"] < 50
    assert m[0]["reason"] == "マツキヨまで約80m。リップを試してみる？" and m[0]["source"] == "groq"
    assert llm.provider() == "groq"


def test_自分のものだけ_ログインが必要(client):  # noqa: F811
    item = analyzed(client, "token-a")
    rec = client.post(f"/api/recommendations/items/{item['id']}").json()["recommendations"][0]
    assert client.put(f"/api/screenshots/{item['id']}/place", json={"lat": 35.0}).status_code == 400
    client.cookies.set("session", "token-b")
    assert client.post(f"/api/recommendations/items/{item['id']}").status_code == 404
    assert client.post(f"/api/recommendations/{rec['id']}/accept").status_code == 404
    assert client.get("/api/recommendations").json()["recommendations"] == []
    client.cookies.clear()
    assert client.post("/api/recommendations/nearby", json=SHINJUKU).status_code == 401


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

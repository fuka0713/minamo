"""P3 気づかせる・P4 設定。"""

from datetime import UTC, datetime, timedelta

from app.models import Reminder
from tests.conftest import signup, upload

ANSWERS = [
    {"questionId": "payday", "value": "10日"},
    {"questionId": "favoriteGenres", "value": "コスメ、暮らし"},
    {"questionId": "shoppingStyle", "value": "ネットで見ることが多い"},
    {"questionId": "budgetTiming", "value": "給料日のあと"},
    {"questionId": "reminderTime", "value": "朝（6〜11時）"},
]


def test_診断の質問と回答(client):
    signup(client)
    assert len(client.get("/api/lifestyle/questions").json()["questions"]) == 5
    assert client.get("/api/lifestyle").json() == {"payday": 25, "source": "default", "preferences": {}}
    result = client.post("/api/lifestyle/diagnosis", json={"answers": ANSWERS}).json()
    assert result["payday"] == 10 and result["source"] == "diagnosed"
    assert result["preferences"]["favoriteGenres"] == ["コスメ", "暮らし"]
    changed = client.put("/api/lifestyle", json={"payday": 25}).json()
    assert changed["payday"] == 25 and changed["source"] == "manual"
    assert changed["preferences"]["reminderTime"] == "朝（6〜11時）"  # 送っていない好みはそのまま


def test_診断の答えがおかしければ400(client):
    signup(client)
    assert client.post("/api/lifestyle/diagnosis", json={"answers": ANSWERS[:4]}).status_code == 400
    bad = [*ANSWERS[:4], {"questionId": "reminderTime", "value": "真夜中"}]
    assert client.post("/api/lifestyle/diagnosis", json={"answers": bad}).json()["error"]["code"] == "INVALID_ANSWER"


def test_リマインド候補と登録と取消(client):
    signup(client)
    client.post("/api/lifestyle/diagnosis", json={"answers": ANSWERS})
    item = upload(client)
    suggestions = client.get(f"/api/items/{item['id']}/reminder-suggestions").json()["suggestions"]
    assert 1 <= len(suggestions) <= 3
    assert all(s["reason"] for s in suggestions)
    assert any(s["source"] == "lifestyle" for s in suggestions)

    at = (datetime.now(UTC) + timedelta(hours=1)).replace(microsecond=0)
    created = client.post(f"/api/items/{item['id']}/reminders", json={"remindAt": at.isoformat(), "reason": "テスト"}).json()
    assert created["status"] == "scheduled"
    assert client.get(f"/api/items/{item['id']}").json()["remindAt"] == at.isoformat().replace("+00:00", "Z")
    assert client.delete(f"/api/reminders/{created['id']}").status_code == 204
    assert client.delete("/api/reminders/rmd_nothing").status_code == 404


def test_時刻が来たら通知になり_答えられる(client):
    signup(client)
    item = upload(client)
    with client.db() as db:  # 自動で入ったリマインドを、過去の時刻にする
        for r in db.query(Reminder).all():
            r.remind_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    notes = client.get("/api/notifications").json()["notifications"]
    assert len(notes) == 1 and notes[0]["status"] == "unread" and notes[0]["itemId"] == item["id"]
    assert client.get("/api/notifications").json()["notifications"] == notes  # 二重に作らない

    later = client.post(f"/api/notifications/{notes[0]['id']}/answer", json={"answer": "later"}).json()
    assert later["status"] == "answered" and later["item"]["status"] == "wanted"
    reminders = client.get(f"/api/items/{item['id']}/reminders").json()["reminders"]
    assert sum(r["status"] == "scheduled" for r in reminders) == 1  # 「あとで」の次のリマインド

    with client.db() as db:
        for r in db.query(Reminder).filter(Reminder.status == "scheduled").all():
            r.remind_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    second = client.get("/api/notifications").json()["notifications"][0]
    bought = client.post(f"/api/notifications/{second['id']}/answer", json={"answer": "bought"}).json()
    assert bought["item"]["status"] == "bought"
    assert client.post("/api/notifications/ntf_nothing/answer", json={"answer": "later"}).status_code == 404


def test_お知らせをオフにすると通知を作らない(client):
    signup(client)
    upload(client)
    assert client.put("/api/settings", json={"pushEnabled": False, "privacyMode": True}).json() == {"pushEnabled": False, "privacyMode": True}
    with client.db() as db:
        for r in db.query(Reminder).all():
            r.remind_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    assert client.get("/api/notifications").json()["notifications"] == []
    assert client.get("/api/settings").json()["privacyMode"] is True


def test_掲示板は理由つき(client):
    signup(client)
    item = upload(client)
    board = client.get("/api/board").json()["items"]
    assert board[0]["itemId"] == item["id"] and board[0]["reason"]


def test_プッシュの購読先(client):
    signup(client)
    body = {"endpoint": "https://push.example.com/abc", "keys": {"p256dh": "k", "auth": "a"}}
    res = client.post("/api/push-subscriptions", json=body)
    assert res.status_code == 201 and res.json()["active"] is True
    assert client.post("/api/push-subscriptions", json={**body, "endpoint": "http://insecure"}).status_code == 400

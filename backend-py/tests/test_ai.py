"""生成 AI（Gemini / xAI Grok）を使うところのテスト。本物の AI には送らず、答えを「にせもの」に差し替える。"""

import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx

from app.services import ai, analysis, llm, ocr

TZ = ZoneInfo("Asia/Tokyo")
TODAY = date(2026, 11, 18)
NOW = datetime(2026, 11, 18, 12, 0, tzinfo=TZ)
OCR_TEXT = "限定アクスタ\nアニメイト 受注締切 12/5\n¥1,650"


def fake_ai(monkeypatch, answer: dict, provider="gemini", sent: dict | None = None):
    """AI の答えを差し替える（送った中身は sent に入れる）。"""
    for k in ("GEMINI_API_KEY", "XAI_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY" if provider == "gemini" else "XAI_API_KEY", "test-key")
    text = json.dumps(answer, ensure_ascii=False)

    def fake_post(url, headers, json, timeout):
        if sent is not None:
            sent.update(url=url, headers=headers, body=json)
        body = ({"candidates": [{"content": {"parts": [{"text": text}]}}]} if "googleapis" in url
                else {"choices": [{"message": {"content": text}}]})
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)


def test_AIを選ぶ_既定はGemini(monkeypatch):
    for k in ("GEMINI_API_KEY", "XAI_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(k, raising=False)
    assert llm.provider() == "none"  # 鍵がなければ使わない
    monkeypatch.setenv("XAI_API_KEY", "x")
    assert llm.provider() == "xai"  # Gemini の鍵がなければ、xAI の鍵を使う
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    assert llm.provider() == "gemini"  # 両方あれば既定の Gemini
    monkeypatch.setenv("LLM_PROVIDER", "xai")
    assert llm.provider() == "xai"  # LLM_PROVIDER で選べる
    monkeypatch.delenv("XAI_API_KEY")
    assert llm.provider() == "gemini"  # 選んだ方の鍵がなければ、もう一方
    monkeypatch.setenv("LLM_PROVIDER", "なぞ")
    assert llm.provider() == "gemini"


def test_鍵がなければルールで解析する(monkeypatch):
    for k in ("GEMINI_API_KEY", "XAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(ocr, "read_text", lambda image: OCR_TEXT)
    values, text, used = analysis.analyze(b"\x89PNG...", TODAY)
    assert used == "rules" and values["place_name"] == "アニメイト"


def test_Geminiの解析_おかしな値は捨てる(monkeypatch):
    sent = {}
    fake_ai(monkeypatch, {"title": "ちいかわ 限定アクリルスタンド", "price": -5, "genre": "ラーメン", "storeName": None,
                          "periodEnd": "2026-11-30", "deadline": "12月5日"}, "gemini", sent)
    monkeypatch.setattr(ocr, "read_text", lambda image: OCR_TEXT)
    values, text, used = analysis.analyze(b"\x89PNG...", TODAY)
    assert used == "gemini"
    assert sent["headers"]["x-goog-api-key"] == "test-key" and "test-key" not in sent["url"]  # 鍵は URL に入れない
    assert sent["body"]["contents"][0]["parts"][1]["inline_data"]["mime_type"] == "image/png"
    assert values["price"] is None and values["genre"] == "other"
    assert values["place_name"] == "アニメイト"  # AI が空なら OCR の文字からおぎなう
    assert values["period_end"] == date(2026, 11, 30) and values["deadline"] is None


def test_xAIのGrokでも解析できる(monkeypatch):
    sent = {}
    fake_ai(monkeypatch, {"title": "北欧風ソファ", "genre": "interior", "price": 39900, "storeName": "IKEA"}, "xai", sent)
    monkeypatch.setattr(ocr, "read_text", lambda image: "")
    values, _, used = analysis.analyze(b"\xff\xd8...", TODAY)
    assert used == "xai" and values["price"] == 39900 and values["place_category"] == "家具・インテリアショップ"
    assert sent["url"] == "https://api.x.ai/v1/chat/completions" and sent["body"]["model"] == "grok-4"
    assert sent["headers"]["Authorization"] == "Bearer test-key"
    assert sent["body"]["response_format"] == {"type": "json_object"}
    assert sent["body"]["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_AIが失敗したらルールに戻る(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("down")))
    monkeypatch.setattr(ocr, "read_text", lambda image: OCR_TEXT)
    assert analysis.analyze(b"x", TODAY)[2] == "rules"


def test_AIの推薦日_過去や同じ日やおかしな値は捨てる(monkeypatch):
    fake_ai(monkeypatch, {"recommendations": [
        {"date": "2026-12-04", "time": "20:00", "reason": "締切の前日です。アニメイト 新宿で受け取れます。", "basis": "deadline"},
        {"date": "2026-12-04", "time": "09:00", "reason": "同じ日", "basis": "other"},
        {"date": "2026-11-01", "time": "20:00", "reason": "過去", "basis": "other"},
        {"date": "あした", "time": "20:00", "reason": "形が違う", "basis": "other"},
        {"date": "2026-11-25", "time": "03:00", "reason": "給料日です。", "basis": "なぞ"},
    ]})
    item = {"title": "限定アクスタ", "genre": "goods", "price": 1650, "deadline": date(2026, 12, 5)}
    context = {"payday": date(2026, 11, 25), "hints": [], "store": {"name": "アニメイト 新宿", "area": "新宿", "distanceM": 420}}
    recs = ai.recommend_dates(item, context, NOW)
    assert [r["basis"] for r in recs] == ["other", "deadline"]  # 早い順。決まり以外の basis は other
    assert recs[0]["remindAt"] == datetime(2026, 11, 25, 7, 0, tzinfo=TZ)  # 時刻は 7〜22時におさめる
    assert recs[1]["remindAt"] == datetime(2026, 12, 4, 20, 0, tzinfo=TZ)


def test_AIの推薦が全部だめならエラー(monkeypatch):
    fake_ai(monkeypatch, {"recommendations": [{"date": "2020-01-01", "time": "20:00", "reason": "過去", "basis": "other"}]})
    try:
        ai.recommend_dates({"title": "x"}, {"payday": date(2026, 11, 25), "hints": [], "store": None}, NOW)
    except ValueError:
        return
    raise AssertionError("ValueError になるはず")


def test_xAI用に答えの形を文にする():
    plain = llm._plain(ai.RECOMMEND_SCHEMA)
    assert plain == {"recommendations": [{"date": "STRING", "time": "STRING", "reason": "STRING", "basis": "|".join(ai.BASIS)}]}
    assert llm.sniff_type(b"RIFF\x00\x00\x00\x00WEBP") == "image/webp"

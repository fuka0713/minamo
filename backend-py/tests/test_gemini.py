"""Gemini による解析のテスト。本物の Gemini には送らず、答えを「にせもの」に差し替える。"""

import json as jsonlib
from datetime import date

import httpx

from app.services import analysis, gemini, ocr
from tests.test_screenshots import client, register  # noqa: F401  （fixture を使い回す）

TODAY = date(2026, 11, 18)
OCR_TEXT = "限定アクスタ\nアニメイト 受注締切 12/5\n¥1,650"


def fake_gemini(monkeypatch, answer: dict, sent: dict | None = None):
    """Gemini の答えを差し替える（送った中身は sent に入れる）。"""

    def fake_post(url, headers, json, timeout):
        if sent is not None:
            sent.update(url=url, headers=headers, body=json)
        text = jsonlib.dumps(answer, ensure_ascii=False)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]},
                              request=httpx.Request("POST", url))

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "post", fake_post)


def test_鍵がなければGeminiを使わない(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(ocr, "read_text", lambda image: OCR_TEXT)
    values, text, used = analysis.analyze(b"\x89PNG...", TODAY)
    assert used == "rules" and values["title"] == "限定アクスタ" and values["place_name"] == "アニメイト"


def test_Geminiの答えを使い_おかしな値は捨てる(monkeypatch):
    sent = {}
    fake_gemini(monkeypatch, {"title": "ちいかわ 限定アクリルスタンド", "description": "カフェ限定のアクスタ", "price": -5,
                              "genre": "ラーメン", "storeName": None, "periodStart": "2026-11-01", "periodEnd": "2026-11-30",
                              "deadline": "12月5日", "releaseDate": None}, sent)
    monkeypatch.setattr(ocr, "read_text", lambda image: OCR_TEXT)
    values, text, used = analysis.analyze(b"\x89PNG...", TODAY)
    assert used == "gemini"
    assert sent["headers"]["x-goog-api-key"] == "test-key" and "test-key" not in sent["url"]  # 鍵は URL に入れない
    assert sent["body"]["contents"][0]["parts"][1]["inline_data"]["mime_type"] == "image/png"
    assert values["title"] == "ちいかわ 限定アクリルスタンド"
    assert values["price"] is None  # マイナスの価格は捨てる
    assert values["genre"] == "other" and values["place_category"] is None  # 決まり以外のジャンルは「その他」
    assert values["place_name"] == "アニメイト"  # Gemini が空なら、OCR の文字からおぎなう
    assert values["period_end"] == date(2026, 11, 30) and values["deadline"] is None  # 日付の形が違うものは捨てる
    assert text == OCR_TEXT  # 読み取った文字は検索用に残す


def test_Geminiが失敗したらルールで解析する(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("down")))
    monkeypatch.setattr(ocr, "read_text", lambda image: OCR_TEXT)
    assert analysis.analyze(b"x", TODAY)[2] == "rules"


def test_OCRが使えなくてもGeminiだけで解析できる(monkeypatch):
    fake_gemini(monkeypatch, {"title": "北欧風ソファ", "genre": "interior", "price": 39900, "storeName": "IKEA"})

    def broken(image):
        raise ocr.OcrError("Tesseract が入っていません")

    monkeypatch.setattr(ocr, "read_text", broken)
    values, text, used = analysis.analyze(b"\xff\xd8...", TODAY)
    assert used == "gemini" and text == ""
    assert values["price"] == 39900 and values["place_category"] == "家具・インテリアショップ" and values["place_name"] == "IKEA"


def test_APIで解析すると_使った解析が分かる(client, monkeypatch):  # noqa: F811
    fake_gemini(monkeypatch, {"title": "限定アクスタ", "genre": "goods", "periodEnd": "2026-11-30"})
    item_id = register(client).json()[0]["id"]
    item = client.post(f"/api/screenshots/{item_id}/analyze").json()
    assert item["analysis"] == {**item["analysis"], "status": "done", "analyzer": "gemini"}
    assert item["period"]["end"] == "2026-11-30"


def test_画像の種類を判断する():
    assert gemini.sniff_type(b"\x89PNG\r\n") == "image/png"
    assert gemini.sniff_type(b"\xff\xd8\xff") == "image/jpeg"
    assert gemini.sniff_type(b"RIFF\x00\x00\x00\x00WEBP") == "image/webp"
    assert jsonlib.dumps(gemini.SCHEMA)  # Gemini に送る形が JSON にできる

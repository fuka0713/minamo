"""解析（ルール・Gemini）とリマインド候補。"""

from datetime import UTC, date, datetime

import httpx

from app import config
from app.services import analysis, analyzer, ocr
from app.services.suggestions import lifestyle_suggestion

TODAY = date(2026, 11, 14)


def test_期間を読み取る():
    assert analyzer.find_period("開催期間 11/1(金)〜11/30(土)", TODAY) == {"type": "event_period", "start": date(2026, 11, 1), "end": date(2026, 11, 30)}
    assert analyzer.find_period("12/20〜1/10", TODAY)["end"] == date(2027, 1, 10)
    assert analyzer.find_period("受注締切：12/5 23:59", TODAY) == {"type": "deadline", "start": None, "end": date(2026, 12, 5)}
    assert analyzer.find_period("2027年1月20日 発売", TODAY) == {"type": "release_date", "start": date(2027, 1, 20), "end": None}
    assert analyzer.find_period("今日は晴れ", TODAY) is None


def test_ジャンルと名前():
    assert analyzer.find_genre("ウォータリーティント リップ") == "コスメ"
    assert analyzer.find_genre("陶器のマグ キッチン") == "暮らし"
    assert analyzer.find_genre("詰め替え 洗剤") == "日用品"
    assert analyzer.find_name("«include»\nUC01\n12:34\nやわらかニットカーディガン") == "やわらかニットカーディガン"


def test_文字がなくても仮の名前で返す():
    result = analyzer.analyze_text("", TODAY)
    assert result["name"] == analyzer.FALLBACK_NAME
    assert result["price"] is None and result["currency"] is None
    assert result["genre"] == "その他"


def test_Geminiの結果を使い_おかしな値は捨てる(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    payload = {"name": "キャンバストート", "brand": "SAMPLE", "genre": "ファッション", "price": 3900, "currency": "JPY",
               "shop": None, "url": "javascript:alert(1)", "memo": "軽くてたっぷり入る", "identification": "identified",
               "confidence": 1.7, "period": {"type": "release_date", "start": "2026-12-01", "end": None}}

    def fake_post(url, headers, json, timeout):
        assert headers["x-goog-api-key"] == "test-key"
        import json as j
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": j.dumps(payload)}]}}]},
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    result = analysis.analyze(b"img", "image/png", datetime(2026, 11, 14, tzinfo=UTC))
    assert result["analyzer"] == "gemini" and result["identification"] == "identified"
    assert result["url"] is None  # http / https 以外は捨てる
    assert result["confidence"] == 1.0
    assert result["period"] == {"type": "release_date", "start": date(2026, 12, 1), "end": None}


def test_Geminiが失敗したらルールの解析に戻る(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("down")))
    monkeypatch.setattr(ocr, "read_text", lambda image: "新作ティント リップ\n¥1,650")
    result = analysis.analyze(b"img", "image/png", datetime(2026, 11, 14, tzinfo=UTC))
    assert result["analyzer"] == "rules" and result["genre"] == "コスメ"


def test_生活スタイルから候補日を作る():
    now = datetime(2026, 11, 14, 3, 0, tzinfo=UTC)  # 日本時間 11/14 12:00
    at, reason = lifestyle_suggestion(10, {"budgetTiming": "給料日のあと", "reminderTime": "朝（6〜11時）"}, now)
    assert at.isoformat() == "2026-12-12T09:00:00+09:00"  # 次の給料日 12/10 の2日後、朝9時
    assert "給料日" in reason
    at, _ = lifestyle_suggestion(25, {}, now)
    assert at.date() == date(2026, 11, 21) and at.hour == 20  # 決まっていなければ1週間後の夜


def test_期限の種類を読み取る():
    assert analyzer.find_limited_kind("ちいかわ×カフェ コラボ") == "collab"
    assert analyzer.find_limited_kind("BLACK FRIDAY SALE 30%OFF") == "sale"
    assert analyzer.find_limited_kind("期間限定 11/30まで") == "limited"
    assert analyzer.find_limited_kind("やわらかニット") is None

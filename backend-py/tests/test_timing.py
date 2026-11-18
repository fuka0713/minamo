"""期間の読み取り（services/period.py）と、リマインドのタイミングの推測（services/timing.py）のテスト。"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.services.analyzer import analyze, find_place_name
from app.services.period import find_period
from app.services.timing import next_payday, suggest

TZ = ZoneInfo("Asia/Tokyo")
TODAY = date(2026, 11, 18)  # 水曜日
NOW = datetime(2026, 11, 18, 12, 0, tzinfo=TZ)


def test_期間を読み取る():
    p = find_period("開催期間 11/1(金)〜11/30(土)\n受注締切 12/5 23:59", TODAY)
    assert p == {"period_start": date(2026, 11, 1), "period_end": date(2026, 11, 30), "deadline": date(2026, 12, 5), "release_date": None}
    assert find_period("12/20〜1/10", TODAY)["period_end"] == date(2027, 1, 10)  # 年をまたぐ
    assert find_period("2027年1月20日 発売", TODAY)["release_date"] == date(2027, 1, 20)
    assert find_period("1/15 発売", TODAY)["release_date"] == date(2027, 1, 15)  # だいぶ前なら来年
    assert find_period("11/30まで", TODAY)["period_end"] == date(2026, 11, 30)
    assert find_period("今日は晴れ", TODAY) == {"period_start": None, "period_end": None, "deadline": None, "release_date": None}


def test_お店の名前を読み取る():
    assert find_place_name("IKEA 新宿 限定ソファ") == "IKEA"
    assert find_place_name("マツキヨ限定 リップ") == "マツキヨ"
    assert find_place_name("ユーザーGUIDE") is None  # 「GU」は単語のときだけ
    assert find_place_name("GU の新作ニット") == "GU"
    assert analyze("限定アクスタ\nアニメイト 受注締切 12/5", TODAY)["place_name"] == "アニメイト"


def test_給料日は土日なら直前の金曜():
    assert next_payday(TODAY) == date(2026, 11, 25)  # 水曜
    assert next_payday(date(2026, 11, 26)) == date(2026, 12, 25)  # 金曜
    assert next_payday(date(2027, 3, 1)) == date(2027, 3, 25)
    assert next_payday(date(2026, 12, 26)) == date(2027, 1, 25)  # 月曜
    assert next_payday(date(2027, 4, 1)) == date(2027, 4, 23)  # 4/25 は日曜 → 23日（金）


def test_期間があれば_終わる3日前や締切の前日を候補にする():
    values = {"title": "限定アクスタ", "genre": "goods", "period_start": None, "period_end": date(2026, 11, 30),
              "deadline": date(2026, 12, 5), "release_date": None}
    s = suggest(values, NOW)
    assert [x["source"] for x in s] == ["payday", "period_end", "deadline"]  # 早い順
    assert s[1]["remindAt"] == datetime(2026, 11, 27, 20, 0, tzinfo=TZ)
    assert "終わる3日前" in s[1]["reason"] and "限定アクスタ" in s[1]["reason"]
    assert s[2]["remindAt"] == datetime(2026, 12, 4, 20, 0, tzinfo=TZ)


def test_過去の日は候補にしない():
    values = {"title": "x", "genre": "other", "period_start": date(2026, 11, 1), "period_end": None,
              "deadline": None, "release_date": None}
    assert [x["source"] for x in suggest(values, NOW)] == ["payday"]


def test_手がかりがなければ給料日と1週間後():
    values = {"title": "ニット", "genre": "fashion", "period_start": None, "period_end": None, "deadline": None, "release_date": None}
    s = suggest(values, NOW)
    assert [x["source"] for x in s] == ["payday"]  # 1週間後（11/25）と給料日が同じ日なので、1つにまとめる
    s = suggest(values, datetime(2026, 11, 26, 12, 0, tzinfo=TZ))
    assert [x["source"] for x in s] == ["week_later", "payday"]  # 12/3 と 12/25


def test_飲食店は週末のお昼前():
    values = {"title": "ラーメン屋", "genre": "food", "period_start": None, "period_end": None, "deadline": None, "release_date": None}
    s = suggest(values, NOW)
    assert s[0]["source"] == "weekend" and s[0]["remindAt"] == datetime(2026, 11, 21, 11, 0, tzinfo=TZ)

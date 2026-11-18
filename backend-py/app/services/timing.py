"""解析の結果から、リマインドするタイミング（いつ思い出させるか）を推測する。

材料と考え方（早い順に並べ、過去の日時は入れない。最大3つ）：
  1. 開催期間 … 終わる3日前（行くか決める）／始まる日
  2. 締切     … 締切の前日（申し込むなら今のうち）
  3. 発売日   … 発売日の当日
  4. ジャンル … 飲食店は次の土曜のお昼前（行ける日に）
  5. 給料日   … 次の給料日（仮で毎月25日。土日なら直前の金曜）
  6. どれもなければ … 1週間後（気持ちを見直す）
"""

import os
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo(os.environ.get("APP_TIMEZONE", "Asia/Tokyo"))
REMIND_HOUR = 20  # 知らせる時刻（夜8時）。生活スタイルの診断ができたら、人ごとに変える
DEFAULT_PAYDAY = 25  # 給料日（仮）。設定ができたら、人ごとに変える


def _at(d: date, hour: int = REMIND_HOUR) -> datetime:
    return datetime.combine(d, time(hour), tzinfo=TZ)


def next_payday(today: date, day: int = DEFAULT_PAYDAY) -> date:
    """今日より後の給料日。土日なら直前の金曜にする（祝日はまだ見ていない）。"""
    year, month = today.year, today.month
    for _ in range(3):
        last = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day
        d = date(year, month, min(day, last))
        while d.weekday() >= 5:  # 5=土, 6=日
            d -= timedelta(days=1)
        if d > today:
            return d
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return d


def suggest(values: dict, now: datetime, payday: int = DEFAULT_PAYDAY) -> list[dict]:
    """リマインドの候補を [{"remindAt", "reason", "source"}] で返す。

    values は解析の結果（period_start・period_end・deadline・release_date・genre・title）。
    """
    today = now.astimezone(TZ).date()
    name = values.get("title") or "保存したもの"
    found: list[tuple[datetime, str, str]] = []

    start, end = values.get("period_start"), values.get("period_end")
    if end:
        found.append((_at(end - timedelta(days=3)), f"「{name}」の期間が終わる3日前です。行くか・買うかを決めるのにちょうどいい日です。", "period_end"))
    if start:
        found.append((_at(start, 10), f"「{name}」が始まる日です。", "period_start"))
    if d := values.get("deadline"):
        found.append((_at(d - timedelta(days=1)), f"「{name}」の締切の前日です。申し込むなら今のうちです。", "deadline"))
    if d := values.get("release_date"):
        found.append((_at(d, 10), f"「{name}」の発売日です。", "release_date"))
    if values.get("genre") == "food":
        saturday = today + timedelta(days=(5 - today.weekday()) % 7 or 7)
        found.append((_at(saturday, 11), f"週末です。「{name}」に行けるか考えてみませんか？", "weekend"))

    found = [f for f in found if f[0] > now]  # 過去の日時は使わない
    pay = next_payday(today, payday)
    found.append((_at(pay), f"給料日（{pay.month}/{pay.day}）です。「{name}」を買うか決めませんか？", "payday"))
    if len(found) == 1 and not any(values.get(k) for k in ("period_start", "period_end", "deadline", "release_date")):
        found.append((_at(today + timedelta(days=7)), f"1週間たちました。「{name}」は今も欲しいですか？", "week_later"))

    out, days = [], set()
    for at, reason, source in sorted(found, key=lambda f: f[0]):
        if at.date() in days:  # 同じ日に2つは入れない（先に入れた方を残す）
            continue
        days.add(at.date())
        out.append({"remindAt": at, "reason": reason, "source": source})
    return out[:3]

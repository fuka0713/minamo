"""リマインドの候補日と、ホームの掲示板のおすすめを作る。

候補日の材料：
  - 商品の期間（開催期間の終わり3日前・始まる日、締切の前日、発売日）
  - 生活スタイル（給料日・考える時期・通知の時間帯）
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app import config
from app.services.timeutil import as_utc

TZ = ZoneInfo(config.APP_TIMEZONE)


def local_now(now: datetime) -> datetime:
    return now.astimezone(TZ)


def preferred_hour(preferences: dict) -> int:
    """通知の時間帯（朝・昼・夜）から、知らせる時刻を決める。"""
    value = str(preferences.get("reminderTime", "夜"))
    return 9 if value.startswith("朝") else 14 if value.startswith("昼") else 20


def _at(d: date, hour: int) -> datetime:
    return datetime(d.year, d.month, d.day, hour, tzinfo=TZ)


def _next_day_of_month(day: int, today: date) -> date:
    """今日より後の「毎月 day 日」（その月に day 日がなければ月末）。"""
    year, month = today.year, today.month
    for _ in range(2):
        last = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day
        candidate = date(year, month, min(day, last))
        if candidate > today:
            return candidate
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return candidate


def lifestyle_suggestion(payday: int, preferences: dict, now: datetime) -> tuple[datetime, str]:
    """生活スタイルから、1つ候補を作る（画面のモックと同じ考え方）。"""
    today = local_now(now).date()
    timing = str(preferences.get("budgetTiming", ""))
    if "給料日のあと" in timing:
        d = _next_day_of_month(payday, today) + timedelta(days=2)
        reason = f"給料日（{payday}日）のあとに、少し落ち着いて考えられる日にしました。"
    elif "真ん中" in timing:
        d = _next_day_of_month(15, today)
        reason = "月の真ん中ごろに、もう一度見直せる日にしました。"
    elif "月末" in timing:
        d = _next_day_of_month(28, today)
        reason = "月末ごろに、今も欲しいか確認できる日にしました。"
    else:
        d = today + timedelta(days=7)
        reason = "1週間ほど時間をおいて、気持ちを見直せる日にしました。"
    genres = preferences.get("favoriteGenres") or []
    if genres:
        reason += f" よく見るジャンルは「{genres[0]}」ですね。"
    return _at(d, preferred_hour(preferences)), reason


def suggestions_for(item, payday: int, preferences: dict, now: datetime) -> list[dict]:
    """商品のリマインド候補日を、理由つきで最大3つ返す（早い順。過去の日は入れない）。"""
    hour = preferred_hour(preferences)
    out: list[dict] = []
    start = as_utc(item.period_start_at).astimezone(TZ).date() if item.period_start_at else None
    end = as_utc(item.period_end_at).astimezone(TZ).date() if item.period_end_at else None

    if item.period_type == "event_period":
        if end:
            out.append((_at(end - timedelta(days=3), hour), "終わる3日前です。行くか・買うかを決めるのにちょうどいい日です。", "period_end"))
        if start:
            out.append((_at(start, hour), "始まる日です。", "period_start"))
    elif item.period_type == "deadline" and end:
        out.append((_at(end - timedelta(days=1), hour), "締切の前日です。申し込むなら今のうちです。", "deadline"))
    elif item.period_type == "release_date" and start:
        out.append((_at(start, hour), "発売日です。", "release_date"))

    at, reason = lifestyle_suggestion(payday, preferences, now)
    out.append((at, reason, "lifestyle"))

    result, seen = [], set()
    for at, reason, source in sorted(out, key=lambda x: x[0]):
        if at <= now or at.date() in seen:
            continue
        seen.add(at.date())
        result.append({"date": at.date(), "reason": reason, "source": source, "remindAt": at})
    return result[:3]


def board_score(item, now: datetime) -> tuple[float, str]:
    """掲示板に出すための点数と、おすすめの理由。"""
    today = local_now(now).date()
    score, reasons = 0.0, []
    end = as_utc(item.period_end_at).astimezone(TZ).date() if item.period_end_at else None
    start = as_utc(item.period_start_at).astimezone(TZ).date() if item.period_start_at else None
    if end and 0 <= (end - today).days <= 7:
        score += 3
        reasons.append(f"あと{(end - today).days}日で終わります")
    if item.period_type == "release_date" and start and 0 <= (start - today).days <= 7:
        score += 2
        reasons.append("もうすぐ発売です" if start > today else "今日が発売日です")
    if item.remind_at and as_utc(item.remind_at) <= now:
        score += 2
        reasons.append("見直すタイミングが来ています")
    if item.status == "wanted":
        score += 1
    if not reasons:
        reasons.append("最近「欲しい」と思ったものです")
    return score, "。".join(reasons) + "。"

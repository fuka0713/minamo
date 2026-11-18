"""読み取った文字から、期間（開催期間・締切・発売日）を取り出す。

例：「開催期間 11/1(金)〜11/30(土)」「受注締切 12/5 23:59」「2027年1月20日 発売」
年が書いていなければ今年とみなし、だいぶ前（60日より前）なら来年とみなす。
"""

import re
import unicodedata
from datetime import date, timedelta

# 日付1つ分：「2026/11/1」または「11/1」。後ろに曜日「(金)」や時刻「23:59」が付いてもよい
DATE = r"(?:(\d{4})/)?(\d{1,2})/(\d{1,2})(?:\s*[(（][^)）]{1,3}[)）])?(?:\s*\d{1,2}:\d{2})?"
DEADLINE_WORDS = r"(?:締切|締め切り|〆切|受付終了|受注終了|予約締切)"
RELEASE_WORDS = r"(?:発売日|発売|公開日|公開|配信開始|入荷)"


def _unify(text: str) -> str:
    """「2026年11月1日」「11月1日」「2026.11.1」を「2026/11/1」「11/1」の形にそろえる。"""
    t = unicodedata.normalize("NFKC", text)
    t = re.sub(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?", r"\1/\2/\3", t)
    t = re.sub(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日?", r"\1/\2", t)
    return re.sub(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", r"\1/\2/\3", t)


def _make_date(year: str | None, month: str, day: str, today: date) -> date | None:
    try:
        d = date(int(year) if year else today.year, int(month), int(day))
    except ValueError:
        return None
    if not year and today - d > timedelta(days=60):
        d = d.replace(year=d.year + 1)
    return d


def find_period(text: str, today: date | None = None) -> dict:
    """{"period_start", "period_end", "deadline", "release_date"} を返す（見つからない項目は None）。"""
    today = today or date.today()
    t = _unify(text)
    out = {"period_start": None, "period_end": None, "deadline": None, "release_date": None}

    # 開催期間「11/1〜11/30」「11/1〜30日」
    m = re.search(rf"{DATE}\s*(?:〜|~|-|–|—|から)\s*(?:{DATE}|(\d{{1,2}})日?)", t)
    if m:
        y1, m1, d1, y2, m2, d2, day_only = m.groups()
        start = _make_date(y1, m1, d1, today)
        if start and m2:
            end_year = y2 or str(start.year + 1 if int(m2) < int(m1) else start.year)
            out["period_end"] = _make_date(end_year, m2, d2, today)
        elif start and day_only:
            out["period_end"] = _make_date(str(start.year), m1, day_only, today)
        out["period_start"] = start
    elif m := re.search(rf"{DATE}\s*まで", t):  # 「11/30まで」
        out["period_end"] = _make_date(*m.groups()[:3], today)

    # 締切「受注締切 12/5」「12/5 締切」
    m = re.search(rf"{DEADLINE_WORDS}[:：\s]*{DATE}", t) or re.search(rf"{DATE}\s*{DEADLINE_WORDS}", t)
    if m:
        out["deadline"] = _make_date(*m.groups()[:3], today)

    # 発売日「12/20 発売」「発売日：2027/1/20」
    m = re.search(rf"{RELEASE_WORDS}[:：\s]*{DATE}", t) or re.search(rf"{DATE}\s*{RELEASE_WORDS}", t)
    if m:
        out["release_date"] = _make_date(*m.groups()[:3], today)
    return out

"""OCR で読み取った文字から、商品の項目を取り出す（AI を使わない、ルールだけの解析）。

決まり：価格・ブランド・ショップ・URL は、文字に書いてあるときだけ入れる。作り出さない。
ルールでは商品を「特定」できないので、identification は常に unidentified。
"""

import re
import unicodedata
from datetime import date, datetime, timedelta

from app.services.genres import DEFAULT_GENRE, GENRES

FALLBACK_NAME = "スクショのアイテム（要確認）"


def normalize(text: str) -> str:
    """全角の英数字（１２３、ＡＢＣ）を半角にそろえる。"""
    return unicodedata.normalize("NFKC", text)


def find_price(text: str) -> float | None:
    """価格：「¥3,980」「3,980円」を探す。"""
    m = re.search(r"[¥￥]\s*([0-9][0-9,]*)|([0-9][0-9,]*)\s*円", normalize(text))
    if not m:
        return None
    value = float((m.group(1) or m.group(2)).replace(",", ""))
    return value if 0 < value < 1_000_000_000 else None


def find_url(text: str) -> str | None:
    m = re.search(r"https?://[^\s\"'<>]+", normalize(text))
    return m.group(0) if m else None


def _is_noise(line: str) -> bool:
    """時刻・電池の％・価格だけ・URL・記号だけ・「UC01」のような短い英数字だけ、などの行。"""
    if len(line) < 2:
        return True
    if re.fullmatch(r"[0-9:%\s]+", line):
        return True
    if re.search(r"https?://", line):
        return True
    if find_price(line) is not None and len(line) < 15:
        return True
    if re.fullmatch(r"[A-Za-z0-9«»<>|_\-\s]{1,6}", line):
        return True
    if re.fullmatch(r"(«|<<)\s*[A-Za-z]+\s*(»|>>)", line):  # 図の「«include»」のような記号
        return True
    return not re.search(r"[^\W\d_]", line)


def _good_lines(text: str) -> list[str]:
    return [line.strip() for line in normalize(text).splitlines() if not _is_noise(line.strip())]


def find_name(text: str) -> str | None:
    lines = _good_lines(text)
    return lines[0][:100] if lines else None


def find_genre(text: str) -> str:
    t = normalize(text)
    best, best_count = DEFAULT_GENRE, 0
    for name, words in GENRES:
        count = sum(1 for word in words if word in t)
        if count > best_count:
            best, best_count = name, count
    return best


def make_memo(text: str) -> str:
    """説明：商品名の次の行を2つほどつなぐ（120文字まで）。"""
    return " ".join(_good_lines(text)[1:3])[:120]


# ---------------- 期間 ----------------
# 日付1つ分：「2026/11/1」または「11/1」。後ろに曜日「(金)」や時刻「23:59」が付いてもよい
DATE = r"(?:(\d{4})/)?(\d{1,2})/(\d{1,2})(?:\s*[(（][^)）]{1,3}[)）])?(?:\s*\d{1,2}:\d{2})?"


def _unify_dates(text: str) -> str:
    t = normalize(text)
    t = re.sub(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?", r"\1/\2/\3", t)
    t = re.sub(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日?", r"\1/\2", t)
    return re.sub(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", r"\1/\2/\3", t)


def _make_date(year: str | None, month: str, day: str, today: date) -> date | None:
    try:
        d = date(int(year) if year else today.year, int(month), int(day))
    except ValueError:
        return None
    if not year and today - d > timedelta(days=60):  # だいぶ前なら来年のこと
        d = d.replace(year=d.year + 1)
    return d


def find_period(text: str, today: date | None = None) -> dict | None:
    """期間を {"type", "start", "end"}（日付）で返す。見つからなければ None。

    開催期間 > 締切 > 発売日 の順に、見つかったものを使う。
    """
    today = today or date.today()
    t = _unify_dates(text)

    m = re.search(rf"{DATE}\s*(?:〜|~|-|–|—|から)\s*(?:{DATE}|(\d{{1,2}})日?)", t)
    if m:
        y1, m1, d1, y2, m2, d2, day_only = m.groups()
        start = _make_date(y1, m1, d1, today)
        end = None
        if start and m2:
            end_year = y2 or str(start.year + 1 if int(m2) < int(m1) else start.year)
            end = _make_date(end_year, m2, d2, today)
        elif start and day_only:
            end = _make_date(str(start.year), m1, day_only, today)
        if start:
            return {"type": "event_period", "start": start, "end": end}

    words = r"(?:締切|締め切り|〆切|受付終了|受注終了)"
    m = re.search(rf"{words}[:：\s]*{DATE}", t) or re.search(rf"{DATE}\s*{words}", t)
    if m and (d := _make_date(*m.groups()[:3], today)):
        return {"type": "deadline", "start": None, "end": d}

    words = r"(?:発売日|発売|公開日|公開|配信開始)"
    m = re.search(rf"{words}[:：\s]*{DATE}", t) or re.search(rf"{DATE}\s*{words}", t)
    if m and (d := _make_date(*m.groups()[:3], today)):
        return {"type": "release_date", "start": d, "end": None}

    m = re.search(rf"{DATE}\s*まで", t)
    if m and (d := _make_date(*m.groups()[:3], today)):
        return {"type": "event_period", "start": None, "end": d}
    return None


def find_limited_kind(text: str) -> str | None:
    """期限の種類：「コラボ」→ collab、「SALE」「セール」「％OFF」→ sale、「期間限定」「限定」「締切」「まで」→ limited。"""
    t = normalize(text)
    if re.search(r"コラボ|collab", t, re.IGNORECASE):
        return "collab"
    if re.search(r"SALE|セール|\d+\s*%\s*OFF|割引", t, re.IGNORECASE):
        return "sale"
    if re.search(r"期間限定|限定|締切|締め切り|受注|まで", t):
        return "limited"
    return None


def analyze_text(text: str, today: date | None = None) -> dict:
    """読み取った文字から、商品の項目をまとめて返す。"""
    name = find_name(text)
    price = find_price(text)
    genre = find_genre(text)
    # 確かさ：ルールでは特定できないので、手がかりの数で 0.1〜0.6 の間にする
    confidence = 0.1 + 0.2 * (name is not None) + 0.15 * (price is not None) + 0.15 * (genre != DEFAULT_GENRE)
    return {
        "name": name or FALLBACK_NAME,
        "brand": None,
        "genre": genre,
        "price": price,
        "currency": "JPY" if price is not None else None,
        "shop": None,
        "url": find_url(text),
        "memo": make_memo(text),
        "period": find_period(text, today),
        "identification": "unidentified",
        "confidence": round(min(confidence, 0.6), 2),
        "limited_kind": find_limited_kind(text),
    }


def to_datetime(d: date | None, hour: int, tz) -> datetime | None:
    """日付を、そのタイムゾーンの決まった時刻の日時にする。"""
    return datetime(d.year, d.month, d.day, hour, tzinfo=tz) if d else None

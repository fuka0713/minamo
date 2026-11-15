"""OCR で読み取った文字から、商品データの項目を埋める（AI は使わず、ルールだけの簡単なしくみ）。

埋める項目：商品名・説明文・価格・ジャンル・場所（お店の種類）
"""

import re
import unicodedata

from app.services.genres import GENRES, genre_label, place_for


def normalize(text: str) -> str:
    """全角の英数字（１２３、ＡＢＣ）を半角にそろえる。"""
    return unicodedata.normalize("NFKC", text)


def find_price(text: str) -> int | None:
    """価格：「¥3,980」や「3,980円」を探して数字にする。"""
    m = re.search(r"[¥￥]\s*([0-9,]+)|([0-9,]+)\s*円", normalize(text))
    if not m:
        return None
    digits = (m.group(1) or m.group(2)).replace(",", "")
    return int(digits) if digits and int(digits) > 0 else None


def _is_noise(line: str) -> bool:
    """時刻・電池の％・価格だけの行・URL など、商品名に向かない行。"""
    if len(line) < 2:
        return True
    if re.fullmatch(r"[0-9:%\s]+", line):  # 「12:34」「80%」など
        return True
    if re.search(r"https?://", line):
        return True
    if find_price(line) is not None and len(line) < 15:  # 価格だけの行
        return True
    return not re.search(r"[^\W\d_]", line)  # 文字（ひらがな・漢字・英字）がない


def _good_lines(text: str) -> list[str]:
    return [line.strip() for line in normalize(text).splitlines() if not _is_noise(line.strip())]


def find_title(text: str) -> str | None:
    """商品名：上から見て、最初の「ちゃんとした文字の行」を使う（正確でなくてよい）。"""
    lines = _good_lines(text)
    return lines[0][:40] if lines else None


def find_genre(text: str) -> str:
    """ジャンル：キーワードが一番多く見つかったジャンルにする（なければ「その他」）。"""
    t = normalize(text)
    best, best_count = "other", 0
    for genre in GENRES:
        count = sum(1 for word in genre["keywords"] if word in t)
        if count > best_count:
            best, best_count = genre["id"], count
    return best


def make_description(text: str, genre: str) -> str | None:
    """説明文：商品名の次の行を2つほどつないで、ジャンル名を前につける（60文字まで）。"""
    body = " ".join(_good_lines(text)[1:3])
    return f"{genre_label(genre)}｜{body}"[:60] if body else None


def analyze(text: str) -> dict:
    """読み取った文字から、埋められる項目を全部まとめて返す（埋められない項目は None）。"""
    genre = find_genre(text)
    return {
        "title": find_title(text),
        "description": make_description(text, genre),
        "price": find_price(text),
        "genre": genre,
        "place_category": place_for(genre),
        "place_name": None,  # 具体的なお店は、AI を入れたら推定する（今は空）
    }

"""Gemini による画像の解析（任意）。サーバーの環境変数 GEMINI_API_KEY を入れたときだけ使う。

- 鍵はサーバーの .env だけに置き、画面（ブラウザ）には絶対に返さない
- 返ってきた JSON は形を確かめてから使う。失敗したら呼び出し元が OCR とルールの解析に戻す
- 価格・お店の名前・期間は、画像に書いてあるときだけ。作り出さないように指示する
"""

import base64
import json
import os
from datetime import date

import httpx

from app.services.genres import GENRES

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GENRE_IDS = [g["id"] for g in GENRES]
GENRE_GUIDE = "、".join(f'{g["id"]}={g["label"]}' for g in GENRES)

PROMPT = f"""あなたは買い物メモの整理を手伝います。スクリーンショットに写っている「欲しいもの」を1つ読み取り、JSON で答えてください。
- title：商品名（40文字以内）。分からなければ null
- description：どんなものかを日本語で1文（60文字以内）
- price：画像に書いてある価格（円・整数）。書いていなければ null（推測しない）
- genre：次の id のどれか → {GENRE_GUIDE}
- storeName：画像に書いてあるお店・ブランドの店舗名（例：IKEA、マツキヨ、アニメイト）。書いていなければ null
- periodStart / periodEnd：開催期間・販売期間の始まりと終わり、deadline：締切、releaseDate：発売日
  日付は YYYY-MM-DD。年が書いていなければ、今日（{{today}}）から見て近い未来の年にする。書いていなければ null"""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING", "nullable": True},
        "description": {"type": "STRING", "nullable": True},
        "price": {"type": "INTEGER", "nullable": True},
        "genre": {"type": "STRING", "enum": GENRE_IDS},
        "storeName": {"type": "STRING", "nullable": True},
        "periodStart": {"type": "STRING", "nullable": True},
        "periodEnd": {"type": "STRING", "nullable": True},
        "deadline": {"type": "STRING", "nullable": True},
        "releaseDate": {"type": "STRING", "nullable": True},
    },
    "required": ["genre"],
}


def api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "")


def enabled() -> bool:
    """鍵が入っていれば Gemini を使う。"""
    return bool(api_key())


def sniff_type(image: bytes) -> str:
    """画像の先頭のバイトから、種類（MIME タイプ）を判断する。"""
    if image.startswith(b"\x89PNG"):
        return "image/png"
    if image.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if image[:4] == b"RIFF" and image[8:12] == b"WEBP":
        return "image/webp"
    if image[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "image/jpeg"


def _date(value) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


def _text(value, limit: int) -> str | None:
    return value.strip()[:limit] or None if isinstance(value, str) else None


def analyze_image(image: bytes, today: date) -> dict:
    """画像を Gemini に送り、商品の項目を返す（analyzer.analyze と同じ形）。うまくいかなければ例外を投げる。"""
    body = {
        "contents": [{"parts": [
            {"text": PROMPT.replace("{today}", today.isoformat())},
            {"inline_data": {"mime_type": sniff_type(image), "data": base64.b64encode(image).decode()}},
        ]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "temperature": 0.1},
    }
    res = httpx.post(
        ENDPOINT.format(model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")),
        headers={"x-goog-api-key": api_key()},  # 鍵は URL ではなくヘッダーで送る（ログに残りにくい）
        json=body,
        timeout=30,
    )
    res.raise_for_status()
    data = json.loads(res.json()["candidates"][0]["content"]["parts"][0]["text"])
    if not isinstance(data, dict):
        raise ValueError("Gemini の答えの形が違います")

    price = data.get("price")
    return {
        "title": _text(data.get("title"), 40),
        "description": _text(data.get("description"), 60),
        "price": price if isinstance(price, int) and not isinstance(price, bool) and price > 0 else None,
        "genre": data["genre"] if data.get("genre") in GENRE_IDS else "other",
        "place_name": _text(data.get("storeName"), 100),
        "period_start": _date(data.get("periodStart")),
        "period_end": _date(data.get("periodEnd")),
        "deadline": _date(data.get("deadline")),
        "release_date": _date(data.get("releaseDate")),
    }

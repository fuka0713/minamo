"""Gemini による画像の解析（任意）。GEMINI_API_KEY を入れたときだけ使う。

- 鍵はサーバーの環境変数だけに置き、ブラウザには絶対に返さない
- 返ってきた JSON は形を確かめてから使う。失敗したら呼び出し元がルールの解析に戻す
- 価格・ブランド・ショップ・URL は、画像に書いてあるときだけ。作り出さないように指示する
"""

import base64
import json
from datetime import date

import httpx

from app import config
from app.services.genres import DEFAULT_GENRE, GENRE_NAMES

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = f"""あなたは買い物メモの整理を手伝います。スクリーンショットに写っている「欲しい商品」を1つ読み取り、JSON で答えてください。
- 画像に書かれていない価格・ブランド・ショップ・URL は必ず null にする（推測しない）
- genre は次のどれか：{"、".join(GENRE_NAMES)}
- 商品を特定できたときだけ identification を identified にする
- 期間（発売日・開催期間・締切）が書いてあれば period に入れる。日付は YYYY-MM-DD。今日は {{today}}
- memo には、商品の特徴を日本語で1文（60文字以内）"""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "name": {"type": "STRING"},
        "brand": {"type": "STRING", "nullable": True},
        "genre": {"type": "STRING", "enum": GENRE_NAMES},
        "price": {"type": "NUMBER", "nullable": True},
        "currency": {"type": "STRING", "nullable": True},
        "shop": {"type": "STRING", "nullable": True},
        "url": {"type": "STRING", "nullable": True},
        "memo": {"type": "STRING"},
        "identification": {"type": "STRING", "enum": ["identified", "unidentified"]},
        "confidence": {"type": "NUMBER"},
        "period": {
            "type": "OBJECT",
            "nullable": True,
            "properties": {
                "type": {"type": "STRING", "enum": ["release_date", "event_period", "deadline", "other"]},
                "start": {"type": "STRING", "nullable": True},
                "end": {"type": "STRING", "nullable": True},
            },
        },
    },
    "required": ["name", "genre", "identification", "confidence", "memo"],
}


def enabled() -> bool:
    return bool(config.GEMINI_API_KEY)


def _date(value) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


def analyze_image(image: bytes, content_type: str, today: date) -> dict:
    """画像を Gemini に送り、商品の項目を返す。うまくいかなければ例外を投げる。"""
    body = {
        "contents": [{"parts": [
            {"text": PROMPT.replace("{today}", today.isoformat())},
            {"inline_data": {"mime_type": content_type, "data": base64.b64encode(image).decode()}},
        ]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "temperature": 0.1},
    }
    res = httpx.post(
        ENDPOINT.format(model=config.GEMINI_MODEL),
        headers={"x-goog-api-key": config.GEMINI_API_KEY},
        json=body,
        timeout=30,
    )
    res.raise_for_status()
    data = json.loads(res.json()["candidates"][0]["content"]["parts"][0]["text"])

    url = data.get("url")
    period = data.get("period") or None
    if period:
        period = {"type": period.get("type", "other"), "start": _date(period.get("start")), "end": _date(period.get("end"))}
        if not period["start"] and not period["end"]:
            period = None
    price = data.get("price")
    return {
        "name": (data.get("name") or "").strip()[:100] or "スクショのアイテム（要確認）",
        "brand": data.get("brand") or None,
        "genre": data["genre"] if data.get("genre") in GENRE_NAMES else DEFAULT_GENRE,
        "price": float(price) if isinstance(price, int | float) and price >= 0 else None,
        "currency": (data.get("currency") or None) if price is not None else None,
        "shop": data.get("shop") or None,
        "url": url if isinstance(url, str) and url.startswith(("http://", "https://")) else None,
        "memo": (data.get("memo") or "")[:120],
        "period": period,
        "identification": "identified" if data.get("identification") == "identified" else "unidentified",
        "confidence": max(0.0, min(1.0, float(data.get("confidence") or 0))),
    }

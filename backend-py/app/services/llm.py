"""生成 AI（Gemini または Groq）を呼ぶ入口。どちらを使うかは、サーバーの .env に入っている鍵で決まる。

  GEMINI_API_KEY があれば Gemini、GROQ_API_KEY があれば Groq（両方あれば LLM_PROVIDER で選ぶ）。どちらも無ければ使わない。
  - 鍵はサーバーの .env だけに置き、画面（ブラウザ）には絶対に返さない。鍵は URL ではなくヘッダーで送る
  - 答えは JSON で返してもらい、呼び出し元で形を確かめてから使う。失敗したら呼び出し元がルールに戻す
"""

import base64
import json
import os

import httpx

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def provider() -> str:
    """使う AI：gemini / groq / none。"""
    chosen = os.environ.get("LLM_PROVIDER", "").lower()
    keys = {"gemini": os.environ.get("GEMINI_API_KEY", ""), "groq": os.environ.get("GROQ_API_KEY", "")}
    if chosen in keys:
        return chosen if keys[chosen] else "none"
    return "gemini" if keys["gemini"] else "groq" if keys["groq"] else "none"


def enabled() -> bool:
    return provider() != "none"


def sniff_type(image: bytes) -> str:
    """画像の先頭のバイトから、種類（MIME タイプ）を判断する。"""
    if image.startswith(b"\x89PNG"):
        return "image/png"
    if image[:4] == b"RIFF" and image[8:12] == b"WEBP":
        return "image/webp"
    if image[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "image/jpeg"


def generate_json(prompt: str, schema: dict, image: bytes | None = None) -> dict:
    """AI に聞いて、JSON（dict）で答えをもらう。schema は答えの形（Gemini の書き方）。うまくいかなければ例外を投げる。"""
    which = provider()
    if which == "gemini":
        return _gemini(prompt, schema, image)
    if which == "groq":
        return _groq(prompt, schema, image)
    raise RuntimeError("AI の鍵が設定されていません")


def _gemini(prompt: str, schema: dict, image: bytes | None) -> dict:
    parts: list[dict] = [{"text": prompt}]
    if image is not None:
        parts.append({"inline_data": {"mime_type": sniff_type(image), "data": base64.b64encode(image).decode()}})
    res = httpx.post(
        GEMINI_URL.format(model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")),
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        json={"contents": [{"parts": parts}],
              "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema, "temperature": 0.2}},
        timeout=30,
    )
    res.raise_for_status()
    return _as_dict(res.json()["candidates"][0]["content"]["parts"][0]["text"])


def _groq(prompt: str, schema: dict, image: bytes | None) -> dict:
    # Groq は OpenAI と同じ形の API。答えの形は、文で伝えて JSON モードで返してもらう
    text = f"{prompt}\n\n次の JSON の形だけで答えてください（説明の文は不要）：\n{json.dumps(_plain(schema), ensure_ascii=False)}"
    content: list[dict] = [{"type": "text", "text": text}]
    if image is not None:
        data_url = f"data:{sniff_type(image)};base64,{base64.b64encode(image).decode()}"
        content.append({"type": "image_url", "image_url": {"url": data_url}})
    res = httpx.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={"model": os.environ.get("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"),
              "messages": [{"role": "user", "content": content}],
              "response_format": {"type": "json_object"}, "temperature": 0.2},
        timeout=30,
    )
    res.raise_for_status()
    return _as_dict(res.json()["choices"][0]["message"]["content"])


def _plain(schema: dict):
    """Gemini 用の形の説明を、人が読める見本（例：{"title": "STRING|null"}）にする。"""
    kind = schema.get("type", "STRING")
    if kind == "OBJECT":
        return {k: _plain(v) for k, v in schema.get("properties", {}).items()}
    if kind == "ARRAY":
        return [_plain(schema.get("items", {}))]
    label = "|".join(schema["enum"]) if "enum" in schema else kind
    return f"{label}|null" if schema.get("nullable") else label


def _as_dict(text: str) -> dict:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("AI の答えの形が違います")
    return data

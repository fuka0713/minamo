"""生成 AI（Gemini または xAI の Grok）を呼ぶ入口。どちらを使うかは、サーバーの .env で決まる。

  LLM_PROVIDER＝gemini（既定）/ xai。選んだ方の鍵（GEMINI_API_KEY / XAI_API_KEY）が無ければ、もう一方の鍵を使う。
  どちらの鍵も無ければ AI は使わない（呼び出し元がルールで動く）。
  - 鍵はサーバーの .env だけに置き、画面（ブラウザ）には絶対に返さない。鍵は URL ではなくヘッダーで送る
  - 答えは JSON で返してもらい、呼び出し元で形を確かめてから使う。失敗したら呼び出し元がルールに戻す
"""

import base64
import json
import os

import httpx

# Gemini の呼び先は2つある。どちらも同じ形の JSON を送り、同じ形で返ってくる
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"  # Gemini API（AIza… の鍵）
VERTEX_URL = "https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent"  # Vertex AI（AQ.… の鍵）
XAI_URL = "https://api.x.ai/v1/chat/completions"


def provider() -> str:
    """使う AI：gemini / xai / none（既定は gemini）。"""
    keys = {"gemini": os.environ.get("GEMINI_API_KEY", ""), "xai": os.environ.get("XAI_API_KEY", "")}
    chosen = os.environ.get("LLM_PROVIDER", "").lower() or "gemini"
    if chosen not in keys:
        chosen = "gemini"
    if keys[chosen]:
        return chosen
    other = "xai" if chosen == "gemini" else "gemini"
    return other if keys[other] else "none"


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
    if which == "xai":
        return _xai(prompt, schema, image)
    raise RuntimeError("AI の鍵が設定されていません")


def gemini_urls(key: str) -> list[str]:
    """鍵の形から、先に試す呼び先を決める。GEMINI_ENDPOINT（gemini / vertex）で決め打ちもできる。

    AIza… は Gemini API（Google AI Studio の鍵）、AQ.… は Vertex AI の鍵のことが多い。
    """
    chosen = os.environ.get("GEMINI_ENDPOINT", "").lower()
    if chosen == "gemini":
        return [GEMINI_URL]
    if chosen == "vertex":
        return [VERTEX_URL]
    return [VERTEX_URL, GEMINI_URL] if key.startswith("AQ.") else [GEMINI_URL, VERTEX_URL]


def _gemini(prompt: str, schema: dict, image: bytes | None) -> dict:
    parts: list[dict] = [{"text": prompt}]
    if image is not None:
        parts.append({"inline_data": {"mime_type": sniff_type(image), "data": base64.b64encode(image).decode()}})
    key = os.environ["GEMINI_API_KEY"]
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema, "temperature": 0.2}}
    urls = gemini_urls(key)
    for i, url in enumerate(urls):
        res = httpx.post(url.format(model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")),
                         headers={"x-goog-api-key": key}, json=body, timeout=30)
        # 鍵がこの呼び先で使えない（400・401・403・404）ときだけ、もう一方を試す
        if res.status_code in (400, 401, 403, 404) and i + 1 < len(urls):
            print(f"Gemini の呼び先 {url.split('/')[2]} で使えませんでした（{res.status_code}）。もう一方を試します")
            continue
        res.raise_for_status()
        return _as_dict(res.json()["candidates"][0]["content"]["parts"][0]["text"])
    raise RuntimeError("Gemini を呼べませんでした")


def _xai(prompt: str, schema: dict, image: bytes | None) -> dict:
    # xAI（Grok）は OpenAI と同じ形の API。答えの形は、文で伝えて JSON モードで返してもらう
    text = f"{prompt}\n\n次の JSON の形だけで答えてください（説明の文は不要）：\n{json.dumps(_plain(schema), ensure_ascii=False)}"
    content: list[dict] = [{"type": "text", "text": text}]
    if image is not None:
        data_url = f"data:{sniff_type(image)};base64,{base64.b64encode(image).decode()}"
        content.append({"type": "image_url", "image_url": {"url": data_url}})
    res = httpx.post(
        XAI_URL,
        headers={"Authorization": f"Bearer {os.environ['XAI_API_KEY']}"},
        json={"model": os.environ.get("XAI_MODEL", "grok-4"),
              "messages": [{"role": "user", "content": content}],
              "response_format": {"type": "json_object"}, "temperature": 0.2},
        timeout=60,
    )
    res.raise_for_status()
    return _as_dict(res.json()["choices"][0]["message"]["content"])


def _plain(schema: dict):
    """Gemini 用の形の説明を、xAI に文で伝える見本（例：{"title": "STRING|null"}）にする。"""
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

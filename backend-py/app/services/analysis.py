"""解析の入口。Gemini の鍵があれば Gemini、なければ（または失敗したら）OCR とルールで解析する。"""

from datetime import datetime

from app.services import analyzer, gemini, ocr


def analyze(image: bytes, content_type: str, now: datetime) -> dict:
    """画像から商品の項目を作る。結果には、使った解析の名前（analyzer）と読み取った文字（ocr_text）も入る。"""
    today = now.date()
    if gemini.enabled():
        try:
            result = gemini.analyze_image(image, content_type, today)
            kind = analyzer.find_limited_kind(f"{result['name']}\n{result['memo']}")
            return {**result, "limited_kind": kind, "analyzer": "gemini", "ocr_text": ""}
        except Exception as err:  # 失敗したらルールの解析に戻す
            print(f"Gemini で解析できませんでした。ルールで解析します: {err!r}")

    try:
        text = ocr.read_text(image)
    except ocr.OcrError as err:
        print(f"文字を読み取れませんでした: {err}")
        text = ""
    return {**analyzer.analyze_text(text, today), "analyzer": "rules", "ocr_text": text}

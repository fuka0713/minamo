"""解析の入口：Gemini の鍵があれば Gemini、なければ（または失敗したら）OCR とルールで解析する。

Gemini を使うときも OCR は動かし、読み取った文字は検索用に残す。
Gemini が空にした項目（お店の名前・期間）は、OCR の文字から読み取れたものでおぎなう。
"""

from datetime import date

from app.services import analyzer, gemini, ocr
from app.services.genres import place_for

PERIOD_FIELDS = ["period_start", "period_end", "deadline", "release_date"]


class AnalysisError(Exception):
    """Gemini も OCR も使えず、何も読み取れなかった。"""


def analyze(image: bytes, today: date | None = None) -> tuple[dict, str, str]:
    """(項目, 読み取った文字, 使った解析 "gemini" か "rules") を返す。"""
    today = today or date.today()
    try:
        text = ocr.read_text(image)
    except ocr.OcrError as err:
        if not gemini.enabled():
            raise AnalysisError(str(err)) from err
        print(f"文字を読み取れませんでした（Gemini だけで解析します）: {err}")
        text = ""
    rules = analyzer.analyze(text, today)

    if gemini.enabled():
        try:
            values = gemini.analyze_image(image, today)
        except Exception as err:  # 失敗したら OCR とルールの結果を使う
            print(f"Gemini で解析できませんでした。ルールで解析します: {err!r}")
        else:
            values["place_category"] = place_for(values["genre"])
            values["place_name"] = values["place_name"] or rules["place_name"]
            if not any(values[f] for f in PERIOD_FIELDS):  # 期間が空なら、ルールで読み取れたものを使う
                values.update({f: rules[f] for f in PERIOD_FIELDS})
            return values, text, "gemini"

    if not text:
        raise AnalysisError("文字を読み取れませんでした")
    return rules, text, "rules"

"""文字認識（OCR）：コンテナに入れた Tesseract で、日本語と英語の文字を読み取る。"""

import subprocess


class OcrError(Exception):
    """文字を読み取れなかった。"""


def read_text(image: bytes) -> str:
    try:
        result = subprocess.run(["tesseract", "stdin", "stdout", "-l", "jpn+eng"], input=image, capture_output=True, timeout=30)
    except FileNotFoundError as err:
        raise OcrError("Tesseract が入っていません") from err
    except subprocess.TimeoutExpired as err:
        raise OcrError("文字の読み取りに時間がかかりすぎました") from err
    if result.returncode != 0:
        raise OcrError(result.stderr.decode("utf-8", errors="ignore")[:200])
    return result.stdout.decode("utf-8", errors="ignore").strip()

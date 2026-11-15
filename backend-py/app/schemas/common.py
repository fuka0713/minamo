from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """エラーのときの形。例：{"detail": "ログインしてください"}"""

    detail: str

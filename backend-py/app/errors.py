"""エラーの形をそろえる。

すべてのエラーは次の形で返す（API の取り決め）：
  {"error": {"code": "NOT_FOUND", "message": "対象が見つかりません。", "requestId": "req_..."}}
"""

import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

CODES = {
    400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 429: "TOO_MANY_REQUESTS",
    409: "CONFLICT", 413: "PAYLOAD_TOO_LARGE", 415: "UNSUPPORTED_MEDIA_TYPE", 500: "INTERNAL_ERROR",
}


class ApiError(HTTPException):
    """コードを指定して返したいエラー。例：raise ApiError(404, "NOT_FOUND", "対象が見つかりません。")"""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.code = code


class ErrorBody(BaseModel):
    code: str
    message: str
    requestId: str


class ErrorEnvelope(BaseModel):
    """エラーのときの形（Swagger に表示する用）。"""

    error: ErrorBody


def not_found() -> ApiError:
    return ApiError(404, "NOT_FOUND", "対象が見つかりません。")


def _body(request: Request, status: int, code: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "req_unknown")
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "requestId": request_id}},
        headers={"X-Request-ID": request_id},
    )


def install(app: FastAPI) -> None:
    """エラーの形をそろえる処理と、リクエストごとの ID を付ける処理を登録する。"""

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = f"req_{uuid.uuid4().hex[:16]}"
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        code = getattr(exc, "code", None) or CODES.get(exc.status_code, "ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "エラーが起きました。"
        return _body(request, exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # 入力がおかしいときは 400（どの項目がおかしいかを短く伝える）
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", []) if p not in ("body", "query", "path"))
        message = f"入力が正しくありません：{where}（{first.get('msg', '')}）" if where else "入力が正しくありません。"
        return _body(request, 400, "VALIDATION_ERROR", message)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        print(f"予期しないエラー（{getattr(request.state, 'request_id', '')}）: {exc!r}")
        return _body(request, 500, "INTERNAL_ERROR", "サーバーでエラーが起きました。")

"""共通の部品。"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import PlainSerializer


def _utc(value: datetime) -> str:
    """日時を UTC の ISO 8601（例：2026-11-15T03:00:00Z）にする。"""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


# 返すときは必ず UTC（…Z）の形にする日時
UtcDatetime = Annotated[datetime, PlainSerializer(_utc, return_type=str)]

"""日時のそろえ方：データベースには UTC で入れ、API ではタイムゾーンつきで返す。"""

from datetime import UTC, datetime


def to_utc(value: datetime | None) -> datetime | None:
    """タイムゾーンのない日時は UTC とみなす（SQLite はタイムゾーンを持たないため）。"""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

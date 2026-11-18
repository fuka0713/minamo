"""日時の扱いをそろえる（いつも「タイムゾーンつきの UTC」で扱う）。"""

from datetime import UTC, datetime


def now_utc() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime | None) -> datetime | None:
    """タイムゾーンのない日時（テスト用の SQLite など）は UTC とみなす。"""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

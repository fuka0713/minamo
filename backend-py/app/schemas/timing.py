"""リマインドと場所の入力の形（解析 API の側）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReminderIn(BaseModel):
    """自分で決めたリマインド。"""

    model_config = ConfigDict(extra="forbid")
    remindAt: datetime = Field(description="知らせる日時（タイムゾーンつき。例：2026-12-02T20:00:00+09:00）")
    reason: str | None = Field(None, max_length=200, description="理由")


class PlaceIn(BaseModel):
    """場所の登録・変更（送った項目だけ変わる）。"""

    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, max_length=100, description="お店の名前（例：IKEA 新宿）")
    category: str | None = Field(None, max_length=100, description="お店の種類（例：ドラッグストア）")
    lat: float | None = Field(None, ge=-90, le=90, description="緯度（ブラウザの「現在地」などから）")
    lng: float | None = Field(None, ge=-180, le=180, description="経度")
    radiusM: int | None = Field(None, ge=50, le=2000, description="この半径（m）に入ったら知らせる")
    visible: bool | None = Field(None, description="画面に表示するか")

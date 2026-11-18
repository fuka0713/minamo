"""リマインドのタイミングと、場所の入出力の形。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["period_end", "period_start", "deadline", "release_date", "weekend", "payday", "week_later"]


class ReminderSuggestion(BaseModel):
    """リマインドの候補（解析の結果から推測）。"""

    remindAt: datetime = Field(description="知らせる日時")
    reason: str = Field(description="その日時にした理由（通知の文にも使う）")
    source: Source = Field(description="period_end=終わる3日前 / period_start=始まる日 / deadline=締切の前日 / "
                           "release_date=発売日 / weekend=週末（飲食店）/ payday=給料日 / week_later=1週間後")


class SuggestionList(BaseModel):
    suggestions: list[ReminderSuggestion]


class ReminderIn(BaseModel):
    """ユーザーが選んだリマインド（候補から選ぶか、自分で日時を決める）。"""

    model_config = ConfigDict(extra="forbid")
    remindAt: datetime = Field(description="知らせる日時（タイムゾーンつき。例：2026-12-02T20:00:00+09:00）")
    reason: str | None = Field(None, max_length=200, description="理由（候補を選んだときは、その reason をそのまま送る）")


class PlaceIn(BaseModel):
    """場所の登録・変更（送った項目だけ変わる）。"""

    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, max_length=100, description="お店の名前（例：IKEA 新宿）")
    category: str | None = Field(None, max_length=100, description="お店の種類（例：ドラッグストア）")
    lat: float | None = Field(None, ge=-90, le=90, description="緯度（ブラウザの「現在地」などから）")
    lng: float | None = Field(None, ge=-180, le=180, description="経度")
    radiusM: int | None = Field(None, ge=50, le=2000, description="この半径（m）に入ったら知らせる")
    visible: bool | None = Field(None, description="画面に表示するか")


class NearbyIn(BaseModel):
    """今いる場所。保存はしない（近くに欲しいものがあるかを調べるだけ）。"""

    model_config = ConfigDict(extra="forbid")
    lat: float = Field(ge=-90, le=90, examples=[35.6909])
    lng: float = Field(ge=-180, le=180, examples=[139.7003])


class NearbyMatch(BaseModel):
    itemId: int
    title: str | None
    imageUrl: str
    placeName: str = Field(description="近くにある場所・お店の名前")
    distanceM: int = Field(description="だいたいの距離（m）")
    reason: str = Field(description="通知の文")


class NearbyOut(BaseModel):
    matches: list[NearbyMatch] = Field(description="知らせるもの（同じ商品は24時間に1回まで）")

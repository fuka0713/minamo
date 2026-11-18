"""推薦 API の入出力の形。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Basis = Literal["period_end", "period_start", "deadline", "release_date", "payday", "weekend", "season", "place", "other"]
Source = Literal["gemini", "xai", "rules"]


class Location(BaseModel):
    """今いる場所（任意）。保存はしない。送らなければ仮の場所（新宿駅）を使う。"""

    model_config = ConfigDict(extra="forbid")
    lat: float | None = Field(None, ge=-90, le=90, examples=[35.6896])
    lng: float | None = Field(None, ge=-180, le=180, examples=[139.7006])


class RecPlace(BaseModel):
    name: str = Field(description="推薦理由に使ったお店（ダミーのこともある）")
    lat: float | None
    lng: float | None


class RecItem(BaseModel):
    id: int
    title: str | None
    genre: str | None
    imageUrl: str


class RecommendationOut(BaseModel):
    """推薦：いつ知らせるとよいか（推薦日）と、その理由（推薦理由）。"""

    id: int
    itemId: int
    recommendAt: datetime = Field(description="推薦日（知らせるとよい日時）")
    reason: str = Field(description="推薦理由（通知の文にも使う）")
    basis: Basis = Field(description="一番の理由：period_end=期間の終わり / deadline=締切 / release_date=発売日 / "
                         "period_start=始まる日 / payday=給料日 / weekend=週末 / season=季節 / place=お店 / other")
    source: Source = Field(description="考えたもの：gemini / xai / rules（AI が使えないときのルール）")
    status: Literal["suggested", "accepted"] = Field(description="suggested=提案中 / accepted=リマインドにした")
    place: RecPlace | None = Field(None, description="理由に使ったお店")
    item: RecItem | None = Field(None, description="（ホームの一覧のときだけ）商品")


class RecommendationList(BaseModel):
    recommendations: list[RecommendationOut]


class NearbyIn(BaseModel):
    """今いる場所。保存はしない（近くに欲しいものがあるかを調べるだけ）。"""

    model_config = ConfigDict(extra="forbid")
    lat: float = Field(ge=-90, le=90, examples=[35.6912])
    lng: float = Field(ge=-180, le=180, examples=[139.7019])


class NearbyMatch(BaseModel):
    itemId: int
    title: str | None
    imageUrl: str
    placeName: str = Field(description="近くにある場所・お店の名前（既定はダミーのお店）")
    distanceM: int = Field(description="だいたいの距離（m）")
    reason: str = Field(description="推薦理由（通知の文）")
    source: Source


class NearbyOut(BaseModel):
    matches: list[NearbyMatch] = Field(description="知らせるもの（同じ商品は24時間に1回まで・近い順）")

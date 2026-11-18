"""欲しいもの（スクショ1枚分）の入出力の形。"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

WishStatus = Literal["want", "not_want", "pending"]  # いる / いらない / 保留
AnalysisStatus = Literal["pending", "done", "failed"]  # 待ち / 完了 / 失敗


class Price(BaseModel):
    """価格。間違っているとストレスなので、visible が true になるまで画面に出さない。"""

    value: int | None = Field(None, description="解析で読み取った価格（円）")
    visible: bool = Field(False, description="画面に表示するか（最初は false）")


class Place(BaseModel):
    """買える場所。間違っているとストレスなので、visible が true になるまで画面に出さない。"""

    category: str | None = Field(None, description="お店の種類（ジャンルから自動。例：ドラッグストア）")
    name: str | None = Field(None, description="具体的なお店（例：IKEA 新宿）")
    visible: bool = Field(False, description="画面に表示するか（最初は false）")
    lat: float | None = Field(None, description="緯度（「ここを通ったら知らせて」の場所。ユーザーが登録）")
    lng: float | None = Field(None, description="経度")
    radiusM: int = Field(200, description="この半径（m）に入ったら知らせる")


class Period(BaseModel):
    """期間。解析で読み取る（YYYY-MM-DD。分からなければ null）。"""

    start: date | None = Field(None, description="始まる日")
    end: date | None = Field(None, description="終わる日")
    deadline: date | None = Field(None, description="締切")
    release: date | None = Field(None, description="発売日")
    source: Literal["auto", "user"] = Field("auto", description="auto=自動 / user=ユーザーが修正")


class Analysis(BaseModel):
    """解析の状態。"""

    status: AnalysisStatus = Field(description="pending=待ち / done=完了 / failed=失敗")
    analyzedAt: datetime | None = Field(None, description="解析した日時")
    analyzer: Literal["gemini", "groq", "rules"] | None = Field(None, description="使った解析：gemini / groq / rules（OCR とルール）")


class ReminderOut(BaseModel):
    """リマインド日。"""

    id: int
    remindAt: datetime = Field(description="知らせる日時")
    reason: str = Field(description="通知に出す理由")
    status: Literal["scheduled", "sent", "canceled"]
    source: Literal["auto", "user"] = Field("auto", description="auto=解析から自動 / user=ユーザーが選んだ")


class ItemOut(BaseModel):
    """欲しいもの。登録した直後は、登録した日と画像だけが入っている（ほかは解析で埋まる）。"""

    id: int
    createdAt: datetime = Field(description="登録した日（登録のときに入る）")
    imageUrl: str = Field(description="画像の URL（登録のときに入る）")
    analysis: Analysis
    title: str | None = Field(None, description="商品名（解析で埋まる。正確でなくてよい）")
    description: str | None = Field(None, description="説明文（解析で埋まる）")
    price: Price
    wishStatus: WishStatus = Field(description="欲しいステータス：want=いる / not_want=いらない / pending=保留")
    genre: str | None = Field(None, description="ジャンル（解析で埋まる）")
    place: Place
    period: Period
    reminders: list[ReminderOut] = Field(default_factory=list, description="リマインド日")

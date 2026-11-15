"""欲しいもの（スクショ1枚分）の入出力の形。"""

from datetime import datetime
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


class Analysis(BaseModel):
    """解析の状態。"""

    status: AnalysisStatus = Field(description="pending=待ち / done=完了 / failed=失敗")
    analyzedAt: datetime | None = Field(None, description="解析した日時")


class ReminderOut(BaseModel):
    """リマインド日。"""

    id: int
    remindAt: datetime = Field(description="知らせる日時")
    reason: str = Field(description="通知に出す理由")
    status: Literal["scheduled", "sent", "canceled"]


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
    reminders: list[ReminderOut] = Field(default_factory=list, description="リマインド日")

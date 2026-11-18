"""リマインド・掲示板・通知・設定の入出力。"""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDatetime
from app.schemas.item import ItemOut


class ReminderSuggestion(BaseModel):
    date: dt.date = Field(description="候補の日（利用者のタイムゾーン）")
    reason: str = Field(description="その日にした理由")
    source: str = Field(description="period_end / period_start / deadline / release_date / lifestyle")
    remindAt: UtcDatetime = Field(description="（追加）そのまま登録に使える日時")


class SuggestionList(BaseModel):
    suggestions: list[ReminderSuggestion]


class ReminderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    remindAt: dt.datetime
    reason: str | None = Field(None, max_length=200)


class ReminderOut(BaseModel):
    id: str
    itemId: str
    remindAt: UtcDatetime
    reason: str
    status: Literal["scheduled", "sent", "cancelled"]


class ReminderList(BaseModel):
    reminders: list[ReminderOut]


class BoardItem(BaseModel):
    itemId: str
    name: str
    imageUrl: str
    releaseDate: dt.date | None = Field(None, description="発売日（あれば）")
    reason: str = Field(description="おすすめの理由")


class BoardList(BaseModel):
    items: list[BoardItem]


class NotificationOut(BaseModel):
    id: str
    itemId: str
    message: str
    status: Literal["unread", "answered"]
    answer: Literal["bought", "later", "unwanted"] | None = Field(None, description="（追加）回答")
    createdAt: UtcDatetime = Field(description="（追加）知らせた日時")
    item: ItemOut | None = Field(None, description="（追加）回答のあとの商品の状態")


class NotificationList(BaseModel):
    notifications: list[NotificationOut]


class AnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: Literal["bought", "later", "unwanted"]


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoint: str = Field(pattern=r"^https://")
    keys: PushKeys


class PushOut(BaseModel):
    id: str
    active: bool


class SettingsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pushEnabled: bool = Field(description="お知らせ（リマインド）を使うか")
    privacyMode: bool = Field(description="価格を隠すか")

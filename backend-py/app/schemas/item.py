"""欲しいもの（商品）の入出力。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import UtcDatetime

ItemStatus = Literal["wanted", "hold", "bought", "unwanted"]  # 欲しい / 保留 / 買った / いらない
PeriodType = Literal["release_date", "event_period", "deadline", "other"]  # 発売日 / 開催期間 / 締切 / その他
Repeat = Literal["none", "daily", "weekly", "monthly"]
LimitedKind = Literal["limited", "collab", "sale"]  # 期間限定 / コラボ / セール


class Period(BaseModel):
    """期間。自由文にせず、種類をつけて持つ。"""

    type: PeriodType = Field(description="release_date=発売日 / event_period=開催期間 / deadline=締切 / other=その他")
    startAt: UtcDatetime | None = Field(None, description="始まり（発売日・開催の初日）")
    endAt: UtcDatetime | None = Field(None, description="終わり（開催の最終日・締切）")


class ItemOut(BaseModel):
    """欲しいもの。分からない項目は null（解析で値を作り出さない）。"""

    id: str = Field(examples=["itm_1a2b3c"])
    name: str = Field(description="商品名（特定できなければ、仮の名前）")
    brand: str | None = Field(description="ブランド")
    genre: str = Field(description="ジャンル（/api/genres のどれか）")
    price: float | None = Field(description="価格")
    currency: str | None = Field(description="通貨（ISO 4217。例：JPY）")
    shop: str | None = Field(description="販売元・ショップ")
    url: str | None = Field(description="購入先（http / https）")
    period: Period | None = Field(description="期間（発売日・開催期間・締切）")
    identification: Literal["identified", "unidentified"] = Field(description="identified=商品を特定できた / unidentified=まだ")
    confidence: float = Field(ge=0, le=1, description="解析の確かさ（0〜1）")
    status: ItemStatus = Field(description="wanted=欲しい / hold=保留 / bought=買った / unwanted=いらない")
    memo: str = Field(description="説明・メモ")
    createdAt: UtcDatetime = Field(description="登録した日時")
    remindAt: UtcDatetime | None = Field(description="次に思い出す日時")
    imageUrl: str = Field(description="スクショ画像（<img src> にそのまま使える）", examples=["/api/items/itm_1a2b3c/image"])
    # ---- 取り決めへの追加（画面で使う） ----
    reminderReason: str | None = Field(None, description="（追加）remindAt にした理由")
    repeat: Repeat = Field("none", description="（追加）リマインドの繰り返し")
    limitedUntil: UtcDatetime | None = Field(None, description="（追加）期間限定・締切の終わり（開催期間か締切の終わりの日の 23:59:59）")
    limitedKind: LimitedKind | None = Field(None, description="（追加）期限の種類：limited=期間限定 / collab=コラボ / sale=セール")


class ItemPage(BaseModel):
    items: list[ItemOut]
    nextCursor: str | None = Field(description="続きがあるときの目印。null なら最後まで読んだ")


class PeriodIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: PeriodType
    startAt: datetime | None = None
    endAt: datetime | None = None


class ItemPatch(BaseModel):
    """送った項目だけ変わる。null を送った項目は「未設定」にする。決められた項目以外を送ると 400。"""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=100)
    brand: str | None = Field(None, max_length=100)
    genre: str | None = None
    price: float | None = Field(None, ge=0, le=999_999_999)
    currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")
    shop: str | None = Field(None, max_length=100)
    url: str | None = Field(None, max_length=2000)
    memo: str | None = Field(None, max_length=500)
    period: PeriodIn | None = None
    status: ItemStatus | None = None
    repeat: Repeat | None = Field(None, description="（追加）リマインドの繰り返し")
    limitedKind: LimitedKind | None = Field(None, description="（追加）期限の種類")

    @field_validator("url")
    @classmethod
    def http_only(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith(("http://", "https://")):
            raise ValueError("http または https の URL にしてください")
        return value


class GenreList(BaseModel):
    genres: list[str] = Field(examples=[["コスメ", "ファッション", "家具・インテリア", "暮らし", "日用品", "ガジェット", "本・文具", "その他"]])

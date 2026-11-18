"""欲しいもの（スクショ1枚分）と、リマインド日。"""

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))  # 持ち主

    # ---- 登録のときに入れる ----
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # 登録した日
    image_key: Mapped[str] = mapped_column(Text)  # 画像の保存場所（users/{ユーザーID}/…）

    # ---- 解析で埋める（ユーザーが直せる） ----
    title: Mapped[str | None] = mapped_column(Text)  # 商品名（正確でなくてよい）
    description: Mapped[str | None] = mapped_column(Text)  # 説明文
    price: Mapped[int | None] = mapped_column(Integer)  # 価格
    genre: Mapped[str | None] = mapped_column(Text)  # ジャンル
    place_category: Mapped[str | None] = mapped_column(Text)  # 場所：お店の種類（ジャンルから自動）
    place_name: Mapped[str | None] = mapped_column(Text)  # 場所：具体的なお店（AI・ユーザー）
    period_start: Mapped[date | None] = mapped_column(Date)  # 期間：始まる日
    period_end: Mapped[date | None] = mapped_column(Date)  # 期間：終わる日
    deadline: Mapped[date | None] = mapped_column(Date)  # 締切
    release_date: Mapped[date | None] = mapped_column(Date)  # 発売日

    # ---- 場所と結びつける（ユーザーが登録。「ここを通ったら知らせて」） ----
    place_lat: Mapped[float | None] = mapped_column(Float)  # 緯度
    place_lng: Mapped[float | None] = mapped_column(Float)  # 経度
    place_radius_m: Mapped[int] = mapped_column(Integer, default=200)  # この半径（m）に入ったら知らせる
    place_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 最後に場所で知らせた日時（何度も知らせないため）

    # ---- ユーザーが決める ----
    wish_status: Mapped[str] = mapped_column(Text, default="want")  # want=いる / not_want=いらない / pending=保留
    price_visible: Mapped[bool] = mapped_column(Boolean, default=False)  # 価格を表示するか（間違いのストレスを避けるため最初は非表示）
    place_visible: Mapped[bool] = mapped_column(Boolean, default=False)  # 場所を表示するか（同上）
    edited_fields: Mapped[list] = mapped_column(JSON, default=list)  # ユーザーが直した項目（再解析で上書きしない）

    # ---- 解析の状態 ----
    analysis_status: Mapped[str] = mapped_column(Text, default="pending")  # pending=待ち / done=完了 / failed=失敗
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 解析した日時
    ocr_text: Mapped[str] = mapped_column(Text, default="")  # 読み取った文字（画面には出さない）

    # ---- Express の backend が使っている列 ----
    genre_source: Mapped[str] = mapped_column(Text, default="auto")  # auto=自動 / user=ユーザーが修正
    period_source: Mapped[str] = mapped_column(Text, default="auto")  # auto=自動 / user=ユーザーが修正
    url: Mapped[str | None] = mapped_column(Text)
    memo: Mapped[str] = mapped_column(Text, default="")


class Reminder(Base):
    """リマインド日（1つの商品に複数登録できる）。"""

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # 知らせる日時
    reason: Mapped[str] = mapped_column(Text, default="")  # 通知に出す理由
    source: Mapped[str] = mapped_column(Text, default="auto")  # auto=解析から自動 / user=ユーザーが選んだ
    status: Mapped[str] = mapped_column(Text, default="scheduled")  # scheduled=予定 / sent=送った / canceled=取り消し
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

"""欲しいもの（スクショ1枚から見つけた商品）。"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # 例：itm_1a2b…
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)  # 持ち主

    # ---- 商品の情報（解析で埋まる。分からなければ null。ユーザーが直せる） ----
    name: Mapped[str] = mapped_column(Text)  # 商品名（特定できなければ仮の名前）
    brand: Mapped[str | None] = mapped_column(Text)  # ブランド
    genre: Mapped[str] = mapped_column(Text)  # ジャンル（/api/genres のどれか）
    price: Mapped[float | None] = mapped_column(Numeric(12, 2))  # 価格
    currency: Mapped[str | None] = mapped_column(Text)  # 通貨（ISO 4217。例：JPY）
    shop: Mapped[str | None] = mapped_column(Text)  # 販売元・ショップ
    url: Mapped[str | None] = mapped_column(Text)  # 購入先（http / https だけ）
    memo: Mapped[str] = mapped_column(Text, default="")  # 説明・メモ

    # ---- 期間（発売日・開催期間・締切など） ----
    period_type: Mapped[str | None] = mapped_column(Text)  # release_date / event_period / deadline / other
    period_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ---- 解析の確かさ ----
    identification: Mapped[str] = mapped_column(Text, default="unidentified")  # identified=商品を特定できた / unidentified=できていない
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0〜1
    analyzer: Mapped[str] = mapped_column(Text, default="rules")  # rules（OCR とルール）/ gemini
    ocr_text: Mapped[str] = mapped_column(Text, default="")  # 読み取った文字（画面には出さない）

    # ---- 状態・リマインド ----
    status: Mapped[str] = mapped_column(Text, default="wanted")  # wanted=欲しい / hold=保留 / bought=買った / unwanted=いらない
    remind_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 次に思い出す日時
    reminder_reason: Mapped[str | None] = mapped_column(Text)  # その日にした理由
    repeat: Mapped[str] = mapped_column(Text, default="none")  # none / daily / weekly / monthly
    limited_kind: Mapped[str | None] = mapped_column(Text)  # 期限の種類：limited=期間限定 / collab=コラボ / sale=セール（画面の推薦理由に使う）

    image_key: Mapped[str] = mapped_column(Text)  # 画像の保存場所（users/{ユーザーID}/…）
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

"""リマインド（1つの商品に複数登録できる）。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # 例：rmd_1a2b…
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # 知らせる日時
    reason: Mapped[str] = mapped_column(Text, default="")  # 理由
    source: Mapped[str] = mapped_column(Text, default="user")  # user=自分で登録 / auto=登録時に自動 / later=「あとで」で自動
    status: Mapped[str] = mapped_column(Text, default="scheduled")  # scheduled=予定 / sent=知らせた / cancelled=取り消し
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

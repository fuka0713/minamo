"""通知と、Web プッシュ通知の宛先。"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # 例：ntf_1a2b…
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    reminder_id: Mapped[str | None] = mapped_column(ForeignKey("reminders.id", ondelete="SET NULL"))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="unread")  # unread=未回答 / answered=回答済み
    answer: Mapped[str | None] = mapped_column(Text)  # bought / later / unwanted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PushSubscription(Base):
    """ブラウザの Web プッシュ通知の宛先（秘密の情報として扱う）。"""

    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # 例：psh_1a2b…
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    keys: Mapped[dict] = mapped_column(JSON)  # p256dh・auth
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

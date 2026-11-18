"""通知・プライバシーの設定。"""

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Setting(Base):
    __tablename__ = "settings"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # お知らせ（リマインド）を使うか
    privacy_mode: Mapped[bool] = mapped_column(Boolean, default=False)  # 価格を隠すか

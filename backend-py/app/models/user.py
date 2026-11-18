"""アカウントとログイン中の印。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # 例：usr_1a2b…
    email: Mapped[str] = mapped_column(Text, unique=True)  # 小文字にそろえて保存
    password_hash: Mapped[str] = mapped_column(Text)  # 「salt:hash」（scrypt）。パスワードそのものは保存しない
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoginSession(Base):
    """ログイン中の印（ブラウザのクッキー「session」の値）。"""

    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

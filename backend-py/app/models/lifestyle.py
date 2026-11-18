"""生活スタイル（5問の診断の結果）。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Lifestyle(Base):
    __tablename__ = "lifestyles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    payday: Mapped[int] = mapped_column(Integer, default=25)  # 給料日（1〜31）
    source: Mapped[str] = mapped_column(Text, default="diagnosed")  # diagnosed=診断の回答 / manual=あとから直接変更
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)  # 回答（よく見るジャンル・買い物のスタイル・考える時期・通知の時間帯）
    answers: Mapped[list] = mapped_column(JSON, default=list)  # 5問の回答そのもの
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

"""推薦（いつ・どこで思い出させるか）の記録。"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    recommend_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # 推薦日（知らせるとよい日時）
    reason: Mapped[str] = mapped_column(Text)  # 推薦理由（通知の文にも使う）
    basis: Mapped[str] = mapped_column(Text, default="other")  # 一番の理由：period_end / deadline / payday / place など
    source: Mapped[str] = mapped_column(Text, default="rules")  # 考えたもの：gemini / groq / rules
    place_name: Mapped[str | None] = mapped_column(Text)  # 理由に使ったお店
    place_lat: Mapped[float | None] = mapped_column(Float)
    place_lng: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(Text, default="suggested")  # suggested=提案中 / accepted=リマインドにした / replaced=作り直した
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

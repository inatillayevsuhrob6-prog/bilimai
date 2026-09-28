from datetime import datetime, date
from sqlalchemy import Integer, ForeignKey, DateTime, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class LearningHistory(Base):
    __tablename__ = "learning_history"
    __table_args__ = (UniqueConstraint("user_id", "activity_date", name="uq_history_user_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    lessons_count: Mapped[int] = mapped_column(Integer, default=0)
    tests_count: Mapped[int] = mapped_column(Integer, default=0)
    score_sum: Mapped[int] = mapped_column(Integer, default=0)
    score_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User")

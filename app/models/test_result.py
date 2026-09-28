from datetime import datetime
from sqlalchemy import Integer, ForeignKey, DateTime, Text, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)

    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=10)
    percentage: Mapped[float] = mapped_column(Float, default=0.0)

    weak_concepts: Mapped[list | None] = mapped_column(JSON, nullable=True)
    strong_concepts: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="test_results")
    lesson = relationship("Lesson", back_populates="test_results")
    answers = relationship("Answer", back_populates="test_result", cascade="all, delete-orphan")

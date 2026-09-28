from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # NEW fields for rich notes
    color: Mapped[str] = mapped_column(String(16), default="violet")  # violet|pink|cyan|amber|emerald|rose|slate
    font_style: Mapped[str] = mapped_column(String(16), default="normal")  # normal|bold|italic|handwritten|code
    priority: Mapped[str] = mapped_column(String(16), default="normal")  # low|normal|high|urgent
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)

    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True)
    test_result_id: Mapped[int | None] = mapped_column(ForeignKey("test_results.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notes")

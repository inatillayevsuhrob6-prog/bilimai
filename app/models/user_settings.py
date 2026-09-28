from sqlalchemy import Integer, ForeignKey, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)

    auto_save_notes: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_tests: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_revision: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_streak: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_weak_topics: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_difficulty: Mapped[str] = mapped_column(String(16), default="mixed")

    user = relationship("User", back_populates="settings")

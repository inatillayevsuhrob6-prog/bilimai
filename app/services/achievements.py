"""Achievement definitions and unlock logic."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Achievement, Lesson, TestResult, User

ACHIEVEMENTS = {
    "first_lesson": ("First Lesson", "Birinchi dars", "Создан первый урок"),
    "first_test":   ("First Test", "Birinchi test", "Первый тест завершён"),
    "ten_tests":    ("10 Tests Completed", "10 ta test", "Пройдено 10 тестов"),
    "streak_7":     ("7-Day Streak", "7 kunlik davomiylik", "Серия 7 дней"),
    "score_90":     ("90% Score", "90% natija", "Результат 90%"),
    "score_100":    ("100% Score", "100% natija", "Результат 100%"),
    "lessons_50":   ("50 Lessons", "50 ta dars", "50 уроков"),
    "consistent":   ("Consistent Learner", "Barqaror o'quvchi", "Постоянный ученик"),
}


def _unlock(db: Session, user_id: int, code: str) -> None:
    exists = db.scalar(select(Achievement).where(
        Achievement.user_id == user_id, Achievement.code == code))
    if exists:
        return
    title, uz, ru = ACHIEVEMENTS[code]
    db.add(Achievement(user_id=user_id, code=code, title=title, description=uz))
    db.flush()


def check_after_lesson(db: Session, user: User) -> None:
    count = db.scalar(select(func.count()).select_from(Lesson).where(Lesson.user_id == user.id))
    if count and count >= 1:
        _unlock(db, user.id, "first_lesson")
    if count and count >= 50:
        _unlock(db, user.id, "lessons_50")


def check_after_test(db: Session, user: User, percentage: float) -> None:
    count = db.scalar(select(func.count()).select_from(TestResult).where(TestResult.user_id == user.id))
    if count and count >= 1:
        _unlock(db, user.id, "first_test")
    if count and count >= 10:
        _unlock(db, user.id, "ten_tests")
    if percentage >= 90:
        _unlock(db, user.id, "score_90")
    if percentage >= 100:
        _unlock(db, user.id, "score_100")


def check_streak(db: Session, user: User, streak: int) -> None:
    if streak >= 7:
        _unlock(db, user.id, "streak_7")

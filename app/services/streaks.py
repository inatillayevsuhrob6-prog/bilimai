"""Learning streak calculation based on learning_history."""
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LearningHistory


def current_streak(db: Session, user_id: int) -> int:
    today = date.today()
    rows = db.scalars(
        select(LearningHistory.activity_date)
        .where(LearningHistory.user_id == user_id)
        .order_by(LearningHistory.activity_date.desc())
        .limit(400)
    ).all()
    days = {r for r in rows}
    if not days:
        return 0
    streak = 0
    cursor = today
    # allow streak to count yesterday too if user hasn't learned today yet
    if cursor not in days and (cursor - timedelta(days=1)) in days:
        cursor = cursor - timedelta(days=1)
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def record_activity(db: Session, user_id: int, lesson_inc: int = 0, test_inc: int = 0, score: int = 0) -> None:
    today = date.today()
    row = db.scalar(select(LearningHistory).where(
        LearningHistory.user_id == user_id, LearningHistory.activity_date == today))
    if not row:
        row = LearningHistory(user_id=user_id, activity_date=today)
        db.add(row)
        db.flush()
    row.lessons_count = (row.lessons_count or 0) + lesson_inc
    row.tests_count = (row.tests_count or 0) + test_inc
    if score:
        row.score_sum = (row.score_sum or 0) + score
        row.score_count = (row.score_count or 0) + 1

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, TestResult, Lesson, Question, Answer
from app.security.deps import get_current_user
from app.services.i18n import translator_for
from app.services.streaks import current_streak

router = APIRouter(prefix="/analytics", tags=["analytics"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def analytics(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tt = translator_for(user.language)

    tests = db.scalars(select(TestResult).where(TestResult.user_id == user.id).order_by(TestResult.created_at)).all()
    chart = [{"date": t.created_at.strftime("%m-%d"), "pct": t.percentage} for t in tests[-30:]]

    total_q = db.scalar(
        select(func.count()).select_from(Answer).join(TestResult, Answer.test_result_id == TestResult.id)
        .where(TestResult.user_id == user.id)
    ) or 0
    correct_q = db.scalar(
        select(func.count()).select_from(Answer).join(TestResult, Answer.test_result_id == TestResult.id)
        .where(TestResult.user_id == user.id, Answer.is_correct == True)
    ) or 0

    subject_stats_rows = db.execute(
        select(Lesson.subject,
               func.count(func.distinct(TestResult.id)),
               func.avg(TestResult.percentage))
        .join(TestResult, TestResult.lesson_id == Lesson.id)
        .where(Lesson.user_id == user.id)
        .group_by(Lesson.subject)
    ).all()
    subject_stats = [{"subject": s, "tests": c, "avg": round(float(a or 0), 1)} for s, c, a in subject_stats_rows]
    weak = sorted(subject_stats, key=lambda x: x["avg"])[:3]
    strong = sorted(subject_stats, key=lambda x: x["avg"], reverse=True)[:3]

    avg = round(sum(t.percentage for t in tests) / len(tests), 1) if tests else 0
    best = round(max((t.percentage for t in tests), default=0), 1)

    return templates.TemplateResponse("main/analytics.html", {
        "request": request, "user": user, "lang": user.language, "t": tt,
        "chart": chart, "weak": weak, "strong": strong,
        "avg": avg, "best": best,
        "tests_count": len(tests),
        "lessons_count": db.scalar(select(func.count()).select_from(Lesson).where(Lesson.user_id == user.id)) or 0,
        "total_q": total_q, "correct_q": correct_q,
        "correct_pct": round(correct_q / total_q * 100, 1) if total_q else 0,
        "streak": current_streak(db, user.id),
        "history": [{"date": t.created_at.strftime("%Y-%m-%d"), "pct": t.percentage, "lesson_id": t.lesson_id} for t in reversed(tests[-20:])],
    })

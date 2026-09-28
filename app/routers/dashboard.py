from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Lesson, TestResult, Note, Notification, Achievement
from app.security.deps import get_current_user
from app.services.i18n import translator_for
from app.services.subjects import list_subjects
from app.services.streaks import current_streak

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), user: User | None = Depends(lambda: None)):
    from app.security.deps import get_current_user_optional
    # manual optional check
    u = get_current_user_optional(request, db)
    if not u:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")
    return _render_dashboard(request, db, u)


def _render_dashboard(request: Request, db: Session, user: User):
    tt = translator_for(user.language)

    lessons_count = db.scalar(select(func.count()).select_from(Lesson).where(Lesson.user_id == user.id)) or 0
    tests_count = db.scalar(select(func.count()).select_from(TestResult).where(TestResult.user_id == user.id)) or 0
    avg_score = db.scalar(select(func.avg(TestResult.percentage)).where(TestResult.user_id == user.id)) or 0.0

    recent_lessons = db.scalars(
        select(Lesson).where(Lesson.user_id == user.id).order_by(desc(Lesson.created_at)).limit(5)
    ).all()
    recent_notes = db.scalars(
        select(Note).where(Note.user_id == user.id).order_by(desc(Note.updated_at)).limit(5)
    ).all()
    recent_results = db.scalars(
        select(TestResult).where(TestResult.user_id == user.id).order_by(desc(TestResult.created_at)).limit(5)
    ).all()

    unread_notifications = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user.id, Notification.is_read == False)
    ) or 0

    # progress chart: last 14 test percentages
    chart_rows = db.execute(
        select(TestResult.created_at, TestResult.percentage)
        .where(TestResult.user_id == user.id)
        .order_by(desc(TestResult.created_at)).limit(14)
    ).all()
    chart_data = [{"date": r[0].strftime("%m-%d"), "pct": float(r[1])} for r in reversed(chart_rows)]

    streak = current_streak(db, user.id)
    subjects = list_subjects(db, user.id)

    return templates.TemplateResponse("main/dashboard.html", {
        "request": request,
        "user": user,
        "lang": user.language,
        "t": tt,
        "subjects": subjects,
        "stats": {
            "lessons": lessons_count,
            "tests": tests_count,
            "avg": round(float(avg_score), 1),
            "streak": streak,
            "unread": unread_notifications,
        },
        "recent_lessons": recent_lessons,
        "recent_notes": recent_notes,
        "recent_results": recent_results,
        "chart_data": chart_data,
    })

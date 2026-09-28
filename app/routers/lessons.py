from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Lesson, Question
from app.security.deps import get_current_user
from app.services import ai_service
from app.services.i18n import translator_for
from app.services.streaks import record_activity
from app.services.achievements import check_after_lesson
from app.services.notifications import notify

router = APIRouter(prefix="/lessons", tags=["lessons"])
templates = Jinja2Templates(directory="app/templates")


@router.post("/create")
def create_lesson(
    request: Request,
    subject: str = Form(...),
    topic: str = Form(...),
    content: str = Form(...),
    notes: str = Form(""),
    tutor_name: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lesson = Lesson(
        user_id=user.id,
        subject=subject.strip(),
        topic=topic.strip(),
        content=content.strip(),
        notes=notes.strip() or None,
        tutor_name=tutor_name.strip() or None,
        lesson_date=datetime.utcnow(),
        language=user.language,
        ai_status="pending",
    )
    db.add(lesson)
    db.flush()

    try:
        analysis = ai_service.analyze_lesson(subject, topic, content, notes, user.language)
        lesson.ai_summary = analysis.get("summary")
        lesson.ai_topics = analysis.get("topics", [])
        lesson.ai_status = "ok"
    except ai_service.AIUnavailable as e:
        lesson.ai_status = "failed"
        tt = translator_for(user.language)
        notify(db, user.id, "info", tt("ai_unavailable"), str(e)[:200])

    record_activity(db, user.id, lesson_inc=1)
    check_after_lesson(db, user)
    db.commit()

    return RedirectResponse(url=f"/lessons/{lesson.id}/review?lang={user.language}",
                            status_code=303)


@router.get("/{lesson_id}/review", response_class=HTMLResponse)
def review_lesson(lesson_id: int, request: Request,
                  db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    lesson = db.scalar(select(Lesson).where(
        Lesson.id == lesson_id, Lesson.user_id == user.id))
    if not lesson:
        return RedirectResponse(url=f"/?lang={user.language}", status_code=303)
    tt = translator_for(user.language)
    return templates.TemplateResponse("main/lesson_review.html", {
        "request": request, "user": user, "lang": user.language,
        "t": tt, "lesson": lesson,
    })


@router.post("/{lesson_id}/generate-test")
def generate_test(lesson_id: int, request: Request,
                  db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    lesson = db.scalar(select(Lesson).where(
        Lesson.id == lesson_id, Lesson.user_id == user.id))
    if not lesson:
        return RedirectResponse(url=f"/?lang={user.language}", status_code=303)

    existing = db.scalars(select(Question).where(Question.lesson_id == lesson.id)).all()
    if len(existing) == 10:
        return RedirectResponse(url=f"/tests/{lesson.id}/start?lang={user.language}",
                                status_code=303)

    # Delete any partial old questions
    for q in existing:
        db.delete(q)
    db.flush()

    try:
        qs = ai_service.generate_questions(
            lesson.subject, lesson.topic, lesson.content,
            lesson.ai_summary or lesson.topic, user.language,
        )
    except ai_service.AIUnavailable as e:
        tt = translator_for(user.language)
        logger_msg = f"generate-test failed for lesson {lesson.id}: {e}"
        import logging
        logging.getLogger("bilimai").error(logger_msg)
        return templates.TemplateResponse("main/lesson_review.html", {
            "request": request, "user": user, "lang": user.language,
            "t": tt, "lesson": lesson,
            "ai_error": f"{tt('ai_unavailable')} ({e})",
        }, status_code=503)

    for q in qs:
        db.add(Question(
            lesson_id=lesson.id,
            order_index=int(q["order_index"]),
            qtype=q.get("qtype", "mcq"),
            difficulty=q.get("difficulty", "medium"),
            question_text=q["question_text"],
            options=q.get("options"),
            correct_answer=str(q["correct_answer"]),
            explanation=q.get("explanation"),
        ))
    db.commit()
    return RedirectResponse(url=f"/tests/{lesson.id}/start?lang={user.language}",
                            status_code=303)


@router.get("/list", response_class=HTMLResponse)
def list_lessons(request: Request, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    tt = translator_for(user.language)
    lessons = db.scalars(
        select(Lesson).where(Lesson.user_id == user.id)
        .order_by(desc(Lesson.created_at)).limit(50)
    ).all()
    return templates.TemplateResponse("main/lessons_list.html", {
        "request": request, "user": user, "lang": user.language,
        "t": tt, "lessons": lessons,
    })

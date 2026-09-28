from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Lesson, Question, Answer, TestResult, Notification
from app.security.deps import get_current_user
from app.services import ai_service
from app.services.scoring import local_evaluate
from app.services.i18n import translator_for
from app.services.streaks import record_activity
from app.services.achievements import check_after_test
from app.services.notifications import notify

router = APIRouter(prefix="/tests", tags=["tests"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/{lesson_id}/start", response_class=HTMLResponse)
def start_test(lesson_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.user_id == user.id))
    if not lesson:
        return RedirectResponse(url=f"/?lang={user.language}", status_code=303)
    questions = db.scalars(select(Question).where(Question.lesson_id == lesson.id).order_by(Question.order_index)).all()
    if len(questions) != 10:
        return RedirectResponse(url=f"/lessons/{lesson.id}/review?lang={user.language}", status_code=303)
    tt = translator_for(user.language)
    return templates.TemplateResponse("main/test.html", {
        "request": request, "user": user, "lang": user.language, "t": tt,
        "lesson": lesson, "questions": questions,
    })


@router.post("/{lesson_id}/submit")
async def submit_test(lesson_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lesson = db.scalar(select(Lesson).where(Lesson.id == lesson_id, Lesson.user_id == user.id))
    if not lesson:
        return RedirectResponse(url=f"/?lang={user.language}", status_code=303)

    questions = db.scalars(select(Question).where(Question.lesson_id == lesson.id).order_by(Question.order_index)).all()
    if len(questions) != 10:
        return RedirectResponse(url=f"/lessons/{lesson.id}/review?lang={user.language}", status_code=303)

    form = await request.form()
    user_answers: dict[int, str] = {}
    for q in questions:
        key = f"q_{q.order_index}"
        user_answers[q.order_index] = str(form.get(key, "")).strip()

    # AI evaluation with local fallback
    try:
        eval_res = ai_service.evaluate_answers(
            {"subject": lesson.subject, "topic": lesson.topic, "content": lesson.content},
            [{"order_index": q.order_index, "question_text": q.question_text, "correct_answer": q.correct_answer} for q in questions],
            user_answers, user.language,
        )
    except ai_service.AIUnavailable:
        eval_res = local_evaluate(
            [{"order_index": q.order_index, "correct_answer": q.correct_answer, "explanation": q.explanation} for q in questions],
            user_answers,
        )

    # Save TestResult
    tr = TestResult(
        user_id=user.id,
        lesson_id=lesson.id,
        correct_count=int(eval_res.get("score", 0)),
        total_count=int(eval_res.get("total", 10)),
        percentage=float(eval_res.get("percentage", 0)),
        weak_concepts=eval_res.get("weak_concepts", []),
        strong_concepts=eval_res.get("strong_concepts", []),
        recommendations=eval_res.get("recommendations", ""),
        ai_analysis=eval_res.get("overall_analysis", ""),
    )
    db.add(tr)
    db.flush()

    per_q_map = {p["order_index"]: p for p in eval_res.get("per_question", [])}
    for q in questions:
        p = per_q_map.get(q.order_index, {"is_correct": False, "feedback": ""})
        db.add(Answer(
            question_id=q.id,
            test_result_id=tr.id,
            user_answer=user_answers[q.order_index],
            is_correct=bool(p.get("is_correct")),
            ai_feedback=p.get("feedback", ""),
        ))

    record_activity(db, user.id, test_inc=1, score=int(eval_res.get("score", 0)))
    check_after_test(db, user, float(eval_res.get("percentage", 0)))
    tt = translator_for(user.language)
    notify(db, user.id, "test", tt("tests_completed"), f"{tr.correct_count}/{tr.total_count} — {tr.percentage}%")
    db.commit()

    return RedirectResponse(url=f"/tests/result/{tr.id}?lang={user.language}", status_code=303)


@router.get("/result/{result_id}", response_class=HTMLResponse)
def view_result(result_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tr = db.scalar(select(TestResult).where(TestResult.id == result_id, TestResult.user_id == user.id))
    if not tr:
        return RedirectResponse(url=f"/?lang={user.language}", status_code=303)
    lesson = db.get(Lesson, tr.lesson_id)
    questions = db.scalars(select(Question).where(Question.lesson_id == lesson.id).order_by(Question.order_index)).all()
    answers = {a.question_id: a for a in db.scalars(select(Answer).where(Answer.test_result_id == tr.id)).all()}
    tt = translator_for(user.language)
    return templates.TemplateResponse("main/result.html", {
        "request": request, "user": user, "lang": user.language, "t": tt,
        "tr": tr, "lesson": lesson, "questions": questions, "answers": answers,
    })

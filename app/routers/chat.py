from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Lesson, AIConversation
from app.security.deps import get_current_user
from app.services import ai_service
from app.services.i18n import translator_for

router = APIRouter(prefix="/chat", tags=["chat"])
templates = Jinja2Templates(directory="app/templates")


def _parse_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


@router.get("", response_class=HTMLResponse)
def chat_page(request: Request, lesson_id: str = "",
              db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    tt = translator_for(user.language)
    lesson_id_int = _parse_int(lesson_id, 0)
    lessons = db.scalars(
        select(Lesson).where(Lesson.user_id == user.id)
        .order_by(desc(Lesson.created_at)).limit(50)
    ).all()
    conv = None
    if lesson_id_int:
        lesson = db.scalar(select(Lesson).where(
            Lesson.id == lesson_id_int, Lesson.user_id == user.id))
        if lesson:
            conv = db.scalar(
                select(AIConversation).where(
                    AIConversation.user_id == user.id,
                    AIConversation.lesson_id == lesson_id_int,
                ).order_by(desc(AIConversation.updated_at))
            )
    return templates.TemplateResponse("main/chat.html", {
        "request": request, "user": user, "lang": user.language, "t": tt,
        "lessons": lessons, "conv": conv, "lesson_id": lesson_id_int or "",
    })


@router.post("/send")
def chat_send(request: Request,
              message: str = Form(...),
              lesson_id: str = Form("0"),
              conversation_id: str = Form("0"),
              db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    tt = translator_for(user.language)
    lesson_id_int = _parse_int(lesson_id, 0)
    conv_id_int = _parse_int(conversation_id, 0)

    lesson = None
    if lesson_id_int:
        lesson = db.scalar(select(Lesson).where(
            Lesson.id == lesson_id_int, Lesson.user_id == user.id))

    conv = None
    if conv_id_int:
        conv = db.scalar(select(AIConversation).where(
            AIConversation.id == conv_id_int,
            AIConversation.user_id == user.id))
    if not conv:
        conv = AIConversation(
            user_id=user.id,
            lesson_id=lesson.id if lesson else None,
            title=(lesson.topic if lesson else "Chat"),
            messages=[],
        )
        db.add(conv)
        db.flush()

    msgs = list(conv.messages or [])
    msgs.append({"role": "user", "content": message})

    ctx = None
    if lesson:
        ctx = (f"Fan: {lesson.subject}\nMavzu: {lesson.topic}\n"
               f"Bilganlar: {lesson.content}\nXulosa: {lesson.ai_summary or ''}")

    try:
        reply = ai_service.ai_chat_reply(msgs, ctx, user.language)
    except ai_service.AIUnavailable as e:
        reply = f"{tt('ai_unavailable')}\n\n({e})"
    except Exception as e:
        reply = f"{tt('error')}: {e}"

    msgs.append({"role": "assistant", "content": reply})
    conv.messages = msgs
    db.commit()
    return RedirectResponse(
        url=f"/chat?lang={user.language}&lesson_id={lesson_id_int or ''}",
        status_code=303)

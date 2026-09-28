"""Protected admin panel. Separate login. Never exposes private user content."""
import secrets
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (User, Lesson, TestResult, Question, Answer, Note,
                        AIConversation, AuditLog)
from app.security.passwords import verify_password, hash_password
from app.security.sessions import encode_session, decode_session
from app.security.deps import require_admin
from app.services.i18n import translator_for

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, lang: str = "uz"):
    return templates.TemplateResponse("admin/login.html", {
        "request": request, "lang": lang, "t": translator_for(lang),
    })


@router.post("/login")
def login_admin(request: Request, username: str = Form(...), password: str = Form(...),
                db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == username, User.is_admin == True))
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("admin/login.html", {
            "request": request, "lang": "uz", "t": translator_for("uz"),
            "error": "Invalid admin credentials",
        }, status_code=403)
    token = encode_session({"uid": user.id, "admin": True})
    resp = RedirectResponse(url="/admin", status_code=303)
    resp.set_cookie(settings.SESSION_COOKIE_NAME, token, httponly=True,
                    samesite="lax", secure=settings.is_production, path="/",
                    max_age=settings.SESSION_MAX_AGE)
    db.add(AuditLog(actor_user_id=user.id, action="admin_login",
                    ip=request.client.host if request.client else None))
    db.commit()
    return resp


@router.get("", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    tt = translator_for(user.language)
    stats = {
        "users": db.scalar(select(func.count()).select_from(User).where(User.is_admin == False)) or 0,
        "active_users": db.scalar(select(func.count()).select_from(User).where(
            User.is_admin == False, User.is_active == True)) or 0,
        "lessons": db.scalar(select(func.count()).select_from(Lesson)) or 0,
        "tests": db.scalar(select(func.count()).select_from(TestResult)) or 0,
        "questions": db.scalar(select(func.count()).select_from(Question)) or 0,
        "answers": db.scalar(select(func.count()).select_from(Answer)) or 0,
        "notes": db.scalar(select(func.count()).select_from(Note)) or 0,
        "avg_score": round(float(db.scalar(select(func.avg(TestResult.percentage))) or 0), 1),
        "ai_conversations": db.scalar(select(func.count()).select_from(AIConversation)) or 0,
    }
    recent_audit = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(30)).all()
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "user": user, "lang": user.language, "t": tt,
        "stats": stats, "recent_audit": recent_audit,
    })

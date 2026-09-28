from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, UserSettings, TestResult, Lesson, Note, Achievement, Notification
from app.security.deps import get_current_user
from app.security.passwords import hash_password, verify_password
from app.services.i18n import translator_for, SUPPORTED_LANGUAGES
from app.services.streaks import current_streak

router = APIRouter(prefix="/profile", tags=["profile"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def profile(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tt = translator_for(user.language)
    settings_row = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    if not settings_row:
        settings_row = UserSettings(user_id=user.id)
        db.add(settings_row)
        db.commit()
    achievements = db.scalars(select(Achievement).where(Achievement.user_id == user.id).order_by(Achievement.unlocked_at.desc())).all()
    stats = {
        "lessons": db.scalar(select(func.count()).select_from(Lesson).where(Lesson.user_id == user.id)) or 0,
        "tests": db.scalar(select(func.count()).select_from(TestResult).where(TestResult.user_id == user.id)) or 0,
        "avg": round(float(db.scalar(select(func.avg(TestResult.percentage)).where(TestResult.user_id == user.id)) or 0), 1),
        "streak": current_streak(db, user.id),
    }
    return templates.TemplateResponse("main/profile.html", {
        "request": request, "user": user, "lang": user.language, "t": tt,
        "settings_row": settings_row, "achievements": achievements, "stats": stats,
        "languages": SUPPORTED_LANGUAGES,
    })


@router.post("/settings")
def update_settings(request: Request, language: str = Form("uz"), theme: str = Form("dark"),
                    auto_save_notes: str = Form("off"), notify_tests: str = Form("off"),
                    notify_revision: str = Form("off"), notify_streak: str = Form("off"),
                    notify_weak_topics: str = Form("off"),
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if language not in SUPPORTED_LANGUAGES:
        language = "uz"
    user.language = language
    user.theme = "dark" if theme == "dark" else "light"

    s = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    if not s:
        s = UserSettings(user_id=user.id); db.add(s); db.flush()
    s.auto_save_notes = auto_save_notes == "on"
    s.notify_tests = notify_tests == "on"
    s.notify_revision = notify_revision == "on"
    s.notify_streak = notify_streak == "on"
    s.notify_weak_topics = notify_weak_topics == "on"
    db.commit()
    return RedirectResponse(url=f"/profile?lang={language}", status_code=303)


@router.post("/change-password")
def change_password(request: Request, old_password: str = Form(...), new_password: str = Form(...),
                    new_password_confirm: str = Form(...), db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    tt = translator_for(user.language)
    if not verify_password(old_password, user.password_hash):
        return RedirectResponse(url=f"/profile?lang={user.language}&error=pw", status_code=303)
    if new_password != new_password_confirm or len(new_password) < 8:
        return RedirectResponse(url=f"/profile?lang={user.language}&error=pw2", status_code=303)
    user.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse(url=f"/profile?lang={user.language}&ok=1", status_code=303)


@router.post("/delete-account")
def delete_account(request: Request, password: str = Form(...),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(password, user.password_hash):
        return RedirectResponse(url=f"/profile?lang={user.language}&error=pw", status_code=303)
    db.delete(user)
    db.commit()
    resp = RedirectResponse(url="/auth/login", status_code=303)
    resp.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    return resp

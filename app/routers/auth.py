from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, UserSettings, AuditLog
from app.security.passwords import hash_password, verify_password
from app.security.sessions import encode_session
from app.services.i18n import t, SUPPORTED_LANGUAGES, translator_for
from app.services.subjects import ensure_default_subjects

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


def _set_session_cookie(resp: RedirectResponse | JSONResponse, user_id: int) -> None:
    token = encode_session({"uid": user_id})
    resp.set_cookie(
        settings.SESSION_COOKIE_NAME,
        token,
        max_age=settings.SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request, lang: str = "uz"):
    _ = translator_for(lang)
    return templates.TemplateResponse("auth/register.html", {
        "request": request, "lang": lang, "t": translator_for(lang),
    })


@router.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    language: str = Form("uz"),
    db: Session = Depends(get_db),
):
    if language not in SUPPORTED_LANGUAGES:
        language = "uz"
    tt = translator_for(language)

    if password != password_confirm:
        return templates.TemplateResponse("auth/register.html", {
            "request": request, "lang": language, "t": tt, "error": tt("error") + ": password mismatch",
        }, status_code=400)
    if len(password) < 8:
        return templates.TemplateResponse("auth/register.html", {
            "request": request, "lang": language, "t": tt, "error": tt("error") + ": password too short (min 8)",
        }, status_code=400)

    email = email.strip().lower()
    username = username.strip()

    existing = db.scalar(select(User).where(or_(User.email == email, User.username == username)))
    if existing:
        return templates.TemplateResponse("auth/register.html", {
            "request": request, "lang": language, "t": tt, "error": tt("error") + ": user already exists",
        }, status_code=400)

    user = User(email=email, username=username, password_hash=hash_password(password), language=language)
    db.add(user)
    db.flush()
    db.add(UserSettings(user_id=user.id))
    ensure_default_subjects(db, user.id)
    db.add(AuditLog(actor_user_id=user.id, action="register", ip=request.client.host if request.client else None))
    db.commit()

    resp = RedirectResponse(url=f"/?lang={language}", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(resp, user.id)
    return resp


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, lang: str = "uz"):
    return templates.TemplateResponse("auth/login.html", {
        "request": request, "lang": lang, "t": translator_for(lang),
    })


@router.post("/login")
def login(
    request: Request,
    login_id: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    login_id = login_id.strip().lower()
    user = db.scalar(select(User).where(or_(User.email == login_id, User.username == login_id)))
    if not user or not verify_password(password, user.password_hash) or not user.is_active:
        lang = user.language if user else "uz"
        return templates.TemplateResponse("auth/login.html", {
            "request": request, "lang": lang, "t": translator_for(lang),
            "error": translator_for(lang)("error") + ": invalid credentials",
        }, status_code=400)

    user.last_login = datetime.utcnow()
    db.add(AuditLog(actor_user_id=user.id, action="login", ip=request.client.host if request.client else None))
    db.commit()

    resp = RedirectResponse(url=f"/?lang={user.language}", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(resp, user.id)
    return resp


@router.post("/logout")
@router.get("/logout")
def logout(request: Request):
    lang = request.query_params.get("lang", "uz")
    resp = RedirectResponse(url=f"/auth/login?lang={lang}", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    return resp

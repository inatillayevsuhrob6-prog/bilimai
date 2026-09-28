from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Achievement
from app.security.deps import get_current_user
from app.services.i18n import translator_for

router = APIRouter(prefix="/achievements", tags=["achievements"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tt = translator_for(user.language)
    rows = db.scalars(select(Achievement).where(Achievement.user_id == user.id).order_by(Achievement.unlocked_at.desc())).all()
    return templates.TemplateResponse("main/achievements.html", {
        "request": request, "user": user, "lang": user.language, "t": tt, "achievements": rows,
    })

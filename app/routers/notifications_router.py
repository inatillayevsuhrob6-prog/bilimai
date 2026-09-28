from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Notification
from app.security.deps import get_current_user
from app.services.i18n import translator_for

router = APIRouter(prefix="/notifications", tags=["notifications"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tt = translator_for(user.language)
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(desc(Notification.created_at)).limit(100)).all()
    return templates.TemplateResponse("main/notifications.html", {
        "request": request, "user": user, "lang": user.language, "t": tt, "notifications": rows,
    })


@router.post("/read-all")
def read_all(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    for n in db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.is_read == False)).all():
        n.is_read = True
    db.commit()
    return RedirectResponse(url=f"/notifications?lang={user.language}", status_code=303)

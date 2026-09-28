from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc, asc, or_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Note
from app.security.deps import get_current_user
from app.services.i18n import translator_for
from app.services.subjects import list_subjects

router = APIRouter(prefix="/notebook", tags=["notebook"])
templates = Jinja2Templates(directory="app/templates")

COLORS = ["violet", "pink", "cyan", "amber", "emerald", "rose", "slate"]
FONTS = ["normal", "bold", "italic", "handwritten", "code"]
PRIORITIES = ["low", "normal", "high", "urgent"]


@router.get("", response_class=HTMLResponse)
def index(request: Request, q: str = "", subject: str = "", fav: str = "",
          sort: str = "new", color: str = "", priority: str = "",
          db: Session = Depends(get_db),
          user: User = Depends(get_current_user)):
    tt = translator_for(user.language)
    stmt = select(Note).where(Note.user_id == user.id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Note.title.ilike(like), Note.body.ilike(like),
                              Note.category.ilike(like)))
    if subject:
        stmt = stmt.where(Note.subject == subject)
    if fav == "1":
        stmt = stmt.where(Note.is_favorite == True)
    if color:
        stmt = stmt.where(Note.color == color)
    if priority:
        stmt = stmt.where(Note.priority == priority)

    if sort == "old":
        stmt = stmt.order_by(asc(Note.created_at))
    elif sort == "title":
        stmt = stmt.order_by(asc(Note.title))
    else:
        stmt = stmt.order_by(desc(Note.is_pinned), desc(Note.updated_at))

    notes = db.scalars(stmt.limit(200)).all()

    total = db.scalar(select(func.count()).select_from(Note).where(Note.user_id == user.id)) or 0
    fav_count = db.scalar(select(func.count()).select_from(Note).where(
        Note.user_id == user.id, Note.is_favorite == True)) or 0
    pinned_count = db.scalar(select(func.count()).select_from(Note).where(
        Note.user_id == user.id, Note.is_pinned == True)) or 0

    return templates.TemplateResponse("main/notebook.html", {
        "request": request, "user": user, "lang": user.language, "t": tt,
        "notes": notes, "q": q, "subject_filter": subject, "fav": fav,
        "sort": sort, "color_filter": color, "priority_filter": priority,
        "subjects": list_subjects(db, user.id),
        "colors": COLORS, "fonts": FONTS, "priorities": PRIORITIES,
        "stats": {"total": total, "fav": fav_count, "pinned": pinned_count},
    })


@router.post("/create")
def create(request: Request,
           title: str = Form(...), body: str = Form(...),
           subject: str = Form(""), tags: str = Form(""),
           category: str = Form(""),
           color: str = Form("violet"),
           font_style: str = Form("normal"),
           priority: str = Form("normal"),
           is_favorite: str = Form(""),
           db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    tags_list = [x.strip() for x in tags.split(",") if x.strip()] if tags else []
    if color not in COLORS: color = "violet"
    if font_style not in FONTS: font_style = "normal"
    if priority not in PRIORITIES: priority = "normal"
    db.add(Note(
        user_id=user.id,
        title=title.strip(), body=body.strip(),
        subject=subject.strip() or None,
        tags=tags_list,
        category=category.strip() or None,
        color=color, font_style=font_style, priority=priority,
        is_favorite=(is_favorite == "on"),
    ))
    db.commit()
    return RedirectResponse(url=f"/notebook?lang={user.language}", status_code=303)


@router.post("/{note_id}/update")
def update(note_id: int, request: Request,
           title: str = Form(...), body: str = Form(...),
           subject: str = Form(""), tags: str = Form(""),
           category: str = Form(""),
           color: str = Form("violet"),
           font_style: str = Form("normal"),
           priority: str = Form("normal"),
           is_favorite: str = Form(""),
           db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    note = db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user.id))
    if note:
        note.title = title.strip()
        note.body = body.strip()
        note.subject = subject.strip() or None
        note.tags = [x.strip() for x in tags.split(",") if x.strip()] if tags else []
        note.category = category.strip() or None
        if color in COLORS: note.color = color
        if font_style in FONTS: note.font_style = font_style
        if priority in PRIORITIES: note.priority = priority
        note.is_favorite = (is_favorite == "on")
        db.commit()
    return RedirectResponse(url=f"/notebook?lang={user.language}", status_code=303)


@router.post("/{note_id}/toggle-fav")
def toggle_fav(note_id: int, request: Request, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    note = db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user.id))
    if note:
        note.is_favorite = not note.is_favorite
        db.commit()
    return RedirectResponse(url=f"/notebook?lang={user.language}", status_code=303)


@router.post("/{note_id}/toggle-pin")
def toggle_pin(note_id: int, request: Request, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    note = db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user.id))
    if note:
        note.is_pinned = not note.is_pinned
        db.commit()
    return RedirectResponse(url=f"/notebook?lang={user.language}", status_code=303)


@router.post("/{note_id}/delete")
def delete(note_id: int, request: Request, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    note = db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user.id))
    if note:
        db.delete(note)
        db.commit()
    return RedirectResponse(url=f"/notebook?lang={user.language}", status_code=303)

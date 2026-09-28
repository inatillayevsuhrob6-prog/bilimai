"""Subject defaults and per-user subject helpers."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Subject

DEFAULT_SUBJECTS = [
    "Matematika", "Fizika", "Kimyo", "Biologiya", "Tarix",
    "Geografiya", "Ingliz tili", "Rus tili", "O'zbek tili",
    "Dasturlash", "Adabiyot", "Boshqa",
]


def ensure_default_subjects(db: Session, user_id: int) -> None:
    existing = db.scalars(select(Subject.name).where(Subject.user_id == user_id)).all()
    existing_set = set(existing)
    for name in DEFAULT_SUBJECTS:
        if name not in existing_set:
            db.add(Subject(user_id=user_id, name=name, is_custom=False))
    db.flush()


def list_subjects(db: Session, user_id: int) -> list[str]:
    return list(db.scalars(select(Subject.name).where(Subject.user_id == user_id).order_by(Subject.name)).all())

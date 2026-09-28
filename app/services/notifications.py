from sqlalchemy.orm import Session
from app.models import Notification


def notify(db: Session, user_id: int, kind: str, title: str, body: str | None = None) -> None:
    db.add(Notification(user_id=user_id, kind=kind, title=title, body=body))
    db.flush()

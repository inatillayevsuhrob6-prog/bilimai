"""FastAPI dependencies for auth, ownership checks, CSRF, rate-limit."""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.security.sessions import decode_session


def _get_session_token(request: Request) -> str | None:
    return request.cookies.get(settings.SESSION_COOKIE_NAME)


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = _get_session_token(request)
    if not token:
        return None
    data = decode_session(token)
    if not data:
        return None
    uid = data.get("uid")
    if not uid:
        return None
    user = db.get(User, uid)
    if not user or not user.is_active:
        return None
    return user


def get_current_user(user: User | None = Depends(get_current_user_optional)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/auth/login"},
            detail="Not authenticated",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def assert_owner(resource_user_id: int, user: User) -> None:
    """Raise 404 if the resource does not belong to the current user."""
    if resource_user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

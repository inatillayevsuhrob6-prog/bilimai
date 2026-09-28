"""Simple double-submit CSRF token utility tied to the session."""
import hmac
import hashlib
import secrets
from app.config import settings


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_signature(token: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()


def verify_csrf(form_token: str | None, cookie_token: str | None) -> bool:
    if not form_token or not cookie_token:
        return False
    return hmac.compare_digest(form_token, cookie_token)

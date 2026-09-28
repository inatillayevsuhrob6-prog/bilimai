"""Signed-cookie session helpers using itsdangerous."""
from typing import Any
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from app.config import settings

_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="bilimai-session")


def encode_session(data: dict[str, Any]) -> str:
    return _serializer.dumps(data)


def decode_session(token: str, max_age: int | None = None) -> dict[str, Any] | None:
    try:
        return _serializer.loads(token, max_age=max_age or settings.SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None

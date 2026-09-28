"""BilimAI FastAPI entrypoint — production-ready."""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select

from app.config import settings
from app.database import init_db, SessionLocal
from app.models import User
from app.routers import (auth, dashboard, lessons, tests, notebook, profile,
                         analytics, chat, achievements_router,
                         notifications_router, admin)
from app.security.sessions import decode_session
from app.services.i18n import SUPPORTED_LANGUAGES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("bilimai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.exception("Database init failed: %s", e)
    logger.info("BilimAI started in %s mode", settings.APP_ENV)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url=None,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data:;"
        )
        return response


class LanguageSyncMiddleware(BaseHTTPMiddleware):
    """Persist ?lang=xx to user profile for logged-in users."""
    async def dispatch(self, request: Request, call_next):
        lang = request.query_params.get("lang")
        if lang and lang in SUPPORTED_LANGUAGES:
            token = request.cookies.get(settings.SESSION_COOKIE_NAME)
            if token:
                data = decode_session(token)
                if data and data.get("uid"):
                    db = SessionLocal()
                    try:
                        u = db.scalar(select(User).where(User.id == data["uid"]))
                        if u and u.language != lang:
                            u.language = lang
                            db.commit()
                    except Exception as e:
                        logger.warning("Lang sync failed: %s", e)
                    finally:
                        db.close()
        return await call_next(request)


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LanguageSyncMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    same_site="lax",
    https_only=settings.is_production,
)

# Static files
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
except Exception as e:
    logger.warning("Static mount failed: %s", e)

templates = Jinja2Templates(directory="app/templates")

# Routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(lessons.router)
app.include_router(tests.router)
app.include_router(notebook.router)
app.include_router(profile.router)
app.include_router(analytics.router)
app.include_router(chat.router)
app.include_router(achievements_router.router)
app.include_router(notifications_router.router)
app.include_router(admin.router)


@app.get("/healthz")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

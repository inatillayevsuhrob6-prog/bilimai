"""Bootstrap admin account using ADMIN_USERNAME/ADMIN_PASSWORD env vars.
Safe to re-run: updates password if admin already exists.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import init_db, SessionLocal
from app.models import User, UserSettings
from app.security.passwords import hash_password
from app.config import settings
from app.services.subjects import ensure_default_subjects


def main():
    init_db()
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.username == settings.ADMIN_USERNAME))
        if existing:
            existing.password_hash = hash_password(settings.ADMIN_PASSWORD)
            existing.is_admin = True
            existing.is_active = True
            print(f"[+] Admin '{settings.ADMIN_USERNAME}' password updated.")
        else:
            admin = User(
                email=settings.ADMIN_EMAIL,
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                language="uz",
                is_admin=True,
            )
            db.add(admin)
            db.flush()
            db.add(UserSettings(user_id=admin.id))
            ensure_default_subjects(db, admin.id)
            print(f"[+] Admin '{settings.ADMIN_USERNAME}' created.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()

from tests.conftest import *
from app.database import SessionLocal
from app.models import User, Lesson


def _register(client, email, username):
    return client.post("/auth/register", data={
        "email": email, "username": username,
        "password": "password123", "password_confirm": "password123",
        "language": "en",
    }, follow_redirects=False)


def test_user_cannot_access_other_users_lesson(client):
    # user A
    _register(client, "a@example.com", "alice")
    # manually insert a lesson for A
    db = SessionLocal()
    a = db.query(User).filter_by(username="alice").first()
    lesson = Lesson(user_id=a.id, subject="Math", topic="A's lesson", content="x")
    db.add(lesson); db.commit()
    a_lesson_id = lesson.id
    db.close()

    client.cookies.clear()
    # user B
    _register(client, "b@example.com", "bob")

    r = client.get(f"/lessons/{a_lesson_id}/review", follow_redirects=False)
    # B should be redirected — lesson not found for them
    assert r.status_code == 303
    assert r.headers["location"].startswith("/?lang=")

    r = client.post(f"/tests/{a_lesson_id}/submit", data={}, follow_redirects=False)
    assert r.status_code == 303

from tests.conftest import *


def test_create_note(client):
    client.post("/auth/register", data={
        "email": "n@example.com", "username": "noteuser",
        "password": "password123", "password_confirm": "password123",
        "language": "en",
    }, follow_redirects=False)
    r = client.post("/notebook/create", data={"title": "My note", "body": "Hello"}, follow_redirects=False)
    assert r.status_code == 303
    r = client.get("/notebook")
    assert b"My note" in r.content

from tests.conftest import *


def test_register_login_logout(client):
    r = client.post("/auth/register", data={
        "email": "u1@example.com", "username": "u1",
        "password": "password123", "password_confirm": "password123",
        "language": "uz",
    }, follow_redirects=False)
    assert r.status_code == 303
    assert client.cookies.get("bilimai_session")

    r = client.get("/?lang=uz")
    assert r.status_code == 200

    r = client.post("/auth/logout", follow_redirects=False)
    assert r.status_code == 303
    assert not client.cookies.get("bilimai_session")


def test_login_wrong_password(client):
    r = client.post("/auth/register", data={
        "email": "u2@example.com", "username": "u2",
        "password": "password123", "password_confirm": "password123",
        "language": "en",
    }, follow_redirects=False)
    assert r.status_code == 303
    client.cookies.clear()

    r = client.post("/auth/login", data={"login_id": "u2", "password": "wrong"})
    assert r.status_code == 400

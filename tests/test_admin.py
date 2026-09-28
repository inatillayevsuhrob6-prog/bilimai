from tests.conftest import *
from scripts.create_admin import main as create_admin_main


def test_admin_login(client):
    create_admin_main()
    r = client.post("/admin/login", data={"username": "admin", "password": "12admin"},
                    follow_redirects=False)
    assert r.status_code == 303
    r = client.get("/admin")
    assert r.status_code == 200
    assert "Admin Dashboard" in r.text

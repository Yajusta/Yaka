import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from httpx import AsyncClient, ASGITransport
    from asgi_lifespan import LifespanManager
except Exception:
    pytest.skip("httpx or asgi_lifespan not installed in test environment", allow_module_level=True)

from app.main import app
from app.database import SessionLocal
from app.services.user import get_user_by_email
from app.services import email as email_service


@pytest.mark.asyncio
async def test_invite_and_set_password(monkeypatch):
    captured = {}

    def fake_send_invitation(email, display_name, token):
        captured["email"] = email
        captured["display_name"] = display_name
        captured["token"] = token

    monkeypatch.setattr(email_service, "send_invitation", fake_send_invitation)

    db = SessionLocal()
    existing = get_user_by_email(db, "invitee@example.com")
    if existing:
        db.delete(existing)
        db.commit()

    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Authenticate as default admin created on startup
            resp_login = await client.post(
                "/auth/login", data={"username": "admin@yaka.local", "password": "admin123"}
            )
            assert resp_login.status_code == 200
            token = resp_login.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            resp = await client.post(
                "/users/invite",
                json={"email": "invitee@example.com", "display_name": "Invité", "role": "user"},
                headers=headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["email"] == "invitee@example.com"

            assert "token" in captured
            token = captured["token"]

            resp2 = await client.post("/users/set-password", json={"token": token, "password": "secret123"})
            assert resp2.status_code == 200
            assert resp2.json()["message"] == "Mot de passe défini avec succès"

            resp3 = await client.post("/auth/login", data={"username": "invitee@example.com", "password": "secret123"})
            assert resp3.status_code == 200
            assert "access_token" in resp3.json()

    # Cleanup
    user = get_user_by_email(db, "invitee@example.com")
    if user:
        db.delete(user)
        db.commit()
    db.close()

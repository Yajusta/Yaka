"""Integration tests for the invite and password setup flow."""

import pytest
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router


@pytest.mark.asyncio
async def test_invite_and_set_password(async_client_factory, seed_admin_user, login_user, monkeypatch):
    """Test du flux complet d'invitation et de définition du mot de passe."""
    seed_admin_user()

    # Capturer le token d'invitation envoyé par email
    captured = {}

    def fake_send_invitation(email, display_name, token, board_uid=None):
        captured["email"] = email
        captured["display_name"] = display_name
        captured["token"] = token

    # Patcher l'envoi d'email aux deux endroits (module source et référence dans user.py)
    monkeypatch.setattr("app.services.email.send_invitation", fake_send_invitation)
    monkeypatch.setattr("app.services.user.email_service.send_invitation", fake_send_invitation)

    async with async_client_factory(auth_router, users_router) as client:
        # 1. L'admin se connecte
        admin_token = await login_user(client, "admin@yaka.local", "Admin123")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. L'admin invite un nouvel utilisateur
        invite_response = await client.post(
            "/users/invite",
            json={"email": "invitee@example.com", "display_name": "Invité", "role": "editor"},
            headers=admin_headers,
        )
        assert invite_response.status_code == 200
        invite_data = invite_response.json()
        assert invite_data["email"] == "invitee@example.com"
        assert invite_data["display_name"] == "Invité"

        # 3. Vérifier que l'email d'invitation a été envoyé avec un token
        assert "token" in captured
        assert captured["email"] == "invitee@example.com"
        assert captured["display_name"] == "Invité"
        invite_token = captured["token"]

        # 4. L'invité définit son mot de passe avec le token
        set_password_response = await client.post(
            "/users/set-password",
            json={"token": invite_token, "password": "SecurePass123!"},
        )
        assert set_password_response.status_code == 200
        assert set_password_response.json()["message"] == "Mot de passe défini avec succès"

        # 5. L'invité peut maintenant se connecter avec son mot de passe
        login_response = await client.post(
            "/auth/login",
            data={"username": "invitee@example.com", "password": "SecurePass123!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        assert login_data["token_type"] == "bearer"

        # 6. Vérifier que l'invité peut accéder à son profil
        invitee_token = login_data["access_token"]
        me_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {invitee_token}"},
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == "invitee@example.com"
        assert me_data["display_name"] == "Invité"
        assert me_data["role"] == "editor"

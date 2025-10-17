"""Integration tests for the auth router."""

import pytest
from app.routers.auth import router as auth_router


@pytest.mark.asyncio
async def test_login_and_me(async_client_factory, seed_admin_user):
    seed_admin_user()

    async with async_client_factory(auth_router) as client:
        login_response = await client.post(
            "/auth/login",
            data={"username": "admin@yaka.local", "password": "Admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        payload = login_response.json()
        assert payload["token_type"] == "bearer"

        token = payload["access_token"]
        me_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        me_payload = me_response.json()
        assert me_payload["email"] == "admin@yaka.local"

        logout_response = await client.post("/auth/logout")
        assert logout_response.status_code == 200


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client_factory, seed_admin_user):
    seed_admin_user()

    async with async_client_factory(auth_router) as client:
        invalid_response = await client.post(
            "/auth/login",
            data={"username": "admin@yaka.local", "password": "wrong"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert invalid_response.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_request(async_client_factory, seed_admin_user):
    seed_admin_user()

    async with async_client_factory(auth_router) as client:
        reset_response = await client.post(
            "/auth/request-password-reset",
            json={"email": "admin@yaka.local"},
        )
        assert reset_response.status_code == 200
        assert "message" in reset_response.json()


@pytest.mark.asyncio
async def test_password_reset_request_invited_user(async_client_factory, seed_admin_user, integration_session_factory):
    """Test password reset request for an invited (non-activated) user.
    
    When a user who hasn't validated their invitation requests a password reset,
    they should receive a new invitation email instead of a reset email.
    This allows users who lost their invitation email to receive it again.
    """
    seed_admin_user()
    
    # Create an invited user
    from app.services.user import invite_user
    from app.models.user import UserRole
    
    session = integration_session_factory()
    try:
        invited_user = invite_user(
            session,
            email="invited@example.com",
            display_name="Invited User",
            role=UserRole.EDITOR
        )
        invited_email = invited_user.email
        original_token = invited_user.invite_token
    finally:
        session.close()
    
    async with async_client_factory(auth_router) as client:
        # Request password reset for invited user
        reset_response = await client.post(
            "/auth/request-password-reset",
            json={"email": invited_email},
        )
        assert reset_response.status_code == 200
        assert "message" in reset_response.json()
        
        # Verify the user received a new token (simulating invitation resend)
        session = integration_session_factory()
        try:
            from app.services.user import get_user_by_email
            from app.models.user import UserStatus
            
            updated_user = get_user_by_email(session, invited_email)
            assert updated_user is not None
            assert updated_user.status == UserStatus.INVITED  # Status should remain INVITED
            assert updated_user.invite_token is not None
            assert updated_user.invite_token != original_token  # Token should be refreshed
        finally:
            session.close()

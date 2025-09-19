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

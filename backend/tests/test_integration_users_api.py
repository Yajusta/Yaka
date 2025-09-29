"""Integration tests for the users router."""

import pytest
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router


@pytest.mark.asyncio
async def test_users_listing_hides_emails_for_non_admins(
    async_client_factory, seed_admin_user, create_regular_user, login_user
):
    seed_admin_user()
    create_regular_user("member@example.com", "Userpass123", display_name="Member")

    async with async_client_factory(auth_router, users_router) as client:
        admin_token = await login_user(client, "admin@yaka.local", "Admin123")
        admin_response = await client.get(
            "/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_response.status_code == 200
        admin_payload = admin_response.json()
        member_entry = next(user for user in admin_payload if user["display_name"] == "Member")
        assert member_entry["email"] == "member@example.com"

        user_token = await login_user(client, "member@example.com", "Userpass123")
        user_response = await client.get(
            "/users/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert user_response.status_code == 200
        user_payload = user_response.json()
        member_for_user = next(user for user in user_payload if user["display_name"] == "Member")
        assert member_for_user["email"] is None


@pytest.mark.asyncio
async def test_user_management_requires_admin(async_client_factory, seed_admin_user, create_regular_user, login_user):
    seed_admin_user()
    create_regular_user("observer@example.com", "Observer123", display_name="Observer")

    async with async_client_factory(auth_router, users_router) as client:
        admin_token = await login_user(client, "admin@yaka.local", "Admin123")
        payload = {
            "email": "new.user@example.com",
            "password": "Password123!",
            "display_name": "New User",
            "role": "user",
            "language": "fr",
        }
        create_response = await client.post(
            "/users/",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_response.status_code == 200
        created_user = create_response.json()
        assert created_user["email"] == payload["email"]

        # Duplicate should fail
        duplicate_response = await client.post(
            "/users/",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert duplicate_response.status_code == 400

        # Non-admin cannot create a user
        user_token = await login_user(client, "observer@example.com", "Observer123")
        forbidden_response = await client.post(
            "/users/",
            json={
                "email": "should.fail@example.com",
                "password": "Fail123!",
                "display_name": "Should Fail",
                "role": "user",
                "language": "fr",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert forbidden_response.status_code == 403


@pytest.mark.asyncio
async def test_user_can_update_language(async_client_factory, seed_admin_user, create_regular_user, login_user):
    seed_admin_user()
    create_regular_user("languser@example.com", "Langpass123", display_name="Lang User")

    async with async_client_factory(auth_router, users_router) as client:
        token = await login_user(client, "languser@example.com", "Langpass123")
        update_response = await client.put(
            "/users/me/language",
            json={"language": "en"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["language"] == "en"

        invalid_response = await client.put(
            "/users/me/language",
            json={"language": "es"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert invalid_response.status_code == 400

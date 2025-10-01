"""Integration tests for board settings endpoints using an isolated SQLite database."""

import pytest
from app.routers.auth import router as auth_router
from app.routers.board_settings import router as board_settings_router
from app.services.board_settings import DEFAULT_BOARD_TITLE


@pytest.mark.asyncio
async def test_public_endpoint_returns_default_title(async_client_factory):
    """The public endpoint should expose the default board title when no value is stored."""
    async with async_client_factory(auth_router, board_settings_router) as client:
        response = await client.get("/board-settings/title")
    assert response.status_code == 200
    assert response.json() == {"title": DEFAULT_BOARD_TITLE}


@pytest.mark.asyncio
async def test_admin_can_update_board_title(async_client_factory, seed_admin_user, login_user):
    seed_admin_user()

    async with async_client_factory(auth_router, board_settings_router) as client:
        token = await login_user(client, "admin@yaka.local", "Admin123")
        new_title = "Kanban equipe"

        update_response = await client.put(
            "/board-settings/title",
            json={"title": new_title},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert update_response.status_code == 200
        payload = update_response.json()
        assert payload["setting_key"] == "board_title"
        assert payload["setting_value"] == new_title

        title_response = await client.get(
            "/board-settings/title",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert title_response.status_code == 200
        assert title_response.json() == {"title": new_title}


@pytest.mark.asyncio
async def test_non_admin_cannot_update_board_settings(
    async_client_factory, seed_admin_user, create_regular_user, login_user
):
    seed_admin_user()
    create_regular_user("user@example.com", "Userpass123")

    async with async_client_factory(auth_router, board_settings_router) as client:
        user_token = await login_user(client, "user@example.com", "Userpass123")

        forbidden_response = await client.put(
            "/board-settings/title",
            json={"title": "Essai"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert forbidden_response.status_code == 403
    detail = forbidden_response.json().get("detail")
    assert isinstance(detail, str)


@pytest.mark.asyncio
async def test_admin_can_list_settings(async_client_factory, seed_admin_user, login_user):
    seed_admin_user()

    async with async_client_factory(auth_router, board_settings_router) as client:
        token = await login_user(client, "admin@yaka.local", "Admin123")

        response = await client.get(
            "/board-settings/",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    settings = response.json()
    assert isinstance(settings, list)
    assert any(setting["setting_key"] == "board_title" for setting in settings)

"""Tests for AI features availability endpoint."""

import pytest

from app.routers.auth import router as auth_router


@pytest.mark.asyncio
async def test_ai_features_endpoint_returns_correct_structure(async_client_factory):
    """Test that the AI features endpoint returns the expected structure."""
    async with async_client_factory(auth_router) as client:
        response = await client.get("/auth/ai-features")
        assert response.status_code == 200
        data = response.json()
        assert "ai_available" in data
        assert isinstance(data["ai_available"], bool)

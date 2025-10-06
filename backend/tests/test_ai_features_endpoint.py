"""Tests for AI features availability endpoint."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, base_url="http://localhost")


def test_ai_features_endpoint_returns_correct_structure():
    """Test that the AI features endpoint returns the expected structure."""
    response = client.get("/auth/ai-features")
    assert response.status_code == 200
    data = response.json()
    assert "ai_available" in data
    assert isinstance(data["ai_available"], bool)

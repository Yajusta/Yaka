"""Tests du durcissement HTTP : origines CORS et documentation de l'API."""

import pytest
from app.utils.http_config import build_allowed_origins, docs_urls, is_development
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def clean_env(monkeypatch):
    for name in (
        "ENVIRONMENT",
        "BASE_URL",
        "BASE_URL_MOBILE",
        "ALLOWED_ORIGINS",
        "MOBILE_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


class TestEnvironment:
    @pytest.mark.parametrize(
        "value", ["development", " Development ", '"development"', "'development'"]
    )
    def test_development_is_recognized(self, clean_env, value):
        clean_env.setenv("ENVIRONMENT", value)
        assert is_development()

    @pytest.mark.parametrize(
        "value",
        [None, "production", "prod", "staging", "", "production  # values: x", "dev"],
    )
    def test_anything_else_is_production(self, clean_env, value):
        if value is not None:
            clean_env.setenv("ENVIRONMENT", value)
        assert not is_development()


class TestAllowedOrigins:
    def test_empty_allowed_origins_adds_no_empty_origin(self, clean_env):
        clean_env.setenv("ALLOWED_ORIGINS", "")
        assert "" not in build_allowed_origins()

    def test_blank_entries_are_ignored_and_trimmed(self, clean_env):
        clean_env.setenv("ALLOWED_ORIGINS", " https://a.example ,, ,https://b.example,")
        clean_env.setenv("MOBILE_ORIGINS", ",")
        origins = build_allowed_origins()
        assert "" not in origins
        assert "https://a.example" in origins
        assert "https://b.example" in origins

    def test_duplicates_are_removed(self, clean_env):
        clean_env.setenv("BASE_URL", "https://yaka.example")
        clean_env.setenv("ALLOWED_ORIGINS", "https://yaka.example")
        assert build_allowed_origins().count("https://yaka.example") == 1

    def test_no_localhost_mobile_origin_in_production(self, clean_env):
        clean_env.setenv("ENVIRONMENT", "production")
        origins = build_allowed_origins()
        assert "http://localhost" not in origins
        assert "capacitor://localhost" in origins
        assert "file://" not in origins

    def test_production_is_the_default(self, clean_env):
        assert "http://localhost" not in build_allowed_origins()

    def test_unknown_environment_is_production(self, clean_env):
        clean_env.setenv("ENVIRONMENT", "staging")
        origins = build_allowed_origins()
        assert "http://localhost" not in origins
        assert "file://" not in origins

    def test_localhost_mobile_origin_in_development(self, clean_env):
        clean_env.setenv("ENVIRONMENT", "development")
        origins = build_allowed_origins()
        assert "http://localhost" in origins
        assert "file://" in origins

    def test_explicit_mobile_origins_are_kept_in_production(self, clean_env):
        clean_env.setenv("ENVIRONMENT", "production")
        clean_env.setenv("MOBILE_ORIGINS", "http://localhost")
        assert "http://localhost" in build_allowed_origins()

    @pytest.mark.parametrize("value", ["", "  "])
    def test_empty_mobile_origins_falls_back_to_default(self, clean_env, value):
        clean_env.setenv("MOBILE_ORIGINS", value)
        origins = build_allowed_origins()
        assert "capacitor://localhost" in origins
        assert "ionic://localhost" in origins


class TestApiDocumentation:
    @pytest.mark.parametrize(
        "environment", ["production", "PRODUCTION", "prod", "staging", None]
    )
    def test_docs_disabled_outside_development(self, clean_env, environment):
        if environment is not None:
            clean_env.setenv("ENVIRONMENT", environment)
        client = TestClient(FastAPI(**docs_urls()))
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == 404

    def test_docs_enabled_in_development(self, clean_env):
        clean_env.setenv("ENVIRONMENT", "development")
        client = TestClient(FastAPI(**docs_urls()))
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == 200

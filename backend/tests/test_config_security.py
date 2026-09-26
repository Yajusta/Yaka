"""Tests de la configuration sensible : JWT_SECRET, clé admin, chargement du .env."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from app.routers.admin import ADMIN_API_KEY_MIN_LENGTH, verify_admin_api_key
from app.routers.auth import router as auth_router
from app.utils.security import JWT_SECRET_MIN_LENGTH, load_jwt_secret
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

BACKEND_DIR = Path(__file__).resolve().parents[1]
STRONG_SECRET = "0123456789abcdef" * 2  # 32 caractères, 16 distincts


def _run_python(
    code: str, env: dict[str, str], *args: str
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class TestJwtSecret:
    @pytest.mark.parametrize(
        "value",
        [
            None,
            "",
            "trop-court",
            "your_jwt_secret_key_here",
            # Longueur suffisante mais trivial : blancs, caractère répété
            " " * 40,
            "a" * JWT_SECRET_MIN_LENGTH,
            "abab" * 10,
            # Secret court complété par des blancs
            "  0123456789abcdef  " + " " * 20,
        ],
    )
    def test_invalid_secret_rejected(self, monkeypatch, value):
        if value is None:
            monkeypatch.delenv("JWT_SECRET", raising=False)
        else:
            monkeypatch.setenv("JWT_SECRET", value)
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            load_jwt_secret()

    def test_strong_secret_accepted(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", STRONG_SECRET)
        assert load_jwt_secret() == STRONG_SECRET

    def test_startup_refused_without_secret(self):
        """Le contrôle est bien exécuté à l'import du module."""
        # JWT_SECRET vide (et non absent) : load_dotenv ne le remplace pas par un .env local
        result = _run_python(
            "import app.utils.security", {**os.environ, "JWT_SECRET": ""}
        )
        assert result.returncode != 0
        assert "JWT_SECRET" in result.stderr


class TestAdminApiKey:
    """Cas propres à T1 ; absent/invalide/valide sont couverts par test_admin_routes.py."""

    @pytest.mark.parametrize(
        "configured, token, status",
        [
            # Ancienne valeur d'exemple de .env.sample = clé non configurée
            (
                "your-secret-admin-api-key-here",
                "your-secret-admin-api-key-here",
                503,
            ),
            # Clé trop courte = clé non configurée, même avec le bon jeton
            ("admin", "admin", 503),
            # Jeton non ASCII : refus propre, pas d'erreur de compare_digest
            ("k" * ADMIN_API_KEY_MIN_LENGTH, "clé-accentuée", 401),
        ],
    )
    def test_key_rejected(self, monkeypatch, configured, token, status):
        monkeypatch.setenv("YAKA_ADMIN_API_KEY", configured)
        with pytest.raises(HTTPException) as exc:
            verify_admin_api_key(
                HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            )
        assert exc.value.status_code == status

    def test_weak_key_logged(self, monkeypatch, caplog):
        """Une clé définie mais trop courte est signalée à l'opérateur, pas une clé absente."""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="x")

        monkeypatch.delenv("YAKA_ADMIN_API_KEY", raising=False)
        with caplog.at_level("WARNING", logger="app.routers.admin"):
            with pytest.raises(HTTPException):
                verify_admin_api_key(credentials)
        assert not caplog.records

        monkeypatch.setenv("YAKA_ADMIN_API_KEY", "trop-courte")
        with caplog.at_level("WARNING", logger="app.routers.admin"):
            with pytest.raises(HTTPException):
                verify_admin_api_key(credentials)
        assert "YAKA_ADMIN_API_KEY" in caplog.text

    def test_strong_key_accepted(self, monkeypatch):
        key = "k" * ADMIN_API_KEY_MIN_LENGTH
        monkeypatch.setenv("YAKA_ADMIN_API_KEY", key)
        assert verify_admin_api_key(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=key)
        )


class TestEnvPriority:
    async def test_ai_features_reads_process_env(
        self, monkeypatch, async_client_factory
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("LLM_MODEL", "model-test")

        async with async_client_factory(auth_router) as client:
            assert (await client.get("/auth/ai-features")).json() == {
                "ai_available": True
            }
            monkeypatch.delenv("OPENAI_API_KEY")
            assert (await client.get("/auth/ai-features")).json() == {
                "ai_available": False
            }

    def test_dotenv_does_not_override_process_env(self, tmp_path):
        """Un .env chargé à l'import ne doit jamais écraser l'environnement du processus."""
        dotenv_file = tmp_path / ".env"
        dotenv_file.write_text(
            "OPENAI_API_KEY=from-dotenv-file\nYAKA_TEST_DOTENV_MARKER=loaded\n",
            encoding="utf-8",
        )
        # Tous les load_dotenv() de l'application sont redirigés vers ce fichier
        code = (
            "import os, sys, dotenv.main\n"
            "dotenv.main.find_dotenv = lambda *a, **k: sys.argv[1]\n"
            "import app.services.llm_service\n"
            "print(os.environ['OPENAI_API_KEY'])\n"
            "print(os.environ.get('YAKA_TEST_DOTENV_MARKER', ''))\n"
        )
        env = {
            **os.environ,
            "JWT_SECRET": STRONG_SECRET,
            "OPENAI_API_KEY": "from-process",
        }
        env.pop("YAKA_TEST_DOTENV_MARKER", None)

        result = _run_python(code, env, str(dotenv_file))

        assert result.returncode == 0, result.stderr
        process_value, marker = result.stdout.splitlines()[-2:]
        # Le fichier a bien été chargé (variable absente du processus)...
        assert marker == "loaded"
        # ...sans écraser la valeur fixée par l'opérateur
        assert process_value == "from-process"

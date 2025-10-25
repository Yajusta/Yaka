"""Application FastAPI principale pour l'application Kanban."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .database import Base, engine
from .multi_database import get_board_db
from .utils.board_context import BoardContextMiddleware
from .models import BoardSettings, Card, KanbanList, Label, User
from .routers import auth_router, board_settings_router, cards_router, labels_router, lists_router, users_router
from .routers.card_comments import router as card_comments_router
from .routers.card_items import router as card_items_router
from .routers.export import router as export_router
from .routers.voice_control import router as voice_control_router
from .routers import admin_router
from .routers.global_dictionary import router as global_dictionary_router
from .routers.personal_dictionary import router as personal_dictionary_router
from .services.board_settings import initialize_default_settings
from .services.email import FROM_ADDRESS, SMTP_HOST, SMTP_USER
from .services.user import create_admin_user
from .utils.demo_mode import is_demo_mode
from .utils.demo_reset import reset_database, setup_fresh_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gestion du cycle de vie de l'application FastAPI."""
    # Événement de démarrage
    with get_board_db() as db:
        # Vérifier s'il y a déjà des données dans la base
        from .models import User

        user_count = db.query(User).count()
        if user_count > 0:
            print("Base de donnees existante detectee, aucune initialisation automatique effectuee")
            print("Pour reinitialiser en mode demo, utilisez l'endpoint POST /demo/reset")
        else:
            # Base de données vide ou nouvellement créée, configurer avec les données de base
            print("Base de donnees vide detectee, configuration initiale...")
            setup_fresh_database()

    # Afficher la configuration d'envoi d'emails utilisée au démarrage
    print(f"Mail config: FROM_ADDRESS={FROM_ADDRESS}, SMTP_USER={SMTP_USER or 'None'}, SMTP_HOST={SMTP_HOST}")

    yield  # L'application commence à recevoir des requêtes ici

    # Événement d'arrêt (nettoyage si nécessaire)
    print("Arrêt de l'application...")


# Créer les tables de la base de données si nécessaire
def ensure_database_exists():
    """Vérifie si la base de données existe et la crée si nécessaire."""
    try:
        import os

        from sqlalchemy import inspect

        # Vérifier si le répertoire data existe
        db_path = "./data"
        if not os.path.exists(db_path):
            print(f"Création du répertoire {db_path}...")
            os.makedirs(db_path)

        # Vérifier si le fichier de base de données existe
        db_file = f"{db_path}/yaka.db"
        if not os.path.exists(db_file):
            print(f"Création de la base de données {db_file}...")
            # Créer les tables de base
            Base.metadata.create_all(bind=engine)

            # Initialiser la table alembic_version avec la dernière version
            from alembic.script import ScriptDirectory

            alembic_cfg = Config("alembic.ini")
            script = ScriptDirectory.from_config(alembic_cfg)
            latest_version = script.get_current_head()

            from sqlalchemy import text

            with engine.connect() as conn:
                conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
                conn.execute(text(f"INSERT INTO alembic_version (version_num) VALUES ('{latest_version}')"))
                conn.commit()

            print(f"Base de données créée avec succès (version alembic: {latest_version})")
        else:
            print("Base de données existante détectée")

    except Exception as e:
        print(f"Erreur lors de la création de la base de données: {e}")
        raise


# Exécuter les migrations Alembic au démarrage si nécessaire
def run_migrations_for_database(db_path: str, db_name: str):
    """Exécute les migrations Alembic pour une base de données spécifique."""
    try:
        from sqlalchemy import create_engine as create_db_engine
        from sqlalchemy import inspect, text

        # Créer un moteur pour cette base de données spécifique
        db_url = f"sqlite:///{db_path}"
        db_engine = create_db_engine(db_url, connect_args={"check_same_thread": False})

        # Vérifier si la table alembic_version existe
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()

        if "alembic_version" not in tables:
            print(f"[{db_name}] Table alembic_version non trouvée...")

            # Vérifier si les tables principales existent déjà
            main_tables = ["users", "cards", "lists", "labels"]
            if existing_main_tables := [t for t in main_tables if t in tables]:
                print(f"[{db_name}] Tables existantes détectées: {existing_main_tables}")
                print(f"[{db_name}] Initialisation d'alembic_version à la version précédente...")

                # Créer la table alembic_version et l'initialiser à la version avant le language
                with db_engine.connect() as conn:
                    conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
                    conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('756429e64d69')"))
                    conn.commit()

            else:
                print(f"[{db_name}] Base de données vide, exécution de toutes les migrations...")

            # Maintenant exécuter les migrations manquantes
            alembic_cfg = Config("alembic.ini")
            alembic_cfg.set_main_option("sqlalchemy.url", db_url)
            command.upgrade(alembic_cfg, "head")
        else:
            # Vérifier si on est à la dernière version
            with db_engine.connect() as conn:
                upgrade_if_needed(conn, text, db_url, db_name)

        # Fermer le moteur
        db_engine.dispose()

    except Exception as e:
        print(f"[{db_name}] Erreur lors de la vérification des migrations: {e}")
        # En cas d'erreur, on essaie quand même d'exécuter les migrations
        try:
            print(f"[{db_name}] Tentative d'exécution des migrations...")
            from sqlalchemy import create_engine as create_db_engine

            db_url = f"sqlite:///{db_path}"
            alembic_cfg = Config("alembic.ini")
            alembic_cfg.set_main_option("sqlalchemy.url", db_url)
            command.upgrade(alembic_cfg, "head")
        except Exception as e2:
            print(f"[{db_name}] Erreur lors de l'exécution des migrations: {e2}")


def upgrade_if_needed(conn, text, db_url: str, db_name: str):
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    current_version = result.scalar()

    # Obtenir la dernière version disponible
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(alembic_cfg)
    latest_version = script.get_current_head()

    if current_version != latest_version:
        print(f"[{db_name}] Migration nécessaire: {current_version} -> {latest_version}")
        command.upgrade(alembic_cfg, "head")
    else:
        print(f"[{db_name}] Base de données à jour (version {current_version})")


def run_migrations():
    """Exécute les migrations Alembic pour toutes les bases de données .db du répertoire data."""
    import glob
    import os

    # Trouver tous les fichiers .db dans le répertoire data
    db_files = glob.glob("./data/*.db")

    if not db_files:
        print("Aucune base de données trouvée dans le répertoire data")
        return

    print(f"Migration de {len(db_files)} base(s) de données trouvée(s)...")

    for db_path in db_files:
        db_name = os.path.basename(db_path)
        print(f"\n{'='*60}")
        print(f"Migration de: {db_name}")
        print(f"{'='*60}")
        run_migrations_for_database(db_path, db_name)


# S'assurer que la base de données existe avant les migrations
ensure_database_exists()

# Exécuter les migrations Alembic
run_migrations()

# Créer l'application FastAPI
app = FastAPI(
    title="API Yaka",
    description="API pour l'application de gestion Yaka",
    version="1.0.0",
    redirect_slashes=False,
    lifespan=lifespan,
)

# Configuration CORS pour permettre les requêtes depuis le frontend
import os

# En développement, autoriser localhost; en production, utiliser les variables d'environnement
frontend_url = os.getenv("BASE_URL", "http://localhost:5173")
frontend_url_mobile = os.getenv("BASE_URL_MOBILE", "http://localhost:5173")
allowed_origins = [
    frontend_url,
    frontend_url_mobile,
    "http://localhost:3001",
    "http://localhost:5173",
    "http://localhost:4173",
]

# Ajouter les origines pour les applications mobiles (PWA → APK)
mobile_origins = os.getenv("MOBILE_ORIGINS", "capacitor://localhost,ionic://localhost,http://localhost").split(",")
allowed_origins.extend(mobile_origins)

# Ajouter file:// pour le développement mobile (uniquement si environnement de développement)
if os.getenv("ENVIRONMENT", "production").lower() == "development":
    allowed_origins.append("file://")

# Log des origines autorisées pour le debug
print(f"CORS: Origines autorisées: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


# Trusted Host middleware pour prévenir les attaques Host Header
domain = frontend_url.replace("http://", "").replace("https://", "").split(":")[0]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", domain, "testserver"],
)

# Ajouter les headers de sécurité via middleware personnalisé
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # Content Security Policy (CSP)
        if os.getenv("ENVIRONMENT", "production").lower() == "production":
            # Permettre les ressources Cloudflare et connexions externes
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "form-action 'self';"
            )

        # HSTS en production HTTPS uniquement
        if os.getenv("ENVIRONMENT", "production").lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response


app.add_middleware(SecurityHeadersMiddleware)

# Add middleware for board context
app.add_middleware(BoardContextMiddleware)

# Inclure les routeurs (backward compatibility without prefix)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(labels_router)
app.include_router(cards_router)
app.include_router(lists_router)
app.include_router(board_settings_router)
app.include_router(card_items_router)
app.include_router(card_comments_router)
app.include_router(export_router)
app.include_router(voice_control_router)
app.include_router(global_dictionary_router)
app.include_router(personal_dictionary_router)

# Include admin router (global, no board prefix)
app.include_router(admin_router)

# Include routers with prefix for specific boards
# Routes for /board/{board_uid}/*
app.include_router(auth_router, prefix="/board/{board_uid}")
app.include_router(users_router, prefix="/board/{board_uid}")
app.include_router(labels_router, prefix="/board/{board_uid}")
app.include_router(cards_router, prefix="/board/{board_uid}")
app.include_router(lists_router, prefix="/board/{board_uid}")
app.include_router(board_settings_router, prefix="/board/{board_uid}")
app.include_router(card_items_router, prefix="/board/{board_uid}")
app.include_router(card_comments_router, prefix="/board/{board_uid}")
app.include_router(export_router, prefix="/board/{board_uid}")
app.include_router(voice_control_router, prefix="/board/{board_uid}")
app.include_router(global_dictionary_router, prefix="/board/{board_uid}")
app.include_router(personal_dictionary_router, prefix="/board/{board_uid}")


@app.get("/")
async def root():
    """Root entry point for the API."""
    return {
        "message": "Welcome to the Yaka API",
        "version": "1.0.0",
        "documentation": "/docs",
        "usage": "Use /board/{board_uid} to access a specific board",
    }


@app.get("/health")
async def health_check():
    """Health check for the API."""
    return {"status": "healthy"}


@app.post("/demo/reset")
async def demo_reset():
    """Reset the database in demo mode (only if DEMO_MODE=true)."""
    if not is_demo_mode():
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Demo mode not enabled")

    try:
        reset_database()
        return {"message": "Database reset successfully"}
    except Exception as e:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=500,
            detail=f"Error resetting database: {str(e)}",
        ) from e

"""Application FastAPI principale pour l'application Kanban."""

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .database import Base, SessionLocal, engine
from .models import BoardSettings, Card, KanbanList, Label, User
from .routers import auth_router, board_settings_router, cards_router, labels_router, lists_router, users_router
from .routers.card_comments import router as card_comments_router
from .routers.card_items import router as card_items_router
from .services.board_settings import initialize_default_settings
from .services.email import FROM_ADDRESS, SMTP_HOST, SMTP_USER
from .services.user import create_admin_user, get_user_by_email
from .utils.demo_mode import is_demo_mode
from .utils.demo_reset import reset_database, setup_fresh_database


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
def run_migrations():
    """Exécute les migrations Alembic uniquement si nécessaire."""
    try:
        from sqlalchemy import inspect, text

        # Vérifier si la table alembic_version existe
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "alembic_version" not in tables:
            print("Table alembic_version non trouvée...")

            # Vérifier si les tables principales existent déjà
            main_tables = ["users", "cards", "lists", "labels"]
            if existing_main_tables := [t for t in main_tables if t in tables]:
                print(f"Tables existantes détectées: {existing_main_tables}")
                print("Initialisation d'alembic_version à la version précédente...")

                # Créer la table alembic_version et l'initialiser à la version avant le language
                with engine.connect() as conn:
                    conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
                    conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('756429e64d69')"))
                    conn.commit()

            else:
                print("Base de données vide, exécution de toutes les migrations...")
            # Maintenant exécuter les migrations manquantes
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
        else:
            # Vérifier si on est à la dernière version
            with engine.connect() as conn:
                upgrade_if_needed(conn, text)
    except Exception as e:
        print(f"Erreur lors de la vérification des migrations: {e}")
        # En cas d'erreur, on essaie quand même d'exécuter les migrations
        try:
            print("Tentative d'exécution des migrations...")
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
        except Exception as e2:
            print(f"Erreur lors de l'exécution des migrations: {e2}")


def upgrade_if_needed(conn, text):
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    current_version = result.scalar()

    # Obtenir la dernière version disponible
    alembic_cfg = Config("alembic.ini")
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(alembic_cfg)
    latest_version = script.get_current_head()

    if current_version != latest_version:
        print(f"Migration nécessaire: {current_version} -> {latest_version}")
        command.upgrade(alembic_cfg, "head")
    else:
        print(f"Base de données à jour (version {current_version})")


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
)

# Configuration CORS pour permettre les requêtes depuis le frontend
import os

# En développement, autoriser localhost; en production, utiliser les variables d'environnement
frontend_url = os.getenv("BASE_URL", "http://localhost:5173")
allowed_origins = [frontend_url]

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
    allowed_hosts=["localhost", "127.0.0.1", domain],
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

# Inclure les routeurs
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(labels_router)
app.include_router(cards_router)
app.include_router(lists_router)
app.include_router(board_settings_router)
app.include_router(card_items_router)
app.include_router(card_comments_router)


@app.on_event("startup")
async def startup_event():
    """Événement de démarrage de l'application."""
    # Vérifier et initialiser les données par défaut seulement si nécessaire
    db = SessionLocal()
    try:
        # Vérifier s'il y a déjà des données dans la base
        from .models import User

        if admin_user := get_user_by_email(db, "admin@yaka.local"):
            print("Base de donnees existante detectee, aucune initialisation automatique effectuee")
            print("Pour reinitialiser en mode demo, utilisez l'endpoint POST /demo/reset")
        else:
            # Base de données vide ou nouvellement créée, configurer avec les données de base
            print("Base de donnees vide detectee, configuration initiale...")
            setup_fresh_database()
    finally:
        db.close()

    # Afficher la configuration d'envoi d'emails utilisée au démarrage
    print(f"Mail config: FROM_ADDRESS={FROM_ADDRESS}, SMTP_USER={SMTP_USER or 'None'}, SMTP_HOST={SMTP_HOST}")


@app.get("/")
async def root():
    """Point d'entrée racine de l'API."""
    return {"message": "Bienvenue sur l'API Kanban", "version": "1.0.0", "documentation": "/docs"}


@app.get("/health")
async def health_check():
    """Vérification de l'état de l'API."""
    return {"status": "healthy"}


@app.post("/demo/reset")
async def demo_reset():
    """Réinitialise la base de données en mode démo (uniquement si DEMO_MODE=true)."""
    if not is_demo_mode():
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Mode démo non activé")

    try:
        reset_database()
        return {"message": "Base de données réinitialisée avec succès"}
    except Exception as e:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la réinitialisation: {str(e)}",
        ) from e

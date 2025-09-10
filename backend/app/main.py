"""Application FastAPI principale pour l'application Kanban."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .models import User, Label, Card, KanbanList, BoardSettings
from alembic import command
from alembic.config import Config
from .routers import (
    auth_router,
    users_router,
    labels_router,
    cards_router,
    lists_router,
    board_settings_router,
)
from .routers.card_items import router as card_items_router
from .routers.card_comments import router as card_comments_router
from .services.user import create_admin_user, get_user_by_email
from .services.board_settings import initialize_default_settings
from .services.email import FROM_ADDRESS, SMTP_USER, SMTP_HOST
from .database import SessionLocal
from .utils.demo_mode import is_demo_mode
from .utils.demo_reset import reset_database, setup_fresh_database

# Exécuter les migrations Alembic au démarrage
def run_migrations():
    """Exécute les migrations Alembic."""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

run_migrations()

# Créer l'application FastAPI
app = FastAPI(
    title="API Yaka",
    description="API pour l'application de gestion Yaka",
    version="1.0.0",
    redirect_slashes=False,
)

# Configuration CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

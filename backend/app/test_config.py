"""Configuration de test pour FastAPI avec une base de données séparée."""

from fastapi import FastAPI
from app.main import app
from app.test_database import get_test_db
from app import database
from app.test_database import Base as TestBase


def create_test_app():
    """Crée une instance de FastAPI pour les tests avec la base de données de test."""
    # Créer une nouvelle instance de l'application
    test_app = FastAPI(
        title="Yaka Test API",
        description="API de test pour Yaka",
        version="1.0.0"
    )
    
    # Copier les routes de l'application originale
    for route in app.routes:
        test_app.router.routes.append(route)
    
    # Remplacer la Base dans le module database
    original_base = database.Base
    database.Base = TestBase
    
    # Remplacer la dépendance de base de données
    test_app.dependency_overrides["get_db"] = get_test_db
    
    return test_app, original_base


def restore_database_base(original_base):
    """Restaore la Base originale du module database."""
    database.Base = original_base
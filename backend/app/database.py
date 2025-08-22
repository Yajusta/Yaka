"""Configuration de la base de données SQLite."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker
from typing import Generator

# URL de la base de données SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/yaka.db"

# Création du moteur SQLAlchemy
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Session locale
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base pour les modèles (SQLAlchemy 2.0 DeclarativeBase for typed mappings)
class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    """Générateur de session de base de données."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

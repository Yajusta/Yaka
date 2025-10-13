"""Gestionnaire multi-bases de données pour les boards Yaka."""

import os
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from contextvars import ContextVar

# Context variable pour stocker l'identifiant du board courant
current_board_uid: ContextVar[Optional[str]] = ContextVar('current_board_uid', default=None)

# Cache des moteurs et sessions
_engines: Dict[str, Any] = {}
_sessions: Dict[str, Any] = {}


class MultiDatabaseManager:
    """Gestionnaire pour gérer plusieurs bases de données SQLite."""

    def __init__(self, base_path: str = "./data"):
        self.base_path = base_path
        self.ensure_data_directory_exists()

    def ensure_data_directory_exists(self):
        """Assure que le répertoire de données existe."""
        if not os.path.exists(self.base_path):
            print(f"Création du répertoire {self.base_path}...")
            os.makedirs(self.base_path)

    def get_database_path(self, board_uid: str) -> str:
        """Retourne le chemin de la base de données pour un board."""
        return f"{self.base_path}/{board_uid}.db"

    def get_engine(self, board_uid: str) -> Any:
        """Récupère un moteur SQLAlchemy pour un board existant."""
        if board_uid not in _engines:
            db_path = self.get_database_path(board_uid)

            # Vérifier que la base de données existe
            if not os.path.exists(db_path):
                raise ValueError(f"Board '{board_uid}' not found")

            engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False}
            )
            _engines[board_uid] = engine

        return _engines[board_uid]

    def get_session_local(self, board_uid: str) -> sessionmaker:
        """Récupère ou crée un session maker pour un board."""
        if board_uid not in _sessions:
            engine = self.get_engine(board_uid)
            _sessions[board_uid] = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine
            )
        return _sessions[board_uid]

    def _initialize_alembic_version(self, engine: Any):
        """Initialise la table alembic_version pour une nouvelle base."""
        from alembic.script import ScriptDirectory
        from alembic.config import Config
        from sqlalchemy import text

        try:
            alembic_cfg = Config("alembic.ini")
            script = ScriptDirectory.from_config(alembic_cfg)
            latest_version = script.get_current_head()

            with engine.connect() as conn:
                conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
                conn.execute(text(f"INSERT INTO alembic_version (version_num) VALUES ('{latest_version}')"))
                conn.commit()

            print(f"Base de données initialisée avec alembic version {latest_version}")
        except Exception as e:
            print(f"Avertissement: Impossible d'initialiser alembic_version: {e}")

    def ensure_database_exists(self, board_uid: str) -> bool:
        """Vérifie que la base de données existe pour un board."""
        db_path = self.get_database_path(board_uid)
        return os.path.exists(db_path)


# Instance globale du gestionnaire
db_manager = MultiDatabaseManager()


def set_current_board_uid(board_uid: Optional[str]):
    """Définit l'identifiant du board courant pour le contexte."""
    current_board_uid.set(board_uid)


def get_current_board_uid() -> Optional[str]:
    """Récupère l'identifiant du board courant depuis le contexte."""
    return current_board_uid.get()


def get_database_for_board(board_uid: Optional[str] = None) -> str:
    """
    Retourne l'URL de la base de données pour le board spécifié ou courant.
    Utilise 'yaka.db' par défaut si aucun board n'est spécifié.
    """
    if board_uid is None:
        board_uid = get_current_board_uid()

    if board_uid is None:
        # Board par défaut pour la rétrocompatibilité
        return "sqlite:///./data/yaka.db"

    return f"sqlite:///./data/{board_uid}.db"


def get_engine_for_board(board_uid: Optional[str] = None) -> Any:
    """Récupère le moteur SQLAlchemy pour un board spécifique."""
    if board_uid is None:
        board_uid = get_current_board_uid()

    if board_uid is None:
        # Moteur par défaut pour la rétrocompatibilité
        from .database import engine
        return engine

    return db_manager.get_engine(board_uid)


def get_session_for_board(board_uid: Optional[str] = None) -> sessionmaker:
    """Récupère le session maker pour un board spécifique."""
    if board_uid is None:
        board_uid = get_current_board_uid()

    if board_uid is None:
        # Session par défaut pour la rétrocompatibilité
        from .database import SessionLocal
        return SessionLocal

    return db_manager.get_session_local(board_uid)


@contextmanager
def get_board_db(board_uid: Optional[str] = None) -> Generator[Session, None, None]:
    """
    Context manager pour obtenir une session de base de données pour un board.

    Usage:
        with get_board_db("mon-board") as db:
            # Utiliser db
            pass
    """
    if board_uid is None:
        board_uid = get_current_board_uid()

    if board_uid is None:
        # Session par défaut pour la rétrocompatibilité
        from .database import get_db
        db_gen = get_db()
        db = next(db_gen)
        try:
            yield db
        finally:
            db.close()
            next(db_gen, None)
    else:
        session_local = get_session_for_board(board_uid)
        db = session_local()
        try:
            yield db
        finally:
            db.close()


def get_dynamic_db() -> Generator[Session, None, None]:
    """
    Générateur de session de base de données dynamique basé sur le contexte.
    Cette fonction est conçue pour remplacer get_db() dans les dépendances FastAPI.
    """
    board_uid = get_current_board_uid()

    if board_uid is None:
        # Fallback vers la base par défaut
        from .database import get_db
        yield from get_db()
    else:
        session_local = get_session_for_board(board_uid)
        db = session_local()
        try:
            yield db
        finally:
            db.close()
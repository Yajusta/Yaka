"""Gestionnaire multi-bases de données pour les boards Yaka."""

import glob
import logging
import os
import re
import secrets
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Optional, TypeVar

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Board de la base par défaut (data/yaka.db), aussi accessible via /board/yaka/
DEFAULT_BOARD_UID = "yaka"

# Identifiant de board : alphanumérique et tirets, 1 à 50 caractères
_BOARD_UID_PATTERN = re.compile(r"[a-zA-Z0-9-]{1,50}")


def is_valid_board_uid(board_uid: str) -> bool:
    """Règle unique (middleware et routes admin) ; fullmatch refuse un saut de ligne final."""
    return _BOARD_UID_PATTERN.fullmatch(board_uid) is not None


# Context variable pour stocker l'identifiant du board courant
current_board_uid: ContextVar[Optional[str]] = ContextVar(
    "current_board_uid", default=None
)

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

            # mode=rw : une connexion ouverte après l'archivage du fichier
            # échoue au lieu de recréer une base vide à sa place.
            # as_uri() encode les caractères réservés du chemin (#, ?, %)
            engine = create_engine(
                f"sqlite:///{Path(db_path).resolve().as_uri()}?mode=rw&uri=true",
                connect_args={"check_same_thread": False, "timeout": 30},
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            _engines[board_uid] = engine

        return _engines[board_uid]

    def get_session_local(self, board_uid: str) -> sessionmaker:
        """Récupère ou crée un session maker pour un board."""
        if board_uid not in _sessions:
            engine = self.get_engine(board_uid)
            _sessions[board_uid] = sessionmaker(
                autocommit=False, autoflush=False, bind=engine
            )
        return _sessions[board_uid]

    def _initialize_alembic_version(self, engine: Any):
        """Initialise la table alembic_version pour une nouvelle base."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from sqlalchemy import text

        try:
            alembic_cfg = Config("alembic.ini")
            script = ScriptDirectory.from_config(alembic_cfg)
            latest_version = script.get_current_head()

            with engine.connect() as conn:
                conn.execute(
                    text(
                        "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"
                    )
                )
                conn.execute(
                    text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
                    {"version": latest_version},
                )
                conn.commit()

            print(f"Base de données initialisée avec alembic version {latest_version}")
        except Exception as e:
            print(f"Avertissement: Impossible d'initialiser alembic_version: {e}")

    def list_database_paths(self) -> list[str]:
        """Liste les fichiers .db du répertoire de données (tous les boards)."""
        return sorted(glob.glob(f"{self.base_path}/*.db"))

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


def get_effective_board_uid() -> str:
    """Board de la requête courante, base par défaut comprise (claim `board` des JWT)."""
    return get_current_board_uid() or DEFAULT_BOARD_UID


def evict_board(board_uid: str) -> None:
    """Retire un board des caches et ferme les connexions de son moteur.

    À appeler quand le fichier du board est supprimé ou recréé : sinon le
    moteur en cache continue de viser l'ancienne base. Les connexions encore
    empruntées par une session ouverte ne sont fermées qu'à leur restitution.
    Toutes les casses sont retirées : sur un système de fichiers insensible à
    la casse, /board/MonBoard/ et /board/monboard/ visent le même fichier.
    """
    target = board_uid.lower()
    for key in [k for k in list(_sessions) if k.lower() == target]:
        _sessions.pop(key, None)
    for key in [k for k in list(_engines) if k.lower() == target]:
        engine = _engines.pop(key, None)
        if engine is not None:
            engine.dispose()


def publish_board_database(board_uid: str, build: Callable[[str], T]) -> T:
    """Construit la base d'un nouveau board à l'écart, puis la publie d'un bloc.

    `build` reçoit un chemin temporaire (hors motif *.db, donc ni servi ni
    migré ni listé) et doit y créer la base complète puis fermer son moteur.
    La publication par os.link est atomique et échoue si la cible existe
    (repli par création exclusive + os.replace sans liens physiques) :
    le middleware ne voit jamais une base sans schéma, deux créations
    concurrentes ne s'écrasent pas, et un échec ne laisse aucun fichier qui
    bloquerait une nouvelle tentative.

    Lève FileExistsError si le board existe déjà (toutes casses sur un
    système de fichiers insensible à la casse).
    """
    db_path = db_manager.get_database_path(board_uid)
    tmp_path = f"{db_manager.base_path}/.{board_uid}.{secrets.token_hex(8)}.creating"
    try:
        result = build(tmp_path)
        try:
            os.link(tmp_path, db_path)
        except FileExistsError:
            raise
        except OSError:
            # Système de fichiers sans liens physiques (SMB, FAT, certains
            # montages Docker Desktop) : réservation exclusive du nom, puis
            # remplacement ; la base reste brièvement vide pendant l'échange.
            os.close(os.open(db_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            try:
                os.replace(tmp_path, db_path)
            except OSError:
                os.remove(db_path)
                raise
    finally:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass
        except OSError:
            logger.exception("Fichier temporaire du board %s non supprimé", board_uid)
    # Un moteur resté en cache d'un board archivé viserait l'ancienne base
    evict_board(board_uid)
    return result


def get_database_for_board(board_uid: Optional[str] = None) -> str:
    """
    Retourne l'URL de la base de données pour le board spécifié ou courant.
    Utilise 'yaka.db' par défaut si aucun board n'est spécifié.
    """
    if board_uid is None:
        board_uid = get_effective_board_uid()
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

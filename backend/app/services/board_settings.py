"""Service pour la gestion des paramètres du tableau."""

from sqlalchemy.orm import Session
from typing import Optional, List
from ..models import BoardSettings
from sqlalchemy.sql import func


def get_setting(db: Session, setting_key: str) -> Optional[BoardSettings]:
    """Récupérer un paramètre par sa clé."""
    return db.query(BoardSettings).filter(BoardSettings.setting_key == setting_key).first()


def get_all_settings(db: Session) -> List[BoardSettings]:
    """Récupérer tous les paramètres."""
    return db.query(BoardSettings).all()


def create_or_update_setting(
    db: Session, setting_key: str, setting_value: str, description: Optional[str] = None
) -> BoardSettings:
    """Créer ou mettre à jour un paramètre."""
    # Vérifier si le paramètre existe déjà
    existing_setting = get_setting(db, setting_key)

    if existing_setting:
        # Mettre à jour le paramètre existant
        existing_setting.setting_value = setting_value
        if description is not None:
            existing_setting.description = description
        db.commit()
        db.refresh(existing_setting)
        return existing_setting
    else:
        # Créer un nouveau paramètre
        db_setting = BoardSettings(setting_key=setting_key, setting_value=setting_value, description=description)
        db.add(db_setting)
        db.commit()
        db.refresh(db_setting)
        return db_setting


def delete_setting(db: Session, setting_key: str) -> bool:
    """Supprimer un paramètre."""
    setting = get_setting(db, setting_key)
    if not setting:
        return False

    db.delete(setting)
    db.commit()
    return True


def get_board_title(db: Session, default: str = "Yaka (Yet Another Kanban App)") -> str:
    """Récupérer le titre du tableau avec une valeur par défaut."""
    setting = get_setting(db, "board_title")
    return setting.setting_value if setting else default


def set_board_title(db: Session, title: str) -> BoardSettings:
    """Définir le titre du tableau."""
    return create_or_update_setting(
        db, setting_key="board_title", setting_value=title, description="Titre affiché du tableau Kanban"
    )


def initialize_default_settings(db: Session) -> None:
    """Initialiser les paramètres par défaut si nécessaire."""
    # Créer le titre par défaut si il n'existe pas
    if not get_setting(db, "board_title"):
        create_or_update_setting(
            db,
            setting_key="board_title",
            setting_value="Yaka (Yet Another Kanban App)",
            description="Titre affiché du tableau Kanban",
        )

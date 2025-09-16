"""Service pour la gestion des paramètres du tableau."""

from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import BoardSettings

DEFAULT_BOARD_TITLE = "Yaka (Yet Another Kanban App)"


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

    try:
        if existing_setting:
            # Mettre à jour le paramètre existant
            existing_setting.setting_value = setting_value
            if description is not None:
                existing_setting.description = description
            return update_settings(db, existing_setting)
        else:
            # Créer un nouveau paramètre
            db_setting = BoardSettings(setting_key=setting_key, setting_value=setting_value, description=description)
            db.add(db_setting)
            return update_settings(db, db_setting)
    except SQLAlchemyError as e:
        db.rollback()
        # Optionally, you can log the error here or raise a custom exception
        raise e


def update_settings(db: Session, settings: BoardSettings) -> BoardSettings:
    db.commit()
    db.refresh(settings)
    return settings


def delete_setting(db: Session, setting_key: str) -> bool:
    """Supprimer un paramètre."""
    setting = get_setting(db, setting_key)
    if not setting:
        return False

    try:
        db.delete(setting)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        return False


def get_board_title(db: Session, default: str = DEFAULT_BOARD_TITLE) -> str:
    """Récupérer le titre du tableau avec une valeur par défaut."""
    setting = get_setting(db, "board_title")
    return setting.setting_value if setting else default


def set_board_title(db: Session, title: str) -> BoardSettings:
    """Définir le titre du tableau."""
    return create_or_update_setting(
        db, setting_key="board_title", setting_value=title, description="Titre affiché du tableau Kanban"
    )


def initialize_default_settings(db: Session) -> None:
    """Initialiser dynamiquement les paramètres par défaut si nécessaire."""
    default_settings = [
        {
            "setting_key": "board_title",
            "setting_value": DEFAULT_BOARD_TITLE,
            "description": "Titre affiché du tableau Kanban",
        },
    ]
    for setting in default_settings:
        if not get_setting(db, setting["setting_key"]):
            create_or_update_setting(
                db,
                setting_key=setting["setting_key"],
                setting_value=setting["setting_value"],
                description=setting["description"],
            )

"""Script de réinitialisation de la base de données pour le mode démo."""

import os
from app.database import engine, Base
from app.models import User, Label, Card, KanbanList, BoardSettings, CardItem
from app.services.user import create_admin_user, get_user_by_email
from app.services.board_settings import initialize_default_settings
from app.utils.demo_mode import is_demo_mode
from app.services.kanban_list import create_list
from app.services.label import create_label
from app.services.card import create_card
from app.services.card_item import create_item as create_card_item
from app.schemas.kanban_list import KanbanListCreate
from app.schemas.label import LabelCreate
from app.schemas.card import CardCreate
from app.schemas.card_item import CardItemCreate
from app.models.card import CardPriority
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initialize_default_data(db_session=None):
    """Initialise les données par défaut : utilisateur admin et paramètres (sans données de démo)."""
    if db_session is None:
        db_session = SessionLocal()
        should_close = True
    else:
        should_close = False

    try:
        # Vérifier et créer l'utilisateur administrateur si nécessaire
        admin_user = get_user_by_email(db_session, "admin@yaka.local")
        if not admin_user:
            create_admin_user(db_session)
            print("Utilisateur administrateur cree : admin@yaka.local / admin123")

        # Initialiser les paramètres par défaut
        initialize_default_settings(db_session)
        print("Parametres par defaut initialises")

        return True

    except Exception as e:
        print(f"Erreur lors de l'initialisation: {e}")
        if db_session:
            db_session.rollback()
        return False
    finally:
        if should_close and db_session:
            db_session.close()


def create_demo_data(db_session):
    """Crée les données de démo : listes, étiquette et tâche."""
    print("Creation des donnees de demo...")

    # Récupérer l'utilisateur admin
    from app.services.user import get_user_by_email

    admin_user = get_user_by_email(db_session, "admin@yaka.local")
    if not admin_user:
        print("Erreur: Utilisateur admin non trouve")
        return

    # Déterminer la langue par défaut
    default_language = os.getenv("DEFAULT_LANGUAGE", "fr")

    # Définir les libellés selon la langue
    if default_language == "en":
        list_names = ["📝 To do", "🔄 In progress", "✅ Done"]
        label_name = "Important"  # English label
        card_title = "Configure Yaka"
        card_description = "Initial configuration of the Yaka application"
        checklist_items = [
            "Install Yaka",
            "Create a new administrator",
            "Delete the default administrator",
            "Modify the lists",
            "Add tasks",
            "Invite other people",
        ]
    else:
        list_names = ["📝 A faire", "🔄 En cours", "✅ Terminé"]
        label_name = "Important"  # French label
        card_title = "Configurer Yaka"
        card_description = "Configuration initiale de l'application Yaka"
        checklist_items = [
            "Installer Yaka",
            "Créer un nouvel administrateur",
            "Supprimer l'administrateur par défaut",
            "Modifier les listes",
            "Ajouter des tâches",
            "Inviter d'autres personnes",
        ]

    # Créer les 3 listes
    todo_list_data = KanbanListCreate(name=list_names[0], order=1)
    todo_list = create_list(db_session, todo_list_data)

    in_progress_list_data = KanbanListCreate(name=list_names[1], order=2)
    _ = create_list(db_session, in_progress_list_data)

    done_list_data = KanbanListCreate(name=list_names[2], order=3)
    _ = create_list(db_session, done_list_data)

    # Créer l'étiquette "Important" avec couleur rouge
    label_data = LabelCreate(nom=label_name, couleur="#940000")
    important_label = create_label(db_session, label_data, admin_user.id)

    # Créer la tâche de configuration dans la liste "A faire"/"To Do"
    card_data = CardCreate(
        titre=card_title,
        description=card_description,
        date_echeance=None,
        list_id=todo_list.id,
        position=1,
        priorite=CardPriority.HIGH,
        assignee_id=admin_user.id,
        label_ids=[important_label.id],
    )
    config_card = create_card(db_session, card_data, admin_user.id)

    # Ajouter les éléments de checklist à la tâche
    for i, item_text in enumerate(checklist_items):
        is_done = i == 0
        item_data = CardItemCreate(card_id=config_card.id, texte=item_text, is_done=is_done, position=i + 1)
        create_card_item(db_session, item_data)

    print("Donnees de demo creees avec succes!")


def reset_database():
    """Réinitialise la base de données avec les valeurs par défaut."""
    if not is_demo_mode():
        print("Mode demo non active. Aucune reinitialisation effectuee.")
        print("Pour activer le mode demo, definir DEMO_MODE=true dans les variables d'environnement")
        return

    print("Reinitialisation de la base de donnees en mode demo...")

    db = SessionLocal()
    try:
        delete_all_data(db)
    except Exception as e:
        print(f"Erreur lors de la reinitialisation: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# TODO Rename this here and in `reset_database`
def delete_all_data(db):
    # Supprimer toutes les données existantes
    print("Suppression des donnees existantes...")

    # Supprimer d'abord les éléments de checklist
    db.query(CardItem).delete()

    # Supprimer les relations many-to-many entre cartes et étiquettes
    from app.database import engine
    from sqlalchemy import text

    db.execute(text("DELETE FROM card_labels"))

    # Supprimer les entités principales
    db.query(Card).delete()
    db.query(KanbanList).delete()
    db.query(Label).delete()
    db.query(BoardSettings).delete()
    db.query(User).delete()

    db.commit()
    print("Base de donnees nettoyee avec succes")

    # Recréer les données de base (utilisateur admin, paramètres)
    initialize_default_data(db)

    # Créer les données de démo spécifiques
    create_demo_data(db)

    print("Base de donnees reinitialisee avec succes!")


def setup_fresh_database():
    """Configure une base de données fraîche avec les données de base (utilisé au premier démarrage)."""
    print("Configuration d'une base de donnees fraiche...")

    db = SessionLocal()
    try:
        # Vérifier si la base est déjà configurée
        from app.models import User

        if get_user_by_email(db, "admin@yaka.local"):
            print("Base de donnees deja configuree, aucune action necessaire")
            return

        # Base vide, initialiser les données de base
        initialize_default_data(db)

        # Si on est en mode demo, ajouter les données de demo
        if is_demo_mode():
            print("Mode demo detecte, ajout des donnees de demo...")
            create_demo_data(db)
        else:
            print("Mode demo non active, seulement les donnees de base ont ete creees")

        print("Base de donnees configuree avec succes!")

    except Exception as e:
        print(f"Erreur lors de la configuration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_database()

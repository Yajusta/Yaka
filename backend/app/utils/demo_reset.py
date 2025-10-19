"""Database reset script for demo mode."""

import os

from app.database import Base
from app.multi_database import get_board_db
from app.models import BoardSettings, Card, CardComment, CardHistory, CardItem, KanbanList, Label, User, UserRole
from app.models.card import CardPriority
from app.schemas.card import CardCreate
from app.schemas.card_item import CardItemCreate
from app.schemas.kanban_list import KanbanListCreate
from app.schemas.label import LabelCreate
from app.schemas.user import UserCreate
from app.services.board_settings import initialize_default_settings
from app.services.card import create_card
from app.services.card_item import create_item as create_card_item
from app.services.kanban_list import create_list
from app.services.label import create_label
from app.services.user import create_admin_user, create_user, get_user_by_email
from app.utils.demo_mode import is_demo_mode


def initialize_default_data(db_session=None):
    """Initialize default data: admin user and settings (without demo data)."""
    if db_session is None:
        with get_board_db() as db_session:
            return _initialize_default_data_impl(db_session)
    else:
        return _initialize_default_data_impl(db_session)


def _initialize_default_data_impl(db_session):
    """Implementation of initialize_default_data."""
    try:
        # Check and create administrator user if needed
        admin_user = get_user_by_email(db_session, "admin@yaka.local")
        if not admin_user:
            create_admin_user(db_session)
            print("Administrator user created: admin@yaka.local / Admin123")

        # Initialize default settings
        initialize_default_settings(db_session)
        print("Default settings initialized")

        return True

    except Exception as e:
        print(f"Error during initialization: {e}")
        if db_session:
            db_session.rollback()
        return False


def create_demo_users(db_session):
    """Create demo users with different roles."""
    default_language = os.getenv("DEFAULT_LANGUAGE", "fr")

    demo_users = [
        {
            "email": "supervisor@yaka.local",
            "password": "Demo1234",
            "display_name": "Sarah Supervisor",
            "role": UserRole.SUPERVISOR,
        },
        {
            "email": "editor@yaka.local",
            "password": "Demo1234",
            "display_name": "Eric Editor",
            "role": UserRole.EDITOR,
        },
        {
            "email": "contributor@yaka.local",
            "password": "Demo1234",
            "display_name": "Chris Contributor",
            "role": UserRole.CONTRIBUTOR,
        },
        {
            "email": "commenter@yaka.local",
            "password": "Demo1234",
            "display_name": "Carol Commenter",
            "role": UserRole.COMMENTER,
        },
        {
            "email": "visitor@yaka.local",
            "password": "Demo1234",
            "display_name": "Victor Visitor",
            "role": UserRole.VISITOR,
        },
    ]

    created_users = []
    for user_data in demo_users:
        if existing_user := get_user_by_email(db_session, user_data["email"]):
            created_users.append(existing_user)
        else:
            user_create = UserCreate(
                email=user_data["email"],
                password=user_data["password"],
                display_name=user_data["display_name"],
                role=user_data["role"],
                language=default_language,
            )
            user = create_user(db_session, user_create)
            created_users.append(user)
            print(f"Demo user created: {user_data['email']} ({user_data['role'].value}) / {user_data['password']}")
    return created_users


def create_demo_lists(db_session):
    """Create default kanban lists for demo boards."""
    default_language = os.getenv("DEFAULT_LANGUAGE", "fr")

    if default_language == "en":
        list_names = ["📝 To do", "🔄 In progress", "✅ Done"]
        list_descriptions = [
            "Tasks to be started",
            'Tasks currently in progress. If a task with multiple subtasks have at least one subtask done but not all, it should be in the "In progress" list.',
            'Completed tasks. If a task with multiple subtasks have all subtask done, it should be in the "Done" list.',
        ]
    else:
        list_names = ["📝 A faire", "🔄 En cours", "✅ Terminé"]
        list_descriptions = [
            "Tâches en attente de démarrage",
            'Tâches en cours de réalisation. Si une tâche avec plusieurs sous-tâches a au moins une sous-tâche terminée mais pas toutes, elle doit être dans la liste "En cours".',
            'Tâches terminées. Si une tâche avec plusieurs sous-tâches a toutes les sous-tâches terminées, elle doit être dans la liste "Terminé".',
        ]

    # Create the 3 lists
    todo_list_data = KanbanListCreate(name=list_names[0], description=list_descriptions[0], order=1)
    todo_list = create_list(db_session, todo_list_data)

    in_progress_list_data = KanbanListCreate(name=list_names[1], description=list_descriptions[1], order=2)
    in_progress_list = create_list(db_session, in_progress_list_data)

    done_list_data = KanbanListCreate(name=list_names[2], description=list_descriptions[2], order=3)
    done_list = create_list(db_session, done_list_data)

    return todo_list, in_progress_list, done_list


def create_demo_labels(db_session, admin_user_id):
    """Create default labels for demo boards."""
    default_language = os.getenv("DEFAULT_LANGUAGE", "fr")

    if default_language == "en":
        label_name = "Important"
        label_description = "High priority tasks requiring immediate attention"
    else:
        label_name = "Important"
        label_description = "Tâches prioritaires nécessitant une attention immédiate"

    # Create "Important" label with red color
    label_data = LabelCreate(name=label_name, color="#940000", description=label_description)
    important_label = create_label(db_session, label_data, admin_user_id)

    return important_label


def create_demo_task(db_session, todo_list, important_label, admin_user):
    """Create a sample configuration task for demo boards."""
    default_language = os.getenv("DEFAULT_LANGUAGE", "fr")

    if default_language == "en":
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

    # Create configuration task in "To do" list
    card_data = CardCreate(
        title=card_title,
        description=card_description,
        due_date=None,
        list_id=todo_list.id,
        position=1,
        priority=CardPriority.HIGH,
        assignee_id=admin_user.id,
        label_ids=[important_label.id],
    )
    config_card = create_card(db_session, card_data, admin_user.id)

    # Add checklist items to the task
    for i, item_text in enumerate(checklist_items):
        is_done = i == 0
        item_data = CardItemCreate(card_id=config_card.id, text=item_text, is_done=is_done, position=i + 1)
        create_card_item(db_session, item_data)

    return config_card


def create_demo_board_content(db_session, admin_user=None):
    """Create demo board content: lists, labels and sample task."""
    print("Creating demo board content...")

    # Get admin user
    if admin_user is None:
        admin_user = get_user_by_email(db_session, "admin@yaka.local")
    if not admin_user:
        print("Error: Admin user not found")
        return

    # Create lists
    todo_list, in_progress_list, done_list = create_demo_lists(db_session)

    # Create labels
    important_label = create_demo_labels(db_session, admin_user.id)

    # Create sample task
    create_demo_task(db_session, todo_list, important_label, admin_user)

    print("Demo board content created successfully!")


def create_demo_data(db_session):
    """Create complete demo data: users, lists, labels and tasks."""
    print("Creating demo data...")

    # Create demo users with different roles
    demo_users = create_demo_users(db_session)

    # Create board content (lists, labels, and sample task)
    create_demo_board_content(db_session)

    print("Demo data created successfully!")


def reset_database():
    """Reset database with default values."""
    if not is_demo_mode():
        print("Demo mode not active. No reset performed.")
        print("To activate demo mode, set DEMO_MODE=true in environment variables")
        return

    print("Resetting database in demo mode...")

    with get_board_db() as db:
        try:
            delete_all_data(db)
        except Exception as e:
            print(f"Error during reset: {e}")
            db.rollback()
            raise


def delete_all_data(db):
    """Delete all existing data from database."""
    print("Deleting existing data...")

    # Delete checklist items first
    db.query(CardItem).delete()

    # Delete card comments
    db.query(CardComment).delete()

    # Delete card history
    db.query(CardHistory).delete()

    # Delete many-to-many relationships between cards and labels
    from sqlalchemy import text

    db.execute(text("DELETE FROM card_labels"))

    # Delete main entities
    db.query(Card).delete()
    db.query(KanbanList).delete()
    db.query(Label).delete()
    db.query(BoardSettings).delete()
    db.query(User).delete()

    db.commit()
    print("Database cleaned successfully")

    # Recreate base data (admin user, settings)
    initialize_default_data(db)

    # Create specific demo data
    create_demo_data(db)

    print("Database reset successfully!")


def setup_fresh_database():
    """Configure a fresh database with base data (used on first startup)."""
    print("Configuring fresh database...")

    with get_board_db() as db:
        try:
            # Check if database is already configured
            from app.models import User

            if get_user_by_email(db, "admin@yaka.local"):
                print("Database already configured, no action needed")
                return

            # Empty database, initialize base data
            initialize_default_data(db)

            # Add demo data
            create_demo_data(db)
            print("Database configured successfully!")

        except Exception as e:
            print(f"Error during configuration: {e}")
            db.rollback()
            raise


if __name__ == "__main__":
    reset_database()

"""Database reset script for demo mode."""

import logging
import os
from pathlib import Path

from app.models import (
    BoardSettings,
    Card,
    CardComment,
    CardHistory,
    CardItem,
    KanbanList,
    Label,
    User,
    UserRole,
    UserStatus,
)
from app.models.card import CardPriority
from app.multi_database import db_manager, get_board_db
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
from app.services.user import (
    DEMO_ADMIN_PASSWORD,
    LEGACY_ADMIN_EMAIL,
    create_admin_user,
    create_user,
    default_admin_email,
    generate_initial_password,
    get_user_by_email,
)
from app.utils.demo_mode import is_demo_mode
from app.utils.security import get_password_hash, verify_password
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Mot de passe public des comptes de démonstration (documenté dans le README).
DEMO_USER_PASSWORD = "Demo1234"  # nosec B105
DEMO_USERS = (
    ("supervisor@yaka.local", "Sarah Supervisor", UserRole.SUPERVISOR),
    ("editor@yaka.local", "Eric Editor", UserRole.EDITOR),
    ("contributor@yaka.local", "Chris Contributor", UserRole.CONTRIBUTOR),
    ("commenter@yaka.local", "Carol Commenter", UserRole.COMMENTER),
    ("visitor@yaka.local", "Victor Visitor", UserRole.VISITOR),
)
DEMO_USER_EMAILS = tuple(email for email, _, _ in DEMO_USERS)


def secure_default_accounts(db_session) -> list[str]:
    """Neutralize seeded accounts that still use their public password.

    Demo accounts are disabled (soft-deleted), except those promoted to ADMIN
    (possibly the board's only administrator), which are treated like the
    default admin: a new random password (included once in the returned
    descriptions, to be logged) that must be changed at next login.
    Returns a description of each change.
    """
    admin_emails = {LEGACY_ADMIN_EMAIL, default_admin_email()}
    candidates = (
        db_session.query(User)
        .filter(
            func.lower(User.email).in_([*DEMO_USER_EMAILS, *admin_emails]),
            func.lower(User.status) != UserStatus.DELETED.value.lower(),
            User.password_hash.isnot(None),
            # Already reset to a random password: no need for a costly bcrypt check
            User.must_change_password.is_(False),
        )
        .all()
    )

    changes = []
    for user in candidates:
        email = user.email.lower()
        public_password = (
            DEMO_USER_PASSWORD if email in DEMO_USER_EMAILS else DEMO_ADMIN_PASSWORD
        )
        if not verify_password(public_password, user.password_hash):
            continue
        if email in DEMO_USER_EMAILS and user.role != UserRole.ADMIN:
            user.status = UserStatus.DELETED
            changes.append(f"{email} disabled")
        else:
            # Flagging alone is not enough: anyone knowing the public password
            # could supply it as the current one. Replace it with a random
            # password, shown only once in the logs.
            new_password = generate_initial_password()
            user.password_hash = get_password_hash(new_password)
            user.must_change_password = True
            changes.append(
                f"{email} password reset to {new_password} "
                "(must be changed at next login)"
            )

    if changes:
        db_session.commit()
    return changes


def secure_default_accounts_on_all_boards():
    """Run secure_default_accounts on every board database (outside demo mode).

    Uses a short-lived engine per file so that dormant boards do not keep a
    cached engine open for the lifetime of the process.
    """
    for db_path in db_manager.list_database_paths():
        board_uid = Path(db_path).stem
        engine = create_engine(f"sqlite:///{db_path}")
        try:
            with Session(engine) as db:
                if changes := secure_default_accounts(db):
                    logger.warning(
                        "[%s] Public default passwords detected: %s",
                        board_uid,
                        ", ".join(changes),
                    )
        except Exception as e:
            logger.error("[%s] Could not check default accounts: %s", board_uid, e)
        finally:
            engine.dispose()


def initialize_default_data(db_session):
    """Initialize default data: admin user and settings (without demo data).

    Errors propagate: an installation without an administrator is unusable.
    """
    if not get_user_by_email(db_session, default_admin_email()):
        admin_user = create_admin_user(db_session)
        print(f"Administrator user created: {admin_user.email}")

    initialize_default_settings(db_session)
    print("Default settings initialized")


def create_demo_users(db_session):
    """Create demo users with different roles."""
    default_language = os.getenv("DEFAULT_LANGUAGE", "fr")

    created_users = []
    for email, display_name, role in DEMO_USERS:
        if existing_user := get_user_by_email(db_session, email):
            created_users.append(existing_user)
        else:
            user_create = UserCreate(
                email=email,
                password=DEMO_USER_PASSWORD,
                display_name=display_name,
                role=role,
                language=default_language,
            )
            created_users.append(create_user(db_session, user_create))
            print(f"Demo user created: {email} ({role.value}) / {DEMO_USER_PASSWORD}")
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
    todo_list_data = KanbanListCreate(
        name=list_names[0], description=list_descriptions[0], order=1
    )
    todo_list = create_list(db_session, todo_list_data)

    in_progress_list_data = KanbanListCreate(
        name=list_names[1], description=list_descriptions[1], order=2
    )
    in_progress_list = create_list(db_session, in_progress_list_data)

    done_list_data = KanbanListCreate(
        name=list_names[2], description=list_descriptions[2], order=3
    )
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
    label_data = LabelCreate(
        name=label_name, color="#940000", description=label_description
    )
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
        item_data = CardItemCreate(
            card_id=config_card.id, text=item_text, is_done=is_done, position=i + 1
        )
        create_card_item(db_session, item_data)

    return config_card


def create_demo_board_content(db_session, admin_user=None):
    """Create demo board content: lists, labels and sample task."""
    print("Creating demo board content...")

    # Get admin user
    if admin_user is None:
        admin_user = get_user_by_email(db_session, default_admin_email())
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
    create_demo_users(db_session)

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

    # No commit here: the deletion is committed together with the admin
    # re-creation, so that a failure while re-creating the admin (e.g. invalid
    # configuration) is undone by reset_database's rollback instead of leaving
    # zero users. Later failures (demo content) leave an admin-only board.
    db.flush()
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

            if get_user_by_email(db, default_admin_email()):
                print("Database already configured, no action needed")
                return

            # Empty database, initialize base data
            initialize_default_data(db)

            # Demo accounts (public password) only in demo mode
            if is_demo_mode():
                create_demo_users(db)
            create_demo_board_content(db)
            print("Database configured successfully!")

        except Exception as e:
            print(f"Error during configuration: {e}")
            db.rollback()
            raise


if __name__ == "__main__":
    reset_database()

"""Tests for the personal dictionary service."""

import os
import sys

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.personal_dictionary import PersonalDictionary
from app.models.user import User, UserRole, UserStatus
from app.schemas import PersonalDictionaryCreate, PersonalDictionaryUpdate
from app.services.personal_dictionary import (
    create_entry,
    delete_entry,
    get_entries_by_user,
    get_entry,
    get_entry_by_user_and_term,
    update_entry,
)

# Test database configuration
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_personal_dictionary.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Fixture to create a test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_users(db_session):
    """Fixture to create sample users."""
    users = [
        User(
            email="user1@example.com",
            password_hash="hashed_password",
            display_name="User One",
            role=UserRole.EDITOR,
            status=UserStatus.ACTIVE,
        ),
        User(
            email="user2@example.com",
            password_hash="hashed_password",
            display_name="User Two",
            role=UserRole.EDITOR,
            status=UserStatus.ACTIVE,
        ),
    ]

    for user in users:
        db_session.add(user)
    db_session.commit()

    for user in users:
        db_session.refresh(user)

    return users


@pytest.fixture
def sample_entries(db_session, sample_users):
    """Fixture to create sample personal dictionary entries."""
    entries = [
        PersonalDictionary(user_id=sample_users[0].id, term="Repo", definition="Référentiel de code source"),
        PersonalDictionary(user_id=sample_users[0].id, term="PR", definition="Pull Request"),
        PersonalDictionary(user_id=sample_users[1].id, term="CI/CD", definition="Integration et déploiement continu"),
    ]

    for entry in entries:
        db_session.add(entry)
    db_session.commit()

    for entry in entries:
        db_session.refresh(entry)

    return entries


class TestGetEntry:
    """Tests for the get_entry function."""

    def test_get_existing_entry(self, db_session, sample_entries):
        """Test retrieving an existing entry."""
        entry = get_entry(db_session, sample_entries[0].id)
        assert entry is not None
        assert entry.id == sample_entries[0].id
        assert entry.term == "Repo"
        assert entry.definition == "Référentiel de code source"

    def test_get_nonexistent_entry(self, db_session):
        """Test retrieving a nonexistent entry."""
        entry = get_entry(db_session, 999)
        assert entry is None


class TestGetEntriesByUser:
    """Tests for the get_entries_by_user function."""

    def test_get_all_entries_for_user(self, db_session, sample_entries, sample_users):
        """Test retrieving all entries for a user."""
        entries = get_entries_by_user(db_session, sample_users[0].id)
        assert len(entries) == 2
        # Check alphabetical ordering
        assert entries[0].term == "PR"
        assert entries[1].term == "Repo"

    def test_get_entries_for_user_with_no_entries(self, db_session, sample_users):
        """Test retrieving entries for a user with no entries."""
        # Create a new user with no entries
        new_user = User(
            email="noentries@example.com",
            password_hash="hashed_password",
            display_name="No Entries",
            role=UserRole.EDITOR,
            status=UserStatus.ACTIVE,
        )
        db_session.add(new_user)
        db_session.commit()
        db_session.refresh(new_user)

        entries = get_entries_by_user(db_session, new_user.id)
        assert len(entries) == 0

    def test_get_entries_with_pagination(self, db_session, sample_entries, sample_users):
        """Test retrieving entries with pagination."""
        entries = get_entries_by_user(db_session, sample_users[0].id, skip=1, limit=1)
        assert len(entries) == 1


class TestGetEntryByUserAndTerm:
    """Tests for the get_entry_by_user_and_term function."""

    def test_get_existing_entry_by_user_and_term(self, db_session, sample_entries, sample_users):
        """Test retrieving an existing entry by user and term."""
        entry = get_entry_by_user_and_term(db_session, sample_users[0].id, "Repo")
        assert entry is not None
        assert entry.term == "Repo"
        assert entry.definition == "Référentiel de code source"

    def test_get_nonexistent_entry_by_user_and_term(self, db_session, sample_users):
        """Test retrieving a nonexistent entry by user and term."""
        entry = get_entry_by_user_and_term(db_session, sample_users[0].id, "NonExistent")
        assert entry is None

    def test_get_entry_for_wrong_user(self, db_session, sample_entries, sample_users):
        """Test retrieving an entry with wrong user."""
        # User 2 trying to get User 1's entry
        entry = get_entry_by_user_and_term(db_session, sample_users[1].id, "Repo")
        assert entry is None


class TestCreateEntry:
    """Tests for the create_entry function."""

    def test_create_entry_successfully(self, db_session, sample_users):
        """Test creating an entry successfully."""
        entry_data = PersonalDictionaryCreate(term="MVP", definition="Minimum Viable Product")
        entry = create_entry(db_session, entry_data, sample_users[0].id)

        assert entry.id is not None
        assert entry.user_id == sample_users[0].id
        assert entry.term == "MVP"
        assert entry.definition == "Minimum Viable Product"

    def test_create_entry_duplicate_term_for_same_user(self, db_session, sample_entries, sample_users):
        """Test creating an entry with a duplicate term for the same user."""
        entry_data = PersonalDictionaryCreate(term="Repo", definition="Autre définition")

        with pytest.raises(SQLAlchemyError):
            create_entry(db_session, entry_data, sample_users[0].id)

    def test_create_entry_same_term_for_different_users(self, db_session, sample_entries, sample_users):
        """Test creating an entry with the same term for different users."""
        # User 2 can create an entry with term "Repo" even though User 1 has it
        entry_data = PersonalDictionaryCreate(term="Repo", definition="Repository of source code")
        entry = create_entry(db_session, entry_data, sample_users[1].id)

        assert entry.id is not None
        assert entry.user_id == sample_users[1].id
        assert entry.term == "Repo"


class TestUpdateEntry:
    """Tests for the update_entry function."""

    def test_update_entry_term(self, db_session, sample_entries):
        """Test updating an entry's term."""
        entry_id = sample_entries[0].id
        update_data = PersonalDictionaryUpdate(term="Repository")

        entry = update_entry(db_session, entry_id, update_data)

        assert entry is not None
        assert entry.term == "Repository"
        assert entry.definition == sample_entries[0].definition

    def test_update_entry_definition(self, db_session, sample_entries):
        """Test updating an entry's definition."""
        entry_id = sample_entries[0].id
        update_data = PersonalDictionaryUpdate(definition="Nouvelle définition")

        entry = update_entry(db_session, entry_id, update_data)

        assert entry is not None
        assert entry.term == sample_entries[0].term
        assert entry.definition == "Nouvelle définition"

    def test_update_nonexistent_entry(self, db_session):
        """Test updating a nonexistent entry."""
        update_data = PersonalDictionaryUpdate(term="Test")
        entry = update_entry(db_session, 999, update_data)
        assert entry is None


class TestDeleteEntry:
    """Tests for the delete_entry function."""

    def test_delete_existing_entry(self, db_session, sample_entries):
        """Test deleting an existing entry."""
        entry_id = sample_entries[0].id

        result = delete_entry(db_session, entry_id)

        assert result is True
        entry = get_entry(db_session, entry_id)
        assert entry is None

    def test_delete_nonexistent_entry(self, db_session):
        """Test deleting a nonexistent entry."""
        result = delete_entry(db_session, 999)
        assert result is False


class TestSecurityAndValidation:
    """Tests for security and validation."""

    def test_xss_attempt_in_term(self, db_session):
        """Test XSS attempt in term."""
        xss_term = "<script>alert('XSS')</script>"

        with pytest.raises(ValidationError):
            PersonalDictionaryCreate(term=xss_term, definition="Test")

    def test_xss_attempt_in_definition(self, db_session):
        """Test XSS attempt in definition."""
        xss_definition = "<script>alert('XSS')</script>"

        with pytest.raises(ValidationError):
            PersonalDictionaryCreate(term="Test", definition=xss_definition)

    def test_empty_term(self, db_session):
        """Test with empty term."""
        with pytest.raises(ValidationError):
            PersonalDictionaryCreate(term="", definition="Test")

    def test_empty_definition(self, db_session):
        """Test with empty definition."""
        with pytest.raises(ValidationError):
            PersonalDictionaryCreate(term="Test", definition="")

    def test_term_max_length(self, db_session, sample_users):
        """Test term maximum length (32 characters)."""
        long_term = "A" * 32
        entry_data = PersonalDictionaryCreate(term=long_term, definition="Test")
        entry = create_entry(db_session, entry_data, sample_users[0].id)
        assert entry.term == long_term

    def test_term_too_long(self, db_session):
        """Test term exceeding maximum length."""
        too_long_term = "A" * 33

        with pytest.raises(ValidationError):
            PersonalDictionaryCreate(term=too_long_term, definition="Test")

    def test_definition_max_length(self, db_session, sample_users):
        """Test definition maximum length (250 characters)."""
        long_definition = "A" * 250
        entry_data = PersonalDictionaryCreate(term="Test", definition=long_definition)
        entry = create_entry(db_session, entry_data, sample_users[0].id)
        assert entry.definition == long_definition

    def test_definition_too_long(self, db_session):
        """Test definition exceeding maximum length."""
        too_long_definition = "A" * 251

        with pytest.raises(ValidationError):
            PersonalDictionaryCreate(term="Test", definition=too_long_definition)


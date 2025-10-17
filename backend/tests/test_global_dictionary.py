"""Tests for the global dictionary service."""

import os
import sys

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.global_dictionary import GlobalDictionary
from app.schemas import GlobalDictionaryCreate, GlobalDictionaryUpdate
from app.services.global_dictionary import (
    create_entry,
    delete_entry,
    get_entries,
    get_entry,
    get_entry_by_term,
    update_entry,
)

# Test database configuration
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_global_dictionary.db")
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
def sample_entries(db_session):
    """Fixture to create sample global dictionary entries."""
    entries = [
        GlobalDictionary(term="Sprint", definition="Une période de travail de 2 semaines"),
        GlobalDictionary(term="Epic", definition="Un grand ensemble de fonctionnalités"),
        GlobalDictionary(term="Story", definition="Une fonctionnalité utilisateur"),
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
        assert entry.term == "Sprint"
        assert entry.definition == "Une période de travail de 2 semaines"

    def test_get_nonexistent_entry(self, db_session):
        """Test retrieving a nonexistent entry."""
        entry = get_entry(db_session, 999)
        assert entry is None


class TestGetEntries:
    """Tests for the get_entries function."""

    def test_get_all_entries(self, db_session, sample_entries):
        """Test retrieving all entries."""
        entries = get_entries(db_session)
        assert len(entries) == 3
        # Check alphabetical ordering
        assert entries[0].term == "Epic"
        assert entries[1].term == "Sprint"
        assert entries[2].term == "Story"

    def test_get_entries_with_pagination(self, db_session, sample_entries):
        """Test retrieving entries with pagination."""
        entries = get_entries(db_session, skip=1, limit=2)
        assert len(entries) == 2

    def test_get_entries_empty_database(self, db_session):
        """Test retrieving entries from an empty database."""
        entries = get_entries(db_session)
        assert len(entries) == 0


class TestGetEntryByTerm:
    """Tests for the get_entry_by_term function."""

    def test_get_existing_entry_by_term(self, db_session, sample_entries):
        """Test retrieving an existing entry by term."""
        entry = get_entry_by_term(db_session, "Sprint")
        assert entry is not None
        assert entry.term == "Sprint"
        assert entry.definition == "Une période de travail de 2 semaines"

    def test_get_nonexistent_entry_by_term(self, db_session):
        """Test retrieving a nonexistent entry by term."""
        entry = get_entry_by_term(db_session, "NonExistent")
        assert entry is None


class TestCreateEntry:
    """Tests for the create_entry function."""

    def test_create_entry_successfully(self, db_session):
        """Test creating an entry successfully."""
        entry_data = GlobalDictionaryCreate(term="Backlog", definition="Liste de tâches à faire")
        entry = create_entry(db_session, entry_data)

        assert entry.id is not None
        assert entry.term == "Backlog"
        assert entry.definition == "Liste de tâches à faire"

    def test_create_entry_duplicate_term(self, db_session, sample_entries):
        """Test creating an entry with a duplicate term."""
        entry_data = GlobalDictionaryCreate(term="Sprint", definition="Autre définition")

        with pytest.raises(SQLAlchemyError):
            create_entry(db_session, entry_data)

    def test_create_entry_with_special_characters(self, db_session):
        """Test creating an entry with special characters."""
        entry_data = GlobalDictionaryCreate(term="Café", definition="Un lieu de rencontre")
        entry = create_entry(db_session, entry_data)

        assert entry.term == "Café"


class TestUpdateEntry:
    """Tests for the update_entry function."""

    def test_update_entry_term(self, db_session, sample_entries):
        """Test updating an entry's term."""
        entry_id = sample_entries[0].id
        update_data = GlobalDictionaryUpdate(term="Sprint Agile")

        entry = update_entry(db_session, entry_id, update_data)

        assert entry is not None
        assert entry.term == "Sprint Agile"
        assert entry.definition == sample_entries[0].definition

    def test_update_entry_definition(self, db_session, sample_entries):
        """Test updating an entry's definition."""
        entry_id = sample_entries[0].id
        update_data = GlobalDictionaryUpdate(definition="Nouvelle définition")

        entry = update_entry(db_session, entry_id, update_data)

        assert entry is not None
        assert entry.term == sample_entries[0].term
        assert entry.definition == "Nouvelle définition"

    def test_update_nonexistent_entry(self, db_session):
        """Test updating a nonexistent entry."""
        update_data = GlobalDictionaryUpdate(term="Test")
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
            GlobalDictionaryCreate(term=xss_term, definition="Test")

    def test_xss_attempt_in_definition(self, db_session):
        """Test XSS attempt in definition."""
        xss_definition = "<script>alert('XSS')</script>"

        with pytest.raises(ValidationError):
            GlobalDictionaryCreate(term="Test", definition=xss_definition)

    def test_empty_term(self, db_session):
        """Test with empty term."""
        with pytest.raises(ValidationError):
            GlobalDictionaryCreate(term="", definition="Test")

    def test_empty_definition(self, db_session):
        """Test with empty definition."""
        with pytest.raises(ValidationError):
            GlobalDictionaryCreate(term="Test", definition="")

    def test_term_max_length(self, db_session):
        """Test term maximum length (32 characters)."""
        long_term = "A" * 32
        entry_data = GlobalDictionaryCreate(term=long_term, definition="Test")
        entry = create_entry(db_session, entry_data)
        assert entry.term == long_term

    def test_term_too_long(self, db_session):
        """Test term exceeding maximum length."""
        too_long_term = "A" * 33

        with pytest.raises(ValidationError):
            GlobalDictionaryCreate(term=too_long_term, definition="Test")

    def test_definition_max_length(self, db_session):
        """Test definition maximum length (250 characters)."""
        long_definition = "A" * 250
        entry_data = GlobalDictionaryCreate(term="Test", definition=long_definition)
        entry = create_entry(db_session, entry_data)
        assert entry.definition == long_definition

    def test_definition_too_long(self, db_session):
        """Test definition exceeding maximum length."""
        too_long_definition = "A" * 251

        with pytest.raises(ValidationError):
            GlobalDictionaryCreate(term="Test", definition=too_long_definition)


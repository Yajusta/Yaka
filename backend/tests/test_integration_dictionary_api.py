"""Integration tests for dictionary APIs."""

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.main import app
from app.models.user import User, UserRole, UserStatus
from app.multi_database import get_dynamic_db
from app.utils.dependencies import get_current_active_user

# Test database configuration
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_integration_dictionary.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    """Create a test client."""
    app.dependency_overrides[get_dynamic_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def admin_user(client):
    """Create an admin user for testing."""
    db = TestingSessionLocal()
    try:
        # Try to get existing user first
        user = db.query(User).filter(User.email == "admin@example.com").first()
        if not user:
            user = User(
                email="admin@example.com",
                password_hash="hashed_password",
                display_name="Admin User",
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()


@pytest.fixture(scope="module")
def editor_user(client):
    """Create an editor user for testing."""
    db = TestingSessionLocal()
    try:
        # Try to get existing user first
        user = db.query(User).filter(User.email == "editor@example.com").first()
        if not user:
            user = User(
                email="editor@example.com",
                password_hash="hashed_password",
                display_name="Editor User",
                role=UserRole.EDITOR,
                status=UserStatus.ACTIVE,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()


@pytest.fixture(scope="module")
def visitor_user(client):
    """Create a visitor user for testing."""
    db = TestingSessionLocal()
    try:
        # Try to get existing user first
        user = db.query(User).filter(User.email == "visitor@example.com").first()
        if not user:
            user = User(
                email="visitor@example.com",
                password_hash="hashed_password",
                display_name="Visitor User",
                role=UserRole.VISITOR,
                status=UserStatus.ACTIVE,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()


class TestGlobalDictionaryAPI:
    """Tests for global dictionary API endpoints."""

    def test_create_global_entry_as_admin(self, client, admin_user):
        """Test creating a global dictionary entry as admin."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        response = client.post(
            "/global-dictionary/", json={"term": "Scrum", "definition": "Une méthode agile de gestion de projet"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["term"] == "Scrum"
        assert data["definition"] == "Une méthode agile de gestion de projet"
        assert "id" in data

    def test_create_global_entry_as_editor_forbidden(self, client, editor_user):
        """Test that editors cannot create global dictionary entries."""
        app.dependency_overrides[get_current_active_user] = lambda: editor_user

        response = client.post(
            "/global-dictionary/", json={"term": "Scrum", "definition": "Une méthode agile de gestion de projet"}
        )
        assert response.status_code == 403

    def test_get_global_entries(self, client, editor_user):
        """Test getting global dictionary entries as any authenticated user."""
        app.dependency_overrides[get_current_active_user] = lambda: editor_user

        response = client.get("/global-dictionary/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_update_global_entry_as_admin(self, client, admin_user):
        """Test updating a global dictionary entry as admin."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        # Create entry first
        create_response = client.post(
            "/global-dictionary/", json={"term": "Kanban", "definition": "Méthode de gestion visuelle"}
        )
        entry_id = create_response.json()["id"]

        # Update entry
        response = client.put(f"/global-dictionary/{entry_id}", json={"definition": "Méthode agile visuelle"})
        assert response.status_code == 200
        data = response.json()
        assert data["definition"] == "Méthode agile visuelle"

    def test_delete_global_entry_as_admin(self, client, admin_user):
        """Test deleting a global dictionary entry as admin."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        # Create entry first
        create_response = client.post(
            "/global-dictionary/", json={"term": "DevOps", "definition": "Culture de collaboration"}
        )
        entry_id = create_response.json()["id"]

        # Delete entry
        response = client.delete(f"/global-dictionary/{entry_id}")
        assert response.status_code == 200

        # Verify deletion
        get_response = client.get(f"/global-dictionary/{entry_id}")
        assert get_response.status_code == 404


class TestPersonalDictionaryAPI:
    """Tests for personal dictionary API endpoints."""

    def test_create_personal_entry_as_editor(self, client, editor_user):
        """Test creating a personal dictionary entry as editor."""
        app.dependency_overrides[get_current_active_user] = lambda: editor_user

        response = client.post(
            "/personal-dictionary/", json={"term": "MyTerm", "definition": "My personal definition"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["term"] == "MyTerm"
        assert data["definition"] == "My personal definition"
        assert data["user_id"] == editor_user.id

    def test_create_personal_entry_as_visitor_forbidden(self, client, visitor_user):
        """Test that visitors cannot create personal dictionary entries."""
        app.dependency_overrides[get_current_active_user] = lambda: visitor_user

        response = client.post(
            "/personal-dictionary/", json={"term": "MyTerm", "definition": "My personal definition"}
        )
        assert response.status_code == 403

    def test_get_personal_entries_only_own(self, client, editor_user, admin_user):
        """Test that users can only see their own personal dictionary entries."""
        # Create entry as admin
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        client.post("/personal-dictionary/", json={"term": "AdminTerm", "definition": "Admin definition"})

        # Create entry as editor
        app.dependency_overrides[get_current_active_user] = lambda: editor_user
        client.post("/personal-dictionary/", json={"term": "EditorTerm", "definition": "Editor definition"})

        # Editor should only see their own entries
        response = client.get("/personal-dictionary/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1  # At least the editor's entry
        # Check that all entries belong to the editor
        for entry in data:
            assert entry["user_id"] == editor_user.id

    def test_update_personal_entry_own_only(self, client, editor_user, admin_user):
        """Test that users can only update their own personal dictionary entries."""
        # Create entry as editor
        app.dependency_overrides[get_current_active_user] = lambda: editor_user
        create_response = client.post(
            "/personal-dictionary/", json={"term": "UpdateTest", "definition": "Original definition"}
        )
        entry_id = create_response.json()["id"]

        # Try to update as admin (should fail)
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        response = client.put(f"/personal-dictionary/{entry_id}", json={"definition": "Admin's change"})
        assert response.status_code == 403

        # Update as editor (should succeed)
        app.dependency_overrides[get_current_active_user] = lambda: editor_user
        response = client.put(f"/personal-dictionary/{entry_id}", json={"definition": "Editor's change"})
        assert response.status_code == 200
        data = response.json()
        assert data["definition"] == "Editor's change"

    def test_delete_personal_entry_own_only(self, client, editor_user, admin_user):
        """Test that users can only delete their own personal dictionary entries."""
        # Create entry as editor
        app.dependency_overrides[get_current_active_user] = lambda: editor_user
        create_response = client.post(
            "/personal-dictionary/", json={"term": "DeleteTest", "definition": "To be deleted"}
        )
        entry_id = create_response.json()["id"]

        # Try to delete as admin (should fail)
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        response = client.delete(f"/personal-dictionary/{entry_id}")
        assert response.status_code == 403

        # Delete as editor (should succeed)
        app.dependency_overrides[get_current_active_user] = lambda: editor_user
        response = client.delete(f"/personal-dictionary/{entry_id}")
        assert response.status_code == 200


class TestDictionaryValidation:
    """Tests for dictionary validation."""

    def test_create_entry_with_xss_term(self, client, admin_user):
        """Test that XSS attempts in term are blocked."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        response = client.post(
            "/global-dictionary/",
            json={"term": "<script>alert('XSS')</script>", "definition": "Malicious entry"},
        )
        assert response.status_code == 422

    def test_create_entry_with_xss_definition(self, client, admin_user):
        """Test that XSS attempts in definition are blocked."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        response = client.post(
            "/global-dictionary/",
            json={"term": "Test", "definition": "<script>alert('XSS')</script>"},
        )
        assert response.status_code == 422

    def test_create_entry_with_too_long_term(self, client, admin_user):
        """Test that terms exceeding max length are rejected."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        response = client.post("/global-dictionary/", json={"term": "A" * 33, "definition": "Test"})
        assert response.status_code == 422

    def test_create_entry_with_too_long_definition(self, client, admin_user):
        """Test that definitions exceeding max length are rejected."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        response = client.post("/global-dictionary/", json={"term": "Test", "definition": "A" * 251})
        assert response.status_code == 422


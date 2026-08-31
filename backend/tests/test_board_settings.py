"""Tests pour le service BoardSettings."""

import os
import sys
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.board_settings import BoardSettings
from app.services.board_settings import (
    DEFAULT_BOARD_TITLE,
    create_or_update_setting,
    delete_setting,
    get_all_settings,
    get_board_title,
    get_setting,
    initialize_default_settings,
    set_board_title,
    update_settings,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuration de la base de données de test
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_board_settings.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Fixture pour créer une session de base de données de test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_settings(db_session):
    """Fixture pour créer des paramètres d'exemple."""
    settings = [
        BoardSettings(
            setting_key="test_key_1",
            setting_value="test_value_1",
            description="Description test 1",
        ),
        BoardSettings(
            setting_key="test_key_2",
            setting_value="test_value_2",
            description="Description test 2",
        ),
        BoardSettings(
            setting_key="board_title",
            setting_value="Custom Board Title",
            description="Titre personnalisé",
        ),
    ]

    for setting in settings:
        db_session.add(setting)
    db_session.commit()

    for setting in settings:
        db_session.refresh(setting)

    return settings


class TestGetSetting:
    """Tests pour la fonction get_setting."""

    def test_get_existing_setting(self, db_session, sample_settings):
        """Test de récupération d'un paramètre existant."""
        setting = get_setting(db_session, "test_key_1")
        assert setting is not None
        assert setting.setting_key == "test_key_1"
        assert setting.setting_value == "test_value_1"
        assert setting.description == "Description test 1"

    def test_get_nonexistent_setting(self, db_session):
        """Test de récupération d'un paramètre qui n'existe pas."""
        setting = get_setting(db_session, "nonexistent_key")
        assert setting is None

    def test_get_setting_empty_database(self, db_session):
        """Test de récupération d'un paramètre dans une base de données vide."""
        setting = get_setting(db_session, "any_key")
        assert setting is None


class TestGetAllSettings:
    """Tests pour la fonction get_all_settings."""

    def test_get_all_settings_with_data(self, db_session, sample_settings):
        """Test de récupération de tous les paramètres quand il y en a."""
        settings = get_all_settings(db_session)
        assert len(settings) == 3
        keys = [s.setting_key for s in settings]
        assert "test_key_1" in keys
        assert "test_key_2" in keys
        assert "board_title" in keys

    def test_get_all_settings_empty_database(self, db_session):
        """Test de récupération de tous les paramètres d'une base vide."""
        settings = get_all_settings(db_session)
        assert len(settings) == 0


class TestCreateOrUpdateSetting:
    """Tests pour la fonction create_or_update_setting."""

    def test_create_new_setting(self, db_session):
        """Test de création d'un nouveau paramètre."""
        setting = create_or_update_setting(
            db_session,
            setting_key="new_key",
            setting_value="new_value",
            description="New description",
        )

        assert setting.setting_key == "new_key"
        assert setting.setting_value == "new_value"
        assert setting.description == "New description"

        # Vérifier que le paramètre est bien dans la base de données
        retrieved = get_setting(db_session, "new_key")
        assert retrieved is not None
        assert retrieved.setting_value == "new_value"

    def test_update_existing_setting(self, db_session, sample_settings):
        """Test de mise à jour d'un paramètre existant."""
        setting = create_or_update_setting(
            db_session,
            setting_key="test_key_1",
            setting_value="updated_value",
            description="Updated description",
        )

        assert setting.setting_key == "test_key_1"
        assert setting.setting_value == "updated_value"
        assert setting.description == "Updated description"

        # Vérifier que le paramètre est bien mis à jour
        retrieved = get_setting(db_session, "test_key_1")
        assert retrieved is not None
        assert retrieved.setting_value == "updated_value"
        assert retrieved.description == "Updated description"

    def test_update_existing_setting_without_description(
        self, db_session, sample_settings
    ):
        """Test de mise à jour d'un paramètre existant sans changer la description."""
        original_setting = get_setting(db_session, "test_key_1")
        original_description = (
            original_setting.description if original_setting else None
        )

        setting = create_or_update_setting(
            db_session, setting_key="test_key_1", setting_value="updated_value"
        )

        assert setting.setting_value == "updated_value"
        assert setting.description == original_description

    def test_create_setting_without_description(self, db_session):
        """Test de création d'un paramètre sans description."""
        setting = create_or_update_setting(
            db_session, setting_key="new_key_no_desc", setting_value="new_value"
        )

        assert setting.setting_key == "new_key_no_desc"
        assert setting.setting_value == "new_value"
        assert setting.description is None

    def test_create_setting_with_empty_strings(self, db_session):
        """Test de création d'un paramètre avec des chaînes vides."""
        setting = create_or_update_setting(
            db_session, setting_key="empty_strings", setting_value="", description=""
        )

        assert setting.setting_key == "empty_strings"
        assert setting.setting_value == ""
        assert setting.description == ""

    @patch("app.services.board_settings.update_settings")
    def test_database_error_handling(self, mock_update_settings, db_session):
        """Test de gestion des erreurs de base de données."""
        mock_update_settings.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(SQLAlchemyError):
            create_or_update_setting(
                db_session, setting_key="error_key", setting_value="error_value"
            )

    def test_concurrent_creation(self, db_session):
        """Test de création concurrente du même paramètre."""
        # Créer le même paramètre deux fois
        create_or_update_setting(
            db_session, setting_key="concurrent_key", setting_value="value1"
        )

        setting2 = create_or_update_setting(
            db_session, setting_key="concurrent_key", setting_value="value2"
        )

        # Le second appel devrait mettre à jour le premier
        assert setting2.setting_value == "value2"

        # Vérifier qu'il n'y a qu'un seul paramètre
        settings = get_all_settings(db_session)
        concurrent_settings = [s for s in settings if s.setting_key == "concurrent_key"]
        assert len(concurrent_settings) == 1


class TestUpdateSettings:
    """Tests pour la fonction update_settings."""

    def test_update_settings_successfully(self, db_session, sample_settings):
        """Test de mise à jour réussie des paramètres."""
        setting = sample_settings[0]
        setting.setting_value = "updated_value"

        result = update_settings(db_session, setting)

        assert result.setting_value == "updated_value"
        db_session.refresh(setting)
        assert setting.setting_value == "updated_value"


class TestDeleteSetting:
    """Tests pour la fonction delete_setting."""

    def test_delete_existing_setting(self, db_session, sample_settings):
        """Test de suppression d'un paramètre existant."""
        result = delete_setting(db_session, "test_key_1")

        assert result is True

        # Vérifier que le paramètre est bien supprimé
        setting = get_setting(db_session, "test_key_1")
        assert setting is None

    def test_delete_nonexistent_setting(self, db_session):
        """Test de suppression d'un paramètre qui n'existe pas."""
        result = delete_setting(db_session, "nonexistent_key")
        assert result is False

    def test_delete_setting_integrity_error(self, db_session, sample_settings):
        """Test de gestion des erreurs d'intégrité lors de la suppression."""
        with patch.object(
            db_session,
            "commit",
            side_effect=IntegrityError("statement", "params", Exception("orig")),
        ):
            result = delete_setting(db_session, "test_key_1")
            assert result is False


class TestGetBoardTitle:
    """Tests pour la fonction get_board_title."""

    def test_get_board_title_existing(self, db_session, sample_settings):
        """Test de récupération du title du tableau quand il existe."""
        title = get_board_title(db_session)
        assert title == "Custom Board Title"

    def test_get_board_title_default(self, db_session):
        """Test de récupération du title du tableau par défaut."""
        title = get_board_title(db_session)
        assert title == DEFAULT_BOARD_TITLE

    def test_get_board_title_custom_default(self, db_session):
        """Test de récupération du title du tableau avec un défaut personnalisé."""
        title = get_board_title(db_session, "Custom Default Title")
        assert title == "Custom Default Title"


class TestSetBoardTitle:
    """Tests pour la fonction set_board_title."""

    def test_set_board_title_new(self, db_session):
        """Test de définition d'un nouveau title de tableau."""
        setting = set_board_title(db_session, "New Board Title")

        assert setting.setting_key == "board_title"
        assert setting.setting_value == "New Board Title"
        assert setting.description == "Titre affiché du tableau Kanban"

        # Vérifier que le title est bien récupéré
        title = get_board_title(db_session)
        assert title == "New Board Title"

    def test_set_board_title_update(self, db_session, sample_settings):
        """Test de mise à jour du title de tableau existant."""
        setting = set_board_title(db_session, "Updated Board Title")

        assert setting.setting_value == "Updated Board Title"

        # Vérifier que le title est bien mis à jour
        title = get_board_title(db_session)
        assert title == "Updated Board Title"

    def test_set_board_title_empty(self, db_session):
        """Test de définition d'un title de tableau vide."""
        setting = set_board_title(db_session, "")

        assert setting.setting_value == ""

        title = get_board_title(db_session)
        assert title == ""

    def test_set_board_title_long_title(self, db_session):
        """Test de définition d'un title de tableau très long."""
        long_title = "A" * 1000
        setting = set_board_title(db_session, long_title)

        assert setting.setting_value == long_title

        title = get_board_title(db_session)
        assert title == long_title


class TestInitializeDefaultSettings:
    """Tests pour la fonction initialize_default_settings."""

    def test_initialize_default_settings_empty_db(self, db_session):
        """Test d'initialisation des paramètres par défaut sur une base vide."""
        initialize_default_settings(db_session)

        # Vérifier que les paramètres par défaut sont créés
        settings = get_all_settings(db_session)
        assert len(settings) == 1

        title_setting = get_setting(db_session, "board_title")
        assert title_setting is not None
        assert title_setting.setting_value == DEFAULT_BOARD_TITLE
        assert title_setting.description == "Titre affiché du tableau Kanban"

    def test_initialize_default_settings_existing_settings(
        self, db_session, sample_settings
    ):
        """Test d'initialisation des paramètres par défaut quand ils existent déjà."""
        # Le paramètre board_title existe déjà
        original_title = get_setting(db_session, "board_title")
        original_value = original_title.setting_value if original_title else None

        initialize_default_settings(db_session)

        # Vérifier que le title existant n'a pas été écrasé
        title_setting = get_setting(db_session, "board_title")
        assert title_setting is not None
        assert title_setting.setting_value == original_value

    def test_initialize_default_settings_partial_existing(self, db_session):
        """Test d'initialisation quand certains paramètres existent déjà."""
        # Créer seulement un paramètre qui n'est pas dans les defaults
        create_or_update_setting(
            db_session, setting_key="other_setting", setting_value="other_value"
        )

        initialize_default_settings(db_session)

        # Vérifier que les paramètres par défaut sont ajoutés
        settings = get_all_settings(db_session)
        assert len(settings) == 2

        title_setting = get_setting(db_session, "board_title")
        assert title_setting is not None
        assert title_setting.setting_value == DEFAULT_BOARD_TITLE

        other_setting = get_setting(db_session, "other_setting")
        assert other_setting is not None

    def test_initialize_default_settings_multiple_calls(self, db_session):
        """Test d'appels multiples à initialize_default_settings."""
        initialize_default_settings(db_session)

        # Appeler une deuxième fois
        initialize_default_settings(db_session)

        # Vérifier qu'il n'y a pas de duplication
        settings = get_all_settings(db_session)
        title_settings = [s for s in settings if s.setting_key == "board_title"]
        assert len(title_settings) == 1


class TestSecurityAndEdgeCases:
    """Tests de sécurité et cas particuliers."""

    def test_sql_injection_attempt(self, db_session):
        """Test de tentative d'injection SQL."""
        malicious_key = "test_key'; DROP TABLE board_settings; --"
        malicious_value = "test_value"

        setting = create_or_update_setting(
            db_session, setting_key=malicious_key, setting_value=malicious_value
        )

        # La clé doit être stockée telle quelle (pas d'exécution SQL)
        assert setting.setting_key == malicious_key
        assert setting.setting_value == malicious_value

    def test_xss_attempt_in_value(self, db_session):
        """Test de tentative XSS dans la valeur."""
        xss_value = "<script>alert('XSS')</script>"

        setting = create_or_update_setting(
            db_session, setting_key="xss_test", setting_value=xss_value
        )

        assert setting.setting_value == xss_value

    def test_special_characters(self, db_session):
        """Test avec des caractères spéciaux."""
        special_chars_key = "key_with_éèàçù_ñáéíóú_中文_العربية"
        special_chars_value = "value_with_éèàçù_ñáéíóú_中文_العربية"

        setting = create_or_update_setting(
            db_session,
            setting_key=special_chars_key,
            setting_value=special_chars_value,
            description="Description avec caractères spéciaux: éèàçù",
        )

        assert setting.setting_key == special_chars_key
        assert setting.setting_value == special_chars_value
        assert setting.description == "Description avec caractères spéciaux: éèàçù"

    def test_very_long_values(self, db_session):
        """Test avec des valeurs très longues."""
        long_key = "long_key_" + "a" * 200
        long_value = "x" * 10000
        long_description = "y" * 500

        setting = create_or_update_setting(
            db_session,
            setting_key=long_key,
            setting_value=long_value,
            description=long_description,
        )

        assert setting.setting_key == long_key
        assert setting.setting_value == long_value
        assert setting.description == long_description

    def test_null_and_none_values(self, db_session):
        """Test avec des valeurs nulles."""
        setting = create_or_update_setting(
            db_session, setting_key="null_test", setting_value="null", description=None
        )

        assert setting.setting_value == "null"
        assert setting.description is None

    def test_whitespace_handling(self, db_session):
        """Test de gestion des espaces blancs."""
        setting = create_or_update_setting(
            db_session,
            setting_key="  whitespace_key  ",
            setting_value="  whitespace_value  ",
            description="  whitespace description  ",
        )

        assert setting.setting_key == "  whitespace_key  "
        assert setting.setting_value == "  whitespace_value  "
        assert setting.description == "  whitespace description  "

    def test_unicode_characters(self, db_session):
        """Test avec des caractères Unicode."""
        unicode_key = "🚀_unicode_测试"
        unicode_value = "🎯_value_测试"

        setting = create_or_update_setting(
            db_session,
            setting_key=unicode_key,
            setting_value=unicode_value,
            description="📝_description_测试",
        )

        assert setting.setting_key == unicode_key
        assert setting.setting_value == unicode_value
        assert setting.description == "📝_description_测试"

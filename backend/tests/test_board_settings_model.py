"""Tests complets pour le modèle BoardSettings."""

import datetime
import os
import sys
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.board_settings import BoardSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuration de la base de données de test
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_board_settings_model.db")
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
def sample_board_settings(db_session):
    """Fixture pour créer des paramètres de tableau de test."""
    settings = [
        BoardSettings(
            setting_key="board_title",
            setting_value="Mon Tableau Kanban",
            description="Titre principal du tableau",
        ),
        BoardSettings(
            setting_key="theme_color",
            setting_value="#3b82f6",
            description="Couleur du thème",
        ),
        BoardSettings(
            setting_key="notifications_enabled",
            setting_value="true",
            description="Activer les notifications",
        ),
    ]

    for setting in settings:
        db_session.add(setting)
    db_session.commit()

    for setting in settings:
        db_session.refresh(setting)

    return settings


class TestBoardSettingsModel:
    """Tests pour le modèle BoardSettings."""

    def test_model_creation(self):
        """Test de création du modèle BoardSettings."""
        setting = BoardSettings()

        # Vérifier que l'objet est créé
        assert setting is not None
        assert isinstance(setting, BoardSettings)

    def test_model_attributes(self):
        """Test que le modèle a tous les attributs attendus."""
        setting = BoardSettings()

        # Vérifier que tous les attributs existent
        assert hasattr(setting, "id")
        assert hasattr(setting, "setting_key")
        assert hasattr(setting, "setting_value")
        assert hasattr(setting, "description")
        assert hasattr(setting, "created_at")
        assert hasattr(setting, "updated_at")

    def test_model_table_name(self):
        """Test que le nom de la table est correct."""
        assert BoardSettings.__tablename__ == "board_settings"

    def test_create_board_settings_successfully(self, db_session):
        """Test de création réussie d'un paramètre de tableau."""
        setting = BoardSettings(
            setting_key="test_setting",
            setting_value="test_value",
            description="Test setting description",
        )

        db_session.add(setting)
        db_session.commit()
        db_session.refresh(setting)

        assert setting.id is not None
        assert setting.setting_key == "test_setting"
        assert setting.setting_value == "test_value"
        assert setting.description == "Test setting description"
        assert setting.created_at is not None
        assert setting.updated_at is None  # Pas encore mis à jour

    def test_create_board_settings_minimal(self, db_session):
        """Test de création avec les champs minimum requis."""
        setting = BoardSettings(
            setting_key="minimal_setting", setting_value="minimal_value"
        )

        db_session.add(setting)
        db_session.commit()
        db_session.refresh(setting)

        assert setting.id is not None
        assert setting.setting_key == "minimal_setting"
        assert setting.setting_value == "minimal_value"
        assert setting.description is None  # Optionnel

    def test_board_settings_timestamps(self, db_session):
        """Test que les timestamps sont correctement gérés."""
        setting = BoardSettings(
            setting_key="timestamp_test", setting_value="timestamp_value"
        )

        db_session.add(setting)
        db_session.commit()

        # Vérifier created_at
        assert setting.created_at is not None
        assert isinstance(setting.created_at, datetime.datetime)

        # Mettre à jour pour tester updated_at
        setting.setting_value = "updated_value"
        db_session.commit()
        db_session.refresh(setting)

        # updated_at devrait maintenant être défini
        assert setting.updated_at is not None
        assert isinstance(setting.updated_at, datetime.datetime)

    def test_unique_key_constraint(self, db_session):
        """Test que la contrainte d'unicité sur setting_key fonctionne."""
        # Créer le premier paramètre
        setting1 = BoardSettings(setting_key="unique_key", setting_value="first_value")
        db_session.add(setting1)
        db_session.commit()

        # Essayer de créer un deuxième paramètre avec la même clé
        setting2 = BoardSettings(setting_key="unique_key", setting_value="second_value")
        db_session.add(setting2)

        # Devrait lever une erreur d'intégrité
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_board_settings_update(self, db_session, sample_board_settings):
        """Test de mise à jour d'un paramètre de tableau."""
        setting = sample_board_settings[0]
        original_created_at = setting.created_at

        # Mettre à jour plusieurs champs
        setting.setting_value = "Nouvelle valeur"
        setting.description = "Nouvelle description"

        db_session.commit()
        db_session.refresh(setting)

        # Vérifier les mises à jour
        assert setting.setting_value == "Nouvelle valeur"
        assert setting.description == "Nouvelle description"
        assert setting.created_at == original_created_at  # Ne devrait pas changer
        assert setting.updated_at is not None  # Devrait être mis à jour

    def test_board_settings_query(self, db_session, sample_board_settings):
        """Test de requêtes sur les paramètres de tableau."""
        # Query par clé
        setting = (
            db_session.query(BoardSettings)
            .filter(BoardSettings.setting_key == "board_title")
            .first()
        )

        assert setting is not None
        assert setting.setting_value == "Mon Tableau Kanban"

        # Query avec like
        settings = (
            db_session.query(BoardSettings)
            .filter(BoardSettings.setting_key.like("theme_%"))
            .all()
        )

        assert len(settings) == 1
        assert settings[0].setting_key == "theme_color"

    def test_board_settings_delete(self, db_session, sample_board_settings):
        """Test de suppression d'un paramètre de tableau."""
        setting = sample_board_settings[0]
        setting_id = setting.id

        db_session.delete(setting)
        db_session.commit()

        # Vérifier que le paramètre a été supprimé
        deleted_setting = (
            db_session.query(BoardSettings)
            .filter(BoardSettings.id == setting_id)
            .first()
        )
        assert deleted_setting is None

    def test_board_settings_string_fields(self, db_session):
        """Test avec des chaînes de caractères de différentes longueurs."""
        # Test avec chaînes longues
        long_key = "very_long_setting_key_" + "a" * 100
        long_value = "very_long_setting_value_" + "b" * 1000
        long_description = "very_long_description_" + "c" * 500

        setting = BoardSettings(
            setting_key=long_key, setting_value=long_value, description=long_description
        )

        db_session.add(setting)
        db_session.commit()
        db_session.refresh(setting)

        assert setting.setting_key == long_key
        assert setting.setting_value == long_value
        assert setting.description == long_description

    def test_board_settings_empty_strings(self, db_session):
        """Test avec des chaînes vides."""
        setting = BoardSettings(
            setting_key="empty_strings", setting_value="", description=""
        )

        db_session.add(setting)
        db_session.commit()

        assert setting.setting_value == ""
        assert setting.description == ""

    def test_board_settings_special_characters(self, db_session):
        """Test avec des caractères spéciaux."""
        setting = BoardSettings(
            setting_key="special_éèàçù_中文_العربية",
            setting_value="valeur_éèàçù_中文_العربية",
            description="description_éèàçù_中文_العربية",
        )

        db_session.add(setting)
        db_session.commit()

        assert setting.setting_key == "special_éèàçù_中文_العربية"
        assert setting.setting_value == "valeur_éèàçù_中文_العربية"
        assert setting.description == "description_éèàçù_中文_العربية"

    def test_board_settings_unicode_emojis(self, db_session):
        """Test avec des emojis Unicode."""
        setting = BoardSettings(
            setting_key="emoji_test_🚀",
            setting_value="valeur_avec_emojis_🎯🚀",
            description="description_📝✨",
        )

        db_session.add(setting)
        db_session.commit()

        assert setting.setting_key == "emoji_test_🚀"
        assert setting.setting_value == "valeur_avec_emojis_🎯🚀"
        assert setting.description == "description_📝✨"

    def test_board_settings_html_content(self, db_session):
        """Test avec contenu HTML."""
        html_content = "<div>HTML Content</div><script>alert('test')</script>"

        setting = BoardSettings(
            setting_key="html_test",
            setting_value=html_content,
            description="<span>HTML Description</span>",
        )

        db_session.add(setting)
        db_session.commit()

        # Le contenu HTML devrait être stocké tel quel
        assert setting.setting_value == html_content
        assert setting.description == "<span>HTML Description</span>"

    def test_board_settings_json_values(self, db_session):
        """Test avec des valeurs JSON."""
        json_value = '{"theme": "dark", "fontSize": 14, "features": ["notifications", "autosave"]}'

        setting = BoardSettings(
            setting_key="json_config",
            setting_value=json_value,
            description="Configuration JSON",
        )

        db_session.add(setting)
        db_session.commit()

        assert setting.setting_value == json_value

    def test_board_settings_boolean_values(self, db_session):
        """Test avec des valeurs booléennes (comme chaînes)."""
        setting1 = BoardSettings(setting_key="bool_true", setting_value="true")

        setting2 = BoardSettings(setting_key="bool_false", setting_value="false")

        db_session.add(setting1)
        db_session.add(setting2)
        db_session.commit()

        assert setting1.setting_value == "true"
        assert setting2.setting_value == "false"

    def test_board_settings_numeric_values(self, db_session):
        """Test avec des valeurs numériques (comme chaînes)."""
        setting = BoardSettings(
            setting_key="numeric_test",
            setting_value="42",
            description="Number as string",
        )

        db_session.add(setting)
        db_session.commit()

        assert setting.setting_value == "42"

    def test_board_settings_whitespace_handling(self, db_session):
        """Test de gestion des espaces blancs."""
        setting = BoardSettings(
            setting_key="  whitespace_key  ",
            setting_value="  whitespace_value  ",
            description="  whitespace description  ",
        )

        db_session.add(setting)
        db_session.commit()

        # Les espaces devraient être préservés
        assert setting.setting_key == "  whitespace_key  "
        assert setting.setting_value == "  whitespace_value  "
        assert setting.description == "  whitespace description  "

    def test_board_settings_null_values(self, db_session):
        """Test avec des valeurs NULL."""
        setting = BoardSettings(
            setting_key="null_test", setting_value="null_value", description=None
        )

        db_session.add(setting)
        db_session.commit()

        assert setting.setting_value == "null_value"
        assert setting.description is None

    def test_board_settings_case_sensitivity(self, db_session):
        """Test de sensibilité à la casse."""
        setting1 = BoardSettings(setting_key="CaseSensitive", setting_value="value1")

        setting2 = BoardSettings(setting_key="casesensitive", setting_value="value2")

        db_session.add(setting1)
        db_session.add(setting2)
        db_session.commit()

        # Les deux devraient coexister (clés différentes)
        assert setting1.setting_key == "CaseSensitive"
        assert setting2.setting_key == "casesensitive"

    def test_board_settings_ordering(self, db_session, sample_board_settings):
        """Test de tri des paramètres."""
        # Trier par clé
        settings = (
            db_session.query(BoardSettings).order_by(BoardSettings.setting_key).all()
        )

        keys = [s.setting_key for s in settings]
        assert keys == sorted(keys)

    def test_board_settings_pagination(self, db_session):
        """Test de pagination des résultats."""
        # Créer plusieurs paramètres
        for i in range(10):
            setting = BoardSettings(
                setting_key=f"setting_{i:03d}", setting_value=f"value_{i}"
            )
            db_session.add(setting)

        db_session.commit()

        # Test pagination
        page1 = db_session.query(BoardSettings).limit(3).all()
        page2 = db_session.query(BoardSettings).offset(3).limit(3).all()

        assert len(page1) == 3
        assert len(page2) == 3
        assert page1[0].id != page2[0].id

    def test_board_settings_count(self, db_session, sample_board_settings):
        """Test de comptage des paramètres."""
        count = db_session.query(BoardSettings).count()
        assert count == len(sample_board_settings)

    def test_board_settings_filter_by_description(
        self, db_session, sample_board_settings
    ):
        """Test de filtrage par description."""
        # Chercher les paramètres avec "Couleur" dans la description
        settings = (
            db_session.query(BoardSettings)
            .filter(BoardSettings.description.like("%Couleur%"))
            .all()
        )

        assert len(settings) == 1
        assert settings[0].setting_key == "theme_color"

    def test_board_settings_filter_by_value(self, db_session, sample_board_settings):
        """Test de filtrage par valeur."""
        # Chercher les paramètres avec "true" comme valeur
        settings = (
            db_session.query(BoardSettings)
            .filter(BoardSettings.setting_value == "true")
            .all()
        )

        assert len(settings) == 1
        assert settings[0].setting_key == "notifications_enabled"

    def test_board_settings_batch_operations(self, db_session):
        """Test d'opérations par lots."""
        # Créer plusieurs paramètres en lot
        settings = []
        for i in range(5):
            setting = BoardSettings(
                setting_key=f"batch_{i}", setting_value=f"batch_value_{i}"
            )
            settings.append(setting)

        db_session.add_all(settings)
        db_session.commit()

        # Vérifier que tous ont été créés
        count = (
            db_session.query(BoardSettings)
            .filter(BoardSettings.setting_key.like("batch_%"))
            .count()
        )
        assert count == 5

    def test_board_settings_relationships(self, db_session):
        """Test que le modèle n'a pas de relations problématiques."""
        # BoardSettings n'a pas de relations définies, mais on vérifie
        # qu'il peut être utilisé sans erreurs
        setting = BoardSettings(
            setting_key="relationship_test", setting_value="test_value"
        )

        db_session.add(setting)
        db_session.commit()

        # Pas de relations à tester, mais l'objet devrait être valide
        assert setting.id is not None

    def test_board_settings_representation(self, db_session, sample_board_settings):
        """Test de la représentation textuelle de l'objet."""
        setting = sample_board_settings[0]

        # La représentation par défaut de SQLAlchemy contient le nom de la classe
        str_repr = str(setting)
        assert "BoardSettings" in str_repr

    def test_board_settings_equality(self, db_session):
        """Test de l'égalité entre objets."""
        setting1 = BoardSettings(setting_key="equality_test_1", setting_value="value1")

        setting2 = BoardSettings(setting_key="equality_test_2", setting_value="value2")

        db_session.add(setting1)
        db_session.add(setting2)
        db_session.commit()

        # Ce sont des objets différents
        assert setting1 != setting2
        assert setting1.id != setting2.id

    def test_board_settings_database_constraints(self, db_session):
        """Test des contraintes de base de données."""
        # Test que setting_key ne peut pas être NULL
        setting = BoardSettings(
            setting_key=None, setting_value="test"
        )  # Devrait échouer

        db_session.add(setting)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Test que setting_value ne peut pas être NULL
        setting = BoardSettings(
            setting_key="test_key", setting_value=None
        )  # Devrait échouer

        db_session.add(setting)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_board_settings_transactions(self, db_session):
        """Test de transactions."""
        # Créer un paramètre
        setting = BoardSettings(
            setting_key="transaction_test", setting_value="original_value"
        )
        db_session.add(setting)
        db_session.commit()

        # Modifier dans une transaction
        setting.setting_value = "modified_value"

        # Faire un rollback
        db_session.rollback()
        db_session.refresh(setting)

        # La valeur devrait être celle d'avant la modification
        assert setting.setting_value == "original_value"

    def test_board_settings_concurrent_access(self, db_session):
        """Test d'accès concurrent (simplifié)."""
        # Créer un paramètre
        setting = BoardSettings(
            setting_key="concurrent_test", setting_value="initial_value"
        )
        db_session.add(setting)
        db_session.commit()

        # Simuler des modifications concurrentes
        setting1 = (
            db_session.query(BoardSettings)
            .filter(BoardSettings.setting_key == "concurrent_test")
            .first()
        )

        setting2 = (
            db_session.query(BoardSettings)
            .filter(BoardSettings.setting_key == "concurrent_test")
            .first()
        )

        # Les deux devraient être le même objet
        assert setting1.id == setting2.id

        # Modifier à travers la première référence
        setting1.setting_value = "concurrent_modification_1"
        db_session.commit()

        # Rafraîchir la deuxième référence
        db_session.refresh(setting2)

        # La deuxième référence devrait voir la modification
        assert setting2.setting_value == "concurrent_modification_1"

    def test_board_settings_error_handling(self, db_session):
        """Test de gestion des erreurs."""
        # Simuler une erreur de base de données
        with patch.object(
            db_session, "commit", side_effect=SQLAlchemyError("Database error")
        ):
            setting = BoardSettings(
                setting_key="error_test", setting_value="test_value"
            )

            db_session.add(setting)
            with pytest.raises(SQLAlchemyError):
                db_session.commit()

    def test_board_settings_session_isolation(self, db_session):
        """Test d'isolation des sessions."""
        # Créer un paramètre
        setting = BoardSettings(
            setting_key="session_test", setting_value="session_value"
        )
        db_session.add(setting)

        # Ne pas commiter encore
        # L'objet ne devrait pas être visible dans une nouvelle session
        new_session = TestingSessionLocal()
        try:
            count = (
                new_session.query(BoardSettings)
                .filter(BoardSettings.setting_key == "session_test")
                .count()
            )
            assert count == 0
        finally:
            new_session.close()

        # Commiter maintenant
        db_session.commit()

        # Maintenant il devrait être visible
        new_session = TestingSessionLocal()
        try:
            count = (
                new_session.query(BoardSettings)
                .filter(BoardSettings.setting_key == "session_test")
                .count()
            )
            assert count == 1
        finally:
            new_session.close()

    def test_board_settings_validation_at_application_level(self, db_session):
        """Test de la validation au niveau applicatif."""
        # Le modèle SQLAlchemy lui-même n'a pas de validation Pydantic
        # mais on peut tester des contraintes de base
        setting = BoardSettings(
            setting_key="validation_test", setting_value="x" * 10000
        )  # Très longue valeur

        # Devrait fonctionner (pas de limitation de longueur dans le modèle)
        db_session.add(setting)
        db_session.commit()

        assert len(setting.setting_value) == 10000

    def test_board_settings_cascade_operations(self, db_session):
        """Test des opérations en cascade."""
        # BoardSettings n'a pas de relations, donc pas de cascade à tester
        # Mais on vérifie que les opérations de base fonctionnent
        setting = BoardSettings(
            setting_key="cascade_test", setting_value="cascade_value"
        )

        db_session.add(setting)
        db_session.commit()

        setting_id = setting.id

        # Supprimer
        db_session.delete(setting)
        db_session.commit()

        # Vérifier que l'objet est bien supprimé
        deleted = (
            db_session.query(BoardSettings)
            .filter(BoardSettings.id == setting_id)
            .first()
        )
        assert deleted is None

    def test_board_settings_index_usage(self, db_session, sample_board_settings):
        """Test que les index sont utilisés efficacement."""
        # Cette test est plus difficile à vérifier directement
        # mais on peut vérifier que les requêtes fonctionnent

        # Recherche par clé (devrait utiliser l'index)
        setting = (
            db_session.query(BoardSettings)
            .filter(BoardSettings.setting_key == "board_title")
            .first()
        )

        assert setting is not None
        assert setting.setting_value == "Mon Tableau Kanban"

    def test_board_settings_bulk_update(self, db_session):
        """Test de mises à jour en masse."""
        # Créer plusieurs paramètres
        settings = []
        for i in range(3):
            setting = BoardSettings(
                setting_key=f"bulk_update_{i}", setting_value=f"initial_{i}"
            )
            settings.append(setting)

        db_session.add_all(settings)
        db_session.commit()

        # Mettre à jour en masse
        db_session.query(BoardSettings).filter(
            BoardSettings.setting_key.like("bulk_update_%")
        ).update({"setting_value": "bulk_updated"})

        db_session.commit()

        # Vérifier les mises à jour
        updated_settings = (
            db_session.query(BoardSettings)
            .filter(BoardSettings.setting_key.like("bulk_update_%"))
            .all()
        )

        for setting in updated_settings:
            assert setting.setting_value == "bulk_updated"

    def test_board_settings_data_types(self, db_session):
        """Test avec différents types de données."""
        test_data = [
            ("string_type", "simple_string"),
            ("numeric_string", "123.45"),
            ("boolean_string", "true"),
            ("json_string", '{"key": "value"}'),
            ("empty_string", ""),
            ("whitespace_string", "   "),
            ("unicode_string", "unicode_éèàçù"),
        ]

        for key, value in test_data:
            setting = BoardSettings(setting_key=key, setting_value=value)
            db_session.add(setting)

        db_session.commit()

        # Vérifier que toutes les valeurs sont stockées correctement
        for key, expected_value in test_data:
            setting = (
                db_session.query(BoardSettings)
                .filter(BoardSettings.setting_key == key)
                .first()
            )
            assert setting is not None
            assert setting.setting_value == expected_value

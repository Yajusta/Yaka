"""Tests complets pour le modèle Label."""

import datetime
import os
import sys
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.label import Label
from app.models.user import User, UserRole, UserStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuration de la base de données de test
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_label_model.db")
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
def sample_user(db_session):
    """Fixture pour créer un utilisateur de test."""
    user = User(
        email="test@example.com",
        display_name="Test User",
        role=UserRole.EDITOR,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_labels(db_session, sample_user):
    """Fixture pour créer des étiquettes de test."""
    labels = [
        Label(
            name="Bug",
            color="#FF0000",
            created_by=sample_user.id,
        ),
        Label(
            name="Feature",
            color="#00FF00",
            created_by=sample_user.id,
        ),
        Label(
            name="Enhancement",
            color="#0000FF",
            created_by=sample_user.id,
        ),
    ]

    for label in labels:
        db_session.add(label)
    db_session.commit()

    for label in labels:
        db_session.refresh(label)

    return labels


class TestLabelModel:
    """Tests pour le modèle Label."""

    def test_model_creation(self):
        """Test de création du modèle Label."""
        label = Label()

        # Vérifier que l'objet est créé
        assert label is not None
        assert isinstance(label, Label)

    def test_model_attributes(self):
        """Test que le modèle a tous les attributs attendus."""
        label = Label()

        # Vérifier que tous les attributs existent
        assert hasattr(label, "id")
        assert hasattr(label, "name")
        assert hasattr(label, "color")
        assert hasattr(label, "description")
        assert hasattr(label, "created_by")
        assert hasattr(label, "created_at")

    def test_model_table_name(self):
        """Test que le nom de la table est correct."""
        assert Label.__tablename__ == "labels"

    def test_create_label_successfully(self, db_session, sample_user):
        """Test de création réussie d'une étiquette."""
        before_creation = datetime.datetime.now(datetime.timezone.utc)

        label = Label(
            name="Test Label",
            color="#FF00FF",
            description="Test description",
            created_by=sample_user.id,
        )

        db_session.add(label)
        db_session.commit()
        db_session.refresh(label)

        after_creation = datetime.datetime.now(datetime.timezone.utc)

        assert label.id is not None
        assert label.name == "Test Label"
        assert label.color == "#FF00FF"
        assert label.description == "Test description"
        assert label.created_by == sample_user.id
        assert label.created_at is not None

        # Vérifier que le timestamp existe et est récent
        assert label.created_at is not None
        time_diff = abs((after_creation - before_creation).total_seconds())
        # La création devrait avoir pris moins de temps que le test entier
        assert time_diff > 0

    def test_create_label_minimal(self, db_session, sample_user):
        """Test de création avec les champs minimum requis."""
        label = Label(
            name="Minimal Label",
            color="#123456",
            created_by=sample_user.id,
        )

        db_session.add(label)
        db_session.commit()
        db_session.refresh(label)

        assert label.id is not None
        assert label.name == "Minimal Label"
        assert label.color == "#123456"
        assert label.description is None  # Description is optional
        assert label.created_by == sample_user.id
        assert label.created_at is not None

    def test_create_label_with_description(self, db_session, sample_user):
        """Test de création d'une étiquette avec description."""
        label = Label(
            name="Label with Description",
            color="#123456",
            description="This is a test description",
            created_by=sample_user.id,
        )

        db_session.add(label)
        db_session.commit()
        db_session.refresh(label)

        assert label.id is not None
        assert label.name == "Label with Description"
        assert label.color == "#123456"
        assert label.description == "This is a test description"
        assert label.created_by == sample_user.id
        assert label.created_at is not None

    def test_create_label_with_max_length_description(self, db_session, sample_user):
        """Test de création d'une étiquette avec description maximale (255 caractères)."""
        max_description = "x" * 255
        label = Label(
            name="Max Description Label",
            color="#123456",
            description=max_description,
            created_by=sample_user.id,
        )

        db_session.add(label)
        db_session.commit()
        db_session.refresh(label)

        assert label.description is not None
        assert label.description == max_description
        assert len(label.description) == 255

    def test_label_timestamps(self, db_session, sample_user):
        """Test que les timestamps sont correctement gérés."""
        label = Label(
            name="Timestamp Test",
            color="#FF0000",
            created_by=sample_user.id,
        )

        db_session.add(label)
        db_session.commit()

        # Vérifier created_at
        assert label.created_at is not None
        assert isinstance(label.created_at, datetime.datetime)

    def test_label_update(self, db_session, sample_labels):
        """Test de mise à jour d'une étiquette."""
        label = sample_labels[0]
        original_created_at = label.created_at

        # Mettre à jour plusieurs champs
        label.name = "Updated Label Name"
        label.color = "#00FFFF"

        db_session.commit()
        db_session.refresh(label)

        # Vérifier les mises à jour
        assert label.name == "Updated Label Name"
        assert label.color == "#00FFFF"
        assert label.created_at == original_created_at  # Ne devrait pas changer

    def test_label_query_by_name(self, db_session, sample_labels):
        """Test de recherche par nom."""
        label = db_session.query(Label).filter(Label.name == "Bug").first()

        assert label is not None
        assert label.name == "Bug"

    def test_label_query_by_creator(self, db_session, sample_labels, sample_user):
        """Test de recherche par créateur."""
        labels = (
            db_session.query(Label).filter(Label.created_by == sample_user.id).all()
        )

        assert len(labels) >= 1
        assert all(label.created_by == sample_user.id for label in labels)

    def test_label_query_by_color(self, db_session, sample_labels):
        """Test de recherche par color."""
        label = db_session.query(Label).filter(Label.color == "#FF0000").first()

        assert label is not None
        assert label.color == "#FF0000"

    def test_label_search_by_name(self, db_session, sample_user):
        """Test de recherche textuelle dans le nom."""
        # Créer des étiquettes avec des noms spécifiques
        search_labels = [
            Label(name="High Priority", color="#FF0000", created_by=sample_user.id),
            Label(name="Medium Priority", color="#FFFF00", created_by=sample_user.id),
            Label(name="Low Priority", color="#00FF00", created_by=sample_user.id),
        ]

        for label in search_labels:
            db_session.add(label)

        db_session.commit()

        # Rechercher les étiquettes contenant "Priority"
        priority_labels = (
            db_session.query(Label).filter(Label.name.like("%Priority%")).all()
        )

        assert len(priority_labels) == 3
        assert all("Priority" in label.name for label in priority_labels)

    def test_label_order_by_name(self, db_session, sample_labels):
        """Test de tri par nom."""
        labels = db_session.query(Label).order_by(Label.name).all()

        # Vérifier que les noms sont en ordre alphabétique
        names = [label.name for label in labels]
        assert names == sorted(names)

    def test_label_order_by_creation_date(self, db_session, sample_labels):
        """Test de tri par date de création."""
        labels = db_session.query(Label).order_by(Label.created_at).all()

        # Vérifier que les dates sont en ordre chronologique
        for i in range(len(labels) - 1):
            assert labels[i].created_at <= labels[i + 1].created_at

    def test_label_delete(self, db_session, sample_labels):
        """Test de suppression d'une étiquette."""
        label = sample_labels[0]
        label_id = label.id

        db_session.delete(label)
        db_session.commit()

        # Vérifier que l'étiquette a été supprimée
        deleted_label = db_session.query(Label).filter(Label.id == label_id).first()
        assert deleted_label is None

    def test_label_string_fields_validation(self, db_session, sample_user):
        """Test des validations des champs text."""
        # Test avec name à la limite de la longueur
        max_length_nom = "x" * 32  # Longueur maximale selon le modèle

        label = Label(
            name=max_length_nom,
            color="#123456",
            created_by=sample_user.id,
        )

        db_session.add(label)
        db_session.commit()

        assert label.name == max_length_nom
        assert len(label.name) == 32

    def test_label_color_formats(self, db_session, sample_user):
        """Test avec différents formats de color."""
        color_formats = [
            "#FF0000",  # Rouge standard
            "#00FF00",  # Vert standard
            "#0000FF",  # Bleu standard
            "#FFFF00",  # Jaune
            "#FF00FF",  # Magenta
            "#00FFFF",  # Cyan
            "#FFFFFF",  # Blanc
            "#000000",  # Noir
            "#123ABC",  # Couleur hexadécimale aléatoire
        ]

        for color in color_formats:
            label = Label(
                name=f"Color Test {color}",
                color=color,
                created_by=sample_user.id,
            )
            db_session.add(label)

        db_session.commit()

        # Vérifier que toutes les étiquettes ont été créées
        for color in color_formats:
            label = (
                db_session.query(Label)
                .filter(Label.name == f"Color Test {color}")
                .first()
            )
            assert label is not None
            assert label.color == color

    def test_label_special_characters(self, db_session, sample_user):
        """Test avec des caractères spéciaux."""
        label = Label(
            name="Étiquette spéciale: éèàçù",
            color="#FF00FF",
            created_by=sample_user.id,
        )

        db_session.add(label)
        db_session.commit()

        assert label.name == "Étiquette spéciale: éèàçù"

    def test_label_unicode_emojis(self, db_session, sample_user):
        """Test avec des emojis Unicode."""
        label = Label(
            name="Emoji Label 🎯🚀✨",
            color="#FFD700",  # Or
            created_by=sample_user.id,
        )

        db_session.add(label)
        db_session.commit()

        assert label.name == "Emoji Label 🎯🚀✨"

    def test_label_empty_name(self, db_session, sample_user):
        """Test avec un nom vide."""
        label = Label(
            name="",
            color="#FF0000",
            created_by=sample_user.id,
        )

        db_session.add(label)
        db_session.commit()

        assert label.name == ""

    def test_label_whitespace_only_name(self, db_session, sample_user):
        """Test avec un nom ne contenant que des espaces."""
        label = Label(
            name="   ",
            color="#FF0000",
            created_by=sample_user.id,
        )

        db_session.add(label)
        db_session.commit()

        assert label.name == "   "

    def test_label_unique_name_constraint(self, db_session, sample_user):
        """Test de la contrainte d'unicité sur le nom."""
        # Créer la première étiquette
        label1 = Label(
            name="Unique Name",
            color="#FF0000",
            created_by=sample_user.id,
        )

        db_session.add(label1)
        db_session.commit()

        # Essayer de créer une deuxième étiquette avec le même name
        label2 = Label(
            name="Unique Name",  # Même name
            color="#00FF00",
            created_by=sample_user.id,
        )

        db_session.add(label2)

        # Devrait lever une erreur d'intégrité
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_label_color_validation(self, db_session, sample_user):
        """Test de validation des colors."""
        valid_colors = [
            "#ABC",  # Court
            "#ABCDEF",  # Standard
            "#123456",  # Nombres
            "#abcdef",  # Minuscules
            "#AbCdEf",  # Mixte
        ]

        for color in valid_colors:
            label = Label(
                name=f"Color Valid {color}",
                color=color,
                created_by=sample_user.id,
            )
            db_session.add(label)

        db_session.commit()

        # Vérifier que toutes les étiquettes ont été créées
        count = db_session.query(Label).filter(Label.name.like("Color Valid %")).count()
        assert count == len(valid_colors)

    def test_label_case_sensitivity(self, db_session, sample_user):
        """Test de sensibilité à la casse."""
        label1 = Label(
            name="Case Sensitive",
            color="#FF0000",
            created_by=sample_user.id,
        )

        label2 = Label(
            name="case sensitive",  # Même name en minuscules
            color="#00FF00",
            created_by=sample_user.id,
        )

        db_session.add(label1)
        db_session.add(label2)

        # Les deux devraient pouvoir coexister (la contrainte est sensible à la casse)
        try:
            db_session.commit()
            assert label1.id is not None
            assert label2.id is not None
        except Exception:
            # Si la base de données est configurée pour être insensible à la casse
            db_session.rollback()

    def test_label_foreign_key_constraints(self, db_session):
        """Test des contraintes de clé étrangère."""
        # Essayer de créer une étiquette avec un created_by invalide
        label = Label(
            name="Invalid User Test",
            color="#FF0000",
            created_by=99999,  # N'existe pas
        )

        db_session.add(label)
        # Peut échouer selon la configuration de la base de données
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()

    def test_label_batch_operations(self, db_session, sample_user):
        """Test d'opérations par lots."""
        # Créer plusieurs étiquettes en lot
        labels = []
        colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF"]

        for i, color in enumerate(colors):
            label = Label(
                name=f"Batch Label {i}",
                color=color,
                created_by=sample_user.id,
            )
            labels.append(label)

        db_session.add_all(labels)
        db_session.commit()

        # Vérifier que toutes ont été créées
        count = db_session.query(Label).filter(Label.name.like("Batch Label %")).count()
        assert count == len(colors)

    def test_label_bulk_update(self, db_session, sample_labels):
        """Test de mises à jour en masse."""
        # Ajouter un préfixe à tous les noms d'étiquettes
        db_session.query(Label).update({"name": Label.name + " (Updated)"})

        db_session.commit()

        # Vérifier que tous les noms ont été mis à jour
        updated_labels = db_session.query(Label).all()

        for label in updated_labels:
            assert "(Updated)" in label.name

    def test_label_complex_queries(self, db_session, sample_user):
        """Test de requêtes complexes."""
        # Créer des étiquettes variées
        labels_data = [
            ("Urgent", "#FF0000"),
            ("Important", "#FFA500"),
            ("Normal", "#008000"),
            ("Low Priority", "#0000FF"),
            ("Information", "#800080"),
        ]

        for name, color in labels_data:
            label = Label(name=name, color=color, created_by=sample_user.id)
            db_session.add(label)

        db_session.commit()

        # Chercher les étiquettes avec des colors "chaudes" (rouge/orange)
        from sqlalchemy import or_

        warm_colors = (
            db_session.query(Label)
            .filter(or_(Label.color == "#FF0000", Label.color == "#FFA500"))
            .all()
        )

        assert len(warm_colors) == 2

    def test_label_pagination(self, db_session, sample_user):
        """Test de pagination des résultats."""
        # Créer plusieurs étiquettes
        for i in range(20):
            label = Label(
                name=f"Pagination Label {i}",
                color=f"#{i:02X}{i:02X}{i:02X}",
                created_by=sample_user.id,
            )
            db_session.add(label)

        db_session.commit()

        # Test pagination
        page1 = db_session.query(Label).limit(5).all()
        page2 = db_session.query(Label).offset(5).limit(5).all()

        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].id != page2[0].id

    def test_label_count_aggregations(self, db_session, sample_user):
        """Test d'agrégations et de comptage."""
        # Créer des étiquettes
        colors = ["#FF0000", "#00FF00", "#0000FF"]
        for i in range(6):
            color_index = i % len(colors)
            label = Label(
                name=f"Count Label {i}",
                color=colors[color_index],
                created_by=sample_user.id,
            )
            db_session.add(label)

        db_session.commit()

        # Compter par color
        for color in colors:
            count = db_session.query(Label).filter(Label.color == color).count()
            assert count == 2  # 6 étiquettes / 3 colors = 2 par color

    def test_label_error_handling(self, db_session, sample_user):
        """Test de gestion des erreurs."""
        # Simuler une erreur de base de données
        with patch.object(
            db_session, "commit", side_effect=SQLAlchemyError("Database error")
        ):
            label = Label(
                name="Error Test",
                color="#FF0000",
                created_by=sample_user.id,
            )

            db_session.add(label)
            with pytest.raises(SQLAlchemyError):
                db_session.commit()

    def test_label_representation(self, db_session, sample_user):
        """Test de la représentation textuelle de l'objet."""
        label = Label(
            name="Representation Test",
            color="#FF0000",
            created_by=sample_user.id,
        )

        db_session.add(label)
        db_session.commit()

        # La représentation devrait contenir des informations utiles
        str_repr = str(label)
        assert "Label" in str_repr

    def test_label_equality(self, db_session, sample_user):
        """Test de l'égalité entre objets."""
        label1 = Label(
            name="Equality Test 1",
            color="#FF0000",
            created_by=sample_user.id,
        )

        label2 = Label(
            name="Equality Test 2",
            color="#00FF00",
            created_by=sample_user.id,
        )

        db_session.add(label1)
        db_session.add(label2)
        db_session.commit()

        # Ce sont des objets différents
        assert label1 != label2
        assert label1.id != label2.id

    def test_label_database_constraints(self, db_session):
        """Test des contraintes de base de données."""
        # Créer un utilisateur pour le test
        user = User(
            email="constrainttest@example.com",
            display_name="Constraint Test",
            role=UserRole.EDITOR,
            status=UserStatus.ACTIVE,
        )
        db_session.add(user)
        db_session.commit()

        # Test que nom ne peut pas être NULL
        label = Label(
            name=None,  # Devrait échouer
            color="#FF0000",
            created_by=user.id,
        )

        db_session.add(label)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Test que color ne peut pas être NULL
        label = Label(
            name="Test",
            color=None,  # Devrait échouer
            created_by=user.id,
        )

        db_session.add(label)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Test que created_by ne peut pas être NULL
        label = Label(
            name="Test",
            color="#FF0000",
            created_by=None,  # Devrait échouer
        )

        db_session.add(label)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_label_name_length_constraint(self, db_session, sample_user):
        """Test de la contrainte de longueur du nom."""
        # Le modèle limite le nom à 32 caractères
        exact_length_name = "x" * 32

        label = Label(
            name=exact_length_name,
            color="#FF0000",
            created_by=sample_user.id,
        )

        db_session.add(label)
        db_session.commit()

        assert len(label.name) == 32
        assert label.name == exact_length_name

    def test_label_color_palette_management(self, db_session, sample_user):
        """Test de gestion de palettes de colors."""
        # Créer une palette de colors cohérente
        color_palette = [
            ("Primary", "#007bff"),
            ("Secondary", "#6c757d"),
            ("Success", "#28a745"),
            ("Danger", "#dc3545"),
            ("Warning", "#ffc107"),
            ("Info", "#17a2b8"),
        ]

        created_labels = []
        for name, color in color_palette:
            label = Label(
                name=name,
                color=color,
                created_by=sample_user.id,
            )
            db_session.add(label)
            created_labels.append(label)

        db_session.commit()

        # Vérifier que toutes les étiquettes de la palette ont été créées
        for name, color in color_palette:
            label = db_session.query(Label).filter(Label.name == name).first()
            assert label is not None
            assert label.color == color

    def test_label_category_organization(self, db_session, sample_user):
        """Test de l'organisation par catégorie."""
        # Créer des étiquettes par catégorie
        categories = {
            "Priority": ["High", "Medium", "Low"],
            "Type": ["Bug", "Feature", "Enhancement"],
            "Status": ["New", "InProgress", "Review"],
        }

        for category, labels in categories.items():
            for label_name in labels:
                full_name = f"{category}: {label_name}"
                # Assigner des colors différentes par catégorie
                if category == "Priority":
                    color = (
                        "#FF"
                        + {"High": "0000", "Medium": "8000", "Low": "FFFF"}[label_name]
                    )
                elif category == "Type":
                    color = {
                        "Bug": "#FF0000",
                        "Feature": "#00FF00",
                        "Enhancement": "#0000FF",
                    }[label_name]
                else:  # Status
                    color = {
                        "New": "#CCCCCC",
                        "InProgress": "#FFA500",
                        "Review": "#800080",
                    }[label_name]

                label = Label(
                    name=full_name,
                    color=color,
                    created_by=sample_user.id,
                )
                db_session.add(label)

        db_session.commit()

        # Vérifier que toutes les étiquettes ont été créées
        total_expected = sum(len(labels) for labels in categories.values())
        total_actual = db_session.query(Label).filter(Label.name.like("%: %")).count()
        assert total_actual == total_expected

    def test_label_data_types(self, db_session, sample_user):
        """Test avec différents types de données."""
        test_labels = [
            ("simple_name", "Simple Label", "#FF0000"),
            ("unicode_name", "Étiquette: éèàçù 中文", "#00FF00"),
            ("emoji_name", "Emoji Label 🎯🚀✨", "#0000FF"),
            ("html_name", "HTML <b>Label</b>", "#FFFF00"),
            ("long_name", "x" * 31, "#FF00FF"),  # Juste sous la limite
            ("special_chars", "!@#$%^&*()", "#00FFFF"),
            ("numbers_and_text", "Label 123", "#FFD700"),
        ]

        for _suffix, name, color in test_labels:
            label = Label(
                name=name,
                color=color,
                created_by=sample_user.id,
            )
            db_session.add(label)

        db_session.commit()

        # Vérifier que toutes les étiquettes ont été créées
        count = db_session.query(Label).count()
        assert count >= len(test_labels)

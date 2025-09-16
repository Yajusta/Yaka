"""Tests pour le service Label."""

import pytest
import sys
import os
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.label import Label
from app.models.user import User, UserRole, UserStatus
from app.schemas import LabelCreate, LabelUpdate
from app.services.label import (
    get_label,
    get_labels,
    get_label_by_name,
    create_label,
    update_label,
    delete_label,
)

# Configuration de la base de données de test
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_label.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
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
        password_hash="hashed_password",
        display_name="Test User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_labels(db_session, sample_user):
    """Fixture pour créer des libellés d'exemple."""
    labels = [
        Label(nom="Urgent", couleur="#FF0000", created_by=sample_user.id),
        Label(nom="Important", couleur="#FFA500", created_by=sample_user.id),
        Label(nom="Faible priorité", couleur="#00FF00", created_by=sample_user.id),
    ]

    for label in labels:
        db_session.add(label)
    db_session.commit()

    for label in labels:
        db_session.refresh(label)

    return labels


class TestGetLabel:
    """Tests pour la fonction get_label."""

    def test_get_existing_label(self, db_session, sample_labels):
        """Test de récupération d'un libellé existant."""
        label = get_label(db_session, sample_labels[0].id)
        assert label is not None
        assert label.id == sample_labels[0].id
        assert label.nom == "Urgent"
        assert label.couleur == "#FF0000"
        assert label.created_by == sample_labels[0].created_by

    def test_get_nonexistent_label(self, db_session):
        """Test de récupération d'un libellé qui n'existe pas."""
        label = get_label(db_session, 999)
        assert label is None

    def test_get_label_with_zero_id(self, db_session):
        """Test de récupération d'un libellé avec ID 0."""
        label = get_label(db_session, 0)
        assert label is None

    def test_get_label_with_negative_id(self, db_session):
        """Test de récupération d'un libellé avec ID négatif."""
        label = get_label(db_session, -1)
        assert label is None


class TestGetLabels:
    """Tests pour la fonction get_labels."""

    def test_get_all_labels(self, db_session, sample_labels):
        """Test de récupération de tous les libellés."""
        labels = get_labels(db_session)
        assert len(labels) == 3
        noms = [label.nom for label in labels]
        assert "Urgent" in noms
        assert "Important" in noms
        assert "Faible priorité" in noms

    def test_get_labels_with_pagination(self, db_session, sample_labels):
        """Test de récupération des libellés avec pagination."""
        labels = get_labels(db_session, skip=1, limit=2)
        assert len(labels) == 2

    def test_get_labels_skip_all(self, db_session, sample_labels):
        """Test de récupération des libellés en sautant tout."""
        labels = get_labels(db_session, skip=10, limit=5)
        assert len(labels) == 0

    def test_get_labels_empty_database(self, db_session):
        """Test de récupération des libellés d'une base vide."""
        labels = get_labels(db_session)
        assert len(labels) == 0

    def test_get_labels_with_zero_limit(self, db_session, sample_labels):
        """Test de récupération des libellés avec limite 0."""
        labels = get_labels(db_session, skip=0, limit=0)
        assert len(labels) == 0

    def test_get_labels_with_negative_skip(self, db_session, sample_labels):
        """Test de récupération des libellés avec skip négatif."""
        labels = get_labels(db_session, skip=-1, limit=5)
        # Devrait quand même fonctionner car la base de données gère les négatifs
        assert len(labels) == 3


class TestGetLabelByName:
    """Tests pour la fonction get_label_by_name."""

    def test_get_existing_label_by_name(self, db_session, sample_labels):
        """Test de récupération d'un libellé existant par nom."""
        label = get_label_by_name(db_session, "Urgent")
        assert label is not None
        assert label.nom == "Urgent"
        assert label.couleur == "#FF0000"

    def test_get_nonexistent_label_by_name(self, db_session):
        """Test de récupération d'un libellé qui n'existe pas par nom."""
        label = get_label_by_name(db_session, "Nonexistent")
        assert label is None

    def test_get_label_by_empty_name(self, db_session):
        """Test de récupération d'un libellé avec nom vide."""
        label = get_label_by_name(db_session, "")
        assert label is None

    def test_get_label_by_case_sensitive_name(self, db_session, sample_labels):
        """Test de récupération d'un libellé avec sensibilité à la casse."""
        label = get_label_by_name(db_session, "urgent")  # minuscule
        assert label is None  # Le nom est "Urgent" avec majuscule

    def test_get_label_by_name_with_special_characters(self, db_session, sample_user):
        """Test de récupération d'un libellé avec caractères spéciaux."""
        special_label = Label(nom="Test Spécial", couleur="#123456", created_by=sample_user.id)
        db_session.add(special_label)
        db_session.commit()
        
        label = get_label_by_name(db_session, "Test Spécial")
        assert label is not None
        assert label.nom == "Test Spécial"


class TestCreateLabel:
    """Tests pour la fonction create_label."""

    def test_create_label_successfully(self, db_session, sample_user):
        """Test de création réussie d'un libellé."""
        label_data = LabelCreate(nom="Nouveau libellé", couleur="#FF00FF")
        label = create_label(db_session, label_data, sample_user.id)

        assert label.id is not None
        assert label.nom == "Nouveau libellé"
        assert label.couleur == "#FF00FF"
        assert label.created_by == sample_user.id
        assert label.created_at is not None

    def test_create_label_with_different_user(self, db_session, sample_user):
        """Test de création d'un libellé avec un autre utilisateur."""
        other_user = User(
            email="other@example.com",
            password_hash="hashed_password",
            display_name="Other User",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        label_data = LabelCreate(nom="Autre libellé", couleur="#00FFFF")
        label = create_label(db_session, label_data, other_user.id)

        assert label.created_by == other_user.id

    def test_create_label_with_minimal_data(self, db_session, sample_user):
        """Test de création d'un libellé avec données minimales."""
        label_data = LabelCreate(nom="Simple", couleur="#000000")
        label = create_label(db_session, label_data, sample_user.id)

        assert label.nom == "Simple"
        assert label.couleur == "#000000"

    def test_create_label_duplicate_name(self, db_session, sample_labels, sample_user):
        """Test de création d'un libellé avec nom en double."""
        label_data = LabelCreate(nom="Urgent", couleur="#FF0000")
        
        with pytest.raises(SQLAlchemyError):
            create_label(db_session, label_data, sample_user.id)

    def test_create_label_with_long_name(self, db_session, sample_user):
        """Test de création d'un libellé avec nom long (32 caractères)."""
        long_name = "A" * 32  # Longueur maximale autorisée
        label_data = LabelCreate(nom=long_name, couleur="#FF0000")
        label = create_label(db_session, label_data, sample_user.id)

        assert label.nom == long_name

    def test_create_label_with_unicode_name(self, db_session, sample_user):
        """Test de création d'un libellé avec nom unicode."""
        label_data = LabelCreate(nom="测试标签", couleur="#FF0000")
        label = create_label(db_session, label_data, sample_user.id)

        assert label.nom == "测试标签"

    def test_create_label_with_emoji_in_name(self, db_session, sample_user):
        """Test de création d'un libellé avec emoji dans le nom."""
        label_data = LabelCreate(nom="🚀 Urgent", couleur="#FF0000")
        label = create_label(db_session, label_data, sample_user.id)

        assert label.nom == "🚀 Urgent"

    def test_create_label_invalid_user_id(self, db_session):
        """Test de création d'un libellé avec ID utilisateur invalide."""
        label_data = LabelCreate(nom="Test", couleur="#FF0000")
        
        # Devrait quand même créer le libellé même si l'utilisateur n'existe pas
        # car la contrainte est au niveau de la base de données
        label = create_label(db_session, label_data, 999)
        assert label.created_by == 999

    def test_create_label_with_zero_user_id(self, db_session):
        """Test de création d'un libellé avec ID utilisateur 0."""
        label_data = LabelCreate(nom="Test", couleur="#FF0000")
        label = create_label(db_session, label_data, 0)
        assert label.created_by == 0

    def test_create_label_with_negative_user_id(self, db_session):
        """Test de création d'un libellé avec ID utilisateur négatif."""
        label_data = LabelCreate(nom="Test", couleur="#FF0000")
        label = create_label(db_session, label_data, -1)
        assert label.created_by == -1


class TestUpdateLabel:
    """Tests pour la fonction update_label."""

    def test_update_label_name(self, db_session, sample_labels):
        """Test de mise à jour du nom d'un libellé."""
        label_id = sample_labels[0].id
        update_data = LabelUpdate(nom="Nouveau nom")
        
        label = update_label(db_session, label_id, update_data)
        
        assert label is not None
        assert label.nom == "Nouveau nom"
        assert label.couleur == sample_labels[0].couleur  # La couleur ne change pas

    def test_update_label_color(self, db_session, sample_labels):
        """Test de mise à jour de la couleur d'un libellé."""
        label_id = sample_labels[0].id
        update_data = LabelUpdate(couleur="#123456")
        
        label = update_label(db_session, label_id, update_data)
        
        assert label is not None
        assert label.couleur == "#123456"
        assert label.nom == sample_labels[0].nom  # Le nom ne change pas

    def test_update_label_both_fields(self, db_session, sample_labels):
        """Test de mise à jour des deux champs d'un libellé."""
        label_id = sample_labels[0].id
        update_data = LabelUpdate(nom="Complètement nouveau", couleur="#ABCDEF")
        
        label = update_label(db_session, label_id, update_data)
        
        assert label is not None
        assert label.nom == "Complètement nouveau"
        assert label.couleur == "#ABCDEF"

    def test_update_nonexistent_label(self, db_session):
        """Test de mise à jour d'un libellé qui n'existe pas."""
        update_data = LabelUpdate(nom="Test")
        label = update_label(db_session, 999, update_data)
        assert label is None

    def test_update_label_with_empty_update(self, db_session, sample_labels):
        """Test de mise à jour d'un libellé avec données vides."""
        label_id = sample_labels[0].id
        original_label = get_label(db_session, label_id)
        update_data = LabelUpdate()  # Pas de champs à mettre à jour
        
        label = update_label(db_session, label_id, update_data)
        
        assert label is not None
        assert label.nom == original_label.nom
        assert label.couleur == original_label.couleur

    def test_update_label_with_same_values(self, db_session, sample_labels):
        """Test de mise à jour d'un libellé avec les mêmes valeurs."""
        label_id = sample_labels[0].id
        update_data = LabelUpdate(nom=sample_labels[0].nom, couleur=sample_labels[0].couleur)
        
        label = update_label(db_session, label_id, update_data)
        
        assert label is not None
        assert label.nom == sample_labels[0].nom
        assert label.couleur == sample_labels[0].couleur

    def test_update_label_with_unicode(self, db_session, sample_labels):
        """Test de mise à jour d'un libellé avec caractères unicode."""
        label_id = sample_labels[0].id
        update_data = LabelUpdate(nom="测试", couleur="#测试")
        
        label = update_label(db_session, label_id, update_data)
        
        assert label is not None
        assert label.nom == "测试"
        assert label.couleur == "#测试"

    def test_update_label_with_emoji(self, db_session, sample_labels):
        """Test de mise à jour d'un libellé avec emoji."""
        label_id = sample_labels[0].id
        update_data = LabelUpdate(nom="🚀 Urgent", couleur="#FF0000")
        
        label = update_label(db_session, label_id, update_data)
        
        assert label is not None
        assert label.nom == "🚀 Urgent"


class TestDeleteLabel:
    """Tests pour la fonction delete_label."""

    def test_delete_existing_label(self, db_session, sample_labels):
        """Test de suppression d'un libellé existant."""
        label_id = sample_labels[0].id
        
        result = delete_label(db_session, label_id)
        
        assert result is True
        
        # Vérifier que le libellé est bien supprimé
        label = get_label(db_session, label_id)
        assert label is None

    def test_delete_nonexistent_label(self, db_session):
        """Test de suppression d'un libellé qui n'existe pas."""
        result = delete_label(db_session, 999)
        assert result is False

    def test_delete_label_with_zero_id(self, db_session):
        """Test de suppression d'un libellé avec ID 0."""
        result = delete_label(db_session, 0)
        assert result is False

    def test_delete_label_with_negative_id(self, db_session):
        """Test de suppression d'un libellé avec ID négatif."""
        result = delete_label(db_session, -1)
        assert result is False

    def test_delete_label_integrity_error(self, db_session, sample_labels):
        """Test de gestion des erreurs d'intégrité lors de la suppression."""
        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("Database error")):
            # La fonction ne gère pas les exceptions, donc l'exception se propage
            with pytest.raises(SQLAlchemyError):
                delete_label(db_session, sample_labels[0].id)

    def test_delete_last_label(self, db_session, sample_user):
        """Test de suppression du dernier libellé."""
        # Créer un seul libellé
        single_label = Label(nom="Seul", couleur="#FF0000", created_by=sample_user.id)
        db_session.add(single_label)
        db_session.commit()
        db_session.refresh(single_label)
        
        result = delete_label(db_session, single_label.id)
        
        assert result is True
        
        # Vérifier qu'il n'y a plus de libellés
        labels = get_labels(db_session)
        assert len(labels) == 0


class TestSecurityAndEdgeCases:
    """Tests de sécurité et cas particuliers."""

    def test_sql_injection_attempt_in_name(self, db_session, sample_user):
        """Test de tentative d'injection SQL dans le nom."""
        malicious_name = "test'; DROP TABLE labels; --"
        label_data = LabelCreate(nom=malicious_name, couleur="#FF0000")
        
        # Le nom doit être stocké tel quelle (pas d'exécution SQL)
        label = create_label(db_session, label_data, sample_user.id)
        assert label.nom == malicious_name

    def test_sql_injection_attempt_in_color(self, db_session, sample_user):
        """Test de tentative d'injection SQL dans la couleur."""
        malicious_color = "#FF0000'; DROP TABLE labels; --"
        label_data = LabelCreate(nom="Test", couleur=malicious_color)
        
        label = create_label(db_session, label_data, sample_user.id)
        assert label.couleur == malicious_color

    def test_xss_attempt_in_name(self, db_session, sample_user):
        """Test de tentative XSS dans le nom."""
        xss_name = "<script>alert('XSS')</script>"
        label_data = LabelCreate(nom=xss_name, couleur="#FF0000")
        
        label = create_label(db_session, label_data, sample_user.id)
        assert label.nom == xss_name

    def test_xss_attempt_in_color(self, db_session, sample_user):
        """Test de tentative XSS dans la couleur."""
        xss_color = "<script>alert('XSS')</script>"
        label_data = LabelCreate(nom="XSS Test", couleur=xss_color)
        
        label = create_label(db_session, label_data, sample_user.id)
        assert label.couleur == xss_color

    def test_special_characters_in_name(self, db_session, sample_user):
        """Test avec des caractères spéciaux dans le nom."""
        special_name = "éèàçùñáéíóú_中文_العربية"
        label_data = LabelCreate(nom=special_name, couleur="#FF0000")
        
        label = create_label(db_session, label_data, sample_user.id)
        assert label.nom == special_name

    def test_special_characters_in_color(self, db_session, sample_user):
        """Test avec des caractères spéciaux dans la couleur."""
        special_color = "#éèàçùñáéíóú"
        label_data = LabelCreate(nom="Special", couleur=special_color)
        
        label = create_label(db_session, label_data, sample_user.id)
        assert label.couleur == special_color

    def test_unicode_characters(self, db_session, sample_user):
        """Test avec des caractères Unicode."""
        unicode_name = "🚀_测试_العربية"
        unicode_color = "#🎯_测试"
        label_data = LabelCreate(nom=unicode_name, couleur=unicode_color)
        
        label = create_label(db_session, label_data, sample_user.id)
        assert label.nom == unicode_name
        assert label.couleur == unicode_color

    def test_whitespace_handling(self, db_session, sample_user):
        """Test de gestion des espaces blancs."""
        whitespace_name = "  whitespace label  "
        whitespace_color = "  #FF0000  "
        label_data = LabelCreate(nom=whitespace_name, couleur=whitespace_color)
        
        label = create_label(db_session, label_data, sample_user.id)
        assert label.nom == whitespace_name
        assert label.couleur == whitespace_color

    def test_empty_strings(self, db_session, sample_user):
        """Test avec des chaînes vides."""
        # Le schéma Pydantic accepte les chaînes vides, donc on teste que le service les gère
        label_data = LabelCreate(nom="", couleur="#FF0000")
        label = create_label(db_session, label_data, sample_user.id)
        
        assert label is not None
        assert label.nom == ""  # Le nom vide est accepté
        assert label.couleur == "#FF0000"

    def test_very_long_color_value(self, db_session, sample_user):
        """Test avec une couleur très longue."""
        long_color = "#" + "A" * 1000
        label_data = LabelCreate(nom="Long Color", couleur=long_color)
        
        label = create_label(db_session, label_data, sample_user.id)
        assert label.couleur == long_color

    def test_concurrent_operations(self, db_session, sample_user):
        """Test d'opérations concurrentes."""
        # Créer un libellé
        label_data1 = LabelCreate(nom="Original", couleur="#FF0000")
        label1 = create_label(db_session, label_data1, sample_user.id)
        
        # Le mettre à jour
        update_data = LabelUpdate(nom="Updated", couleur="#00FF00")
        label2 = update_label(db_session, label1.id, update_data)
        
        # Vérifier que les opérations sont séquentielles
        assert label2.id == label1.id
        assert label2.nom == "Updated"
        assert label2.couleur == "#00FF00"

    def test_database_transaction_rollback_on_error(self, db_session, sample_user):
        """Test de rollback de transaction en cas d'erreur."""
        label_data = LabelCreate(nom="Test Transaction", couleur="#FF0000")
        
        # Simuler une erreur pendant la création
        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("Database error")):
            with pytest.raises(SQLAlchemyError):
                create_label(db_session, label_data, sample_user.id)
        
        # Vérifier que le libellé n'a pas été créé
        label = get_label_by_name(db_session, "Test Transaction")
        assert label is None
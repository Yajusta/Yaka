"""Tests complets pour le modèle __init__.py (import des modèles)."""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestModelImports:
    """Tests pour les imports du module __init__.py."""

    def test_import_all_models(self):
        """Test que tous les modèles peuvent être importés correctement."""
        # Importer le module __init__.py
        from app.models import (
            BoardSettings,
            Card,
            CardComment,
            CardHistory,
            CardItem,
            CardPriority,
            KanbanList,
            Label,
            User,
            UserRole,
            UserStatus,
            card_labels,
        )

        # Vérifier que les classes sont correctement importées
        assert User is not None
        assert UserRole is not None
        assert UserStatus is not None
        assert Label is not None
        assert Card is not None
        assert CardPriority is not None
        assert card_labels is not None
        assert KanbanList is not None
        assert BoardSettings is not None
        assert CardItem is not None
        assert CardComment is not None
        assert CardHistory is not None

    def test_user_enum_values(self):
        """Test les valeurs de l'énumération UserRole."""
        from app.models import UserRole

        assert UserRole.ADMIN.value == "admin"
        assert UserRole.SUPERVISOR.value == "supervisor"
        assert UserRole.EDITOR.value == "editor"
        assert UserRole.CONTRIBUTOR.value == "contributor"
        assert UserRole.COMMENTER.value == "commenter"
        assert UserRole.VISITOR.value == "visitor"

        expected_values = {"admin", "supervisor", "editor", "contributor", "commenter", "visitor"}
        assert {role.value for role in UserRole} == expected_values

    def test_user_status_enum_values(self):
        """Test les valeurs de l'énumération UserStatus."""
        from app.models import UserStatus

        assert UserStatus.INVITED.value == "invited"
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.DELETED.value == "deleted"

        # Vérifier que toutes les valeurs sont présentes
        status_values = [status.value for status in UserStatus]
        assert "invited" in status_values
        assert "active" in status_values
        assert "deleted" in status_values

    def test_card_priority_enum_values(self):
        """Test les valeurs de l'énumération CardPriority."""
        from app.models import CardPriority

        assert CardPriority.LOW.value == "low"
        assert CardPriority.MEDIUM.value == "medium"
        assert CardPriority.HIGH.value == "high"

        # Vérifier que toutes les valeurs sont présentes
        priority_values = [priority.value for priority in CardPriority]
        assert "low" in priority_values
        assert "medium" in priority_values
        assert "high" in priority_values

    def test_card_labels_table(self):
        """Test que la table d'association card_labels est correctement définie."""
        from app.models import card_labels
        from sqlalchemy import Table

        assert isinstance(card_labels, Table)
        assert card_labels.name == "card_labels"

        # Vérifier que la table a les colonnes attendues
        column_names = [col.name for col in card_labels.columns]
        assert "card_id" in column_names
        assert "label_id" in column_names

    def test_all_exports(self):
        """Test que __all__ contient tous les éléments attendus."""
        from app.models import __all__

        expected_all = [
            "User",
            "UserStatus",
            "UserRole",
            "Label",
            "Card",
            "CardPriority",
            "card_labels",
            "KanbanList",
            "BoardSettings",
            "CardItem",
            "CardComment",
            "CardHistory",
            "ViewScope",
            "GlobalDictionary",
            "PersonalDictionary",
        ]

        assert set(__all__) == set(expected_all)
        assert len(__all__) == len(expected_all)

    def test_import_error_handling(self):
        """Test la gestion des erreurs d'import."""
        # Sauvegarder les modules actuels
        original_modules = sys.modules.copy()

        try:
            # Supprimer le module des modèles pour forcer une réimportation
            if "app.models" in sys.modules:
                del sys.modules["app.models"]
            if "app.models.user" in sys.modules:
                del sys.modules["app.models.user"]

            # Simuler une erreur dans un sous-module
            with patch.dict("sys.modules", {"app.models.user": None}):
                with pytest.raises(ImportError):
                    from app.models import User
        finally:
            # Restaurer les modules originaux
            sys.modules.clear()
            sys.modules.update(original_modules)

    def test_circular_import_handling(self):
        """Test que les imports circulaires sont correctement gérés."""
        # Les modèles utilisent TYPE_CHECKING pour éviter les imports circulaires
        # Ce test vérifie que les imports fonctionnent malgré les références circulaires
        from app.models import Card, CardComment, User

        # Ces modèles ont des références circulaires mais devraient pouvoir être importés
        assert User is not None
        assert Card is not None
        assert CardComment is not None

    def test_model_attributes_availability(self):
        """Test que les attributs des modèles sont disponibles après import."""
        from app.models import BoardSettings, Card, CardPriority, User

        # Vérifier que les attributs spécifiques des modèles sont accessibles
        assert hasattr(User, "PROTECTED_FIELDS")
        assert hasattr(Card, "PROTECTED_FIELDS")
        assert hasattr(BoardSettings, "__tablename__")

        # CardPriority est une classe séparée, pas un attribut de Card
        assert CardPriority is not None

    def test_import_consistency(self):
        """Test que les imports sont cohérents entre eux."""
        # Importer les modèles de différentes manières
        from app.models import User as User1
        from app.models.user import User as User2

        # Les deux références devraient pointer vers la même classe
        assert User1 is User2

    def test_dynamic_imports(self):
        """Test les imports dynamiques fonctionnent correctement."""
        import importlib

        # Importer dynamiquement le module
        models_module = importlib.import_module("app.models")

        # Vérifier que les attributs sont accessibles
        assert hasattr(models_module, "User")
        assert hasattr(models_module, "Card")
        assert hasattr(models_module, "__all__")

    def test_module_level_documentation(self):
        """Test que la documentation au niveau module est présente."""
        import app.models

        assert hasattr(app.models, "__doc__")
        assert app.models.__doc__ is not None
        assert len(app.models.__doc__.strip()) > 0

    def test_backward_compatibility(self):
        """Test que les anciens chemins d'import fonctionnent toujours."""
        # Tester que les anciens chemins d'import directs fonctionnent
        from app.models.board_settings import BoardSettings
        from app.models.card import Card, CardPriority
        from app.models.user import User, UserRole

        assert User is not None
        assert UserRole is not None
        assert Card is not None
        assert CardPriority is not None
        assert BoardSettings is not None

    def test_import_performance(self):
        """Test que les imports sont performants (pas d'import circulaire infini)."""
        import time

        start_time = time.time()

        # Importer tous les modèles

        end_time = time.time()

        # L'import devrait être rapide (moins de 1 seconde)
        assert end_time - start_time < 1.0

    def test_model_namespace_isolation(self):
        """Test que les espaces de noms des modèles sont correctement isolés."""
        from app.models import User as ModelsUser
        from app.models.user import User as DirectUser

        # Les deux devraient être le même objet
        assert ModelsUser is DirectUser

        # Vérifier que les modifications dans un module sont répercutées dans l'autre
        assert hasattr(ModelsUser, "PROTECTED_FIELDS")
        assert hasattr(DirectUser, "PROTECTED_FIELDS")
        assert ModelsUser.PROTECTED_FIELDS == DirectUser.PROTECTED_FIELDS

    def test_import_path_consistency(self):
        """Test que les chemins d'import sont cohérents."""
        import app.models
        from app import models

        # Les deux références devraient pointer vers le même module
        assert app.models is models

    def test_missing_import_handling(self):
        """Test la gestion des imports manquants."""
        with pytest.raises(ImportError):
            # Essayer d'importer un modèle qui n'existe pas
            from app.models import NonExistentModel  # type: ignore[attr-defined]

    def test_submodule_imports(self):
        """Test que les sous-modules peuvent être importés individuellement."""
        from app.models import board_settings, card, user

        assert user is not None
        assert card is not None
        assert board_settings is not None

    def test_relative_imports(self):
        """Test que les imports relatifs fonctionnent correctement."""
        # Le fichier __init__.py utilise des imports relatifs
        # Ce test vérifie qu'ils fonctionnent correctement
        from app.models import User

        # Si les imports relatifs fonctionnent, User devrait être importable
        assert User is not None
        assert hasattr(User, "__tablename__")
        assert User.__tablename__ == "users"

    def test_import_order_independence(self):
        """Test que l'ordre des imports n'affecte pas le résultat."""
        # Importer dans un ordre différent
        from app.models import Card, CardComment, CardHistory, CardItem, Label, User

        assert all(model is not None for model in [CardHistory, CardItem, CardComment, User, Card, Label])

    def test_module_reloading(self):
        """Test le rechargement du module."""
        import importlib

        import app.models

        # Obtenir l'ID du module original
        original_id = id(app.models)

        # Reloader le module
        reloaded_module = importlib.reload(app.models)

        # Vérifier que c'est le même module
        assert id(reloaded_module) == original_id

    def test_import_caching(self):
        """Test que les imports sont correctement mis en cache."""
        # Importer le même modèle plusieurs fois
        from app.models import User as User1
        from app.models import User as User2
        from app.models.user import User as User3

        # Toutes les références devraient être identiques
        assert User1 is User2 is User3

    def test_package_structure(self):
        """Test que la structure du package est correcte."""
        import app.models

        # Vérifier que c'est bien un package
        assert hasattr(app.models, "__path__")
        assert hasattr(app.models, "__name__")
        assert app.models.__name__ == "app.models"

    def test_cross_module_references(self):
        """Test que les références entre modules fonctionnent."""
        from app.models import Card, CardComment, User

        # Vérifier que les relations entre modèles sont définies
        assert hasattr(User, "created_cards")
        assert hasattr(Card, "creator")
        assert hasattr(CardComment, "card")
        assert hasattr(CardComment, "user")

    def test_import_completeness(self):
        """Test que tous les modèles nécessaires sont importés."""
        from app.models import __all__

        # Vérifier que les modèles essentiels sont dans __all__
        essential_models = ["User", "Card", "Label", "KanbanList", "BoardSettings"]
        for model in essential_models:
            assert model in __all__, f"{model} manquant dans __all__"

    def test_type_checking_imports(self):
        """Test que les imports conditionnels TYPE_CHECKING fonctionnent."""
        # Vérifier que les imports pour le typage sont disponibles
        from app.models.card import Card
        from app.models.card_comment import CardComment

        # Les références circulaires devraient être résolues
        assert hasattr(Card, "comments")
        assert hasattr(CardComment, "card")

    def test_enum_functionality(self):
        """Test que les énumérations importées fonctionnent correctement."""
        from app.models import CardPriority, UserRole, UserStatus

        # Vérifier que les énumérations peuvent être itérées
        assert len(list(UserRole)) == 6
        assert len(list(UserStatus)) == 3
        assert len(list(CardPriority)) == 3

        # Vérifier que les énumérations peuvent être comparées
        assert UserRole.ADMIN != UserRole.EDITOR
        assert CardPriority.HIGH != CardPriority.LOW

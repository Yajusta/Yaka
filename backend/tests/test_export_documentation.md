# Documentation des Tests d'Export

Ce document décrit les tests créés pour la fonctionnalité d'export CSV et Excel.

## Structure des Tests

### Tests Unitaires (`test_export_service.py`)

#### 1. Tests des Fonctions de Formatage (`TestFormatFunctions`)

- **test_sanitize_csv_text_with_newlines**: Vérifie que les retours à la ligne sont remplacés par des espaces
- **test_sanitize_csv_text_with_none**: Vérifie le comportement avec une valeur `None`
- **test_sanitize_csv_text_with_empty_string**: Vérifie le comportement avec une chaîne vide
- **test_sanitize_csv_text_with_multiple_spaces**: Vérifie que les espaces multiples sont consolidés
- **test_format_checklist_empty**: Vérifie le formatage d'une checklist vide
- **test_format_checklist_with_items**: Vérifie le formatage d'une checklist avec items cochés/non cochés
- **test_format_labels_empty**: Vérifie le formatage sans étiquettes
- **test_format_labels_with_multiple**: Vérifie le formatage de plusieurs étiquettes séparées par ` + `
- **test_format_due_date_none**: Vérifie le formatage d'une date nulle
- **test_format_due_date_with_date**: Vérifie le formatage d'une date au format YYYY-MM-DD
- **test_format_due_date_with_string**: Vérifie le formatage d'une date sous forme de chaîne
- **test_format_priority**: Vérifie le formatage d'une priorité
- **test_format_priority_none**: Vérifie le formatage d'une priorité nulle

#### 2. Tests de Récupération des Cartes (`TestGetCardsForExport`)

- **test_get_cards_excludes_archived**: Vérifie que les cartes archivées sont exclues
- **test_get_cards_sorted_by_list_and_position**: Vérifie le tri par liste puis par position

#### 3. Tests d'Export CSV (`TestGenerateCSVExport`)

- **test_csv_export_structure**: Vérifie la structure du fichier CSV (en-têtes, nombre de lignes)
- **test_csv_export_removes_newlines**: Vérifie que les retours à la ligne sont supprimés
- **test_csv_export_no_checklist_column**: Vérifie que la colonne Checklist n'est pas présente

#### 4. Tests d'Export Excel (`TestGenerateExcelExport`)

- **test_excel_export_structure**: Vérifie la structure du fichier Excel (en-têtes, nombre de lignes)
- **test_excel_export_has_checklist**: Vérifie que la checklist est présente dans Excel
- **test_excel_export_preserves_newlines**: Vérifie que les retours à la ligne sont préservés dans Excel
- **test_excel_export_column_widths**: Vérifie que les largeurs de colonnes sont définies

#### 5. Tests de Génération de Nom de Fichier (`TestGetExportFilename`)

- **test_csv_filename_format**: Vérifie le format du nom de fichier CSV
- **test_xlsx_filename_format**: Vérifie le format du nom de fichier Excel
- **test_filename_contains_timestamp**: Vérifie que le nom contient un timestamp au format attendu

### Tests d'Intégration (`test_integration_export_api.py`)

#### 1. Tests CSV

- **test_export_csv_success**: Vérifie qu'un export CSV réussit (code 200, headers corrects)
- **test_export_csv_content**: Vérifie le contenu du CSV (en-têtes, données)
- **test_export_csv_excludes_archived**: Vérifie que les cartes archivées ne sont pas exportées

#### 2. Tests Excel

- **test_export_excel_success**: Vérifie qu'un export Excel réussit (code 200, headers corrects)
- **test_export_excel_content**: Vérifie le contenu du fichier Excel (en-têtes, checklist)

#### 3. Tests d'Authentification et Validation

- **test_export_requires_authentication**: Vérifie que l'export nécessite une authentification
- **test_export_invalid_format**: Vérifie le rejet d'un format invalide (400)
- **test_export_missing_format**: Vérifie le rejet d'une requête sans format (422)

#### 4. Tests de Permissions

- **test_visitor_can_export**: Vérifie qu'un visiteur peut exporter

#### 5. Tests de Cas Limites

- **test_export_empty_database**: Vérifie l'export d'une base vide (seulement l'en-tête)

## Couverture des Tests

Les tests couvrent :

✅ **Fonctionnalités de base** :
- Export CSV avec nettoyage des retours à la ligne
- Export Excel avec préservation du formatage
- Formatage correct de toutes les colonnes

✅ **Validation** :
- Format de fichier valide (csv/xlsx)
- Authentification requise
- Gestion des erreurs

✅ **Règles métier** :
- Exclusion des cartes archivées
- Tri par liste et position
- Différences CSV/Excel (checklist)
- Permissions (visiteur peut exporter)

✅ **Cas limites** :
- Base de données vide
- Valeurs nulles
- Chaînes vides
- Caractères spéciaux

## Exécution des Tests

### Tous les tests d'export :
```bash
python -m pytest tests/test_export_service.py tests/test_integration_export_api.py -v
```

### Tests unitaires uniquement :
```bash
python -m pytest tests/test_export_service.py -v
```

### Tests d'intégration uniquement :
```bash
python -m pytest tests/test_integration_export_api.py -v
```

## Résultats

- **Tests unitaires** : 25 tests ✅
- **Tests d'intégration** : 10 tests ✅
- **Total** : 35 tests ✅

Tous les tests passent avec succès.


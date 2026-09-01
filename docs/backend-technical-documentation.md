# Yaka - Documentation technique du backend

## 🏗️ Structure du Projet

```none
kanban-app/
├── backend/                 # API FastAPI
│   ├── app/
│   │   ├── main.py         # Point d'entrée
│   │   ├── database.py     # Configuration BDD
│   │   ├── models/         # Modèles SQLAlchemy
│   │   ├── schemas/        # Schémas Pydantic
│   │   ├── routers/        # Endpoints API
│   │   ├── services/       # Logique métier
│   │   └── utils/          # Utilitaires
│   └── pyproject.toml      # Dépendances Python (uv)
├── frontend/               # Application React
│   ├── src/
│   │   ├── components/     # Composants React
│   │   ├── hooks/          # Hooks personnalisés
│   │   ├── services/       # Services API
│   │   └── types/          # Types et constantes
│   └── package.json        # Dépendances Node.js
└── docs/                   # Documentation
```

## 🔧 API Endpoints

### Authentification

- `POST /auth/login` - Connexion utilisateur
- `GET /auth/me` - Informations utilisateur connecté

### Utilisateurs

- `GET /users` - Liste des utilisateurs (admin)
- `POST /users` - Créer un utilisateur (admin)
- `PUT /users/{id}` - Modifier un utilisateur (admin)
- `DELETE /users/{id}` - Supprimer un utilisateur (admin)

### Cartes

- `GET /cards` - Liste des cartes avec filtres
- `POST /cards` - Créer une carte
- `PUT /cards/{id}` - Modifier une carte
- `DELETE /cards/{id}` - Supprimer une carte
- `POST /cards/{id}/archive` - Archiver une carte
- `GET /cards/archived` - Liste des cartes archivées

### Libellés

- `GET /labels` - Liste des libellés
- `POST /labels` - Créer un libellé (admin)
- `PUT /labels/{id}` - Modifier un libellé (admin)
- `DELETE /labels/{id}` - Supprimer un libellé (admin)

## 💾 Gestion des Bases de Données

### Architecture Multi-Bases

Yaka supporte la gestion de plusieurs bases de données SQLite simultanément. Chaque board peut avoir sa propre base de données dans le répertoire `backend/data/`.

### Migrations Automatiques

Au démarrage du serveur backend, le système :

1. **Scanne le répertoire data** : Recherche tous les fichiers `.db` dans `backend/data/`
2. **Vérifie chaque base** : Pour chaque base de données trouvée :
   - Vérifie la présence de la table `alembic_version`
   - Compare la version actuelle avec la dernière version disponible
   - Affiche un message préfixé par le nom de la base (ex: `[yaka.db]`)
3. **Applique les migrations** : Si une base n'est pas à jour, Alembic applique automatiquement les migrations nécessaires

### Exemple de sortie au démarrage

```text
Migration de 9 base(s) de données trouvée(s)...

============================================================
Migration de: yaka.db
============================================================
[yaka.db] Base de données à jour (version c1d2e3f4g5h6)

============================================================
Migration de: mon-board.db
============================================================
[mon-board.db] Migration nécessaire: 689984d4c0de -> c1d2e3f4g5h6
INFO  [alembic.runtime.migration] Running upgrade...
[mon-board.db] Migration terminée avec succès
```

### Gestion manuelle des migrations

Pour créer une nouvelle migration :

```bash
cd backend
alembic revision --autogenerate -m "Description de la migration"
```

Pour appliquer manuellement les migrations à une base spécifique :

```bash
cd backend
# Modifier temporairement sqlalchemy.url dans alembic.ini
alembic upgrade head
```

### Structure des fichiers de base de données

- `backend/data/yaka.db` : Base de données par défaut
- `backend/data/{board-uid}.db` : Bases de données spécifiques aux boards
- `backend/data/deleted/` : Bases de données archivées

## 🧪 Tests

### Tests Backend

```bash
cd backend
pytest
```

(mais il faut que je les fasse d'abord...)

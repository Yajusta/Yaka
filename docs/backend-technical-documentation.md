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
│   └── requirements.txt    # Dépendances Python
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

## 🧪 Tests

### Tests Backend

```bash
cd backend
pytest
```

(mais il faut que je les fasse d'abord...)

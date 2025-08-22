
# YAKA - Yet Another Kanban App

![Logo](https://raw.githubusercontent.com/Yajusta/Yaka/refs/heads/main/frontend/public/yaka.ico)

Une application web moderne et intuitive pour la gestion collaborative de tâches utilisant la méthodologie Kanban.

## 🚀 Fonctionnalités

- **Tableau Kanban interactif**
- **Drag & Drop** fluide pour déplacer les cartes
- **Authentification sécurisée** avec JWT
- **Cartes détaillées** avec titre, description, liste d'éléments, priorité, assigné, libellés, date d'échéance
- **Recherche et filtres**
- **Utilisaturs illimités**
- **Gestion des rôles** (administrateur / membre)
- **Gestion des colonnes** pour mettre autant de colonnes que nécessaire
- **Gestion des libellés** colorés pour la catégorisation

## 📋 Prérequis

- [Python](https://www.python.org/downloads/) 3.12+ + [uv](https://docs.astral.sh/uv/)
- [Node.js](https://nodejs.org/fr/download) 18+
- [pnpm](https://pnpm.io/) (recommandé) ou [npm](https://www.npmjs.com/)

## 📦 Installation et démarrage

### 1. Cloner le projet

```bash
git clone https://github.com/Yajusta/Yaka.git
cd Yaka
```

### 2. Configuration du serveur de mail

Copier / coller le fichier `.env.sample` en `.env` et remplir les paramètres de configuration de votre serveur SMTP/

Exemple :

```txt
# Paramètres pour l'envoi de mail
SMTP_HOST = "smtp.resend.com"
SMTP_PORT = 587
SMTP_USER = "resend"
SMTP_PASS = "re_xxxxxxxxxxxx"
SMTP_SECURE = "starttls"  # values: 'ssl'|'starttls'|'none'
SMTP_FROM = "no-reply@domain.com"
```

### 3. Démarrage du backend

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Un environnement virtuel sera automatiquement créé avec toutes les dépendances nécessaires.
Le backend sera accessible sur <http://localhost:8000>

### 4. Démarrage du frontend

```bash
cd frontend
pnpm install
pnpm run dev
```

Le frontend sera accessible sur <http://localhost:5173>

## 🚀 Déploiement

### 1. Modifier les variables d'environnement

```bash
cp .env.sample .env
```

### 2. Déployer avec Docker

```bash
docker compose build
docker compose up -d
```

## 👤 Compte administrateur par défaut

Un compte administrateur est créé automatiquement lors de l'initialisation :

- **Email :** `admin@kyaka.local`
- **Mot de passe :** `admin123`

Une fois connecté, créez un nouvel administrateur avec votre email puis supprimez ce compte.

## 📖 Documentation

- [Guide technique du frontend](docs/frontend-technical-documentation.md) - Documentation complète du frontend
- [Guide technique du backend](docs/backend-technical-documentation.md) - Documentation complète du backend
- [Guide Utilisateur](docs/user-guide.md) - Manuel d'utilisation de l'application

## 📄 Licence

Ce projet est sous licence **Non-Commercial License** : vous pouvez utiliser et modifier l'application, mais sans en rendre son utilisation payante sans l'accord de l'auteur.

## 🆘 Support

Pour toute question ou problème :

1. Consulter la [documentation](docs/)
2. Vérifier les [issues existantes]([../../issues](https://github.com/Yajusta/Yaka/issues))
3. Créer une nouvelle issue si nécessaire

## 🔄 Roadmap

- [ ] Notifications en temps réel (websockets)
- [ ] Commentaires sur les cartes
- [ ] Pièces jointes
- [ ] Rapports et analytics
- [ ] API publique
- [ ] Application mobile
- [ ] Intégrations tierces (Slack, Teams, etc.)

## 🛠️ Technologies

### Backend

- **FastAPI** - Framework web Python moderne et performant
- **SQLAlchemy** - ORM pour la gestion de base de données
- **SQLite** - Base de données embarquée
- **JWT** - Authentification par tokens
- **Pydantic** - Validation et sérialisation des données

### Frontend

- **React** - Bibliothèque JavaScript pour l'interface utilisateur
- **shadcn/ui** - Composants UI modernes et accessibles
- **Tailwind CSS** - Framework CSS utility-first
- **Vite** - Outil de build rapide

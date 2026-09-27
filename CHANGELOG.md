# Changelog

## 1.6.0 (2026-09-27)

Mise à jour de sécurité issue de l'audit du 2026-09-26 (identifiants F01–F19, NV1 et NV2 du rapport). **Lire la section « Breaking changes » avant de mettre à jour.**

### Secrets et configuration

- [SECURITY] `JWT_SECRET` obligatoire : plus de valeur de repli, le backend refuse de démarrer si la variable est absente, fait moins de 32 caractères non blancs ou moins de 8 caractères distincts (F01). `docker compose` s'arrête si elle n'est pas définie.
- [SECURITY] `YAKA_ADMIN_API_KEY` : comparaison à temps constant ; une clé de moins de 32 caractères (dont l'ancienne valeur d'exemple) est traitée comme absente (`/admin` répond 503, avec un avertissement dans les logs).
- [SECURITY] Plus de `load_dotenv(override=True)` ni de rechargement de la configuration dans un handler : les variables d'environnement priment sur le fichier `.env` (F19).
- [SECURITY] Fichiers `.env.*` ignorés par git et par le contexte Docker (sauf `.env.sample`).

### Comptes par défaut

- [SECURITY] Installation neuve : comptes de démonstration créés seulement si `DEMO_MODE=true` ; administrateur initial avec `DEFAULT_ADMIN_PASSWORD`, sinon avec un mot de passe aléatoire affiché une seule fois dans les logs et à changer à la première connexion (F02).
- [SECURITY] Nouveau flag `must_change_password` : tant qu'il est actif, l'API répond 403 `password_change_required`, sauf pour le profil, la langue, le changement de mot de passe (nouvel endpoint `POST /auth/change-password`) et la déconnexion ; écran de changement obligatoire sur desktop et mobile.
- [SECURITY] Au démarrage hors `DEMO_MODE`, dans chaque board : les comptes de démo encore en `Demo1234` sont désactivés (soft-delete), et l'administrateur par défaut encore en `Admin123` (comme un compte de démo promu administrateur encore en `Demo1234`) reçoit un mot de passe aléatoire, affiché une seule fois dans les logs et à changer à la connexion suivante. `DEFAULT_ADMIN_PASSWORD=Admin123` est ignoré hors mode démo.

### Sessions et JWT

- [SECURITY] Les jetons portent le board d'émission (`board`), l'id de l'utilisateur (`uid`) et sa version de jetons (`ver`) : un jeton est refusé sur un autre board, pour un compte recréé ou non actif, ou si sa version a changé (F03, F11).
- [SECURITY] Révocation : la version de jetons est incrémentée à chaque changement de mot de passe ou de rôle, suppression de compte, déconnexion et `/demo/reset` ; `POST /auth/logout` révoque côté serveur (sauf en `DEMO_MODE`) ; `POST /auth/change-password` renvoie un nouveau jeton. Un board recréé n'accepte pas les jetons de l'ancien.

### Réinitialisation de mot de passe et invitations

- [SECURITY] Lien de réinitialisation ou d'invitation construit avec le board du chemin (validé par le middleware), et non plus avec un `board_uid` fourni dans le corps ; composants encodés et valeurs échappées dans les gabarits HTML des emails (F04, F12).
- [SECURITY] Jetons à durée limitée : 1 h pour une réinitialisation, 7 jours pour une invitation ; jeton expiré refusé et effacé ; 60 s minimum entre deux envois (sinon 429) ; tout changement de mot de passe efface le jeton en attente et révoque les sessions (F13).
- [SECURITY] Envoi SMTP avec un délai de 10 s, en tâche de fond (`BackgroundTasks`).
- [FIX] Un compte invité est activé quand un administrateur fixe son mot de passe.

### Limitation de débit

- [SECURITY] `slowapi` (fenêtre glissante, en mémoire) : par IP, 10/min sur la connexion et le changement de mot de passe (`LOGIN_RATE_LIMIT`), 5/min sur la demande de réinitialisation (`PASSWORD_RESET_RATE_LIMIT`) ; par compte, 5 tentatives par 15 minutes pour la connexion et le changement de mot de passe (`LOGIN_ACCOUNT_RATE_LIMIT`), compteur remis à zéro après un succès. Réponse 429 traduite sur desktop et mobile (F07, F09).
- [SECURITY] Temps de réponse homogène : vérification bcrypt contre un hash factice pour un compte inconnu ou inactif ; un mot de passe de plus de 72 octets est refusé (401 à la connexion) au lieu de provoquer une erreur 500 (F14).
- [NEW] `FORWARDED_ALLOW_IPS` : proxys autorisés à transmettre l'IP du client (`X-Forwarded-For`).

### Périmètre de vue (view-scope)

- [SECURITY] Un non-administrateur ne peut que réduire son propre périmètre de vue (F05).
- [SECURITY] Le périmètre de vue s'applique à toutes les routes de carte : lecture, commentaires, checklist, historique, modifications, déplacement en masse, compteurs de liste et export (F06).
- [FIX] La lecture d'une carte supprimait définitivement ses commentaires supprimés logiquement.

### Pilotage vocal / LLM

- [SECURITY] Appels au fournisseur bornés (délai de 30 s, un seul nouvel essai) et exécutés hors de la boucle d'événements ; au plus `LLM_MAX_CONCURRENT_CALLS` appels simultanés (4 par défaut, 503 au-delà) et `VOICE_CONTROL_RATE_LIMIT` requêtes par utilisateur (20/min par défaut, 429 au-delà) (F08).
- [CHANGE] Codes d'erreur : 503 si le pilotage vocal n'est pas configuré ou est saturé, 502 si le fournisseur échoue ; une réponse invalide du modèle donne un résultat vide.
- [SECURITY] Plus aucun email dans le prompt : seulement le nom affiché ou « Utilisateur #id » (F16) ; seules les cartes visibles par l'utilisateur sont envoyées.
- [SECURITY] Description de carte limitée à 20 000 caractères ; contexte envoyé au modèle plafonné (200 cartes, 1 000 caractères par description, 60 000 caractères au total) (NV2).

### Export

- [SECURITY] Neutralisation des formules dans les exports CSV et Excel (apostrophe devant `=`, `+`, `-`, `@`, tabulation et retour chariot en tête de cellule) ; cellules Excel forcées en texte (F10).

### Données personnelles et historique

- [SECURITY] Les utilisateurs imbriqués (commentaires, historique) n'exposent plus que `id` et `display_name`, sans email (F15).
- [SECURITY] `POST /cards/{id}/history` : carte prise dans le chemin, auteur = utilisateur courant, droit de modification exigé ; seuls `action` et `description` sont acceptés (F17). Routeur d'historique orphelin supprimé.

### Multi-board et administration

- [SECURITY] Suppression puis recréation d'un board : moteurs en cache évincés, base ouverte en `mode=rw` (plus de recréation silencieuse d'un fichier archivé), création atomique, archive horodatée (F18).
- [SECURITY] `GET /admin/boards/{uid}` exige la clé d'administration et ne renvoie plus le chemin de la base.
- [SECURITY] Erreurs 500 génériques (détail uniquement dans les logs) pour l'administration, `/demo/reset` et les listes ; identifiant de board validé partout de la même façon (invalide → 401).

### En-têtes HTTP et PWA

- [SECURITY] nginx : `Content-Security-Policy` (`connect-src` limité à l'origine de `API_BASE_URL` et aux CDN des modèles Whisper, `frame-ancestors 'none'`), `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, `Permissions-Policy` ; `api-config.js`, `demo-config.js` et le service worker servis en `no-store`.
- [SECURITY] PWA : les réponses de l'API ne sont plus mises en cache par le service worker et l'ancien cache `api-cache` est purgé (NV1).
- [SECURITY] Backend : `/docs`, `/redoc` et `/openapi.json` servis seulement si `ENVIRONMENT=development` ; origines `http://localhost` (mobile) et `file://` autorisées seulement en développement ; origines CORS vides ignorées.
- [CHORE] Suppression de `whisper-poc.html`.

### Docker

- [SECURITY] Images de base épinglées par digest.
- [SECURITY] Dépendances Python installées au build depuis `uv.lock` (plus de résolution au démarrage) ; un seul worker uvicorn ; code et environnement virtuel en lecture seule, seul `/app/data` est inscriptible (UID 10001) ; tests exclus de l'image.
- [FIX] `demo-cron` : la réinitialisation horaire échouait silencieusement (400).
- [CHANGE] `docker-compose.yaml` transmet les nouvelles variables (limites de débit, LLM, CORS, `FORWARDED_ALLOW_IPS`, `DEFAULT_ADMIN_PASSWORD`).

### Breaking changes / actions requises à la mise à jour

- [BREAKING] Définir `JWT_SECRET` (au moins 32 caractères) avant de démarrer : `openssl rand -hex 32`.
- [BREAKING] Tous les jetons existants sont invalidés : tous les utilisateurs doivent se reconnecter.
- [BREAKING] Un navigateur n'est connecté qu'à un seul board à la fois (le jeton est lié au board).
- [BREAKING] La déconnexion déconnecte l'utilisateur de tous ses appareils (hors `DEMO_MODE`).
- [BREAKING] Installation neuve : l'administrateur initial n'a plus le mot de passe `Admin123` ; sauf si `DEFAULT_ADMIN_PASSWORD` est défini, son mot de passe aléatoire est affiché une seule fois dans les logs du backend (`Administrateur initial créé`) et doit être changé à la première connexion.
- [BREAKING] Instance existante hors `DEMO_MODE` : les comptes de démo encore en `Demo1234` sont désactivés (soft-delete) et l'administrateur encore en `Admin123` reçoit un mot de passe aléatoire, affiché une seule fois dans les logs au premier démarrage (`Public default passwords detected`), à changer à la connexion suivante.
- [BREAKING] `YAKA_ADMIN_API_KEY` doit faire au moins 32 caractères, sinon `/admin` est désactivé (503) ; `GET /admin/boards/{uid}` exige désormais la clé.
- [BREAKING] `/docs`, `/redoc` et `/openapi.json` ne sont servis que si `ENVIRONMENT=development`.
- [BREAKING] `http://localhost` n'est plus une origine mobile autorisée par défaut en production (l'ajouter à `MOBILE_ORIGINS` si nécessaire).
- [BREAKING] `API_BASE_URL` doit être une URL absolue (`http(s)://hôte[:port]`) pour être autorisée par la CSP ; sinon seule l'origine du frontend l'est et une API sur une autre origine est bloquée.
- [BREAKING] Docker : le répertoire `./data` de l'hôte doit appartenir à l'UID 10001 (`sudo chown -R 10001:10001 data`).
- [BREAKING] Docker : lancer les scripts avec `docker compose exec backend python scripts/...` (et non `uv run`) ; BuildKit est requis pour construire l'image (défaut de Docker ≥ 23 et de `docker compose` v2).
- [BREAKING] Description de carte limitée à 20 000 caractères (création et modification).
- [BREAKING] Un seul worker uvicorn : la limitation de débit est en mémoire et propre à chaque processus.

## 1.5.1 (2026-09-13)

- [FIX] Connexion à une base spécifique sur mobile.
- [FIX] Mise à jour de sécurité.

## 1.5.0 (2026-09-01)

- [CHORE] Trunk check.
- [NEW] Paramétrage des ports.
- [FIX] Problème d'affichage des boutons sur les appareils tactiles.

## 1.4.3 (2025-12-02)

- [FIX] Changement de format pour le LLM.

## 1.4.2 (2025-11-10)

- [FIX] Problème de focus quand on modifie un champ de la checklist.
- [CHORE] Refacto du VoiceControl.

## 1.4.1 (2025-11-01)

- [NEW] Filtre des tâches à la voix.

## 1.4.0. (2025-10-27)

- [NEW] Ajout d'une version mobile.

## 1.3.4 (2025-10-19)

- [UX] Réorganisation du menu de paramètres.
- [FIX] Problème d'accès à la base de données multiple pour le service de voix.

## 1.3.3 (2025-10-18)

- [CHANGE] Les migrations Alembic s'appliquent maintenant à toutes les bases de données du répertoire `data` au démarrage du serveur.
- [CHANGE] Meilleur gestion de la concurrence des bases.

## 1.3.2 (2025-10-15)

- [NEW] Périmètre de vue (qui peut voir quoi).
- [NEW] Gestion de dictionnaire personnel pour aider l'IA dans sa compréhension.
- [UX] Précision sur l'utilité des descriptions (listes et libellés)

## 1.3.1 (2025-10-15)

- [NEW] Gestion des bases de données multiples.
- [FIX] Enregistrement des positions de cartes.
- [CHANGE] Clean tests.
- [CHORES] Update dependencies.
- [FIX] Edition du titre.

## v1.2.3 (2025-10-09)

- [NEW] Possibilité de réduire les colonnes.
- [NEW] Affichage compact.
- [NEW] Export CSV / Excel.
- [UX] Modification de l'emplacement des paramètres dans le menu.
- [UX] Titre de la page lié au nom du tableau.
- Modifications mineures d'UX.

## v1.2.1 (2025-10-07)

- [NEW] Saisie et modification des tâches par la voix (nécessite un accès à une API de LLM OpenAI ou similaire).
- [NEW] Ajout de description pour les libellés et les listes.
- [UX] Possibilité de changer une carte de liste depuis son formulaire.
- [NEW] Utilisation de Whisper en local.

## v1.1.0 (2025-10-01)

- [NEW] Nouveaux rôles plus granulaires pour les utilisateurs.

## v1.0.0 (2025-09-19)

- [SECU] Configuration du token JWT en variable d'environnement.
- [SECU] Expiration du token JWT.
- [SECU] Cors origins.
- [FIX] Possibilité de créer des utilisateurs avec un email déjà utilisé (sur un utilisateur supprimé).
- [FIX] Nettoyage des commentaires dans la démo.
- [TESTS] Ajout de tests unitaires.

## v0.2.0 (2025-09-10)

- [NEW] Interface multilingue (français / anglais).
- [NEW] Commentaires sur les cartes.
- [NEW] Possibilité de changer le rôle d'un utilisateur existant.
- [NEW] Date d'échéance mise en avant quand elle est dépassée.

## v0.1.0 (2025-08-24)

- [NEW] Gestion de l'archivage / désarchivage.
- [NEW] Historique des actions effectuées sur les cartes.
- [FIX] Prise en compte du fuseau horaire pour les dates.

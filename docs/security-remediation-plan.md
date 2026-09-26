# Plan de remédiation — audit de sécurité du 2026-09-26

Source : `security-audit-skill/Yaka/run-1/REPORT.md` (révision auditée `a953a58`).
Branche : `worktree-security-audit-fixes`.

## Décisions validées

- Périmètre : F01–F19, pistes NV1/NV2, candidat rejeté (§5) et durcissements (§6).
- F02 : sans `DEFAULT_ADMIN_PASSWORD`, mot de passe admin aléatoire logué une seule fois + changement forcé à la première connexion (flag `must_change_password`, backend + desktop + mobile).
- F02 : au démarrage hors `DEMO_MODE`, les comptes démo `*@yaka.local` qui ont encore le mot de passe `Demo1234` sont désactivés, dans chaque board.
- F07/F09 : limitation de débit avec `slowapi`.
- F03 : claim `board` dans le JWT, comparée au contexte de la requête.
- F05 : un non-admin ne peut que _réduire_ son propre view-scope.
- F17 : endpoint conservé mais `card_id` pris du chemin et `user_id` de l'utilisateur courant.

## Règles communes

- Chaque tâche : tests backend ciblés + `uv run pytest` complet vert ; `pnpm run lint` et `pnpm run build` si le frontend est touché.
- Toute nouvelle colonne passe par une migration Alembic (appliquée à tous les boards par `run_migrations()`).
- `backend/app/utils/permissions.py` et `frontend/shared/utils/permissions.ts` restent synchronisés.
- Chaîne i18n nouvelle → `fr.json` et `en.json`.
- Un commit par tâche après développement, `/simplify` et `/code-review`.

## Tâches

### T1 — Secrets et configuration (F01, F19, §6 clé admin, `.gitignore`)

- `backend/app/utils/security.py` : plus de valeur de repli pour `JWT_SECRET` ; au démarrage, refus si absent, < 32 caractères ou égal à une valeur d'exemple connue.
- `docker-compose.yaml` : `JWT_SECRET=${JWT_SECRET:?...}` dans le service backend (+ `DEFAULT_ADMIN_PASSWORD` transmis, optionnel).
- `.env.sample` : consigne `openssl rand -hex 32` au lieu d'une valeur.
- `backend/app/routers/admin.py` : `hmac.compare_digest` ; refuser la valeur d'exemple `your-secret-admin-api-key-here`.
- F19 : supprimer `load_dotenv(override=True)` (`llm_service.py`) et tout rechargement de config dans un handler (`GET /auth/ai-features`).
- `.gitignore` : couvrir `.env.*` (sauf `.env.sample`).
- Tests : démarrage refusé sans secret / secret faible ; comparaison de clé admin ; priorité de l'environnement sur `.env`.
- `conftest.py` : définir un `JWT_SECRET` de test fort.

### T2 — Installation neuve et comptes par défaut (F02, coquille README)

- `demo_reset.setup_fresh_database()` : `create_demo_data` seulement si `is_demo_mode()`, sinon `create_demo_board_content` seul.
- Admin initial : `DEFAULT_ADMIN_PASSWORD` si défini, sinon mot de passe aléatoire (`secrets`) logué une seule fois (WARNING) ; `must_change_password=True` dans ce cas.
- Modèle `User` : colonne `must_change_password` (migration). Exposée dans la réponse de login / `/users/me`.
- Enforcement backend : tant que le flag est vrai, seules les routes de changement de mot de passe, `/users/me` et déconnexion sont autorisées (403 sinon) ; changement de mot de passe → flag remis à faux.
- Frontend desktop + mobile (`shared/`) : écran/dialogue de changement de mot de passe obligatoire quand le flag est vrai.
- Au démarrage hors mode démo : pour chaque board, désactiver les comptes `supervisor|editor|contributor|commenter|visitor@yaka.local` dont le hash correspond encore à `Demo1234` (log WARNING).
- README : corriger `admin@kyaka.local`, documenter le mot de passe initial.
- Tests : installation neuve hors démo → un seul compte ; flag et enforcement ; désactivation des comptes démo.

### T3 — Jetons de session (F03, F11, §6 comptes INVITED)

- JWT : claims `board` (uid ou valeur fixe pour la base par défaut) et `ver` (token_version).
- `get_current_user` : rejette si `board` ≠ contexte de la requête, si `ver` ≠ `user.token_version`, si statut ≠ `ACTIVE`.
- Colonne `token_version` (migration), incrémentée à chaque changement de mot de passe, rôle, statut et à la déconnexion.
- `POST /auth/logout` qui incrémente la version ; frontend (desktop + mobile) l'appelle à la déconnexion.
- Tests : jeton inter-boards refusé ; jeton invalide après reset/déconnexion/changement de rôle ; compte INVITED refusé.

### T4 — Réinitialisation et invitations (F04, F09 SMTP, F12, F13)

- `POST /auth/request-password-reset` : ne plus faire confiance au `board_uid` du corps — validation `^[a-zA-Z0-9-]{1,50}$` + existence du board (ou contexte validé).
- Liens construits avec composants encodés (`urllib.parse.quote`) ; `html.escape(..., quote=True)` sur toute valeur insérée dans les gabarits HTML (dont `DISPLAY_NAME`). Idem `invite_user` / `resend_invitation`.
- `smtplib.SMTP/SMTP_SSL(..., timeout=10)` ; envoi hors boucle d'événements (handler `def` ou `BackgroundTasks`).
- Délai minimal entre deux jetons de reset pour un même utilisateur.
- TTL : reset ≈ 1 h, invitation ≈ 7 jours ; jeton expiré rejeté et effacé.
- `update_user` : changement de mot de passe → vide `invite_token` / `invited_at`.
- Tests : board_uid invalide refusé ; échappement HTML ; jeton expiré ; jeton invalidé après changement admin.

### T5 — Login (F07, F14, limitation F07/F09)

- `slowapi` : limite par IP sur `/auth/login` et `/auth/request-password-reset` (+ par compte côté login). 429 propre. Désactivable en tests.
- Vérification bcrypt hors boucle (`run_in_threadpool` ou handler `def`).
- F14 : comparaison contre un hash factice pour un utilisateur inconnu/inactif ; mot de passe > 72 octets → 401 (login) et 422 (schémas set-password/changement alignés sur 72 octets).
- Tests : 429 après N tentatives ; mot de passe long → 401 ; chemin inconnu exécute bcrypt.

### T6 — View-scope (F05, F06)

- F05 : `PUT /users/{id}/view-scope` — admin : libre ; soi-même non-admin : uniquement réduction (`ALL` > `UNASSIGNED_PLUS_MINE` > `MINE_ONLY`).
- F06 : helper unique `get_accessible_card_or_404(db, card_id, user)` utilisé par cartes, commentaires, checklist, historique et toutes les mutations ; `apply_view_scope_filter` sur les compteurs de liste ; `current_user` passé à l'export.
- Tests : auto-élargissement refusé ; 404/403 sur sous-ressources et export filtré.

### T7 — Voice-control / LLM (F08, F16, NV2)

- Client OpenAI : `timeout=30`, `max_retries=1` ; appels hors boucle (`run_in_threadpool` ou `AsyncOpenAI`).
- Quota par utilisateur (slowapi) et sémaphore global.
- F16 : prompt n'utilise que `display_name` ou `Utilisateur #<id>` ; pas d'emails.
- NV2 : `max_length` sur la description de carte (schémas create/update), troncature des descriptions et plafond global du contexte LLM.
- Tests : pas d'email dans le prompt ; description trop longue → 422 ; contexte plafonné.

### T8 — Export (F10)

- Neutraliser les valeurs commençant par `= + - @ \t \r` (apostrophe) dans CSV et XLSX ; forcer le type chaîne en XLSX.
- Tests : cellule non formule, CSV préfixé.

### T9 — Données utilisateurs et historique (F15, F17, §6 routeur orphelin)

- Schéma public `UserPublic` (`id`, `display_name`) pour les utilisateurs imbriqués (commentaires, historique, cartes) ; vérifier l'usage frontend de `email` sur ces objets.
- F17 : `card_id` du chemin, `user_id` = utilisateur courant.
- Supprimer `backend/app/routers/card_history.py` (non monté).
- Tests : pas d'email pour un VISITOR ; entrée d'historique forcée impossible.

### T10 — Multi-board et administration (F18, §5, §6 erreurs)

- `evict_board(uid)` (pop + `dispose()`) dans `multi_database.py`, appelé à la suppression et avant la création d'un board.
- `GET /admin/boards/{uid}` : `Depends(verify_admin_api_key)`, plus de `database_path`.
- Ne plus renvoyer `str(e)` dans les 500 (`admin.py`, `main.py`) — logguer côté serveur.
- Tests : recréation après suppression ; endpoint sans clé → 401 ; message d'erreur générique.

### T11 — Durcissement HTTP / frontend (NV1, §6 CORS, nginx, docs, whisper-poc)

- `frontend/nginx.conf` (+ mobile si distinct) : CSP avec `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff` ; `api-config.js` en `no-cache`.
- NV1 : exclure les routes authentifiées du cache Workbox et vider `api-cache` à la connexion/déconnexion.
- CORS : ignorer les origines vides ; pas de `http://localhost` mobile par défaut en production.
- `/docs`, `/redoc`, `/openapi.json` désactivés quand `ENVIRONMENT=production`.
- Supprimer `frontend/whisper-poc.html`.

### T12 — Docker (§6)

- Épingler les images de base par digest.
- Installer les dépendances Python au build (`uv sync --frozen --no-dev`) et lancer sans résolution au démarrage.

### T13 — Documentation (étape finale)

- README, CHANGELOG, `.env.sample`, `docs/*`, `VERSION`, `TODO.md` : variables obligatoires (`JWT_SECRET`), mot de passe initial, comptes démo, rate-limit, logout, notes de migration (tous les jetons invalidés).

## Avancement

| Tâche | Dev | /simplify                     | /code-review | Commit |
| ----- | --- | ----------------------------- | ------------ | ------ |
| T1    | ✅  | ✅ (12 findings, 7 appliqués) | ✅ (10 → 7)  | ✅     |
| T2    | ☐   | ☐                             | ☐            | ☐      |
| T3    | ☐   | ☐                             | ☐            | ☐      |
| T4    | ☐   | ☐                             | ☐            | ☐      |
| T5    | ☐   | ☐                             | ☐            | ☐      |
| T6    | ☐   | ☐                             | ☐            | ☐      |
| T7    | ☐   | ☐                             | ☐            | ☐      |
| T8    | ☐   | ☐                             | ☐            | ☐      |
| T9    | ☐   | ☐                             | ☐            | ☐      |
| T10   | ☐   | ☐                             | ☐            | ☐      |
| T11   | ☐   | ☐                             | ☐            | ☐      |
| T12   | ☐   | ☐                             | ☐            | ☐      |
| T13   | ☐   | —                             | —            | ☐      |

## Journal

- Baseline `a953a58` : 1124 passés, 7 erreurs `PermissionError [WinError 32]` au teardown (verrou de fichier Windows, hors périmètre), 25 min.

- T1 terminé : JWT_SECRET obligatoire (≥32 car. non blancs, ≥8 car. distincts), clé admin ≥32 car. + compare_digest (warning si trop courte), plus de `override=True`, `.env.*` ignoré par git et Docker, README. Tests : 1141 passés, 7 erreurs préexistantes. Renvoyé à T2 : init admin (`Admin123`, log de démarrage, `DEFAULT_ADMIN_PASSWORD` invalide avalé).

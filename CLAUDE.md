# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

YAKA ("Yet Another Kanban App") — self-hosted collaborative Kanban with voice control via an OpenAI-compatible LLM. FastAPI + SQLite backend, two React frontends (desktop + mobile PWA) sharing a common code layer. Version in `VERSION`, history in `CHANGELOG.md`, open items in `TODO.md`.

Code comments, docstrings and commit history are largely in French; user-facing strings live in i18n catalogs (fr/en). Match the surrounding language when editing a file.

## Commands

### Backend (`backend/`, Python 3.12+, uv)

```bash
uv run uvicorn app.main:app --reload      # dev server → http://localhost:8000 (docs at /docs)
uv run pytest                             # full suite (~1124 tests)
uv run pytest tests/test_card.py          # one file
uv run pytest tests/test_card.py::TestCardService::test_x   # one test
uv run pytest -k "position"               # by name
uv run alembic revision --autogenerate -m "msg"   # new migration
uv run python scripts/create_board.py <board_uid> [admin_email]   # provision a board DB
uv run python generate_response_model.py schema_reponse.json      # regenerate app/models/response_model.py
```

`pytest.ini_options` in `pyproject.toml` sets `asyncio_mode = "auto"` — async tests need no marker.

### Frontend (`frontend/`, pnpm)

```bash
pnpm install
pnpm run dev        # desktop app → http://localhost:5173
pnpm run test       # vitest, single run
pnpm run lint       # eslint
pnpm run build      # tsc-less vite build

cd mobile && pnpm install && pnpm run dev   # mobile PWA → http://localhost:3001
```

`packageManager` pins pnpm — use pnpm, never npm.

### Docker (full stack)

```bash
cp .env.sample .env   # then fill SMTP + optional OPENAI_* + YAKA_ADMIN_API_KEY
docker compose build && docker compose up -d
```

Services: `backend` (8000), `frontend-desktop` (3000), `frontend-mobile` (3001), `demo-cron` (hourly `POST /demo/reset` when `DEMO_MODE=true`).

## Architecture

### Multi-database: one SQLite file per board

The single most load-bearing design decision. Each board is a **separate SQLite file** at `backend/data/{board_uid}.db`; `data/yaka.db` is the default/legacy board.

Flow: `BoardContextMiddleware` (`app/utils/board_context.py`) regex-matches `^/board/{board_uid}/` on the request path, validates the uid (`[a-zA-Z0-9-]{1,50}`), checks the `.db` file exists (401 otherwise), and stores it in a `ContextVar` (`app/multi_database.py`). Routers depend on `get_dynamic_db()`, which resolves the engine/session for that ContextVar, falling back to the default DB when unset.

Consequences:

- **Every router is registered twice** in `app/main.py` — bare (`/cards`) for backwards compatibility and under `/board/{board_uid}` — so a new router must be added to both `include_router` blocks.
- Any code path that opens a session outside a request (background work, scripts) must set the board context itself or use `get_board_db(board_uid)`.
- Engines and sessionmakers are cached per board in module-level dicts in `multi_database.py`.
- `/admin/*` (`app/routers/admin.py`) is global, has **no** board prefix, and is guarded by a bearer token equal to `YAKA_ADMIN_API_KEY` — not by JWT.

### Migrations run at import time, across all boards

`app/main.py` calls `ensure_database_exists()` and `run_migrations()` at **module import**, before the FastAPI app is created. `run_migrations()` globs `./data/*.db` and upgrades each one to head, stamping `alembic_version` for pre-Alembic databases. So importing `app.main` (including in tests) touches the filesystem and can migrate real data; the working directory must be `backend/` for `alembic.ini` to resolve.

Seeding happens in the `lifespan` hook: an empty DB triggers `setup_fresh_database()` (`app/utils/demo_reset.py`), creating the default admin `admin@yaka.local` / `Admin123`.

### Backend layering

`routers/` (HTTP + auth deps) → `services/` (business logic, commits) → `models/` (SQLAlchemy 2.0 `DeclarativeBase`, `Mapped[...]`) with `schemas/` holding Pydantic I/O. Services own the transaction: they `db.commit()`, `db.refresh()`, and `db.rollback()` on `SQLAlchemyError`.

Cross-cutting concerns:

- **Permissions** — `app/utils/permissions.py` exposes `is_*_or_above()` predicates and `ensure_can_*()` guards that raise 403. Two orthogonal axes:
  - 6-level role hierarchy: `VISITOR < COMMENTER < CONTRIBUTOR < EDITOR < SUPERVISOR < ADMIN` (`models/user.py:UserRole`).
  - `ViewScope` (`ALL`, `UNASSIGNED_PLUS_MINE`, `MINE_ONLY`) filtering which cards a user can see at all.
  - **This file is mirrored in `frontend/shared/utils/permissions.ts` with the same function names.** Change both together or the UI and API disagree.
- **Card ordering** — `cards.position` is a manually maintained integer per list. `services/card.py` shifts neighbouring non-archived cards on move; don't reorder cards by writing `position` directly.
- **History** — card mutations log an entry through `services/card_history.py`; new mutating operations should do the same.

### Voice control / LLM

`POST /voice-control/` (`routers/voice_control.py`) truncates the transcript to 500 chars, then `services/llm_service.py` calls an OpenAI-compatible endpoint (`OPENAI_API_KEY`, `OPENAI_API_BASE_URL`, `LLM_MODEL`, `MODEL_TEMPERATURE`) and validates the reply against Pydantic models in `models/response_model.py` (`AutoIntentResponse`, `CardEditResponse`, `CardFilterResponse`, `UnknownResponse`). Two-step: intent detection first, then the typed response for that intent.

`models/response_model.py` is **generated** from `schema_reponse.json` by `generate_response_model.py` — edit the JSON schema and regenerate rather than hand-editing the module. `LLMService.__init__` raises if `OPENAI_API_KEY` is unset, so the feature is off (not degraded) without a key. Global and personal dictionaries (`models/global_dictionary.py`, `personal_dictionary.py`) feed the prompt to improve recognition of project-specific vocabulary.

### Frontend: two apps, one shared layer

```text
frontend/
  src/          desktop app (shadcn/ui + Radix, dnd-kit, framer-motion)  → alias @
  mobile/       mobile PWA (own package.json, vite-plugin-pwa, port 3001)
  shared/       services, hooks, contexts, types, utils, i18n           → alias @shared
```

`shared/` is the contract between the two apps: `services/api.tsx` (the axios instance and most endpoints), `services/listsApi.ts`, `cardsApi.ts`, `exportApi.ts`, `voiceControlApi.ts`, the auth/board-settings/users contexts, `utils/permissions.ts`, `types/index.ts`, and the `i18n/locales/{en,fr}.json` catalogs. A change here hits desktop and mobile — check both. The mobile app is a distinct UI (screens + bottom nav), not a responsive variant of the desktop components.

**API base URL resolution** (`shared/services/api.tsx`), in order:

1. `localStorage['api_base_url']` — set by the mobile app's config screen, used verbatim.
2. otherwise `window.API_BASE_URL` (injected by `/api-config.js`, written by the nginx container entrypoint from `API_BASE_URL`) or `http://localhost:8000`, with `/board/{board_uid}` appended when the browser URL is `/board/{uid}/...`.

The JWT lives in `localStorage['token']`; a 401 response clears it and redirects, except on `/login` and `/invite`.

## Gotchas

- **`frontend/vitest.config.ts` defines only the `@` alias, not `@shared`.** Vitest uses that file instead of `vite.config.ts`, so 7 of the 9 test files currently fail to collect with `Failed to resolve import "@shared/..."` (28 tests in the 2 collectible files pass). If you touch frontend tests, add the `@shared` alias there first rather than assuming your change broke them.
- `docs/backend-technical-documentation.md` and `docs/frontend-technical-documentation.md` predate the mobile app and the `shared/` split — the directory trees they show are stale. Trust the code.
- `redirect_slashes=False` on the FastAPI app: trailing slashes matter (`/voice-control/`, not `/voice-control`).
- `TrustedHostMiddleware` allows only `localhost`, `127.0.0.1`, `testserver` and the host derived from `BASE_URL` — a wrong `BASE_URL` yields opaque 400s.
- Backend tests build isolated apps via the `build_test_app` / `async_client_factory` fixtures in `tests/conftest.py`, overriding `get_dynamic_db` against a temp SQLite file. Follow that pattern instead of importing the real `app`.

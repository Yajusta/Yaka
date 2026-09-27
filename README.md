# YAKA - Yet Another Kanban App

[FRANÇAIS](README.fr.md) - **ENGLISH**

![Logo](https://raw.githubusercontent.com/Yajusta/Yaka/refs/heads/main/frontend/public/yaka.ico)

A modern and intuitive web application for collaborative task management using the Kanban methodology.

NEW: **Voice control**
Manage your tasks with your voice using natural language thanks to the power of AI.

## 🖼️ Screenshots

![Board](./docs/screenshot-001.png)

![Card](./docs/screenshot-002.png)

## 🖥️ Demo

To see what this application looks like before installing it, the easiest way is to try [the demo](https://yaka-demo.yajusta.fr/).

Username: `admin@yaka.local`
Password: `Admin123`

🗑️ The database is regularly deleted.
⚠️ The environment is public: do not put sensitive information.
Email invitation sending is disabled.

## ⚙️ Features

- **Interactive Kanban Board**
- **Manage tasks with your voice with AI**
- **Drag & Drop** for moving cards smoothly
- **Secure Authentication** with JWT
- **Detailed Cards** with title, description, checklist, priority, assignee, labels, due date, comments
- **Search and filters**
- **Unlimited Users**
- **Role Management** (administrator / member)
- **Column Management** to add as many columns as needed
- **Colored Label Management** for categorization
- **Event History** to track who did what
- **Archive Management** to never lose anything

## 📝 Changelog

[Changelog](CHANGELOG.md)

## 🚀 Deployment

The simplest method to use Yaka without hassle.

### 1. Clone the project

```bash
git clone https://github.com/Yajusta/Yaka.git
cd Yaka
```

### 2. Modify environment variables

```bash
cp .env.sample .env
```

And fill in the necessary environment variables.

`JWT_SECRET` is **required**: the backend refuses to start (and `docker compose` aborts) if it is missing or shorter than 32 characters. Generate one with:

```bash
openssl rand -hex 32
```

`YAKA_ADMIN_API_KEY` is optional; leave it empty to disable the `/admin` endpoints, or set a random value of at least 32 characters (same command).

`API_BASE_URL` must be the absolute URL of the backend as seen by the browsers (`https://api.example.com`): its origin is added to the Content-Security-Policy of the frontends, and any other origin is blocked. All variables are listed in [Environment variables](#-environment-variables).

### 3. Give the data directory to the container user

The backend container runs as the unprivileged uid `10001`, and `./data/` is bind-mounted into it. That directory (and everything in it) must belong to that uid, otherwise SQLite opens the board databases read-only and any write fails with `sqlite3.OperationalError: attempt to write a readonly database`.

```bash
mkdir -p data
sudo chown -R 10001:10001 data/
```

The directory itself matters as much as the `.db` files: SQLite writes `-journal`/`-wal` siblings, and provisioning a new board creates a new file.

### 4. Deploy with Docker

```bash
docker compose build
docker compose up -d
```

Building requires BuildKit (the default since Docker 23 and with `docker compose` v2).

On first start, unless `DEFAULT_ADMIN_PASSWORD` is set, the initial administrator password is printed **once** in the backend logs, and must be changed at first login:

```bash
docker compose logs backend | grep "Administrateur initial"
```

Maintenance scripts run inside the container with `python` (not `uv run`, the virtual environment is read-only):

```bash
docker compose exec backend python scripts/create_board.py <board_uid> [admin_email]
```

### 5. Update an existing instance

Read the **Breaking changes** section of the [changelog](CHANGELOG.md) before updating: version 1.6.0 requires `JWT_SECRET`, the `chown` of step 3, and logs every user out.

```bash
docker compose down
docker compose build
docker compose up -d
```

TODO: Create a public Docker image that won't require cloning the project.

## 📦 Installation and startup

If you want to run it manually, that's possible too.

### 📋 Prerequisites

- [Python](https://www.python.org/downloads/) 3.12+ + [uv](https://docs.astral.sh/uv/)
- [Node.js](https://nodejs.org/download) 18+
- [pnpm](https://pnpm.io/) (recommended) or [npm](https://www.npmjs.com/)

### 1. Clone the project

```bash
git clone https://github.com/Yajusta/Yaka.git
cd Yaka
```

### 2. Mail server configuration

Copy/paste the `.env.sample` file to `.env` and fill in the configuration parameters for your SMTP server.

Example:

```txt
# Parameters for email sending
SMTP_HOST = "smtp.resend.com"
SMTP_PORT = 587
SMTP_USER = "resend"
SMTP_PASS = "re_xxxxxxxxxxxx"
# values: 'ssl'|'starttls'|'none'
SMTP_SECURE = "starttls"
SMTP_FROM = "no-reply@domain.com"
```

Also set `JWT_SECRET` (required, at least 32 characters, e.g. `openssl rand -hex 32`); the backend will not start without it.

### 3. (optional) AI endpoint

The LLM model that will be used to analyze natural language requests.
Leave empty to disable the feature.

```txt
## AI features (leave empty to disable)
OPENAI_API_KEY=sk-proj-bim-bam-boum
OPENAI_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-5-nano
MODEL_TEMPERATURE=
```

### 4. Start the backend

```bash
cd backend
uv run uvicorn app.main:app --reload
```

A virtual environment will be automatically created with all necessary dependencies.
The backend will be accessible at <http://localhost:8000>

### 5. Start the frontend

```bash
cd frontend
pnpm install
pnpm run dev
```

The frontend will be accessible at <http://localhost:5173>

### 6. Trunk checks

To check code quality with Trunk:

```bash
cd frontend
npm run trunk -- upgrade
npm run trunk -- check --all --no-fix
```

## 👤 Default administrator account

An administrator account is automatically created during initialization:

- **Email:** `admin@yaka.local` (or `DEFAULT_ADMIN_EMAIL`)
- **Password:** the value of `DEFAULT_ADMIN_PASSWORD` if set (ignored outside demo mode if it is the public `Admin123`; at least 8 characters with an uppercase letter, a lowercase letter and a digit, otherwise startup fails). If it is not set, a random password is generated and printed **once** in the backend logs (`WARNING ... Administrateur initial créé`), and must be changed at first login: until then, the account can only change its password or log out.

Once connected, **create a new administrator** with your email then **delete this default account**.

Demo accounts (`supervisor@`, `editor@`, `contributor@`, `commenter@`, `visitor@yaka.local`, password `Demo1234`) are only created when `DEMO_MODE=true`. Outside demo mode, at each startup and for every board, the backend disables any of these accounts still using `Demo1234` (or, if it was promoted to administrator, resets its password as below), and, if `admin@yaka.local` (or `DEFAULT_ADMIN_EMAIL`) still uses `Admin123`, replaces that password with a random one printed **once** in the `WARNING` log line (`Public default passwords detected`) and to be changed at next login.

## 🔧 Environment variables

Defined in `.env` (Docker, see `.env.sample`) or `backend/.env` (manual install, see `backend/.env.sample`). An empty value means the default.

| Variable                                                                       | Default                                                                         | Description                                                                                                                                                      |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `JWT_SECRET`                                                                   | — (**required**)                                                                | Session signing key: at least 32 non-blank characters and 8 distinct ones, otherwise the backend does not start. `openssl rand -hex 32`.                         |
| `YAKA_ADMIN_API_KEY`                                                           | empty                                                                           | Bearer key of the `/admin` endpoints (board management). Empty or shorter than 32 characters: `/admin` answers 503.                                              |
| `DEFAULT_ADMIN_PASSWORD`                                                       | empty                                                                           | Initial administrator password, used only when a database is created. Empty: random password printed once in the logs, to be changed at first login.             |
| `DEFAULT_ADMIN_EMAIL`                                                          | `admin@yaka.local`                                                              | Initial administrator email (manual install; not passed by `docker-compose.yaml`).                                                                               |
| `BASE_URL` / `BASE_URL_MOBILE`                                                 | `http://localhost:3000` / `http://localhost:3001` (Docker)                      | Public URLs of the desktop and mobile frontends: links in emails, CORS origins; the host of `BASE_URL` is the only one accepted besides `localhost`/`127.0.0.1`. |
| `API_BASE_URL`                                                                 | `http://localhost:8000`                                                         | Backend URL used by the browsers. Must be absolute (`http(s)://host[:port]`) to be allowed by the CSP.                                                           |
| `ENVIRONMENT`                                                                  | `production`                                                                    | Only the exact value `development` enables `/docs`, `/redoc`, `/openapi.json` and the `http://localhost` / `file://` origins; any other value means production.  |
| `ALLOWED_ORIGINS`                                                              | empty                                                                           | Extra CORS origins, comma-separated.                                                                                                                             |
| `MOBILE_ORIGINS`                                                               | `capacitor://localhost,ionic://localhost` (+ `http://localhost` in development) | Mobile app origins. A value replaces the default; `","` allows none.                                                                                             |
| `LOGIN_RATE_LIMIT`                                                             | `10/minute`                                                                     | Per IP: login and password change.                                                                                                                               |
| `PASSWORD_RESET_RATE_LIMIT`                                                    | `5/minute`                                                                      | Per IP: password reset request.                                                                                                                                  |
| `LOGIN_ACCOUNT_RATE_LIMIT`                                                     | `5 per 15 minutes`                                                              | Per account (board + email or user): login and password change attempts, reset after a success.                                                                  |
| `VOICE_CONTROL_RATE_LIMIT`                                                     | `20/minute`                                                                     | Per user: voice control requests (429 beyond).                                                                                                                   |
| `LLM_MAX_CONCURRENT_CALLS`                                                     | `4`                                                                             | Simultaneous LLM calls for the whole backend (503 beyond).                                                                                                       |
| `FORWARDED_ALLOW_IPS`                                                          | `127.0.0.1`                                                                     | Proxies trusted to send the client IP in `X-Forwarded-For` (read by uvicorn from the process environment).                                                       |
| `DEMO_MODE`                                                                    | `false`                                                                         | Public demo: demo accounts, `POST /demo/reset`, no server-side logout.                                                                                           |
| `DEFAULT_LANGUAGE`                                                             | `fr` (Docker)                                                                   | Language of the initial accounts.                                                                                                                                |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_SECURE`, `SMTP_FROM` | see `.env.sample`                                                               | Mail server (invitations, password reset). `SMTP_SECURE`: `ssl`, `starttls` or `none`.                                                                           |
| `OPENAI_API_KEY`, `OPENAI_API_BASE_URL`, `LLM_MODEL`, `MODEL_TEMPERATURE`      | empty                                                                           | OpenAI-compatible endpoint for voice control; no key = feature disabled.                                                                                         |
| `FRONTEND_DESKTOP_PORT` / `FRONTEND_MOBILE_PORT`                               | `3000` / `3001`                                                                 | Host ports of the frontends (Docker).                                                                                                                            |

Rate limits use the [`limits`](https://limits.readthedocs.io/) syntax (`10/minute`, `5 per 15 minutes`, several limits separated by `;`); an invalid value stops the backend at startup, as does an invalid `LLM_MAX_CONCURRENT_CALLS`. Keep comments on their own line in `.env` files.

## 🔒 Security and deployment

- **Reverse proxy**: rate limits are per client IP. Behind a proxy, set `FORWARDED_ALLOW_IPS` to the proxy's IP or network (in Docker, the bridge gateway or the proxy container, never `127.0.0.1`), and publish the backend port on `127.0.0.1` only; never use `*` if the backend port is reachable. Otherwise every client shares the proxy's IP and its limits.
- **Single worker**: rate-limit counters live in the memory of the process (reset on restart). The image runs one uvicorn worker; do not add workers or replicas.
- **Account lockout**: after 5 failed login attempts in 15 minutes (default), the account is blocked for that board, including for its owner (429). Anyone knowing an email can trigger it; adjust `LOGIN_ACCOUNT_RATE_LIMIT` if needed.
- **Sessions**: a token is bound to its board, so a browser is logged in to one board at a time. Logging out, changing a password or a role, or deleting a user revokes all of that user's sessions on every device.
- **HTTP headers**: the frontend nginx sends a Content-Security-Policy (`connect-src` limited to the origin of `API_BASE_URL` and to the Hugging Face / jsDelivr CDNs used by Whisper speech recognition), `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff` and a `Permissions-Policy` that only allows the microphone.
- **Docker images**: base images are pinned by digest (`backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yaml`). Refresh the digests regularly to get security fixes, then rebuild.
- **Data**: `./data` holds one SQLite file per board and must belong to uid `10001`.

## 🧪 Demo mode

`DEMO_MODE=true` is for public demonstrations only: it creates the demo accounts (`admin@yaka.local` with `DEFAULT_ADMIN_PASSWORD` or `Admin123`, the others with `Demo1234`), enables `POST /demo/reset` (called every hour by the `demo-cron` service) and disables server-side logout. Never enable it on an instance holding real data. When switching back to `DEMO_MODE=false`, the demo accounts still using `Demo1234` are disabled at the next start, and an administrator still using `Admin123` gets a random password (see [Default administrator account](#-default-administrator-account)).

## 📖 Documentation

- [Frontend Technical Guide](docs/frontend-technical-documentation.md) - Complete frontend documentation
- [Backend Technical Guide](docs/backend-technical-documentation.md) - Complete backend documentation
- [User Guide](docs/user-guide.md) - Application user manual

## 📄 License

This project is under **Non-Commercial License**: you can use and modify the application, but without making its use paid without the author's agreement.

## 🆘 Support

For any questions or problems:

1. Consult the [documentation](docs/)
2. Check [existing issues](https://github.com/Yajusta/Yaka/issues)
3. Create a new issue if necessary

## 🔄 Hypothetical Roadmap

- [ ] Real-time notifications (websockets)
- [ ] Attachments
- [ ] Reports and analytics
- [ ] Public API
- [ ] Third-party integrations (Slack, Teams, etc.)

## 🛠️ Technologies

### Backend

- **FastAPI** - Modern and performant Python web framework
- **SQLAlchemy** - ORM for database management
- **SQLite** - Embedded database
- **JWT** - Token authentication
- **Pydantic** - Data validation and serialization

### Frontend

- **React** - JavaScript library for user interface
- **shadcn/ui** - Modern and accessible UI components
- **Tailwind CSS** - Utility-first CSS framework
- **Vite** - Fast build tool

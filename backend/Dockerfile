# Image épinglée par digest (index multi-arch) : le tag reste indicatif, seul le
# digest fait foi. Pour mettre à jour : récupérer le nouveau digest du tag.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Utiliser le Python de l'image, jamais un interpréteur téléchargé ; précompiler
# le bytecode au build (le venv est en lecture seule à l'exécution) ; copier
# depuis le cache monté plutôt que d'y créer des liens.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# OS deps for TLS + healthcheck (toutes les dépendances Python ont des wheels :
# pas de compilateur dans l'image)
# Les versions apt ne sont volontairement pas épinglées : bookworm reçoit des
# correctifs de sécurité en continu et les anciennes versions disparaissent du
# dépôt, ce qui casserait le build. La reproductibilité vient du digest de l'image.
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances au build, strictement depuis uv.lock (--locked : le
# build échoue si uv.lock ne correspond plus à pyproject.toml) : copier les
# fichiers de dépendances avant le code pour garder cette couche en cache. Le
# cache uv est monté et ne finit donc pas dans l'image ; --mount exige BuildKit
# (défaut de Docker >= 23 et de docker compose v2+, pas de DOCKER_BUILDKIT=0).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# Make the venv binaries available (docker exec, healthchecks)
# Dans le conteneur, lancer les scripts avec `python` (ex. `docker compose exec
# backend python scripts/create_board.py <board_uid>`), pas `uv run` : il
# tenterait de resynchroniser le venv, en lecture seule pour l'UID 10001.
ENV PATH="/app/.venv/bin:$PATH"

# Copy the rest of the source (includes app/)
COPY . .

# Exécuter l'application sous un compte non privilégié. Le code et le venv
# restent la propriété de root (lecture seule pour l'application) ; seul
# /app/data, où vivent les bases SQLite, doit être accessible en écriture.
# Un bind mount (./data de docker-compose.yaml) masque ce répertoire : le
# dossier de l'hôte doit alors appartenir à l'UID 10001 (chown 10001:10001 data).
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown appuser:appuser /app/data
USER 10001

EXPOSE 8000

HEALTHCHECK --interval=300s --timeout=10s --start-period=5s --retries=3 \
    CMD ["curl", "-fsS", "http://localhost:8000/health"]

# Lancer directement l'uvicorn du venv : aucune résolution ni installation de
# dépendances au démarrage (contrairement à `uv run`). Un seul worker : la
# limitation de débit est en mémoire, propre à chaque processus.
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

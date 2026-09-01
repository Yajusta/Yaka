FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# OS deps for TLS + healthcheck
# Les versions apt ne sont volontairement pas épinglées : bookworm reçoit des
# correctifs de sécurité en continu et les anciennes versions disparaissent du
# dépôt, ce qui casserait le build. La reproductibilité vient du tag de l'image.
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create venv and install deps without invoking project packaging
RUN uv venv .venv

# Make the venv active for runtime
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy the rest of the source (includes app/)
COPY . .

# Exécuter l'application sous un compte non privilégié.
# `uv run` installe les dépendances au premier démarrage et l'application écrit
# dans /app/data : tout /app doit donc appartenir à cet utilisateur.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER 10001

EXPOSE 8000

HEALTHCHECK --interval=300s --timeout=10s --start-period=5s --retries=3 \
    CMD ["curl", "-fsS", "http://localhost:8000/health"]

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

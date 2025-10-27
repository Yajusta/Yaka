# Étape de build pour la version desktop
FROM node:22-alpine AS desktop-builder

# Installer les dépendances système et mettre à jour
RUN apk update && apk upgrade

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de configuration des dépendances
COPY package*.json pnpm-lock.yaml ./

# Installer pnpm globalement
RUN npm install -g pnpm

# Installer les dépendances
RUN pnpm install --frozen-lockfile

# Copier le code source
COPY . .

# Construire l'application desktop (génère le dossier dist)
RUN pnpm build

# Étape de build pour la version mobile
FROM node:22-alpine AS mobile-builder

# Installer les dépendances système et mettre à jour
RUN apk update && apk upgrade

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de configuration des dépendances
COPY package*.json pnpm-lock.yaml ./

# Installer pnpm globalement
RUN npm install -g pnpm

# Installer les dépendances
RUN pnpm install --frozen-lockfile

# Copier le code source
COPY . .
ARG VITE_BASE_PATH=/m/
ENV VITE_BASE_PATH=$VITE_BASE_PATH
# Construire la version mobile
WORKDIR /app/mobile
COPY mobile/package*.json ./
RUN pnpm install --frozen-lockfile
COPY mobile/index.html ./
COPY mobile/vite.config.ts ./
RUN pnpm build

# Étape de production pour desktop
FROM nginx:alpine AS desktop-production

# Utiliser l'argument de build pour les variables d'environnement
ARG DEMO_MODE=false
ARG API_BASE_URL=http://localhost:8000
ARG BASE_URL=http://localhost:3000
ARG BASE_URL_MOBILE=http://localhost:3001

# Copier les fichiers statiques générés depuis l'étape de build desktop
COPY --from=desktop-builder /app/dist /usr/share/nginx/html

# Script d'initialisation qui génère les fichiers de config au démarrage
RUN echo '#!/bin/sh' > /docker-entrypoint.sh && \
    echo 'set -e' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo '# Generate configuration files from environment variables' >> /docker-entrypoint.sh && \
    echo 'echo "window.DEMO_MODE = \"${DEMO_MODE:-false}\";" > /usr/share/nginx/html/demo-config.js' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo 'echo "window.API_BASE_URL = \"${API_BASE_URL:-http://localhost:8000}\";" > /usr/share/nginx/html/api-config.js' >> /docker-entrypoint.sh && \
    echo 'echo "window.BASE_URL = \"${BASE_URL:-http://localhost:3000}\";" >> /usr/share/nginx/html/api-config.js' >> /docker-entrypoint.sh && \
    echo 'echo "window.BASE_URL_MOBILE = \"${BASE_URL_MOBILE:-http://localhost:3001}\";" >> /usr/share/nginx/html/api-config.js' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo 'exec "$@"' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# Copier une configuration Nginx personnalisée (optionnel, pour SPA)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exposer le port 80 (standard pour Nginx)
EXPOSE 80

# Healthcheck pour vérifier que le serveur Nginx répond
HEALTHCHECK --interval=300s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Lancer Nginx via le script d'entrée
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]

# Étape de production pour mobile
FROM nginx:alpine AS mobile-production

# Utiliser l'argument de build pour les variables d'environnement
ARG DEMO_MODE=false
ARG API_BASE_URL=http://localhost:8000
ARG BASE_URL=http://localhost:3000
ARG BASE_URL_MOBILE=http://localhost:3001

# Copier les fichiers statiques générés depuis l'étape de build mobile
COPY --from=mobile-builder /app/mobile/dist /usr/share/nginx/html

# Script d'initialisation qui génère les fichiers de config au démarrage
RUN echo '#!/bin/sh' > /docker-entrypoint.sh && \
    echo 'set -e' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo '# Generate configuration files from environment variables' >> /docker-entrypoint.sh && \
    echo 'echo "window.DEMO_MODE = \"${DEMO_MODE:-false}\";" > /usr/share/nginx/html/demo-config.js' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo 'echo "window.API_BASE_URL = \"${API_BASE_URL:-http://localhost:8000}\";" > /usr/share/nginx/html/api-config.js' >> /docker-entrypoint.sh && \
    echo 'echo "window.BASE_URL = \"${BASE_URL:-http://localhost:3000}\";" >> /usr/share/nginx/html/api-config.js' >> /docker-entrypoint.sh && \
    echo 'echo "window.BASE_URL_MOBILE = \"${BASE_URL_MOBILE:-http://localhost:3001}\";" >> /usr/share/nginx/html/api-config.js' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo 'exec "$@"' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# Copier une configuration Nginx personnalisée (optionnel, pour SPA)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exposer le port 80 (standard pour Nginx)
EXPOSE 80

# Healthcheck pour vérifier que le serveur Nginx répond
HEALTHCHECK --interval=300s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Lancer Nginx via le script d'entrée
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
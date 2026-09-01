# Étape de build pour la version desktop
FROM node:22-alpine AS desktop-builder

# Installer les dépendances système et mettre à jour
RUN apk update && apk upgrade

# Définir le répertoire de travail
WORKDIR /app

# pnpm est non interactif dans Docker : sans CI il tente de demander
# confirmation (ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY)
ENV CI=true

# Copier les fichiers de configuration des dépendances
COPY package*.json pnpm-lock.yaml ./

# Installer pnpm (version alignée sur `packageManager`) puis les dépendances
RUN npm install -g pnpm@10.19.0 \
    && pnpm install --frozen-lockfile

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

# pnpm est non interactif dans Docker : sans CI il tente de demander
# confirmation (ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY)
ENV CI=true

# Copier les fichiers de configuration des dépendances
COPY package*.json pnpm-lock.yaml ./

# Installer pnpm (version alignée sur `packageManager`) puis les dépendances
RUN npm install -g pnpm@10.19.0 \
    && pnpm install --frozen-lockfile

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

# Copier une configuration Nginx personnalisée (optionnel, pour SPA)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Script d'initialisation qui génère les fichiers de config au démarrage
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Nginx tourne sous l'utilisateur `nginx` (non root) : le PID va dans /tmp et
# l'entrypoint doit pouvoir écrire les fichiers de config dans le dossier servi.
RUN chmod +x /docker-entrypoint.sh \
    && sed -i 's|^pid .*|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf \
    && chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx
USER 101

# Exposer le port 8080 (port non privilégié, requis en non root)
EXPOSE 8080

# Healthcheck pour vérifier que le serveur Nginx répond
HEALTHCHECK --interval=300s --timeout=10s --start-period=5s --retries=3 \
    CMD ["wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/"]

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

# Copier une configuration Nginx personnalisée (optionnel, pour SPA)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Script d'initialisation qui génère les fichiers de config au démarrage
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Nginx tourne sous l'utilisateur `nginx` (non root) : le PID va dans /tmp et
# l'entrypoint doit pouvoir écrire les fichiers de config dans le dossier servi.
RUN chmod +x /docker-entrypoint.sh \
    && sed -i 's|^pid .*|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf \
    && chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx
USER 101

# Exposer le port 8080 (port non privilégié, requis en non root)
EXPOSE 8080

# Healthcheck pour vérifier que le serveur Nginx répond
HEALTHCHECK --interval=300s --timeout=10s --start-period=5s --retries=3 \
    CMD ["wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/"]

# Lancer Nginx via le script d'entrée
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]

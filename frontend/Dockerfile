# Images épinglées par digest (index multi-arch) : le tag reste indicatif, seul
# le digest fait foi. Les correctifs de sécurité n'arrivent plus au rebuild :
# récupérer régulièrement le nouveau digest du tag (pas d'`apk upgrade`, qui
# annulerait l'épinglage). Déclarées une seule fois pour que les étapes desktop et mobile ne divergent pas.
# checkov:skip=CKV_DOCKER_7:images épinglées par digest via ARG, que checkov ne résout pas
ARG NODE_IMAGE=node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402
ARG NGINX_IMAGE=nginx:alpine@sha256:df221db836e1754089190208cee7eeda94f233197056426eda74a43ab1abeac2

# Étape de build pour la version desktop
FROM ${NODE_IMAGE} AS desktop-builder

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
FROM ${NODE_IMAGE} AS mobile-builder

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
FROM ${NGINX_IMAGE} AS desktop-production

# Utiliser l'argument de build pour les variables d'environnement
ARG DEMO_MODE=false
ARG API_BASE_URL=http://localhost:8000
ARG BASE_URL=http://localhost:3000
ARG BASE_URL_MOBILE=http://localhost:3001

# Copier les fichiers statiques générés depuis l'étape de build desktop
COPY --from=desktop-builder /app/dist /usr/share/nginx/html

# Copier une configuration Nginx personnalisée (optionnel, pour SPA)
COPY nginx.conf /etc/nginx/conf.d/default.conf
# En-têtes de sécurité (CSP complétée par l'entrypoint avec l'origine de l'API)
COPY nginx-security-headers.conf /etc/nginx/security-headers.conf.template

# Script d'initialisation qui génère les fichiers de config au démarrage
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Nginx tourne sous l'utilisateur `nginx` (non root) : le PID va dans /tmp et
# l'entrypoint doit pouvoir écrire les fichiers de config dans le dossier servi
# et les en-têtes de sécurité dans /etc/nginx/yaka.
RUN chmod +x /docker-entrypoint.sh \
    && sed -i 's|^pid .*|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf \
    && mkdir -p /etc/nginx/yaka \
    && chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /etc/nginx/yaka
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
FROM ${NGINX_IMAGE} AS mobile-production

# Utiliser l'argument de build pour les variables d'environnement
ARG DEMO_MODE=false
ARG API_BASE_URL=http://localhost:8000
ARG BASE_URL=http://localhost:3000
ARG BASE_URL_MOBILE=http://localhost:3001

# Copier les fichiers statiques générés depuis l'étape de build mobile
COPY --from=mobile-builder /app/mobile/dist /usr/share/nginx/html

# Copier une configuration Nginx personnalisée (optionnel, pour SPA)
COPY nginx.conf /etc/nginx/conf.d/default.conf
# En-têtes de sécurité (CSP complétée par l'entrypoint avec l'origine de l'API)
COPY nginx-security-headers.conf /etc/nginx/security-headers.conf.template

# Script d'initialisation qui génère les fichiers de config au démarrage
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Nginx tourne sous l'utilisateur `nginx` (non root) : le PID va dans /tmp et
# l'entrypoint doit pouvoir écrire les fichiers de config dans le dossier servi
# et les en-têtes de sécurité dans /etc/nginx/yaka.
RUN chmod +x /docker-entrypoint.sh \
    && sed -i 's|^pid .*|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf \
    && mkdir -p /etc/nginx/yaka \
    && chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /etc/nginx/yaka
USER 101

# Exposer le port 8080 (port non privilégié, requis en non root)
EXPOSE 8080

# Healthcheck pour vérifier que le serveur Nginx répond
HEALTHCHECK --interval=300s --timeout=10s --start-period=5s --retries=3 \
    CMD ["wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/"]

# Lancer Nginx via le script d'entrée
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]

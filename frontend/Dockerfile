# Étape de build
FROM node:22-alpine AS builder

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

# Créer une version mobile dans un sous-dossier
WORKDIR /app/mobile
COPY package*.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY --from=builder /app/src ../src
COPY mobile/index.html ./
COPY mobile/vite.config.ts ./
RUN pnpm build

# Revenir au répertoire principal
WORKDIR /app

# Étape de production
FROM nginx:alpine

# Copier les fichiers statiques générés depuis l'étape de build
COPY --from=builder /app/dist /usr/share/nginx/html

# Copier les fichiers spécifiques à la version mobile
COPY --from=builder /app/mobile/dist /usr/share/nginx/html/mobile

# Copier le api-config.js généré pour mobile
COPY --from=builder /app/mobile/public/api-config.js /usr/share/nginx/html/mobile/api-config.js

# Utiliser l'argument de build pour les variables d'environnement
ARG DEMO_MODE=false
ARG API_BASE_URL=http://localhost:8000
ARG BASE_URL=http://localhost:3000
ARG BASE_URL_MOBILE=http://localhost:3001

# Définir les variables d'environnement pour qu'elles soient disponibles lors du build
ENV DEMO_MODE=${DEMO_MODE}
ENV API_BASE_URL=${API_BASE_URL}
ENV BASE_URL=${BASE_URL}
ENV BASE_URL_MOBILE=${BASE_URL_MOBILE}

# Créer un fichier de configuration avec les variables d'environnement
RUN echo "window.DEMO_MODE = '${DEMO_MODE}';" > /usr/share/nginx/html/demo-config.js

# Créer le fichier api-config.js pour la version desktop
RUN echo "window.API_BASE_URL = '${API_BASE_URL}';" > /usr/share/nginx/html/api-config.js
RUN echo "window.BASE_URL = '${BASE_URL}';" >> /usr/share/nginx/html/api-config.js
RUN echo "window.BASE_URL_MOBILE = '${BASE_URL_MOBILE}';" >> /usr/share/nginx/html/api-config.js

# Créer le fichier api-config.js pour la version mobile
RUN echo "window.API_BASE_URL = '${API_BASE_URL}';" > /usr/share/nginx/html/mobile/api-config.js
RUN echo "window.BASE_URL = '${BASE_URL}';" >> /usr/share/nginx/html/mobile/api-config.js
RUN echo "window.BASE_URL_MOBILE = '${BASE_URL_MOBILE}';" >> /usr/share/nginx/html/mobile/api-config.js

# Copier une configuration Nginx personnalisée (optionnel, pour SPA)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exposer le port 80 (standard pour Nginx)
EXPOSE 80

# Healthcheck pour vérifier que le serveur Nginx répond
HEALTHCHECK --interval=300s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Lancer Nginx
CMD ["nginx", "-g", "daemon off;"]
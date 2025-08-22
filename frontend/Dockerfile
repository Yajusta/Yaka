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

# Construire l'application (génère le dossier dist)
RUN pnpm build

# Étape de production
FROM nginx:alpine

# Copier les fichiers statiques générés depuis l'étape de build
COPY --from=builder /app/dist /usr/share/nginx/html

# Utiliser l'argument de build pour les variables d'environnement
ARG DEMO_MODE=false
ARG API_BASE_URL=http://localhost:8000

# Définir les variables d'environnement pour qu'elles soient disponibles lors du build
ENV DEMO_MODE=${DEMO_MODE}
ENV API_BASE_URL=${API_BASE_URL}

# Créer un fichier de configuration avec les variables d'environnement
RUN echo "window.DEMO_MODE = '${DEMO_MODE}';" > /usr/share/nginx/html/demo-config.js
RUN echo "window.API_BASE_URL = '${API_BASE_URL}';" > /usr/share/nginx/html/api-config.js

# Copier une configuration Nginx personnalisée (optionnel, pour SPA)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exposer le port 80 (standard pour Nginx)
EXPOSE 80

# Healthcheck pour vérifier que le serveur Nginx répond
HEALTHCHECK --interval=300s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Lancer Nginx
CMD ["nginx", "-g", "daemon off;"]
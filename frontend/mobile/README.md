# Yaka Mobile - PWA

Application mobile PWA pour Yaka (Yet Another Kanban App).

## 🚀 Démarrage rapide

### Installation des dépendances

```bash
pnpm install
```

### Développement

```bash
pnpm dev
```

L'application sera accessible sur `http://localhost:5173`

### Build pour production

```bash
pnpm build
```

### Preview du build

```bash
pnpm preview
```

## 📱 Fonctionnalités

### Version actuelle (v1)

- ✅ Configuration de l'URL de l'API
- ✅ Authentification (email/password)
- ✅ Affichage des listes et cartes
- ✅ Affichage détaillé des cartes (titre, description, assigné, priorité, labels)
- ✅ Menu paramètres avec déconnexion
- ✅ Support PWA (installable)
- ✅ Mode sombre/clair
- ✅ Internationalisation (FR/EN)

### À venir

- 🔄 Filtres (recherche, assigné, priorité, labels)
- 🔄 Saisie vocale pour créer des cartes
- 🔄 Création/édition de cartes
- 🔄 Drag & drop des cartes
- 🔄 Notifications push
- 🔄 Mode hors ligne

## 🏗️ Architecture

### Structure des répertoires

```text
mobile/
├── public/           # Fichiers statiques (manifest, icons)
├── src/
│   ├── components/   # Composants React
│   │   ├── auth/     # Composants d'authentification
│   │   ├── board/    # Composants du board (header, cards, lists)
│   │   ├── navigation/ # Navigation (bottom nav)
│   │   └── settings/ # Menu paramètres
│   ├── screens/      # Écrans principaux
│   │   ├── BoardConfigScreen.tsx
│   │   ├── LoginScreen.tsx
│   │   └── MainScreen.tsx
│   ├── App.tsx       # Configuration routing
│   ├── main.tsx      # Point d'entrée
│   └── index.css     # Styles globaux
└── package.json
```

### Code partagé

L'application mobile réutilise le code du frontend desktop via le répertoire `../shared/` :

- **Services API** : `@shared/services/` - Tous les appels API
- **Hooks React** : `@shared/hooks/` - useAuth, useTheme, etc.
- **Types TypeScript** : `@shared/types/` - Interfaces et types
- **i18n** : `@shared/i18n/` - Traductions FR/EN
- **Utilitaires** : `@shared/lib/` - Fonctions utilitaires

## 🎨 Design

### Couleurs

L'application mobile utilise exactement les mêmes couleurs que le frontend desktop :

- **Primary** : `#667eea` (violet)
- **Background** : `#fafbfc` (light) / `#0f172a` (dark)
- **Success** : `#22c55e` (vert)
- **Warning** : `#f59e0b` (orange)
- **Destructive** : `#e53e3e` (rouge)

### Principes

- **Mobile-first** : Interface optimisée pour mobile
- **Touch-friendly** : Boutons min 44x44px
- **Safe areas** : Support des encoches (iPhone X+)
- **Responsive** : S'adapte à toutes les tailles d'écran
- **Performant** : Animations fluides, lazy loading

## 🔧 Configuration

### Variables d'environnement

Aucune variable d'environnement n'est nécessaire. L'URL de l'API est configurée directement dans l'application via l'écran de configuration.

### PWA

La configuration PWA est dans `vite.config.ts` avec le plugin `vite-plugin-pwa`.

Le manifest PWA est dans `public/manifest.json`.

### Icons PWA

Les icônes doivent être placées dans `public/icons/` :

- icon-72x72.png
- icon-96x96.png
- icon-128x128.png
- icon-144x144.png
- icon-152x152.png
- icon-192x192.png
- icon-384x384.png
- icon-512x512.png

## 📦 Déploiement

### Build

```bash
pnpm build
```

Les fichiers de production seront dans le répertoire `dist/`.

### Serveur web

L'application peut être servie par n'importe quel serveur web statique (nginx, Apache, etc.).

Exemple de configuration nginx :

```nginx
server {
    listen 80;
    server_name mobile.yaka.example.com;
    root /var/www/yaka-mobile/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### HTTPS requis

Pour que la PWA soit installable, le site doit être servi en HTTPS (sauf sur localhost).

## 🧪 Tests

Les tests seront ajoutés dans une version future.

## 📝 Licence

Même licence que le projet principal Yaka.

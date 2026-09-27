import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// https://vitejs.dev/config/
export default defineConfig(() => {
  // Déterminer le base à partir d'une variable d'environnement
  const base = process.env.VITE_BASE_PATH || "/";

  return {
    server: {
      port: 3001, // Changez le port ici (par défaut 5173)
      strictPort: false, // Si le port est occupé, essayer le suivant
    },
    plugins: [
      react(),
      tailwindcss(),
      VitePWA({
        registerType: "autoUpdate",
        includeAssets: ["yaka.svg", "robots.txt"],
        manifest: {
          scope: base,
          start_url: base,
          name: "Yaka Mobile",
          short_name: "Yaka",
          description: "Yet Another Kanban App (mobile)",
          theme_color: "#667eea",
          background_color: "#fafbfc",
          display: "standalone",
          orientation: "portrait",
          icons: [
            {
              src: "/icons/icon-192x192.png",
              sizes: "192x192",
              type: "image/png",
            },
            {
              src: "/icons/icon-512x512.png",
              sizes: "512x512",
              type: "image/png",
            },
            {
              src: "/icons/icon-512x512.png",
              sizes: "512x512",
              type: "image/png",
              purpose: "any maskable",
            },
          ],
        },
        workbox: {
          globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
          // Générés au démarrage du conteneur (docker-entrypoint.sh) : toujours
          // lus sur le réseau, jamais figés dans le précache
          globIgnores: ["**/api-config.js", "**/demo-config.js"],
          navigateFallback: `${base}index.html`,
          // Pas de cache des réponses de l'API : elles sont authentifiées et
          // survivraient à la déconnexion (l'ancien cache "api-cache" est
          // supprimé au chargement, cf. shared/services/api.tsx)
        },
      }),
    ],
    resolve: {
      alias: {
        "@shared": path.resolve(__dirname, "../shared"),
      },
    },
    base: base,
  };
});

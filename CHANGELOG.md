# Changelog

## 1.4.3 (2025-12-02)

- [FIX] Changement de format pour le LLM.

## 1.4.2 (2025-11-10)

- [FIX] Problème de focus quand on modifie un champ de la checklist.
- [CHORE] Refacto du VoiceControl.

## 1.4.1 (2025-11-01)

- [NEW] Filtre des tâches à la voix.

## 1.4.0. (2025-10-27)

- [NEW] Ajout d'une version mobile.

## 1.3.4 (2025-10-19)

- [UX] Réorganisation du menu de paramètres.
- [FIX] Problème d'accès à la base de données multiple pour le service de voix.

## 1.3.3 (2025-10-18)

- [CHANGE] Les migrations Alembic s'appliquent maintenant à toutes les bases de données du répertoire `data` au démarrage du serveur.
- [CHANGE] Meilleur gestion de la concurrence des bases.

## 1.3.2 (2025-10-15)

- [NEW] Périmètre de vue (qui peut voir quoi).
- [NEW] Gestion de dictionnaire personnel pour aider l'IA dans sa compréhension.
- [UX] Précision sur l'utilité des descriptions (listes et libellés)

## 1.3.1 (2025-10-15)

- [NEW] Gestion des bases de données multiples.
- [FIX] Enregistrement des positions de cartes.
- [CHANGE] Clean tests.
- [CHORES] Update dependencies.
- [FIX] Edition du titre.

## v1.2.3 (2025-10-09)

- [NEW] Possibilité de réduire les colonnes.
- [NEW] Affichage compact.
- [NEW] Export CSV / Excel.
- [UX] Modification de l'emplacement des paramètres dans le menu.
- [UX] Titre de la page lié au nom du tableau.
- Modifications mineures d'UX.

## v1.2.1 (2025-10-07)

- [NEW] Saisie et modification des tâches par la voix (nécessite un accès à une API de LLM OpenAI ou similaire).
- [NEW] Ajout de description pour les libellés et les listes.
- [UX] Possibilité de changer une carte de liste depuis son formulaire.
- [NEW] Utilisation de Whisper en local.

## v1.1.0 (2025-10-01)

- [NEW] Nouveaux rôles plus granulaires pour les utilisateurs.

## v1.0.0 (2025-09-19)

- [SECU] Configuration du token JWT en variable d'environnement.
- [SECU] Expiration du token JWT.
- [SECU] Cors origins.
- [FIX] Possibilité de créer des utilisateurs avec un email déjà utilisé (sur un utilisateur supprimé).
- [FIX] Nettoyage des commentaires dans la démo.
- [TESTS] Ajout de tests unitaires.

## v0.2.0 (2025-09-10)

- [NEW] Interface multilingue (français / anglais).
- [NEW] Commentaires sur les cartes.
- [NEW] Possibilité de changer le rôle d'un utilisateur existant.
- [NEW] Date d'échéance mise en avant quand elle est dépassée.

## v0.1.0 (2025-08-24)

- [NEW] Gestion de l'archivage / désarchivage.
- [NEW] Historique des actions effectuées sur les cartes.
- [FIX] Prise en compte du fuseau horaire pour les dates.

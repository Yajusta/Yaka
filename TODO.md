# TODO

## Bugs

[ ] Déplacement horizontal quand il y a un scroll.
[ ] Reconnaissance vocale Edge mobile.

## Features

[ ] Pièces jointes sur les tâches.
[ ] Définir l'utilisateur par défaut dans les variables d'environnement.
[ ] Import en masse.
[ ] Chiffrer les données.

## Frontend

[ ] Séparer la page "invite" et la page "reset-password".
[x] Revoir le menu de paramètres.

## Mobile

[ ] Reorder des cartes.
[ ] Gestion d'un cache en cas de hors connexion.
[ ] Faire un APK.

## Backend

[x] Rate limiting sur l'authentification.
[x] Tokens d'invitation/réinitialisation sans expiration
[ ] Endpoints `/admin` : ne plus renvoyer les chemins de fichiers (`database_path` en création et en liste, `original_path`/`archived_path` en suppression), comme déjà fait pour `GET /admin/boards/{uid}`.
[ ] `invited_at` stocké en datetime naïf : fixer le fuseau (UTC) pour le calcul des TTL.
[ ] TTL du jeton en attente choisi selon le statut de l'utilisateur (INVITED → 7 j) plutôt que selon le type de jeton (invitation / réinitialisation).
[ ] `delete_list` : les cartes déplacées vers la liste de destination gardent leur `position` d'origine (non recalculée, doublons possibles).
[ ] Limitation de débit en mémoire : stockage partagé (Redis) si plusieurs workers ou réplicas.
[ ] Sortir `pytest`, `pytest-asyncio` et `datamodel-code-generator` des dépendances runtime (groupe dev).

## Docker

[ ] Dependabot/Renovate pour rafraîchir les digests des images de base.
[ ] `demo-cron` : sortie de `wget` jetée (`>/dev/null 2>&1`), aucun log en cas d'échec de `/demo/reset`.

### Tech

[ ] Synchro par websocket.
[ ] Faire une application smartphone.

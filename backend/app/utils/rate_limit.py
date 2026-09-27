"""Limitation de débit (slowapi) des routes d'authentification et du pilotage vocal.

Pilotage vocal : quota par utilisateur authentifié (board + id), compté
comme les tentatives par compte ci-dessous.

Authentification, deux niveaux :

- par IP (décorateur ``limiter.limit``) sur la connexion, la demande de
  réinitialisation et le changement de mot de passe. La clé est
  ``request.client.host`` : derrière un reverse proxy, c'est uvicorn qui la
  réécrit depuis ``X-Forwarded-For``, et seulement pour les proxys listés dans
  ``FORWARDED_ALLOW_IPS`` (127.0.0.1 par défaut).
  L'en-tête n'est jamais lu ici : un client ne peut pas choisir son IP.
  La clé ne dépend pas du board : un routeur monté deux fois (``/auth`` et
  ``/board/{uid}/auth``) partage le même compteur.
- par compte : tentatives de connexion comptées par board + email normalisé,
  tentatives de changement de mot de passe par board + id utilisateur
  (incrément atomique avant bcrypt, pour que des requêtes parallèles ne
  passent pas toutes le contrôle), compteur remis à zéro après un succès.

Fenêtre glissante (``moving-window``) : pas de rafale doublée à la frontière
d'une fenêtre fixe. Stockage en mémoire du processus : un seul worker uvicorn,
compteurs remis à zéro au redémarrage. ``RATELIMIT_ENABLED=false`` désactive
tout (tests).
"""

import os

from fastapi import HTTPException, status
from limits import RateLimitItem, parse_many
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..multi_database import get_effective_board_uid

RATE_LIMIT_MESSAGE = "Trop de tentatives, réessayez plus tard"

# Portées des compteurs par compte
LOGIN_SCOPE = "login"
CHANGE_PASSWORD_SCOPE = "change-password"
VOICE_CONTROL_SCOPE = "voice-control"


def _limit_from_env(name: str, default: str) -> str:
    """Lire une limite (syntaxe `limits` : "10/minute", "5 per 15 minutes",
    plusieurs limites séparées par ";"...).

    Valeur vide = défaut. Une valeur invalide fait échouer le démarrage : slowapi
    se contenterait sinon de journaliser l'erreur et de ne rien limiter.
    """
    value = os.getenv(name) or default
    try:
        parse_many(value)
    except ValueError as exc:
        raise ValueError(f"{name} invalide : {value!r}") from exc
    return value


LOGIN_RATE_LIMIT = _limit_from_env("LOGIN_RATE_LIMIT", "10/minute")
PASSWORD_RESET_RATE_LIMIT = _limit_from_env("PASSWORD_RESET_RATE_LIMIT", "5/minute")
# Toutes les limites de la valeur s'appliquent (comme pour slowapi)
ACCOUNT_RATE_LIMITS: list[RateLimitItem] = parse_many(
    _limit_from_env("LOGIN_ACCOUNT_RATE_LIMIT", "5 per 15 minutes")
)
VOICE_CONTROL_RATE_LIMITS: list[RateLimitItem] = parse_many(
    _limit_from_env("VOICE_CONTROL_RATE_LIMIT", "20/minute")
)

# key_style="endpoint" : compteur par fonction, pas par chemin (sinon chaque
# préfixe /board/{uid} aurait le sien)
limiter = Limiter(
    key_func=get_remote_address, key_style="endpoint", strategy="moving-window"
)


def _account_key(scope: str, subject: str) -> tuple[str, str, str]:
    return (scope, get_effective_board_uid(), subject)


def consume_account_attempt(
    scope: str, subject: str, limits: list[RateLimitItem] | None = None
) -> None:
    """Compter une tentative pour un compte ; 429 si son quota est épuisé.

    `subject` : email normalisé (connexion) ou id utilisateur.
    `limits` : ``ACCOUNT_RATE_LIMITS`` par défaut.
    """
    if not limiter.enabled:
        return
    key = _account_key(scope, subject)
    items = ACCOUNT_RATE_LIMITS if limits is None else limits
    # Liste (pas de court-circuit) : chaque limite compte la tentative
    allowed = [limiter.limiter.hit(item, *key) for item in items]
    if not all(allowed):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=RATE_LIMIT_MESSAGE
        )


def reset_account_attempts(scope: str, subject: str) -> None:
    if limiter.enabled:
        key = _account_key(scope, subject)
        for item in ACCOUNT_RATE_LIMITS:
            limiter.limiter.clear(item, *key)

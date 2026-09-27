"""Configuration HTTP dérivée de l'environnement (CORS, documentation de l'API).

Module sans effet de bord : il peut être importé (et testé) sans charger
`app.main`, qui migre les bases au moment de l'import.
"""

import os

DEFAULT_FRONTEND_URL = "http://localhost:5173"


def get_environment() -> str:
    """Environnement d'exécution normalisé (`production` par défaut)."""
    return os.getenv("ENVIRONMENT", "production").strip().strip("\"'").lower()


def is_development() -> bool:
    """Vrai uniquement pour ENVIRONMENT=development.

    Les assouplissements (documentation de l'API, origines localhost, en-têtes
    de production absents) ne s'appliquent qu'à cette valeur explicite : toute
    autre valeur (faute de frappe, `prod`, `staging`...) est traitée comme la
    production.
    """
    return get_environment() == "development"


def get_frontend_url() -> str:
    """URL publique du frontend desktop (BASE_URL)."""
    return os.getenv("BASE_URL", DEFAULT_FRONTEND_URL).strip()


def docs_urls() -> dict[str, str | None]:
    """Désactive /docs, /redoc et /openapi.json hors développement."""
    if is_development():
        return {}
    return {"docs_url": None, "redoc_url": None, "openapi_url": None}


def build_allowed_origins() -> list[str]:
    """Origines CORS autorisées, sans entrée vide ni doublon."""
    development = is_development()
    # Origines des applications mobiles (PWA → APK) ; http://localhost
    # seulement en développement
    default_mobile_origins = "capacitor://localhost,ionic://localhost"
    if development:
        default_mobile_origins += ",http://localhost"
    candidates = [
        get_frontend_url(),
        os.getenv("BASE_URL_MOBILE", "http://localhost:5174"),
        *os.getenv("ALLOWED_ORIGINS", "").split(","),
        # Vide (ou blanche) ou absente : valeur par défaut, comme les autres
        # variables (docker-compose la transmet toujours, vide par défaut)
        *(os.getenv("MOBILE_ORIGINS", "").strip() or default_mobile_origins).split(","),
    ]
    # file:// pour le développement mobile (uniquement en développement)
    if development:
        candidates.append("file://")
    stripped = (origin.strip() for origin in candidates)
    return list(dict.fromkeys(origin for origin in stripped if origin))

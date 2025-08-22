"""Utilitaires pour le mode démo."""

import os


def is_demo_mode() -> bool:
    """Vérifie si le mode démo est activé."""
    return os.getenv('DEMO_MODE', 'false').lower() == 'true'


def get_demo_reset_interval() -> int:
    """Récupère l'intervalle de réinitialisation en minutes (par défaut 60 minutes)."""
    try:
        return int(os.getenv('DEMO_RESET_INTERVAL_MINUTES', '60'))
    except ValueError:
        return 60
from datetime import datetime


def get_system_timezone_datetime():
    """Retourne la date et heure actuelle dans le fuseau horaire du système."""
    return datetime.now().astimezone()

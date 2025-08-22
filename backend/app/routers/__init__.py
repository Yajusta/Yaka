"""Routeurs de l'application Kanban."""

from .auth import router as auth_router
from .users import router as users_router
from .labels import router as labels_router
from .cards import router as cards_router
from .lists import router as lists_router
from .board_settings import router as board_settings_router
from .card_items import router as card_items_router

__all__ = [
    "auth_router",
    "users_router",
    "labels_router",
    "cards_router",
    "lists_router",
    "board_settings_router",
    "card_items_router",
]

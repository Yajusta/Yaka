"""Utility helpers for user role authorization checks."""

from fastapi import HTTPException, status

from ..models import Card, User, UserRole

_FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


def _raise_forbidden() -> None:
    """Raise a standardized 403 error."""
    raise _FORBIDDEN


def ensure_can_create_card(user: User, assignee_id: int | None) -> None:
    """Ensure the user can create a card with the requested assignee."""
    if user.role in (UserRole.ADMIN, UserRole.USER):
        return
    if user.role in (UserRole.READ_ONLY, UserRole.COMMENTS_ONLY):
        _raise_forbidden()
    if user.role is UserRole.ASSIGNED_ONLY:
        if assignee_id != user.id:
            _raise_forbidden()
        return
    _raise_forbidden()


def ensure_can_modify_card(user: User, card: Card) -> None:
    """Ensure the user can modify the given card."""
    if user.role in (UserRole.ADMIN, UserRole.USER):
        return
    if user.role in (UserRole.READ_ONLY, UserRole.COMMENTS_ONLY):
        _raise_forbidden()
    if user.role is UserRole.ASSIGNED_ONLY:
        if card.assignee_id != user.id:
            _raise_forbidden()
        return
    _raise_forbidden()


def ensure_can_comment_on_card(user: User, card: Card) -> None:
    """Ensure the user can add a comment to the given card."""
    if user.role in (UserRole.ADMIN, UserRole.USER):
        return
    if user.role is UserRole.READ_ONLY:
        _raise_forbidden()
    if user.role is UserRole.COMMENTS_ONLY:
        return
    if user.role is UserRole.ASSIGNED_ONLY:
        if card.assignee_id != user.id:
            _raise_forbidden()
        return
    _raise_forbidden()


def ensure_can_manage_comment(user: User, card: Card) -> None:
    """Ensure the user can edit or delete a comment on the given card."""
    if user.role in (UserRole.ADMIN, UserRole.USER):
        return
    if user.role in (UserRole.READ_ONLY, UserRole.COMMENTS_ONLY):
        _raise_forbidden()
    if user.role is UserRole.ASSIGNED_ONLY:
        if card.assignee_id != user.id:
            _raise_forbidden()
        return
    _raise_forbidden()

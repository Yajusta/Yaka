"""Utility helpers for user role authorization checks.

Role hierarchy:
- VISITOR: Read-only access
- COMMENTER: VISITOR + add/edit own comments
- CONTRIBUTOR: COMMENTER + self-assign + checklist items + move own tasks
- EDITOR: CONTRIBUTOR + create task + fully modify own tasks
- SUPERVISOR: EDITOR + create task for others + modify all tasks + move all tasks
- ADMIN: SUPERVISOR + full access + manage users/settings
"""

from fastapi import HTTPException, status

from ..models import Card, CardComment, User, UserRole

_FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


def _raise_forbidden() -> None:
    """Raise a standardized 403 error."""
    raise _FORBIDDEN


# ============================================================================
# Role verification helpers
# ============================================================================


def is_admin(user: User) -> bool:
    """Check if user is admin."""
    return user.role == UserRole.ADMIN


def is_supervisor_or_above(user: User) -> bool:
    """Check if user is supervisor or admin."""
    return user.role in (UserRole.SUPERVISOR, UserRole.ADMIN)


def is_editor_or_above(user: User) -> bool:
    """Check if user is editor, supervisor or admin."""
    return user.role in (UserRole.EDITOR, UserRole.SUPERVISOR, UserRole.ADMIN)


def is_contributor_or_above(user: User) -> bool:
    """Check if user is contributor, editor, supervisor or admin."""
    return user.role in (UserRole.CONTRIBUTOR, UserRole.EDITOR, UserRole.SUPERVISOR, UserRole.ADMIN)


def is_commenter_or_above(user: User) -> bool:
    """Check if user can comment (all roles except VISITOR)."""
    return user.role in (
        UserRole.COMMENTER,
        UserRole.CONTRIBUTOR,
        UserRole.EDITOR,
        UserRole.SUPERVISOR,
        UserRole.ADMIN,
    )


# ============================================================================
# Card permissions
# ============================================================================


def ensure_can_create_card(user: User, assignee_id: int | None) -> None:
    """Ensure user can create a card.

    - ADMIN, SUPERVISOR: can create any card
    - EDITOR: can create a card (must be the assignee)
    - CONTRIBUTOR and below: forbidden
    """
    # ADMIN and SUPERVISOR can create any card
    if is_supervisor_or_above(user):
        return

    # EDITOR can create a card but must be the assignee
    if user.role == UserRole.EDITOR:
        if assignee_id is None or assignee_id == user.id:
            return
        # If EDITOR tries to assign to someone else
        _raise_forbidden()

    # All other roles cannot create cards
    _raise_forbidden()


def ensure_can_modify_card(user: User, card: Card) -> None:
    """Ensure user can modify a card.

    - ADMIN: can fully modify all cards
    - SUPERVISOR: can fully modify all cards
    - EDITOR: can fully modify own assigned cards
    - CONTRIBUTOR: can modify limited aspects of own assigned cards (checklist items and position)
    - COMMENTER and below: forbidden
    """
    # ADMIN and SUPERVISOR can fully modify all cards
    if is_supervisor_or_above(user):
        return

    # EDITOR can fully modify own assigned cards
    if user.role == UserRole.EDITOR:
        if card.assignee_id == user.id:
            return
        _raise_forbidden()

    # CONTRIBUTOR can modify certain aspects of own assigned cards
    # (checklist items and position)
    if user.role == UserRole.CONTRIBUTOR:
        if card.assignee_id == user.id:
            return
        _raise_forbidden()

    # All other roles cannot modify
    _raise_forbidden()


def ensure_can_modify_card_metadata(user: User, card: Card) -> None:
    """Ensure user can modify card metadata.

    Metadata = due date, priority, assignee, labels

    - ADMIN: can modify all metadata on all cards
    - SUPERVISOR: can modify all metadata on all cards
    - EDITOR: can modify all metadata on own assigned cards
    - CONTRIBUTOR and below: forbidden
    """
    # ADMIN and SUPERVISOR can modify metadata on all cards
    if is_supervisor_or_above(user):
        return

    # EDITOR can modify metadata on own assigned cards
    if user.role == UserRole.EDITOR:
        if card.assignee_id == user.id:
            return
        _raise_forbidden()

    # All other roles cannot modify metadata
    _raise_forbidden()


def ensure_can_modify_card_content(user: User, card: Card) -> None:
    """Ensure user can modify card content.

    Content = title, description

    - ADMIN: can modify content on all cards
    - SUPERVISOR: can modify content on all cards
    - EDITOR: can modify content on own assigned cards
    - All others: forbidden
    """
    # ADMIN and SUPERVISOR can modify content on all cards
    if is_supervisor_or_above(user):
        return

    # EDITOR can modify content on own assigned cards
    if user.role == UserRole.EDITOR:
        if card.assignee_id == user.id:
            return
        _raise_forbidden()

    # All other roles cannot modify content
    _raise_forbidden()


def ensure_can_move_card(user: User, card: Card) -> None:
    """Ensure user can move a card.

    - ADMIN: can move all cards
    - SUPERVISOR: can move all cards (workflow control)
    - EDITOR: can move own assigned cards
    - CONTRIBUTOR: can move own assigned cards
    - COMMENTER and below: forbidden
    """
    # ADMIN and SUPERVISOR can move all cards
    if is_supervisor_or_above(user):
        return

    # EDITOR and CONTRIBUTOR can move own assigned cards
    if is_contributor_or_above(user):
        if card.assignee_id == user.id:
            return
        _raise_forbidden()

    # All other roles cannot move
    _raise_forbidden()


def ensure_can_delete_card(user: User, card: Card) -> None:
    """Ensure user can delete a card.

    - ADMIN or SUPERVISOR: can delete all cards
    - All others: forbidden
    """
    if is_supervisor_or_above(user):
        return
    _raise_forbidden()


def ensure_can_archive_card(user: User, card: Card) -> None:
    """Ensure user can archive a card.

    - ADMIN or SUPERVISOR: can archive all cards
    - All others: forbidden
    """
    if is_supervisor_or_above(user):
        return
    _raise_forbidden()


def ensure_can_assign_card(user: User, card: Card) -> None:
    """Ensure user can self-assign a card.

    - ADMIN: can assign anyone
    - SUPERVISOR: can assign anyone
    - EDITOR: can manage assignments on own cards, self-assign on others
    - CONTRIBUTOR: can self-assign only
    - COMMENTER and below: forbidden
    """
    # ADMIN and SUPERVISOR can assign anyone
    if is_supervisor_or_above(user):
        return

    # EDITOR can manage assignments on own cards
    if user.role == UserRole.EDITOR:
        if card.assignee_id == user.id:
            return
        # Can self-assign on other cards
        _raise_forbidden()

    # CONTRIBUTOR can self-assign
    if user.role == UserRole.CONTRIBUTOR:
        return  # Self-assignment verification is done at service level

    _raise_forbidden()


# ============================================================================
# Comment permissions
# ============================================================================


def ensure_can_comment_on_card(user: User, card: Card) -> None:
    """Ensure user can add a comment.

    - ADMIN, SUPERVISOR, EDITOR: can comment anywhere
    - CONTRIBUTOR: can comment anywhere
    - COMMENTER: can comment anywhere
    - VISITOR: forbidden
    """
    if is_commenter_or_above(user):
        return
    _raise_forbidden()


def ensure_can_edit_comment(user: User, comment: CardComment) -> None:
    """Ensure user can edit a comment.

    - ADMIN: can edit all comments
    - Comment owner: can edit own comment (if COMMENTER+)
    - All others: forbidden
    """
    # ADMIN can edit all comments
    if is_admin(user):
        return

    # User can edit own comment if they have at least COMMENTER role
    if is_commenter_or_above(user) and comment.user_id == user.id:
        return

    _raise_forbidden()


def ensure_can_delete_comment(user: User, comment: CardComment) -> None:
    """Ensure user can delete a comment.

    - ADMIN: can delete all comments
    - Comment owner: can delete own comment (if COMMENTER+)
    - All others: forbidden
    """
    # ADMIN can delete all comments
    if is_admin(user):
        return

    # User can delete own comment if they have at least COMMENTER role
    if is_commenter_or_above(user) and comment.user_id == user.id:
        return

    _raise_forbidden()


# ============================================================================
# Checklist item permissions
# ============================================================================


def ensure_can_create_card_item(user: User, card: Card) -> None:
    """Ensure user can create a checklist item.

    - ADMIN: can create items on all cards
    - SUPERVISOR: can create items on all cards
    - EDITOR: can create items on own assigned cards
    - CONTRIBUTOR and below: forbidden
    """
    # ADMIN and SUPERVISOR can create items anywhere
    if is_supervisor_or_above(user):
        return

    # EDITOR can create items on own assigned cards
    if user.role == UserRole.EDITOR:
        if card.assignee_id == user.id:
            return
        _raise_forbidden()

    _raise_forbidden()


def ensure_can_toggle_card_item(user: User, card: Card) -> None:
    """Ensure user can check/uncheck a checklist item.

    - ADMIN: can toggle everything
    - SUPERVISOR: can toggle everything
    - EDITOR: can toggle on own assigned cards
    - CONTRIBUTOR: can toggle on own assigned cards
    - COMMENTER and below: forbidden
    """
    # ADMIN and SUPERVISOR can toggle everything
    if is_supervisor_or_above(user):
        return

    # EDITOR and CONTRIBUTOR can toggle on own assigned cards
    if is_contributor_or_above(user):
        if card.assignee_id == user.id:
            return
        _raise_forbidden()

    _raise_forbidden()


def ensure_can_modify_card_item(user: User, card: Card) -> None:
    """Ensure user can modify a checklist item.

    - ADMIN: can modify all items
    - SUPERVISOR: can modify all items
    - EDITOR: can modify items on own assigned cards
    - CONTRIBUTOR and below: forbidden
    """
    # ADMIN and SUPERVISOR can modify all items
    if is_supervisor_or_above(user):
        return

    # EDITOR can modify items on own assigned cards
    if user.role == UserRole.EDITOR:
        if card.assignee_id == user.id:
            return
        _raise_forbidden()

    _raise_forbidden()


def ensure_can_delete_card_item(user: User, card: Card) -> None:
    """Ensure user can delete a checklist item.

    - ADMIN: can delete all items
    - SUPERVISOR: can delete all items
    - EDITOR: can delete items on own assigned cards
    - CONTRIBUTOR and below: forbidden
    """
    # ADMIN and SUPERVISOR can delete all items
    if is_supervisor_or_above(user):
        return

    # EDITOR can delete items on own assigned cards
    if user.role == UserRole.EDITOR:
        if card.assignee_id == user.id:
            return
        _raise_forbidden()

    _raise_forbidden()


# ============================================================================
# List permissions
# ============================================================================


def ensure_can_manage_lists(user: User) -> None:
    """Ensure user can manage lists.

    - ADMIN: can manage lists
    - All others: forbidden
    """
    if is_admin(user):
        return
    _raise_forbidden()


# ============================================================================
# Label permissions
# ============================================================================


def ensure_can_manage_labels(user: User) -> None:
    """Ensure user can manage labels.

    - ADMIN: can manage labels
    - All others: forbidden
    """
    if is_admin(user):
        return
    _raise_forbidden()


# ============================================================================
# User and settings permissions
# ============================================================================


def ensure_can_manage_users(user: User) -> None:
    """Ensure user can manage users.

    - ADMIN: can manage users
    - All others: forbidden
    """
    if is_admin(user):
        return
    _raise_forbidden()


def ensure_can_manage_board_settings(user: User) -> None:
    """Ensure user can manage board settings.

    - ADMIN: can manage settings
    - All others: forbidden
    """
    if is_admin(user):
        return
    _raise_forbidden()

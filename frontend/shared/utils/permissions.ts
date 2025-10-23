/**
 * Frontend permission management utilities
 * 
 * Role hierarchy:
 * - VISITOR: Read-only access
 * - COMMENTER: VISITOR + add/edit own comments
 * - CONTRIBUTOR: COMMENTER + self-assign + checklist items + move own tasks
 * - EDITOR: CONTRIBUTOR + create task + fully modify own tasks
 * - SUPERVISOR: EDITOR + create task for others + modify all tasks + move all tasks
 * - ADMIN: SUPERVISOR + full access + manage users/settings
 */

import { Card, UserRole, UserRoleValue, CardComment } from '@shared/types';

// ============================================================================
// Role verification helpers
// ============================================================================

export const isAdmin = (role?: UserRoleValue): boolean => {
    return role === UserRole.ADMIN;
};

export const isSupervisorOrAbove = (role?: UserRoleValue): boolean => {
    return role === UserRole.SUPERVISOR || role === UserRole.ADMIN;
};

export const isEditorOrAbove = (role?: UserRoleValue): boolean => {
    return role === UserRole.EDITOR || isSupervisorOrAbove(role);
};

export const isContributorOrAbove = (role?: UserRoleValue): boolean => {
    return role === UserRole.CONTRIBUTOR || isEditorOrAbove(role);
};

export const isCommenterOrAbove = (role?: UserRoleValue): boolean => {
    return role === UserRole.COMMENTER || isContributorOrAbove(role);
};

// ============================================================================
// Card permissions
// ============================================================================

export const canCreateCard = (role?: UserRoleValue): boolean => {
    return isEditorOrAbove(role);
};

export const canModifyCard = (role?: UserRoleValue, card?: Card, userId?: number): boolean => {
    if (!role || !card) return false;

    // ADMIN can modify everything
    if (isAdmin(role)) return true;

    // SUPERVISOR can modify all cards
    if (role === UserRole.SUPERVISOR) return true;

    // EDITOR can modify own assigned cards
    if (role === UserRole.EDITOR) {
        return card.assignee_id === userId;
    }

    // CONTRIBUTOR can modify (limited) own assigned cards
    if (role === UserRole.CONTRIBUTOR) {
        return card.assignee_id === userId;
    }

    return false;
};

export const canModifyCardMetadata = (role?: UserRoleValue, card?: Card, userId?: number): boolean => {
    if (!role || !card) return false;

    // ADMIN and SUPERVISOR can modify metadata on all cards
    if (isSupervisorOrAbove(role)) return true;

    // EDITOR can modify metadata on own assigned cards
    if (role === UserRole.EDITOR) {
        return card.assignee_id === userId;
    }

    return false;
};

export const canModifyCardContent = (role?: UserRoleValue, card?: Card, userId?: number): boolean => {
    if (!role || !card) return false;

    // ADMIN and SUPERVISOR can modify content on all cards
    if (isSupervisorOrAbove(role)) return true;

    // EDITOR can modify content on own assigned cards
    if (role === UserRole.EDITOR) {
        return card.assignee_id === userId;
    }

    return false;
};

export const canMoveCard = (role?: UserRoleValue, card?: Card, userId?: number): boolean => {
    if (!role || !card) return false;

    // ADMIN and SUPERVISOR can move all cards
    if (isSupervisorOrAbove(role)) return true;

    // EDITOR and CONTRIBUTOR can move own assigned cards
    if (isContributorOrAbove(role)) {
        return card.assignee_id === userId;
    }

    return false;
};

export const canDeleteCard = (role?: UserRoleValue): boolean => {
    return isAdmin(role);
};

export const canArchiveCard = (role?: UserRoleValue): boolean => {
    return isAdmin(role);
};

export const canAssignCard = (role?: UserRoleValue, card?: Card, userId?: number): boolean => {
    if (!role) return false;

    // ADMIN and SUPERVISOR can assign anyone
    if (isSupervisorOrAbove(role)) return true;

    // EDITOR can manage assignments on own cards
    if (role === UserRole.EDITOR && card) {
        return card.assignee_id === userId;
    }

    // CONTRIBUTOR can self-assign
    if (role === UserRole.CONTRIBUTOR) return true;

    return false;
};

// ============================================================================
// Comment permissions
// ============================================================================

export const canCommentOnCard = (role?: UserRoleValue): boolean => {
    return isCommenterOrAbove(role);
};

export const canEditComment = (role?: UserRoleValue, comment?: CardComment, userId?: number): boolean => {
    if (!role || !comment) return false;

    // ADMIN can edit all comments
    if (isAdmin(role)) return true;

    // User can edit own comment if they have at least COMMENTER role
    if (isCommenterOrAbove(role) && comment.user_id === userId) {
        return true;
    }

    return false;
};

export const canDeleteComment = (role?: UserRoleValue, comment?: CardComment, userId?: number): boolean => {
    if (!role || !comment) return false;

    // ADMIN can delete all comments
    if (isAdmin(role)) return true;

    // User can delete own comment if they have at least COMMENTER role
    if (isCommenterOrAbove(role) && comment.user_id === userId) {
        return true;
    }

    return false;
};

// ============================================================================
// Checklist item permissions
// ============================================================================

export const canCreateCardItem = (role?: UserRoleValue, card?: Card, userId?: number): boolean => {
    if (!role || !card) return false;

    // ADMIN and SUPERVISOR can create items anywhere
    if (isSupervisorOrAbove(role)) return true;

    // EDITOR can create items on own assigned cards
    if (role === UserRole.EDITOR) {
        return card.assignee_id === userId;
    }

    return false;
};

export const canToggleCardItem = (role?: UserRoleValue, card?: Card, userId?: number): boolean => {
    if (!role || !card) return false;

    // ADMIN and SUPERVISOR can toggle everything
    if (isSupervisorOrAbove(role)) return true;

    // EDITOR and CONTRIBUTOR can toggle on own assigned cards
    if (isContributorOrAbove(role)) {
        return card.assignee_id === userId;
    }

    return false;
};

export const canModifyCardItem = (role?: UserRoleValue, card?: Card, userId?: number): boolean => {
    if (!role || !card) return false;

    // ADMIN and SUPERVISOR can modify all items
    if (isSupervisorOrAbove(role)) return true;

    // EDITOR can modify items on own assigned cards
    if (role === UserRole.EDITOR) {
        return card.assignee_id === userId;
    }

    return false;
};

export const canDeleteCardItem = (role?: UserRoleValue, card?: Card, userId?: number): boolean => {
    return canModifyCardItem(role, card, userId);
};

// ============================================================================
// List permissions
// ============================================================================

export const canManageLists = (role?: UserRoleValue): boolean => {
    return isAdmin(role);
};

// ============================================================================
// Label permissions
// ============================================================================

export const canManageLabels = (role?: UserRoleValue): boolean => {
    return isAdmin(role);
};

// ============================================================================
// User and settings permissions
// ============================================================================

export const canManageUsers = (role?: UserRoleValue): boolean => {
    return isAdmin(role);
};

export const canManageBoardSettings = (role?: UserRoleValue): boolean => {
    return isAdmin(role);
};

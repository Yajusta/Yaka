/**
 * Custom hook to manage user permissions in the frontend
 */

import { useMemo } from 'react';
import { Card, CardComment, User, UserRoleValue } from '../types';
import * as permissions from '../utils/permissions';

export const usePermissions = (user?: User | null) => {
    const userRole = user?.role as UserRoleValue | undefined;
    const userId = user?.id;

    return useMemo(() => ({
        // Role and ID
        role: userRole,
        userId,

        // Role helpers
        isAdmin: permissions.isAdmin(userRole),
        isSupervisorOrAbove: permissions.isSupervisorOrAbove(userRole),
        isEditorOrAbove: permissions.isEditorOrAbove(userRole),
        isContributorOrAbove: permissions.isContributorOrAbove(userRole),
        isCommenterOrAbove: permissions.isCommenterOrAbove(userRole),

        // Card permissions
        canCreateCard: permissions.canCreateCard(userRole),
        canModifyCard: (card?: Card) => permissions.canModifyCard(userRole, card, userId),
        canModifyCardMetadata: (card?: Card) => permissions.canModifyCardMetadata(userRole, card, userId),
        canModifyCardContent: (card?: Card) => permissions.canModifyCardContent(userRole, card, userId),
        canMoveCard: (card?: Card) => permissions.canMoveCard(userRole, card, userId),
        canDeleteCard: permissions.canDeleteCard(userRole),
        canArchiveCard: permissions.canArchiveCard(userRole),
        canAssignCard: (card?: Card) => permissions.canAssignCard(userRole, card, userId),

        // Comment permissions
        canCommentOnCard: permissions.canCommentOnCard(userRole),
        canEditComment: (comment?: CardComment) => permissions.canEditComment(userRole, comment, userId),
        canDeleteComment: (comment?: CardComment) => permissions.canDeleteComment(userRole, comment, userId),

        // Checklist item permissions
        canCreateCardItem: (card?: Card) => permissions.canCreateCardItem(userRole, card, userId),
        canToggleCardItem: (card?: Card) => permissions.canToggleCardItem(userRole, card, userId),
        canModifyCardItem: (card?: Card) => permissions.canModifyCardItem(userRole, card, userId),
        canDeleteCardItem: (card?: Card) => permissions.canDeleteCardItem(userRole, card, userId),

        // List permissions
        canManageLists: permissions.canManageLists(userRole),

        // Label permissions
        canManageLabels: permissions.canManageLabels(userRole),

        // User and settings permissions
        canManageUsers: permissions.canManageUsers(userRole),
        canManageBoardSettings: permissions.canManageBoardSettings(userRole),
    }), [userRole, userId]);
};
import { User as UserIcon, Shield, Key, PenTool, Users, MessageSquare, Eye } from 'lucide-react';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useToast } from '@shared/hooks/use-toast';
import { useUsers } from '@shared/hooks/useUsers';
import { cardService } from '@shared/services/api';
import { Card, UpdateCardData, UserRole } from '@shared/types';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';

interface AssigneeChangerProps {
    card: Card;
    onAssigneeChange: (updatedCard: Card) => void;
    isCurrentUserAssigned?: boolean;
    disabled?: boolean;
}

export const AssigneeChanger: React.FC<AssigneeChangerProps> = ({ card, onAssigneeChange, isCurrentUserAssigned = false, disabled = false }) => {
    const { t } = useTranslation();
    const { toast } = useToast();
    const { users } = useUsers();

    const getRoleIcon = (role?: string) => {
        switch (role) {
            case UserRole.ADMIN:
                return Key;
            case UserRole.SUPERVISOR:
                return Shield;
            case UserRole.EDITOR:
                return PenTool;
            case UserRole.CONTRIBUTOR:
                return Users;
            case UserRole.COMMENTER:
                return MessageSquare;
            case UserRole.VISITOR:
                return Eye;
            default:
                return UserIcon;
        }
    };

    const handleAssigneeChange = async (newAssigneeId: number | null) => {
        if (disabled) {
            return;
        }
        if (newAssigneeId === card.assignee_id) {
            return;
        }

        const updatePayload: UpdateCardData = {
            assignee_id: newAssigneeId,
        };

        try {
            const updatedCard = await cardService.updateCard(card.id, updatePayload);
            onAssigneeChange(updatedCard);
            toast({
                title: newAssigneeId
                    ? t('card.cardAssignedTo', { cardTitle: card.title, userName: users.find(u => u.id === newAssigneeId)?.display_name || t('user.unknownUser') })
                    : t('card.cardUnassignedTo', { cardTitle: card.title }),
                variant: "success",
            });
        } catch (error) {
            console.error("Failed to update assignee", error);
            toast({
                title: t('common.error'),
                description: t('card.updateAssigneeError'),
                variant: "destructive",
            });
        }
    };

    if (disabled) {
        return (
            <div className="flex items-center space-x-1 text-muted-foreground" title={t('card.changeAssignee')}>
                {card.assignee_id ? (
                    <>
                        <UserIcon className={`h-3 w-3 ${isCurrentUserAssigned ? 'text-primary-foreground' : 'text-muted-foreground'}`} />
                        <span className={`text-xs font-medium ${isCurrentUserAssigned ? 'text-primary-foreground' : 'text-muted-foreground'}`}>
                            {card.assignee_name || "-"}
                        </span>
                    </>
                ) : (
                    <div className='flex items-center text-muted-foreground'>
                        <UserIcon className="h-3 w-3" />
                    </div>
                )}
            </div>
        );
    }

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <div className="flex items-center space-x-1 cursor-pointer" title={t('card.changeAssignee')}>
                    {card.assignee_id ? (
                        <>
                            <UserIcon className={`h-3 w-3 ${isCurrentUserAssigned ? 'text-primary-foreground' : 'text-muted-foreground'}`} />
                            <span className={`text-xs font-medium ${isCurrentUserAssigned ? 'text-primary-foreground' : 'text-muted-foreground'}`}>
                                {card.assignee_name || "-"}
                            </span>
                        </>
                    ) : (
                        <div className={`flex items-center ${isCurrentUserAssigned ? 'text-primary-foreground hover:text-primary-foreground' : 'text-muted-foreground hover:text-foreground'} transition-colors`}>
                            <UserIcon className="h-3 w-3" />
                        </div>
                    )}
                </div>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
                <DropdownMenuItem onSelect={() => handleAssigneeChange(null)}>
                    {t('card.unassign')}
                </DropdownMenuItem>
                {users
                    .slice()
                    .sort((a, b) => (a.display_name || '').localeCompare(b.display_name || ''))
                    .map((user) => {
                        const RoleIcon = getRoleIcon(user.role);
                        return (
                            <DropdownMenuItem key={user.id} onSelect={() => handleAssigneeChange(user.id)} className="flex items-center gap-2">
                                <RoleIcon className="h-4 w-4 text-muted-foreground" />
                                <span>{user.display_name}</span>
                            </DropdownMenuItem>
                        );
                    })}
            </DropdownMenuContent>
        </DropdownMenu>
    );
};

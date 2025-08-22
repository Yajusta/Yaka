import React from 'react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { User as UserIcon } from 'lucide-react';
import { Card, UpdateCardData } from '../../types';
import { cardService } from '../../services/api';
import { useToast } from '../../hooks/use-toast';
import { useUsers } from '../../hooks/useUsers';

interface AssigneeChangerProps {
    card: Card;
    onAssigneeChange: (updatedCard: Card) => void;
    isCurrentUserAssigned?: boolean;
}

export const AssigneeChanger: React.FC<AssigneeChangerProps> = ({ card, onAssigneeChange, isCurrentUserAssigned = false }) => {
    const { toast } = useToast();
    const { users } = useUsers();

    const handleAssigneeChange = async (newAssigneeId: number | null) => {
        if (newAssigneeId === card.assignee_id) return;

        const updatePayload: UpdateCardData = {
            assignee_id: newAssigneeId,
        };

        try {
            const updatedCard = await cardService.updateCard(card.id, updatePayload);
            onAssigneeChange(updatedCard);
            toast({
                title: `La carte "${card.titre}" est maintenant assignée à ${users.find(u => u.id === newAssigneeId)?.display_name || 'personne'}.`,
                variant: "success",
            });
        } catch (error) {
            console.error("Failed to update assignee", error);
            toast({
                title: "Erreur",
                description: "Impossible de mettre à jour l'assigné de la carte.",
                variant: "destructive",
            });
        }
    };

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <div className="flex items-center space-x-1 cursor-pointer" title="Changer l'assigné">
                    {card.assignee ? (
                        <>
                            <UserIcon className={`h-3 w-3 ${isCurrentUserAssigned ? 'text-primary-foreground' : 'text-muted-foreground'}`} />
                            <span className={`text-xs font-medium ${isCurrentUserAssigned ? 'text-primary-foreground' : 'text-muted-foreground'}`}>
                                {card.assignee.display_name}
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
                    Aucun
                </DropdownMenuItem>
                {users.map((user) => (
                    <DropdownMenuItem key={user.id} onSelect={() => handleAssigneeChange(user.id)}>
                        {user.display_name}
                    </DropdownMenuItem>
                ))}
            </DropdownMenuContent>
        </DropdownMenu>
    );
};
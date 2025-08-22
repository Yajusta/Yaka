
import React from 'react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { PriorityBadge } from '../ui/PriorityBadge';
import { Card, UpdateCardData, getPriorityIcon, getPriorityLabel, getPriorityIconColor } from '../../types';
import { cardService } from '../../services/api';
import { useToast } from '../../hooks/use-toast';

interface PriorityChangerProps {
    card: Card;
    onPriorityChange: (updatedCard: Card) => void;
}

const priorities: ('low' | 'medium' | 'high')[] = ['high', 'medium', 'low'];

export const PriorityChanger: React.FC<PriorityChangerProps> = ({ card, onPriorityChange }) => {
    const { toast } = useToast();

    const handlePriorityChange = async (newPriority: 'low' | 'medium' | 'high') => {
        if (newPriority === card.priorite) return;

        const updatePayload: UpdateCardData = {
            priorite: newPriority,
        };

        try {
            const updatedCard = await cardService.updateCard(card.id, updatePayload);
            onPriorityChange(updatedCard);
            toast({
                title: "Priorité mise à jour",
                description: `La priorité de la carte "${card.titre}" est maintenant "${getPriorityLabel(newPriority)}".`,
                variant: "success",
            });
        } catch (error) {
            console.error("Failed to update priority", error);
            toast({
                title: "Erreur",
                description: "Impossible de mettre à jour la priorité de la carte.",
                variant: "destructive",
            });
        }
    };

    return (
        <DropdownMenu>
            <DropdownMenuTrigger>
                <PriorityBadge priority={card.priorite} />
            </DropdownMenuTrigger>
            <DropdownMenuContent>
                {priorities.map((p) => {
                    const Icon = getPriorityIcon(p);
                    const iconColor = getPriorityIconColor(p);
                    return (
                        <DropdownMenuItem key={p} onSelect={() => handlePriorityChange(p)} className="flex items-center gap-2">
                            <Icon className={`h-4 w-4 ${iconColor}`} />
                            <span>{getPriorityLabel(p)}</span>
                        </DropdownMenuItem>
                    );
                })}
            </DropdownMenuContent>
        </DropdownMenu>
    );
};

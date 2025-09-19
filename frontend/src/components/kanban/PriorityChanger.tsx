
import React from 'react';
import { useTranslation } from 'react-i18next';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { PriorityBadge } from '../ui/PriorityBadge';
import { Card, UpdateCardData, getPriorityIcon, getPriorityIconColor } from '../../types';
import { cardService } from '../../services/api';
import { useToast } from '../../hooks/use-toast';
import { useTranslatedLabels } from '../../hooks/useTranslatedLabels';

interface PriorityChangerProps {
    card: Card;
    onPriorityChange: (updatedCard: Card) => void;
}

const priorities: ('low' | 'medium' | 'high')[] = ['high', 'medium', 'low'];

export const PriorityChanger: React.FC<PriorityChangerProps> = ({ card, onPriorityChange }) => {
    const { t } = useTranslation();
    const { toast } = useToast();
    const { getPriorityLabel } = useTranslatedLabels();

    const handlePriorityChange = async (newPriority: 'low' | 'medium' | 'high') => {
        if (newPriority === card.priority) {
            return;
        }

        const updatePayload: UpdateCardData = {
            priority: newPriority,
        };

        try {
            const updatedCard = await cardService.updateCard(card.id, updatePayload);
            onPriorityChange(updatedCard);
            toast({
                title: t('card.priorityUpdated'),
                description: t('card.priorityUpdatedDescription', { cardTitle: card.title, priority: getPriorityLabel(newPriority) }),
                variant: "success",
            });
        } catch (error) {
            console.error("Failed to update priority", error);
            toast({
                title: t('common.error'),
                description: t('card.updatePriorityError'),
                variant: "destructive",
            });
        }
    };

    return (
        <DropdownMenu>
            <DropdownMenuTrigger>
                <PriorityBadge priority={card.priority} />
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

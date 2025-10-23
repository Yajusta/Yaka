
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useToast } from '@shared/hooks/use-toast';
import { useTranslatedLabels } from '@shared/hooks/useTranslatedLabels';
import { cardService } from '@shared/services/api';
import { Card, UpdateCardData, getPriorityIcon, getPriorityIconColor } from '@shared/types';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { PriorityBadge } from '../ui/PriorityBadge';

interface PriorityChangerProps {
    card: Card;
    onPriorityChange: (updatedCard: Card) => void;
    disabled?: boolean;
}

const priorities: ('low' | 'medium' | 'high')[] = ['high', 'medium', 'low'];

export const PriorityChanger: React.FC<PriorityChangerProps> = ({ card, onPriorityChange, disabled = false }) => {
    const { t } = useTranslation();
    const { toast } = useToast();
    const { getPriorityLabel } = useTranslatedLabels();

    const handlePriorityChange = async (newPriority: 'low' | 'medium' | 'high') => {
        if (disabled) {
            return;
        }
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

    if (disabled) {
        return <PriorityBadge priority={card.priority} interactive={false} />;
    }

    return (
        <DropdownMenu>
            <DropdownMenuTrigger>
                <PriorityBadge priority={card.priority} interactive={true} />
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

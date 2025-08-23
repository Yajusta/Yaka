import { useDraggable } from '@dnd-kit/core';
import { CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { CalendarDays, Edit, Trash2, MoreHorizontal } from 'lucide-react';
import { GlassmorphicCard } from '../ui/GlassmorphicCard';
import { PriorityChanger } from './PriorityChanger';
import { AssigneeChanger } from './AssigneeChanger';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Card } from '../../types/index';
import { useAuth } from '../../hooks/useAuth';

interface CardItemProps {
    card: Card;
    isDragging?: boolean;
    onUpdate: (card: Card, action?: 'edit' | 'update') => void;
    onDelete: (cardId: number) => void | Promise<void>;
    isActiveCard?: boolean;
    isJustDropped?: boolean;
    isHidden?: boolean;
    isInTrashZone?: boolean;
}

export const CardItem = ({
    card,
    isDragging = false,
    onUpdate,
    onDelete,
    isActiveCard = false,
    isJustDropped = false,
    isHidden = false,
    isInTrashZone = false
}: CardItemProps) => {
    const { user: currentUser } = useAuth();

    const {
        attributes,
        listeners,
        setNodeRef,
        isDragging: isDraggableActive,
    } = useDraggable({
        id: card.id,
        data: {
            type: 'card',
            card
        }
    });

    const isCurrentUserAssigned = !!(card.assignee && currentUser && card.assignee.id === currentUser.id);

    // Normalize priority to get the correct border color
    const normalizePriority = (priority: string): 'low' | 'medium' | 'high' => {
        if (!priority) {
            return 'low';
        }
        const lower = String(priority).toLowerCase();
        const normalized = lower.normalize('NFD').replace(/\p{Diacritic}/gu, '');

        if (normalized.includes('high') || normalized.includes('elev') || normalized.includes('eleve')) {
            return 'high';
        }
        if (normalized.includes('medium') || normalized.includes('moy')) {
            return 'medium';
        }
        if (normalized.includes('low') || normalized.includes('faibl') || normalized.includes('faible')) {
            return 'low';
        }

        return 'low';
    };

    const priorityKey = normalizePriority(card.priorite);

    const draggingClasses = isDragging || isDraggableActive
        ? `ring-2 ${priorityKey === 'high' ? 'ring-destructive' : priorityKey === 'medium' ? 'ring-sky-600' : 'ring-gray-400'} shadow-xl scale-[1.02] z-50`
        : '';

    const style = {
        opacity: (isHidden || isActiveCard || isJustDropped) ? 0 : 1,
        willChange: 'transform, opacity',
        transformOrigin: 'center',
        boxShadow: isInTrashZone ? '0 30px 60px rgba(229,62,62,0.25)' : undefined,
        overflow: 'visible'
    } as React.CSSProperties;

    // Prevent mobile touch gestures (scroll/zoom) from conflicting with drag.
    // Set touch-action to none so touching a card doesn't trigger page panning while attempting to drag.
    style.touchAction = 'none';

    const formatDate = (dateString: string): string | null => {
        if (!dateString) {
            return null;
        }
        return new Date(dateString).toLocaleDateString('fr-FR');
    };

    const handleEdit = (e: React.MouseEvent): void => {
        e.stopPropagation();
        onUpdate(card, 'edit');
    };

    const handleDoubleClick = (e: React.MouseEvent): void => {
        e.stopPropagation();
        onUpdate(card, 'edit');
    };

    const handlePriorityChange = (updatedCard: Card) => {
        onUpdate(updatedCard, 'update');
    };

    const handleAssigneeChange = (updatedCard: Card) => {
        onUpdate(updatedCard, 'update');
    };

    const trashClass = isInTrashZone
        ? 'z-[3000] ring-4 ring-destructive/60 shadow-[0_20px_40px_rgba(229,62,62,0.25)] scale-[1.03] bg-destructive/10 text-destructive border-destructive'
        : '';

    // Apply CSS class to force hiding
    const hiddenClass = (isHidden || isActiveCard || isJustDropped) ? 'card-being-dragged' : '';

    const priorityGlowClass = {
        'high': 'shadow-[0_0_8px_rgba(239,68,68,0.4),0_0_16px_rgba(239,68,68,0.2)] hover:shadow-[0_0_12px_rgba(239,68,68,0.6),0_0_24px_rgba(239,68,68,0.3)]',
        'medium': 'shadow-[0_0_8px_rgba(14,165,233,0.4),0_0_16px_rgba(14,165,233,0.2)] hover:shadow-[0_0_12px_rgba(14,165,233,0.6),0_0_24px_rgba(14,165,233,0.3)]',
        'low': 'shadow-[0_0_8px_rgba(156,163,175,0.4),0_0_16px_rgba(156,163,175,0.2)] hover:shadow-[0_0_12px_rgba(156,163,175,0.6),0_0_24px_rgba(156,163,175,0.3)]'
    }[priorityKey];

    const totalItems = card.items?.length || 0;
    const doneItems = card.items?.filter(i => i.is_done).length || 0;
    const progress = totalItems > 0 ? Math.round((doneItems / totalItems) * 100) : 0;

    return (
        <GlassmorphicCard
            ref={setNodeRef}
            style={style}
            {...attributes}
            {...listeners}
            onDoubleClick={handleDoubleClick}
            variant="interactive"
            className={`group cursor-grab active:cursor-grabbing border-2 ${priorityGlowClass} ${draggingClasses} ${hiddenClass} ${trashClass} ${isInTrashZone ? 'card-trash-active border-destructive' : ''}`}
        >
            <CardContent>
                <div>
                    {/* Header with title and actions */}
                    <div className="flex items-start justify-between gap-2">
                        <h3 className="font-semibold text-sm leading-tight flex-1 text-foreground">
                            {card.titre}
                        </h3>
                        <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 w-7 p-0 hover:bg-primary/10"
                                onClick={handleEdit}
                                title="Modifier la carte"
                            >
                                <Edit className="h-3.5 w-3.5" />
                            </Button>
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-7 w-7 p-0 hover:bg-muted"
                                        title="Actions"
                                    >
                                        <MoreHorizontal className="h-3.5 w-3.5" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="w-40">
                                    <DropdownMenuItem
                                        variant="destructive"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onDelete(card.id);
                                        }}
                                        className="flex items-center gap-2"
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                        Supprimer
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>
                    </div>

                    {/* Description */}
                    {card.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                            {card.description}
                        </p>
                    )}

                    {/* Labels */}
                    {card.labels && card.labels.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                            {card.labels.map(label => (
                                <Badge
                                    key={label.id}
                                    variant="outline"
                                    className="text-xs px-2 py-0.5 font-medium border-opacity-50"
                                    style={{
                                        backgroundColor: label.couleur + '15',
                                        borderColor: label.couleur + '40',
                                        color: label.couleur
                                    }}
                                >
                                    {label.nom}
                                </Badge>
                            ))}
                        </div>
                    )}

                    {/* Footer */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                        <div className="flex items-center space-x-2">
                            <PriorityChanger card={card} onPriorityChange={handlePriorityChange} />

                            {card.date_echeance && (
                                <div
                                    className="flex items-center text-muted-foreground hover:text-foreground transition-colors"
                                    title="Date d'échéance"
                                >
                                    <CalendarDays className="h-3 w-3 mr-1" />
                                    <span className="text-xs">{formatDate(card.date_echeance)}</span>
                                </div>
                            )}
                            {totalItems > 0 && (
                                <div className="flex items-center gap-2 ml-1" title="Progression de la checklist">
                                    <div className="relative h-5 w-5">
                                        <svg className="h-5 w-5 text-muted-foreground" viewBox="0 0 36 36">
                                            <path
                                                className="text-muted-foreground/20"
                                                strokeWidth="4"
                                                stroke="currentColor"
                                                fill="none"
                                                pathLength="100"
                                                d="M18 2 a 16 16 0 1 0 0 32 a 16 16 0 1 0 0 -32"
                                            />
                                            <path
                                                className="text-primary"
                                                strokeWidth="4"
                                                strokeLinecap="round"
                                                stroke="currentColor"
                                                fill="none"
                                                pathLength="100"
                                                strokeDasharray={`${progress} ${100 - progress}`}
                                                transform="scale(-1,1) translate(-36,0)"
                                                d="M18 2 a 16 16 0 1 0 0 32 a 16 16 0 1 0 0 -32"
                                            />
                                        </svg>
                                    </div>
                                    <span className="text-xs text-muted-foreground">{doneItems} / {totalItems}</span>
                                </div>
                            )}
                        </div>

                        <div className={`flex items-center ml-auto ${card.assignee ? "opacity-100" : "opacity-0 group-hover:opacity-100 transition-opacity duration-200"} ${isCurrentUserAssigned ? 'bg-primary text-primary-foreground rounded-md px-2 py-1 -mx-2 -my-1 shadow-sm' : ''}`}>
                            <AssigneeChanger card={card} onAssigneeChange={handleAssigneeChange} isCurrentUserAssigned={isCurrentUserAssigned} />
                        </div>
                    </div>
                </div>
            </CardContent>
        </GlassmorphicCard>
    );
};
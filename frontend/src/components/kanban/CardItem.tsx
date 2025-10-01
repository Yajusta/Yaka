import { useDraggable } from '@dnd-kit/core';
import { AlertCircle, AlertTriangle, CalendarDays, Clock, Edit, MessageSquare, MoreHorizontal, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuth';
import { usePermissions } from '../../hooks/usePermissions';
import { Card } from '../../types/index';
import { CommentsForm } from '../cards/CommentsForm';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { CardContent } from '../ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { GlassmorphicCard } from '../ui/GlassmorphicCard';
import { AssigneeChanger } from './AssigneeChanger';
import { CardHistoryModal } from './CardHistoryModal';
import { PriorityChanger } from './PriorityChanger';

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
    const currentUserId = currentUser?.id ?? null;
    const isCurrentUserAssigned = currentUserId !== null && (card.assignee_id === currentUserId || card.assignee?.id === currentUserId);

    // Use the permissions hook for proper role-based access control
    const permissions = usePermissions(currentUser);
    const canModifyCard = permissions.canModifyCard(card);
    const canComment = permissions.canCommentOnCard;
    const canDrag = permissions.canMoveCard(card);

    // Determine if the user can view actions (edit, delete buttons)
    const canViewActions = canModifyCard;
    const { t } = useTranslation();
    const [showHistoryModal, setShowHistoryModal] = useState(false);
    const [showCommentsModal, setShowCommentsModal] = useState(false);

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
        },
        disabled: !canDrag,
    });

    const dragProps = canDrag ? { ...attributes, ...listeners } : {};

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

    const priorityKey = normalizePriority(card.priority);

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

    const getDueDateStatus = (dateString: string): 'overdue' | 'upcoming' | 'normal' => {
        if (!dateString) {
            return 'normal';
        }

        const dueDate = new Date(dateString);
        const today = new Date();
        dueDate.setHours(0, 0, 0, 0);
        today.setHours(0, 0, 0, 0);

        const diffTime = dueDate.getTime() - today.getTime();
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays <= 0) {
            return 'overdue';
        } else if (diffDays <= 7) {
            return 'upcoming';
        }

        return 'normal';
    };

    const handleEdit = (e: React.MouseEvent): void => {
        e.stopPropagation();
        if (!canModifyCard) {
            return;
        }
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
        'high': 'priority-high',
        'medium': 'priority-medium',
        'low': 'priority-low'
    }[priorityKey];

    const totalItems = card.items?.length || 0;
    const doneItems = card.items?.filter(i => i.is_done).length || 0;
    const progress = totalItems > 0 ? Math.round((doneItems / totalItems) * 100) : 0;

    const totalComments = card.comments?.length || 0;

    return (
        <GlassmorphicCard
            ref={setNodeRef}
            style={style}
            {...dragProps}
            onDoubleClick={handleDoubleClick}
            variant={canDrag ? "interactive" : "default"}
            className={`group ${canDrag ? 'cursor-grab active:cursor-grabbing' : 'cursor-default no-drag-effect'} border-2 ${priorityGlowClass} ${draggingClasses} ${hiddenClass} ${trashClass} ${isInTrashZone ? 'card-trash-active border-destructive' : ''}`}
        >
            <CardContent>
                <div>
                    {/* Header with title and actions */}
                    <div className="flex items-start justify-between gap-2">
                        <h3 className="font-semibold text-sm leading-tight flex-1 text-foreground">
                            {card.title}
                        </h3>
                        {canViewActions && (
                            <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 w-7 p-0 hover:bg-primary/10"
                                    onClick={handleEdit}
                                    title={t('card.editCard')}
                                >
                                    <Edit className="h-3.5 w-3.5" />
                                </Button>
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-7 w-7 p-0 hover:bg-muted"
                                            title={t('common.actions')}
                                        >
                                            <MoreHorizontal className="h-3.5 w-3.5" />
                                        </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end" className="w-40">
                                        <DropdownMenuItem
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setShowHistoryModal(true);
                                            }}
                                            className="flex items-center gap-2"
                                        >
                                            <Clock className="h-3.5 w-3.5" />
                                            {t('card.history')}
                                        </DropdownMenuItem>
                                        <DropdownMenuItem
                                            variant="destructive"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onDelete(card.id);
                                            }}
                                            className="flex items-center gap-2"
                                        >
                                            <Trash2 className="h-3.5 w-3.5" />
                                            {t('card.archiveCard')}
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            </div>
                        )}
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
                                        backgroundColor: label.color + '15',
                                        borderColor: label.color + '40',
                                        color: label.color
                                    }}
                                >
                                    {label.name}
                                </Badge>
                            ))}
                        </div>
                    )}

                    {/* Footer */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                        <div className="flex items-center space-x-2">
                            <PriorityChanger card={card} onPriorityChange={handlePriorityChange} disabled={!canModifyCard} />

                            {card.due_date && (() => {
                                const dueDateStatus = getDueDateStatus(card.due_date);
                                const isOverdue = dueDateStatus === 'overdue';
                                const isUpcoming = dueDateStatus === 'upcoming';

                                const dateClasses = `flex items-center transition-colors relative ${isOverdue
                                    ? 'text-red-800 hover:text-red-900 px-2 py-1 rounded-md border-2 border-red-400 overflow-hidden'
                                    : isUpcoming
                                        ? 'text-orange-600 hover:text-orange-700 bg-orange-50/50 px-2 py-1 rounded-md border border-orange-200'
                                        : 'text-muted-foreground hover:text-foreground'
                                    }`;

                                const Icon = isOverdue ? AlertCircle : isUpcoming ? AlertTriangle : CalendarDays;

                                return (
                                    <div
                                        className={dateClasses}
                                        title={t('card.dueDate')}
                                    >
                                        {isOverdue && (
                                            <div className="absolute inset-0 bg-red-500/20 animate-pulse"></div>
                                        )}
                                        <div className="relative z-10 flex items-center">
                                            <Icon className={`h-3 w-3 mr-1 ${isOverdue ? 'text-red-800' : isUpcoming ? 'text-orange-600' : 'text-muted-foreground'}`} />
                                            <span className="text-xs font-medium">{formatDate(card.due_date)}</span>
                                        </div>
                                    </div>
                                );
                            })()}
                            {totalItems > 0 && (
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <div className="flex items-center gap-2 ml-1 cursor-pointer" title={t('card.checklistProgress')}>
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
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="start" className="w-72 p-0 bg-background border border-border" sideOffset={5}>
                                        <div className="p-3 space-y-2">
                                            <div className="text-sm font-medium text-foreground">
                                                {t('card.checklist')} ({doneItems}/{totalItems})
                                            </div>
                                            <div className="space-y-1 max-h-64 overflow-y-auto">
                                                {card.items?.map((item) => (
                                                    <div key={item.id} className="flex items-center gap-2 p-2 rounded-lg bg-muted/50 border border-border">
                                                        <div className={`w-4 h-4 rounded border-2 flex items-center justify-center ${item.is_done ? 'bg-primary border-primary' : 'border-muted-foreground'}`}>
                                                            {item.is_done && (
                                                                <svg className="w-3 h-3 text-primary-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                                                                    <path d="M5 13l4 4L19 7" />
                                                                </svg>
                                                            )}
                                                        </div>
                                                        <span className={`text-sm ${item.is_done ? 'text-muted-foreground line-through' : 'text-foreground'}`}>
                                                            {item.text}
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            )}
                            <div className={`flex items-center gap-1 cursor-pointer transition-opacity duration-200 ${totalComments > 0 ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                                }`} title={t('card.comments')} onClick={() => setShowCommentsModal(true)}>
                                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                                {totalComments > 0 && (
                                    <span className="text-xs text-muted-foreground">{totalComments}</span>
                                )}
                            </div>
                        </div>

                        <div className={`flex items-center ml-auto ${card.assignee ? "opacity-100" : "opacity-0 group-hover:opacity-100 transition-opacity duration-200"} ${isCurrentUserAssigned ? 'bg-primary text-primary-foreground rounded-md px-2 py-1 -mx-2 -my-1 shadow-sm' : ''}`}>
                            <AssigneeChanger card={card} onAssigneeChange={handleAssigneeChange} isCurrentUserAssigned={isCurrentUserAssigned} disabled={!canModifyCard} />
                        </div>
                    </div>
                </div>
            </CardContent>

            <CardHistoryModal
                isOpen={showHistoryModal}
                onClose={() => setShowHistoryModal(false)}
                cardId={card.id}
                cardTitle={card.title}
            />

            <CommentsForm
                cardId={card.id}
                isOpen={showCommentsModal}
                onClose={() => setShowCommentsModal(false)}
                canAdd={canComment}
            />
        </GlassmorphicCard>
    );
};
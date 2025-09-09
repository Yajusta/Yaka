import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useDroppable } from '@dnd-kit/core';
import { CardItem } from './CardItem';
import { GlassmorphicCard } from '../ui/GlassmorphicCard';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';
import { Card, KanbanList } from '../../types/index';
import { useElasticTransition } from '../../hooks/useElasticTransition';
import { Plus } from 'lucide-react';

interface KanbanColumnProps {
    id: string;
    list: KanbanList;
    cards: Card[];
    onCardUpdate: (card: Card, action?: 'edit' | 'update') => void;
    onCardDelete: (cardId: number) => void;
    onCreateCard?: (listId: number) => void;
    isDragging: boolean;
    dropTarget: number | null;
    activeCardId?: number | null;
    justDroppedCardId?: number | null;
    hiddenCardId?: number | null;
    activeCardSize?: { width: number; height: number } | null;
    originalPositions?: Map<string, DOMRect>;
}

export const KanbanColumn: React.FC<KanbanColumnProps> = ({
    id,
    list,
    cards,
    onCardUpdate,
    onCardDelete,
    onCreateCard,
    isDragging,
    dropTarget,
    activeCardId,
    justDroppedCardId,
    hiddenCardId,
    activeCardSize,
    originalPositions
}) => {
    const { t } = useTranslation();
    const { setNodeRef } = useDroppable({
        id: id,
    });

    // removed debug logs
    useEffect(() => {
        /* no-op for now */
    }, [dropTarget, isDragging, cards.length, id, list.id]);

    const containerRef = useElasticTransition({
        isDragging,
        dropTarget,
        cards,
        activeCardId,
        activeCardSize,
        originalPositions: originalPositions || null
    });

    // État pour éviter les animations parasites après drop
    const [justDropped, setJustDropped] = useState(false);

    // Détecter la fin du drag pour éviter les animations parasites
    useEffect(() => {
        if (!isDragging && justDroppedCardId) {
            setJustDropped(true);
            // Retirer la classe après un court délai
            const timeout = setTimeout(() => {
                setJustDropped(false);
            }, 100);
            return () => clearTimeout(timeout);
        }
    }, [isDragging, justDroppedCardId]);

    return (
        <div className="h-full flex flex-col">
            <GlassmorphicCard
                ref={setNodeRef}
                data-list-id={id}
                className={cn(
                    "h-full flex flex-col kanban-column py-0 gap-0",
                    isDragging && "kanban-column-dragging",
                    isDragging && dropTarget !== null && "placeholder-active",
                    justDropped && "just-dropped"
                )}
            >
                <div className="p-4 border-b border-border/50">
                    <div className="flex items-center justify-between group">
                        <div>
                            <h3 className="text-lg font-semibold text-foreground">{list.name}</h3>
                            <p className="text-sm text-muted-foreground">{t('list.card', { count: cards.length })}</p>
                        </div>
                        {onCreateCard && (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => onCreateCard(list.id)}
                                className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:bg-primary/10"
                                title={t('list.createCardInList')}
                            >
                                <Plus className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                </div>

                <div
                    ref={containerRef}
                    className={cn(
                        "flex-1 p-4 space-y-3 overflow-y-auto",
                        isDragging && "sortable-context-dragging"
                    )}
                    style={{
                        '--placeholder-height': activeCardSize?.height ? `${activeCardSize.height}px` : '120px'
                    } as React.CSSProperties}
                >
                    {(() => {
                        const elements: React.ReactElement[] = [];

                        // Eviter d'afficher plusieurs placeholders simultanément dans une même colonne
                        let placeholderRendered = false;

                        // Calculer la position actuelle de la carte active dans cette colonne
                        const activeCard = cards.find(c => c.id === activeCardId);
                        const isActiveCardInThisColumn = activeCard && activeCard.list_id === list.id;

                        // Placeholder au début (position 0) - toujours afficher si dropTarget === 0
                        const shouldShowPlaceholderAtStart = dropTarget === 0 && isDragging;

                        if (shouldShowPlaceholderAtStart && !placeholderRendered) {

                            elements.push(
                                <div
                                    key="drop-indicator-0"
                                    className="placeholder-card rounded-lg flex items-center justify-center border-2 border-dashed border-blue-400 bg-blue-50"
                                    style={{
                                        width: activeCardSize?.width ? `${activeCardSize.width}px` : 'auto',
                                        height: activeCardSize?.height ? `${activeCardSize.height}px` : '120px',
                                        minHeight: activeCardSize?.height ? `${activeCardSize.height}px` : '120px'
                                    }}
                                >
                                    <span className="text-sm text-blue-600 font-medium">

                                    </span>
                                </div>
                            );
                            placeholderRendered = true;
                        }

                        // Ajouter toutes les cartes (y compris la carte active avec son placeholder si elle est dans cette colonne)
                        cards.forEach((card: Card) => {
                            const isActiveCard = card.id === activeCardId;
                            const isHiddenCard = card.id === hiddenCardId;



                            // Ignorer les cartes cachées, SAUF si c'est la carte active dans cette colonne (pour afficher le placeholder)
                            if (isHiddenCard && !(isActiveCard && isActiveCardInThisColumn)) {
                                return;
                            }

                            // Si c'est la carte active dans cette colonne ET qu'on est en train de dragger, afficher le placeholder "position actuelle"
                            if (isActiveCard && isActiveCardInThisColumn && isDragging) {
                                // Ne pas afficher le placeholder "position actuelle" - on veut seulement le placeholder "nouvelle position"
                                // La carte active est cachée via hiddenCardId, donc on n'affiche rien ici
                            } else {
                                // Afficher la carte normalement
                                elements.push(
                                    <div
                                        key={card.id}
                                        data-card-id={card.id}
                                        className="kanban-card-container"
                                    >
                                        <CardItem
                                            card={card}
                                            onUpdate={onCardUpdate}
                                            onDelete={(id) => onCardDelete(id)}
                                            isActiveCard={false}
                                            isJustDropped={card.id === justDroppedCardId}
                                            isHidden={false}
                                        />
                                    </div>
                                );
                            }

                            // Calculer l'index logique pour les placeholders
                            // Si c'est la carte active ou une carte cachée, ne pas ajouter de placeholder après
                            if (isActiveCard || isHiddenCard) {
                                return;
                            }

                            // Nouvelle logique simplifiée : calculer l'index dans la liste des cartes visibles
                            const visibleCards = cards.filter(c => c.id !== activeCardId);
                            const visibleCardIndex = visibleCards.findIndex(c => c.id === card.id);

                            // Ajouter un placeholder après cette carte si nécessaire
                            const shouldShowPlaceholderAfterCard = dropTarget === visibleCardIndex + 1 && isDragging;


                            if (shouldShowPlaceholderAfterCard && !placeholderRendered) {

                                elements.push(
                                    <div
                                        key={`drop-indicator-${visibleCardIndex + 1}`}
                                        className="placeholder-card rounded-lg flex items-center justify-center border-2 border-dashed border-blue-400 bg-blue-50"
                                        style={{
                                            width: activeCardSize?.width ? `${activeCardSize.width}px` : 'auto',
                                            height: activeCardSize?.height ? `${activeCardSize.height}px` : '120px',
                                            minHeight: activeCardSize?.height ? `${activeCardSize.height}px` : '120px'
                                        }}
                                    >
                                        <span className="text-sm text-blue-600 font-medium">

                                        </span>
                                    </div>
                                );
                                placeholderRendered = true;
                            }
                        });

                        // Placeholder à la fin (après toutes les cartes)
                        const visibleCardsCount = cards.filter(c => c.id !== activeCardId).length;
                        const shouldShowPlaceholderAtEnd = dropTarget === visibleCardsCount && isDragging;

                        if (shouldShowPlaceholderAtEnd && !placeholderRendered) {
                            elements.push(
                                <div
                                    key="drop-indicator-end"
                                    className="placeholder-card rounded-lg flex items-center justify-center border-2 border-dashed border-blue-400 bg-blue-50"
                                    style={{
                                        width: activeCardSize?.width ? `${activeCardSize.width}px` : 'auto',
                                        height: activeCardSize?.height ? `${activeCardSize.height}px` : '120px',
                                        minHeight: activeCardSize?.height ? `${activeCardSize.height}px` : '120px'
                                    }}
                                >
                                    <span className="text-sm text-blue-600 font-medium">

                                    </span>
                                </div>
                            );
                            placeholderRendered = true;
                        }

                        return elements;
                    })()}
                </div>
            </GlassmorphicCard>
        </div>
    );
}; 
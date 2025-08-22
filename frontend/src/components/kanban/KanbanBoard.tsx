import { useState, useRef, useEffect } from 'react';
import { DndContext, DragOverlay, closestCenter, PointerSensor, useSensor, useSensors, DragStartEvent, DragEndEvent, DragOverEvent, useDroppable } from '@dnd-kit/core';
import { KanbanColumn } from './KanbanColumn';
import { CardItem } from './index';
import { GlassmorphicCard } from '../ui/GlassmorphicCard';
import { Trash2, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Card as CardType, KanbanList } from '../../types/index';
import { listsApi } from '../../services/listsApi';


interface KanbanBoardProps {
    cards: CardType[];
    onCardUpdate: (card: CardType, action?: 'edit' | 'update') => void;
    onCardDelete: (cardId: number) => void;
    onCardMove: (cardId: number, newListId: number, position?: number) => void;
    onCreateCard?: (listId: number) => void;
    refreshTrigger?: number; // Prop pour forcer le rechargement des listes
}

const TrashZone = ({ isActive, onOverChange }: { isActive: boolean; onOverChange?: (v: boolean) => void }) => {
    const { setNodeRef, isOver } = useDroppable({ id: 'trash' });

    useEffect(() => {
        onOverChange?.(!!isOver);
    }, [isOver]);

    return (
        <div ref={setNodeRef} data-trash-zone className="fixed bottom-6 right-6 z-[2000]">
            <GlassmorphicCard
                className={cn(
                    "p-4 transition-all duration-200 border-2 border-dashed pointer-events-auto",
                    isOver
                        ? "border-destructive bg-destructive/20 scale-110 shadow-2xl"
                        : isActive
                            ? "border-destructive bg-destructive/10 scale-105 shadow-lg"
                            : "border-muted-foreground/30 bg-muted/50 opacity-60"
                )}
            >
                <div className="flex items-center space-x-2 text-destructive">
                    <Trash2 className="h-5 w-5" />
                    <span className="text-sm font-medium">Supprimer</span>
                </div>
            </GlassmorphicCard>
        </div>
    );
};

export const KanbanBoard = ({
    cards,
    onCardUpdate,
    onCardDelete,
    onCardMove,
    onCreateCard,
    refreshTrigger
}: KanbanBoardProps) => {
    const [activeCard, setActiveCard] = useState<CardType | null>(null);
    const [dropTarget, setDropTarget] = useState<{ listId: number; position: number } | null>(null);
    const [justDroppedCardId, setJustDroppedCardId] = useState<number | null>(null);
    const [hiddenCardId, setHiddenCardId] = useState<number | null>(null);
    const [isOverTrash, setIsOverTrash] = useState<boolean>(false);
    const [activeCardSize, setActiveCardSize] = useState<{ width: number; height: number } | null>(null);
    const [originalPositions, setOriginalPositions] = useState<Map<string, DOMRect>>(new Map());
    const [, setAnimationData] = useState<Map<string, { element: HTMLElement; deltaY: number }>>(new Map());
    const [lists, setLists] = useState<KanbanList[]>([]);
    const [, setSuppressAnimationListId] = useState<number | null>(null);
    const [listsLoading, setListsLoading] = useState<boolean>(true);
    const [listsError, setListsError] = useState<string | null>(null);
    const [shouldCenter, setShouldCenter] = useState<boolean>(false);
    const [optimalColumnWidth, setOptimalColumnWidth] = useState<number>(280);
    const boardRef = useRef<HTMLDivElement>(null);
    const lastDropUpdateTsRef = useRef<number>(0);

    // Fetch lists on component mount and when refreshTrigger changes
    useEffect(() => {
        const fetchLists = async () => {
            try {
                setListsLoading(true);
                setListsError(null);
                const fetchedLists = await listsApi.getLists();
                setLists(fetchedLists);
            } catch (error) {
                console.error('Error fetching lists:', error);
                setListsError('Erreur lors du chargement des listes');
            } finally {
                setListsLoading(false);
            }
        };

        fetchLists();
    }, [refreshTrigger]);

    const getCardsForList = (listId: number): CardType[] => {
        return cards.filter(card => card.list_id === listId);
    };

    // Calculer si les listes tiennent dans l'écran et la largeur optimale
    const calculateLayout = () => {
        if (lists.length === 0 || !boardRef.current) {
            return { shouldCenter: false, optimalWidth: 280 };
        }

        const containerWidth = boardRef.current.clientWidth; // Largeur intérieure sans padding
        const padding = 64; // Padding du conteneur (p-4 = 16px * 2)
        const gap = 12; // Gap CSS réel (0.75rem = 12px)
        const availableWidth = containerWidth - padding - (lists.length - 1) * gap;

        // Largeur par colonne si on utilise tout l'espace disponible
        const widthPerColumn = Math.floor(availableWidth / lists.length);

        let optimalWidth = 280;
        let shouldCenter = false;

        if (widthPerColumn >= 480) {
            // Assez d'espace pour 480px par colonne
            optimalWidth = 480;
            shouldCenter = true;
        } else if (widthPerColumn >= 280) {
            // Assez d'espace pour une largeur intermédiaire
            optimalWidth = widthPerColumn;
            shouldCenter = true;
        } else {
            // Pas assez d'espace, utiliser 280px avec scroll
            optimalWidth = 280;
            shouldCenter = false;
        }

        return { shouldCenter, optimalWidth };
    };

    // Mettre à jour le layout quand les listes changent
    useEffect(() => {
        const updateLayout = () => {
            const { shouldCenter, optimalWidth } = calculateLayout();
            setShouldCenter(shouldCenter);
            setOptimalColumnWidth(optimalWidth);
        };
        updateLayout();

        // Écouter les changements de taille de fenêtre
        window.addEventListener('resize', updateLayout);
        return () => window.removeEventListener('resize', updateLayout);
    }, [lists]);





    const clearDragStates = () => {
        setActiveCard(null);
        setJustDroppedCardId(null);
        setHiddenCardId(null);
        setActiveCardSize(null);
        setOriginalPositions(new Map());
        setAnimationData(new Map());
    };





    // Event listener global pour capturer la position de la souris
    useEffect(() => {
        const handleMouseMove = (event: MouseEvent) => {
            if (activeCard) {
                // Calculer la position en temps réel
                calculatePositionFromMouse(event.clientX, event.clientY);
            }
        };

        if (activeCard) {
            document.addEventListener('mousemove', handleMouseMove);
        }

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
        };
    }, [activeCard]);

    const calculatePositionFromMouse = (mouseX: number, mouseY: number): void => {
        if (!activeCard) return;

        // Trouver la colonne la plus proche de la souris
        const columnElements = boardRef.current?.querySelectorAll('[data-list-id]');
        let closestColumn: HTMLElement | null = null;
        let minDistance = Infinity;

        columnElements?.forEach((columnElement) => {
            const element = columnElement as HTMLElement;
            const rect = element.getBoundingClientRect();

            // Vérifier si la souris est dans cette colonne
            if (mouseX >= rect.left && mouseX <= rect.right && mouseY >= rect.top && mouseY <= rect.bottom) {
                closestColumn = element;
                minDistance = 0;
            } else {
                const columnCenterX = rect.left + rect.width / 2;
                const distance = Math.abs(mouseX - columnCenterX);
                if (distance < minDistance) {
                    minDistance = distance;
                    closestColumn = element;
                }
            }
        });

        if (closestColumn) {
            const listIdStr = (closestColumn as HTMLElement).getAttribute('data-list-id');
            if (listIdStr) {
                const listId = parseInt(listIdStr, 10);
                // Calculer la position dans cette colonne (même si c'est la même colonne)
                calculatePositionInList(listId, mouseY);
            }
        }
    };

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: { distance: 8 }  // Augmenter la distance pour éviter les drags accidentels
        })
    );

    const handleDragStart = (event: DragStartEvent): void => {
        const { active } = event;
        const card = cards.find(c => c.id === active.id);

        // Capturer la taille de la carte avant qu'elle ne soit cachée
        const cardElement = document.querySelector(`[data-card-id="${active.id}"]`) as HTMLElement;
        if (cardElement) {
            const rect = cardElement.getBoundingClientRect();
            setActiveCardSize({
                width: rect.width,
                height: rect.height
            });
        }

        setActiveCard(card || null);
        setHiddenCardId(Number(active.id));  // Keep track of the hidden card

        // Capturer les positions de toutes les cartes dans la liste d'origine
        if (card?.list_id) {
            const columnElement = boardRef.current?.querySelector(`[data-list-id="${card.list_id}"]`);
            const cardElements = columnElement?.querySelectorAll('[data-card-id]');
            const positions = new Map();

            cardElements?.forEach((element) => {
                const cardId = element.getAttribute('data-card-id');
                if (cardId) {
                    positions.set(cardId, element.getBoundingClientRect());
                }
            });

            setOriginalPositions(positions);
        }

        setDropTarget(null);
    };

    const handleDragOver = (event: DragOverEvent): void => {
        if (!activeCard) {
            setDropTarget(null);
            setIsOverTrash(false);
            return;
        }

        const mouseEvent = event.activatorEvent as MouseEvent;
        if (mouseEvent) {
            calculatePositionFromMouse(mouseEvent.clientX, mouseEvent.clientY);

            // Detect if mouse is over trash zone element
            const trashElem = document.querySelector('[data-trash-zone]') as HTMLElement | null;
            if (trashElem) {
                const rect = trashElem.getBoundingClientRect();
                const over = mouseEvent.clientX >= rect.left && mouseEvent.clientX <= rect.right && mouseEvent.clientY >= rect.top && mouseEvent.clientY <= rect.bottom;
                setIsOverTrash(over);
            } else {
                setIsOverTrash(false);
            }
        }
    };

    const calculatePositionInList = (listId: number, mouseY: number): void => {
        const columnElement = boardRef.current?.querySelector(`[data-list-id="${listId}"]`) as HTMLElement;

        if (columnElement) {
            const cardsInList = getCardsForList(listId);
            let insertPosition = cardsInList.length; // Default to end
            let boundaryY: number | null = null; // limite de bascule entre deux positions

            if (cardsInList.length === 0) {
                insertPosition = 0;
            } else {
                // Find the position based on mouse Y position
                const columnRect = columnElement.getBoundingClientRect();

                // Check if mouse is in the top area (before first card)
                const headerHeight = 80; // Hauteur approximative du header
                const topArea = columnRect.top + headerHeight;

                if (mouseY < topArea + 50) { // Réduire la tolérance pour être plus précis
                    insertPosition = 0;
                } else {
                    // Approche simplifiée : calculer la position d'insertion basée sur la position Y de la souris
                    // Créer une liste des cartes visibles (sans la carte active)
                    const visibleCards = cardsInList.filter(c => c.id !== activeCard?.id);

                    // Trouver la position d'insertion en comparant avec les rectangles des cartes
                    let targetPosition = visibleCards.length; // Par défaut, à la fin

                    for (let i = 0; i < visibleCards.length; i++) {
                        const card = visibleCards[i];
                        const cardElement = columnElement.querySelector(`[data-card-id="${card.id}"]`);

                        if (cardElement) {
                            const cardRect = cardElement.getBoundingClientRect();
                            const cardMiddle = cardRect.top + (cardRect.height / 2);

                            if (mouseY < cardMiddle) {
                                // On veut insérer avant cette carte
                                targetPosition = i;
                                boundaryY = cardMiddle;
                                break;
                            }
                        }
                    }

                    if (targetPosition === visibleCards.length && visibleCards.length > 0) {
                        const lastCard = visibleCards[visibleCards.length - 1];
                        const lastEl = columnElement.querySelector(`[data-card-id="${lastCard.id}"]`);
                        if (lastEl) {
                            const r = (lastEl as HTMLElement).getBoundingClientRect();
                            boundaryY = r.bottom;
                        }
                    }

                    insertPosition = targetPosition;
                }
            }

            // Note: L'ajustement de position est maintenant géré dans KanbanColumn
            // pour un affichage correct des indicateurs

            // Éviter les mises à jour inutiles
            if (!dropTarget || dropTarget.listId !== listId || dropTarget.position !== insertPosition) {
                const HYSTERESIS = 14; // px de marge pour éviter le flapping
                const now = performance.now();

                // Si on change de position dans la même colonne, appliquer une hystérésis et un throttle léger
                if (dropTarget && dropTarget.listId === listId) {
                    if (typeof boundaryY === 'number' && Math.abs(mouseY - boundaryY) < HYSTERESIS) {
                        // Trop près de la frontière: ne pas changer
                        return;
                    }
                    if (now - lastDropUpdateTsRef.current < 60) {
                        // Throttle: trop rapproché
                        return;
                    }
                }

                lastDropUpdateTsRef.current = now;

                // Capture first rects for this column before React inserts the placeholder
                const positions = new Map<string, DOMRect>();
                const cardEls = columnElement.querySelectorAll('[data-card-id]');
                cardEls?.forEach((el) => {
                    const id = el.getAttribute('data-card-id');
                    if (id) positions.set(id, el.getBoundingClientRect());
                });
                setOriginalPositions(positions);

                setDropTarget({ listId: listId, position: insertPosition });
            }
        }
    };

    const handleDragEnd = async (event: DragEndEvent): Promise<void> => {
        const { active, over } = event;

        // Store the drop target before clearing it
        const finalDropTarget = dropTarget;

        const activeId = active.id as number;

        // Mark this card as just dropped to keep it invisible
        setJustDroppedCardId(activeId);

        // Clear drop target immediately
        setDropTarget(null);

        if (!over) {
            // Delay clearing to prevent flash
            setTimeout(() => {
                clearDragStates();
            }, 300);
            return;
        }

        const overId = over.id as string;

        // Handle trash
        if (overId === 'trash') {
            try {
                onCardDelete(activeId);
            } catch (e) {
                console.error("Erreur lors de l'archivage de la carte:", e);
            }

            setTimeout(() => {
                clearDragStates();
            }, 300);
            return;
        }

        // Utiliser notre finalDropTarget au lieu de la logique DndKit
        if (finalDropTarget) {
            const targetListId = finalDropTarget.listId;
            const position = finalDropTarget.position;

            // Déplacer la carte exactement où le placeholder était affiché
            // Suppress animations for both source and destination lists
            setSuppressAnimationListId(finalDropTarget.listId);
            // expose globally for hooks inside columns to read synchronously
            (window as any).__SUPPRESS_ANIM_LIST_ID = finalDropTarget.listId;
            onCardMove(activeId, targetListId, position);

            // Delay clearing to ensure the card has moved
            setTimeout(() => {
                clearDragStates();
                setSuppressAnimationListId(null);
                try { delete (window as any).__SUPPRESS_ANIM_LIST_ID; } catch (e) { }
            }, 300);
            return;
        }

        // Fallback: utiliser la logique DndKit si pas de finalDropTarget
        // Try to parse overId as list ID
        const listId = parseInt(overId, 10);
        if (!isNaN(listId) && lists.some(list => list.id === listId)) {
            const position = getCardsForList(listId).length;
            onCardMove(activeId, listId, position);
            setTimeout(() => {
                clearDragStates();
            }, 300);
            return;
        }

        // Clear states with delay
        setTimeout(() => {
            clearDragStates();
        }, 150);
    };

    // Show loading state
    if (listsLoading) {
        return (
            <div className="flex-1 p-4 bg-background min-h-0 relative flex items-center justify-center">
                <div className="flex items-center space-x-2 text-muted-foreground">
                    <Loader2 className="h-6 w-6 animate-spin" />
                    <span>Chargement des listes...</span>
                </div>
            </div>
        );
    }

    // Show error state
    if (listsError) {
        return (
            <div className="flex-1 p-4 bg-background min-h-0 relative flex items-center justify-center">
                <div className="text-center">
                    <p className="text-destructive mb-2">{listsError}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="text-sm text-muted-foreground hover:text-foreground"
                    >
                        Actualiser la page
                    </button>
                </div>
            </div>
        );
    }

    // Show empty state if no lists
    if (lists.length === 0) {
        return (
            <div className="flex-1 p-4 bg-background min-h-0 relative flex items-center justify-center">
                <div className="text-center text-muted-foreground">
                    <p>Aucune liste disponible</p>
                    <p className="text-sm mt-1">Contactez un administrateur pour créer des listes</p>
                </div>
            </div>
        );
    }

    return (
        <div
            ref={boardRef}
            className="flex-1 p-4 bg-background min-h-0 relative overflow-hidden"
        >
            <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
                onDragOver={handleDragOver}
                autoScroll={true}
            >
                {/* Horizontal scrolling container */}
                <div className="h-full kanban-horizontal-scroll">
                    <div className="kanban-lists-container h-full" style={{
                        justifyContent: shouldCenter ? 'center' : 'flex-start'
                    }}>
                        {lists.map(list => {
                            const listCards = getCardsForList(list.id);
                            return (
                                <div
                                    key={list.id}
                                    className="kanban-list-column"
                                    style={{
                                        minWidth: '280px',
                                        maxWidth: '480px',
                                        width: `${optimalColumnWidth}px`,
                                        flex: `0 0 ${optimalColumnWidth}px`
                                    }}
                                >
                                    <KanbanColumn
                                        id={String(list.id)}
                                        list={list}
                                        cards={listCards}
                                        onCardUpdate={onCardUpdate}
                                        onCardDelete={onCardDelete}
                                        onCreateCard={onCreateCard}
                                        isDragging={!!activeCard}
                                        dropTarget={isOverTrash ? null : (dropTarget?.listId === list.id ? dropTarget.position : null)}
                                        activeCardId={activeCard?.id || null}
                                        justDroppedCardId={justDroppedCardId}
                                        hiddenCardId={hiddenCardId}
                                        activeCardSize={activeCardSize}
                                        originalPositions={originalPositions}
                                    />
                                </div>
                            );
                        })}
                    </div>
                </div>

                <TrashZone isActive={!!activeCard} onOverChange={(v) => setIsOverTrash(v)} />

                <div data-debug-is-over-trash style={{ display: 'none' }} data-over={String(isOverTrash)} />

                <DragOverlay
                    dropAnimation={null}  // Désactiver l'animation de drop
                    modifiers={[]}  // Pas de modificateurs d'animation
                >
                    {activeCard ? (
                        <div className={`drag-overlay ${isOverTrash ? 'z-[3000]' : ''}`}>
                            <div className="relative">
                                {isOverTrash && (
                                    <div className="absolute inset-0 rounded-xl bg-destructive/20 pointer-events-none" />
                                )}
                                <CardItem
                                    card={activeCard}
                                    isDragging={true}
                                    isInTrashZone={isOverTrash}
                                    onUpdate={() => { }}
                                    onDelete={(id) => onCardDelete(id)}
                                />
                            </div>
                        </div>
                    ) : null}
                </DragOverlay>
            </DndContext>
        </div>
    );
}; 
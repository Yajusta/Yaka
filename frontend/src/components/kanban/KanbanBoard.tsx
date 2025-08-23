import { useState, useRef, useEffect } from 'react';
import { DndContext, DragOverlay, closestCenter, PointerSensor, TouchSensor, useSensor, useSensors, DragStartEvent, DragEndEvent, DragOverEvent, useDroppable } from '@dnd-kit/core';
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
    isAnyModalOpen?: boolean; // Prop pour masquer le TrashZone quand une modale est ouverte
}

const TrashZone = ({ isActive, onOverChange, isAnyModalOpen }: { isActive: boolean; onOverChange?: (v: boolean) => void; isAnyModalOpen?: boolean }) => {
    const { setNodeRef, isOver } = useDroppable({ id: 'trash' });

    useEffect(() => {
        onOverChange?.(!!isOver);
    }, [isOver]);

    return (
        <div
            ref={setNodeRef}
            data-trash-zone
            className={cn(
                "fixed bottom-6 right-6 z-[2000] transition-all duration-200",
                isAnyModalOpen ? "opacity-0 pointer-events-none" : "opacity-100"
            )}
        >
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
    refreshTrigger,
    isAnyModalOpen = false
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





    // Event listener global pour capturer la position de la souris ou du tactile
    useEffect(() => {
        const handlePointerMove = (event: MouseEvent | TouchEvent) => {
            if (!activeCard) {
                return;
            }

            let clientX: number | null = null;
            let clientY: number | null = null;

            // TouchEvent
            if ('touches' in event) {
                // Prevent the page from scrolling while dragging
                try { (event as TouchEvent).preventDefault(); } catch (e) { }
                const touch = (event as TouchEvent).touches?.[0] || (event as any).changedTouches?.[0];
                if (touch) {
                    clientX = touch.clientX;
                    clientY = touch.clientY;
                }
            } else {
                // MouseEvent
                clientX = (event as MouseEvent).clientX;
                clientY = (event as MouseEvent).clientY;
            }

            if (clientX != null && clientY != null) {
                // Calculer la position en temps réel
                calculatePositionFromMouse(clientX, clientY);
            }
        };

        if (activeCard) {
            document.addEventListener('mousemove', handlePointerMove as any);
            // Use non-passive listener so we can preventDefault and avoid page scrolling during drag
            document.addEventListener('touchmove', handlePointerMove as any, { passive: false });
            // Pointer events cover mouse, touch and pen on many platforms — ensure we capture pointermove as well
            document.addEventListener('pointermove', handlePointerMove as any, { passive: false });
        }

        return () => {
            document.removeEventListener('mousemove', handlePointerMove as any);
            document.removeEventListener('touchmove', handlePointerMove as any);
            document.removeEventListener('pointermove', handlePointerMove as any);
        };
    }, [activeCard]);

    const calculatePositionFromMouse = (mouseX: number, mouseY: number): void => {
        if (!activeCard) {
            return;
        }

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
        }),
        useSensor(TouchSensor, {
            activationConstraint: {
                delay: 80,
                tolerance: 5,
            }
        })
    );

    // While a card is active (being dragged), disable body touch-action to prevent page panning
    useEffect(() => {
        const original = document.body.style.touchAction || '';
        if (activeCard) {
            document.body.style.touchAction = 'none';
        } else {
            document.body.style.touchAction = original;
        }
        return () => {
            document.body.style.touchAction = original;
        };
    }, [activeCard]);

    const handleDragStart = (event: DragStartEvent): void => {
        const { active } = event;
        // Find card by normalizing ids to string to avoid type mismatches (number vs string)
        const card = cards.find(c => String(c.id) === String(active.id));

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
        // Only hide the DOM card if we actually found the card object
        if (card) {
            setHiddenCardId(Number(active.id));  // Keep track of the hidden card
        } else {
            setHiddenCardId(null);
        }

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

        // If DnDKit reports a droppable under the pointer, use it as a quick fallback
        const reportedOverId = event?.over?.id as string | undefined;
        if (reportedOverId && reportedOverId !== 'trash') {
            const reportedListId = parseInt(reportedOverId, 10);
            if (!isNaN(reportedListId) && lists.some(list => list.id === reportedListId)) {
                // If we don't yet have a dropTarget for this list, set it to the end (temporary)
                const endPos = getCardsForList(reportedListId).length;
                if (!dropTarget || dropTarget.listId !== reportedListId) {
                    setDropTarget({ listId: reportedListId, position: endPos });
                }
            }
        }

        const activatorEvent = event.activatorEvent as MouseEvent | TouchEvent | undefined;
        if (activatorEvent) {
            let clientX: number | null = null;
            let clientY: number | null = null;

            if ('touches' in activatorEvent) {
                const touch = (activatorEvent as TouchEvent).touches?.[0] || (activatorEvent as any).changedTouches?.[0];
                if (touch) {
                    clientX = touch.clientX;
                    clientY = touch.clientY;
                }
            } else {
                clientX = (activatorEvent as MouseEvent).clientX;
                clientY = (activatorEvent as MouseEvent).clientY;
            }

            if (clientX != null && clientY != null) {
                // Try to resolve the column directly under the pointer (more robust than closestCenter heuristics)
                const elem = document.elementFromPoint(clientX, clientY) as HTMLElement | null;
                let listEl = elem?.closest ? elem.closest('[data-list-id]') as HTMLElement | null : null;

                // If closest failed (e.g. empty column), try to find a column whose rect contains the point
                if (!listEl && boardRef.current) {
                    const columns = boardRef.current.querySelectorAll('[data-list-id]');
                    for (let i = 0; i < columns.length; i++) {
                        const col = columns[i] as HTMLElement;
                        const r = col.getBoundingClientRect();
                        const contains = clientX >= r.left && clientX <= r.right && clientY >= r.top && clientY <= r.bottom;
                        if (contains) {
                            listEl = col;
                            break;
                        }
                    }
                }

                if (listEl) {
                    const listIdStr = listEl.getAttribute('data-list-id');
                    if (listIdStr) {
                        const listId = parseInt(listIdStr, 10);
                        if (!isNaN(listId)) {
                            // Compute precise insertion position inside that list
                            calculatePositionInList(listId, clientY);
                        }
                    }
                } else {
                    // Fallback to previous center-based calculation
                    calculatePositionFromMouse(clientX, clientY);
                }

                // Detect if pointer is over trash zone element
                const trashElem = document.querySelector('[data-trash-zone]') as HTMLElement | null;
                if (trashElem) {
                    const rect = trashElem.getBoundingClientRect();
                    const over = clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom;
                    setIsOverTrash(over);
                } else {
                    setIsOverTrash(false);
                }

                // done
            }
        }

        // Fallback: if no dropTarget was computed, try to infer the list under the pointer
        if (!dropTarget && activatorEvent) {
            let clientX: number | null = null;
            let clientY: number | null = null;
            if ('touches' in activatorEvent) {
                const touch = (activatorEvent as TouchEvent).touches?.[0] || (activatorEvent as any).changedTouches?.[0];
                if (touch) { clientX = touch.clientX; clientY = touch.clientY; }
            } else {
                clientX = (activatorEvent as MouseEvent).clientX;
                clientY = (activatorEvent as MouseEvent).clientY;
            }

            if (clientX != null && clientY != null && boardRef.current) {
                const elem = document.elementFromPoint(clientX, clientY) as HTMLElement | null;
                const listEl = elem?.closest ? elem.closest('[data-list-id]') as HTMLElement | null : null;
                if (listEl) {
                    const listIdStr = listEl.getAttribute('data-list-id');
                    if (listIdStr) {
                        const listId = parseInt(listIdStr, 10);
                        if (!isNaN(listId)) {
                            const pos = getCardsForList(listId).length;
                            setDropTarget({ listId, position: pos });
                        }
                    }
                }
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
                // Debugging removed in cleanup
                // Find the position based on mouse Y position
                const columnRect = columnElement.getBoundingClientRect();

                // Check if mouse is in the top area (before first card)
                const headerHeight = 80; // Hauteur approximative du header
                const topArea = columnRect.top + headerHeight;

                if (mouseY < topArea + 50) { // Réduire la tolérance pour être plus précis
                    insertPosition = 0;
                } else {
                    // Approche simplifiée : calculer la position d'insertion basée sur la position Y de la souris
                    // Use DOM elements to compute insertion position. This is more robust when the active card
                    // is hidden from the DOM (we rely on data-card-id attributes rendered for visible cards).
                    const cardEls = Array.from(columnElement.querySelectorAll('[data-card-id]')) as HTMLElement[];
                    let targetPosition = cardEls.length; // default to end

                    for (let i = 0; i < cardEls.length; i++) {
                        const el = cardEls[i];
                        const rect = el.getBoundingClientRect();
                        const middle = rect.top + rect.height / 2;
                        if (mouseY < middle) {
                            targetPosition = i;
                            boundaryY = middle;
                            break;
                        }
                    }

                    if (targetPosition === cardEls.length && cardEls.length > 0) {
                        const lastEl = cardEls[cardEls.length - 1];
                        const r = lastEl.getBoundingClientRect();
                        boundaryY = r.bottom;
                    }

                    insertPosition = targetPosition;

                    // computed insertPosition
                }
            }

            // Note: L'ajustement de position est maintenant géré dans KanbanColumn
            // pour un affichage correct des indicateurs

            // Éviter les mises à jour inutiles
            if (!dropTarget || dropTarget.listId !== listId || dropTarget.position !== insertPosition) {
                const HYSTERESIS = 8; // px de marge pour éviter le flapping — réduit pour être plus réactif
                const now = performance.now();

                // Si on change de position dans la même colonne, appliquer une hystérésis et un throttle léger
                if (dropTarget && dropTarget.listId === listId) {
                    if (typeof boundaryY === 'number' && Math.abs(mouseY - boundaryY) < HYSTERESIS) {
                        // Trop près de la frontière: ne pas changer
                        return;
                    }
                    if (now - lastDropUpdateTsRef.current < 40) {
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
                    if (id) {
                        positions.set(id, el.getBoundingClientRect());
                    }
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

        // Resolve active card id robustly (active.id can be number or string)
        let activeId = Number(active.id);
        if (Number.isNaN(activeId)) {
            const found = cards.find(c => String(c.id) === String(active.id));
            if (found) {
                activeId = found.id;
            }
        }

        // handleDragEnd

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
            const { position } = finalDropTarget;

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

                <TrashZone
                    isActive={!!activeCard}
                    onOverChange={(v) => setIsOverTrash(v)}
                    isAnyModalOpen={isAnyModalOpen}
                />



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
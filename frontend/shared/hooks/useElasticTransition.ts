import { useEffect, useRef, useCallback, useLayoutEffect } from 'react';

interface UseElasticTransitionProps {
    isDragging: boolean;
    dropTarget: number | null;
    cards: any[];
    activeCardId?: number | null;
    activeCardSize?: { width: number; height: number } | null;
    hiddenCardId?: number | null;
    originalPositions?: Map<string, DOMRect> | null;
}

export const useElasticTransition = ({
    isDragging,
    dropTarget,
    cards,
    activeCardId,
    activeCardSize,
    originalPositions
}: UseElasticTransitionProps) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const previousDropTarget = useRef<number | null>(null);
    const previousIsDragging = useRef<boolean>(false);

    const resetCardPositions = useCallback(() => {
        if (!containerRef.current) {
            return;
        }

        const cardElements = containerRef.current.querySelectorAll('.kanban-card-container');
        cardElements.forEach((element) => {
            const cardElement = element as HTMLElement;
            cardElement.style.transform = '';
        });
    }, []);

    // Keep last measured rects to compute FLIP when a card is removed from this column
    const prevRectsRef = useRef<Map<string, DOMRect> | null>(null);
    const columnAnimatingRef = useRef<boolean>(false);
    const lastAnimationKey = useRef<string | null>(null);

    // Measure positions synchronously after every render so prevRectsRef holds the 'before' positions
    useLayoutEffect(() => {
        if (!containerRef.current) {
            return;
        }
        const nodeList = containerRef.current.querySelectorAll('.kanban-card-container');
        const elems = Array.from(nodeList).filter(el => (el as HTMLElement).getAttribute('data-card-id')) as HTMLElement[];
        const rects = new Map<string, DOMRect>();
        elems.forEach(el => {
            const id = el.getAttribute('data-card-id')!;
            rects.set(id, el.getBoundingClientRect());
        });
        prevRectsRef.current = rects;
    });

    useEffect(() => {
        if (!containerRef.current) {
            return;
        }
        const container = containerRef.current;
        const nodeList = container.querySelectorAll('.kanban-card-container');
        const cardElements = Array.from(nodeList).filter(el => (el as HTMLElement).getAttribute('data-card-id')) as HTMLElement[];

        const prevRects = prevRectsRef.current;

        // If placeholder position changed while dragging, run FLIP using originalPositions (if available) or prevRects
        const hasDropTargetChanged = dropTarget !== previousDropTarget.current;
        if (isDragging && dropTarget !== null && hasDropTargetChanged && !columnAnimatingRef.current) {
            columnAnimatingRef.current = true;
            const firstRects = (originalPositions && originalPositions.size ? originalPositions : prevRects) || new Map<string, DOMRect>();

            // build animation key to avoid duplicate FLIP runs
            const animationKey = `${String(dropTarget)}|${Array.from(firstRects.keys()).join(',')}`;
            if (lastAnimationKey.current === animationKey) {
                columnAnimatingRef.current = false;
                previousDropTarget.current = dropTarget;
                previousIsDragging.current = isDragging;
                return;
            }
            lastAnimationKey.current = animationKey;

            // If parent passed suppress flag, don't animate this column
            try {
                const colEl = containerRef.current?.closest('[data-list-id]') as HTMLElement | null;
                if (colEl) {
                    const listId = Number(colEl.getAttribute('data-list-id'));
                    const parentSuppress = (window as any).__SUPPRESS_ANIM_LIST_ID || null;
                    if (parentSuppress === listId) {
                        columnAnimatingRef.current = false;
                        previousDropTarget.current = dropTarget;
                        previousIsDragging.current = isDragging;
                        return;
                    }
                }
            } catch (e) { }

            // Delay one frame to ensure DOM has applied placeholder/layout changes, then capture last rects
            requestAnimationFrame(() => {
                const lastRects = new Map<string, DOMRect>();
                cardElements.forEach(el => {
                    const id = el.getAttribute('data-card-id')!;
                    lastRects.set(id, el.getBoundingClientRect());
                });

                // apply inverse transforms to moved cards (skip active card) and mark animating
                cardElements.forEach(el => {
                    const id = el.getAttribute('data-card-id')!;
                    if (String(activeCardId) === id) {
                        return;
                    }
                    // cancel any running animations on this element to avoid double runs, but only if they belong to a different key
                    try {
                        const prevAnim = (el as any).__flipAnim as Animation | null;
                        const prevKey = (el as any).__flipKey as string | null;
                        if (prevAnim && prevKey !== animationKey) {
                            try { prevAnim.cancel(); } catch (e) { }
                            (el as any).__flipAnim = null;
                            (el as any).__flipKey = null;
                        }
                    } catch (e) { }
                    if (el.dataset.flipAnimating) {
                        return;
                    }
                    const first = firstRects.get(id);
                    const last = lastRects.get(id);
                    if (!first || !last) {
                        return;
                    }
                    const deltaY = first.top - last.top;
                    if (Math.abs(deltaY) > 1) {
                        el.style.transition = 'none';
                        el.style.transform = `translateY(${deltaY}px)`;
                        el.style.willChange = 'transform';
                        el.dataset.flipAnimating = '1';
                    }
                });

                // next frame: animate to natural positions using WAAPI for elastic effect (with CSS fallback)
                requestAnimationFrame(() => {
                    // capture lastRects again for debugging
                    const debugLast = new Map<string, DOMRect>();
                    cardElements.forEach(el => {
                        const id = el.getAttribute('data-card-id')!;
                        debugLast.set(id, el.getBoundingClientRect());
                    });

                    cardElements.forEach(el => {
                        if (!el.style.transform || !el.dataset.flipAnimating) {
                            return;
                        }

                        // parse current translateY value
                        const match = el.style.transform.match(/translateY\((-?\d+(?:\.\d+)?)px\)/);
                        const delta = match ? Number(match[1]) : 0;

                        // ensure no duplicate animations: cancel any before starting
                        try { el.getAnimations().forEach(a => a.cancel()); } catch (e) { }

                        try {
                            const anim = el.animate([
                                { transform: `translateY(${delta}px)` },
                                { transform: 'translateY(0px)' }
                            ], {
                                duration: 200,
                                easing: 'ease'
                            });

                            // store animation and key on element to avoid global cancels
                            (el as any).__flipAnim = anim;
                            (el as any).__flipKey = animationKey;

                            anim.addEventListener('finish', () => {
                                el.style.transform = '';
                                el.style.willChange = '';
                                delete el.dataset.flipAnimating;
                                try { (el as any).__flipAnim = null; } catch (e) { }
                                try { (el as any).__flipKey = null; } catch (e) { }
                            });
                        } catch (e) {
                            // fallback to CSS transition if WAAPI not available
                            el.style.transition = 'transform 700ms cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                            el.style.transform = '';

                            const cleanup = () => {
                                el.style.transition = '';
                                el.style.willChange = '';
                                delete el.dataset.flipAnimating;
                                el.removeEventListener('transitionend', cleanup);
                            };
                            el.addEventListener('transitionend', cleanup);
                        }
                    });

                    const columnEl = container.closest('.kanban-column') as HTMLElement || container;
                    columnEl.classList.add('placeholder-active');

                    // early return to avoid duplicate animations
                    previousDropTarget.current = dropTarget;
                    previousIsDragging.current = isDragging;

                    // allow next column animation after a short cooldown
                    setTimeout(() => { columnAnimatingRef.current = false; }, 250);
                });
            });

            return;
        }

        // Detect if a card was just removed from this column (fallback for source column removal)
        const prevIds = prevRects ? Array.from(prevRects.keys()) : [];
        const currentIds = cardElements.map(el => el.getAttribute('data-card-id')!);
        const removedIds = prevIds.filter(id => !currentIds.includes(id));

        const originalRects = originalPositions || prevRects;
        const originalIds = originalRects ? Array.from(originalRects.keys()) : [];
        const removedFromOriginal = originalIds.filter(id => !currentIds.includes(id));

        const effectiveRemoved = removedFromOriginal.length > 0 ? removedFromOriginal : removedIds;

        if (isDragging && effectiveRemoved.length > 0) {
            const movingCards = cardElements.filter(el => {
                const id = el.getAttribute('data-card-id')!;
                return (originalRects?.has(id) || prevRects?.has(id));
            });

            movingCards.forEach(el => {
                const id = el.getAttribute('data-card-id')!;
                const first = (originalPositions && originalPositions.get(id)) || prevRects!.get(id);
                const last = el.getBoundingClientRect();
                const deltaY = first ? first.top - last.top : 0;
                if (Math.abs(deltaY) > 1) {
                    el.style.transition = 'none';
                    el.style.transform = `translateY(${deltaY}px)`;
                    el.style.willChange = 'transform';
                }
            });

            requestAnimationFrame(() => {
                movingCards.forEach(el => {
                    if (el.style.transform) {
                        el.style.transition = 'transform 500ms cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                        el.style.transform = '';

                        const cleanup = () => {
                            el.style.transition = '';
                            el.style.willChange = '';
                            el.removeEventListener('transitionend', cleanup);
                        };

                        el.addEventListener('transitionend', cleanup);
                    }
                });
            });

            const columnEl = container.closest('.kanban-column') as HTMLElement || container;
            columnEl.classList.add('placeholder-active');
        }

        // restore/remove placeholder-active when needed
        if (isDragging && dropTarget === null && previousDropTarget.current !== null) {
            container.classList.remove('placeholder-active');
            cardElements.forEach(el => {
                el.style.transition = 'transform 200ms ease';
                el.style.transform = '';
                setTimeout(() => {
                    el.style.transition = '';
                }, 220);
            });
        } else if (!isDragging && previousIsDragging.current) {
            container.classList.remove('placeholder-active');
            setTimeout(() => {
                cardElements.forEach(el => {
                    el.style.transition = 'none';
                    el.style.transform = '';
                    el.offsetHeight;
                    el.style.transition = '';
                });
            }, 100);
        }

        previousDropTarget.current = dropTarget;
        previousIsDragging.current = isDragging;
    }, [isDragging, dropTarget, activeCardId, cards.length, activeCardSize, resetCardPositions]);

    return containerRef;
};
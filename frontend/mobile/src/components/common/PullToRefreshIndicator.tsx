import { useState, useRef, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface PullToRefreshIndicatorProps {
  onRefresh: () => Promise<void>;
  children: React.ReactNode;
  isRefreshing?: boolean;
}

export const PullToRefreshIndicator: React.FC<PullToRefreshIndicatorProps> = ({
  onRefresh,
  children,
  isRefreshing: externalRefreshing = false
}) => {
  const { t } = useTranslation();
  const [isPulling, setIsPulling] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const [isInternalRefreshing, setIsInternalRefreshing] = useState(false);
  const startY = useRef<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const isRefreshing = externalRefreshing || isInternalRefreshing;
  const PULL_THRESHOLD = 80; // Distance needed to trigger refresh

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleTouchStart = (e: TouchEvent) => {
      // Only allow pull-to-refresh when at the top of the container
      if (container.scrollTop <= 5) {
        startY.current = e.touches[0].clientY;
        setIsPulling(false);
        setPullDistance(0);
      }
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (startY.current === null || isRefreshing) return;

      const currentY = e.touches[0].clientY;
      const diff = currentY - startY.current;

      // Only pull down (positive diff) when at the top and with sufficient distance
      if (diff > 15 && container.scrollTop <= 5) {
        e.preventDefault();
        setPullDistance(Math.min(diff - 15, 150)); // Cap the pull distance, subtract threshold
        setIsPulling(true);
      } else if (diff <= 0) {
        // Allow normal scrolling when not pulling down
        startY.current = null;
        setIsPulling(false);
        setPullDistance(0);
      }
    };

    const handleTouchEnd = async (e: TouchEvent) => {
      if (startY.current === null) return;

      if (pullDistance >= PULL_THRESHOLD && !isRefreshing) {
        setIsInternalRefreshing(true);
        try {
          await onRefresh();
        } finally {
          setIsInternalRefreshing(false);
        }
      }

      // Reset states
      startY.current = null;
      setIsPulling(false);
      setPullDistance(0);
    };

    container.addEventListener('touchstart', handleTouchStart, { passive: false });
    container.addEventListener('touchmove', handleTouchMove, { passive: false });
    container.addEventListener('touchend', handleTouchEnd, { passive: false });

    return () => {
      container.removeEventListener('touchstart', handleTouchStart);
      container.removeEventListener('touchmove', handleTouchMove);
      container.removeEventListener('touchend', handleTouchEnd);
    };
  }, [onRefresh, isRefreshing, pullDistance]);

  return (
    <div className="relative h-full flex flex-col">
      {/* Pull indicator */}
      <div
        className="absolute top-0 left-0 right-0 z-50 flex items-center justify-center bg-background border-b border-border transition-all duration-300"
        style={{
          height: `${isPulling ? Math.min(pullDistance, 150) : 0}px`,
          opacity: isPulling ? 1 : 0,
          transform: `translateY(${isPulling ? 0 : -20}px)`
        }}
      >
        <div className="flex flex-col items-center justify-center">
          <RefreshCw
            className={`w-6 h-6 mb-2 transition-transform duration-300 ${
              isRefreshing ? 'animate-spin' : ''
            } ${pullDistance >= PULL_THRESHOLD ? 'text-primary' : 'text-muted-foreground'}`}
            style={{
              transform: `rotate(${Math.min(pullDistance * 2, 360)}deg)`
            }}
          />
          <span className="text-sm text-muted-foreground">
            {isRefreshing
              ? t('pullToRefresh.refreshing')
              : pullDistance >= PULL_THRESHOLD
                ? t('pullToRefresh.releaseToRefresh')
                : t('pullToRefresh.pullToRefresh')
            }
          </span>
        </div>
      </div>

      {/* Scrollable content */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto smooth-scroll"
        style={{
          transform: isPulling ? `translateY(${Math.min(pullDistance, 150)}px)` : 'translateY(0)'
        }}
      >
        {children}
      </div>
    </div>
  );
};
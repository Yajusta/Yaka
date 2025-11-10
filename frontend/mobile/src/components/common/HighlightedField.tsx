import { Info } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';

interface HighlightedFieldProps {
  isChanged: boolean;
  tooltipContent: string;
  children: React.ReactNode;
  className?: string;
}

export const HighlightedField = ({ isChanged, tooltipContent, children, className = '' }: HighlightedFieldProps) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState<'bottom' | 'top'>('bottom');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isChanged && showTooltip) {
      setShowTooltip(false);
    }
  }, [isChanged, showTooltip]);

  useEffect(() => {
    if (showTooltip && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;

      if (spaceBelow < 150 && spaceAbove > spaceBelow) {
        setTooltipPosition('top');
      } else {
        setTooltipPosition('bottom');
      }
    }
  }, [showTooltip]);

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="relative">
        <div className={`relative rounded-lg ${isChanged ? 'border-2 border-green-500 p-0.5' : ''}`}>
          {children}
        </div>

        {isChanged && (
          <button
            type="button"
            onClick={() => setShowTooltip(!showTooltip)}
            className="absolute -top-2 -right-2 bg-green-500 text-white rounded-full p-1 shadow-lg z-10"
            aria-label="Show previous value"
          >
            <Info className="w-4 h-4" />
          </button>
        )}
      </div>

      {isChanged && showTooltip && (
        <>
          <div
            className="fixed inset-0 z-20"
            onClick={() => setShowTooltip(false)}
          />
          <div
            className={`absolute left-0 right-0 bg-card border-2 border-green-500 rounded-lg p-3 shadow-xl z-30 ${
              tooltipPosition === 'bottom'
                ? 'top-full mt-2 animate-slide-up'
                : 'bottom-full mb-2 animate-slide-down'
            }`}
          >
            <p className="text-sm text-foreground break-words">{tooltipContent}</p>
          </div>
        </>
      )}
    </div>
  );
};


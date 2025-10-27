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
    if (showTooltip && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      
      // Si moins de 150px en dessous, afficher au-dessus
      if (spaceBelow < 150 && spaceAbove > spaceBelow) {
        setTooltipPosition('top');
      } else {
        setTooltipPosition('bottom');
      }
    }
  }, [showTooltip]);

  if (!isChanged) {
    return <>{children}</>;
  }

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="relative">
        {/* Green border wrapper */}
        <div className="relative border-2 border-green-500 rounded-lg p-0.5">
          {children}
        </div>
        
        {/* Info icon */}
        <button
          type="button"
          onClick={() => setShowTooltip(!showTooltip)}
          className="absolute -top-2 -right-2 bg-green-500 text-white rounded-full p-1 shadow-lg z-10"
          aria-label="Show previous value"
        >
          <Info className="w-4 h-4" />
        </button>
      </div>

      {/* Tooltip */}
      {showTooltip && (
        <>
          {/* Backdrop to close tooltip */}
          <div
            className="fixed inset-0 z-20"
            onClick={() => setShowTooltip(false)}
          />
          {/* Tooltip content */}
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


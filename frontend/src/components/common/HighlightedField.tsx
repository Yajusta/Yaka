import { ReactNode } from 'react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';

interface HighlightedFieldProps {
    isChanged: boolean;
    tooltipContent: string;
    children: ReactNode;
    className?: string;
}

/**
 * Composant wrapper qui met en évidence les champs modifiés avec une bordure verte,
 * un fond teinté, une animation pulse et un petit indicateur dans le coin.
 * Affiche une tooltip avec l'ancienne valeur au survol.
 */
export const HighlightedField = ({ isChanged, tooltipContent, children, className = '' }: HighlightedFieldProps) => {
    if (!isChanged) {
        return <>{children}</>;
    }

    return (
        <TooltipProvider>
            <Tooltip>
                <TooltipTrigger asChild>
                    <div className={`relative ${className}`}>
                        <div className="[&>*]:border-2 [&>*]:border-green-500 [&>*]:ring-2 [&>*]:ring-green-200 [&>*]:bg-green-50/30 [&>*]:dark:bg-green-950/20 animate-pulse-slow">
                            {children}
                        </div>
                        {/* Petit indicateur visuel dans le coin */}
                        <div className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full animate-ping" style={{ animationIterationCount: '3' }}></div>
                        <div className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full"></div>
                    </div>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800">
                    <p className="text-sm text-green-900 dark:text-green-100">{tooltipContent}</p>
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
};


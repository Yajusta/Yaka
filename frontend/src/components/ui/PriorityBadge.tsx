import { ArrowDown, ArrowUp, Minus } from 'lucide-react';
import { cn } from '@shared/lib/utils';
import { Badge } from './badge';

interface PriorityBadgeProps {
    // Accept backend values ("Faible", "Moyen", "Élevé"), normalized French keys ('faible'|'moyen'|'eleve')
    // or internal english keys ('low'|'medium'|'high').
    priority: string;
    className?: string;
    interactive?: boolean;
}

// Render a small icon-only badge for priorities.
// - high: red upward arrow
// - medium: blue horizontal dash
// - low: gray downward arrow
export const PriorityBadge = ({ priority, className, interactive = true }: PriorityBadgeProps) => {
    const baseClass = `inline-flex items-center justify-center p-0.5 rounded-sm ${interactive ? 'cursor-pointer' : 'cursor-default'}`;

    // Normalize input to a simple key: 'low' | 'medium' | 'high'
    const normalize = (p: string): 'low' | 'medium' | 'high' => {
        if (!p) {
            return 'low';
        }
        const lower = String(p).toLowerCase();
        // remove accents (é -> e)
        const normalized = lower.normalize('NFD').replace(/\p{Diacritic}/gu, '');

        // English forms
        if (normalized.includes('high') || normalized === 'high') {
            return 'high';
        }
        if (normalized.includes('medium') || normalized === 'medium') {
            return 'medium';
        }
        if (normalized.includes('low') || normalized === 'low') {
            return 'low';
        }

        // French forms (defensive)
        if (normalized.includes('elev') || normalized.includes('eleve') || normalized.includes('ele')) {
            return 'high';
        }
        if (normalized.includes('moy')) {
            return 'medium';
        }
        if (normalized.includes('faibl') || normalized.includes('faible')) {
            return 'low';
        }

        // default
        return 'low';
    };

    const key = normalize(priority);

    if (key === 'high') {
        return (
            <Badge variant="outline" className={cn(baseClass, 'text-destructive', className)}>
                <ArrowUp className="h-4 w-4 text-destructive" aria-hidden />
                <span className="sr-only">Priorité élevée</span>
            </Badge>
        );
    }

    if (key === 'medium') {
        return (
            <Badge variant="outline" className={cn(baseClass, 'text-sky-600', className)}>
                <Minus className="h-4 w-4 text-sky-600" aria-hidden />
                <span className="sr-only">Priorité moyenne</span>
            </Badge>
        );
    }

    // low
    return (
        <Badge variant="outline" className={cn(baseClass, 'text-muted-foreground', className)}>
            <ArrowDown className="h-4 w-4 text-muted-foreground" aria-hidden />
            <span className="sr-only">Priorité faible</span>
        </Badge>
    );
};

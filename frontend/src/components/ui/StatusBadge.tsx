import { Badge } from './badge';
import { cn } from '../../lib/utils';

interface StatusBadgeProps {
    status: 'a_faire' | 'en_cours' | 'termine';
    className?: string;
}

const statusConfig = {
    a_faire: {
        label: 'À faire',
        className: 'bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700'
    },
    en_cours: {
        label: 'En cours',
        className: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800'
    },
    termine: {
        label: 'Terminé',
        className: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-800'
    }
};

export const StatusBadge = ({ status, className }: StatusBadgeProps) => {
    const config = statusConfig[status];

    return (
        <Badge
            variant="outline"
            className={cn(config.className, 'text-xs font-medium', className)}
        >
            {config.label}
        </Badge>
    );
}; 
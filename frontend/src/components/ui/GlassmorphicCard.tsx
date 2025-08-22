import { Card } from './card';
import { cn } from '../../lib/utils';

interface GlassmorphicCardProps {
    children: React.ReactNode;
    className?: string;
    variant?: 'default' | 'elevated' | 'interactive';
}

const variants = {
    default: 'backdrop-blur-sm bg-card/90 border-2 border-border/40',
    elevated: 'backdrop-blur-md bg-card/95 border-2 border-border/50 shadow-lg',
    interactive: 'backdrop-blur-sm bg-card/90 border-2 border-border/40 hover:bg-card/95 hover:border-border/60 hover:shadow-md'  // Transition supprimée pour un drag and drop instantané
};

export const GlassmorphicCard = ({
    children,
    className,
    variant = 'default',
    ...props
}: GlassmorphicCardProps & React.ComponentProps<typeof Card>) => {
    return (
        <Card
            className={cn(
                'shadow-sm',
                variants[variant],
                className
            )}
            {...props}
        >
            {children}
        </Card>
    );
}; 
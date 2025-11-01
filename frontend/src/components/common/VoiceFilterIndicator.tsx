import { Badge } from '../ui/badge';
import { Mic, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface VoiceFilterIndicatorProps {
    onClear: () => void;
    description?: string;
}

export const VoiceFilterIndicator = ({ onClear, description }: VoiceFilterIndicatorProps) => {
    const { t } = useTranslation();

    return (
        <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
            <Mic className="h-3 w-3 mr-1" />
            {description || t('voice.filter.active')}
            <X
                className="h-3 w-3 ml-1 cursor-pointer hover:text-primary/80"
                onClick={onClear}
                aria-label={t('voice.filter.clear')}
            />
        </Badge>
    );
};

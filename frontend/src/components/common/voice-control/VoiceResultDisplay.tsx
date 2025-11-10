import { CardFilterResponse, VoiceControlResponse } from '@shared/services/voiceControlApi';
import { Badge } from '../../ui/badge';
import { ScrollArea } from '../../ui/scroll-area';

interface VoiceResultDisplayProps {
    result: VoiceControlResponse | CardFilterResponse | null;
    t: (key: string, options?: Record<string, unknown>) => string;
}

const isFilterResponse = (result: VoiceControlResponse | CardFilterResponse | null): result is CardFilterResponse => {
    return Boolean(result && 'response_type' in result && result.response_type === 'filter');
};

export const VoiceResultDisplay = ({ result, t }: VoiceResultDisplayProps) => {
    if (!result) {
        return null;
    }

    if (isFilterResponse(result)) {
        const count = result.cards?.length ?? 0;
        const countLabel = t('voice.filter.resultCount', {
            count,
            defaultValue: count === 1 ? '1 card' : '{{count}} cards'
        });
        return (
            <div className="rounded-md border border-dashed border-muted p-3 text-sm space-y-1">
                <div className="font-medium">{t('voice.filter.previewTitle', { defaultValue: 'Last filter result' })}</div>
                <div className="text-muted-foreground">{result.description}</div>
                <div className="text-xs text-muted-foreground">{countLabel}</div>
            </div>
        );
    }

    return (
        <div className="rounded-md border border-muted/40 p-3 space-y-2 text-sm">
            <div className="flex items-center justify-between">
                <span className="font-medium">{result.title || t('voice.card.noTitle', { defaultValue: 'Untitled card' })}</span>
                {result.priority && (
                    <Badge variant="secondary">{result.priority}</Badge>
                )}
            </div>
            {result.description && (
                <ScrollArea className="max-h-16 text-muted-foreground text-xs">
                    {result.description}
                </ScrollArea>
            )}
            {result.labels && result.labels.length > 0 && (
                <div className="flex flex-wrap gap-1 text-xs text-muted-foreground">
                    {result.labels.map((label) => (
                        <Badge key={label.label_id} variant="outline">
                            #{label.label_id}
                        </Badge>
                    ))}
                </div>
            )}
        </div>
    );
};

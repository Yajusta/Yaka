import { Textarea } from '../../ui/textarea';
import { Trash2 } from 'lucide-react';

interface VoiceTranscriptEditorProps {
    value: string;
    listening: boolean;
    isProcessing: boolean;
    placeholder: string;
    charLimit: number;
    onChange: (value: string) => void;
    onClear: () => void;
}

export const VoiceTranscriptEditor = ({
    value,
    listening,
    isProcessing,
    placeholder,
    charLimit,
    onChange,
    onClear
}: VoiceTranscriptEditorProps) => {
    const canClear = value.trim().length > 0 && !listening && !isProcessing;

    return (
        <div className="space-y-2">
            <div className="relative">
                <Textarea
                    value={value}
                    onChange={(event) => onChange(event.target.value)}
                    readOnly={listening}
                    placeholder={placeholder}
                    className="min-h-[150px] resize-none pr-10"
                />
                {canClear && (
                    <button
                        type="button"
                        onClick={onClear}
                        className="absolute bottom-2 left-2 p-1 text-muted-foreground hover:text-foreground active:bg-accent rounded transition-colors"
                        aria-label="clear transcript"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                )}
            </div>
            <div className="text-xs text-muted-foreground text-right">
                {value.length}/{charLimit}
            </div>
        </div>
    );
};


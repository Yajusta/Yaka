import { Button } from '../../ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../ui/dropdown-menu';
import { Check, Settings } from 'lucide-react';
import { TFunction } from 'i18next';

type RecognitionMode = 'browser' | 'whisper-tiny' | 'whisper-base';
type VoiceMode = 'card_update' | 'filter' | 'auto';

interface VoiceControlModeSelectorProps {
    voiceMode: VoiceMode;
    recognitionMode: RecognitionMode;
    listening: boolean;
    isProcessing: boolean;
    onVoiceModeChange: (mode: VoiceMode) => void;
    onRecognitionModeChange: (mode: RecognitionMode) => void;
    t: TFunction;
}

export const VoiceControlModeSelector = ({
    voiceMode,
    recognitionMode,
    listening,
    isProcessing,
    onVoiceModeChange,
    onRecognitionModeChange,
    t
}: VoiceControlModeSelectorProps) => {
    return (
        <div className="space-y-2">
            <label className="text-sm font-medium">{t('voice.mode.title')}</label>
            <div className="flex flex-wrap items-center gap-4">
                <div className="flex flex-wrap gap-4">
                    {[
                        { value: 'auto', label: t('voice.mode.auto') },
                        { value: 'card_update', label: t('voice.mode.cardUpdate') },
                        { value: 'filter', label: t('voice.mode.filter') }
                    ].map(option => (
                        <label key={option.value} className="flex items-center space-x-2 cursor-pointer">
                            <input
                                type="radio"
                                name="voiceMode"
                                value={option.value}
                                checked={voiceMode === option.value}
                                onChange={(event) => onVoiceModeChange(event.target.value as VoiceMode)}
                                className="w-4 h-4 text-primary focus:ring-primary border-gray-300"
                            />
                            <span className="text-sm">{option.label}</span>
                        </label>
                    ))}
                </div>

                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button
                            variant="outline"
                            size="icon"
                            disabled={listening || isProcessing}
                            aria-label={t('voice.mode.settings', { defaultValue: 'Settings' })}
                        >
                            <Settings className="h-4 w-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="w-56">
                        <DropdownMenuItem
                            onClick={() => onRecognitionModeChange('browser')}
                            className="flex items-center justify-between"
                        >
                            <span>{t('voice.mode.browser')}</span>
                            {recognitionMode === 'browser' && <Check className="h-4 w-4" />}
                        </DropdownMenuItem>
                        {/* Whisper tiny est désactivé pour le moment, laisser l'option centrale */}
                        <DropdownMenuItem
                            onClick={() => onRecognitionModeChange('whisper-base')}
                            className="flex items-center justify-between"
                        >
                            <span>{t('voice.mode.whisperBase')}</span>
                            {recognitionMode === 'whisper-base' && <Check className="h-4 w-4" />}
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </div>
    );
};

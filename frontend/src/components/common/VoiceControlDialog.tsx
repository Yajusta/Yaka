import { VOICE_TRANSCRIPT_LIMIT } from '@shared/config/voice';
import { useToast } from '@shared/hooks/use-toast';
import { useAuth } from '@shared/hooks/useAuth';
import { usePermissions } from '@shared/hooks/usePermissions';
import { useVoiceCapture } from '@shared/hooks/useVoiceCapture';
import { cardService } from '@shared/services/api';
import { CardFilterResponse, VoiceControlResponse, voiceControlService } from '@shared/services/voiceControlApi';
import { Card } from '@shared/types';
import { AlertTriangle, Mic, MicOff, Send, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import CardForm from '../cards/CardForm';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import { VoiceControlModeSelector } from './voice-control/VoiceControlModeSelector';
import { VoiceResultDisplay } from './voice-control/VoiceResultDisplay';
import { VoiceTranscriptEditor } from './voice-control/VoiceTranscriptEditor';
import { VoiceControlWhisperDialog } from './VoiceControlWhisperDialog';

interface VoiceControlDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCardSave?: (card: Card) => void;
    defaultListId?: number;
    onVoiceFilterApply?: (cardIds: number[], description: string) => void;
}

type RecognitionMode = 'browser' | 'whisper-tiny' | 'whisper-base';

type VoiceMode = 'card_update' | 'filter' | 'auto';

export const VoiceControlDialog = ({ open, onOpenChange, onCardSave, defaultListId, onVoiceFilterApply }: VoiceControlDialogProps) => {
    const { t, i18n } = useTranslation();
    const { toast } = useToast();
    const { user: currentUser } = useAuth();
    const permissions = usePermissions(currentUser);

    // Charger le mode de reconnaissance depuis localStorage
    const getInitialRecognitionMode = (): RecognitionMode => {
        try {
            const saved = localStorage.getItem('voiceRecognitionMode');
            if (saved && ['browser', 'whisper-tiny', 'whisper-base'].includes(saved)) {
                return saved as RecognitionMode;
            }
        } catch (error) {
            console.error('Erreur lors du chargement du mode de reconnaissance:', error);
        }
        return 'browser';
    };

    const [recognitionMode, setRecognitionMode] = useState<RecognitionMode>(getInitialRecognitionMode);
    const [isProcessing, setIsProcessing] = useState(false);
    const [result, setResult] = useState<VoiceControlResponse | CardFilterResponse | null>(null);
    const [showCardForm, setShowCardForm] = useState(false);
    const [cardInitialData, setCardInitialData] = useState<any>(null);
    const [cardToEdit, setCardToEdit] = useState<Card | null>(null);
    const [proposedChanges, setProposedChanges] = useState<any>(null);
    const [voiceMode, setVoiceMode] = useState<VoiceMode>('auto');

    // Déterminer si on utilise Whisper
    const isWhisperMode = recognitionMode === 'whisper-tiny' || recognitionMode === 'whisper-base';

    const {
        currentText,
        listening,
        browserSupportsSpeechRecognition,
        startListening,
        stopListening,
        resetTranscript,
        handleManualChange,
        clearTranscripts,
        setManualTranscript
    } = useVoiceCapture({
        open,
        language: i18n.language === 'fr' ? 'fr-FR' : 'en-US',
        autoStart: !isWhisperMode,
        continuous: true,
        disabled: isWhisperMode
    });

    const handleTranscriptChange = (value: string) => {
        handleManualChange(value);
    };

    const handleStartListening = () => {
        startListening({ enableAutoStart: true });
    };

    const handleStopListening = () => {
        stopListening({ disableAutoStart: true });
    };

    const handleModeChange = (mode: RecognitionMode) => {
        stopListening({ disableAutoStart: false });
        try {
            localStorage.setItem('voiceRecognitionMode', mode);
        } catch (error) {
            console.error('Erreur lors de la sauvegarde du mode de reconnaissance:', error);
        }
        setRecognitionMode(mode);
    };

    // Si on utilise Whisper, afficher le dialogue Whisper à la place
    // IMPORTANT: Ce return doit être APRÈS tous les hooks
    if (isWhisperMode) {
        const whisperModel = recognitionMode === 'whisper-tiny' ? 'Xenova/whisper-tiny' : 'Xenova/whisper-base';

        return (
            <VoiceControlWhisperDialog
                open={open}
                onOpenChange={onOpenChange}
                onCardSave={onCardSave}
                defaultListId={defaultListId}
                onSwitchToNative={() => handleModeChange('browser')}
                onSwitchModel={(model) => {
                    const mode = model === 'Xenova/whisper-tiny' ? 'whisper-tiny' : 'whisper-base';
                    handleModeChange(mode);
                }}
                initialModel={whisperModel}
                autoStart={true}
                onVoiceFilterApply={onVoiceFilterApply}
            />
        );
    }

    // Fonction pour convertir la réponse en données initiales pour CardForm
    const convertResponseToInitialData = (response: VoiceControlResponse) => {
        return {
            title: response.title || '',
            description: response.description || '',
            due_date: response.due_date || '',
            priority: response.priority || 'medium',
            assignee_id: response.assignee_id || null,
            label_ids: response.labels?.map(l => l.label_id) || [],
            list_id: response.list_id || undefined,
            checklist: response.checklist?.map((item, index) => ({
                id: item.item_id || undefined,
                text: item.item_name,
                is_done: item.is_done,
                position: index + 1
            })) || []
        };
    };

    const handleSend = async () => {
        const textToSend = currentText;
        if (!textToSend.trim()) {
            return;
        }

        // Stop listening before processing (as requested)
        stopListening({ disableAutoStart: true });
        setIsProcessing(true);

        try {
            const response = await voiceControlService.processTranscript(textToSend, voiceMode);
            setResult(response);

            // Gérer la réponse "unknown"
            if ('response_type' in response && response.response_type === 'unknown') {
                toast({
                    title: t('voice.unknown'),
                    variant: 'destructive'
                });
                onOpenChange(false);
                resetTranscript();
                setManualTranscript('');
                return;
            }

            // Vérifier si la réponse est un filtre (que ce soit en mode "filter" ou "auto")
            if ('response_type' in response && response.response_type === 'filter') {
                const filterResponse = response as CardFilterResponse;
                if (filterResponse.cards && onVoiceFilterApply) {
                    const cardIds = filterResponse.cards.map(card => card.id);
                    onVoiceFilterApply(cardIds, filterResponse.description);
                    toast({
                        title: t('voice.filter.applied'),
                        description: filterResponse.description,
                    });
                }
                onOpenChange(false);
                resetTranscript();
                setManualTranscript('');
                return;
            }

            // Si task_id est null ou vide, ouvrir CardForm en mode création avec les données pré-remplies
            const cardResponse = response as VoiceControlResponse;
            if (!cardResponse.task_id) {
                // Vérifier les permissions pour créer une carte
                if (!permissions.canCreateCard) {
                    toast({
                        title: t('voice.noPermission'),
                        description: t('voice.cannotCreateCard'),
                        variant: 'destructive'
                    });
                    return;
                }

                const initialData = convertResponseToInitialData(cardResponse);
                setCardInitialData(initialData);
                setCardToEdit(null);
                setProposedChanges(null);
                setShowCardForm(true);
            } else {
                // Sinon, charger la carte existante et ouvrir CardForm en mode édition
                try {
                    const existingCard = await cardService.getCard(cardResponse.task_id);

                    if (existingCard) {
                        // Vérifier les permissions pour modifier la carte
                        if (!permissions.canModifyCardContent(existingCard) && !permissions.canModifyCardMetadata(existingCard)) {
                            toast({
                                title: t('voice.noPermission'),
                                description: t('voice.cannotEditCard'),
                                variant: 'destructive'
                            });
                            return;
                        }

                        // Carte existe → Mode édition avec proposedChanges
                        const changes = convertResponseToInitialData(cardResponse);
                        setCardToEdit(existingCard);
                        setProposedChanges(changes);
                        setCardInitialData(null);
                        setShowCardForm(true);
                    } else {
                        // Carte n'existe plus → Mode création avec les données
                        if (!permissions.canCreateCard) {
                            toast({
                                title: t('voice.noPermission'),
                                description: t('voice.cannotCreateCard'),
                                variant: 'destructive'
                            });
                            return;
                        }

                        toast({
                            title: t('voice.cardNotFound'),
                            description: t('voice.cardNotFoundDescription'),
                            variant: 'default'
                        });

                        const initialData = convertResponseToInitialData(cardResponse);
                        setCardInitialData(initialData);
                        setCardToEdit(null);
                        setProposedChanges(null);
                        setShowCardForm(true);
                    }
                } catch (error) {
                    console.error('Erreur lors du chargement de la carte:', error);
                    toast({
                        title: t('common.error'),
                        description: t('voice.cardLoadError'),
                        variant: 'destructive'
                    });
                }
            }

            onOpenChange(false);
            resetTranscript();
            setManualTranscript('');
        } catch (error) {
            console.error('Erreur lors du traitement de l\'instruction vocale:', error);
            toast({
                title: t('common.error'),
                description: t('voice.processingError'),
                variant: 'destructive'
            });
        } finally {
            setIsProcessing(false);
        }
    };

    const handleCancel = () => {
        stopListening({ disableAutoStart: true });
        onOpenChange(false);
        resetTranscript();
        setManualTranscript('');
    };

    const handleClear = () => {
        clearTranscripts();
    };

    return (
        <>
            <Dialog open={open} onOpenChange={onOpenChange}>
                <DialogContent className="sm:max-w-[600px]">
                    <DialogHeader>
                        <DialogTitle>{t('voice.title')}</DialogTitle>
                        <DialogDescription>
                            {t('voice.description')}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4">
                        <VoiceTranscriptEditor
                            value={currentText}
                            listening={listening}
                            isProcessing={isProcessing}
                            placeholder={t('voice.placeholder')}
                            charLimit={VOICE_TRANSCRIPT_LIMIT}
                            onChange={handleTranscriptChange}
                            onClear={handleClear}
                        />

                        <VoiceControlModeSelector
                            t={t}
                            voiceMode={voiceMode}
                            recognitionMode={recognitionMode}
                            listening={listening}
                            isProcessing={isProcessing}
                            onVoiceModeChange={setVoiceMode}
                            onRecognitionModeChange={handleModeChange}
                        />

                        {/* Indicateur d'écoute */}
                        {listening && (
                            <div className="flex items-center justify-center space-x-2 text-primary">
                                <div className="flex space-x-1">
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                                <span className="text-sm font-medium">{t('voice.listening')}</span>
                            </div>
                        )}

                        {/* Indicateur de traitement */}
                        {isProcessing && (
                            <div className="flex items-center justify-center space-x-2 text-primary">
                                <div className="flex space-x-1">
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                                <span className="text-sm font-medium">{t('voice.processing')}</span>
                            </div>
                        )}

                        <VoiceResultDisplay result={result} t={t} />

                        {/* Message d'incompatibilité si mode navigateur sélectionné mais non supporté */}
                        {!browserSupportsSpeechRecognition && (
                            <div className="flex items-center gap-2 text-sm text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-950/20 rounded-lg p-3">
                                <AlertTriangle className="h-4 w-4" />
                                <div>
                                    <div className="font-medium">{t('voice.notSupportedBrowser')}</div>
                                    <div className="text-xs mt-1">{t('voice.notSupportedDescription')}</div>
                                </div>
                            </div>
                        )}

                        {/* Boutons d'action */}
                        <div className="flex justify-between gap-2">
                            <div className="flex gap-2 items-center">
                                {!listening ? (
                                    <Button
                                        onClick={handleStartListening}
                                        variant="default"
                                        className="bg-primary hover:bg-primary/90"
                                        disabled={!browserSupportsSpeechRecognition || isProcessing}
                                    >
                                        <Mic className="h-4 w-4 mr-2" />
                                        {t('voice.start')}
                                    </Button>
                                ) : (
                                    <Button
                                        onClick={handleStopListening}
                                        variant="destructive"
                                        disabled={isProcessing}
                                    >
                                        <MicOff className="h-4 w-4 mr-2" />
                                        {t('voice.stop')}
                                    </Button>
                                )}
                            </div>

                            <div className="flex gap-2">
                                <Button
                                    onClick={handleCancel}
                                    variant="outline"
                                    disabled={isProcessing}
                                >
                                    <X className="h-4 w-4 mr-2" />
                                    {t('common.cancel')}
                                </Button>
                                <Button
                                    onClick={handleSend}
                                    disabled={!currentText.trim() || isProcessing}
                                    className="bg-primary hover:bg-primary/90"
                                >
                                    <Send className="h-4 w-4 mr-2" />
                                    {isProcessing ? t('voice.processing') : t('voice.send')}
                                </Button>
                            </div>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            {/* CardForm pour créer/modifier une carte */}
            {showCardForm && (
                <CardForm
                    card={cardToEdit}
                    isOpen={showCardForm}
                    onClose={() => {
                        setShowCardForm(false);
                        setCardInitialData(null);
                        setCardToEdit(null);
                        setProposedChanges(null);
                    }}
                    onSave={(card) => {
                        setShowCardForm(false);
                        setCardInitialData(null);
                        setCardToEdit(null);
                        setProposedChanges(null);
                        if (onCardSave) {
                            onCardSave(card);
                        }
                    }}
                    defaultListId={(result && 'list_id' in result && result.list_id != null) ? result.list_id : defaultListId}
                    initialData={cardInitialData}
                    proposedChanges={proposedChanges}
                />
            )}
        </>
    );
};

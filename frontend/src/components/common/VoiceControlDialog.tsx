import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Mic, MicOff, Send, X, AlertTriangle, Settings, Check, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import { voiceControlService, VoiceControlResponse, CardFilterResponse } from '@shared/services/voiceControlApi';
import CardForm from '../cards/CardForm';
import { Card } from '@shared/types';
import { cardService } from '@shared/services/api';
import { useToast } from '@shared/hooks/use-toast';
import { useAuth } from '@shared/hooks/useAuth';
import { usePermissions } from '@shared/hooks/usePermissions';
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

    const {
        transcript,
        listening,
        resetTranscript,
        browserSupportsSpeechRecognition
    } = useSpeechRecognition();

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
    const [shouldAutoRestart, setShouldAutoRestart] = useState(false);
    const [useContinuousMode] = useState(true);
    const [voiceMode, setVoiceMode] = useState<VoiceMode>('auto');
    const [manualTranscript, setManualTranscript] = useState('');

    // Gérer le changement de mode
    const handleModeChange = (mode: RecognitionMode) => {
        if (listening) {
            SpeechRecognition.abortListening();
        }
        setShouldAutoRestart(false);
        // Sauvegarder le mode dans localStorage
        try {
            localStorage.setItem('voiceRecognitionMode', mode);
        } catch (error) {
            console.error('Erreur lors de la sauvegarde du mode de reconnaissance:', error);
        }
        // Ne pas fermer le dialogue lors du changement de mode
        setRecognitionMode(mode);
    };

    // Déterminer si on utilise Whisper
    const isWhisperMode = recognitionMode === 'whisper-tiny' || recognitionMode === 'whisper-base';

    // Handle manual transcript editing
    const handleTranscriptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setManualTranscript(e.target.value);
    };

    // Get the current text to display
    const getCurrentText = () => {
        // When listening, combine manual text with live transcript
        if (listening && transcript.trim()) {
            // If manual text exists, append space + transcript
            if (manualTranscript.trim()) {
                return manualTranscript.trim() + ' ' + transcript;
            } else {
                // If no manual text, use transcript directly
                return transcript;
            }
        }

        // When not listening, use only manual transcript (transcript has been copied to manual)
        return manualTranscript;
    };

    // Update language when it changes
    useEffect(() => {
        const lang = i18n.language === 'fr' ? 'fr-FR' : 'en-US';
        const recognition = SpeechRecognition.getRecognition();
        if (recognition) {
            recognition.lang = lang;
        }
    }, [i18n.language]);

    // Auto-restart logic for non-continuous mode (same as VoiceInputDialog.tsx)
    useEffect(() => {
        if (!useContinuousMode && !isWhisperMode) {
            const recognition = SpeechRecognition.getRecognition();
            if (recognition) {
                const handleEnd = () => {
                    // Auto-restart if needed
                    if (shouldAutoRestart && !listening && open) {
                        setTimeout(() => {
                            if (shouldAutoRestart && open) {
                                SpeechRecognition.startListening({
                                    continuous: false,
                                    language: i18n.language === 'fr' ? 'fr-FR' : 'en-US'
                                });
                            }
                        }, 100);
                    }
                };

                recognition.addEventListener('end', handleEnd);
                return () => {
                    recognition.removeEventListener('end', handleEnd);
                };
            }
        }
    }, [shouldAutoRestart, listening, useContinuousMode, i18n.language, open, isWhisperMode]);

    // Stop listening when dialog closes
    useEffect(() => {
        if (!open) {
            setShouldAutoRestart(false);
            SpeechRecognition.stopListening();
        } else {
            setShouldAutoRestart(false);
        }
    }, [open]);

    // Copy transcript to manual transcript when listening stops
    useEffect(() => {
        if (!listening && transcript) {
            // Concatene le nouveau transcript avec le texte manuel existant
            setManualTranscript(prev => {
                const combined = prev ? prev + ' ' + transcript : transcript;
                return combined.trim();
            });
        }
    }, [listening, transcript]);

    // Auto-start listening when dialog opens
    useEffect(() => {
        if (open && browserSupportsSpeechRecognition && !listening && !isWhisperMode) {
            const timer = setTimeout(() => {
                startListening();
            }, 300);
            return () => clearTimeout(timer);
        }
    }, [open, browserSupportsSpeechRecognition]); // Removed 'listening' from dependencies

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

    const startListening = () => {
        setShouldAutoRestart(true);

        // Always reset when starting to listen
        if (!listening) {
            resetTranscript();
        }

        try {
            SpeechRecognition.startListening({
                continuous: useContinuousMode,
                language: i18n.language === 'fr' ? 'fr-FR' : 'en-US'
            });
        } catch (error: any) {
            console.error('Error starting speech recognition:', error.message);
        }
    };

    const stopListening = () => {
        setShouldAutoRestart(false);

        try {
            SpeechRecognition.stopListening();
        } catch (error: any) {
            console.error('Error stopping speech recognition:', error.message);
        }
    };

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
        const textToSend = getCurrentText();
        if (!textToSend.trim()) {
            return;
        }

        // Stop listening before processing (as requested)
        stopListening();
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
        stopListening();
        onOpenChange(false);
        resetTranscript();
        setManualTranscript('');
    };

    const handleClear = () => {
        if (listening) {
            resetTranscript();
        } else {
            setManualTranscript('');
        }
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
                        {/* Zone de texte éditable */}
                        <div className="space-y-2">
                            <div className="relative">
                                <Textarea
                                    value={getCurrentText()}
                                    onChange={handleTranscriptChange}
                                    readOnly={listening}
                                    placeholder={t('voice.placeholder')}
                                    className="min-h-[150px] resize-none pr-10"
                                />
                                {getCurrentText().trim() && !listening && !isProcessing && (
                                    <button
                                        onClick={handleClear}
                                        className="absolute bottom-2 left-2 p-1 text-muted-foreground hover:text-foreground active:bg-accent rounded transition-colors"
                                        aria-label={t('voice.clear')}
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                )}
                            </div>
                            <div className="text-xs text-muted-foreground text-right">
                                {getCurrentText().length}/500
                            </div>
                        </div>

                        {/* Sélection du mode vocal */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium">{t('voice.mode.title')}</label>
                            <div className="flex gap-4">
                                <label className="flex items-center space-x-2 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="voiceMode"
                                        value="auto"
                                        checked={voiceMode === 'auto'}
                                        onChange={(e) => setVoiceMode(e.target.value as VoiceMode)}
                                        className="w-4 h-4 text-primary focus:ring-primary border-gray-300"
                                    />
                                    <span className="text-sm">{t('voice.mode.auto')}</span>
                                </label>
                                <label className="flex items-center space-x-2 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="voiceMode"
                                        value="card_update"
                                        checked={voiceMode === 'card_update'}
                                        onChange={(e) => setVoiceMode(e.target.value as 'card_update')}
                                        className="w-4 h-4 text-primary focus:ring-primary border-gray-300"
                                    />
                                    <span className="text-sm">{t('voice.mode.cardUpdate')}</span>
                                </label>
                                <label className="flex items-center space-x-2 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="voiceMode"
                                        value="filter"
                                        checked={voiceMode === 'filter'}
                                        onChange={(e) => setVoiceMode(e.target.value as 'filter')}
                                        className="w-4 h-4 text-primary focus:ring-primary border-gray-300"
                                    />
                                    <span className="text-sm">{t('voice.mode.filter')}</span>
                                </label>
                            </div>
                        </div>

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
                                        onClick={startListening}
                                        variant="default"
                                        className="bg-primary hover:bg-primary/90"
                                        disabled={!browserSupportsSpeechRecognition || isProcessing}
                                    >
                                        <Mic className="h-4 w-4 mr-2" />
                                        {t('voice.start')}
                                    </Button>
                                ) : (
                                    <Button
                                        onClick={stopListening}
                                        variant="destructive"
                                        disabled={isProcessing}
                                    >
                                        <MicOff className="h-4 w-4 mr-2" />
                                        {t('voice.stop')}
                                    </Button>
                                )}

                                {/* Menu de paramètres */}
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            disabled={listening || isProcessing}
                                        >
                                            <Settings className="h-4 w-4" />
                                        </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="start" className="w-56">
                                        <DropdownMenuItem
                                            onClick={() => handleModeChange('browser')}
                                            className="flex items-center justify-between"
                                        >
                                            <span>{t('voice.mode.browser')}</span>
                                            {recognitionMode === 'browser' && <Check className="h-4 w-4" />}
                                        </DropdownMenuItem>
                                        {/* <DropdownMenuItem
                                            onClick={() => handleModeChange('whisper-tiny')}
                                            className="flex items-center justify-between"
                                        >
                                            <span>{t('voice.mode.whisperTiny')}</span>
                                            {recognitionMode === 'whisper-tiny' && <Check className="h-4 w-4" />}
                                        </DropdownMenuItem> */}
                                        <DropdownMenuItem
                                            onClick={() => handleModeChange('whisper-base')}
                                            className="flex items-center justify-between"
                                        >
                                            <span>{t('voice.mode.whisperBase')}</span>
                                            {(recognitionMode as RecognitionMode) === 'whisper-base' && <Check className="h-4 w-4" />}
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
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
                                    disabled={!getCurrentText().trim() || isProcessing}
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

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Mic, MicOff, Send, X, AlertTriangle, Settings, Check, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import { voiceControlService, VoiceControlResponse } from '@shared/services/voiceControlApi';
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
}

type RecognitionMode = 'browser' | 'whisper-tiny' | 'whisper-base';

export const VoiceControlDialog = ({ open, onOpenChange, onCardSave, defaultListId }: VoiceControlDialogProps) => {
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
    const [result, setResult] = useState<VoiceControlResponse | null>(null);
    const [showCardForm, setShowCardForm] = useState(false);
    const [cardInitialData, setCardInitialData] = useState<any>(null);
    const [cardToEdit, setCardToEdit] = useState<Card | null>(null);
    const [proposedChanges, setProposedChanges] = useState<any>(null);
    const [shouldAutoRestart, setShouldAutoRestart] = useState(false);
    const [useContinuousMode] = useState(true);

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
            />
        );
    }

    const startListening = () => {
        setShouldAutoRestart(true);

        // Reset transcript only if not already listening (same as VoiceInputDialog.tsx)
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
        if (!transcript.trim()) {
            return;
        }

        // Stop listening before processing (as requested)
        stopListening();
        setIsProcessing(true);

        try {
            const response = await voiceControlService.processTranscript(transcript);
            setResult(response);

            // Si task_id est null ou vide, ouvrir CardForm en mode création avec les données pré-remplies
            if (!response.task_id) {
                // Vérifier les permissions pour créer une carte
                if (!permissions.canCreateCard) {
                    toast({
                        title: t('voice.noPermission'),
                        description: t('voice.cannotCreateCard'),
                        variant: 'destructive'
                    });
                    return;
                }

                const initialData = convertResponseToInitialData(response);
                setCardInitialData(initialData);
                setCardToEdit(null);
                setProposedChanges(null);
                setShowCardForm(true);
            } else {
                // Sinon, charger la carte existante et ouvrir CardForm en mode édition
                try {
                    const existingCard = await cardService.getCard(response.task_id);

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
                        const changes = convertResponseToInitialData(response);
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

                        const initialData = convertResponseToInitialData(response);
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
                                    value={transcript}
                                    readOnly
                                    placeholder={t('voice.placeholder')}
                                    className="min-h-[150px] resize-none pr-10"
                                />
                                {transcript.trim() && !listening && !isProcessing && (
                                    <button
                                        onClick={resetTranscript}
                                        className="absolute bottom-2 left-2 p-1 text-muted-foreground hover:text-foreground active:bg-accent rounded transition-colors"
                                        aria-label={t('voice.clear')}
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                )}
                            </div>
                            <div className="text-xs text-muted-foreground text-right">
                                {transcript.length}/500
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
                                    disabled={!transcript.trim() || isProcessing}
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
                    defaultListId={result?.list_id || defaultListId}
                    initialData={cardInitialData}
                    proposedChanges={proposedChanges}
                />
            )}
        </>
    );
};

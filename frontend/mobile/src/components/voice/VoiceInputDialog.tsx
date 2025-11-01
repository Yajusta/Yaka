import { useEffect, useState } from 'react';
import { Mic, MicOff, Send, X, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import { voiceControlService, VoiceControlResponse, CardFilterResponse } from '@shared/services/voiceControlApi';
import { Card } from '@shared/types';
import { cardService } from '@shared/services/api';
import { useAuth } from '@shared/hooks/useAuth';
import { usePermissions } from '@shared/hooks/usePermissions';
import { useToast } from '@shared/hooks/use-toast';
import CardDetail from '../card/CardDetail';

interface VoiceInputDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCardSave?: (card: any) => void;
    defaultListId?: number;
    onVoiceFilterApply?: (cardIds: number[], description: string) => void;
}

type VoiceMode = 'card_update' | 'filter' | 'auto';

const VoiceInputDialog = ({ open, onOpenChange, onCardSave, defaultListId, onVoiceFilterApply }: VoiceInputDialogProps) => {
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

    const [shouldAutoRestart, setShouldAutoRestart] = useState(false);
    const [useContinuousMode] = useState(true);
    const [isProcessing, setIsProcessing] = useState(false);
    const [showCardDetail, setShowCardDetail] = useState(false);
    const [cardToEdit, setCardToEdit] = useState<Card | null>(null);
    const [cardInitialData, setCardInitialData] = useState<any>(null);
    const [proposedChanges, setProposedChanges] = useState<any>(null);
    const [voiceMode, setVoiceMode] = useState<VoiceMode>('auto');
    const [manualTranscript, setManualTranscript] = useState('');

    // Auto-restart logic for non-continuous mode (same as VoiceRecognitionTest.tsx)
    useEffect(() => {
        if (!useContinuousMode) {
            const recognition = SpeechRecognition.getRecognition();
            if (recognition) {
                const handleEnd = () => {
                    // Auto-restart if needed
                    if (shouldAutoRestart && !listening) {
                        setTimeout(() => {
                            if (shouldAutoRestart) {
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
    }, [shouldAutoRestart, listening, useContinuousMode, i18n.language]);

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
        if (open && browserSupportsSpeechRecognition && !listening) {
            const timer = setTimeout(() => {
                startListening();
            }, 300);
            return () => clearTimeout(timer);
        }
    }, [open, browserSupportsSpeechRecognition]); // Removed 'listening' from dependencies

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

    // Copy transcript to manual transcript when listening stops
    useEffect(() => {
        if (!listening && transcript) {
            // Concatenate the new transcript with the existing manual text
            setManualTranscript(prev => {
                const combined = prev ? prev + ' ' + transcript : transcript;
                return combined.trim();
            });
        }
    }, [listening, transcript]);

    const startListening = () => {
        setShouldAutoRestart(true);

        // Reset transcript only if not already listening (same as VoiceRecognitionTest.tsx)
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

    // Function to convert response to initial data for CardDetail (from VoiceInputDialogOld.tsx)
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

            // Handle "unknown" response type
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

            // Check if response is a filter (either in 'filter' or 'auto' mode)
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

            // If task_id is null or empty, open CardDetail in creation mode with pre-filled data
            const cardResponse = response as VoiceControlResponse;
            if (!cardResponse.task_id) {
                // Check permissions to create a card
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
                setShowCardDetail(true);
            } else {
                // Otherwise, load existing card and open CardDetail in edit mode
                try {
                    const existingCard = await cardService.getCard(cardResponse.task_id);

                    if (existingCard) {
                        // Check permissions to edit card
                        if (!permissions.canModifyCardContent(existingCard) && !permissions.canModifyCardMetadata(existingCard)) {
                            toast({
                                title: t('voice.noPermission'),
                                description: t('voice.cannotEditCard'),
                                variant: 'destructive'
                            });
                            return;
                        }

                        // Card exists → Edit mode with proposedChanges
                        const changes = convertResponseToInitialData(cardResponse);
                        setCardToEdit(existingCard);
                        setProposedChanges(changes);
                        setCardInitialData(null);
                        setShowCardDetail(true);
                    } else {
                        // Card doesn't exist anymore → Creation mode with data
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
                        setShowCardDetail(true);
                    }
                } catch (error) {
                    console.error('Error loading card:', error);
                    toast({
                        title: t('common.error'),
                        description: t('voice.cardLoadError'),
                        variant: 'destructive'
                    });
                }
            }

            // Don't close the voice dialog here - let CardDetail handle it
            // onOpenChange(false);
            resetTranscript();
            setManualTranscript('');
        } catch (error) {
            console.error('Error processing voice command:', error);
            toast({
                title: t('common.error'),
                description: t('voice.processingError'),
                variant: 'destructive'
            });
        } finally {
            setIsProcessing(false);
        }
    };

    const handleClear = () => {
        resetTranscript();
        setManualTranscript('');
    };

  const handleCardSave = (savedCard: Card) => {
    setShowCardDetail(false);
    setCardToEdit(null);
    setCardInitialData(null);
    setProposedChanges(null);
    onOpenChange(false);

    if (onCardSave) {
      onCardSave(savedCard);
    }
  };

  const handleCardClose = () => {
    setShowCardDetail(false);
    setCardToEdit(null);
    setCardInitialData(null);
    setProposedChanges(null);
    // Close also voice dialog to return to main page
    onOpenChange(false);
  };

    const handleCancel = () => {
        stopListening();
        onOpenChange(false);
        resetTranscript();
        setManualTranscript('');
    };

    if (!open) return null;

    if (!browserSupportsSpeechRecognition) {
        return (
            <>
                {/* Backdrop */}
                <div
                    className="fixed inset-0 bg-black/50 z-40 animate-fade-in"
                    onClick={() => onOpenChange(false)}
                />

                {/* Full screen page */}
                <div className="fixed inset-0 bg-background z-50 overflow-y-auto animate-slide-up">
                    {/* Header */}
                    <div className="sticky top-0 bg-card border-b-2 border-border z-10">
                        <div className="flex items-center justify-between p-4" style={{ paddingTop: 'calc(1rem + env(safe-area-inset-top))' }}>
                            <button
                                onClick={() => onOpenChange(false)}
                                className="p-2 -ml-2 text-muted-foreground hover:text-foreground active:bg-accent rounded-lg transition-colors"
                                aria-label={t('common.close')}
                            >
                                <X className="w-6 h-6" />
                            </button>

                            <div className="flex items-center gap-2">
                                <Mic className="w-5 h-5 text-primary" />
                                <h1 className="text-lg font-bold text-foreground">{t('voice.title')}</h1>
                            </div>

                            {/* Empty space for balance */}
                            <div className="w-10" />
                        </div>
                    </div>

                    {/* Content */}
                    <div className="pb-safe p-4">
                        <div className="bg-destructive/10 border-2 border-destructive rounded-lg p-6">
                            <h2 className="text-2xl font-bold text-destructive mb-2">{t('voice.notSupported')}</h2>
                            <p>{t('voice.notSupportedDescription')}</p>
                        </div>
                    </div>
                </div>
            </>
        );
    }

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 z-40 animate-fade-in"
                onClick={handleCancel}
            />

            {/* Modal */}
            <div className="fixed inset-0 bg-background z-50 overflow-y-auto animate-slide-up" style={{ display: showCardDetail ? 'none' : 'block' }}>
                {/* Header */}
                <div className="sticky top-0 bg-card border-b-2 border-border z-10">
                    <div className="flex items-center justify-between p-4" style={{ paddingTop: 'calc(1rem + env(safe-area-inset-top))' }}>
                        <button
                            onClick={handleCancel}
                            className="p-2 -ml-2 text-muted-foreground hover:text-foreground active:bg-accent rounded-lg transition-colors"
                            aria-label={t('common.close')}
                        >
                            <X className="w-6 h-6" />
                        </button>

                        <div className="flex items-center gap-2">
                            <Mic className="w-5 h-5 text-primary" />
                            <h1 className="text-lg font-bold text-foreground">{t('voice.title')}</h1>
                        </div>

                        {/* Empty space for balance */}
                        <div className="w-10" />
                    </div>

                    {/* Subtitle */}
                    <div className="px-4 pb-3">
                        <p className="text-sm text-muted-foreground text-center">
                            {t('voice.description')}
                        </p>
                    </div>
                </div>

                {/* Content */}
                <div className="pb-safe p-4 space-y-4">
                    {/* Text area with trash icon */}
                    <div className="space-y-2">
                        <div className="relative">
                            <textarea
                                value={getCurrentText()}
                                onChange={handleTranscriptChange}
                                readOnly={listening}
                                placeholder={t('voice.placeholder')}
                                className="w-full min-h-[150px] p-4 bg-background border-2 border-border rounded-lg resize-none font-mono pr-12"
                            />
                            {getCurrentText().trim() && !listening && !isProcessing && (
                                <button
                                    onClick={handleClear}
                                    className="absolute bottom-4 left-4 p-1 text-muted-foreground hover:text-foreground active:bg-accent rounded transition-colors"
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

                    {/* Voice mode selection */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium">{t('voice.mode.title')}</label>
                        <select
                            value={voiceMode}
                            onChange={(e) => setVoiceMode(e.target.value as VoiceMode)}
                            className="w-full p-3 bg-background border-2 border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent appearance-none"
                        >
                            <option value="auto">{t('voice.mode.auto')}</option>
                            <option value="card_update">{t('voice.mode.cardUpdate')}</option>
                            <option value="filter">{t('voice.mode.filter')}</option>
                        </select>
                    </div>

                    {/* Listening indicator */}
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

                    {/* Processing indicator */}
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

                    {/* Action buttons */}
                    <div className="flex justify-between gap-2 pt-4">
                        <div className="flex gap-2">
                            {!listening ? (
                                <button
                                    onClick={startListening}
                                    disabled={isProcessing}
                                    className="btn-touch bg-green-500 hover:bg-green-600 text-white hover:text-white font-medium rounded-lg transition-colors shadow-lg flex items-center justify-center gap-2 px-6 py-3"
                                >
                                    <Mic className="w-5 h-5" />
                                    {t('voice.start')}
                                </button>
                            ) : (
                                <button
                                    onClick={stopListening}
                                    disabled={isProcessing}
                                    className="btn-touch bg-destructive text-destructive-foreground font-medium rounded-lg hover:bg-destructive/90 active:bg-destructive/80 transition-colors flex items-center justify-center gap-2 px-6 py-3"
                                >
                                    <MicOff className="w-5 h-5" />
                                    {t('voice.stop')}
                                </button>
                            )}
                        </div>

                        <div className="flex gap-2">
                            <button
                                onClick={handleSend}
                                disabled={!transcript.trim() || isProcessing}
                                className="btn-touch bg-primary text-primary-foreground font-medium rounded-lg hover:bg-primary/90 active:bg-primary/80 transition-colors flex items-center justify-center gap-2 px-6 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <Send className="w-5 h-5" />
                                {isProcessing ? t('voice.processing') : t('voice.send')}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* CardDetail modal for creating/editing card */}
            {showCardDetail && (
                <CardDetail
                    card={cardToEdit || {
                        id: 0,
                        title: '',
                        description: '',
                        priority: 'medium',
                        assignee_id: null,
                        label_id: null,
                        colonne: '',
                        list_id: defaultListId || 0,
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString(),
                        labels: [],
                        items: []
                    }}
                    isOpen={showCardDetail}
                    onClose={handleCardClose}
                    onSave={handleCardSave}
                    initialData={cardInitialData}
                    proposedChanges={proposedChanges}
                />
            )}
        </>
    );
};

export default VoiceInputDialog;
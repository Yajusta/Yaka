import { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Mic, MicOff, Send, X, AlertTriangle, Settings, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { voiceControlService, VoiceControlResponse } from '../../services/voiceControlApi';
import CardForm from '../cards/CardForm';
import { Card } from '../../types';
import { cardService } from '../../services/api';
import { useToast } from '../../hooks/use-toast';
import { useAuth } from '../../hooks/useAuth';
import { usePermissions } from '../../hooks/usePermissions';
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
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState('');
    const [isSupported, setIsSupported] = useState(true);
    const [isProcessing, setIsProcessing] = useState(false);
    const [result, setResult] = useState<VoiceControlResponse | null>(null);
    const [showCardForm, setShowCardForm] = useState(false);
    const [cardInitialData, setCardInitialData] = useState<any>(null);
    const [cardToEdit, setCardToEdit] = useState<Card | null>(null);
    const [proposedChanges, setProposedChanges] = useState<any>(null);
    const recognitionRef = useRef<any>(null);
    const isListeningRef = useRef<boolean>(false);

    // Stocker le mode actuel dans un ref pour éviter les problèmes de narrowing TypeScript
    const currentModeRef = useRef<RecognitionMode>(recognitionMode);
    currentModeRef.current = recognitionMode;

    // Gérer le changement de mode
    const handleModeChange = (mode: RecognitionMode) => {
        if (isListening) {
            stopListening();
        }
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

    // TOUS les useEffect doivent être appelés AVANT tout return conditionnel
    useEffect(() => {
        // Vérifier si l'API Web Speech est disponible
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

        if (!SpeechRecognition) {
            setIsSupported(false);
            return;
        }

        // Initialiser la reconnaissance vocale seulement si elle n'existe pas déjà
        if (!recognitionRef.current) {
            const recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;

            recognition.onresult = (event: any) => {
                // Ne traiter les résultats que si on est encore en train d'écouter
                if (!isListeningRef.current) {
                    return;
                }

                let interimTranscript = '';
                let finalTranscript = '';

                // Parcourir tous les résultats pour reconstruire le transcript complet
                for (let i = 0; i < event.results.length; i++) {
                    const transcriptPart = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcriptPart + ' ';
                    } else {
                        interimTranscript += transcriptPart;
                    }
                }

                // Remplacer le transcript par la combinaison des résultats finaux et intermédiaires
                setTranscript(finalTranscript + interimTranscript);
            };

            recognition.onerror = (event: any) => {
                console.error('Speech recognition error:', event.error);
                if (event.error === 'no-speech') {
                    // Pas de parole détectée, continuer l'écoute
                    return;
                }
                isListeningRef.current = false;
                setIsListening(false);
            };

            recognition.onend = () => {
                // Vérifier avec le ref pour avoir la valeur actuelle, pas celle du closure
                if (isListeningRef.current) {
                    // Redémarrer automatiquement si on est toujours en mode écoute
                    try {
                        recognition.start();
                    } catch (e) {
                        console.error('Error restarting recognition:', e);
                        isListeningRef.current = false;
                        setIsListening(false);
                    }
                }
            };

            recognitionRef.current = recognition;
        }

        // Mettre à jour la langue à chaque fois que i18n.language change
        if (recognitionRef.current) {
            const lang = i18n.language === 'fr' ? 'fr-FR' : 'en-US';
            recognitionRef.current.lang = lang;
        }

        return () => {
            // Ne pas réinitialiser le ref lors du cleanup
            if (recognitionRef.current) {
                try {
                    recognitionRef.current.stop();
                } catch (e) {
                    // Ignorer l'erreur si déjà arrêté
                }
            }
        };
    }, [i18n.language]);

    // Arrêter l'écoute quand le dialogue se ferme
    useEffect(() => {
        if (!open && isListening) {
            stopListening();
        }
    }, [open]);

    // Démarrer automatiquement l'écoute quand le dialogue s'ouvre
    useEffect(() => {
        if (open && isSupported && !isListening && !isWhisperMode) {
            // Petit délai pour s'assurer que le dialogue est complètement ouvert
            const timer = setTimeout(() => {
                startListening();
            }, 300);
            return () => clearTimeout(timer);
        }
    }, [open, isSupported, isWhisperMode]);

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
        if (recognitionRef.current && !isListeningRef.current) {
            setTranscript('');
            try {
                recognitionRef.current.start();
                isListeningRef.current = true;
                setIsListening(true);
            } catch (e) {
                console.error('Error starting recognition:', e);
                isListeningRef.current = false;
                setIsListening(false);
            }
        }
    };

    const stopListening = () => {
        // Mettre à jour le ref AVANT d'arrêter pour éviter le redémarrage automatique
        isListeningRef.current = false;
        setIsListening(false);

        if (recognitionRef.current) {
            try {
                recognitionRef.current.stop();
            } catch (e) {
                console.error('Error stopping recognition:', e);
            }
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

        // Arrêter l'écoute en mettant à jour le ref AVANT d'arrêter la reconnaissance
        isListeningRef.current = false;
        setIsListening(false);

        if (recognitionRef.current) {
            try {
                recognitionRef.current.stop();
            } catch (e) {
                console.error('Error stopping recognition:', e);
            }
        }

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
            setTranscript('');
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
        setTranscript('');
    };

    const handleTranscriptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setTranscript(e.target.value);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        // Si Enter est pressé sans Shift et qu'il y a du texte, envoyer
        if (e.key === 'Enter' && !e.shiftKey && transcript.trim() && !isProcessing) {
            e.preventDefault();
            // Arrêter l'écoute si elle est en cours avant d'envoyer
            if (isListening) {
                stopListening();
            }
            handleSend();
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
                            <Textarea
                                value={transcript}
                                onChange={handleTranscriptChange}
                                onKeyDown={handleKeyDown}
                                placeholder={t('voice.placeholder')}
                                className="min-h-[150px] resize-none"
                                disabled={isProcessing}
                                readOnly={isListening}
                                maxLength={500}
                            />
                            <div className="text-xs text-muted-foreground text-right">
                                {transcript.length}/500
                            </div>
                        </div>

                        {/* Indicateur d'écoute */}
                        {isListening && (
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
                        {!isSupported && (
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
                                {!isListening ? (
                                    <Button
                                        onClick={startListening}
                                        variant="default"
                                        className="bg-primary hover:bg-primary/90"
                                        disabled={!isSupported || isProcessing}
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
                                            disabled={isListening || isProcessing}
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
                                            {currentModeRef.current === 'browser' && <Check className="h-4 w-4" />}
                                        </DropdownMenuItem>
                                        {/* <DropdownMenuItem
                                            onClick={() => handleModeChange('whisper-tiny')}
                                            className="flex items-center justify-between"
                                        >
                                            <span>{t('voice.mode.whisperTiny')}</span>
                                            {currentModeRef.current === 'whisper-tiny' && <Check className="h-4 w-4" />}
                                        </DropdownMenuItem> */}
                                        <DropdownMenuItem
                                            onClick={() => handleModeChange('whisper-base')}
                                            className="flex items-center justify-between"
                                        >
                                            <span>{t('voice.mode.whisperBase')}</span>
                                            {currentModeRef.current === 'whisper-base' && <Check className="h-4 w-4" />}
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

import { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Mic, MicOff, Send, X, AlertTriangle, Settings, Check } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { useTranslation } from 'react-i18next';
import { voiceControlService, VoiceControlResponse, CardFilterResponse } from '@shared/services/voiceControlApi';
import CardForm from '../cards/CardForm';
import { Card } from '@shared/types';
import { cardService } from '@shared/services/api';
import { useToast } from '@shared/hooks/use-toast';
import { useAuth } from '@shared/hooks/useAuth';
import { usePermissions } from '@shared/hooks/usePermissions';
import { pipeline, env } from '@xenova/transformers';

// Configuration Transformers.js
env.allowLocalModels = false;
env.useBrowserCache = true;
env.backends.onnx.wasm.numThreads = 1;

type WhisperModel = 'Xenova/whisper-tiny' | 'Xenova/whisper-base';

// Cache global pour les modèles Whisper (partagé entre toutes les instances)
const whisperModelsCache: { [key: string]: any } = {};

interface VoiceControlWhisperDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCardSave?: (card: Card) => void;
    defaultListId?: number;
    onSwitchToNative?: () => void;
    onSwitchModel?: (model: WhisperModel) => void;
    initialModel?: WhisperModel;
    autoStart?: boolean;
    onVoiceFilterApply?: (cardIds: number[], description: string) => void;
}

export const VoiceControlWhisperDialog = ({
    open,
    onOpenChange,
    onCardSave,
    defaultListId,
    onSwitchToNative,
    onSwitchModel,
    initialModel = 'Xenova/whisper-base',
    autoStart = false,
    onVoiceFilterApply
}: VoiceControlWhisperDialogProps) => {
    const { t, i18n } = useTranslation();
    const { toast } = useToast();
    const { user: currentUser } = useAuth();
    const permissions = usePermissions(currentUser);

    const [isRecording, setIsRecording] = useState(false);
    const [transcript, setTranscript] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [isLoadingModel, setIsLoadingModel] = useState(true);
    const [modelLoadError, setModelLoadError] = useState<string | null>(null);
    const [loadProgress, setLoadProgress] = useState<string>('');
    const [selectedModel] = useState<WhisperModel>(initialModel);

    // Utiliser la langue de l'interface
    const selectedLanguage = i18n.language === 'fr' ? 'french' : 'english';
    const [result, setResult] = useState<VoiceControlResponse | CardFilterResponse | null>(null);
    const [showCardForm, setShowCardForm] = useState(false);
    const [cardInitialData, setCardInitialData] = useState<any>(null);
    const [cardToEdit, setCardToEdit] = useState<Card | null>(null);
    const [proposedChanges, setProposedChanges] = useState<any>(null);
    const [voiceMode, setVoiceMode] = useState<'card_update' | 'filter'>('card_update');

    const transcriberRef = useRef<any>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const transcriptRef = useRef<string>('');

    // Charger le modèle Whisper
    useEffect(() => {
        let isMounted = true;

        const loadModel = async () => {
            // Vérifier si le modèle est déjà dans le cache
            if (whisperModelsCache[selectedModel]) {
                transcriberRef.current = whisperModelsCache[selectedModel];
                setIsLoadingModel(false);
                setLoadProgress(t('voice.whisper.ready'));
                return;
            }

            // Si le modèle est déjà chargé dans le ref, ne pas recharger
            if (transcriberRef.current) {
                setIsLoadingModel(false);
                return;
            }

            try {
                setIsLoadingModel(true);
                setModelLoadError(null);
                setLoadProgress(t('voice.whisper.loading'));

                const transcriber = await pipeline(
                    'automatic-speech-recognition',
                    selectedModel,
                    {
                        quantized: true,
                        progress_callback: (progress: any) => {
                            if (!isMounted) return;

                            if (progress.status === 'progress') {
                                const percent = Math.round((progress.loaded / progress.total) * 100);
                                setLoadProgress(`${t('voice.whisper.downloading')}: ${progress.file} (${percent}%)`);
                            } else if (progress.status === 'done') {
                                setLoadProgress(`✓ ${progress.file}`);
                            } else if (progress.status === 'ready') {
                                setLoadProgress(`✓ ${t('voice.whisper.ready')}`);
                            }
                        }
                    }
                );

                if (isMounted) {
                    // Stocker dans le cache global
                    whisperModelsCache[selectedModel] = transcriber;
                    transcriberRef.current = transcriber;
                    setIsLoadingModel(false);
                    setLoadProgress(t('voice.whisper.ready'));
                }
            } catch (error: any) {
                console.error('Erreur lors du chargement du modèle Whisper:', error);
                console.error('Stack:', error.stack);

                let errorMessage = error.message;
                if (error.message.includes('not valid JSON')) {
                    errorMessage = 'Erreur de chargement. Assurez-vous que l\'application est servie via HTTP et non file://';
                }

                if (isMounted) {
                    setModelLoadError(errorMessage);
                    setIsLoadingModel(false);
                }
            }
        };

        if (open) {
            loadModel();
        }

        return () => {
            isMounted = false;
        };
    }, [open, selectedModel, t]);

    // Arrêter l'enregistrement quand le dialogue se ferme
    useEffect(() => {
        if (!open && isRecording) {
            stopRecording();
        }
    }, [open]);

    // Démarrer automatiquement l'enregistrement si autoStart est true
    useEffect(() => {
        if (open && autoStart && !isLoadingModel && !modelLoadError && !isRecording) {
            // Petit délai pour s'assurer que le dialogue est complètement ouvert et le modèle chargé
            const timer = setTimeout(() => {
                startRecording();
            }, 300);
            return () => clearTimeout(timer);
        }
    }, [open, autoStart, isLoadingModel, modelLoadError]);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            mediaRecorderRef.current = new MediaRecorder(stream);
            audioChunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (event) => {
                audioChunksRef.current.push(event.data);
            };

            mediaRecorderRef.current.onstop = async () => {
                stream.getTracks().forEach(track => track.stop());
                await transcribeAudio();
            };

            mediaRecorderRef.current.start();
            setIsRecording(true);
        } catch (error: any) {
            console.error('Erreur lors de l\'accès au microphone:', error);
            toast({
                title: t('common.error'),
                description: t('voice.microphoneError'),
                variant: 'destructive'
            });
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    const transcribeAudio = async () => {
        setIsTranscribing(true);

        try {
            const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

            // Convertir le blob en ArrayBuffer
            const arrayBuffer = await audioBlob.arrayBuffer();

            // Créer un contexte audio pour décoder
            const audioContext = new AudioContext({ sampleRate: 16000 });
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

            // Extraire les données audio (mono, 16kHz)
            let audio: Float32Array;
            if (audioBuffer.numberOfChannels === 2) {
                // Convertir stéréo en mono
                const left = audioBuffer.getChannelData(0);
                const right = audioBuffer.getChannelData(1);
                audio = new Float32Array(left.length);
                for (let i = 0; i < left.length; i++) {
                    audio[i] = (left[i] + right[i]) / 2;
                }
            } else {
                audio = audioBuffer.getChannelData(0);
            }

            // Transcrire avec Whisper (utiliser la langue de l'interface)
            const result = await transcriberRef.current(audio, {
                language: selectedLanguage,
                task: 'transcribe'
            });

            // Ajouter le texte transcrit
            const newText = result.text.trim();
            if (newText) {
                const currentText = transcript;
                const updatedTranscript = currentText ? currentText + ' ' + newText : newText;
                setTranscript(updatedTranscript);
                transcriptRef.current = updatedTranscript;
            }
        } catch (error: any) {
            console.error('Erreur lors de la transcription:', error);
            toast({
                title: t('common.error'),
                description: t('voice.whisper.transcriptionError'),
                variant: 'destructive'
            });
        } finally {
            setIsTranscribing(false);
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
        // Si on est en train d'enregistrer, arrêter d'abord et attendre la transcription
        if (isRecording) {
            stopRecording();
            // Attendre que la transcription soit terminée
            await new Promise(resolve => {
                const checkTranscribing = setInterval(() => {
                    if (!isTranscribing) {
                        clearInterval(checkTranscribing);
                        resolve(true);
                    }
                }, 100);
            });

            // Petit délai supplémentaire pour s'assurer que le state est à jour
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        // Vérifier qu'il y a du texte après la transcription (utiliser le ref pour la valeur actuelle)
        const currentTranscript = transcriptRef.current || transcript;
        if (!currentTranscript.trim()) {
            toast({
                title: t('voice.whisper.noTranscript'),
                description: t('voice.whisper.noTranscriptDescription'),
                variant: 'destructive'
            });
            return;
        }

        setIsProcessing(true);

        try {
            const response = await voiceControlService.processTranscript(currentTranscript, voiceMode);
            setResult(response);

            // Si le mode est "filter", appliquer le filtre
            if (voiceMode === 'filter') {
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
                setTranscript('');
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
        if (isRecording) {
            stopRecording();
        }
        onOpenChange(false);
        setTranscript('');
    };

    const handleTranscriptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const newValue = e.target.value;
        setTranscript(newValue);
        transcriptRef.current = newValue;
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        // Si Enter est pressé sans Shift et qu'il y a du texte, envoyer
        if (e.key === 'Enter' && !e.shiftKey && transcript.trim() && !isProcessing) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <>
            <Dialog open={open} onOpenChange={onOpenChange}>
                <DialogContent className="sm:max-w-[600px]">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            {t('voice.title')}
                            <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                                {initialModel === 'Xenova/whisper-tiny' ? 'Whisper tiny' : 'Whisper'}
                            </span>
                        </DialogTitle>
                        <DialogDescription>
                            {t('voice.description')}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4">

                        {/* État du modèle */}
                        {isLoadingModel && (
                            <div className="flex items-center justify-center space-x-2 text-primary bg-primary/10 rounded-lg p-3">
                                <div className="flex space-x-1">
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                                <span className="text-sm font-medium">{loadProgress}</span>
                            </div>
                        )}

                        {modelLoadError && (
                            <div className="flex items-center gap-2 text-sm text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-950/20 rounded-lg p-3">
                                <AlertTriangle className="h-4 w-4" />
                                <span>{t('voice.whisper.loadError')}: {modelLoadError}</span>
                            </div>
                        )}

                        {/* Zone de texte éditable */}
                        <div className="space-y-2">
                            <Textarea
                                value={transcript}
                                onChange={handleTranscriptChange}
                                onKeyDown={handleKeyDown}
                                placeholder={t('voice.placeholder')}
                                className="min-h-[150px] resize-none"
                                disabled={isProcessing}
                                readOnly={isRecording}
                                maxLength={500}
                            />
                            <div className="text-xs text-muted-foreground text-right">
                                {transcript.length}/500
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

                        {/* Indicateur d'enregistrement */}
                        {isRecording && (
                            <div className="flex items-center justify-center space-x-2 text-primary">
                                <div className="flex space-x-1">
                                    <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                                </div>
                                <span className="text-sm font-medium">{t('voice.listening')}</span>
                            </div>
                        )}

                        {/* Indicateur de transcription */}
                        {isTranscribing && (
                            <div className="flex items-center justify-center space-x-2 text-primary">
                                <div className="flex space-x-1">
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                                <span className="text-sm font-medium">{t('voice.whisper.transcribing')}</span>
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

                        {/* Boutons d'action */}
                        <div className="flex justify-between gap-2">
                            <div className="flex gap-2 items-center">
                                {!isRecording ? (
                                    <Button
                                        onClick={startRecording}
                                        variant="default"
                                        className="bg-primary hover:bg-primary/90"
                                        disabled={isLoadingModel || isProcessing || !!modelLoadError}
                                    >
                                        <Mic className="h-4 w-4 mr-2" />
                                        {t('voice.start')}
                                    </Button>
                                ) : (
                                    <Button
                                        onClick={stopRecording}
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
                                            disabled={isRecording || isProcessing}
                                        >
                                            <Settings className="h-4 w-4" />
                                        </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="start" className="w-56">
                                        <DropdownMenuItem
                                            onClick={() => onSwitchToNative?.()}
                                            className="flex items-center justify-between"
                                        >
                                            <span>{t('voice.mode.browser')}</span>
                                        </DropdownMenuItem>
                                        {/* <DropdownMenuItem
                                            onClick={() => onSwitchModel?.('Xenova/whisper-tiny')}
                                            className="flex items-center justify-between"
                                        >
                                            <span>{t('voice.mode.whisperTiny')}</span>
                                            {initialModel === 'Xenova/whisper-tiny' && <Check className="h-4 w-4" />}
                                        </DropdownMenuItem> */}
                                        <DropdownMenuItem
                                            onClick={() => onSwitchModel?.('Xenova/whisper-base')}
                                            className="flex items-center justify-between"
                                        >
                                            <span>{t('voice.mode.whisperBase')}</span>
                                            {initialModel === 'Xenova/whisper-base' && <Check className="h-4 w-4" />}
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
                                    disabled={(!transcript.trim() && !isRecording) || isProcessing}
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

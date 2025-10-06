import { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Mic, MicOff, Send, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { voiceControlService, VoiceControlResponse } from '../../services/voiceControlApi';
import { VoiceControlResultDialog } from './VoiceControlResultDialog';
import CardForm from '../cards/CardForm';
import { Card } from '../../types';

interface VoiceControlDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCardSave?: (card: Card) => void;
    defaultListId?: number;
}

export const VoiceControlDialog = ({ open, onOpenChange, onCardSave, defaultListId }: VoiceControlDialogProps) => {
    const { t, i18n } = useTranslation();
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState('');
    const [isSupported, setIsSupported] = useState(true);
    const [isProcessing, setIsProcessing] = useState(false);
    const [result, setResult] = useState<VoiceControlResponse | null>(null);
    const [showResultDialog, setShowResultDialog] = useState(false);
    const [showCardForm, setShowCardForm] = useState(false);
    const [cardInitialData, setCardInitialData] = useState<any>(null);
    const recognitionRef = useRef<any>(null);

    useEffect(() => {
        // Vérifier si l'API Web Speech est disponible
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

        if (!SpeechRecognition) {
            setIsSupported(false);
            return;
        }

        // Initialiser la reconnaissance vocale
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        // Utiliser la langue actuelle de l'utilisateur (fr -> fr-FR, en -> en-US)
        const lang = i18n.language === 'fr' ? 'fr-FR' : 'en-US';
        recognition.lang = lang;

        recognition.onresult = (event: any) => {
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
            setIsListening(false);
        };

        recognition.onend = () => {
            if (isListening) {
                // Redémarrer automatiquement si on est toujours en mode écoute
                recognition.start();
            }
        };

        recognitionRef.current = recognition;

        return () => {
            if (recognitionRef.current) {
                recognitionRef.current.stop();
            }
        };
    }, [isListening, i18n.language]);

    const startListening = () => {
        if (recognitionRef.current && !isListening) {
            setTranscript('');
            recognitionRef.current.start();
            setIsListening(true);
        }
    };

    const stopListening = () => {
        if (recognitionRef.current && isListening) {
            recognitionRef.current.stop();
            setIsListening(false);
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

        setIsProcessing(true);
        stopListening();

        try {
            const response = await voiceControlService.processInstruction(transcript);
            setResult(response);

            // Si task_id est null ou vide, ouvrir CardForm avec les données pré-remplies
            if (!response.task_id) {
                const initialData = convertResponseToInitialData(response);
                setCardInitialData(initialData);
                setShowCardForm(true);
            } else {
                // Sinon afficher le résultat dans VoiceControlResultDialog
                setShowResultDialog(true);
            }

            onOpenChange(false);
            setTranscript('');
        } catch (error) {
            console.error('Erreur lors du traitement de l\'instruction vocale:', error);
            // TODO: Afficher un message d'erreur à l'utilisateur
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

    return (
        <>
            <Dialog open={open} onOpenChange={onOpenChange}>
                <DialogContent className="sm:max-w-[600px]">
                    <DialogHeader>
                        <DialogTitle>{t('voice.title')}</DialogTitle>
                        <DialogDescription>
                            {isSupported ? t('voice.description') : t('voice.notSupported')}
                        </DialogDescription>
                    </DialogHeader>

                    {isSupported ? (
                        <div className="space-y-4">
                            {/* Zone de texte éditable */}
                            <div className="space-y-2">
                                <Textarea
                                    value={transcript}
                                    onChange={handleTranscriptChange}
                                    placeholder={t('voice.placeholder')}
                                    className="min-h-[150px] resize-none"
                                    disabled={isListening || isProcessing}
                                />
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

                            {/* Boutons d'action */}
                            <div className="flex justify-between gap-2">
                                <div className="flex gap-2">
                                    {!isListening ? (
                                        <Button
                                            onClick={startListening}
                                            variant="default"
                                            className="bg-primary hover:bg-primary/90"
                                            disabled={isProcessing}
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
                    ) : (
                        <div className="text-center py-8 text-muted-foreground">
                            <p>{t('voice.notSupportedDescription')}</p>
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            {/* Dialog de résultat */}
            <VoiceControlResultDialog
                open={showResultDialog}
                onOpenChange={setShowResultDialog}
                result={result}
            />

            {/* CardForm pour créer/modifier une carte */}
            {showCardForm && cardInitialData && (
                <CardForm
                    card={null}
                    isOpen={showCardForm}
                    onClose={() => {
                        setShowCardForm(false);
                        setCardInitialData(null);
                    }}
                    onSave={(card) => {
                        setShowCardForm(false);
                        setCardInitialData(null);
                        if (onCardSave) {
                            onCardSave(card);
                        }
                    }}
                    defaultListId={result?.list_id || defaultListId}
                    initialData={cardInitialData}
                />
            )}
        </>
    );
};

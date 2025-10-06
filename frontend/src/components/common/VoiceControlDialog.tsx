import { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Mic, MicOff, Send, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface VoiceControlDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export const VoiceControlDialog = ({ open, onOpenChange }: VoiceControlDialogProps) => {
    const { t, i18n } = useTranslation();
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState('');
    const [isSupported, setIsSupported] = useState(true);
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

    const handleSend = () => {
        // TODO: Implémenter l'envoi de la demande
        console.log('Demande vocale:', transcript);
        stopListening();
        onOpenChange(false);
        setTranscript('');
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
                                disabled={isListening}
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

                        {/* Boutons d'action */}
                        <div className="flex justify-between gap-2">
                            <div className="flex gap-2">
                                {!isListening ? (
                                    <Button
                                        onClick={startListening}
                                        variant="default"
                                        className="bg-primary hover:bg-primary/90"
                                    >
                                        <Mic className="h-4 w-4 mr-2" />
                                        {t('voice.start')}
                                    </Button>
                                ) : (
                                    <Button
                                        onClick={stopListening}
                                        variant="destructive"
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
                                >
                                    <X className="h-4 w-4 mr-2" />
                                    {t('common.cancel')}
                                </Button>
                                <Button
                                    onClick={handleSend}
                                    disabled={!transcript.trim()}
                                    className="bg-primary hover:bg-primary/90"
                                >
                                    <Send className="h-4 w-4 mr-2" />
                                    {t('voice.send')}
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
    );
};

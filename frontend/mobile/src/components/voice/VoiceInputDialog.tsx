import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Mic, MicOff, Send, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Card } from '@shared/types';
import { voiceControlService, VoiceControlResponse } from '@shared/services/voiceControlApi';
import { cardService } from '@shared/services/api';
import { useAuth } from '@shared/hooks/useAuth';
import { usePermissions } from '@shared/hooks/usePermissions';
import CardDetail from '../card/CardDetail';

interface VoiceInputDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onCardSave?: (card: Card) => void;
  defaultListId?: number;
}

const VoiceInputDialog = ({ isOpen, onClose, onCardSave, defaultListId }: VoiceInputDialogProps) => {
  const { t, i18n } = useTranslation();
  const { user: currentUser } = useAuth();
  const permissions = usePermissions(currentUser);
  
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showCardDetail, setShowCardDetail] = useState(false);
  const [cardToEdit, setCardToEdit] = useState<Card | null>(null);
  const [cardInitialData, setCardInitialData] = useState<any>(null);
  const [proposedChanges, setProposedChanges] = useState<any>(null);
  const [debugLogs, setDebugLogs] = useState<string[]>([]);
  
  const recognitionRef = useRef<any>(null);
  const isListeningRef = useRef<boolean>(false);

  useEffect(() => {
    // Check if Web Speech API is available
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
      return;
    }

    // Initialize speech recognition
    if (!recognitionRef.current) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onresult = (event: any) => {
        if (!isListeningRef.current) {
          return;
        }

        const logs: string[] = [];
        logs.push(`Event: idx=${event.resultIndex} len=${event.results.length}`);

        let finalTranscript = '';
        let interimTranscript = '';

        // Rebuild the COMPLETE transcript from ALL results
        // On mobile, each result contains the full phrase up to that point
        for (let i = 0; i < event.results.length; i++) {
          const transcriptPart = event.results[i][0].transcript;
          const isFinal = event.results[i].isFinal;
          
          if (isFinal) {
            finalTranscript += transcriptPart + ' ';
          } else {
            interimTranscript += transcriptPart;
          }
        }

        logs.push(`Final: "${finalTranscript}"`);
        logs.push(`Interim: "${interimTranscript}"`);
        logs.push(`Combined: "${finalTranscript + interimTranscript}"`);
        
        setDebugLogs(prev => [...prev.slice(-15), ...logs]); // Keep last 15 log entries

        // Display the complete transcript
        setTranscript(finalTranscript + interimTranscript);
      };

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        if (event.error === 'no-speech') {
          return;
        }
        isListeningRef.current = false;
        setIsListening(false);
      };

      recognition.onend = () => {
        if (isListeningRef.current) {
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

    // Always update language and properties, even if recognition already exists
    if (recognitionRef.current) {
      const lang = i18n.language === 'fr' ? 'fr-FR' : 'en-US';
      recognitionRef.current.lang = lang;

      // Ensure properties are correctly set (same for all platforms)
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // Ignore error if already stopped
        }
      }
    };
  }, [i18n.language]);

  // Stop listening when dialog closes
  useEffect(() => {
    if (!isOpen && isListening) {
      stopListening();
    }
  }, [isOpen]);

  // Auto-start listening when dialog opens
  useEffect(() => {
    if (isOpen && isSupported && !isListening) {
      const timer = setTimeout(() => {
        startListening();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isOpen, isSupported]);

  const startListening = () => {
    if (recognitionRef.current && !isListeningRef.current) {
      setTranscript('');
      setDebugLogs([]);
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

  // Fonction pour convertir la réponse en données initiales pour CardDetail
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

  const handleSubmit = async () => {
    if (!transcript.trim()) {
      return;
    }

    stopListening();
    setIsProcessing(true);

    try {
      const response = await voiceControlService.processTranscript(transcript);

      // Si task_id est null ou vide, ouvrir CardDetail en mode création avec les données pré-remplies
      if (!response.task_id) {
        // Vérifier les permissions pour créer une carte
        if (!permissions.canCreateCard) {
          toast.error(t('voice.noPermission'), {
            description: t('voice.cannotCreateCard')
          });
          return;
        }

        const initialData = convertResponseToInitialData(response);
        setCardInitialData(initialData);
        setCardToEdit(null);
        setProposedChanges(null);
        setShowCardDetail(true);
      } else {
        // Sinon, charger la carte existante et ouvrir CardDetail en mode édition
        try {
          const existingCard = await cardService.getCard(response.task_id);

          if (existingCard) {
            // Vérifier les permissions pour modifier la carte
            if (!permissions.canModifyCardContent(existingCard) && !permissions.canModifyCardMetadata(existingCard)) {
              toast.error(t('voice.noPermission'), {
                description: t('voice.cannotEditCard')
              });
              return;
            }

            // Carte existe → Mode édition avec proposedChanges
            const changes = convertResponseToInitialData(response);
            setCardToEdit(existingCard);
            setProposedChanges(changes);
            setCardInitialData(null);
            setShowCardDetail(true);
          } else {
            // Carte n'existe plus → Mode création avec les données
            if (!permissions.canCreateCard) {
              toast.error(t('voice.noPermission'), {
                description: t('voice.cannotCreateCard')
              });
              return;
            }

            toast.info(t('voice.cardNotFound'), {
              description: t('voice.cardNotFoundDescription')
            });

            const initialData = convertResponseToInitialData(response);
            setCardInitialData(initialData);
            setCardToEdit(null);
            setProposedChanges(null);
            setShowCardDetail(true);
          }
        } catch (error) {
          console.error('Erreur lors du chargement de la carte:', error);
          toast.error(t('common.error'), {
            description: t('voice.cardLoadError')
          });
        }
      }

      setTranscript('');
    } catch (error) {
      console.error('Erreur lors du traitement de l\'instruction vocale:', error);
      toast.error(t('common.error'), {
        description: t('voice.processingError')
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClose = () => {
    if (!isProcessing) {
      stopListening();
      setTranscript('');
      onClose();
    }
  };

  const handleCardSave = (savedCard: Card) => {
    setShowCardDetail(false);
    setCardToEdit(null);
    setCardInitialData(null);
    setProposedChanges(null);
    onClose();
    
    if (onCardSave) {
      onCardSave(savedCard);
    }
  };

  const handleCardClose = () => {
    setShowCardDetail(false);
    setCardToEdit(null);
    setCardInitialData(null);
    setProposedChanges(null);
    // Fermer aussi le dialogue de saisie vocale pour revenir à la page principale
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 animate-fade-in"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 bg-background z-50 overflow-y-auto animate-slide-up" style={{ display: showCardDetail ? 'none' : 'block' }}>
        {/* Header */}
        <div className="sticky top-0 bg-card border-b-2 border-border z-10">
          <div className="flex items-center justify-between p-4" style={{ paddingTop: 'calc(1rem + env(safe-area-inset-top))' }}>
            <button
              onClick={handleClose}
              className="p-2 text-muted-foreground hover:text-foreground active:bg-accent rounded-lg transition-colors"
              aria-label={t('common.close')}
            >
              <X className="w-6 h-6" />
            </button>
            <h2 className="text-lg font-bold text-foreground">
              {t('voice.title')}
            </h2>
            <button
              onClick={handleSubmit}
              disabled={!transcript.trim() || isProcessing}
              className="p-2 text-primary hover:text-primary/80 active:bg-accent rounded-lg transition-colors disabled:opacity-50"
              aria-label={t('common.send')}
            >
              <Send className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-6 pb-safe">
          {/* Description */}
          <p className="text-sm text-muted-foreground">
            {t('voice.description')}
          </p>

          {/* Transcript area */}
          <div className="space-y-2">
            <div className="relative">
              <textarea
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                placeholder={t('voice.placeholder')}
                className="w-full bg-card border-2 border-border rounded-lg px-4 py-3 text-foreground resize-none min-h-[200px]"
                maxLength={500}
                readOnly={isListening}
                disabled={isProcessing}
              />
              {transcript.trim() && !isListening && !isProcessing && (
                <button
                  onClick={() => setTranscript('')}
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

          {/* Listening indicator */}
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

          {/* Not supported warning */}
          {!isSupported && (
            <div className="flex items-center gap-2 text-sm text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-950/20 rounded-lg p-3">
              <span>{t('voice.notSupportedBrowser')}</span>
            </div>
          )}

          {/* Voice control button */}
          <div className="flex justify-center">
            {!isListening ? (
              <button
                onClick={startListening}
                disabled={!isSupported || isProcessing}
                className="btn-touch bg-primary text-primary-foreground px-8 rounded-lg flex items-center gap-2 disabled:opacity-50"
              >
                <Mic className="w-5 h-5" />
                {t('voice.start')}
              </button>
            ) : (
              <button
                onClick={stopListening}
                disabled={isProcessing}
                className="btn-touch bg-destructive text-destructive-foreground px-8 rounded-lg flex items-center gap-2 disabled:opacity-50"
              >
                <MicOff className="w-5 h-5" />
                {t('voice.stop')}
              </button>
            )}
          </div>

          {/* Submit button */}
          <button
            onClick={handleSubmit}
            disabled={!transcript.trim() || isProcessing}
            className="w-full btn-touch bg-primary text-primary-foreground font-medium rounded-lg hover:bg-primary/90 active:bg-primary/80 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
            {isProcessing ? t('voice.processing') : t('voice.send')}
          </button>

          {/* Debug logs */}
          {debugLogs.length > 0 && (
            <div className="mt-4 p-3 bg-gray-900 text-green-400 rounded-lg text-xs font-mono overflow-auto max-h-[200px]">
              <div className="font-bold mb-2">DEBUG LOGS:</div>
              {debugLogs.map((log, idx) => (
                <div key={idx}>{log}</div>
              ))}
            </div>
          )}
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


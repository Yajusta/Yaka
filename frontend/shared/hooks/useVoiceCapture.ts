import { Dispatch, SetStateAction, useCallback, useEffect, useMemo, useState } from 'react';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';

interface UseVoiceCaptureOptions {
    open: boolean;
    language: string;
    autoStart?: boolean;
    continuous?: boolean;
    disabled?: boolean;
    autoRestartDelayMs?: number;
}

interface UseVoiceCaptureResult {
    currentText: string;
    listening: boolean;
    browserSupportsSpeechRecognition: boolean;
    startListening: (options?: { enableAutoStart?: boolean }) => void;
    stopListening: (options?: { disableAutoStart?: boolean }) => void;
    resetTranscript: () => void;
    handleManualChange: (value: string) => void;
    clearTranscripts: () => void;
    setManualTranscript: Dispatch<SetStateAction<string>>;
}

const LANGUAGE_FALLBACK = 'fr-FR';

export const useVoiceCapture = ({
    open,
    language,
    autoStart = true,
    continuous = true,
    disabled = false,
    autoRestartDelayMs = 100
}: UseVoiceCaptureOptions): UseVoiceCaptureResult => {
    const {
        transcript,
        listening,
        resetTranscript,
        browserSupportsSpeechRecognition
    } = useSpeechRecognition();

    const [manualTranscript, setManualTranscript] = useState('');
    const [shouldAutoRestart, setShouldAutoRestart] = useState(false);
    const [autoStartEnabled, setAutoStartEnabled] = useState(true);

    const effectiveLanguage = language || LANGUAGE_FALLBACK;

    const startListening = useCallback(
        (options?: { enableAutoStart?: boolean }) => {
            if (disabled) {
                return;
            }
            const enableAutoStart = options?.enableAutoStart ?? true;
            setAutoStartEnabled(enableAutoStart);
            setShouldAutoRestart(true);
            if (!listening) {
                resetTranscript();
            }
            try {
                SpeechRecognition.startListening({
                    continuous,
                    language: effectiveLanguage
                });
            } catch (error) {
                console.error('Error starting speech recognition:', error);
            }
        },
        [continuous, disabled, effectiveLanguage, listening, resetTranscript]
    );

    const stopListening = useCallback((options?: { disableAutoStart?: boolean }) => {
        const disableAutoStart = options?.disableAutoStart ?? true;
        if (disableAutoStart) {
            setAutoStartEnabled(false);
        }
        setShouldAutoRestart(false);
        try {
            SpeechRecognition.stopListening();
        } catch (error) {
            console.error('Error stopping speech recognition:', error);
        }
    }, []);

    const handleManualChange = useCallback((value: string) => {
        setManualTranscript(value);
    }, []);

    const clearTranscripts = useCallback(() => {
        if (listening) {
            resetTranscript();
        } else {
            setManualTranscript('');
        }
    }, [listening, resetTranscript, setManualTranscript]);

    const currentText = useMemo(() => {
        if (listening && transcript.trim()) {
            if (manualTranscript.trim()) {
                return `${manualTranscript.trim()} ${transcript}`.trim();
            }
            return transcript;
        }
        return manualTranscript;
    }, [listening, manualTranscript, transcript]);

    // Synchronise la langue du moteur natif
    useEffect(() => {
        if (disabled) {
            return;
        }
        const recognition = SpeechRecognition.getRecognition();
        if (recognition) {
            recognition.lang = effectiveLanguage;
        }
    }, [disabled, effectiveLanguage]);

    // Copie le transcript automatique vers le texte manuel quand l'écoute se termine
    useEffect(() => {
        if (!listening && transcript) {
            setManualTranscript(prev => {
                const combined = prev ? `${prev} ${transcript}` : transcript;
                return combined.trim();
            });
        }
    }, [listening, transcript, setManualTranscript]);

    // Arrête l'écoute si le dialogue se ferme
    useEffect(() => {
        if (!open) {
            setShouldAutoRestart(false);
            setAutoStartEnabled(true);
            stopListening({ disableAutoStart: false });
        }
    }, [open, stopListening]);

    // Auto restart pour le mode non continu
    useEffect(() => {
        if (disabled || continuous) {
            return;
        }
        const recognition = SpeechRecognition.getRecognition();
        if (!recognition) {
            return;
        }
        const handleEnd = () => {
            if (shouldAutoRestart && !listening && open) {
                setTimeout(() => {
                    if (shouldAutoRestart && open) {
                        startListening();
                    }
                }, autoRestartDelayMs);
            }
        };
        recognition.addEventListener('end', handleEnd);
        return () => recognition.removeEventListener('end', handleEnd);
    }, [autoRestartDelayMs, continuous, disabled, listening, open, shouldAutoRestart, startListening]);

    // Auto start quand le dialogue s'ouvre
    useEffect(() => {
        if (
            open &&
            autoStart &&
            autoStartEnabled &&
            !disabled &&
            browserSupportsSpeechRecognition &&
            !listening
        ) {
            const timer = setTimeout(() => {
                startListening();
            }, 300);
            return () => clearTimeout(timer);
        }
    }, [autoStart, autoStartEnabled, browserSupportsSpeechRecognition, disabled, listening, open, startListening]);

    return {
        currentText,
        listening,
        browserSupportsSpeechRecognition,
        startListening,
        stopListening,
        resetTranscript,
        handleManualChange,
        clearTranscripts,
        setManualTranscript
    };
};

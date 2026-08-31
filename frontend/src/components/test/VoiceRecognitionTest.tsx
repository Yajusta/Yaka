import { useEffect, useState } from "react";
import SpeechRecognition, {
  useSpeechRecognition,
} from "react-speech-recognition";
import { Button } from "../ui/button";
import { Mic, MicOff, Trash2 } from "lucide-react";

export const VoiceRecognitionTest = () => {
  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition,
    browserSupportsContinuousListening,
    isMicrophoneAvailable,
  } = useSpeechRecognition();

  const [shouldAutoRestart, setShouldAutoRestart] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [useContinuousMode, setUseContinuousMode] = useState(true);

  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, `[${timestamp}] ${message}`]);
  };

  useEffect(() => {
    addLog("✅ Composant chargé");
    addLog(
      `📱 Navigateur: ${/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ? "Mobile" : "Desktop"}`,
    );
    addLog(
      `🔊 Support reconnaissance: ${browserSupportsSpeechRecognition ? "✅" : "❌"}`,
    );
    addLog(
      `🔄 Support mode continu: ${browserSupportsContinuousListening ? "✅" : "❌"}`,
    );
    addLog(`🎤 Micro disponible: ${isMicrophoneAvailable ? "✅" : "❌"}`);
    addLog(
      `🔒 Protocole: ${window.location.protocol === "https:" ? "HTTPS ✅" : "HTTP ⚠️"}`,
    );

    // Log native recognition events for debugging
    const recognition = SpeechRecognition.getRecognition();
    if (recognition) {
      const handleStart = () => addLog("🎬 [Native] Recognition started");
      const handleEnd = () => addLog("🛑 [Native] Recognition ended");
      const handleError = (e: any) => addLog(`❌ [Native] Error: ${e.error}`);
      const handleResult = (e: any) => {
        const last = e.results[e.results.length - 1];
        const text = last[0].transcript;
        const isFinal = last.isFinal;
        addLog(
          `📢 [Native] Result: "${text}" (${isFinal ? "FINAL" : "interim"})`,
        );
      };

      recognition.addEventListener("start", handleStart);
      recognition.addEventListener("end", handleEnd);
      recognition.addEventListener("error", handleError);
      recognition.addEventListener("result", handleResult);

      return () => {
        recognition.removeEventListener("start", handleStart);
        recognition.removeEventListener("end", handleEnd);
        recognition.removeEventListener("error", handleError);
        recognition.removeEventListener("result", handleResult);
      };
    }
  }, [
    browserSupportsSpeechRecognition,
    browserSupportsContinuousListening,
    isMicrophoneAvailable,
  ]);

  // Auto-restart logic for non-continuous mode
  useEffect(() => {
    if (!useContinuousMode) {
      const recognition = SpeechRecognition.getRecognition();
      if (recognition) {
        const handleEnd = () => {
          addLog("⏹️ Reconnaissance terminée (event: end)");

          // Auto-restart if needed
          if (shouldAutoRestart && !listening) {
            addLog("🔄 Auto-restart dans 100ms...");
            setTimeout(() => {
              if (shouldAutoRestart) {
                addLog("▶️ Redémarrage automatique");
                SpeechRecognition.startListening({
                  continuous: false,
                  language: "fr-FR",
                });
              }
            }, 100);
          }
        };

        recognition.addEventListener("end", handleEnd);
        return () => {
          recognition.removeEventListener("end", handleEnd);
        };
      }
    }
  }, [shouldAutoRestart, listening, useContinuousMode]);

  // Monitor listening state changes
  useEffect(() => {
    if (listening) {
      addLog("🎤 État: EN ÉCOUTE");
    } else {
      addLog("⏸️ État: ARRÊTÉ");
    }
  }, [listening]);

  // Monitor transcript changes
  useEffect(() => {
    if (transcript) {
      addLog(
        `📝 Transcript mis à jour: "${transcript.substring(0, 50)}${transcript.length > 50 ? "..." : ""}"`,
      );
    }
  }, [transcript]);

  const startListening = () => {
    addLog(
      `▶️ Démarrage demandé (mode: ${useContinuousMode ? "continu" : "non-continu + auto-restart"})`,
    );
    setShouldAutoRestart(true);

    // Ne pas réinitialiser le transcript en mode continu, seulement au premier démarrage
    if (!listening) {
      addLog("🗑️ Reset du transcript avant démarrage");
      resetTranscript();
    }

    try {
      SpeechRecognition.startListening({
        continuous: useContinuousMode,
        language: "fr-FR",
      });
    } catch (error: any) {
      addLog(`❌ Erreur démarrage: ${error.message}`);
    }
  };

  const stopListening = () => {
    addLog("⏹️ Arrêt demandé");
    setShouldAutoRestart(false);

    try {
      SpeechRecognition.stopListening();
    } catch (error: any) {
      addLog(`❌ Erreur arrêt: ${error.message}`);
    }
  };

  const handleClear = () => {
    resetTranscript();
    setLogs([]);
    addLog("🗑️ Texte et logs effacés");
  };

  const toggleMode = () => {
    const newMode = !useContinuousMode;
    setUseContinuousMode(newMode);
    addLog(
      `🔄 Mode changé: ${newMode ? "Continu" : "Non-continu + auto-restart"}`,
    );

    // Si on écoute, redémarrer avec le nouveau mode
    if (listening) {
      stopListening();
      setTimeout(() => {
        startListening();
      }, 200);
    }
  };

  if (!browserSupportsSpeechRecognition) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-destructive/10 border-2 border-destructive rounded-lg p-6">
            <h2 className="text-2xl font-bold text-destructive mb-2">
              ❌ Non supporté
            </h2>
            <p>Votre navigateur ne supporte pas la reconnaissance vocale.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-card border-2 border-border rounded-lg p-6">
          <h1 className="text-3xl font-bold mb-2">
            🎤 Test Reconnaissance Vocale
          </h1>
          <p className="text-muted-foreground">
            Page de test pour react-speech-recognition
          </p>
        </div>

        {/* Info Panel */}
        <div className="bg-blue-50 dark:bg-blue-950 border-2 border-blue-200 dark:border-blue-800 rounded-lg p-4 space-y-2">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <strong>Support reconnaissance:</strong>{" "}
              {browserSupportsSpeechRecognition ? "✅ Oui" : "❌ Non"}
            </div>
            <div>
              <strong>Support mode continu:</strong>{" "}
              {browserSupportsContinuousListening ? "✅ Oui" : "❌ Non"}
            </div>
            <div>
              <strong>Micro disponible:</strong>{" "}
              {isMicrophoneAvailable ? "✅ Oui" : "❌ Non"}
            </div>
            <div>
              <strong>Protocole:</strong>{" "}
              {window.location.protocol === "https:" ? "🔒 HTTPS" : "⚠️ HTTP"}
            </div>
          </div>
        </div>

        {/* Warning for HTTP on mobile */}
        {window.location.protocol !== "https:" &&
          window.location.hostname !== "localhost" &&
          window.location.hostname !== "127.0.0.1" && (
            <div className="bg-yellow-50 dark:bg-yellow-950 border-2 border-yellow-400 dark:border-yellow-600 rounded-lg p-4">
              <strong>⚠️ Attention:</strong> La reconnaissance vocale nécessite
              HTTPS sur mobile.
              <br />
              <strong>Solution:</strong> Utilisez ngrok ou testez sur localhost
              (desktop uniquement).
            </div>
          )}

        {/* Mode Toggle */}
        <div className="bg-card border-2 border-border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <strong>Mode actuel:</strong>{" "}
              <span className="text-primary font-mono">
                {useContinuousMode
                  ? "continuous: true"
                  : "continuous: false + auto-restart"}
              </span>
            </div>
            <Button onClick={toggleMode} variant="outline" disabled={listening}>
              Changer de mode
            </Button>
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            {useContinuousMode
              ? "🖥️ Mode continu natif (recommandé desktop)"
              : "📱 Mode non-continu avec auto-restart (recommandé mobile)"}
          </p>
        </div>

        {/* Transcript Area */}
        <div className="bg-card border-2 border-border rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4">Transcription</h2>
          <textarea
            value={transcript}
            readOnly
            placeholder="Le texte transcrit apparaîtra ici..."
            className="w-full min-h-[200px] p-4 bg-background border-2 border-border rounded-lg resize-vertical font-mono"
          />
        </div>

        {/* Controls */}
        <div className="flex gap-4">
          <Button
            onClick={startListening}
            disabled={listening}
            className="flex-1"
            size="lg"
          >
            <Mic className="mr-2 h-5 w-5" />
            Démarrer
          </Button>
          <Button
            onClick={stopListening}
            disabled={!listening}
            variant="destructive"
            className="flex-1"
            size="lg"
          >
            <MicOff className="mr-2 h-5 w-5" />
            Arrêter
          </Button>
          <Button onClick={handleClear} variant="outline" size="lg">
            <Trash2 className="h-5 w-5" />
          </Button>
        </div>

        {/* Status */}
        <div
          className={`border-2 rounded-lg p-4 font-bold ${
            listening
              ? "bg-green-50 dark:bg-green-950 border-green-500 text-green-700 dark:text-green-300"
              : "bg-red-50 dark:bg-red-950 border-red-500 text-red-700 dark:text-red-300"
          }`}
        >
          État: {listening ? "🎤 EN ÉCOUTE" : "⏸️ ARRÊTÉ"}
        </div>

        {/* Debug Logs */}
        <div className="bg-card border-2 border-border rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4">📋 Logs de débogage</h2>
          <div className="bg-background border-2 border-border rounded-lg p-4 font-mono text-xs max-h-[300px] overflow-y-auto space-y-1">
            {logs.map((log, index) => (
              <div key={index}>{log}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

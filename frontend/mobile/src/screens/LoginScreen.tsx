import { useState, FormEvent, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@shared/hooks/useAuth";
import {
  boardSettingsService,
  authService,
  resetUsersCache,
} from "@shared/services/api";
import { listsApi } from "@shared/services/listsApi";
import { saveBoardConfig, getCurrentBoardInfo } from "@shared/utils/boardUtils";
import {
  AlertTriangle,
  Copy,
  Database,
  Eye,
  FolderKanban,
  Loader2,
  Settings,
  Trash,
  Zap,
} from "lucide-react";
import i18n from "../i18n";

// Declaration for global variables injected by nginx
declare global {
  interface Window {
    DEMO_MODE: string;
  }
}

const LoginScreen = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { boardName } = useParams();
  const { login } = useAuth();
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [boardTitle, setBoardTitle] = useState<string>("Yaka"); // Default fallback
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);

  // Board actuellement actif
  const [boardInfo, setBoardInfo] = useState(() => getCurrentBoardInfo());

  // Fetch board title
  const fetchBoardTitle = async () => {
    try {
      const titleData = await boardSettingsService.getBoardTitle();
      setBoardTitle(titleData.title);
    } catch (error) {
      console.error("Failed to fetch board title:", error);
      // Keep default 'Yaka' title on error
    }
  };

  // Load demo mode configuration and fetch board title on component mount
  useEffect(() => {
    // Load demo config securely
    fetch("/demo-config.js")
      .then((response) => response.text())
      .then((script) => {
        // Parse the script to extract DEMO_MODE value without using eval
        const match = script.match(/window\.DEMO_MODE\s*=\s*['"]([^'"]*)['"]/);
        const demoMode = match ? match[1] === "true" : false;
        setIsDemoMode(demoMode);
      })
      .catch((_error) => {
        setIsDemoMode(false);
      });

    fetchBoardTitle();
  }, []);

  // Synchroniser quand boardName change dans l'URL
  useEffect(() => {
    if (boardName) {
      saveBoardConfig(boardName);
      listsApi.invalidateCache();
      resetUsersCache();
      fetchBoardTitle();
    }
    setBoardInfo(getCurrentBoardInfo());
  }, [boardName]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const activeBoard = getCurrentBoardInfo();
      saveBoardConfig(activeBoard.isInternal ? null : activeBoard.boardName);
      listsApi.invalidateCache();
      resetUsersCache();

      await login(email, password);

      // Apply user language setting immediately after login
      const currentUser = authService.getCurrentUserFromStorage();
      if (currentUser?.language) {
        localStorage.setItem("i18nextLng", currentUser.language);
        await i18n.changeLanguage(currentUser.language);
      }

      // Redirection
      if (!activeBoard.isInternal && activeBoard.boardName) {
        navigate(`/board/${encodeURIComponent(activeBoard.boardName)}`);
      } else {
        navigate("/");
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || t("auth.loginError"));
    } finally {
      setLoading(false);
    }
  };

  const handleConfigClick = () => {
    const currentBoardName = localStorage.getItem("board_name") || "";
    if (currentBoardName) {
      navigate(`/config?prefill=${encodeURIComponent(currentBoardName)}`);
    } else {
      navigate("/config");
    }
  };

  const copyToClipboard = async (text: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (error) {
      console.error("Failed to copy to clipboard:", error);
    }
  };

  const fillDemoCredentials = (): void => {
    setEmail("admin@yaka.local");
    setPassword("Admin123");
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background">
      {/* Config button */}
      <button
        onClick={handleConfigClick}
        className="absolute top-4 right-4 p-2 text-muted-foreground hover:text-foreground active:text-primary transition-colors"
      >
        <Settings className="w-6 h-6" />
      </button>

      <div className="w-full max-w-md space-y-8 animate-fade-in">
        {/* Logo */}
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <img src="/yaka.svg" alt="Yaka" className="w-32 h-32" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">{boardTitle}</h1>
          <p className="mt-2 text-muted-foreground">
            {t("auth.connectToAccount")}
          </p>
        </div>

        {/* Demo Mode Section */}
        {isDemoMode && (
          <div className="mb-6 space-y-3 animate-slide-up">
            {/* Main message with icon */}
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-md">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <div className="text-amber-800 text-sm font-medium">
                    🔄 {t("auth.demoModeEnabled")}
                  </div>
                  <div className="text-amber-700 text-sm mt-1">
                    {t("auth.email")} : <strong>admin@yaka.local</strong>
                    <button
                      onClick={() => copyToClipboard("admin@yaka.local")}
                      className="ml-2 p-1 hover:bg-amber-200 rounded transition-colors"
                      title={t("auth.copyEmail")}
                    >
                      <Copy className="h-3 w-3 text-amber-600" />
                    </button>
                    <br />
                    {t("auth.password")} : <strong>Admin123</strong>
                    <button
                      onClick={() => copyToClipboard("Admin123")}
                      className="ml-2 p-1 hover:bg-amber-200 rounded transition-colors"
                      title={t("auth.copyPassword")}
                    >
                      <Copy className="h-3 w-3 text-amber-600" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Auto-fill button - centered in the whole section */}
              <div className="mt-3 pt-3 border-t border-amber-200 flex justify-center">
                <button
                  onClick={fillDemoCredentials}
                  className="bg-amber-100 border border-amber-300 text-amber-800 hover:bg-amber-200 hover:border-amber-400 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center"
                >
                  <Zap className="h-4 w-4 mr-2" />
                  {t("auth.fillDemoCredentials")}
                </button>
              </div>
            </div>

            {/* Database warning */}
            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
              <Trash className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
              <div className="text-red-700 text-sm">
                <strong>{t("auth.databaseDeletedRegularly")}</strong>
                <br />
                {t("auth.dataResetHourly")}
              </div>
            </div>

            {/* Public environment warning */}
            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
              <Eye className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
              <div className="text-red-700 text-sm">
                <strong>{t("auth.publicEnvironment")}</strong>
                <br />
                {t("auth.noSensitiveInfo")}
              </div>
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-foreground mb-2"
            >
              {t("auth.email")}
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="admin@yaka.local"
              className="w-full px-4 py-3 bg-card border-2 border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-foreground mb-2"
            >
              {t("auth.password")}
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              placeholder="••••••••"
              className="w-full px-4 py-3 bg-card border-2 border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          {/* Rappel de la Board en cours (pastille cliquable vers les paramètres) */}
          <div className="p-3 bg-muted/30 border-2 border-border/70 rounded-xl flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              {boardInfo.isInternal ? (
                <Database className="w-4 h-4 text-emerald-500" />
              ) : (
                <FolderKanban className="w-4 h-4 text-indigo-500" />
              )}
              <span>{t("boardConfig.currentBoard")}</span>
            </span>
            <button
              type="button"
              onClick={handleConfigClick}
              className={`text-xs font-semibold px-2.5 py-1 rounded-full cursor-pointer transition-all hover:scale-105 active:scale-95 flex items-center gap-1.5 ${
                boardInfo.isInternal
                  ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
                  : "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30 hover:bg-indigo-500/20"
              }`}
              title={t("boardConfig.switchBoard") || "Changer de Board"}
            >
              <span>
                {boardInfo.isInternal
                  ? t("boardConfig.internalOption")
                  : boardInfo.boardName}
              </span>
              <Settings className="w-3 h-3 opacity-60" />
            </button>
          </div>

          {error && (
            <div className="p-4 bg-destructive/10 border-2 border-destructive/40 rounded-lg animate-slide-up">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full btn-touch bg-primary text-primary-foreground font-medium rounded-lg hover:bg-primary/90 active:bg-primary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
          >
            {loading && <Loader2 className="mr-2 h-5 w-5 animate-spin" />}
            {t("auth.login")}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginScreen;

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
import { FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@shared/hooks/useAuth.tsx";
import {
  authService,
  boardSettingsService,
  resetUsersCache,
} from "@shared/services/api.tsx";
import { listsApi } from "@shared/services/listsApi.ts";
import {
  getCurrentBoardInfo,
  saveBoardConfig,
} from "@shared/utils/boardUtils.ts";
import { Footer } from "../common/Footer.tsx";
import LanguageSelector from "../common/LanguageSelector.tsx";
import { Alert, AlertDescription } from "../ui/alert.tsx";
import { Button } from "../ui/button.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card.tsx";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog.tsx";
import { Input } from "../ui/input.tsx";
import { Label } from "../ui/label.tsx";

// Déclaration pour les variables globales injectées par nginx
declare global {
  interface Window {
    DEMO_MODE: string;
  }
}

const LoginForm = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [resetEmail, setResetEmail] = useState<string>("");
  const [resetLoading, setResetLoading] = useState<boolean>(false);
  const [resetSuccess, setResetSuccess] = useState<boolean>(false);
  const [resetError, setResetError] = useState<string>("");
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
  const [boardTitle, setBoardTitle] = useState<string>(
    "Yaka (Yet Another Kanban App)",
  );
  const { login } = useAuth();

  // État du Board actif et dialog de configuration
  const [boardInfo, setBoardInfo] = useState(() => getCurrentBoardInfo());
  const [isConfigOpen, setIsConfigOpen] = useState<boolean>(false);
  const [configType, setConfigType] = useState<"internal" | "specific">(
    "internal",
  );
  const [configBoardName, setConfigBoardName] = useState<string>("");
  const [configError, setConfigError] = useState<string>("");

  useEffect(() => {
    // Charger le fichier de configuration demo de manière sécurisée
    fetch("/demo-config.js")
      .then((response) => response.text())
      .then((script) => {
        // Parser le script pour extraire la valeur DEMO_MODE sans utiliser eval
        const match = script.match(/window\.DEMO_MODE\s*=\s*['"]([^'"]*)['"]/);
        const demoMode = match ? match[1] === "true" : false;
        setIsDemoMode(demoMode);
      })
      .catch((_error) => {
        setIsDemoMode(false);
      });

    // Récupérer le titre du board
    boardSettingsService
      .getBoardTitle()
      .then((data) => {
        setBoardTitle(data.title);
      })
      .catch((_error) => {
        setBoardTitle("Yaka (Yet Another Kanban App)");
      });

    // Synchroniser avec l'URL si sur /board/:uid/login
    const match = window.location.pathname.match(/^\/board\/([^\/]+)/);
    if (match && match[1]) {
      saveBoardConfig(match[1]);
      listsApi.invalidateCache();
      resetUsersCache();
    }
    setBoardInfo(getCurrentBoardInfo());
  }, []);

  const openBoardConfig = () => {
    const current = getCurrentBoardInfo();
    setConfigType(current.isInternal ? "internal" : "specific");
    setConfigBoardName(current.isInternal ? "" : current.boardName);
    setConfigError("");
    setIsConfigOpen(true);
  };

  const handleSaveBoardConfig = (e: FormEvent) => {
    e.preventDefault();
    setConfigError("");

    if (configType === "specific" && !configBoardName.trim()) {
      setConfigError(
        t("boardConfig.nameRequired") || "Veuillez saisir un nom de Board",
      );
      return;
    }

    const selectedName =
      configType === "internal" ? null : configBoardName.trim();
    const resolved = saveBoardConfig(selectedName);

    setBoardInfo(resolved);
    setIsConfigOpen(false);

    listsApi.invalidateCache();
    resetUsersCache();
    boardSettingsService
      .getBoardTitle()
      .then((data) => {
        setBoardTitle(data.title);
      })
      .catch((_error) => {
        setBoardTitle("Yaka (Yet Another Kanban App)");
      });

    if (resolved.isInternal) {
      navigate("/login", { replace: true });
    } else {
      navigate(`/board/${encodeURIComponent(resolved.boardName)}/login`, {
        replace: true,
      });
    }
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const activeBoard = getCurrentBoardInfo();
      saveBoardConfig(activeBoard.isInternal ? null : activeBoard.boardName);
      listsApi.invalidateCache();
      resetUsersCache();

      await login(email, password);

      // Rediriger vers la page d'accueil du board actuel après une connexion réussie
      if (!activeBoard.isInternal && activeBoard.boardName) {
        navigate(`/board/${encodeURIComponent(activeBoard.boardName)}`, {
          replace: true,
        });
      } else {
        navigate("/", { replace: true });
      }
    } catch (error: any) {
      setError(error.response?.data?.detail || t("auth.loginError"));
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordReset = async (
    e: FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    e.preventDefault();
    setResetError("");
    setResetLoading(true);

    try {
      // Extraire le board_uid de l'URL si présent
      const boardUidMatch =
        window.location.pathname.match(/^\/board\/([^\/]+)/);
      const boardUid = boardUidMatch ? boardUidMatch[1] : undefined;

      await authService.requestPasswordReset(resetEmail, boardUid);
      setResetSuccess(true);
    } catch (error: any) {
      setResetError(
        error.response?.data?.detail || t("auth.resetPasswordError"),
      );
    } finally {
      setResetLoading(false);
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
    <div className="min-h-screen flex flex-col bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      {/* Contrôles en haut à droite : Paramètres du Board + Language selector */}
      <div className="absolute top-4 right-4 flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={openBoardConfig}
          className="text-gray-500 hover:text-gray-900 transition-colors"
          title={t("boardConfig.title")}
          type="button"
        >
          <Settings className="h-5 w-5" />
        </Button>
        <LanguageSelector />
      </div>

      {/* Logo et titre du board */}
      <div className="flex flex-col items-center mb-6">
        <img src="/yaka.svg" alt="Logo Yaka" className="h-32 w-32 mb-3" />
        <h1 className="text-3xl font-bold text-gray-900 mb-4">{boardTitle}</h1>
      </div>

      <div className="flex-1 flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">
              {t("auth.login")}
            </CardTitle>
            <CardDescription className="text-center">
              {t("auth.connectToAccount")}
            </CardDescription>
            {isDemoMode && (
              <div className="mt-4 space-y-3">
                {/* Message principal avec icône */}
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

                  {/* Bouton remplir automatiquement - centré dans toute la section */}
                  <div className="mt-3 pt-3 border-t border-amber-200 flex justify-center">
                    <Button
                      onClick={fillDemoCredentials}
                      variant="outline"
                      size="sm"
                      className="bg-amber-100 border-amber-300 text-amber-800 hover:bg-amber-200 hover:border-amber-400"
                    >
                      <Zap className="h-4 w-4 mr-2" />
                      {t("auth.fillDemoCredentials")}
                    </Button>
                  </div>
                </div>

                {/* Avertissement base de données */}
                <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
                  <Trash className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                  <div className="text-red-700 text-sm">
                    <strong>{t("auth.databaseDeletedRegularly")}</strong>
                    <br />
                    {t("auth.dataResetHourly")}
                  </div>
                </div>

                {/* Avertissement environnement public */}
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
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="email">{t("auth.email")}</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="admin@yaka.local"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">{t("auth.password")}</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                />
              </div>

              {/* Rappel de la Board en cours (pastille cliquable vers les paramètres) */}
              <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-700 flex items-center gap-1.5">
                  {boardInfo.isInternal ? (
                    <Database className="w-4 h-4 text-emerald-600" />
                  ) : (
                    <FolderKanban className="w-4 h-4 text-indigo-600" />
                  )}
                  <span>{t("boardConfig.currentBoard")}</span>
                </span>
                <button
                  type="button"
                  onClick={openBoardConfig}
                  className={`text-xs font-semibold px-2.5 py-1 rounded-full cursor-pointer transition-all hover:scale-105 active:scale-95 flex items-center gap-1.5 ${
                    boardInfo.isInternal
                      ? "bg-emerald-100 text-emerald-700 border border-emerald-200 hover:bg-emerald-200/70"
                      : "bg-indigo-100 text-indigo-700 border border-indigo-200 hover:bg-indigo-200/70"
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

              <Button type="submit" className="w-full" disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {t("auth.login")}
              </Button>
            </form>

            <div className="mt-4 text-center">
              <Dialog>
                <DialogTrigger asChild>
                  <Button variant="link" className="text-sm">
                    {t("auth.forgotPassword")}
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>
                      {t("auth.resetPasswordDialogTitle")}
                    </DialogTitle>
                    <DialogDescription>
                      {t("auth.resetPasswordDialogDescription")}
                    </DialogDescription>
                  </DialogHeader>

                  {resetSuccess ? (
                    <div className="text-center py-4">
                      <Alert>
                        <AlertDescription>
                          {t("auth.resetPasswordSuccess")}
                        </AlertDescription>
                      </Alert>
                    </div>
                  ) : (
                    <form onSubmit={handlePasswordReset} className="space-y-4">
                      {resetError && (
                        <Alert variant="destructive">
                          <AlertDescription>{resetError}</AlertDescription>
                        </Alert>
                      )}

                      <div className="space-y-2">
                        <Label htmlFor="resetEmail">{t("auth.email")}</Label>
                        <Input
                          id="resetEmail"
                          type="email"
                          value={resetEmail}
                          onChange={(e) => setResetEmail(e.target.value)}
                          required
                          placeholder={t("auth.emailPlaceholder")}
                        />
                      </div>

                      <Button
                        type="submit"
                        className="w-full"
                        disabled={resetLoading}
                      >
                        {resetLoading && (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        )}
                        {t("auth.sendResetLink")}
                      </Button>
                    </form>
                  )}
                </DialogContent>
              </Dialog>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Dialog de configuration du Board */}
      <Dialog open={isConfigOpen} onOpenChange={setIsConfigOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5 text-primary" />
              {t("boardConfig.title")}
            </DialogTitle>
            <DialogDescription>{t("boardConfig.subtitle")}</DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSaveBoardConfig} className="space-y-4 pt-2">
            {configError && (
              <Alert variant="destructive">
                <AlertDescription>{configError}</AlertDescription>
              </Alert>
            )}

            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setConfigType("internal")}
                className={`flex flex-col items-center justify-center p-3 rounded-lg border-2 text-center transition-all ${
                  configType === "internal"
                    ? "border-primary bg-primary/5 text-primary font-semibold"
                    : "border-gray-200 text-gray-600 hover:border-gray-300"
                }`}
              >
                <Database className="w-5 h-5 mb-1.5" />
                <span className="text-xs font-medium">
                  {t("boardConfig.internalOption")}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setConfigType("specific")}
                className={`flex flex-col items-center justify-center p-3 rounded-lg border-2 text-center transition-all ${
                  configType === "specific"
                    ? "border-primary bg-primary/5 text-primary font-semibold"
                    : "border-gray-200 text-gray-600 hover:border-gray-300"
                }`}
              >
                <FolderKanban className="w-5 h-5 mb-1.5" />
                <span className="text-xs font-medium">
                  {t("boardConfig.specificOption")}
                </span>
              </button>
            </div>

            {configType === "specific" && (
              <div className="space-y-2 pt-1">
                <Label htmlFor="desktopBoardName">
                  {t("boardConfig.boardName")}
                </Label>
                <Input
                  id="desktopBoardName"
                  value={configBoardName}
                  onChange={(e) => setConfigBoardName(e.target.value)}
                  placeholder={
                    t("boardConfig.boardNamePlaceholder") || "nom-du-board"
                  }
                  autoFocus
                />
                <p className="text-xs text-muted-foreground">
                  {t("boardConfig.boardNameHelp")}
                </p>
              </div>
            )}

            <DialogFooter className="gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsConfigOpen(false)}
              >
                {t("common.cancel") || "Annuler"}
              </Button>
              <Button type="submit">{t("common.save") || "Enregistrer"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default LoginForm;

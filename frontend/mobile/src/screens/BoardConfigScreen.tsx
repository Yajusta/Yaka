import { useState, FormEvent, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Database, FolderKanban, Check, ArrowLeft } from "lucide-react";
import {
  saveBoardConfig,
  isInternalBoard,
  getCurrentBoardInfo,
} from "@shared/utils/boardUtils";
import { listsApi } from "@shared/services/listsApi";
import { resetUsersCache } from "@shared/services/api";

const BoardConfigScreen = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Mode de board : "internal" ou "specific"
  const [boardType, setBoardType] = useState<"internal" | "specific">(
    "internal",
  );
  const [boardName, setBoardName] = useState<string>("");
  const [error, setError] = useState<string>("");

  // Initialisation à partir de l'état actuel ou des query params
  useEffect(() => {
    const prefilledName = searchParams.get("prefill");
    if (prefilledName) {
      if (isInternalBoard(prefilledName)) {
        setBoardType("internal");
        setBoardName("");
      } else {
        setBoardType("specific");
        setBoardName(prefilledName);
      }
      return;
    }

    const currentInfo = getCurrentBoardInfo();
    if (currentInfo.isInternal) {
      setBoardType("internal");
      setBoardName("");
    } else {
      setBoardType("specific");
      setBoardName(currentInfo.boardName);
    }
  }, [searchParams]);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");

    if (boardType === "specific" && !boardName.trim()) {
      setError(
        t("boardConfig.nameRequired") || "Veuillez saisir un nom de board",
      );
      return;
    }

    // Sauvegarder la nouvelle configuration
    const selectedName = boardType === "internal" ? null : boardName.trim();
    const resolved = saveBoardConfig(selectedName);

    // Invalider les caches pour forcer le rafraîchissement complet
    listsApi.invalidateCache();
    resetUsersCache();

    // Rediriger vers la page de login de la board correspondante
    if (resolved.isInternal) {
      navigate("/login");
    } else {
      navigate(`/board/${encodeURIComponent(resolved.boardName)}/login`);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background relative">
      {/* Bouton retour en haut à gauche */}
      <button
        onClick={() => navigate(-1)}
        className="absolute top-4 left-4 p-2 text-muted-foreground hover:text-foreground active:text-primary transition-colors rounded-full"
        aria-label={t("common.back")}
      >
        <ArrowLeft className="w-6 h-6" />
      </button>

      <div className="w-full max-w-md space-y-6 animate-fade-in">
        {/* Logo */}
        <div className="text-center">
          <div className="flex justify-center mb-3">
            <img src="/yaka.svg" alt="Yaka" className="w-24 h-24" />
          </div>
          <h1 className="text-2xl font-bold text-foreground">
            {t("boardConfig.title")}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("boardConfig.subtitle")}
          </p>
        </div>

        {/* Formulaire */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-semibold text-foreground mb-3">
              {t("boardConfig.chooseType")}
            </label>

            {/* Sélecteur de type de board */}
            <div className="grid grid-cols-1 gap-3">
              {/* Option 1: Board interne */}
              <button
                type="button"
                onClick={() => {
                  setBoardType("internal");
                  setError("");
                }}
                className={`flex items-center justify-between p-4 rounded-xl border-2 text-left transition-all ${
                  boardType === "internal"
                    ? "border-emerald-500 bg-emerald-50/70 dark:bg-emerald-950/40 dark:border-emerald-500 shadow-sm"
                    : "border-border bg-card hover:bg-muted/40"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      boardType === "internal"
                        ? "bg-emerald-500 text-white"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    <Database className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="font-semibold text-foreground text-sm">
                      {t("boardConfig.internalOption")}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {t("boardConfig.internalDesc")}
                    </div>
                  </div>
                </div>
                {boardType === "internal" && (
                  <Check className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                )}
              </button>

              {/* Option 2: Board spécifique */}
              <button
                type="button"
                onClick={() => {
                  setBoardType("specific");
                  setError("");
                }}
                className={`flex items-center justify-between p-4 rounded-xl border-2 text-left transition-all ${
                  boardType === "specific"
                    ? "border-indigo-500 bg-indigo-50/70 dark:bg-indigo-950/40 dark:border-indigo-500 shadow-sm"
                    : "border-border bg-card hover:bg-muted/40"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      boardType === "specific"
                        ? "bg-indigo-500 text-white"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    <FolderKanban className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="font-semibold text-foreground text-sm">
                      {t("boardConfig.specificOption")}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {t("boardConfig.boardNameHelp")}
                    </div>
                  </div>
                </div>
                {boardType === "specific" && (
                  <Check className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                )}
              </button>
            </div>
          </div>

          {/* Saisie du nom si board spécifique */}
          {boardType === "specific" && (
            <div className="animate-slide-up pt-1">
              <label
                htmlFor="boardName"
                className="block text-sm font-medium text-foreground mb-2"
              >
                {t("boardConfig.boardName")}
              </label>
              <input
                id="boardName"
                type="text"
                value={boardName}
                onChange={(e) => {
                  setBoardName(e.target.value);
                  setError("");
                }}
                placeholder={
                  t("boardConfig.boardNamePlaceholder") || "nom-du-board"
                }
                autoFocus
                className="w-full px-4 py-3 bg-card border-2 border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
              <p className="mt-2 text-xs text-muted-foreground">
                Exemple: si l'adresse desktop est /board/
                <strong>mon-projet</strong>, saisissez{" "}
                <strong>mon-projet</strong>.
              </p>
            </div>
          )}

          {error && (
            <div className="p-3 bg-destructive/10 border-2 border-destructive/40 rounded-lg animate-slide-up">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          <button
            type="submit"
            className="w-full btn-touch bg-primary text-primary-foreground font-medium rounded-lg hover:bg-primary/90 active:bg-primary/80 transition-colors shadow-sm"
          >
            {t("common.continue")}
          </button>
        </form>
      </div>
    </div>
  );
};

export default BoardConfigScreen;

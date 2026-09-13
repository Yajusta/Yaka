import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Database, FolderKanban, ArrowRightLeft } from "lucide-react";
import { getCurrentBoardInfo } from "@shared/utils/boardUtils";

interface BoardStatusBadgeProps {
  /** Mode compact pour intégration dans un en-tête étroit */
  compact?: boolean;
  /** Permet de forcer un nom de board spécifique */
  boardName?: string;
  /** Afficher le bouton de changement de board */
  showSwitchButton?: boolean;
  /** Action personnalisée au clic sur le bouton de changement */
  onSwitchClick?: () => void;
  /** Classes CSS supplémentaires */
  className?: string;
}

export const BoardStatusBadge = ({
  compact = false,
  boardName,
  showSwitchButton = true,
  onSwitchClick,
  className = "",
}: BoardStatusBadgeProps) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const boardInfo =
    boardName !== undefined
      ? boardName
        ? { isInternal: false, displayName: boardName, boardName }
        : { isInternal: true, displayName: "Board interne", boardName: "" }
      : getCurrentBoardInfo();

  const handleSwitch = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onSwitchClick) {
      onSwitchClick();
    } else {
      const currentName = boardInfo.isInternal ? "" : boardInfo.boardName;
      navigate(
        `/config${currentName ? `?prefill=${encodeURIComponent(currentName)}` : ""}`,
      );
    }
  };

  if (compact) {
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
          boardInfo.isInternal
            ? "bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800"
            : "bg-indigo-50 text-indigo-800 border-indigo-300 dark:bg-indigo-950/50 dark:text-indigo-300 dark:border-indigo-800"
        } ${className}`}
        title={
          boardInfo.isInternal
            ? t("boardConfig.internalDesc")
            : t("boardConfig.specificDesc", { name: boardInfo.displayName })
        }
      >
        {boardInfo.isInternal ? (
          <Database className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
        ) : (
          <FolderKanban className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
        )}
        <span className="truncate max-w-[140px]">
          {boardInfo.isInternal
            ? t("boardConfig.internal")
            : boardInfo.displayName}
        </span>
        {showSwitchButton && (
          <button
            onClick={handleSwitch}
            className="ml-1 p-0.5 hover:bg-black/10 dark:hover:bg-white/10 rounded-full transition-colors"
            title={t("boardConfig.switchBoard")}
            aria-label={t("boardConfig.switchBoard")}
          >
            <ArrowRightLeft className="w-3 h-3 opacity-70 hover:opacity-100" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className={`flex items-center justify-between p-3 rounded-xl border shadow-sm transition-all ${
        boardInfo.isInternal
          ? "bg-emerald-50/70 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-900"
          : "bg-indigo-50/70 border-indigo-200 dark:bg-indigo-950/30 dark:border-indigo-900"
      } ${className}`}
    >
      <div className="flex items-center gap-3 min-w-0">
        <div
          className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
            boardInfo.isInternal
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300"
              : "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/60 dark:text-indigo-300"
          }`}
        >
          {boardInfo.isInternal ? (
            <Database className="w-5 h-5" />
          ) : (
            <FolderKanban className="w-5 h-5" />
          )}
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span
              className={`text-xs uppercase font-bold tracking-wider ${
                boardInfo.isInternal
                  ? "text-emerald-700 dark:text-emerald-400"
                  : "text-indigo-700 dark:text-indigo-400"
              }`}
            >
              {boardInfo.isInternal
                ? t("boardConfig.internal")
                : t("boardConfig.specific")}
            </span>
          </div>
          <p className="text-sm font-semibold text-foreground truncate">
            {boardInfo.isInternal
              ? t("boardConfig.internalDesc")
              : boardInfo.displayName}
          </p>
        </div>
      </div>

      {showSwitchButton && (
        <button
          onClick={handleSwitch}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors shrink-0 ml-2 ${
            boardInfo.isInternal
              ? "bg-emerald-100/60 text-emerald-800 border-emerald-300 hover:bg-emerald-100 active:bg-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-200 dark:border-emerald-800"
              : "bg-indigo-100/60 text-indigo-800 border-indigo-300 hover:bg-indigo-100 active:bg-indigo-200 dark:bg-indigo-900/40 dark:text-indigo-200 dark:border-indigo-800"
          }`}
        >
          <ArrowRightLeft className="w-3.5 h-3.5" />
          <span>{t("boardConfig.switchBoard")}</span>
        </button>
      )}
    </div>
  );
};

export default BoardStatusBadge;

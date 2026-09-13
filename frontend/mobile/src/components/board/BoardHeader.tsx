import { User } from "@shared/types";
import { Monitor } from "lucide-react";
import { useTranslation } from "react-i18next";

import { getCurrentBoardInfo } from "@shared/utils/boardUtils";
import BoardStatusBadge from "./BoardStatusBadge";

interface BoardHeaderProps {
  boardTitle: string;
  user: User;
  onMenuClick: () => void;
}

const BoardHeader = ({ boardTitle, user, onMenuClick }: BoardHeaderProps) => {
  const { t } = useTranslation();

  const getInitials = (name?: string, email?: string) => {
    if (name) {
      return name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .substring(0, 2);
    }
    if (email) {
      return email.substring(0, 2).toUpperCase();
    }
    return "U";
  };

  // Check if user is on desktop browser
  const isDesktop = (): boolean => {
    const userAgent =
      navigator.userAgent || navigator.vendor || (window as any).opera;
    return !/android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(
      userAgent,
    );
  };

  // Get desktop URL with board path if applicable
  const getDesktopUrl = (): string => {
    const boardInfo = getCurrentBoardInfo();
    const baseUrl = (window as any).BASE_URL || "http://localhost:3000";
    const separator = baseUrl.endsWith("/") ? "" : "/";

    if (!boardInfo.isInternal && boardInfo.boardName) {
      return `${baseUrl}${separator}board/${encodeURIComponent(boardInfo.boardName)}`;
    }
    return baseUrl;
  };

  return (
    <header className="mobile-header">
      {/* Left: App icon */}
      <div className="flex items-center justify-center p-1">
        <img src="/yaka.svg" alt="App icon" className="w-9 h-9" />
      </div>

      {/* Center: Board title & compact badge */}
      <div className="flex-1 flex flex-col items-center justify-center px-2 min-w-0">
        <h1 className="text-base font-bold text-foreground truncate max-w-full text-center leading-tight">
          {boardTitle}
        </h1>
        <div className="mt-0.5">
          <BoardStatusBadge compact={true} />
        </div>
      </div>

      {/* Right: Desktop switch (if desktop detected) + User avatar */}
      <div className="flex items-center gap-2">
        {/* Desktop switch - only show on desktop browsers */}
        {isDesktop() && (
          <button
            onClick={() => (window.location.href = getDesktopUrl())}
            className="flex items-center justify-center w-10 h-10 rounded-full bg-secondary text-secondary-foreground hover:bg-secondary/90 active:bg-secondary/80 transition-colors"
            aria-label={t("navigation.switchToDesktop")}
            title={t("navigation.switchToDesktop")}
          >
            <Monitor className="w-4 h-4" />
          </button>
        )}

        <button
          onClick={onMenuClick}
          className="flex items-center justify-center w-10 h-10 rounded-full bg-primary text-primary-foreground font-medium hover:bg-primary/90 active:bg-primary/80 transition-colors"
          aria-label={t("user.userMenu")}
        >
          {getInitials(user.display_name, user.email)}
        </button>
      </div>
    </header>
  );
};

export default BoardHeader;

import { useTranslation } from 'react-i18next';
import { User } from '@shared/types';
import { Monitor } from 'lucide-react';

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
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .substring(0, 2);
    }
    if (email) {
      return email.substring(0, 2).toUpperCase();
    }
    return 'U';
  };

  // Check if user is on desktop browser
  const isDesktop = (): boolean => {
    const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera;
    return !/android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
  };

  // Get desktop URL with board path if applicable
  const getDesktopUrl = (): string => {
    const currentPath = window.location.pathname;
    console.log('currentPath', currentPath);
    const boardMatch = currentPath.match(/^\/board\/([^\/]+)(.*)$/);
    console.log('boardMatch', boardMatch);
    if (boardMatch) {
      return `${(window as any).BASE_URL}/board/${boardMatch[1]}${boardMatch[2]}`;
    }
    console.log('BASE_URL', (window as any).BASE_URL);
    return (window as any).BASE_URL;
  };

  return (
    <header className="mobile-header">
      {/* Left: App icon */}
      <div className="flex items-center justify-center p-2">
        <img
          src="/icons/icon-48x48.png"
          alt="App icon"
          className="w-6 h-6"
        />
      </div>

      {/* Center: Board title */}
      <h1 className="text-lg font-bold text-foreground truncate px-4 flex-1 text-center">
        {boardTitle}
      </h1>

      {/* Right: Desktop switch (if desktop detected) + User avatar */}
      <div className="flex items-center gap-2">
        {/* Desktop switch - only show on desktop browsers */}
        {isDesktop() && (
          <button
            onClick={() => window.location.href = getDesktopUrl()}
            className="flex items-center justify-center w-10 h-10 rounded-full bg-secondary text-secondary-foreground hover:bg-secondary/90 active:bg-secondary/80 transition-colors"
            aria-label={t('navigation.switchToDesktop')}
            title={t('navigation.switchToDesktop')}
          >
            <Monitor className="w-4 h-4" />
          </button>
        )}

        <button
          onClick={onMenuClick}
          className="flex items-center justify-center w-10 h-10 rounded-full bg-primary text-primary-foreground font-medium hover:bg-primary/90 active:bg-primary/80 transition-colors"
          aria-label={t('user.userMenu')}
        >
          {getInitials(user.display_name, user.email)}
        </button>
      </div>
    </header>
  );
};

export default BoardHeader;


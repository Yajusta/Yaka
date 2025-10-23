import { useTranslation } from 'react-i18next';
import { User } from '@shared/types';

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

      {/* Right: User avatar */}
      <button
        onClick={onMenuClick}
        className="flex items-center justify-center w-10 h-10 rounded-full bg-primary text-primary-foreground font-medium hover:bg-primary/90 active:bg-primary/80 transition-colors"
        aria-label={t('user.userMenu')}
      >
        {getInitials(user.display_name, user.email)}
      </button>
    </header>
  );
};

export default BoardHeader;


import { useTranslation } from 'react-i18next';
import { X, LogOut, Settings } from 'lucide-react';
import { User } from '@shared/types';

interface SettingsMenuProps {
  isOpen: boolean;
  onClose: () => void;
  user: User;
  onLogout: () => void;
}

const SettingsMenu = ({ isOpen, onClose, user, onLogout }: SettingsMenuProps) => {
  const { t } = useTranslation();

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 animate-fade-in"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 w-80 max-w-[85vw] bg-card shadow-xl z-50 animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b-2 border-border">
          <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
            <Settings className="w-5 h-5" />
            {t('navigation.settings')}
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-muted-foreground hover:text-foreground active:bg-accent rounded-lg transition-colors"
            aria-label={t('common.close')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-6">
          {/* User info */}
          <div className="p-4 bg-muted/50 rounded-lg">
            <p className="text-sm font-medium text-foreground">
              {user.display_name || user.email}
            </p>
            <p className="text-xs text-muted-foreground mt-1">{user.email}</p>
            {user.role && (
              <p className="text-xs text-muted-foreground mt-1 capitalize">
                {t(`role.${user.role}`)}
              </p>
            )}
          </div>

          {/* Placeholder message */}
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-sm">{t('settings.comingSoon')}</p>
          </div>

          {/* Logout button */}
          <button
            onClick={() => {
              onLogout();
              onClose();
            }}
            className="w-full btn-touch bg-destructive text-destructive-foreground font-medium rounded-lg hover:bg-destructive/90 active:bg-destructive/80 transition-colors flex items-center justify-center gap-2"
          >
            <LogOut className="w-5 h-5" />
            {t('auth.logout')}
          </button>
        </div>
      </div>
    </>
  );
};

export default SettingsMenu;


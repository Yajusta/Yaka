import { useTranslation } from 'react-i18next';
import { Users, Tag, List, BookOpen, Palette, AlertCircle } from 'lucide-react';

interface AdminSettingsMenuProps {
  onBack: () => void;
  onClose: () => void;
}

const AdminSettingsMenu = ({ onClose }: AdminSettingsMenuProps) => {
  const { t } = useTranslation();

  const handleOptionClick = (option: string) => {
    // Close the settings menu and show a message
    // In a full implementation, these would open their respective admin panels
    alert(t('settings.comingSoon') + ': ' + option);
    onClose();
  };

  return (
    <div className="p-4 space-y-4">
      {/* Info message */}
      <div className="flex items-start gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-700 dark:text-amber-400">
        <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
        <p>
          {t('settings.comingSoon')}. Les fonctionnalités d'administration complètes sont disponibles sur la version desktop.
        </p>
      </div>

      {/* Admin options */}
      <div className="space-y-2">
        <button
          onClick={() => handleOptionClick(t('settings.interface'))}
          className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 active:bg-muted transition-colors text-left"
        >
          <Palette className="w-5 h-5 text-muted-foreground" />
          <div className="flex-1">
            <div className="text-sm font-medium">{t('settings.interface')}</div>
            <div className="text-xs text-muted-foreground">{t('settings.interfaceDescription')}</div>
          </div>
        </button>

        <button
          onClick={() => handleOptionClick(t('navigation.users'))}
          className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 active:bg-muted transition-colors text-left"
        >
          <Users className="w-5 h-5 text-muted-foreground" />
          <div className="flex-1">
            <div className="text-sm font-medium">{t('navigation.users')}</div>
            <div className="text-xs text-muted-foreground">{t('user.userManagement')}</div>
          </div>
        </button>

        <button
          onClick={() => handleOptionClick(t('navigation.lists'))}
          className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 active:bg-muted transition-colors text-left"
        >
          <List className="w-5 h-5 text-muted-foreground" />
          <div className="flex-1">
            <div className="text-sm font-medium">{t('navigation.lists')}</div>
            <div className="text-xs text-muted-foreground">{t('list.listManagement')}</div>
          </div>
        </button>

        <button
          onClick={() => handleOptionClick(t('navigation.labels'))}
          className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 active:bg-muted transition-colors text-left"
        >
          <Tag className="w-5 h-5 text-muted-foreground" />
          <div className="flex-1">
            <div className="text-sm font-medium">{t('navigation.labels')}</div>
            <div className="text-xs text-muted-foreground">{t('label.labelManagement')}</div>
          </div>
        </button>

        <button
          onClick={() => handleOptionClick(t('dictionary.globalDictionary'))}
          className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 active:bg-muted transition-colors text-left"
        >
          <BookOpen className="w-5 h-5 text-muted-foreground" />
          <div className="flex-1">
            <div className="text-sm font-medium">{t('dictionary.globalDictionary')}</div>
            <div className="text-xs text-muted-foreground">Gestion du dictionnaire global</div>
          </div>
        </button>
      </div>
    </div>
  );
};

export default AdminSettingsMenu;


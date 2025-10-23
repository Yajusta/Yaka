import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  ArrowLeft,
  LogOut, 
  Settings, 
  Languages, 
  Eye, 
  Palette, 
  BookOpen, 
  ShieldCheck,
  ChevronRight,
  Check,
  Sun,
  Moon
} from 'lucide-react';
import { User } from '@shared/types';
import { useTheme } from '@shared/hooks/useTheme';
import { useDisplayMode, DisplayMode } from '@shared/hooks/useDisplayMode';
import { usePermissions } from '@shared/hooks/usePermissions';
import { userService, authService } from '@shared/services/api';
import PersonalDictionaryMenu from './PersonalDictionaryMenu.tsx';
import AdminSettingsMenu from './AdminSettingsMenu.tsx';

interface SettingsMenuProps {
  isOpen: boolean;
  onClose: () => void;
  user: User;
  onLogout: () => void;
}

type SubMenu = 'main' | 'language' | 'display' | 'theme' | 'dictionary' | 'admin';

const SettingsMenu = ({ isOpen, onClose, user, onLogout }: SettingsMenuProps) => {
  const { t, i18n } = useTranslation();
  const { theme, toggleTheme } = useTheme();
  const { displayMode, setDisplayMode } = useDisplayMode();
  const permissions = usePermissions(user);
  const [currentMenu, setCurrentMenu] = useState<SubMenu>('main');
  const [isChangingLanguage, setIsChangingLanguage] = useState(false);

  const handleChangeLanguage = async (lng: string) => {
    setIsChangingLanguage(true);
    try {
      await i18n.changeLanguage(lng);

      if (authService.isAuthenticated()) {
        try {
          await userService.updateLanguage(lng);
          const currentUser = authService.getCurrentUserFromStorage();
          if (currentUser) {
            const updatedUser = { ...currentUser, language: lng };
            authService.setCurrentUserToStorage(updatedUser);
          }
        } catch (error) {
          console.error('Failed to update language in database:', error);
        }
      }
    } catch (error) {
      console.error('Failed to change language:', error);
    } finally {
      setIsChangingLanguage(false);
    }
  };

  const handleDisplayModeChange = (mode: DisplayMode) => {
    setDisplayMode(mode);
  };

  const goBack = () => {
    setCurrentMenu('main');
  };

  const handleClose = () => {
    setCurrentMenu('main');
    onClose();
  };

  if (!isOpen) return null;

  const getTitle = () => {
    switch (currentMenu) {
      case 'main':
        return t('navigation.settings');
      case 'language':
        return t('language.switchLanguage');
      case 'display':
        return t('display.title');
      case 'theme':
        return t('settings.theme');
      case 'dictionary':
        return t('dictionary.personalDictionary');
      case 'admin':
        return t('settings.admin');
      default:
        return t('navigation.settings');
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 animate-fade-in"
        onClick={handleClose}
      />

      {/* Full screen page */}
      <div className="fixed inset-0 bg-background z-50 overflow-y-auto animate-slide-up">
        {/* Header */}
        <div className="sticky top-0 bg-card border-b-2 border-border z-10">
          <div className="flex items-center justify-between p-4" style={{ paddingTop: 'calc(1rem + env(safe-area-inset-top))' }}>
            <button
              onClick={currentMenu === 'main' ? handleClose : goBack}
              className="p-2 -ml-2 text-muted-foreground hover:text-foreground active:bg-accent rounded-lg transition-colors"
              aria-label={currentMenu === 'main' ? t('common.close') : t('common.back')}
            >
              <ArrowLeft className="w-6 h-6" />
            </button>

            <div className="flex items-center gap-2">
              <Settings className="w-5 h-5 text-primary" />
              <h1 className="text-lg font-bold text-foreground">{getTitle()}</h1>
            </div>

            {/* Empty space for balance */}
            <div className="w-10" />
          </div>
        </div>

        {/* Content */}
        <div className="pb-safe">
          {/* Main Menu */}
          {currentMenu === 'main' && (
            <div className="p-4 space-y-6">
              {/* User info */}
              <div className="p-4 bg-muted/50 rounded-lg border border-border">
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

              {/* Settings options */}
              <div className="space-y-2">
                {/* Language */}
                <button
                  onClick={() => setCurrentMenu('language')}
                  className="w-full flex items-center justify-between p-4 rounded-lg bg-card border border-border hover:bg-muted/50 active:bg-muted transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <Languages className="w-5 h-5 text-primary" />
                    <span className="text-sm font-medium text-foreground">{t('language.switchLanguage')}</span>
                  </div>
                  <ChevronRight className="w-5 h-5 text-muted-foreground" />
                </button>

                {/* Display Mode */}
                <button
                  onClick={() => setCurrentMenu('display')}
                  className="w-full flex items-center justify-between p-4 rounded-lg bg-card border border-border hover:bg-muted/50 active:bg-muted transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <Eye className="w-5 h-5 text-primary" />
                    <span className="text-sm font-medium text-foreground">{t('display.title')}</span>
                  </div>
                  <ChevronRight className="w-5 h-5 text-muted-foreground" />
                </button>

                {/* Theme */}
                <button
                  onClick={() => setCurrentMenu('theme')}
                  className="w-full flex items-center justify-between p-4 rounded-lg bg-card border border-border hover:bg-muted/50 active:bg-muted transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <Palette className="w-5 h-5 text-primary" />
                    <span className="text-sm font-medium text-foreground">{t('settings.theme')}</span>
                  </div>
                  <ChevronRight className="w-5 h-5 text-muted-foreground" />
                </button>

                {/* Personal Dictionary - Only for editors and above */}
                {permissions.isEditorOrAbove && (
                  <button
                    onClick={() => setCurrentMenu('dictionary')}
                    className="w-full flex items-center justify-between p-4 rounded-lg bg-card border border-border hover:bg-muted/50 active:bg-muted transition-colors text-left"
                  >
                    <div className="flex items-center gap-3">
                      <BookOpen className="w-5 h-5 text-primary" />
                      <span className="text-sm font-medium text-foreground">{t('dictionary.personalDictionary')}</span>
                    </div>
                    <ChevronRight className="w-5 h-5 text-muted-foreground" />
                  </button>
                )}

                {/* Admin Settings - Only for admins */}
                {permissions.isAdmin && (
                  <button
                    onClick={() => setCurrentMenu('admin')}
                    className="w-full flex items-center justify-between p-4 rounded-lg bg-card border border-border hover:bg-muted/50 active:bg-muted transition-colors text-left"
                  >
                    <div className="flex items-center gap-3">
                      <ShieldCheck className="w-5 h-5 text-primary" />
                      <span className="text-sm font-medium text-foreground">{t('settings.admin')}</span>
                    </div>
                    <ChevronRight className="w-5 h-5 text-muted-foreground" />
                  </button>
                )}
              </div>

              {/* Logout button */}
              <button
                onClick={() => {
                  onLogout();
                  handleClose();
                }}
                className="w-full btn-touch bg-destructive text-destructive-foreground font-medium rounded-lg hover:bg-destructive/90 active:bg-destructive/80 transition-colors flex items-center justify-center gap-2 mt-8"
              >
                <LogOut className="w-5 h-5" />
                {t('auth.logout')}
              </button>
            </div>
          )}

          {/* Language Menu */}
          {currentMenu === 'language' && (
            <div className="p-4 space-y-2">
              <button
                onClick={() => handleChangeLanguage('fr')}
                disabled={isChangingLanguage}
                className={`w-full flex items-center justify-between p-4 rounded-lg bg-card border-2 transition-colors ${
                  i18n.language === 'fr' ? 'border-primary bg-primary/10' : 'border-border hover:bg-muted/50 active:bg-muted'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">🇫🇷</span>
                  <span className="text-sm font-medium text-foreground">Français</span>
                </div>
                {i18n.language === 'fr' && <Check className="w-5 h-5 text-primary" />}
              </button>

              <button
                onClick={() => handleChangeLanguage('en')}
                disabled={isChangingLanguage}
                className={`w-full flex items-center justify-between p-4 rounded-lg bg-card border-2 transition-colors ${
                  i18n.language === 'en' ? 'border-primary bg-primary/10' : 'border-border hover:bg-muted/50 active:bg-muted'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">🇬🇧</span>
                  <span className="text-sm font-medium text-foreground">English</span>
                </div>
                {i18n.language === 'en' && <Check className="w-5 h-5 text-primary" />}
              </button>
            </div>
          )}

          {/* Display Mode Menu */}
          {currentMenu === 'display' && (
            <div className="p-4 space-y-2">
              <button
                onClick={() => handleDisplayModeChange('extended')}
                className={`w-full flex items-center justify-between p-4 rounded-lg bg-card border-2 transition-colors ${
                  displayMode === 'extended' ? 'border-primary bg-primary/10' : 'border-border hover:bg-muted/50 active:bg-muted'
                }`}
              >
                <div className="flex flex-col items-start">
                  <span className="text-sm font-medium text-foreground">{t('display.extended')}</span>
                  <span className="text-xs text-muted-foreground">{t('display.extendedDescription')}</span>
                </div>
                {displayMode === 'extended' && <Check className="w-5 h-5 text-primary" />}
              </button>

              <button
                onClick={() => handleDisplayModeChange('compact')}
                className={`w-full flex items-center justify-between p-4 rounded-lg bg-card border-2 transition-colors ${
                  displayMode === 'compact' ? 'border-primary bg-primary/10' : 'border-border hover:bg-muted/50 active:bg-muted'
                }`}
              >
                <div className="flex flex-col items-start">
                  <span className="text-sm font-medium text-foreground">{t('display.compact')}</span>
                  <span className="text-xs text-muted-foreground">{t('display.compactDescription')}</span>
                </div>
                {displayMode === 'compact' && <Check className="w-5 h-5 text-primary" />}
              </button>
            </div>
          )}

          {/* Theme Menu */}
          {currentMenu === 'theme' && (
            <div className="p-4 space-y-2">
              <button
                onClick={toggleTheme}
                className={`w-full flex items-center justify-between p-4 rounded-lg bg-card border-2 transition-colors ${
                  theme === 'light' ? 'border-primary bg-primary/10' : 'border-border hover:bg-muted/50 active:bg-muted'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Sun className="w-5 h-5 text-amber-500" />
                  <span className="text-sm font-medium text-foreground">{t('settings.lightTheme')}</span>
                </div>
                {theme === 'light' && <Check className="w-5 h-5 text-primary" />}
              </button>

              <button
                onClick={toggleTheme}
                className={`w-full flex items-center justify-between p-4 rounded-lg bg-card border-2 transition-colors ${
                  theme === 'dark' ? 'border-primary bg-primary/10' : 'border-border hover:bg-muted/50 active:bg-muted'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Moon className="w-5 h-5 text-blue-500" />
                  <span className="text-sm font-medium text-foreground">{t('settings.darkTheme')}</span>
                </div>
                {theme === 'dark' && <Check className="w-5 h-5 text-primary" />}
              </button>
            </div>
          )}

          {/* Personal Dictionary Menu */}
          {currentMenu === 'dictionary' && (
            <PersonalDictionaryMenu onBack={goBack} />
          )}

          {/* Admin Settings Menu */}
          {currentMenu === 'admin' && (
            <AdminSettingsMenu onBack={goBack} onClose={handleClose} />
          )}
        </div>
      </div>
    </>
  );
};

export default SettingsMenu;


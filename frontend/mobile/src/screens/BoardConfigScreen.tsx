import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const BoardConfigScreen = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [apiUrl, setApiUrl] = useState<string>(
    localStorage.getItem('api_base_url') || 'http://localhost:8000'
  );
  const [error, setError] = useState<string>('');

  const validateUrl = (url: string): boolean => {
    try {
      const urlObj = new URL(url);
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:';
    } catch {
      return false;
    }
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');

    if (!apiUrl.trim()) {
      setError(t('boardConfig.urlRequired'));
      return;
    }

    if (!validateUrl(apiUrl)) {
      setError(t('boardConfig.invalidUrl'));
      return;
    }

    // Remove trailing slash
    const cleanUrl = apiUrl.trim().replace(/\/$/, '');
    localStorage.setItem('api_base_url', cleanUrl);
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background">
      <div className="w-full max-w-md space-y-8 animate-fade-in">
        {/* Logo */}
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <div className="w-24 h-24 bg-primary rounded-2xl flex items-center justify-center">
              <span className="text-4xl font-bold text-primary-foreground">Y</span>
            </div>
          </div>
          <h1 className="text-3xl font-bold text-foreground">
            {t('app.name', 'Yaka')}
          </h1>
          <p className="mt-2 text-muted-foreground">
            {t('boardConfig.subtitle', 'Configuration de la connexion')}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              htmlFor="apiUrl"
              className="block text-sm font-medium text-foreground mb-2"
            >
              {t('boardConfig.apiUrl', 'URL de l\'API')}
            </label>
            <input
              id="apiUrl"
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="https://api.yaka.example.com"
              className="w-full px-4 py-3 bg-card border-2 border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
            <p className="mt-2 text-xs text-muted-foreground">
              {t('boardConfig.urlHelp', 'Exemple: http://localhost:8000 ou https://api.yaka.com')}
            </p>
          </div>

          {error && (
            <div className="p-4 bg-destructive/10 border-2 border-destructive/40 rounded-lg">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          <button
            type="submit"
            className="w-full btn-touch bg-primary text-primary-foreground font-medium rounded-lg hover:bg-primary/90 active:bg-primary/80 transition-colors"
          >
            {t('common.continue', 'Continuer')}
          </button>
        </form>

        {/* Info */}
        <div className="text-center text-xs text-muted-foreground">
          <p>{t('boardConfig.info', 'Cette URL sera utilisée pour toutes les requêtes API')}</p>
        </div>
      </div>
    </div>
  );
};

export default BoardConfigScreen;


import { useState, FormEvent, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@shared/hooks/useAuth';
import { boardSettingsService } from '@shared/services/api';
import { Loader2, Settings } from 'lucide-react';

const LoginScreen = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [boardTitle, setBoardTitle] = useState<string>('Yaka'); // Default fallback

  // Fetch board title on component mount
  useEffect(() => {
    const fetchBoardTitle = async () => {
      try {
        const titleData = await boardSettingsService.getBoardTitle();
        setBoardTitle(titleData.title);
      } catch (error) {
        console.error('Failed to fetch board title:', error);
        // Keep default 'Yaka' title on error
      }
    };

    fetchBoardTitle();
  }, []);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || t('auth.loginError'));
    } finally {
      setLoading(false);
    }
  };

  const handleConfigClick = () => {
    const currentBoardName = localStorage.getItem('board_name') || '';
    if (currentBoardName) {
      navigate(`/config?prefill=${encodeURIComponent(currentBoardName)}`);
    } else {
      navigate('/config');
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background">
      {/* Config button */}
      <button
        onClick={handleConfigClick}
        className="absolute top-4 right-4 p-2 text-muted-foreground hover:text-foreground active:text-primary transition-colors"
      >
        <Settings className="w-6 h-6" />
      </button>

      <div className="w-full max-w-md space-y-8 animate-fade-in">
        {/* Logo */}
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <img src="/yaka.svg" alt="Yaka" className="w-32 h-32" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">
            {boardTitle}
          </h1>
          <p className="mt-2 text-muted-foreground">
            {t('auth.connectToAccount')}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-foreground mb-2"
            >
              {t('auth.email')}
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="admin@yaka.local"
              className="w-full px-4 py-3 bg-card border-2 border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-foreground mb-2"
            >
              {t('auth.password')}
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              placeholder="••••••••"
              className="w-full px-4 py-3 bg-card border-2 border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          {error && (
            <div className="p-4 bg-destructive/10 border-2 border-destructive/40 rounded-lg animate-slide-up">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full btn-touch bg-primary text-primary-foreground font-medium rounded-lg hover:bg-primary/90 active:bg-primary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
          >
            {loading && <Loader2 className="mr-2 h-5 w-5 animate-spin" />}
            {t('auth.login')}
          </button>
        </form>

        {/* Board name info */}
        <div className="text-center text-xs text-muted-foreground">
          <p>
            Board: {localStorage.getItem('board_name') || 'Not configured'}
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginScreen;


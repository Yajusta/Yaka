import { useState, FormEvent, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const BoardConfigScreen = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [boardName, setBoardName] = useState<string>('');
  const [error, setError] = useState<string>('');

  // Initialize board name from localStorage or URL params
  useEffect(() => {
    const currentBoardName = localStorage.getItem('board_name') || '';
    const prefilledName = searchParams.get('prefill') || currentBoardName;
    setBoardName(prefilledName);
  }, [searchParams]);

  const resolveEndpoint = (name: string): string => {
    const apiBaseUrl = (window as any).API_BASE_URL || 'http://localhost:8000';

    if (name.trim().toLowerCase() === 'localhost') {
      return apiBaseUrl;
    } else {
      return `${apiBaseUrl}/board/${encodeURIComponent(name.trim())}`;
    }
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');

    if (!boardName.trim()) {
      setError('Please enter a board name');
      return;
    }

    const resolvedEndpoint = resolveEndpoint(boardName);

    // Store both the board name and the resolved endpoint
    localStorage.setItem('board_name', boardName.trim());
    localStorage.setItem('api_base_url', resolvedEndpoint);
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background">
      <div className="w-full max-w-md space-y-8 animate-fade-in">
        {/* Logo */}
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <img src="/yaka.svg" alt="Yaka" className="w-32 h-32" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">
            {t('app.name')}
          </h1>
          <p className="mt-2 text-muted-foreground">
            {t('boardConfig.subtitle')}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              htmlFor="boardName"
              className="block text-sm font-medium text-foreground mb-2"
            >
              Board name
            </label>
            <input
              id="boardName"
              type="text"
              value={boardName}
              onChange={(e) => setBoardName(e.target.value)}
              placeholder="your-board-name"
              className="w-full px-4 py-3 bg-card border-2 border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
            <p className="mt-2 text-xs text-muted-foreground">
              If your desktop access point is <br/>"https://yaka.yajusta.fr/board/your-board-name"<br/>enter "your-board-name" here.
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
            {t('common.continue')}
          </button>
        </form>

      </div>
    </div>
  );
};

export default BoardConfigScreen;


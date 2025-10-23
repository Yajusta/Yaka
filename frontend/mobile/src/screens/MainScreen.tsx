import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@shared/hooks/useAuth';
import { listsApi } from '@shared/services/listsApi';
import { cardService } from '@shared/services/api';
import { KanbanList, Card } from '@shared/types';
import BoardHeader from '../components/board/BoardHeader';
import ListsView from '../components/board/ListsView';
import BottomNav from '../components/navigation/BottomNav';
import SettingsMenu from '../components/settings/SettingsMenu';
import { Loader2 } from 'lucide-react';

const MainScreen = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [lists, setLists] = useState<KanbanList[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [boardTitle] = useState<string>('Yaka');

  useEffect(() => {
    const loadData = async () => {
      if (!user) {
        navigate('/login');
        return;
      }

      try {
        setLoading(true);
        setError('');

        // Load lists and cards in parallel
        const [listsData, cardsData] = await Promise.all([
          listsApi.getLists(),
          cardService.getCards({})
        ]);

        // Sort lists by order
        const sortedLists = listsData.sort((a, b) => a.order - b.order);
        setLists(sortedLists);
        setCards(cardsData);
      } catch (err: any) {
        console.error('Error loading data:', err);
        setError(err.response?.data?.detail || t('app.loadDataError'));
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [user, navigate, t]);

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  const handleCardClick = (card: Card) => {
    // Placeholder: will open card details in future
    console.log('Card clicked:', card);
  };

  const handleCardUpdate = (updatedCard: Card) => {
    // Update the card in the local state
    setCards(prevCards =>
      prevCards.map(card =>
        card.id === updatedCard.id ? updatedCard : card
      )
    );
  };

  const handleFilterClick = () => {
    // Placeholder: will open filters modal in future
    console.log('Filter clicked');
  };

  const handleVoiceClick = () => {
    // Placeholder: will open voice input in future
    console.log('Voice clicked');
  };

  const handleNewCardClick = () => {
    // Placeholder: will open new card form in future
    console.log('New card clicked');
  };

  if (!user) {
    return null;
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">{t('common.loading')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-6">
        <div className="text-center">
          <div className="p-4 bg-destructive/10 border-2 border-destructive/40 rounded-lg mb-4">
            <p className="text-destructive">{error}</p>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="btn-touch bg-primary text-primary-foreground px-6 rounded-lg"
          >
            {t('common.retry')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      {/* Header */}
      <BoardHeader
        boardTitle={boardTitle}
        user={user}
        onMenuClick={() => setShowSettings(true)}
      />

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-4 smooth-scroll" style={{ paddingTop: 'calc(56px + env(safe-area-inset-top))', paddingBottom: 'calc(60px + env(safe-area-inset-bottom))' }}>
        <ListsView
          lists={lists}
          cards={cards}
          onCardClick={handleCardClick}
          onCardUpdate={handleCardUpdate}
        />
      </main>

      {/* Bottom navigation */}
      <BottomNav
        onFilterClick={handleFilterClick}
        onVoiceClick={handleVoiceClick}
        onNewCardClick={handleNewCardClick}
      />

      {/* Settings menu */}
      <SettingsMenu
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        user={user}
        onLogout={handleLogout}
      />
    </div>
  );
};

export default MainScreen;


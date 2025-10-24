import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@shared/hooks/useAuth';
import { useBoardSettings } from '@shared/hooks/useBoardSettings';
import { useUsers } from '@shared/hooks/useUsers';
import { listsApi } from '@shared/services/listsApi';
import { cardService } from '@shared/services/api';
import { labelService } from '@shared/services/api';
import { KanbanList, Card, Label } from '@shared/types';
import BoardHeader from '../components/board/BoardHeader';
import ListsView from '../components/board/ListsView';
import BottomNav from '../components/navigation/BottomNav';
import SettingsMenu from '../components/settings/SettingsMenu';
import CardDetail from '../components/card/CardDetail';
import VoiceInputDialog from '../components/voice/VoiceInputDialog';
import { FilterScreen } from './FilterScreen';
import { Loader2 } from 'lucide-react';

const MainScreen = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { boardTitle } = useBoardSettings();
  const { users, refresh: refreshUsers } = useUsers();
  const [lists, setLists] = useState<KanbanList[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [allCards, setAllCards] = useState<Card[]>([]);
  const [labels, setLabels] = useState<Label[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [selectedCard, setSelectedCard] = useState<Card | null>(null);
  const [showVoiceInput, setShowVoiceInput] = useState<boolean>(false);
  const [isCreatingNewCard, setIsCreatingNewCard] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const [filters, setFilters] = useState({
    search: '',
    assignee_ids: null as number[] | null,
    priorities: null as string[] | null,
    label_ids: null as number[] | null,
  });

  
  const loadData = async (isRefresh = false) => {
    if (!user) {
      navigate('/login');
      return;
    }

    try {
      if (isRefresh) {
        setIsRefreshing(true);
      } else {
        setLoading(true);
      }
      setError('');

      // Load lists, cards and labels in parallel
      const [listsData, cardsData, labelsData] = await Promise.all([
        listsApi.getLists(),
        cardService.getCards({}),
        labelService.getLabels()
      ]);

      
      // Sort lists by order
      const sortedLists = listsData.sort((a, b) => a.order - b.order);
      setLists(sortedLists);
      setAllCards(cardsData);
      setLabels(labelsData);

      // Refresh users list
      refreshUsers();
    } catch (err: any) {
      console.error('Error loading data:', err);
      setError(err.response?.data?.detail || t('app.loadDataError'));
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [user, navigate, t, refreshUsers]);

  // Apply filters whenever filters or allCards change
  useEffect(() => {
    let filteredCards = allCards;

    // Search filter
    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      filteredCards = filteredCards.filter(card =>
        card.title.toLowerCase().includes(searchTerm) ||
        (card.description && card.description.toLowerCase().includes(searchTerm))
      );
    }

    // Assignee filter (multiple)
    if (filters.assignee_ids && filters.assignee_ids.length > 0) {
      filteredCards = filteredCards.filter(card =>
        card.assignee_id && filters.assignee_ids!.includes(card.assignee_id)
      );
    }

    // Priority filter (multiple)
    if (filters.priorities && filters.priorities.length > 0) {
      filteredCards = filteredCards.filter(card =>
        filters.priorities!.includes(card.priority)
      );
    }

    // Label filter (multiple)
    if (filters.label_ids && filters.label_ids.length > 0) {
      filteredCards = filteredCards.filter(card =>
        card.labels?.some(label => filters.label_ids!.includes(label.id))
      );
    }

    setCards(filteredCards);
  }, [filters, allCards]);

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  const handleCardClick = (card: Card) => {
    setSelectedCard(card);
  };

  const handleCardUpdate = (updatedCard: Card) => {
    // Update the card in the local state
    setCards(prevCards =>
      prevCards.map(card =>
        card.id === updatedCard.id ? updatedCard : card
      )
    );
  };

  const handleCardSave = (savedCard: Card) => {
    // If it's a new card, add it to the list
    if (isCreatingNewCard) {
      setCards(prevCards => [...prevCards, savedCard]);
      setIsCreatingNewCard(false);
    } else {
      // Otherwise update existing card
      handleCardUpdate(savedCard);
    }
  };

  const handleCardDelete = async (cardId: number) => {
    try {
      await cardService.deleteCard(cardId);
      setCards(prevCards => prevCards.filter(card => card.id !== cardId));
    } catch (error: any) {
      console.error('Error deleting card:', error);
    }
  };

  const handleFilterClick = () => {
    setShowFilters(true);
  };

  const handleFiltersChange = (newFilters: typeof filters) => {
    setFilters(newFilters);
  };

  // Calculate active filters count for badge
  const getActiveFiltersCount = () => {
    let count = 0;
    if (filters.search) count++;
    if (filters.assignee_ids && filters.assignee_ids.length > 0) count++;
    if (filters.priorities && filters.priorities.length > 0) count++;
    if (filters.label_ids && filters.label_ids.length > 0) count++;
    return count;
  };

  const handleVoiceClick = () => {
    setShowVoiceInput(true);
  };

  const handleVoiceCardSave = (savedCard: Card) => {
    // Check if this is a new card or an update
    const existingCard = cards.find(c => c.id === savedCard.id);
    if (existingCard) {
      // Update existing card
      setCards(prevCards =>
        prevCards.map(card =>
          card.id === savedCard.id ? savedCard : card
        )
      );
    } else {
      // Add new card
      setCards(prevCards => [...prevCards, savedCard]);
    }
  };

  // Pull to refresh handlers
  
  const handleNewCardClick = () => {
    // Create a new card object with minimal data
    const newCard: Card = {
      id: 0, // Temporary ID, will be replaced by backend
      title: '',
      description: '',
      priority: 'medium',
      assignee_id: null,
      label_id: null,
      colonne: '',
      list_id: lists.length > 0 ? lists[0].id : 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      labels: [],
      items: []
    };
    setIsCreatingNewCard(true);
    setSelectedCard(newCard);
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
    <>
      {!showFilters ? (
        <div className="h-screen flex flex-col bg-background overflow-hidden">
          {/* Header */}
          <BoardHeader
            boardTitle={boardTitle}
            user={user}
            onMenuClick={() => setShowSettings(true)}
          />

          {/* Main content */}
          <main className="flex-1 overflow-hidden relative">
            <ListsView
              lists={lists}
              cards={cards}
              onCardClick={handleCardClick}
              onCardUpdate={handleCardUpdate}
              onRefresh={() => loadData(true)}
              isRefreshing={isRefreshing}
            />
          </main>

          {/* Bottom navigation */}
          <BottomNav
            onFilterClick={handleFilterClick}
            onVoiceClick={handleVoiceClick}
            onNewCardClick={handleNewCardClick}
            activeFiltersCount={getActiveFiltersCount()}
          />

          {/* Settings menu */}
          <SettingsMenu
            isOpen={showSettings}
            onClose={() => setShowSettings(false)}
            user={user}
            onLogout={handleLogout}
          />

          {/* Card detail modal */}
          {selectedCard && (
            <CardDetail
              card={selectedCard}
              isOpen={!!selectedCard}
              onClose={() => {
                setSelectedCard(null);
                setIsCreatingNewCard(false);
              }}
              onSave={handleCardSave}
              onDelete={isCreatingNewCard ? undefined : handleCardDelete}
            />
          )}

          {/* Voice input dialog */}
          <VoiceInputDialog
            isOpen={showVoiceInput}
            onClose={() => setShowVoiceInput(false)}
            onCardSave={handleVoiceCardSave}
            defaultListId={lists.length > 0 ? lists[0].id : undefined}
          />
        </div>
      ) : (
        /* Filter screen as full page */
        <FilterScreen
          onBack={() => setShowFilters(false)}
          filters={filters}
          onFiltersChange={handleFiltersChange}
          users={users}
          labels={labels}
        />
      )}
    </>
  );
};

export default MainScreen;


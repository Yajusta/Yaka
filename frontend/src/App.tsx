import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Route, BrowserRouter as Router, Routes, useLocation } from 'react-router-dom';
import { toast as sonnerToast } from 'sonner';
import { ListManager } from './components/admin';
import { InterfaceDialog } from './components/admin/InterfaceDialog';
import InvitePage from './components/auth/InvitePage.tsx';
import LoginForm from './components/auth/LoginForm.tsx';
import CardForm from './components/cards/CardForm.tsx';
import { FilterBar } from './components/common/FilterBar.tsx';
import { Footer } from './components/common/Footer.tsx';
import { Header } from './components/common/Header.tsx';
import LabelManager from './components/common/LabelManager.tsx';
import UsersManager from './components/common/UsersManager';
import { KanbanBoard } from './components/kanban/KanbanBoard.tsx';
import { Toaster } from './components/ui/sonner';
import { useToast } from './hooks/use-toast.tsx';
import { AuthProvider, useAuth } from './hooks/useAuth.tsx';
import { BoardSettingsProvider } from './hooks/useBoardSettingsContext';
import { usePermissions } from './hooks/usePermissions';
import { useTheme } from './hooks/useTheme.tsx';
import { useUserLanguage } from './hooks/useUserLanguage';
import { UsersProvider, useUsers } from './hooks/useUsers';
import { useDisplayMode } from './hooks/useDisplayMode';
import './index.css';
import { cardService, labelService } from './services/api.tsx';
import { Card, Label } from './types/index.ts';

interface Filters {
    search: string;
    assignee_id: number | null;
    priority: string | null;
    label_id: number | null;
}

const KanbanApp = () => {
    const { t } = useTranslation();
    const [showUsersManager, setShowUsersManager] = useState(false);
    const [showListManager, setShowListManager] = useState(false);
    const [showInterfaceDialog, setShowInterfaceDialog] = useState(false);
    const { user, loading, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();
    const { toast } = useToast();
    const permissions = usePermissions(user);
    const { displayMode, setDisplayMode } = useDisplayMode();

    const notifyPermissionDenied = () => {
        toast({
            title: t('card.permissionDenied'),
            variant: 'destructive'
        });
    };

    const [allCards, setAllCards] = useState<Card[]>([]);
    const [cards, setCards] = useState<Card[]>([]);
    const { users, refresh: refreshUsers } = useUsers();
    const [labels, setLabels] = useState<Label[]>([]);
    const [dataLoading, setDataLoading] = useState<boolean>(true);
    const [filters, setFilters] = useState<Filters>({
        search: '',
        assignee_id: null,
        priority: null,
        label_id: null
    });
    const [showCardForm, setShowCardForm] = useState<boolean>(false);
    const [editingCard, setEditingCard] = useState<Card | null>(null);
    const [showLabelManager, setShowLabelManager] = useState<boolean>(false);
    const [listsRefreshTrigger, setListsRefreshTrigger] = useState<number>(0);
    const [defaultListIdForNewCard, setDefaultListIdForNewCard] = useState<number | null>(null);

    // Calculer si une modale est ouverte pour masquer le TrashZone
    const isAnyModalOpen = showCardForm || showLabelManager || showListManager || showUsersManager || showInterfaceDialog;

    // Load initial data (cards + labels) - only when user changes, not filters
    useEffect(() => {
        const loadData = async () => {
            if (!user) {
                setDataLoading(false);
                return;
            }

            try {
                setDataLoading(true);
                // Request the users list for all authenticated users. The backend will
                // mask emails for non-admins, so it's safe to request this here.
                const [cardsData, labelsData] = await Promise.all([
                    cardService.getCards({}), // Load all cards without filters
                    labelService.getLabels()
                ]);

                setAllCards(cardsData);
                setLabels(labelsData);
            } catch (error) {
                console.error('Erreur lors du chargement des données:', error);
                toast({
                    title: t('app.loadDataError'),
                    description: t('errors.tryAgain'),
                    variant: "destructive"
                });
            } finally {
                setDataLoading(false);
            }
        };

        loadData();
    }, [user]); // Remove filters from dependency

    // Normalize text for accent-insensitive search
    const normalizeText = (text: string): string => {
        return text
            .toLowerCase()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, ''); // Remove diacritical marks
    };

    // Frontend filtering
    const filteredCards = useMemo(() => {
        let filtered = allCards;

        // Search filter
        if (filters.search) {
            const searchTerm = normalizeText(filters.search);
            filtered = filtered.filter(card =>
                normalizeText(card.title).includes(searchTerm) ||
                (card.description && normalizeText(card.description).includes(searchTerm))
            );
        }

        // Assignee filter
        if (filters.assignee_id) {
            filtered = filtered.filter(card => card.assignee_id === filters.assignee_id);
        }

        // Priority filter
        if (filters.priority) {
            filtered = filtered.filter(card => card.priority === filters.priority);
        }

        // Label filter
        if (filters.label_id) {
            filtered = filtered.filter(card =>
                card.labels?.some(label => label.id === filters.label_id)
            );
        }

        return filtered;
    }, [allCards, filters]);

    // Update cards when filtered cards change
    useEffect(() => {
        setCards(filteredCards);
    }, [filteredCards]);

    // Ensure users are fetched when auth user changes
    useEffect(() => {
        if (user) {
            refreshUsers();
        }
    }, [user]);

    const handleCreateCard = (listId?: number): void => {
        if (!permissions.canCreateCard) {
            notifyPermissionDenied();
            return;
        }
        setEditingCard(null);
        setDefaultListIdForNewCard(listId ?? null);
        setShowCardForm(true);
    };

    const handleCardUpdate = (updatedCard: Card, action: 'edit' | 'update' = 'edit'): void => {
        if (action === 'edit') {
            // Allow opening card for viewing even if user can't edit it
            if (!permissions.canModifyCard(updatedCard) && !user) {
                notifyPermissionDenied();
                return;
            }
            setEditingCard(updatedCard);
            setDefaultListIdForNewCard(null);
            setShowCardForm(true);
        } else {
            setAllCards(prev => {
                // Vérifier si la carte existe déjà dans la liste
                const existingCard = prev.find(c => c.id === updatedCard.id);
                if (existingCard) {
                    // Mettre à jour la carte existante
                    return prev.map(c => c.id === updatedCard.id ? updatedCard : c);
                } else {
                    // Ajouter la carte (cas de restauration d'une carte archivée)
                    return [...prev, updatedCard];
                }
            });
        }
    };

    const handleCardDelete = async (cardId: number): Promise<void> => {
        const cardToDelete = allCards.find(card => card.id === cardId);
        if (!cardToDelete || !permissions.canArchiveCard) {
            notifyPermissionDenied();
            return;
        }

        try {
            await cardService.archiveCard(cardId);
            setAllCards(prev => prev.filter(card => card.id !== cardId));

            // Importer Sonner pour utiliser les actions
            sonnerToast.success(t('app.cardArchived'), {
                description: t('app.cardArchivedDescription'),
                action: {
                    label: t('app.undo'),
                    onClick: async () => {
                        try {
                            await cardService.unarchiveCard(cardId);
                            setAllCards(prev => [...prev, cardToDelete]);
                            sonnerToast.success(t('app.cardRestored'), {
                                description: t('app.cardRestoredDescription')
                            });
                        } catch (restoreError: any) {
                            console.error('Erreur lors de la restauration:', restoreError);
                            sonnerToast.error(t('app.restoreError'), {
                                description: restoreError.response?.data?.detail || t('app.restoreErrorDescription')
                            });
                        }
                    }
                },
                duration: 5000, // 5 secondes pour donner le temps d'annuler
            });
        } catch (error: any) {
            console.error('Erreur lors de la suppression de la carte:', error);
            toast({
                title: t('app.archiveError'),
                description: error.response?.data?.detail || t('app.archiveErrorDescription'),
                variant: "destructive"
            });
        }
    };


    const handleCardMove = async (cardId: number, newListId: number, position?: number): Promise<void> => {
        try {
            // Find the current card to get its current list_id
            const currentCard = allCards.find(card => card.id === cardId);
            if (!currentCard) {
                console.error('Card not found:', cardId);
                return;
            }

            if (!permissions.canMoveCard(currentCard)) {
                notifyPermissionDenied();
                await loadCards();
                return;
            }

            const currentListId = currentCard.list_id;

            // If the card is already in the target list and no position is specified, do nothing
            if (currentListId === newListId && position === undefined) {
                return;
            }

            // Use the dedicated move endpoint with proper position tracking
            const updatedCard = await cardService.moveCard(cardId, currentListId, newListId, position);

            // Update the card in local state
            const updatedCards = allCards.map(card =>
                card.id === cardId ? updatedCard : card
            );

            // If position is specified, reorder the cards in the target list for immediate UI feedback
            if (position !== undefined && position >= 0) {
                const targetListCards = updatedCards.filter(card => card.list_id === newListId);
                const movedCard = targetListCards.find(card => card.id === cardId);

                if (movedCard) {
                    // Remove the card from its current position in the array
                    const cardsWithoutMoved = targetListCards.filter(card => card.id !== cardId);

                    // Ensure position is within bounds
                    const safePosition = Math.min(position, cardsWithoutMoved.length);

                    // Insert the card at the specified position
                    cardsWithoutMoved.splice(safePosition, 0, movedCard);

                    // Update the cards array with the new order
                    const otherCards = updatedCards.filter(card => card.list_id !== newListId);
                    setAllCards([...otherCards, ...cardsWithoutMoved]);
                } else {
                    setAllCards(updatedCards);
                }
            } else {
                // No specific position, just update the card's list
                setAllCards(updatedCards);
            }
        } catch (error: any) {
            console.error('Erreur lors du déplacement de la carte:', error);
            toast({
                title: t('app.moveError'),
                description: error.response?.data?.detail || t('app.moveErrorDescription'),
                variant: "destructive"
            });
        }
    };

    const handleCloseCardForm = (): void => {
        setShowCardForm(false);
        setEditingCard(null);
        setDefaultListIdForNewCard(null);
    };

    const handleCardSave = async (): Promise<void> => {
        setShowCardForm(false);
        setEditingCard(null);
        setDefaultListIdForNewCard(null);
        // Reload cards to get updated data
        await loadCards();
    };

    const loadCards = async (): Promise<void> => {
        try {
            const cardsData = await cardService.getCards({}); // Load all cards without filters
            setAllCards(cardsData);
            // Also refresh lists when cards are reloaded (after list operations)
            setListsRefreshTrigger(prev => prev + 1);
        } catch (error) {
            console.error('Erreur lors du rechargement des cartes:', error);
            toast({
                title: t('app.reloadCardsError'),
                description: t('errors.tryAgain'),
                variant: "destructive"
            });
        }
    };

    const handleShowUsers = (): void => {
        setShowUsersManager(true);
    };

    const handleShowLabels = (): void => {
        setShowLabelManager(true);
    };

    const handleShowLists = (): void => {
        setShowListManager(true);
    };

    const handleShowInterface = (): void => {
        setShowInterfaceDialog(true);
    };

    const handleLogout = async (): Promise<void> => {
        try {
            await logout();
            toast({
                title: t('app.logoutSuccess'),
                description: t('app.logoutSuccessDescription'),
            });
        } catch (error) {
            console.error('Erreur lors de la déconnexion:', error);
            toast({
                title: t('app.logoutError'),
                description: t('app.logoutErrorDescription'),
                variant: "destructive"
            });
        }
    };

    if (loading || dataLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center app-loading">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
        );
    };

    if (!user) {
        return <LoginForm />;
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/20 app-loaded">
            <div className="flex flex-col min-h-screen">
                <Header
                    user={user}
                    theme={theme}
                    onShowUsers={handleShowUsers}
                    onShowLabels={handleShowLabels}
                    onShowLists={handleShowLists}
                    onShowInterface={handleShowInterface}
                    onToggleTheme={toggleTheme}
                    onLogout={handleLogout}
                    displayMode={displayMode}
                    onDisplayModeChange={setDisplayMode}
                />

                <FilterBar
                    filters={filters}
                    onFiltersChange={setFilters}
                    onCreateCard={handleCreateCard}
                    canCreateCard={permissions.canCreateCard}
                    users={users}
                    labels={labels}
                    localSearchValue={filters.search || ''}
                    onLocalSearchChange={(value) => setFilters(prev => ({ ...prev, search: value }))}
                    onCardSave={handleCardSave}
                />

                <KanbanBoard
                    cards={cards}
                    onCardUpdate={handleCardUpdate}
                    onCardDelete={handleCardDelete}
                    onCardMove={handleCardMove}
                    onCreateCard={permissions.canCreateCard ? (listId) => handleCreateCard(listId) : undefined}
                    refreshTrigger={listsRefreshTrigger}
                    isAnyModalOpen={isAnyModalOpen}
                    displayMode={displayMode}
                />

                <CardForm
                    card={editingCard}
                    isOpen={showCardForm}
                    onClose={handleCloseCardForm}
                    onSave={handleCardSave}
                    onDelete={handleCardDelete}
                    defaultListId={defaultListIdForNewCard || editingCard?.list_id || -1} // Utiliser la liste spécifiée par le bouton "+" ou celle de la carte en cours d'édition
                />

                <LabelManager
                    isOpen={showLabelManager}
                    onClose={() => setShowLabelManager(false)}
                />

                <ListManager
                    isOpen={showListManager}
                    onClose={() => setShowListManager(false)}
                    onListsUpdated={loadCards}
                />

                <UsersManager
                    isOpen={showUsersManager}
                    onClose={() => setShowUsersManager(false)}
                />

                <InterfaceDialog
                    open={showInterfaceDialog}
                    onOpenChange={setShowInterfaceDialog}
                />

                <Footer />
            </div>
        </div>
    );
};

const AppContent = () => {
    const location = useLocation();
    const { theme } = useTheme();
    const { user, loading } = useAuth();
    useUserLanguage(); // Initialize user language

    useEffect(() => {
        document.documentElement.className = theme;
    }, [theme]);

    // Routes qui ne nécessitent pas d'authentification
    const publicRoutes = ['/invite', '/login'];
    const isPublicRoute = publicRoutes.some(route => location.pathname.startsWith(route));

    if (isPublicRoute) {
        return (
            <Routes>
                <Route path="/invite" element={<InvitePage />} />
                <Route path="/login" element={<LoginForm />} />
            </Routes>
        );
    }

    // Si l'utilisateur n'est pas authentifié et n'est pas sur une route publique,
    // afficher le formulaire de login (sans changer l'URL pour le moment)
    if (!loading && !user) {
        return <LoginForm />;
    }

    // Routes protégées (nécessitent une authentification)
    return <KanbanApp />;
};

const App = () => {
    return (
        <Router>
            <AuthProvider>
                <BoardSettingsProvider>
                    <UsersProvider>
                        <AppContent />
                        <Toaster />
                    </UsersProvider>
                </BoardSettingsProvider>
            </AuthProvider>
        </Router>
    );
};

export default App; 
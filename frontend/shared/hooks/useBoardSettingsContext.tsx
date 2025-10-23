import React, { createContext, useContext, useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { boardSettingsService } from '../services/api';
import { useToast } from './use-toast';

interface BoardSettingsContextType {
  boardTitle: string;
  loading: boolean;
  error: string | null;
  updateBoardTitle: (newTitle: string) => Promise<boolean>;
  refetchBoardTitle: () => Promise<void>;
}

const BoardSettingsContext = createContext<BoardSettingsContextType | undefined>(undefined);

export const useBoardSettings = () => {
  const context = useContext(BoardSettingsContext);
  if (context === undefined) {
    throw new Error('useBoardSettings must be used within a BoardSettingsProvider');
  }
  return context;
};

interface BoardSettingsProviderProps {
  children: React.ReactNode;
}

export const BoardSettingsProvider = ({ children }: BoardSettingsProviderProps) => {
  const { t } = useTranslation();
  const [boardTitle, setBoardTitle] = useState<string>('Yaka (Yet Another Kanban App)');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const fetchBoardTitle = async () => {
    try {
      setLoading(true);
      const data = await boardSettingsService.getBoardTitle();
      setBoardTitle(data.title || 'Yaka (Yet Another Kanban App)');
    } catch (err) {
      setError(t('boardSettings.loadError'));
      setBoardTitle('Yaka (Yet Another Kanban App)'); // Fallback en cas d'erreur
    } finally {
      setLoading(false);
    }
  };

  const updateBoardTitle = async (newTitle: string) => {
    try {
      setError(null);
      // S'assurer que le titre n'est pas vide
      const titleToSave = newTitle?.trim() || 'Yaka (Yet Another Kanban App)';
      const data = await boardSettingsService.updateBoardTitle(titleToSave);
      setBoardTitle(data.title || 'Yaka (Yet Another Kanban App)');

      // Afficher un toast de succès
      toast({
        title: t('settings.titleUpdatedSuccess'),
        variant: 'success'
      });

      return true;
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || t('boardSettings.updateError');
      setError(errorMessage);

      // Afficher un toast d'erreur
      toast({
        title: t('common.error'),
        description: errorMessage,
        variant: 'destructive',
      });

      return false;
    }
  };

  useEffect(() => {
    fetchBoardTitle();
  }, []);

  // Mettre à jour le titre de la page HTML quand le titre du board change
  useEffect(() => {
    if (boardTitle && boardTitle !== 'Yaka (Yet Another Kanban App)') {
      document.title = `Yaka - ${boardTitle}`;
    } else {
      document.title = 'Yaka';
    }
  }, [boardTitle]);

  const value: BoardSettingsContextType = {
    boardTitle,
    loading,
    error,
    updateBoardTitle,
    refetchBoardTitle: fetchBoardTitle,
  };

  return (
    <BoardSettingsContext.Provider value={value}>
      {children}
    </BoardSettingsContext.Provider>
  );
};
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { boardSettingsService } from '../services/api';

export interface BoardSettings {
  id: number;
  setting_key: string;
  setting_value: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export const useBoardSettings = () => {
  const { t } = useTranslation();
  const [boardTitle, setBoardTitle] = useState<string>('Yaka (Yet Another Kanban App)');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBoardTitle = async () => {
    try {
      setLoading(true);
      const data = await boardSettingsService.getBoardTitle();
      setBoardTitle(data.title);
    } catch (err) {
      console.error('Error fetching board title:', err);
      setError(t('boardSettings.loadError'));
    } finally {
      setLoading(false);
    }
  };

  const updateBoardTitle = async (newTitle: string) => {
    try {
      setError(null);
      const data = await boardSettingsService.updateBoardTitle(newTitle);
      setBoardTitle(data.title);
      return true;
    } catch (err: any) {
      console.error('Error updating board title:', err);
      const errorMessage = err?.response?.data?.detail || t('boardSettings.updateError');
      setError(errorMessage);
      return false;
    }
  };

  useEffect(() => {
    fetchBoardTitle();
  }, []);

  return {
    boardTitle,
    loading,
    error,
    updateBoardTitle,
    refetchBoardTitle: fetchBoardTitle,
  };
};
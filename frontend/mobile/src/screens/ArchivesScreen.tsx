import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { cardService } from '@shared/services/api';
import { listsApi } from '@shared/services/listsApi';
import { Card, KanbanList } from '@shared/types';
import { ArrowLeft, Archive, Loader2, RotateCcw } from 'lucide-react';
import { useToast } from '@shared/hooks/use-toast';
import { format } from 'date-fns';
import { fr, enUS } from 'date-fns/locale';

interface ArchivedCard extends Card {
  archived_at?: string;
}

const ArchivesScreen = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [archivedCards, setArchivedCards] = useState<ArchivedCard[]>([]);
  const [availableLists, setAvailableLists] = useState<KanbanList[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [restoringCardId, setRestoringCardId] = useState<number | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [cardsData, listsData] = await Promise.all([
        cardService.getCards({ is_archived: true }),
        listsApi.getLists()
      ]);
      setArchivedCards(cardsData as ArchivedCard[]);
      setAvailableLists(listsData);
    } catch (error: any) {
      console.error('Error loading archived cards:', error);
      toast({
        title: t('common.error'),
        description: t('archive.loadError'),
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRestoreCard = async (card: ArchivedCard) => {
    try {
      setRestoringCardId(card.id);

      // Find the original list or use the first available list
      const targetList = availableLists.find(list => list.id === card.list_id) || availableLists[0];

      if (!targetList) {
        toast({
          title: t('common.error'),
          description: t('archive.noListAvailable'),
          variant: 'destructive'
        });
        return;
      }

      // Restore the card
      await cardService.unarchiveCard(card.id);

      // Update local state
      setArchivedCards(prev => prev.filter(c => c.id !== card.id));

      toast({
        title: t('archive.cardRestored'),
        description: t('archive.cardRestoredDescription', { 
          cardTitle: card.title, 
          listName: targetList.name 
        }),
        variant: 'success'
      });
    } catch (error: any) {
      console.error('Error restoring card:', error);
      toast({
        title: t('archive.restoreError'),
        description: error.response?.data?.detail || t('archive.restoreErrorDescription'),
        variant: 'destructive'
      });
    } finally {
      setRestoringCardId(null);
    }
  };

  const formatDate = (dateString?: string): string => {
    if (!dateString) {
      return t('common.unknownDate');
    }
    try {
      const locale = i18n.language === 'fr' ? fr : enUS;
      return format(new Date(dateString), 'dd MMMM yyyy', { locale });
    } catch {
      return t('common.unknownDate');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">{t('archive.loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/95 backdrop-blur-sm border-b border-border">
        <div className="flex items-center h-16 px-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 -ml-2 rounded-lg hover:bg-muted active:bg-muted/80 transition-colors"
          >
            <ArrowLeft className="w-6 h-6 text-foreground" />
          </button>
          <div className="flex-1 ml-3">
            <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
              <Archive className="w-5 h-5" />
              {t('mobile.archives')}
            </h1>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-4">
        {archivedCards.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Archive className="w-16 h-16 text-muted-foreground/50 mb-4" />
            <h2 className="text-lg font-semibold text-foreground mb-2">
              {t('archive.noCards')}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t('archive.noCardsDescription')}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {archivedCards.map((card) => (
              <div
                key={card.id}
                className="bg-card border border-border rounded-lg p-4 shadow-sm"
              >
                {/* Card Title */}
                <h3 className="font-semibold text-foreground mb-2">
                  {card.title}
                </h3>

                {/* Card Description */}
                {card.description && (
                  <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                    {card.description}
                  </p>
                )}

                {/* Card Labels */}
                {card.labels && card.labels.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {card.labels.map((label) => (
                      <span
                        key={label.id}
                        className="text-xs px-2 py-0.5 font-medium border-opacity-50 rounded-md border"
                        style={{
                          backgroundColor: label.color + '15',
                          borderColor: label.color + '40',
                          color: label.color
                        }}
                      >
                        {label.name}
                      </span>
                    ))}
                  </div>
                )}

                {/* Footer with date and restore button */}
                <div className="flex items-center justify-between pt-3 border-t border-border">
                  <span className="text-xs text-muted-foreground">
                    {t('archive.archivedOn', { date: formatDate(card.archived_at || card.updated_at) })}
                  </span>
                  <button
                    onClick={() => handleRestoreCard(card)}
                    disabled={restoringCardId === card.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-primary bg-primary/10 hover:bg-primary/20 active:bg-primary/30 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {restoringCardId === card.id ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>{t('common.loading')}</span>
                      </>
                    ) : (
                      <>
                        <RotateCcw className="w-4 h-4" />
                        <span>{t('archive.restore')}</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default ArchivesScreen;


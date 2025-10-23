import { KanbanList, Card } from '@shared/types';
import { useTranslation } from 'react-i18next';
import CardItem from './CardItem';

interface ListsViewProps {
  lists: KanbanList[];
  cards: Card[];
  onCardClick?: (card: Card) => void;
}

const ListsView = ({ lists, cards, onCardClick }: ListsViewProps) => {
  const { t } = useTranslation();
  // Group cards by list_id
  const cardsByList = cards.reduce((acc, card) => {
    if (!acc[card.list_id]) {
      acc[card.list_id] = [];
    }
    acc[card.list_id].push(card);
    return acc;
  }, {} as Record<number, Card[]>);

  // Sort cards within each list by position (assuming cards have a position field)
  Object.keys(cardsByList).forEach((listId) => {
    cardsByList[parseInt(listId)].sort((a, b) => {
      // If cards don't have position, sort by created_at
      if (!('position' in a) || !('position' in b)) {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      }
      return (a as any).position - (b as any).position;
    });
  });

  return (
    <div className="space-y-6">
      {lists.map((list) => {
        const listCards = cardsByList[list.id] || [];
        
        return (
          <div key={list.id} className="animate-fade-in">
            {/* List Header */}
            <div className="sticky top-0 bg-background/95 backdrop-blur-sm z-10 pb-3 mb-3 border-b-2 border-border">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-foreground">
                  {list.name}
                </h2>
                <span className="px-2 py-1 bg-muted text-muted-foreground text-xs font-medium rounded-full">
                  {listCards.length}
                </span>
              </div>
              </div>

            {/* Cards */}
            <div className="space-y-3">
              {listCards.length > 0 ? (
                listCards.map((card) => (
                  <CardItem
                    key={card.id}
                    card={card}
                    onClick={() => onCardClick?.(card)}
                  />
                ))
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p className="text-sm">{t('list.noCardsInList')}</p>
                </div>
              )}
            </div>
          </div>
        );
      })}

      {lists.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <p>{t('list.noListsAvailable')}</p>
        </div>
      )}
    </div>
  );
};

export default ListsView;


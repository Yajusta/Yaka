import { Filter, Mic, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface BottomNavProps {
  onFilterClick?: () => void;
  onVoiceClick?: () => void;
  onNewCardClick?: () => void;
}

const BottomNav = ({ onFilterClick, onVoiceClick, onNewCardClick }: BottomNavProps) => {
  const { t } = useTranslation();

  return (
    <nav className="bottom-nav">
      {/* Filter button */}
      <button
        onClick={onFilterClick}
        className="flex items-center justify-center btn-touch text-muted-foreground hover:text-primary active:text-primary transition-colors"
        aria-label={t('common.filters')}
      >
        <Filter className="w-7 h-7" />
      </button>

      {/* Voice input button */}
      <button
        onClick={onVoiceClick}
        className="flex items-center justify-center btn-touch text-muted-foreground hover:text-primary active:text-primary transition-colors"
        aria-label={t('voice.input')}
      >
        <Mic className="w-7 h-7" />
      </button>

      {/* New card button */}
      <button
        onClick={onNewCardClick}
        className="flex items-center justify-center btn-touch bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 active:bg-primary/80 transition-colors shadow-lg"
        aria-label={t('card.newCard')}
      >
        <Plus className="w-7 h-7" />
      </button>
    </nav>
  );
};

export default BottomNav;


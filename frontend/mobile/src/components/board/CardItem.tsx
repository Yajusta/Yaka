import { Card, Label } from '@shared/types';
import { User, ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface CardItemProps {
  card: Card;
  onClick?: () => void;
}

const CardItem = ({ card, onClick }: CardItemProps) => {
  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'high':
        return <ArrowUp className="w-4 h-4" />;
      case 'medium':
        return <Minus className="w-4 h-4" />;
      case 'low':
        return <ArrowDown className="w-4 h-4" />;
      default:
        return <Minus className="w-4 h-4" />;
    }
  };

  const getPriorityClass = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'priority-high';
      case 'medium':
        return 'priority-medium';
      case 'low':
        return 'priority-low';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  const truncateText = (text: string, maxLength: number) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div
      onClick={onClick}
      className="mobile-card cursor-pointer"
    >
      {/* Title */}
      <h3 className="font-semibold text-foreground mb-2 line-clamp-2">
        {card.title}
      </h3>

      {/* Description */}
      {card.description && (
        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
          {truncateText(card.description, 100)}
        </p>
      )}

      {/* Labels */}
      {card.labels && card.labels.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {card.labels.map((label: Label) => (
            <span
              key={label.id}
              className="label-badge"
              style={{
                backgroundColor: `${label.color}20`,
                color: label.color,
                borderColor: `${label.color}40`,
                borderWidth: '1px',
              }}
            >
              {label.name}
            </span>
          ))}
        </div>
      )}

      {/* Footer: Priority and Assignee */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
        {/* Priority */}
        <div className={`flex items-center gap-1 px-2 py-1 rounded-md ${getPriorityClass(card.priority)}`}>
          {getPriorityIcon(card.priority)}
          <span className="text-xs font-medium capitalize">{card.priority}</span>
        </div>

        {/* Assignee */}
        {card.assignee_name ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <User className="w-4 h-4" />
            <span className="truncate max-w-[120px]">{card.assignee_name}</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <User className="w-4 h-4" />
            <span className="italic">Non assignée</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default CardItem;


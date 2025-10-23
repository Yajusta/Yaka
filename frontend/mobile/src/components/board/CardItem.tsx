import { Card, Label } from '@shared/types';
import {
  User,
  ArrowUp,
  ArrowDown,
  Minus,
  CalendarDays,
  AlertCircle,
  AlertTriangle,
  MessageSquare
} from 'lucide-react';
import { cn } from '@shared/lib/utils';

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
        return 'text-destructive border-destructive';
      case 'medium':
        return 'text-sky-600 border-sky-600';
      case 'low':
        return 'text-muted-foreground border-muted-foreground';
      default:
        return 'text-muted-foreground border-muted-foreground';
    }
  };

  const normalizePriority = (priority: string): 'low' | 'medium' | 'high' => {
    if (!priority) {
      return 'low';
    }
    const lower = String(priority).toLowerCase();
    const normalized = lower.normalize('NFD').replace(/\p{Diacritic}/gu, '');

    if (normalized.includes('high') || normalized.includes('elev') || normalized.includes('eleve')) {
      return 'high';
    }
    if (normalized.includes('medium') || normalized.includes('moy')) {
      return 'medium';
    }
    if (normalized.includes('low') || normalized.includes('faibl') || normalized.includes('faible')) {
      return 'low';
    }

    return 'low';
  };

  const formatDate = (dateString: string): string | null => {
    if (!dateString) {
      return null;
    }
    return new Date(dateString).toLocaleDateString('fr-FR');
  };

  const getDueDateStatus = (dateString: string): 'overdue' | 'upcoming' | 'normal' => {
    if (!dateString) {
      return 'normal';
    }

    const dueDate = new Date(dateString);
    const today = new Date();
    dueDate.setHours(0, 0, 0, 0);
    today.setHours(0, 0, 0, 0);

    const diffTime = dueDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays <= 0) {
      return 'overdue';
    } else if (diffDays <= 7) {
      return 'upcoming';
    }

    return 'normal';
  };

  const priorityKey = normalizePriority(card.priority);
  const priorityGlowClass = {
    'high': 'priority-high',
    'medium': 'priority-medium',
    'low': 'priority-low'
  }[priorityKey];

  // Calculate checklist progress
  const totalItems = card.items?.length || 0;
  const doneItems = card.items?.filter(i => i.is_done).length || 0;
  const progress = totalItems > 0 ? Math.round((doneItems / totalItems) * 100) : 0;

  const totalComments = card.comments?.length || 0;

  return (
    <div
      onClick={onClick}
      className={cn(
        "mobile-card cursor-pointer bg-card border-2",
        priorityGlowClass
      )}
    >
      {/* Header with title */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="font-semibold leading-tight flex-1 text-foreground text-sm">
          {card.title}
        </h3>
      </div>

      {/* Description */}
      {card.description && (
        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed mb-2">
          {card.description}
        </p>
      )}

      {/* Labels */}
      {card.labels && card.labels.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {card.labels.map((label: Label) => (
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

      {/* Checklist Progress */}
      {totalItems > 0 && (
        <div className="flex items-center gap-2 mb-2">
          <div className="relative h-5 w-5">
            <svg className="h-5 w-5 text-muted-foreground" viewBox="0 0 36 36">
              <path
                className="text-muted-foreground/20"
                strokeWidth="4"
                stroke="currentColor"
                fill="none"
                pathLength="100"
                d="M18 2 a 16 16 0 1 0 0 32 a 16 16 0 1 0 0 -32"
              />
              <path
                className="text-primary"
                strokeWidth="4"
                strokeLinecap="round"
                stroke="currentColor"
                fill="none"
                pathLength="100"
                strokeDasharray={`${progress} ${100 - progress}`}
                transform="scale(-1,1) translate(-36,0)"
                d="M18 2 a 16 16 0 1 0 0 32 a 16 16 0 1 0 0 -32"
              />
            </svg>
          </div>
          <span className="text-xs text-muted-foreground">{doneItems} / {totalItems}</span>
        </div>
      )}

      {/* Footer: All metadata on same line */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          {/* Priority - icon only, round */}
          <div className={`flex items-center justify-center w-6 h-6 rounded-full border ${getPriorityClass(card.priority)}`}>
            {getPriorityIcon(card.priority)}
          </div>

          {/* Due Date with full text */}
          {card.due_date && (() => {
            const dueDateStatus = getDueDateStatus(card.due_date);
            const isOverdue = dueDateStatus === 'overdue';
            const isUpcoming = dueDateStatus === 'upcoming';

            const Icon = isOverdue ? AlertCircle : isUpcoming ? AlertTriangle : CalendarDays;

            return (
              <div className={`flex items-center gap-1 text-xs ${isOverdue ? 'text-red-600' : isUpcoming ? 'text-orange-500' : 'text-muted-foreground'}`}>
                <Icon className="h-3 w-3" />
                <span>{formatDate(card.due_date)}</span>
              </div>
            );
          })()}

          {/* Comments */}
          {totalComments > 0 && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <MessageSquare className="h-3 w-3" />
              <span className="text-xs">{totalComments}</span>
            </div>
          )}
        </div>

        {/* Assignee */}
        {card.assignee_name ? (
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <User className="w-3 h-3" />
            <span className="truncate max-w-[80px] text-xs">{card.assignee_name}</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-sm text-muted-foreground opacity-50">
            <User className="w-3 h-3" />
            <span className="italic text-xs">Non assignée</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default CardItem;


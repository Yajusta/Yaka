import { Card, Label, UpdateCardData, getPriorityIcon, getPriorityIconColor, UserRole } from '@shared/types';
import {
  User,
  Shield,
  Key,
  PenTool,
  Users,
  MessageSquare,
  Eye,
  CalendarDays,
  AlertCircle,
  AlertTriangle
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '@shared/lib/utils';
import { useState, useEffect, useRef } from 'react';
import { cardService } from '@shared/services/api';
import { useUsers } from '@shared/hooks/useUsers';
import { useAuth } from '@shared/hooks/useAuth';
import { useToast } from '@shared/hooks/use-toast';
import { useNavigate, useLocation } from 'react-router-dom';

interface CardItemProps {
  card: Card;
  onClick?: () => void;
  onUpdate?: (updatedCard: Card) => void;
}

const CardItem = ({ card, onClick, onUpdate }: CardItemProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const { users } = useUsers();
  const { user: currentUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const currentUserId = currentUser?.id ?? null;
  const isCurrentUserAssigned = currentUserId !== null && card.assignee_id === currentUserId;

  // Get board ID from localStorage or URL
  const getBoardId = (): string => {
    // First try to get from URL
    const boardMatch = location.pathname.match(/^\/board\/([^\/]+)/);
    if (boardMatch) {
      return boardMatch[1];
    }

    // Fall back to localStorage
    return localStorage.getItem('board_name') || '';
  };

  const [showPriorityDropdown, setShowPriorityDropdown] = useState(false);
  const [showAssigneeDropdown, setShowAssigneeDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowPriorityDropdown(false);
        setShowAssigneeDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const getUserRoleIcon = (role?: string) => {
    switch (role) {
      case UserRole.ADMIN:
        return Key;
      case UserRole.SUPERVISOR:
        return Shield;
      case UserRole.EDITOR:
        return PenTool;
      case UserRole.CONTRIBUTOR:
        return Users;
      case UserRole.COMMENTER:
        return MessageSquare;
      case UserRole.VISITOR:
        return Eye;
      default:
        return User;
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

    if (lower.includes('high') || lower.includes('elev') || lower.includes('eleve')) {
      return 'high';
    }
    if (lower.includes('medium') || lower.includes('moy')) {
      return 'medium';
    }
    if (lower.includes('low') || lower.includes('faibl') || lower.includes('faible')) {
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

  const handlePriorityChange = async (newPriority: 'low' | 'medium' | 'high') => {
    if (newPriority === card.priority) {
      setShowPriorityDropdown(false);
      return;
    }

    const updatePayload: UpdateCardData = {
      priority: newPriority,
    };

    try {
      const updatedCard = await cardService.updateCard(card.id, updatePayload);
      onUpdate?.(updatedCard);
      setShowPriorityDropdown(false);
      toast({
        title: 'Priority updated',
        description: `Card priority changed to ${newPriority}`,
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to update priority", error);
      toast({
        title: 'Error',
        description: 'Failed to update priority',
        variant: "destructive",
      });
    }
  };

  const handleAssigneeChange = async (newAssigneeId: number | null) => {
    if (newAssigneeId === card.assignee_id) {
      setShowAssigneeDropdown(false);
      return;
    }

    const updatePayload: UpdateCardData = {
      assignee_id: newAssigneeId,
    };

    try {
      const updatedCard = await cardService.updateCard(card.id, updatePayload);
      onUpdate?.(updatedCard);
      setShowAssigneeDropdown(false);

      const userName = newAssigneeId
        ? users.find(u => u.id === newAssigneeId)?.display_name || 'Unknown user'
        : 'unassigned';

      toast({
        title: 'Assignee updated',
        description: `Card assigned to ${userName}`,
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to update assignee", error);
      toast({
        title: 'Error',
        description: 'Failed to update assignee',
        variant: "destructive",
      });
    }
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

  const handleCommentsClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const boardId = getBoardId();
    navigate(`/board/${boardId}/card/${card.id}/comments`);
  };

  return (
    <div
      ref={dropdownRef}
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
          {/* Priority - interactive dropdown */}
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowPriorityDropdown(!showPriorityDropdown);
                setShowAssigneeDropdown(false);
              }}
              className={`flex items-center justify-center w-6 h-6 rounded-full border ${getPriorityClass(card.priority)} hover:opacity-80 transition-opacity`}
            >
              {(() => {
                const Icon = getPriorityIcon(card.priority);
                return <Icon className="w-4 h-4" />;
              })()}
            </button>

            {showPriorityDropdown && (
              <div className="absolute bottom-full left-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg z-50 min-w-[120px]">
                <div className="py-1">
                  {(['high', 'medium', 'low'] as const).map((priority) => {
                    const Icon = getPriorityIcon(priority);
                    const iconColor = getPriorityIconColor(priority);
                    const isSelected = priorityKey === priority;
                    return (
                      <button
                        key={priority}
                        onClick={(e) => {
                          e.stopPropagation();
                          handlePriorityChange(priority);
                        }}
                        className={`w-full px-3 py-2 text-left text-xs flex items-center gap-2 hover:bg-gray-100 ${
                          isSelected ? 'bg-gray-50 font-medium' : ''
                        }`}
                      >
                        <Icon className={`w-4 h-4 ${iconColor}`} />
                        <span className="capitalize">{priority}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
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
          <div
            onClick={handleCommentsClick}
            className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors cursor-pointer p-1"
            role="button"
            tabIndex={0}
          >
            <MessageSquare className="h-3 w-3" />
            {totalComments > 0 && (
              <span className="text-xs">{totalComments}</span>
            )}
          </div>
        </div>

        {/* Assignee - interactive dropdown */}
        <div className="relative">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowAssigneeDropdown(!showAssigneeDropdown);
              setShowPriorityDropdown(false);
            }}
            className={`flex items-center gap-1 text-sm hover:opacity-80 transition-opacity ${
              isCurrentUserAssigned
                ? 'bg-primary text-primary-foreground rounded-md px-2 py-1 -mx-2 -my-1 shadow-sm'
                : 'text-muted-foreground'
            }`}
          >
            <User className={`w-3 h-3 ${isCurrentUserAssigned ? 'text-primary-foreground' : 'text-muted-foreground'}`} />
            {card.assignee_name ? (
              <span className={`truncate max-w-[80px] text-xs ${isCurrentUserAssigned ? 'text-primary-foreground' : ''}`}>{card.assignee_name}</span>
            ) : (
              <span className="italic text-xs">{t('card.unassign')}</span>
            )}
          </button>

          {showAssigneeDropdown && (
            <div className="absolute bottom-full right-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg z-50 min-w-[140px] max-h-[200px] overflow-y-auto">
              <div className="py-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAssigneeChange(null);
                  }}
                  className="w-full px-3 py-2 text-left text-xs flex items-center gap-2 hover:bg-gray-100"
                >
                  <span>{t('card.unassign')}</span>
                </button>
                {users
                  .slice()
                  .sort((a, b) => (a.display_name || '').localeCompare(b.display_name || ''))
                  .map((user) => {
                    const RoleIcon = getUserRoleIcon(user.role);
                    return (
                      <button
                        key={user.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAssigneeChange(user.id);
                        }}
                        className={`w-full px-3 py-2 text-left text-xs flex items-center gap-2 hover:bg-gray-100 ${
                        card.assignee_id === user.id ? 'bg-gray-50 font-medium' : ''
                      }`}
                      >
                        <RoleIcon className="w-4 h-4 text-muted-foreground" />
                        <span>{user.display_name}</span>
                      </button>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CardItem;
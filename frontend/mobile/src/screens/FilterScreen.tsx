import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X, Filter, ChevronLeft, Check } from 'lucide-react';
import { cn } from '@shared/lib/utils';
import { useAuth } from '@shared/hooks/useAuth';

interface User {
  id: number;
  email: string;
  display_name?: string;
  role?: string;
}

interface Label {
  id: number;
  name: string;
  color: string;
}

interface Filters {
  search: string;
  assignee_ids: number[] | null;
  priorities: string[] | null;
  label_ids: number[] | null;
}

interface FilterScreenProps {
  onBack: () => void;
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  users: User[];
  labels: Label[];
  voiceFilterIds?: number[] | null;
  voiceFilterDescription?: string;
  onVoiceFilterClear?: () => void;
}

export const FilterScreen = ({
  onBack,
  filters,
  onFiltersChange,
  users,
  labels,
  voiceFilterIds,
  voiceFilterDescription,
  onVoiceFilterClear,
}: FilterScreenProps) => {
  const { t } = useTranslation();
  const { aiAvailable } = useAuth();
  const [searchValue, setSearchValue] = useState(filters.search || '');
  const [selectedAssignees, setSelectedAssignees] = useState<number[]>(filters.assignee_ids || []);
  const [selectedPriorities, setSelectedPriorities] = useState<string[]>(filters.priorities || []);
  const [selectedLabels, setSelectedLabels] = useState<number[]>(filters.label_ids || []);

  useEffect(() => {
    setSearchValue(filters.search || '');
    setSelectedAssignees(filters.assignee_ids || []);
    setSelectedPriorities(filters.priorities || []);
    setSelectedLabels(filters.label_ids || []);
  }, [filters]);

  const handleSearchChange = (value: string) => {
    setSearchValue(value);
  };

  const handleApplyFilters = () => {
    const newFilters = {
      search: searchValue,
      assignee_ids: selectedAssignees.length > 0 ? selectedAssignees : null,
      priorities: selectedPriorities.length > 0 ? selectedPriorities : null,
      label_ids: selectedLabels.length > 0 ? selectedLabels : null,
    };
    onFiltersChange(newFilters);
    onBack();
  };

  const handleClearFilters = () => {
    const clearedFilters = {
      search: '',
      assignee_ids: null,
      priorities: null,
      label_ids: null,
    };
    onFiltersChange(clearedFilters);
    setSearchValue('');
    setSelectedAssignees([]);
    setSelectedPriorities([]);
    setSelectedLabels([]);
    // Go back after clearing filters
    onBack();
  };

  const hasActiveFilters = !!(searchValue || selectedAssignees.length > 0 || selectedPriorities.length > 0 || selectedLabels.length > 0);
  const hasVoiceFilter = !!(voiceFilterIds && voiceFilterIds.length > 0);

  const getSelectedUsers = (): User[] => {
    return users.filter(u => selectedAssignees.includes(u.id));
  };

  const getSelectedLabels = (): Label[] => {
    return labels.filter(l => selectedLabels.includes(l.id));
  };

  const handleClearAllFilters = () => {
    const clearedFilters = {
      search: '',
      assignee_ids: null,
      priorities: null,
      label_ids: null,
    };
    onFiltersChange(clearedFilters);
    setSearchValue('');
    setSelectedAssignees([]);
    setSelectedPriorities([]);
    setSelectedLabels([]);
    if (hasVoiceFilter && onVoiceFilterClear) {
      onVoiceFilterClear();
    }
    onBack();
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <div className="bg-card border-b-2 border-border p-4" style={{ paddingTop: 'calc(1rem + env(safe-area-inset-top))' }}>
        <div className="flex items-center justify-between">
          <button
            onClick={() => {
              // Apply filters when going back
              handleApplyFilters();
            }}
            className="p-2 text-muted-foreground hover:text-foreground active:bg-accent rounded-lg transition-colors"
            aria-label={t('common.back')}
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
          <h2 className="text-lg font-bold text-foreground">{t('common.filters')}</h2>
          <div className="flex items-center gap-2">
            {(hasActiveFilters || hasVoiceFilter) && (
              <button
                onClick={handleClearAllFilters}
                className="p-2 text-muted-foreground hover:text-foreground active:bg-accent rounded-lg transition-colors"
                aria-label={t('common.clear')}
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto pb-safe">
        <div className="p-4 space-y-6">
          {/* Active Filters Summary */}
          {(hasActiveFilters || hasVoiceFilter) && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">{t('filter.activeFilters')}</label>
              <div className="p-3 bg-muted/30 border border-border rounded-lg">
                <div className="space-y-2">
                  {hasVoiceFilter && voiceFilterDescription && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm">🎤 {voiceFilterDescription}</span>
                      {onVoiceFilterClear && (
                        <X
                          className="w-4 h-4 text-muted-foreground cursor-pointer hover:text-foreground"
                          onClick={() => onVoiceFilterClear()}
                        />
                      )}
                    </div>
                  )}
                  {searchValue && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm">{t('common.search')}: {searchValue}</span>
                      <X
                        className="w-4 h-4 text-muted-foreground cursor-pointer hover:text-foreground"
                        onClick={() => setSearchValue('')}
                      />
                    </div>
                  )}
                  {selectedPriorities.length > 0 && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm">{t('card.priority')}: {selectedPriorities.map(p => t(`priority.${p}`)).join(', ')}</span>
                      <X
                        className="w-4 h-4 text-muted-foreground cursor-pointer hover:text-foreground"
                        onClick={() => setSelectedPriorities([])}
                      />
                    </div>
                  )}
                  {selectedAssignees.length > 0 && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm">{t('card.assignee')}: {getSelectedUsers().map(u => u.display_name || u.email || t('user.noName')).join(', ')}</span>
                      <X
                        className="w-4 h-4 text-muted-foreground cursor-pointer hover:text-foreground"
                        onClick={() => setSelectedAssignees([])}
                      />
                    </div>
                  )}
                  {selectedLabels.length > 0 && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm">{t('card.labels')}: {getSelectedLabels().map(l => l.name).join(', ')}</span>
                      <X
                        className="w-4 h-4 text-muted-foreground cursor-pointer hover:text-foreground"
                        onClick={() => setSelectedLabels([])}
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

        {/* Search */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">{t('common.search')}</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
            <input
              type="text"
              placeholder={t('common.search')}
              value={searchValue}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
        </div>

        {/* Priority Filter */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">{t('card.priority')}</label>
          <div className="grid grid-cols-1 gap-2">
            {['high', 'medium', 'low'].map((priority) => {
              const isSelected = selectedPriorities.includes(priority);
              return (
                <button
                  key={priority}
                  onClick={() => {
                    if (isSelected) {
                      setSelectedPriorities(selectedPriorities.filter(p => p !== priority));
                    } else {
                      setSelectedPriorities([...selectedPriorities, priority]);
                    }
                  }}
                  className={cn(
                    "p-3 text-left border border-border rounded-lg transition-colors",
                    isSelected
                      ? "bg-primary/10 border-primary text-primary"
                      : "bg-background hover:bg-muted/50"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span>{t(`priority.${priority}`)}</span>
                    {isSelected && (
                      <Check className="w-4 h-4 text-primary" />
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Assignee Filter */}
        {users.length > 0 && (
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{t('card.assignee')}</label>
            <div className="grid grid-cols-1 gap-2">
              {users.map((user) => {
                const isSelected = selectedAssignees.includes(user.id);
                return (
                  <button
                    key={user.id}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedAssignees(selectedAssignees.filter(id => id !== user.id));
                      } else {
                        setSelectedAssignees([...selectedAssignees, user.id]);
                      }
                    }}
                    className={cn(
                      "p-3 text-left border border-border rounded-lg transition-colors",
                      isSelected
                        ? "bg-primary/10 border-primary text-primary"
                        : "bg-background hover:bg-muted/50"
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span>{user.display_name || user.email || t('user.noName')}</span>
                      {isSelected && (
                        <Check className="w-4 h-4 text-primary" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Label Filter */}
        {labels.length > 0 && (
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{t('card.labels')}</label>
            <div className="grid grid-cols-1 gap-2">
              {labels.map((label) => {
                const isSelected = selectedLabels.includes(label.id);
                return (
                  <button
                    key={label.id}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedLabels(selectedLabels.filter(id => id !== label.id));
                      } else {
                        setSelectedLabels([...selectedLabels, label.id]);
                      }
                    }}
                    className={cn(
                      "p-3 text-left border border-border rounded-lg transition-colors",
                      isSelected
                        ? "bg-primary/10 border-primary text-primary"
                        : "bg-background hover:bg-muted/50"
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full border border-border/50"
                          style={{ backgroundColor: label.color }}
                        />
                        <span>{label.name}</span>
                      </div>
                      {isSelected && (
                        <Check className="w-4 h-4 text-primary" />
                      )}
                    </div>
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
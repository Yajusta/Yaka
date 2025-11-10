import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  X,
  Save,
  Trash2,
  GripVertical,
  Plus,
  ChevronDown,
  User,
  Shield,
  Key,
  PenTool,
  Users,
  MessageSquare,
  Eye
} from 'lucide-react';
import { DndContext, closestCenter, DragEndEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Card, Label as LabelType, KanbanList, UpdateCardData, UserRole, getPriorityIcon, getPriorityIconColor } from '@shared/types';
import { useAuth } from '@shared/hooks/useAuth';
import { useUsers } from '@shared/hooks/useUsers';
import { usePermissions } from '@shared/hooks/usePermissions';
import { useToast } from '@shared/hooks/use-toast';
import { cardService, labelService, cardItemsService } from '@shared/services/api';
import { listsApi } from '@shared/services/listsApi';
import { mapPriorityFromBackend, mapPriorityToBackend } from '@shared/lib/priority';
import { HighlightedField } from '../common/HighlightedField';
import type { CSSProperties, ReactNode } from 'react';

interface CardDetailProps {
  card: Card;
  isOpen: boolean;
  onClose: () => void;
  onSave: (card: Card) => void;
  onDelete?: (cardId: number) => void;
  initialData?: {
    title?: string;
    description?: string;
    due_date?: string;
    priority?: string;
    assignee_id?: number | null;
    label_ids?: number[];
    list_id?: number;
    checklist?: ChecklistItem[];
  };
  proposedChanges?: {
    title?: string;
    description?: string;
    due_date?: string;
    priority?: string;
    assignee_id?: number | null;
    label_ids?: number[];
    list_id?: number;
    checklist?: ChecklistItem[];
  };
}

type ChecklistItem = {
  id?: number;
  clientId?: string;
  text: string;
  is_done: boolean;
  position: number;
};

type DragRender = (args: { attributes: any; listeners: any }) => ReactNode;

const SortableChecklistItem = ({ id, children }: { id: string | number; children: ReactNode | DragRender }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1
  } as CSSProperties;

  return (
    <div ref={setNodeRef} style={style} className="touch-none">
      {typeof children === 'function' ? (children as DragRender)({ attributes, listeners }) : children}
    </div>
  );
};

const CardDetail = ({ card, isOpen, onClose, onSave, onDelete, initialData, proposedChanges }: CardDetailProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const { user: currentUser } = useAuth();
  const { users } = useUsers();
  const permissions = usePermissions(currentUser);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    due_date: '',
    priority: 'medium',
    assignee_id: null as number | null,
    label_ids: [] as number[],
    list_id: -1
  });

  const [labels, setLabels] = useState<LabelType[]>([]);
  const [lists, setLists] = useState<KanbanList[]>([]);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [newItemText, setNewItemText] = useState('');
  const [loading, setLoading] = useState(false);
  const [showConfirmClose, setShowConfirmClose] = useState(false);
  const [showPriorityDropdown, setShowPriorityDropdown] = useState(false);
  const [showListDropdown, setShowListDropdown] = useState(false);
  const [showAssigneeDropdown, setShowAssigneeDropdown] = useState(false);
  
  // Store original values to detect changes
  const [originalFormData, setOriginalFormData] = useState({
    title: '',
    description: '',
    due_date: '',
    priority: 'medium',
    assignee_id: null as number | null,
    label_ids: [] as number[],
    list_id: -1
  });
  const [originalChecklist, setOriginalChecklist] = useState<ChecklistItem[]>([]);
  
  // Store original values when proposedChanges is provided (for voice control)
  const [originalValues, setOriginalValues] = useState<{
    title?: string;
    description?: string;
    due_date?: string;
    priority?: string;
    assignee_id?: number | null;
    label_ids?: number[];
    list_id?: number;
    checklist?: ChecklistItem[];
  }>({});

  const canEditCardContent = permissions.canModifyCardContent(card);
  const canEditCardMetadata = permissions.canModifyCardMetadata(card);
  const canEditCard = canEditCardContent || canEditCardMetadata;
  const canDeleteCard = permissions.canDeleteCard;
  const canToggleChecklistItems = permissions.canToggleCardItem(card);

  const isViewOnly = !canEditCard;

  const checklistIdCounter = useRef<number>(0);
  const ensureChecklistClientIds = (items: ChecklistItem[]): ChecklistItem[] =>
    items.map((item) => (item.id || item.clientId ? item : { ...item, clientId: `temp-${checklistIdCounter.current++}` }));

  const getChecklistItemKey = (item: ChecklistItem): string =>
    item.id ? `item-${item.id}` : item.clientId ?? `temp-${item.position}`;

  // Helper function to check if a field has changed (for voice control highlighting)
  const getFieldChangeInfo = (fieldName: string): { isChanged: boolean; tooltipContent: string } => {
    if (!proposedChanges) {
      return { isChanged: false, tooltipContent: '' };
    }

    switch (fieldName) {
      case 'title': {
        const oldValue = originalValues.title || '';
        const newValue = formData.title || '';
        const isChanged = oldValue !== newValue && proposedChanges.title !== undefined;
        return {
          isChanged,
          tooltipContent: t('voice.previousValue', { value: oldValue })
        };
      }
      case 'description': {
        const oldValue = originalValues.description || '';
        const newValue = formData.description || '';
        const isChanged = oldValue !== newValue && proposedChanges.description !== undefined;
        return {
          isChanged,
          tooltipContent: t('voice.previousValue', { value: oldValue || t('common.empty') })
        };
      }
      case 'due_date': {
        const oldValue = originalValues.due_date || '';
        const newValue = formData.due_date || '';
        const isChanged = oldValue !== newValue && proposedChanges.due_date !== undefined;
        return {
          isChanged,
          tooltipContent: t('voice.previousValue', { value: oldValue || t('common.none') })
        };
      }
      case 'priority': {
        const oldValue = originalValues.priority || '';
        const newValue = formData.priority || '';
        const isChanged = oldValue !== newValue && proposedChanges.priority !== undefined;
        return {
          isChanged,
          tooltipContent: t('voice.previousValue', { value: oldValue ? t(`priority.${oldValue}`) : t('priority.medium') })
        };
      }
      case 'assignee_id': {
        const oldValue = originalValues.assignee_id;
        const newValue = formData.assignee_id;
        const isChanged = oldValue !== newValue && proposedChanges.assignee_id !== undefined;
        const oldUser = users.find(u => u.id === oldValue);
        return {
          isChanged,
          tooltipContent: t('voice.previousValue', { value: oldUser?.display_name || t('card.unassign') })
        };
      }
      case 'labels': {
        const oldIds = originalValues.label_ids || [];
        const newIds = formData.label_ids || [];
        const isChanged = JSON.stringify(oldIds.sort()) !== JSON.stringify(newIds.sort()) && proposedChanges.label_ids !== undefined;
        const oldLabels = labels.filter(l => oldIds.includes(l.id)).map(l => l.name).join(', ');
        return {
          isChanged,
          tooltipContent: t('voice.previousLabels', { labels: oldLabels || t('voice.noLabels') })
        };
      }
      case 'list_id': {
        const oldValue = originalValues.list_id;
        const newValue = formData.list_id;
        const isChanged = oldValue !== newValue && proposedChanges.list_id !== undefined;
        const oldList = lists.find(l => l.id === oldValue);
        return {
          isChanged,
          tooltipContent: t('voice.previousValue', { value: oldList?.name || t('common.unknown') })
        };
      }
      default:
        return { isChanged: false, tooltipContent: '' };
    }
  };

  // Helper function to check if a checklist item has changed
  const getChecklistItemChangeInfo = (item: ChecklistItem, index: number): {
    textChanged: boolean;
    statusChanged: boolean;
    textTooltip: string;
    statusTooltip: string;
    isNew: boolean;
  } => {
    if (!proposedChanges?.checklist || !originalValues.checklist) {
      return { textChanged: false, statusChanged: false, textTooltip: '', statusTooltip: '', isNew: false };
    }

    // Find corresponding original item by id or position
    const originalItem = item.id
      ? originalValues.checklist.find(ci => ci.id === item.id)
      : originalValues.checklist[index];

    // If no original item found, this is a new item
    if (!originalItem) {
      return {
        textChanged: true,
        statusChanged: false,
        textTooltip: t('voice.newItem'),
        statusTooltip: '',
        isNew: true
      };
    }

    const textChanged = originalItem.text !== item.text;
    const statusChanged = originalItem.is_done !== item.is_done;

    return {
      textChanged,
      statusChanged,
      textTooltip: t('voice.previousValue', { value: originalItem.text }),
      statusTooltip: originalItem.is_done ? t('voice.wasChecked') : t('voice.wasUnchecked'),
      isNew: false
    };
  };

  useEffect(() => {
    if (isOpen && card) {
      loadData();
    }
  }, [isOpen, card]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      
      if (showPriorityDropdown && !target.closest('.priority-dropdown-container')) {
        setShowPriorityDropdown(false);
      }
      
      if (showListDropdown && !target.closest('.list-dropdown-container')) {
        setShowListDropdown(false);
      }
      
      if (showAssigneeDropdown && !target.closest('.assignee-dropdown-container')) {
        setShowAssigneeDropdown(false);
      }
    };

    if (showPriorityDropdown || showListDropdown || showAssigneeDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showPriorityDropdown, showListDropdown, showAssigneeDropdown]);

  const loadData = async () => {
    try {
      const [labelsData, listsData] = await Promise.all([
        labelService.getLabels(),
        listsApi.getLists()
      ]);
      setLabels(labelsData);
      setLists(listsData);

      // Check if this is a new card (id === 0)
      const isNewCard = card.id === 0;

      if (isNewCard && initialData) {
        // Use initialData for new card
        const initialFormData = {
          title: initialData.title || '',
          description: initialData.description || '',
          due_date: initialData.due_date || '',
          priority: initialData.priority || 'medium',
          assignee_id: initialData.assignee_id ?? null,
          label_ids: initialData.label_ids || [],
          list_id: initialData.list_id || (listsData.length > 0 ? listsData[0].id : -1)
        };
        setFormData(initialFormData);
        setOriginalFormData(initialFormData);
        setChecklist(ensureChecklistClientIds(initialData.checklist || []));
        setOriginalChecklist(initialData.checklist || []);
      } else if (proposedChanges) {
        // Store original values when proposedChanges is provided
        setOriginalValues({
          title: card.title || '',
          description: card.description || '',
          due_date: card.due_date || '',
          priority: mapPriorityFromBackend(card.priority || ''),
          assignee_id: card.assignee_id ?? null,
          label_ids: card.labels?.map(l => l.id) || [],
          list_id: card.list_id,
          checklist: []
        });

        // Load existing items and store as original
        try {
          const items = await cardItemsService.getItems(card.id);
          const originalItems = items.map(i => ({ id: i.id, text: i.text, is_done: i.is_done, position: i.position }));
          setOriginalValues(prev => ({ ...prev, checklist: originalItems }));

          // Apply proposed changes to checklist
          if (proposedChanges.checklist) {
            setChecklist(ensureChecklistClientIds(proposedChanges.checklist));
          } else {
            setChecklist(ensureChecklistClientIds(originalItems));
          }
          setOriginalChecklist(JSON.parse(JSON.stringify(originalItems)));
        } catch {
          setOriginalValues(prev => ({ ...prev, checklist: [] }));
          setChecklist([]);
          setOriginalChecklist([]);
        }

        // Apply proposed changes to form data
        setFormData({
          title: proposedChanges.title ?? (card.title || ''),
          description: proposedChanges.description ?? (card.description || ''),
          due_date: proposedChanges.due_date ?? (card.due_date || ''),
          priority: proposedChanges.priority ?? mapPriorityFromBackend(card.priority || ''),
          assignee_id: proposedChanges.assignee_id !== undefined ? proposedChanges.assignee_id : (card.assignee_id ?? null),
          label_ids: proposedChanges.label_ids ?? (card.labels?.map(l => l.id) || []),
          list_id: proposedChanges.list_id ?? card.list_id
        });
        
        setOriginalFormData({
          title: card.title || '',
          description: card.description || '',
          due_date: card.due_date || '',
          priority: mapPriorityFromBackend(card.priority || ''),
          assignee_id: card.assignee_id ?? null,
          label_ids: card.labels?.map(l => l.id) || [],
          list_id: card.list_id
        });
      } else {
        // Load card data for existing card (normal edit mode)
        const initialFormData = {
          title: card.title || '',
          description: card.description || '',
          due_date: card.due_date || '',
          priority: mapPriorityFromBackend(card.priority || ''),
          assignee_id: card.assignee_id ?? null,
          label_ids: card.labels?.map(l => l.id) || [],
          list_id: card.list_id
        };
        setFormData(initialFormData);
        setOriginalFormData(initialFormData);

        // Load checklist items
        try {
          const items = await cardItemsService.getItems(card.id);
          const checklistItems = items.map(i => ({ id: i.id, text: i.text, is_done: i.is_done, position: i.position }));
          setChecklist(ensureChecklistClientIds(checklistItems));
          setOriginalChecklist(JSON.parse(JSON.stringify(checklistItems))); // Deep copy
        } catch {
          setChecklist([]);
          setOriginalChecklist([]);
        }
      }
    } catch (error) {
      toast({
        title: t('common.error'),
        description: t('card.loadError'),
        variant: 'destructive'
      });
    }
  };

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

  // Check if there are unsaved changes
  const hasUnsavedChanges = () => {
    // Check form data changes
    const formChanged = 
      formData.title !== originalFormData.title ||
      formData.description !== originalFormData.description ||
      formData.due_date !== originalFormData.due_date ||
      formData.priority !== originalFormData.priority ||
      formData.assignee_id !== originalFormData.assignee_id ||
      formData.list_id !== originalFormData.list_id ||
      JSON.stringify(formData.label_ids.sort()) !== JSON.stringify(originalFormData.label_ids.sort());

    // Check checklist changes
    const checklistChanged = JSON.stringify(checklist) !== JSON.stringify(originalChecklist);

    return formChanged || checklistChanged;
  };

  const handleClose = () => {
    if (!isViewOnly && hasUnsavedChanges()) {
      setShowConfirmClose(true);
    } else {
      onClose();
    }
  };

  const handleConfirmClose = () => {
    setShowConfirmClose(false);
    onClose();
  };

  const handleCancelClose = () => {
    setShowConfirmClose(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!canEditCard) {
      return;
    }

    setLoading(true);

    try {
      // Check if this is a new card (id === 0) or an existing card
      const isNewCard = card.id === 0;
      let savedCard: Card;

      if (isNewCard) {
        // Create new card - ensure title is provided
        const createPayload = {
          title: formData.title || 'Nouvelle carte',
          description: formData.description?.trim() === '' ? null : formData.description,
          due_date: formData.due_date && formData.due_date !== '' ? formData.due_date : null,
          priority: mapPriorityToBackend(formData.priority),
          assignee_id: typeof formData.assignee_id === 'number' ? formData.assignee_id : null,
          list_id: formData.list_id,
          ...(formData.label_ids.length > 0 ? { label_ids: formData.label_ids } : {})
        };
        savedCard = await cardService.createCard(createPayload);
      } else {
        // Update existing card
        const updatePayload: UpdateCardData = {
          title: formData.title,
          description: formData.description?.trim() === '' ? null : formData.description,
          due_date: formData.due_date && formData.due_date !== '' ? formData.due_date : null,
          priority: mapPriorityToBackend(formData.priority),
          assignee_id: typeof formData.assignee_id === 'number' ? formData.assignee_id : null,
          list_id: formData.list_id,
          ...(formData.label_ids.length > 0 ? { label_ids: formData.label_ids } : {})
        };
        savedCard = await cardService.updateCard(card.id, updatePayload);
      }

      // Update checklist items
      try {
        for (let idx = 0; idx < checklist.length; idx++) {
          const item = checklist[idx];
          if (!item.text || item.text.trim() === '') {
            continue;
          }
          if (item.id) {
            await cardItemsService.updateItem(item.id, { text: item.text, is_done: item.is_done, position: idx + 1 });
          } else {
            await cardItemsService.createItem(savedCard.id, item.text, idx + 1, item.is_done);
          }
        }
        const latest = await cardItemsService.getItems(savedCard.id);
        savedCard.items = latest as any;
      } catch {
        // Ignore checklist errors
      }

      onSave(savedCard);
      onClose();
      toast({
        title: isNewCard ? t('card.createSuccess') : t('card.updateSuccess'),
        variant: 'success'
      });
    } catch (error: any) {
      toast({
        title: error.response?.data?.detail || t('card.saveError'),
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete || !canDeleteCard) {
      return;
    }

    try {
      onDelete(card.id);
      onClose();
    } catch (error: any) {
      toast({
        title: t('card.archiveError'),
        description: error.response?.data?.detail || t('card.archiveErrorDescription'),
        variant: 'destructive'
      });
    }
  };

  const handleLabelToggle = (labelId: number) => {
    setFormData(prev => ({
      ...prev,
      label_ids: prev.label_ids.includes(labelId)
        ? prev.label_ids.filter(id => id !== labelId)
        : [...prev.label_ids, labelId]
    }));
  };

  const addChecklistItem = () => {
    const text = newItemText.trim().slice(0, 64);
    if (!text) {
      return;
    }
    const clientId = `temp-${checklistIdCounter.current++}`;
    setChecklist(prev => [...prev, { text, is_done: false, position: prev.length + 1, clientId }]);
    setNewItemText('');
  };

  const toggleChecklistItem = async (index: number) => {
    const item = checklist[index];

    if (item?.id && card?.id) {
      try {
        const updated = await cardItemsService.updateItem(item.id, { is_done: !item.is_done });
        setChecklist(prev => prev.map((it, i) => i === index ? { ...it, is_done: updated.is_done } : it));
      } catch (error: any) {
        toast({
          title: t('common.error'),
          description: error.response?.data?.detail || t('card.updateChecklistItemError'),
          variant: 'destructive'
        });
      }
    } else {
      setChecklist(prev => prev.map((it, i) => i === index ? { ...it, is_done: !it.is_done } : it));
    }
  };

  const updateChecklistItemText = (index: number, text: string) => {
    const limited = text.slice(0, 64);
    setChecklist(prev => prev.map((it, i) => i === index ? { ...it, text: limited } : it));
  };

  const deleteChecklistItem = async (index: number) => {
    const item = checklist[index];
    if (item?.id) {
      try {
        await cardItemsService.deleteItem(item.id);
      } catch {
        // Ignore
      }
    }
    setChecklist(prev => prev.filter((_, i) => i !== index).map((it, i) => ({ ...it, position: i + 1 })));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) {
      return;
    }
    const oldIndex = checklist.findIndex(i => getChecklistItemKey(i) === active.id);
    const newIndex = checklist.findIndex(i => getChecklistItemKey(i) === over.id);
    if (oldIndex === -1 || newIndex === -1) {
      return;
    }
    const newItems = arrayMove(checklist, oldIndex, newIndex).map((it, idx) => ({ ...it, position: idx + 1 }));
    setChecklist(newItems);
  };

  // Configure sensors for better touch support
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px of movement required before drag starts
      },
    })
  );

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 animate-fade-in"
        onClick={handleClose}
      />

      {/* Full screen modal */}
      <div className="fixed inset-0 bg-background z-50 overflow-y-auto animate-slide-up">
        {/* Header */}
        <div className="sticky top-0 bg-card border-b-2 border-border z-10">
          <div className="flex items-center justify-between p-4" style={{ paddingTop: 'calc(1rem + env(safe-area-inset-top))' }}>
            <button
              onClick={handleClose}
              className="p-2 text-muted-foreground hover:text-foreground active:bg-accent rounded-lg transition-colors"
              aria-label={t('common.close')}
            >
              <X className="w-6 h-6" />
            </button>
            <h2 className="text-lg font-bold text-foreground">
              {card.id === 0 ? t('card.newCard') : (isViewOnly ? t('card.viewCard') : t('card.editCard'))}
            </h2>
            {!isViewOnly ? (
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="p-2 text-primary hover:text-primary/80 active:bg-accent rounded-lg transition-colors disabled:opacity-50"
                aria-label={t('common.save')}
              >
                <Save className="w-6 h-6" />
              </button>
            ) : (
              <div className="w-10" />
            )}
          </div>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-4 space-y-6 pb-safe">
          {/* List selector */}
          <div className="space-y-2 relative list-dropdown-container">
            <label className="text-sm font-medium text-foreground">{t('card.list')}</label>
            <HighlightedField
              isChanged={getFieldChangeInfo('list_id').isChanged}
              tooltipContent={getFieldChangeInfo('list_id').tooltipContent}
            >
              <button
                type="button"
                onClick={() => !isViewOnly && setShowListDropdown(!showListDropdown)}
                disabled={isViewOnly}
                className="w-full btn-touch bg-card border-2 border-border rounded-lg px-4 text-foreground disabled:opacity-50 flex items-center justify-between"
              >
                <span className="truncate">
                  {lists.find(l => l.id === formData.list_id)?.name || t('card.selectList')}
                </span>
                <ChevronDown className="w-5 h-5 text-muted-foreground flex-shrink-0 ml-2" />
              </button>
            </HighlightedField>

            {/* List dropdown */}
            {showListDropdown && !isViewOnly && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-card border-2 border-border rounded-lg shadow-lg z-10 max-h-60 overflow-y-auto">
                {lists.map((list) => {
                  const isSelected = formData.list_id === list.id;
                  return (
                    <button
                      key={list.id}
                      type="button"
                      onClick={() => {
                        setFormData(prev => ({ ...prev, list_id: list.id }));
                        setShowListDropdown(false);
                      }}
                      className={`w-full px-4 py-3 text-left hover:bg-accent transition-colors ${
                        isSelected ? 'bg-accent/50 font-medium' : ''
                      }`}
                    >
                      <span className="text-sm">{list.name}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Title */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{t('card.title')} *</label>
            <HighlightedField
              isChanged={getFieldChangeInfo('title').isChanged}
              tooltipContent={getFieldChangeInfo('title').tooltipContent}
            >
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                required
                readOnly={isViewOnly}
                disabled={isViewOnly}
                className="w-full btn-touch bg-card border-2 border-border rounded-lg px-4 text-foreground disabled:opacity-50"
              />
            </HighlightedField>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{t('card.description')}</label>
            <HighlightedField
              isChanged={getFieldChangeInfo('description').isChanged}
              tooltipContent={getFieldChangeInfo('description').tooltipContent}
            >
              <textarea
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                rows={4}
                readOnly={isViewOnly}
                disabled={isViewOnly}
                className="w-full bg-card border-2 border-border rounded-lg px-4 py-3 text-foreground disabled:opacity-50 resize-none"
              />
            </HighlightedField>
          </div>

          {/* Checklist */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{t('card.checklist')}</label>
            <div className="space-y-2">
              <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd} sensors={sensors}>
                <SortableContext items={checklist.map(item => getChecklistItemKey(item))} strategy={verticalListSortingStrategy}>
                  {checklist.map((item, index) => {
                    const changeInfo = getChecklistItemChangeInfo(item, index);
                    const itemKey = getChecklistItemKey(item);
                    return (
                      <SortableChecklistItem key={itemKey} id={itemKey}>
                        {({ attributes, listeners }: any) => (
                          <div className="flex items-center gap-2">
                            {!isViewOnly && (
                              <div
                                className="p-2 text-muted-foreground cursor-grab active:cursor-grabbing"
                                {...attributes}
                                {...listeners}
                              >
                                <GripVertical className="w-5 h-5" />
                              </div>
                            )}
                            <HighlightedField
                              isChanged={changeInfo.statusChanged}
                              tooltipContent={changeInfo.statusTooltip}
                            >
                              <input
                                type="checkbox"
                                className="h-5 w-5 rounded border-2 border-border"
                                checked={item.is_done}
                                onChange={() => toggleChecklistItem(index)}
                                disabled={isViewOnly && !canToggleChecklistItems}
                              />
                            </HighlightedField>
                            <HighlightedField
                              isChanged={changeInfo.textChanged}
                              tooltipContent={changeInfo.textTooltip}
                              className="flex-1"
                            >
                              <input
                                type="text"
                                value={item.text}
                                onChange={(e) => updateChecklistItemText(index, e.target.value)}
                                className={`w-full bg-card border-2 border-border rounded-lg px-3 py-2 text-sm ${
                                  item.is_done ? 'line-through text-muted-foreground' : 'text-foreground'
                                } disabled:opacity-50`}
                                maxLength={64}
                                readOnly={isViewOnly}
                                disabled={isViewOnly}
                              />
                            </HighlightedField>
                            {!isViewOnly && (
                              <button
                                type="button"
                                onClick={() => deleteChecklistItem(index)}
                                className="p-2 text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
                              >
                                <Trash2 className="w-5 h-5" />
                              </button>
                            )}
                          </div>
                        )}
                      </SortableChecklistItem>
                    );
                  })}
                </SortableContext>
              </DndContext>
              {!isViewOnly && (
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    placeholder={t('card.addChecklistItem')}
                    value={newItemText}
                    onChange={(e) => setNewItemText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addChecklistItem();
                      }
                    }}
                    maxLength={64}
                    className="flex-1 bg-card border-2 border-border rounded-lg px-3 py-2 text-sm text-foreground"
                  />
                  <button
                    type="button"
                    onClick={addChecklistItem}
                    className="p-2 text-primary hover:bg-primary/10 rounded-lg transition-colors"
                  >
                    <Plus className="w-5 h-5" />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Labels */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{t('card.labels')}</label>
            <HighlightedField
              isChanged={getFieldChangeInfo('labels').isChanged}
              tooltipContent={getFieldChangeInfo('labels').tooltipContent}
            >
              <div className="flex flex-wrap gap-2 p-2 rounded-lg">
                {labels.map(label => (
                  <button
                    key={label.id}
                    type="button"
                    onClick={isViewOnly ? undefined : () => handleLabelToggle(label.id)}
                    disabled={isViewOnly}
                    className="px-3 py-1.5 text-sm font-medium border-2 rounded-lg transition-colors disabled:opacity-50"
                    style={{
                      backgroundColor: formData.label_ids.includes(label.id) ? label.color : 'transparent',
                      borderColor: label.color,
                      color: formData.label_ids.includes(label.id) ? '#ffffff' : label.color
                    }}
                  >
                    {label.name}
                  </button>
                ))}
              </div>
            </HighlightedField>
          </div>

          {/* Priority */}
          <div className="space-y-2 relative priority-dropdown-container">
            <label className="text-sm font-medium text-foreground">{t('card.priority')}</label>
            <HighlightedField
              isChanged={getFieldChangeInfo('priority').isChanged}
              tooltipContent={getFieldChangeInfo('priority').tooltipContent}
            >
              <button
                type="button"
                onClick={() => !isViewOnly && setShowPriorityDropdown(!showPriorityDropdown)}
                disabled={isViewOnly}
                className="w-full btn-touch bg-card border-2 border-border rounded-lg px-4 text-foreground disabled:opacity-50 flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  {(() => {
                    const Icon = getPriorityIcon(formData.priority);
                    const iconColor = getPriorityIconColor(formData.priority);
                    return (
                      <>
                        <Icon className={`w-5 h-5 ${iconColor}`} />
                        <span className="capitalize">{t(`priority.${formData.priority}`)}</span>
                      </>
                    );
                  })()}
                </div>
                <ChevronDown className="w-5 h-5 text-muted-foreground" />
              </button>
            </HighlightedField>

            {/* Priority dropdown */}
            {showPriorityDropdown && !isViewOnly && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-card border-2 border-border rounded-lg shadow-lg z-10 overflow-hidden">
                {(['high', 'medium', 'low'] as const).map((priority) => {
                  const Icon = getPriorityIcon(priority);
                  const iconColor = getPriorityIconColor(priority);
                  const isSelected = formData.priority === priority;
                  return (
                    <button
                      key={priority}
                      type="button"
                      onClick={() => {
                        setFormData(prev => ({ ...prev, priority }));
                        setShowPriorityDropdown(false);
                      }}
                      className={`w-full px-4 py-3 flex items-center gap-2 hover:bg-accent transition-colors ${
                        isSelected ? 'bg-accent/50' : ''
                      }`}
                    >
                      <Icon className={`w-5 h-5 ${iconColor}`} />
                      <span className="capitalize text-sm">{t(`priority.${priority}`)}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Due Date */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{t('card.dueDate')}</label>
            <HighlightedField
              isChanged={getFieldChangeInfo('due_date').isChanged}
              tooltipContent={getFieldChangeInfo('due_date').tooltipContent}
            >
              <input
                type="date"
                value={formData.due_date}
                onChange={(e) => setFormData(prev => ({ ...prev, due_date: e.target.value }))}
                readOnly={isViewOnly}
                disabled={isViewOnly}
                className="w-full btn-touch bg-card border-2 border-border rounded-lg px-4 text-foreground disabled:opacity-50"
              />
            </HighlightedField>
          </div>

          {/* Assignee */}
          <div className="space-y-2 relative assignee-dropdown-container">
            <label className="text-sm font-medium text-foreground">{t('card.assignee')}</label>
            <HighlightedField
              isChanged={getFieldChangeInfo('assignee_id').isChanged}
              tooltipContent={getFieldChangeInfo('assignee_id').tooltipContent}
            >
              <button
                type="button"
                onClick={() => !isViewOnly && setShowAssigneeDropdown(!showAssigneeDropdown)}
                disabled={isViewOnly}
                className="w-full btn-touch bg-card border-2 border-border rounded-lg px-4 text-foreground disabled:opacity-50 flex items-center justify-between"
              >
                <div className="flex items-center gap-2 truncate">
                  {formData.assignee_id ? (
                    (() => {
                      const selectedUser = users.find(u => u.id === formData.assignee_id);
                      if (selectedUser) {
                        const RoleIcon = getUserRoleIcon(selectedUser.role);
                        return (
                          <>
                            <RoleIcon className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                            <span className="truncate">{selectedUser.display_name}</span>
                          </>
                        );
                      }
                      return <span className="italic truncate">{t('card.unassign')}</span>;
                    })()
                  ) : (
                    <span className="italic truncate">{t('card.unassign')}</span>
                  )}
                </div>
                <ChevronDown className="w-5 h-5 text-muted-foreground flex-shrink-0 ml-2" />
              </button>
            </HighlightedField>

            {/* Assignee dropdown */}
            {showAssigneeDropdown && !isViewOnly && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-card border-2 border-border rounded-lg shadow-lg z-10 max-h-60 overflow-y-auto">
                {/* Unassign option */}
                <button
                  type="button"
                  onClick={() => {
                    setFormData(prev => ({ ...prev, assignee_id: null }));
                    setShowAssigneeDropdown(false);
                  }}
                  className={`w-full px-4 py-3 text-left hover:bg-accent transition-colors ${
                    !formData.assignee_id ? 'bg-accent/50 font-medium' : ''
                  }`}
                >
                  <span className="text-sm italic">{t('card.unassign')}</span>
                </button>
                
                {/* Users list */}
                {users
                  .slice()
                  .sort((a, b) => (a.display_name || '').localeCompare(b.display_name || ''))
                  .map(user => {
                    const isSelected = formData.assignee_id === user.id;
                    const RoleIcon = getUserRoleIcon(user.role);
                    return (
                      <button
                        key={user.id}
                        type="button"
                        onClick={() => {
                          setFormData(prev => ({ ...prev, assignee_id: user.id }));
                          setShowAssigneeDropdown(false);
                        }}
                        className={`w-full px-4 py-3 text-left hover:bg-accent transition-colors flex items-center gap-2 ${
                          isSelected ? 'bg-accent/50 font-medium' : ''
                        }`}
                      >
                        <RoleIcon className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                        <span className="text-sm truncate">{user.display_name}</span>
                      </button>
                    );
                  })}
              </div>
            )}
          </div>

          {/* Delete button */}
          {onDelete && !isViewOnly && canDeleteCard && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={loading}
              className="w-full btn-touch bg-destructive text-destructive-foreground font-medium rounded-lg hover:bg-destructive/90 active:bg-destructive/80 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Trash2 className="w-5 h-5" />
              {t('card.archiveCard')}
            </button>
          )}
        </form>
      </div>

      {/* Confirmation dialog for unsaved changes */}
      {showConfirmClose && (
        <>
          {/* Backdrop for confirmation */}
          <div className="fixed inset-0 bg-black/70 z-[60] animate-fade-in" />
          
          {/* Confirmation dialog */}
          <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
            <div className="bg-card border-2 border-border rounded-lg shadow-xl max-w-md w-full animate-slide-up">
              {/* Header */}
              <div className="p-4 border-b-2 border-border">
                <h3 className="text-lg font-bold text-foreground">
                  {t('card.unsavedChanges')}
                </h3>
              </div>
              
              {/* Content */}
              <div className="p-4">
                <p className="text-sm text-muted-foreground">
                  {t('card.unsavedChangesDescription')}
                </p>
              </div>
              
              {/* Actions */}
              <div className="p-4 border-t-2 border-border flex gap-2 justify-end">
                <button
                  onClick={handleCancelClose}
                  className="btn-touch px-4 bg-muted text-foreground font-medium rounded-lg hover:bg-muted/80 active:bg-muted/60 transition-colors"
                >
                  {t('card.keepEditing')}
                </button>
                <button
                  onClick={handleConfirmClose}
                  className="btn-touch px-4 bg-destructive text-destructive-foreground font-medium rounded-lg hover:bg-destructive/90 active:bg-destructive/80 transition-colors"
                >
                  {t('card.discardChanges')}
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
};

export default CardDetail;


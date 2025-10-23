import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  X,
  Save,
  Trash2,
  GripVertical,
  Plus,
  ChevronDown
} from 'lucide-react';
import { DndContext, closestCenter, DragEndEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Card, Label as LabelType, KanbanList, UpdateCardData, getPriorityIcon, getPriorityIconColor } from '@shared/types';
import { useAuth } from '@shared/hooks/useAuth';
import { useUsers } from '@shared/hooks/useUsers';
import { usePermissions } from '@shared/hooks/usePermissions';
import { useToast } from '@shared/hooks/use-toast';
import { cardService, labelService, cardItemsService } from '@shared/services/api';
import { listsApi } from '@shared/services/listsApi';
import { mapPriorityFromBackend, mapPriorityToBackend } from '@shared/lib/priority';

interface CardDetailProps {
  card: Card;
  isOpen: boolean;
  onClose: () => void;
  onSave: (card: Card) => void;
  onDelete?: (cardId: number) => void;
}

const CardDetail = ({ card, isOpen, onClose, onSave, onDelete }: CardDetailProps) => {
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
  const [checklist, setChecklist] = useState<{ id?: number; text: string; is_done: boolean; position: number }[]>([]);
  const [newItemText, setNewItemText] = useState('');
  const [loading, setLoading] = useState(false);
  const [showConfirmClose, setShowConfirmClose] = useState(false);
  const [showPriorityDropdown, setShowPriorityDropdown] = useState(false);
  
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
  const [originalChecklist, setOriginalChecklist] = useState<{ id?: number; text: string; is_done: boolean; position: number }[]>([]);

  const canEditCardContent = permissions.canModifyCardContent(card);
  const canEditCardMetadata = permissions.canModifyCardMetadata(card);
  const canEditCard = canEditCardContent || canEditCardMetadata;
  const canDeleteCard = permissions.canDeleteCard;
  const canToggleChecklistItems = permissions.canToggleCardItem(card);

  const isViewOnly = !canEditCard;

  useEffect(() => {
    if (isOpen && card) {
      loadData();
    }
  }, [isOpen, card]);

  // Close priority dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (showPriorityDropdown && !target.closest('.priority-dropdown-container')) {
        setShowPriorityDropdown(false);
      }
    };

    if (showPriorityDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showPriorityDropdown]);

  const loadData = async () => {
    try {
      const [labelsData, listsData] = await Promise.all([
        labelService.getLabels(),
        listsApi.getLists()
      ]);
      setLabels(labelsData);
      setLists(listsData);

      // Load card data
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
        setChecklist(checklistItems);
        setOriginalChecklist(JSON.parse(JSON.stringify(checklistItems))); // Deep copy
      } catch {
        setChecklist([]);
        setOriginalChecklist([]);
      }
    } catch (error) {
      toast({
        title: t('common.error'),
        description: t('card.loadError'),
        variant: 'destructive'
      });
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
      const updatePayload: UpdateCardData = {
        title: formData.title,
        description: formData.description?.trim() === '' ? null : formData.description,
        due_date: formData.due_date && formData.due_date !== '' ? formData.due_date : null,
        priority: mapPriorityToBackend(formData.priority),
        assignee_id: typeof formData.assignee_id === 'number' ? formData.assignee_id : null,
        list_id: formData.list_id,
        ...(formData.label_ids.length > 0 ? { label_ids: formData.label_ids } : {})
      };

      const savedCard = await cardService.updateCard(card.id, updatePayload);

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
        title: t('card.updateSuccess'),
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
    setChecklist(prev => [...prev, { text, is_done: false, position: prev.length + 1 }]);
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
    const oldIndex = checklist.findIndex(i => (i.id ?? `new-${i.position}`) === active.id);
    const newIndex = checklist.findIndex(i => (i.id ?? `new-${i.position}`) === over.id);
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

  // Sortable item component for checklist
  type DragRender = (args: { attributes: any; listeners: any }) => React.ReactNode;
  const SortableItem = ({ id, children }: { id: string | number; children: React.ReactNode | DragRender }) => {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
    const style = {
      transform: CSS.Transform.toString(transform),
      transition,
      opacity: isDragging ? 0.6 : 1
    } as React.CSSProperties;
    return (
      <div ref={setNodeRef} style={style} className="touch-none">
        {typeof children === 'function' ? (children as DragRender)({ attributes, listeners }) : children}
      </div>
    );
  };

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
              {isViewOnly ? t('card.viewCard') : t('card.editCard')}
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
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{t('card.list')}</label>
            <select
              value={formData.list_id}
              onChange={(e) => setFormData(prev => ({ ...prev, list_id: parseInt(e.target.value) }))}
              disabled={isViewOnly}
              className="w-full btn-touch bg-card border-2 border-border rounded-lg px-4 text-foreground disabled:opacity-50"
            >
              {lists.map(list => (
                <option key={list.id} value={list.id}>
                  {list.name}
                </option>
              ))}
            </select>
          </div>

          {/* Title */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{t('card.title')} *</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              required
              readOnly={isViewOnly}
              disabled={isViewOnly}
              className="w-full btn-touch bg-card border-2 border-border rounded-lg px-4 text-foreground disabled:opacity-50"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{t('card.description')}</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              rows={4}
              readOnly={isViewOnly}
              disabled={isViewOnly}
              className="w-full bg-card border-2 border-border rounded-lg px-4 py-3 text-foreground disabled:opacity-50 resize-none"
            />
          </div>

          {/* Checklist */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{t('card.checklist')}</label>
            <div className="space-y-2">
              <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd} sensors={sensors}>
                <SortableContext items={checklist.map(i => i.id ?? `new-${i.position}`)} strategy={verticalListSortingStrategy}>
                  {checklist.map((item, index) => (
                    <SortableItem key={item.id ?? `new-${item.position}`} id={item.id ?? `new-${item.position}`}>
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
                          <input
                            type="checkbox"
                            className="h-5 w-5 rounded border-2 border-border"
                            checked={item.is_done}
                            onChange={() => toggleChecklistItem(index)}
                            disabled={isViewOnly && !canToggleChecklistItems}
                          />
                          <input
                            type="text"
                            value={item.text}
                            onChange={(e) => updateChecklistItemText(index, e.target.value)}
                            className={`flex-1 bg-card border-2 border-border rounded-lg px-3 py-2 text-sm ${
                              item.is_done ? 'line-through text-muted-foreground' : 'text-foreground'
                            } disabled:opacity-50`}
                            maxLength={64}
                            readOnly={isViewOnly}
                            disabled={isViewOnly}
                          />
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
                    </SortableItem>
                  ))}
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
            <div className="flex flex-wrap gap-2">
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
          </div>

          {/* Priority */}
          <div className="space-y-2 relative priority-dropdown-container">
            <label className="text-sm font-medium text-foreground">{t('card.priority')}</label>
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
            <input
              type="date"
              value={formData.due_date}
              onChange={(e) => setFormData(prev => ({ ...prev, due_date: e.target.value }))}
              readOnly={isViewOnly}
              disabled={isViewOnly}
              className="w-full btn-touch bg-card border-2 border-border rounded-lg px-4 text-foreground disabled:opacity-50"
            />
          </div>

          {/* Assignee */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{t('card.assignee')}</label>
            <select
              value={formData.assignee_id?.toString() || 'none'}
              onChange={(e) => setFormData(prev => ({
                ...prev,
                assignee_id: e.target.value === 'none' ? null : parseInt(e.target.value)
              }))}
              disabled={isViewOnly}
              className="w-full btn-touch bg-card border-2 border-border rounded-lg px-4 text-foreground disabled:opacity-50"
            >
              <option value="none">{t('card.unassign')}</option>
              {users
                .slice()
                .sort((a, b) => (a.display_name || '').localeCompare(b.display_name || ''))
                .map(user => (
                  <option key={user.id} value={user.id}>
                    {user.display_name}
                  </option>
                ))}
            </select>
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


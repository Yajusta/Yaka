import { closestCenter, DndContext, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { ArrowDown, ArrowUp, GripVertical, Minus, Trash2, X } from 'lucide-react';
import { FormEvent, useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useToast } from '../../hooks/use-toast.tsx';
import { useAuth } from '../../hooks/useAuth';
import { usePermissions } from '../../hooks/usePermissions';
import { useUsers } from '../../hooks/useUsers';
import { mapPriorityFromBackend, mapPriorityToBackend } from '../../lib/priority';
import { cardItemsService, cardService, labelService } from '../../services/api.tsx';
import { Card, CardPriority, Label as LabelType } from '../../types/index.ts';
import { Badge } from '../ui/badge.tsx';
import { Button } from '../ui/button.tsx';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog.tsx';
import { Input } from '../ui/input.tsx';
import { Label } from '../ui/label.tsx';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select.tsx';
import { Textarea } from '../ui/textarea.tsx';

interface CardFormProps {
    card: Card | null;
    isOpen: boolean;
    onClose: () => void;
    onSave: (card: Card) => void;
    onDelete?: (cardId: number) => void;
    defaultListId?: number; // ID de la liste par défaut pour les nouvelles cartes
    initialData?: {
        title?: string;
        description?: string;
        due_date?: string;
        priority?: string;
        assignee_id?: number | null;
        label_ids?: number[];
        checklist?: { id?: number; text: string; is_done: boolean; position: number }[];
    };
}

interface FormData {
    title: string;
    description: string;
    due_date: string;
    priority: string;
    assignee_id: number | null;
    label_ids: number[];
    list_id: number;
}

const CardForm = ({ card, isOpen, onClose, onSave, onDelete, defaultListId, initialData }: CardFormProps) => {
    const { t } = useTranslation();
    const [formData, setFormData] = useState<FormData>({
        title: '',
        description: '',
        due_date: '',
        // use internal english keys by default
        priority: 'medium',
        assignee_id: null,
        label_ids: [],
        list_id: defaultListId ?? -1 // Utiliser -1 par défaut pour laisser le backend choisir la plus basse
    });
    const { toast } = useToast();
    const { users } = useUsers();
    const { user: currentUser } = useAuth();
    const currentUserId = currentUser?.id ?? null;
    const permissions = usePermissions(currentUser);
    const isEditing = Boolean(card);
    const { canCreateCard } = permissions;

    // For editing, check if user can modify content OR metadata (not just checklist items)
    const canEditCardContent = isEditing ? permissions.canModifyCardContent(card!) : canCreateCard;
    const canEditCardMetadata = isEditing ? permissions.canModifyCardMetadata(card!) : canCreateCard;
    const canEditCard = canEditCardContent || canEditCardMetadata;
    const { canDeleteCard } = permissions;

    // Check if user can toggle checklist items (CONTRIBUTOR can do this)
    const canToggleChecklistItems = isEditing ? permissions.canToggleCardItem(card!) : canCreateCard;

    // For EDITOR role, enforce self-assignment on creation
    const isEditorRole = permissions.isEditorOrAbove && !permissions.isSupervisorOrAbove;
    const shouldEnforceSelfAssignment = !isEditing && isEditorRole;

    // Determine if we're in view-only mode
    const isViewOnly = isEditing && !canEditCard;

    const [labels, setLabels] = useState<LabelType[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [checklist, setChecklist] = useState<{ id?: number; text: string; is_done: boolean; position: number }[]>([]);
    const [newItemText, setNewItemText] = useState<string>('');

    useEffect(() => {
        if (isOpen && !canEditCard && !isEditing) {
            onClose();
        }
    }, [isOpen, canEditCard, isEditing, onClose]);

    const loadData = useCallback(async (): Promise<void> => {
        try {
            const labelsData = await labelService.getLabels();
            setLabels(labelsData);
        } catch {
            toast({
                title: t('common.error'),
                description: t('card.loadError'),
                variant: "destructive"
            });
        }
    }, [toast]);

    useEffect(() => {
        if (isOpen) {
            const run = async () => {
                await loadData();
                if (card) {
                    setFormData({
                        title: card.title || '',
                        description: card.description || '',
                        due_date: card.due_date || '',
                        priority: mapPriorityFromBackend(card.priority || ''),
                        assignee_id: card.assignee_id ?? null,
                        label_ids: card.labels?.map(l => l.id) || [],
                        list_id: card.list_id
                    });
                    // Load existing items for edit
                    try {
                        const items = await cardItemsService.getItems(card.id);
                        setChecklist(items.map(i => ({ id: i.id, text: i.text, is_done: i.is_done, position: i.position })));
                    } catch { /* ignore */ }
                } else {
                    // Utiliser initialData si fourni, sinon valeurs par défaut
                    setFormData({
                        title: initialData?.title || '',
                        description: initialData?.description || '',
                        due_date: initialData?.due_date || '',
                        priority: initialData?.priority || CardPriority.MEDIUM,
                        assignee_id: initialData?.assignee_id ?? (shouldEnforceSelfAssignment ? currentUserId ?? null : null),
                        label_ids: initialData?.label_ids || [],
                        list_id: defaultListId ?? -1 // Utiliser -1 par défaut
                    });
                    setChecklist(initialData?.checklist || []);
                }
            };
            run();
        }
    }, [isOpen, card, loadData]);

    const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
        e.preventDefault();

        if (!canEditCard) {
            return;
        }

        if (shouldEnforceSelfAssignment && (typeof formData.assignee_id !== 'number' || formData.assignee_id !== currentUserId)) {
            toast({
                title: t('card.selfAssignmentRequired'),
                variant: 'destructive'
            });
            return;
        }

        setLoading(true);

        try {
            // Sanitize payload to match backend schema types (priority mapping delegated to shared util)

            const basePayload = {
                title: formData.title,
                description: formData.description?.trim() === '' ? null : formData.description,
                due_date: formData.due_date && formData.due_date !== '' ? formData.due_date : null,
                priority: mapPriorityToBackend(formData.priority),
                assignee_id: typeof formData.assignee_id === 'number' ? formData.assignee_id : null,
                list_id: formData.list_id
            };

            const labelIds = Array.isArray(formData.label_ids) ? formData.label_ids.map(Number) : [];
            const createPayload = {
                ...basePayload,
                ...(labelIds.length > 0 ? { label_ids: labelIds } : {})
            };

            const updatePayload = {
                ...basePayload,
                ...(labelIds.length > 0 ? { label_ids: labelIds } : {})
            };

            let savedCard: Card;
            if (card) {
                savedCard = await cardService.updateCard(card.id, updatePayload);
            } else {
                savedCard = await cardService.createCard(createPayload);
            }
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
            } catch { /* ignore checklist errors to not block card save */ }
            onSave(savedCard);
            onClose();
            toast({
                title: card ? t('card.updateSuccess') : t('card.createSuccess'),
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

    const handleLabelToggle = (labelId: number): void => {
        setFormData(prev => ({
            ...prev,
            label_ids: prev.label_ids.includes(labelId)
                ? prev.label_ids.filter(id => id !== labelId)
                : [...prev.label_ids, labelId]
        }));
    };

    const addChecklistItem = (): void => {
        const text = newItemText.trim().slice(0, 64);
        if (!text) {
            return;
        }
        setChecklist(prev => [...prev, { text: text, is_done: false, position: prev.length + 1 }]);
        setNewItemText('');
    };

    const toggleChecklistItem = async (index: number): Promise<void> => {
        const item = checklist[index];

        // If the item has an ID and card exists, update it via API immediately (for CONTRIBUTOR)
        if (item?.id && card?.id) {
            try {
                const updated = await cardItemsService.updateItem(item.id, { is_done: !item.is_done });
                setChecklist(prev => prev.map((it, i) => i === index ? { ...it, is_done: updated.is_done } : it));
                // Also update the parent card's items in memory (without closing the form)
                if (card.items) {
                    card.items = card.items.map(it => it.id === item.id ? { ...it, is_done: updated.is_done } : it);
                }
            } catch (error: any) {
                toast({
                    title: t('common.error'),
                    description: error.response?.data?.detail || t('card.updateChecklistItemError'),
                    variant: 'destructive'
                });
            }
        } else {
            // For new items not yet saved, just update local state
            setChecklist(prev => prev.map((it, i) => i === index ? { ...it, is_done: !it.is_done } : it));
        }
    };

    const updateChecklistItemText = (index: number, text: string): void => {
        const limited = text.slice(0, 64);
        setChecklist(prev => prev.map((it, i) => i === index ? { ...it, text: limited } : it));
    };

    const deleteChecklistItem = async (index: number): Promise<void> => {
        const item = checklist[index];
        if (item?.id) {
            try { await cardItemsService.deleteItem(item.id); } catch { /* ignore */ }
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

    type DragRender = (args: { attributes: any; listeners: any }) => React.ReactNode;
    const SortableItem = ({ id, children }: { id: string | number; children: React.ReactNode | DragRender }) => {
        const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
        // Style inline nécessaire pour @dnd-kit - propriétés dynamiques qui ne peuvent être en CSS
        const style = {
            transform: CSS.Transform.toString(transform),
            transition,
            opacity: isDragging ? 0.6 : 1
        } as React.CSSProperties;
        return (
            <div ref={setNodeRef} style={style} className="touch-none">
                {/* Inject drag handle via function-as-child pattern */}
                {typeof children === 'function' ? (children as DragRender)({ attributes, listeners }) : children}
            </div>
        );
    };

    const handleDelete = async (): Promise<void> => {
        if (!card || !onDelete || !canDeleteCard) {
            return;
        }

        try {
            onDelete(card.id);
            onClose();
        } catch (error: any) {
            toast({
                title: t('card.archiveError'),
                description: error.response?.data?.detail || t('card.archiveErrorDescription'),
                variant: "destructive"
            });
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-h-screen overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>
                        {isViewOnly ? t('card.viewCard') : (card ? t('card.editCard') : t('card.newCard'))}
                    </DialogTitle>
                    <DialogDescription>
                        {isViewOnly ? t('card.viewCardDescription') : (card ? t('card.editCardDescription') : t('card.newCardDescription'))}
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-3">
                    <div className="space-y-2">
                        <Label htmlFor="title">{t('card.title')} *</Label>
                        <Input
                            id="title"
                            value={formData.title}
                            onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                            required
                            readOnly={isViewOnly}
                            disabled={isViewOnly}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="description">{t('card.description')}</Label>
                        <Textarea
                            id="description"
                            value={formData.description}
                            onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                            rows={3}
                            readOnly={isViewOnly}
                            disabled={isViewOnly}
                        />
                    </div>

                    {/* Checklist Section */}
                    <div className="space-y-2">
                        <Label>{t('card.checklist')}</Label>
                        <div className="space-y-2">
                            <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                                <SortableContext items={checklist.map(i => i.id ?? `new-${i.position}`)} strategy={verticalListSortingStrategy}>
                                    {checklist.map((item, index) => (
                                        <SortableItem key={item.id ?? `new-${item.position}`} id={item.id ?? `new-${item.position}`}>
                                            {({ attributes, listeners }: any) => (
                                                <div className="flex items-center gap-2">
                                                    <div
                                                        className="h-6 w-6 flex items-center justify-center text-muted-foreground cursor-grab active:cursor-grabbing"
                                                        title={t('card.move')}
                                                        {...attributes}
                                                        {...listeners}
                                                        style={{ display: isViewOnly ? 'none' : 'flex' }}
                                                    >
                                                        <GripVertical className="h-4 w-4" />
                                                    </div>
                                                    <input
                                                        type="checkbox"
                                                        className="h-4 w-4"
                                                        checked={item.is_done}
                                                        onChange={() => toggleChecklistItem(index)}
                                                        title={t('card.toggleChecklistItem')}
                                                        disabled={isViewOnly && !canToggleChecklistItems}
                                                    />
                                                    <Input
                                                        value={item.text}
                                                        onChange={(e) => updateChecklistItemText(index, e.target.value)}
                                                        className={item.is_done ? 'line-through text-muted-foreground' : ''}
                                                        maxLength={64}
                                                        readOnly={isViewOnly}
                                                        disabled={isViewOnly}
                                                    />
                                                    <Button
                                                        type="button"
                                                        variant="ghost"
                                                        size="icon"
                                                        onClick={() => deleteChecklistItem(index)}
                                                        title={t('card.dropItem')}
                                                        style={{ display: isViewOnly ? 'none' : 'flex' }}
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            )}
                                        </SortableItem>
                                    ))}
                                </SortableContext>
                            </DndContext>
                            {!isViewOnly && (
                                <div className="flex items-center gap-2">
                                    <Input
                                        placeholder={t('card.addChecklistItem')}
                                        value={newItemText}
                                        onChange={(e) => setNewItemText(e.target.value)}
                                        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addChecklistItem(); } }}
                                        maxLength={64}
                                    />
                                    <Button type="button" variant="secondary" onClick={addChecklistItem}>{t('card.add')}</Button>
                                </div>
                            )}
                        </div>
                    </div>


                    <div className="space-y-2">
                        <Label>{t('card.labels')}</Label>
                        <div className="flex flex-wrap gap-2">
                            {labels.map(label => (
                                <Badge
                                    key={label.id}
                                    variant={formData.label_ids.includes(label.id) ? "default" : "outline"}
                                    className={isViewOnly ? "cursor-default" : "cursor-pointer"}
                                    style={{
                                        backgroundColor: formData.label_ids.includes(label.id) ? label.color : 'transparent',
                                        borderColor: label.color
                                    }}
                                    onClick={isViewOnly ? undefined : () => handleLabelToggle(label.id)}
                                >
                                    {label.name}
                                    {formData.label_ids.includes(label.id) && !isViewOnly && (
                                        <X className="h-3 w-3 ml-1" />
                                    )}
                                </Badge>
                            ))}
                        </div>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                        <div className="space-y-2">
                            <Label htmlFor="priority">{t('card.priority')}</Label>
                            <Select
                                value={formData.priority}
                                onValueChange={(value) => setFormData(prev => ({ ...prev, priority: value }))}
                                disabled={isViewOnly}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="high">
                                        <div className="flex items-center gap-2">
                                            <ArrowUp className="h-4 w-4 text-destructive" />
                                            <span>{t('priority.high')}</span>
                                        </div>
                                    </SelectItem>
                                    <SelectItem value="medium">
                                        <div className="flex items-center gap-2">
                                            <Minus className="h-4 w-4 text-sky-600" />
                                            <span>{t('priority.medium')}</span>
                                        </div>
                                    </SelectItem>
                                    <SelectItem value="low">
                                        <div className="flex items-center gap-2">
                                            <ArrowDown className="h-4 w-4 text-muted-foreground" />
                                            <span>{t('priority.low')}</span>
                                        </div>
                                    </SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="due_date">{t('card.dueDate')}</Label>
                            <Input
                                id="due_date"
                                type="date"
                                value={formData.due_date}
                                onChange={(e) => setFormData(prev => ({ ...prev, due_date: e.target.value }))}
                                readOnly={isViewOnly}
                                disabled={isViewOnly}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="assignee">{t('card.assignee')}</Label>
                            <Select
                                value={formData.assignee_id?.toString() || 'none'}
                                onValueChange={(value) => setFormData(prev => ({
                                    ...prev,
                                    assignee_id: value === 'none' ? null : parseInt(value)
                                }))}
                                disabled={isViewOnly}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder={t('card.selectUser')} />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">{t('card.unassign')}</SelectItem>
                                    {users
                                        .slice()
                                        .sort((a, b) => (a.display_name || '').localeCompare(b.display_name || ''))
                                        .map(user => (
                                            <SelectItem key={user.id} value={user.id.toString()}>
                                                {user.display_name}
                                            </SelectItem>
                                        ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <DialogFooter className="flex justify-between items-center">
                        <div className="flex-1">
                            {card && onDelete && !isViewOnly && canDeleteCard && (
                                <Button
                                    type="button"
                                    variant="destructive"
                                    size="sm"
                                    onClick={handleDelete}
                                    disabled={loading}
                                >
                                    <Trash2 className="h-4 w-4" />
                                    {t('card.archiveCard')}
                                </Button>
                            )}
                        </div>
                        <div className="flex gap-2 ml-auto">
                            {isViewOnly ? (
                                <Button type="button" variant="outline" onClick={onClose}>
                                    {t('common.close')}
                                </Button>
                            ) : (
                                <>
                                    <Button type="button" variant="outline" onClick={onClose}>
                                        {t('common.cancel')}
                                    </Button>
                                    <Button type="submit" disabled={loading}>
                                        {loading ? t('common.saving') : (card ? t('common.update') : t('common.create'))}
                                    </Button>
                                </>
                            )}
                        </div>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
};

export default CardForm; 
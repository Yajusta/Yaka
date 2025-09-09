import { useState, useEffect, FormEvent } from 'react';
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragEndEvent,
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import {
    useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from '../ui/select';
import {
    Trash2,
    Edit,
    Plus,
    GripVertical,
    Save,
    X,
    AlertTriangle,
    AlertCircle
} from 'lucide-react';
import { listsApi } from '../../services/listsApi';
import { useToast } from '../../hooks/use-toast';
import {
    KanbanList,
    KanbanListCreate,
    KanbanListUpdate,
    UserRole
} from '../../types';
import { useAuth } from '../../hooks/useAuth';
import {
    validateListName,
    isListNameUnique,
    validateListDeletion,
    getErrorMessage
} from '../../utils/validation';
import { useTranslation } from 'react-i18next';
import { LoadingState } from '../ui/loading-state';
import ErrorBoundary from '../ui/error-boundary';
import ProgressBar from '../ui/progress-bar';

interface ListManagerProps {
    isOpen: boolean;
    onClose: () => void;
    onListsUpdated?: () => void;
}

interface FormData {
    name: string;
}

interface FormErrors {
    name?: string;
    general?: string;
}

interface SortableListItemProps {
    list: KanbanList;
    cardCount: number;
    onEdit: (list: KanbanList) => void;
    onDelete: (list: KanbanList) => void;
    isEditing: boolean;
    editingName: string;
    onEditingNameChange: (name: string) => void;
    onSaveEdit: () => void;
    onCancelEdit: () => void;
    editingErrors: FormErrors;
}

// Sortable list item component
const SortableListItem = ({
    list,
    cardCount,
    onEdit,
    onDelete,
    isEditing,
    editingName,
    onEditingNameChange,
    onSaveEdit,
    onCancelEdit,
    editingErrors
}: SortableListItemProps) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: list.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };
    const { t } = useTranslation();

    return (
        <Card
            ref={setNodeRef}
            {...attributes}
            {...listeners}
            style={style}
            className={`${isDragging ? 'shadow-lg cursor-grabbing' : 'cursor-grab'} p-4 hover:bg-gray-50/50 transition-colors`}
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3 flex-1">
                    <div className="p-1 opacity-60 cursor-grab active:cursor-grabbing">
                        <GripVertical className="h-4 w-4 text-gray-400" />
                    </div>

                    {isEditing ? (
                        <div className="flex items-center space-x-2 flex-1">
                            <div className="flex-1">
                                <Input
                                    value={editingName}
                                    onChange={(e) => onEditingNameChange(e.target.value)}
                                    placeholder={t('list.title')}
                                    maxLength={100}
                                    className={`${editingErrors.name ? 'border-red-500' : ''}`}
                                    autoFocus
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') {
                                            onSaveEdit();
                                        } else if (e.key === 'Escape') {
                                            onCancelEdit();
                                        }
                                    }}
                                    onPointerDown={(e) => e.stopPropagation()}
                                />
                                {editingErrors.name && (
                                    <div className="flex items-center space-x-1 text-red-600 text-xs mt-1">
                                        <AlertCircle className="h-3 w-3" />
                                        <span>{editingErrors.name}</span>
                                    </div>
                                )}
                            </div>
                            <Button
                                size="sm"
                                onClick={() => onSaveEdit()}
                                disabled={!editingName.trim() || !!editingErrors.name || isDragging}
                                onPointerDown={(e) => e.stopPropagation()}
                                className="cursor-pointer"
                            >
                                <Save className="h-4 w-4" />
                            </Button>
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => onCancelEdit()}
                                disabled={isDragging}
                                onPointerDown={(e) => e.stopPropagation()}
                                className="cursor-pointer"
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    ) : (
                        <div className="flex-1">
                            <div className="font-medium">{list.name}</div>
                            <div className="text-sm text-gray-500">
                                {t('list.card', { count: cardCount })}
                            </div>
                        </div>
                    )}
                </div>

                {!isEditing && (
                    <div className={`flex space-x-2 ${isDragging ? 'pointer-events-none' : ''}`}>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onEdit(list)}
                            disabled={isDragging}
                            onPointerDown={(e) => e.stopPropagation()}
                            className="cursor-pointer"
                        >
                            <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onDelete(list)}
                            disabled={isDragging}
                            onPointerDown={(e) => e.stopPropagation()}
                            className="text-red-500 hover:text-red-700 cursor-pointer"
                        >
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </div>
                )}
            </div>
        </Card>
    );
};

const ListManagerContent = ({ isOpen, onClose, onListsUpdated }: ListManagerProps) => {
    const { user } = useAuth();
    const { t } = useTranslation();
    const [lists, setLists] = useState<KanbanList[]>([]);
    const [listCardCounts, setListCardCounts] = useState<Record<number, number>>({});
    const [loading, setLoading] = useState<boolean>(false);
    const [editingList, setEditingList] = useState<KanbanList | null>(null);
    const [editingName, setEditingName] = useState<string>('');
    const [showForm, setShowForm] = useState<boolean>(false);
    const [showDeleteDialog, setShowDeleteDialog] = useState<boolean>(false);
    const [listToDelete, setListToDelete] = useState<KanbanList | null>(null);
    const [targetListId, setTargetListId] = useState<number | null>(null);
    const [cardCount, setCardCount] = useState<number>(0);
    const [isDeleting, setIsDeleting] = useState<boolean>(false);
    const [deletionProgress, setDeletionProgress] = useState<{ current: number; total: number; cardName: string }>({
        current: 0,
        total: 0,
        cardName: ''
    });
    const [formData, setFormData] = useState<FormData>({
        name: ''
    });
    const [formErrors, setFormErrors] = useState<FormErrors>({});
    const [editingErrors, setEditingErrors] = useState<FormErrors>({});
    const { toast } = useToast();

    // Check if user is admin
    const isAdmin = user?.role === UserRole.ADMIN;

    // Drag and drop sensors
    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    useEffect(() => {
        if (isOpen && isAdmin) {
            loadLists();
        }
    }, [isOpen, isAdmin]);

    const loadLists = async (): Promise<void> => {
        try {
            setLoading(true);
            const data = await listsApi.getLists(false); // Force refresh
            setLists(data);

            // Récupérer le nombre de cartes pour chaque liste
            const cardCounts: Record<number, number> = {};
            await Promise.all(
                data.map(async (list) => {
                    try {
                        const listWithCount = await listsApi.getListCardsCount(list.id);
                        cardCounts[list.id] = listWithCount.card_count;
                    } catch (error) {
                        console.error(`Erreur lors du comptage des cartes pour la liste ${list.id}:`, error);
                        cardCounts[list.id] = 0; // Valeur par défaut en cas d'erreur
                    }
                })
            );
            setListCardCounts(cardCounts);
        } catch (error) {
            console.error('Error loading lists:', error);
            const errorMessage = getErrorMessage(error);
            toast({
                title: t('list.loadError'),
                description: errorMessage,
                variant: "destructive"
            });
        } finally {
            setLoading(false);
        }
    };

    // Validation functions
    const validateCreateForm = (): boolean => {
        const errors: FormErrors = {};

        // Validate name
        const nameValidation = validateListName(formData.name);
        if (!nameValidation.isValid) {
            errors.name = nameValidation.error;
        } else {
            // Check uniqueness
            const uniqueValidation = isListNameUnique(formData.name, lists);
            if (!uniqueValidation.isValid) {
                errors.name = uniqueValidation.error;
            }
        }

        setFormErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const validateEditForm = (): boolean => {
        if (!editingList) {
            return false;
        }

        const errors: FormErrors = {};

        // Validate name
        const nameValidation = validateListName(editingName);
        if (!nameValidation.isValid) {
            errors.name = nameValidation.error;
        } else {
            // Check uniqueness (excluding current list)
            const uniqueValidation = isListNameUnique(editingName, lists, editingList.id);
            if (!uniqueValidation.isValid) {
                errors.name = uniqueValidation.error;
            }
        }

        setEditingErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const validateDeletion = (list: KanbanList, cardCount: number, targetId?: number): boolean => {
        const validation = validateListDeletion(list, lists, cardCount, targetId);

        if (!validation.isValid) {
            toast({
                title: t('list.validationFailed'),
                description: validation.error,
                variant: "destructive"
            });
            return false;
        }

        return true;
    };

    const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
        e.preventDefault();

        // Validate form
        if (!validateCreateForm()) {
            return;
        }

        try {
            const newOrder = Math.max(...lists.map(l => l.order), 0) + 1;
            const listData: KanbanListCreate = {
                name: formData.name.trim(),
                order: newOrder
            };

            await listsApi.createList(listData);

            toast({
                title: t('list.createSuccess', { listName: formData.name.trim() }),
                variant: "success"
            });

            setShowForm(false);
            setFormData({ name: '' });
            setFormErrors({});
            await loadLists();
            onListsUpdated?.();
        } catch (error) {
            console.error('Error creating list:', error);
            const errorMessage = getErrorMessage(error);
            toast({
                title: t('list.createError'),
                description: errorMessage,
                variant: "destructive"
            });
        }
    };

    const handleEdit = (list: KanbanList): void => {
        setEditingList(list);
        setEditingName(list.name);
    };

    const handleSaveEdit = async (): Promise<void> => {
        if (!editingList) {
            return;
        }

        // Validate form
        if (!validateEditForm()) {
            return;
        }

        try {
            const updateData: KanbanListUpdate = {
                name: editingName.trim()
            };

            await listsApi.updateList(editingList.id, updateData);

            toast({
                title: t('list.updateSuccess', { listName: editingName.trim() }),
                variant: "success"
            });

            setEditingList(null);
            setEditingName('');
            setEditingErrors({});
            await loadLists();
            onListsUpdated?.();
        } catch (error) {
            console.error('Error updating list:', error);
            const errorMessage = getErrorMessage(error);
            toast({
                title: t('list.updateError'),
                description: errorMessage,
                variant: "destructive"
            });
        }
    };

    const handleCancelEdit = (): void => {
        setEditingList(null);
        setEditingName('');
        setEditingErrors({});
    };

    const handleDelete = async (list: KanbanList): Promise<void> => {
        try {
            // Check if this is the last list (Requirement 4.1)
            if (lists.length <= 1) {
                toast({
                    title: t('list.validationFailed'),
                    description: t('list.cannotDeleteLastList'),
                    variant: "destructive"
                });
                return;
            }

            // Get card count for this list (requirement 4.3)
            const listWithCount = await listsApi.getListCardsCount(list.id);
            const cardCount = listWithCount.card_count;

            // Si la liste est vide, supprimer directement sans popup
            if (cardCount === 0) {
                const availableTargetLists = lists.filter(l => l.id !== list.id);
                const targetId = availableTargetLists[0]?.id || 0;
                await confirmDelete(list, targetId);
                return;
            }

            // Pour les listes avec cartes, afficher la popup de confirmation
            setCardCount(cardCount);
            setListToDelete(list);
            setTargetListId(null);
            setShowDeleteDialog(true);

        } catch (error) {
            console.error('Error checking list cards:', error);
            const errorMessage = getErrorMessage(error);
            toast({
                title: "Erreur de vérification",
                description: errorMessage,
                variant: "destructive"
            });
        }
    };

    const confirmDelete = async (list: KanbanList, targetId: number | null): Promise<void> => {
        // Final validation before deletion (skip for empty lists)
        if (cardCount > 0 && !validateDeletion(list, cardCount, targetId || undefined)) {
            return;
        }

        try {
            setIsDeleting(true);
            setDeletionProgress({ current: 0, total: cardCount, cardName: '' });

            if (cardCount > 0 && targetId) {
                // Use the new progress-enabled deletion method
                await listsApi.deleteListWithProgress(
                    list.id,
                    targetId,
                    (current, total, cardName) => {
                        setDeletionProgress({ current, total, cardName });
                    }
                );
            } else {
                // For empty lists, use the regular deletion method
                await listsApi.deleteList(list.id, targetId || 0);
            }

            // Success message with appropriate details
            let successMessage: string;
            if (cardCount > 0) {
                successMessage = t('list.deleteSuccessWithCards', { listName: list.name, count: cardCount });
            } else {
                successMessage = t('list.deleteSuccess', { listName: list.name });
            }

            toast({
                title: t('common.success'),
                description: successMessage,
                variant: "success"
            });

            // Reset dialog state
            setShowDeleteDialog(false);
            setListToDelete(null);
            setTargetListId(null);
            setCardCount(0);
            setIsDeleting(false);
            setDeletionProgress({ current: 0, total: 0, cardName: '' });

            // Refresh data
            await loadLists();
            onListsUpdated?.();
        } catch (error) {
            console.error('Error deleting list:', error);
            const errorMessage = getErrorMessage(error);
            toast({
                title: t('list.deleteError'),
                description: errorMessage,
                variant: "destructive"
            });

            // Reset deletion state on error
            setIsDeleting(false);
            setDeletionProgress({ current: 0, total: 0, cardName: '' });
        }
    };

    const handleDragEnd = async (event: DragEndEvent): Promise<void> => {
        const { active, over } = event;

        if (over && active.id !== over.id) {
            const oldIndex = lists.findIndex(list => list.id === active.id);
            const newIndex = lists.findIndex(list => list.id === over.id);

            const newLists = arrayMove(lists, oldIndex, newIndex);

            // Update local state immediately for better UX
            setLists(newLists);

            try {
                // Create order mapping
                const listOrders: Record<number, number> = {};
                newLists.forEach((list, index) => {
                    listOrders[list.id] = index + 1;
                });

                await listsApi.reorderLists(listOrders);

                toast({
                    title: t('list.reorderSuccess'),
                    variant: "success"
                });

                onListsUpdated?.();
            } catch (error) {
                console.error('Error reordering lists:', error);
                // Revert local state on error
                await loadLists();
                const errorMessage = getErrorMessage(error);
                toast({
                    title: t('list.reorderError'),
                    description: errorMessage,
                    variant: "destructive"
                });
            }
        }
    };

    const handleCreate = (): void => {
        setFormData({ name: '' });
        setShowForm(true);
    };

    const handleCloseForm = (): void => {
        setShowForm(false);
        setFormData({ name: '' });
        setFormErrors({});
    };

    // Handle form input changes with real-time validation
    const handleNameChange = (value: string): void => {
        setFormData({ ...formData, name: value });

        // Clear errors when user starts typing
        if (formErrors.name) {
            setFormErrors({ ...formErrors, name: undefined });
        }
    };

    const handleEditingNameChange = (value: string): void => {
        setEditingName(value);

        // Clear errors when user starts typing
        if (editingErrors.name) {
            setEditingErrors({ ...editingErrors, name: undefined });
        }
    };

    const availableTargetLists = lists.filter(l => l.id !== listToDelete?.id);

    // Don't render if user is not admin
    if (!isAdmin) {
        return null;
    }

    return (
        <>
            <Dialog open={isOpen} onOpenChange={onClose}>
                <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>{t('list.listManagement')}</DialogTitle>
                    </DialogHeader>

                    <div className="space-y-4">
                        {/* Bouton d'ajout */}
                        <div className="flex justify-end">
                            <Button onClick={handleCreate}>
                                <Plus className="h-4 w-4 mr-2" />
                                {t('list.newList')}
                            </Button>
                        </div>

                        {/* Formulaire de création */}
                        {showForm && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>{t('list.newList')}</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <form onSubmit={handleSubmit} className="space-y-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="name">{t('list.title')}</Label>
                                            <Input
                                                id="name"
                                                value={formData.name}
                                                onChange={(e) => handleNameChange(e.target.value)}
                                                placeholder={t('list.title')}
                                                maxLength={100}
                                                required
                                                autoFocus
                                                className={formErrors.name ? 'border-red-500' : ''}
                                            />
                                            {formErrors.name && (
                                                <div className="flex items-center space-x-1 text-red-600 text-sm">
                                                    <AlertCircle className="h-4 w-4" />
                                                    <span>{formErrors.name}</span>
                                                </div>
                                            )}
                                            <p className="text-xs text-gray-500">
                                                {formData.name.length}/100 {t('common.charactersMax')}
                                            </p>
                                        </div>

                                        <div className="flex justify-end space-x-2">
                                            <Button type="button" variant="outline" onClick={handleCloseForm}>
                                                {t('common.cancel')}
                                            </Button>
                                            <Button
                                                type="submit"
                                                disabled={!formData.name.trim() || !!formErrors.name}
                                            >
                                                {t('common.create')}
                                            </Button>
                                        </div>
                                    </form>
                                </CardContent>
                            </Card>
                        )}

                        {/* Liste des listes avec drag & drop */}
                        {loading ? (
                            <LoadingState message={t('list.loading')} size="lg" />
                        ) : (
                            <div className="space-y-2">
                                <div className="text-sm text-gray-600 mb-4">
                                    {t('list.dragAndDropHint')}
                                </div>

                                <DndContext
                                    sensors={sensors}
                                    collisionDetection={closestCenter}
                                    onDragEnd={handleDragEnd}
                                >
                                    <SortableContext
                                        items={lists.map(list => list.id)}
                                        strategy={verticalListSortingStrategy}
                                    >
                                        {lists.map((list) => (
                                            <SortableListItem
                                                key={list.id}
                                                list={list}
                                                cardCount={listCardCounts[list.id] || 0}
                                                onEdit={handleEdit}
                                                onDelete={handleDelete}
                                                isEditing={editingList?.id === list.id}
                                                editingName={editingName}
                                                onEditingNameChange={handleEditingNameChange}
                                                onSaveEdit={handleSaveEdit}
                                                onCancelEdit={handleCancelEdit}
                                                editingErrors={editingErrors}
                                            />
                                        ))}
                                    </SortableContext>
                                </DndContext>

                                {lists.length === 0 && !loading && (
                                    <div className="text-center py-8 text-gray-500">
                                        {t('list.noLists')}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </DialogContent>
            </Dialog>

            {/* Dialog de confirmation de suppression avec réassignation des cartes */}
            <Dialog open={showDeleteDialog} onOpenChange={(open) => {
                if (!isDeleting) {
                    setShowDeleteDialog(open);
                    if (!open) {
                        setTargetListId(null);
                        setDeletionProgress({ current: 0, total: 0, cardName: '' });
                    }
                }
            }}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center space-x-2">
                            <AlertTriangle className="h-5 w-5 text-orange-500" />
                            <span>{isDeleting ? t('list.deletingInProgress') : t('list.deleteList')}</span>
                        </DialogTitle>
                        <DialogDescription>
                            {isDeleting
                                ? t('list.deletingDescription')
                                : t('list.deleteWarning')
                            }
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4">
                        <div className="p-3 bg-gray-50 rounded-md">
                            <p className="font-medium">
                                {t('list.listToDelete', { listName: listToDelete?.name })}
                            </p>
                            {cardCount > 0 && (
                                <p className="text-sm text-orange-600 mt-1">
                                    ⚠️ {t('list.listContainsCards', { count: cardCount })}
                                </p>
                            )}
                        </div>

                        {/* Progress bar during deletion */}
                        {isDeleting && cardCount > 0 && (
                            <div className="space-y-3">
                                <div className="p-3 border border-blue-200 bg-blue-50 rounded-md">
                                    <p className="text-sm text-blue-800 font-medium mb-2">
                                        {t('list.movingCardsInProgress')}
                                    </p>
                                    <ProgressBar
                                        current={deletionProgress.current}
                                        total={deletionProgress.total}
                                        label={deletionProgress.cardName ? t('list.movingCard', { cardName: deletionProgress.cardName }) : t('list.preparing')}
                                        showPercentage={true}
                                    />
                                </div>
                            </div>
                        )}

                        {/* Configuration form (hidden during deletion) */}
                        {!isDeleting && (
                            <>
                                {cardCount > 0 ? (
                                    <div className="space-y-3">
                                        <div className="p-3 border border-orange-200 bg-orange-50 rounded-md">
                                            <p className="text-sm text-orange-800 font-medium">
                                                {t('list.reassignmentRequired')}
                                            </p>
                                            <p className="text-xs text-orange-700 mt-1">
                                                {t('list.cardsWillBeMoved', { count: cardCount })}
                                            </p>
                                        </div>

                                        <div className="space-y-2">
                                            <Label htmlFor="target-list-select">
                                                {t('list.destinationList')} <span className="text-red-500">*</span>
                                            </Label>
                                            <Select
                                                value={targetListId?.toString() || ''}
                                                onValueChange={(value) => setTargetListId(Number(value))}
                                            >
                                                <SelectTrigger className="w-full">
                                                    <SelectValue placeholder={t('list.selectDestinationList')} />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {availableTargetLists.map(list => (
                                                        <SelectItem key={list.id} value={list.id.toString()}>
                                                            {list.name} ({t('list.card', { count: listCardCounts[list.id] || 0 })})
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            {cardCount > 0 && !targetListId && (
                                                <p className="text-xs text-red-600">
                                                    {t('list.mustSelectDestination')}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="p-3 border border-green-200 bg-green-50 rounded-md">
                                        <p className="text-sm text-green-800">
                                            ✓ {t('list.emptyListSafeToDelete')}
                                        </p>
                                    </div>
                                )}
                            </>
                        )}

                        {/* Action buttons (hidden during deletion) */}
                        {!isDeleting && (
                            <div className="flex justify-end space-x-2 pt-2">
                                <Button
                                    variant="outline"
                                    onClick={() => {
                                        setShowDeleteDialog(false);
                                        setTargetListId(null);
                                    }}
                                >
                                    {t('common.cancel')}
                                </Button>
                                <Button
                                    variant="destructive"
                                    onClick={() => {
                                        if (listToDelete) {
                                            const targetId = cardCount > 0
                                                ? targetListId
                                                : availableTargetLists[0]?.id;

                                            // Additional validation before confirming
                                            if (cardCount > 0 && !targetId) {
                                                toast({
                                                    title: t('list.validationFailed'),
                                                    description: t('list.mustSelectDestinationForCards'),
                                                    variant: "destructive"
                                                });
                                                return;
                                            }

                                            if (targetId || cardCount === 0) {
                                                confirmDelete(listToDelete, targetId || availableTargetLists[0]?.id);
                                            }
                                        }
                                    }}
                                    disabled={cardCount > 0 && !targetListId}
                                    className="min-w-[100px]"
                                >
                                    {cardCount > 0 ? t('list.moveCardsAndDelete') : t('common.delete')}
                                </Button>
                            </div>
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </>
    );
};

// Wrap with ErrorBoundary for better error handling
const ListManager = (props: ListManagerProps) => {
    const { t } = useTranslation();
    return (
        <ErrorBoundary
            fallback={
                <Dialog open={props.isOpen} onOpenChange={props.onClose}>
                    <DialogContent className="max-w-md">
                        <DialogHeader>
                            <DialogTitle className="flex items-center space-x-2">
                                <AlertTriangle className="h-5 w-5 text-red-500" />
                                <span>{t('common.error')}</span>
                            </DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                            <p className="text-sm text-gray-600">
                                {t('list.loadingError')}
                            </p>
                            <div className="flex justify-end">
                                <Button onClick={props.onClose}>
                                    {t('common.close')}
                                </Button>
                            </div>
                        </div>
                    </DialogContent>
                </Dialog>
            }
        >
            <ListManagerContent {...props} />
        </ErrorBoundary>
    );
};

export default ListManager;
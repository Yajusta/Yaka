import { useState, useEffect, useCallback, FormEvent } from 'react';
import { DndContext, closestCenter, DragEndEvent } from '@dnd-kit/core';
import { SortableContext, useSortable, arrayMove, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Button } from '../ui/button.tsx';
import { Input } from '../ui/input.tsx';
import { Label } from '../ui/label.tsx';
import { Textarea } from '../ui/textarea.tsx';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select.tsx';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog.tsx';
import { Badge } from '../ui/badge.tsx';
import { X, ArrowUp, ArrowDown, Minus, Trash2, GripVertical } from 'lucide-react';
import { CardPriority } from '../../types/index.ts';
import { mapPriorityToBackend, mapPriorityFromBackend } from '../../lib/priority';
import { cardService, labelService, cardItemsService } from '../../services/api.tsx';
import { useToast } from '../../hooks/use-toast.tsx';
import { Card, Label as LabelType } from '../../types/index.ts';
import { useUsers } from '../../hooks/useUsers';

interface CardFormProps {
    card: Card | null;
    isOpen: boolean;
    onClose: () => void;
    onSave: (card: Card) => void;
    onDelete?: (cardId: number) => void;
    defaultListId?: number; // ID de la liste par défaut pour les nouvelles cartes
}

interface FormData {
    titre: string;
    description: string;
    date_echeance: string;
    priorite: string;
    assignee_id: number | null;
    label_ids: number[];
    list_id: number;
}

const CardForm = ({ card, isOpen, onClose, onSave, onDelete, defaultListId }: CardFormProps) => {
    const [formData, setFormData] = useState<FormData>({
        titre: '',
        description: '',
        date_echeance: '',
        // use internal english keys by default
        priorite: 'medium',
        assignee_id: null,
        label_ids: [],
        list_id: defaultListId ?? -1 // Utiliser -1 par défaut pour laisser le backend choisir la plus basse
    });
    const { toast } = useToast();
    const { users } = useUsers();
    const [labels, setLabels] = useState<LabelType[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [checklist, setChecklist] = useState<{ id?: number; texte: string; is_done: boolean; position: number }[]>([]);
    const [newItemText, setNewItemText] = useState<string>('');

    const loadData = useCallback(async (): Promise<void> => {
        try {
            const labelsData = await labelService.getLabels();
            setLabels(labelsData);
        } catch {
            toast({
                title: "Erreur",
                description: "Impossible de charger les données",
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
                        titre: card.titre || '',
                        description: card.description || '',
                        date_echeance: card.date_echeance || '',
                        priorite: mapPriorityFromBackend(card.priorite || ''),
                        assignee_id: card.assignee_id ?? null,
                        label_ids: card.labels?.map(l => l.id) || [],
                        list_id: card.list_id
                    });
                    // Load existing items for edit
                    try {
                        const items = await cardItemsService.getItems(card.id);
                        setChecklist(items.map(i => ({ id: i.id, texte: i.texte, is_done: i.is_done, position: i.position })));
                    } catch { /* ignore */ }
                } else {
                    setFormData({
                        titre: '',
                        description: '',
                        date_echeance: '',
                        priorite: CardPriority.MEDIUM,
                        assignee_id: null,
                        label_ids: [],
                        list_id: defaultListId ?? -1 // Utiliser -1 par défaut
                    });
                    setChecklist([]);
                }
            };
            run();
        }
    }, [isOpen, card, loadData]);

    const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
        e.preventDefault();
        setLoading(true);

        try {
            // Sanitize payload to match backend schema types (priority mapping delegated to shared util)

            const basePayload = {
                titre: formData.titre,
                description: formData.description?.trim() === '' ? null : formData.description,
                date_echeance: formData.date_echeance && formData.date_echeance !== '' ? formData.date_echeance : null,
                priorite: mapPriorityToBackend(formData.priorite),
                assignee_id: typeof formData.assignee_id === 'number' ? formData.assignee_id : null,
                list_id: formData.list_id
            };

            // Build payloads to match the updated CreateCardData / UpdateCardData types.
            const labelIds = Array.isArray(formData.label_ids) ? formData.label_ids.map(Number) : [];
            const createPayload = {
                ...basePayload,
                // include label_ids only if present
                ...(labelIds.length > 0 ? { label_ids: labelIds } : {})
            };

            const updatePayload = {
                ...basePayload,
                // for updates the route contains the id; body shouldn't include it
                ...(labelIds.length > 0 ? { label_ids: labelIds } : {})
            };

            let savedCard: Card;
            if (card) {
                savedCard = await cardService.updateCard(card.id, updatePayload);
            } else {
                savedCard = await cardService.createCard(createPayload);
            }
            // Sync checklist changes: create/update/delete as needed
            try {
                // For simplicity, we will upsert items sequentially
                for (let idx = 0; idx < checklist.length; idx++) {
                    const item = checklist[idx];
                    if (!item.texte || item.texte.trim() === '') continue;
                    if (item.id) {
                        await cardItemsService.updateItem(item.id, { texte: item.texte, is_done: item.is_done, position: idx + 1 });
                    } else {
                        await cardItemsService.createItem(savedCard.id, item.texte, idx + 1, item.is_done);
                    }
                }
                // Fetch latest to include IDs
                const latest = await cardItemsService.getItems(savedCard.id);
                savedCard.items = latest as any;
            } catch { /* ignore checklist errors to not block card save */ }
            onSave(savedCard);
            onClose();
            toast({
                title: card ? "Carte mise à jour" : "Carte créée",
                variant: "success"
            });
        } catch (error: any) {
            toast({
                title: error.response?.data?.detail || "Erreur lors de la sauvegarde",
                variant: "destructive"
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
        if (!text) return;
        setChecklist(prev => [...prev, { texte: text, is_done: false, position: prev.length + 1 }]);
        setNewItemText('');
    };

    const toggleChecklistItem = (index: number): void => {
        setChecklist(prev => prev.map((it, i) => i === index ? { ...it, is_done: !it.is_done } : it));
    };

    const updateChecklistItemText = (index: number, texte: string): void => {
        const limited = texte.slice(0, 64);
        setChecklist(prev => prev.map((it, i) => i === index ? { ...it, texte: limited } : it));
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
        if (!over || active.id === over.id) return;
        const oldIndex = checklist.findIndex(i => (i.id ?? `new-${i.position}`) === active.id);
        const newIndex = checklist.findIndex(i => (i.id ?? `new-${i.position}`) === over.id);
        if (oldIndex === -1 || newIndex === -1) return;
        const newItems = arrayMove(checklist, oldIndex, newIndex).map((it, idx) => ({ ...it, position: idx + 1 }));
        setChecklist(newItems);
    };

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
                {/* Inject drag handle via function-as-child pattern */}
                {typeof children === 'function' ? (children as DragRender)({ attributes, listeners }) : children}
            </div>
        );
    };

    const handleDelete = async (): Promise<void> => {
        if (!card || !onDelete) return;

        try {
            onDelete(card.id);
            onClose();
        } catch (error: any) {
            toast({
                title: "Erreur lors de la suppression",
                description: error.response?.data?.detail || "Impossible de supprimer la carte",
                variant: "destructive"
            });
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>
                        {card ? 'Modifier la carte' : 'Nouvelle carte'}
                    </DialogTitle>
                    <DialogDescription>
                        {card ? 'Modifier les informations de la carte.' : 'Remplissez les détails pour créer une nouvelle carte.'}
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-3">
                    <div className="space-y-2">
                        <Label htmlFor="titre">Titre *</Label>
                        <Input
                            id="titre"
                            value={formData.titre}
                            onChange={(e) => setFormData(prev => ({ ...prev, titre: e.target.value }))}
                            required
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="description">Description</Label>
                        <Textarea
                            id="description"
                            value={formData.description}
                            onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                            rows={3}
                        />
                    </div>

                    {/* Checklist Section */}
                    <div className="space-y-2">
                        <Label>Checklist</Label>
                        <div className="space-y-2">
                            <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                                <SortableContext items={checklist.map(i => i.id ?? `new-${i.position}`)} strategy={verticalListSortingStrategy}>
                                    {checklist.map((item, index) => (
                                        <SortableItem key={item.id ?? `new-${item.position}`} id={item.id ?? `new-${item.position}`}>
                                            {({ attributes, listeners }: any) => (
                                                <div className="flex items-center gap-2">
                                                    <div
                                                        className="h-6 w-6 flex items-center justify-center text-muted-foreground cursor-grab active:cursor-grabbing"
                                                        title="Déplacer"
                                                        {...attributes}
                                                        {...listeners}
                                                    >
                                                        <GripVertical className="h-4 w-4" />
                                                    </div>
                                                    <input
                                                        type="checkbox"
                                                        className="h-4 w-4"
                                                        checked={item.is_done}
                                                        onChange={() => toggleChecklistItem(index)}
                                                    />
                                                    <Input
                                                        value={item.texte}
                                                        onChange={(e) => updateChecklistItemText(index, e.target.value)}
                                                        className={item.is_done ? 'line-through text-muted-foreground' : ''}
                                                        maxLength={64}
                                                    />
                                                    <Button type="button" variant="ghost" size="icon" onClick={() => deleteChecklistItem(index)} title="Supprimer">
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            )}
                                        </SortableItem>
                                    ))}
                                </SortableContext>
                            </DndContext>
                            <div className="flex items-center gap-2">
                                <Input
                                    placeholder="Ajouter un élément"
                                    value={newItemText}
                                    onChange={(e) => setNewItemText(e.target.value)}
                                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addChecklistItem(); } }}
                                    maxLength={64}
                                />
                                <Button type="button" variant="secondary" onClick={addChecklistItem}>Ajouter</Button>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label>Libellés</Label>
                        <div className="flex flex-wrap gap-2">
                            {labels.map(label => (
                                <Badge
                                    key={label.id}
                                    variant={formData.label_ids.includes(label.id) ? "default" : "outline"}
                                    className="cursor-pointer"
                                    style={{
                                        backgroundColor: formData.label_ids.includes(label.id) ? label.couleur : 'transparent',
                                        borderColor: label.couleur
                                    }}
                                    onClick={() => handleLabelToggle(label.id)}
                                >
                                    {label.nom}
                                    {formData.label_ids.includes(label.id) && (
                                        <X className="h-3 w-3 ml-1" />
                                    )}
                                </Badge>
                            ))}
                        </div>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                        <div className="space-y-2">
                            <Label htmlFor="priorite">Priorité</Label>
                            <Select
                                value={formData.priorite}
                                onValueChange={(value) => setFormData(prev => ({ ...prev, priorite: value }))}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="high">
                                        <div className="flex items-center gap-2">
                                            <ArrowUp className="h-4 w-4 text-destructive" />
                                            <span>Élevée</span>
                                        </div>
                                    </SelectItem>
                                    <SelectItem value="medium">
                                        <div className="flex items-center gap-2">
                                            <Minus className="h-4 w-4 text-sky-600" />
                                            <span>Moyenne</span>
                                        </div>
                                    </SelectItem>
                                    <SelectItem value="low">
                                        <div className="flex items-center gap-2">
                                            <ArrowDown className="h-4 w-4 text-muted-foreground" />
                                            <span>Faible</span>
                                        </div>
                                    </SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="date_echeance">Date d'échéance</Label>
                            <Input
                                id="date_echeance"
                                type="date"
                                value={formData.date_echeance}
                                onChange={(e) => setFormData(prev => ({ ...prev, date_echeance: e.target.value }))}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="assignee">Assigné à</Label>
                            <Select
                                value={formData.assignee_id?.toString() || 'none'}
                                onValueChange={(value) => setFormData(prev => ({
                                    ...prev,
                                    assignee_id: value === 'none' ? null : parseInt(value)
                                }))}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Sélectionner un utilisateur" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">Aucun</SelectItem>
                                    {users.map(user => (
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
                            {card && onDelete && (
                                <Button
                                    type="button"
                                    variant="destructive"
                                    size="sm"
                                    onClick={handleDelete}
                                    className="flex items-center gap-2"
                                >
                                    <Trash2 className="h-4 w-4" />

                                </Button>
                            )}
                        </div>
                        <div className="flex gap-2 ml-auto">
                            <Button type="button" variant="outline" onClick={onClose}>
                                Annuler
                            </Button>
                            <Button type="submit" disabled={loading}>
                                {loading ? 'Sauvegarde...' : (card ? 'Modifier' : 'Créer')}
                            </Button>
                        </div>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
};

export default CardForm; 
import { useState, useEffect, FormEvent } from 'react';
import { Button } from '../ui/button.tsx';
import { Input } from '../ui/input.tsx';
import { Label } from '../ui/label.tsx';
import { Badge } from '../ui/badge.tsx';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card.tsx';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog.tsx';
import { Trash2, Edit, Plus } from 'lucide-react';
import { labelService } from '../../services/api.tsx';
import { useToast } from '../../hooks/use-toast.tsx';
import { Label as LabelType } from '../../types/index.ts';
import { useTranslation } from 'react-i18next';

interface LabelManagerProps {
    isOpen: boolean;
    onClose: () => void;
}

interface FormData {
    name: string;
    color: string;
    description: string;
}

const LabelManager = ({ isOpen, onClose }: LabelManagerProps) => {
    const { t } = useTranslation();
    const [labels, setLabels] = useState<LabelType[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [editingLabel, setEditingLabel] = useState<LabelType | null>(null);
    const [showForm, setShowForm] = useState<boolean>(false);
    const [formData, setFormData] = useState<FormData>({
        name: '',
        color: '#3B82F6',
        description: ''
    });
    const { toast } = useToast();

    useEffect(() => {
        if (isOpen) {
            loadLabels();
        }
    }, [isOpen]);

    const loadLabels = async (): Promise<void> => {
        try {
            setLoading(true);
            const data = await labelService.getLabels();
            setLabels(data);
        } catch (error) {
            toast({
                title: t('common.error'),
                description: t('errors.loadingError'),
                variant: "destructive"
            });
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
        e.preventDefault();
        try {
            if (editingLabel) {
                await labelService.updateLabel(editingLabel.id, { ...formData, id: editingLabel.id });
                toast({
                    title: t('label.labelUpdated'),
                    variant: "success"
                });
            } else {
                await labelService.createLabel(formData);
                toast({
                    title: t('label.labelCreated'),
                    variant: "success"
                });
            }
            setShowForm(false);
            setEditingLabel(null);
            setFormData({ name: '', color: '#3B82F6', description: '' });
            loadLabels();
        } catch (error: any) {
            toast({
                title: t('common.error'),
                description: t('errors.saveError'),
                variant: "destructive"
            });
        }
    };

    const handleEdit = (label: LabelType): void => {
        setEditingLabel(label);
        setFormData({
            name: label.name,
            color: label.color,
            description: label.description || ''
        });
        setShowForm(true);
    };

    const handleDelete = async (labelId: number): Promise<void> => {
        if (!confirm(t('common.confirmDelete'))) {
            return;
        }

        try {
            await labelService.deleteLabel(labelId);
            toast({
                title: t('label.labelDeleted'),
                variant: "success"
            });
            loadLabels();
        } catch (error: any) {
            toast({
                title: t('common.error'),
                description: t('errors.deleteError'),
                variant: "destructive"
            });
        }
    };

    const handleCreate = (): void => {
        setEditingLabel(null);
        setFormData({ name: '', color: '#3B82F6', description: '' });
        setShowForm(true);
    };

    const handleCloseForm = (): void => {
        setShowForm(false);
        setEditingLabel(null);
        setFormData({ name: '', color: '#3B82F6', description: '' });
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{t('label.labelManagement')}</DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    {/* Bouton d'ajout */}
                    <div className="flex justify-end">
                        <Button onClick={handleCreate}>
                            <Plus className="h-4 w-4 mr-2" />
                            {t('label.newLabel')}
                        </Button>
                    </div>

                    {/* Formulaire */}
                    {showForm && (
                        <Card>
                            <CardHeader>
                                <CardTitle>
                                    {editingLabel ? t('label.editLabel') : t('label.newLabel')}
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <form onSubmit={handleSubmit} className="space-y-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="name">{t('label.name')}</Label>
                                        <Input
                                            id="name"
                                            value={formData.name}
                                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                            placeholder={t('label.name')}
                                            maxLength={32}
                                            required
                                        />
                                        <p className="text-xs text-gray-500">
                                            {formData.name.length}/32 {t('common.charactersMax')}
                                        </p>
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="color">{t('label.color')}</Label>
                                        <div className="flex items-center space-x-2">
                                            <Input
                                                id="color"
                                                type="color"
                                                value={formData.color}
                                                onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                                                className="w-16 h-10 p-1"
                                            />
                                            <Input
                                                value={formData.color}
                                                onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                                                placeholder="#3B82F6"
                                                className="flex-1"
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <div className="text-sm text-blue-600 mb-2 p-3 bg-blue-50 rounded-md border border-blue-200">
                                            ℹ️ {t('label.descriptionHint')}
                                        </div>
                                        <Label htmlFor="description">{t('label.description')}</Label>
                                        <textarea
                                            id="description"
                                            value={formData.description}
                                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                            placeholder={t('label.description')}
                                            maxLength={255}
                                            rows={3}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                                        />
                                        <p className="text-xs text-gray-500">
                                            {formData.description.length}/255 {t('common.charactersMax')}
                                        </p>
                                    </div>

                                    <div className="flex justify-end space-x-2">
                                        <Button type="button" variant="outline" onClick={handleCloseForm}>
                                            {t('common.cancel')}
                                        </Button>
                                        <Button type="submit">
                                            {editingLabel ? t('common.update') : t('common.create')}
                                        </Button>
                                    </div>
                                </form>
                            </CardContent>
                        </Card>
                    )}

                    {/* Liste des libellés */}
                    {loading ? (
                        <div className="flex justify-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {labels.map((label) => (
                                <Card key={label.id}>
                                    <CardContent>
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-3">
                                                <div
                                                    className="w-4 h-4 rounded-full"
                                                    style={{ backgroundColor: label.color }}
                                                />
                                                <Badge
                                                    key={label.id}
                                                    variant="outline"
                                                    className="text-xs px-2 py-0.5 font-medium border-opacity-50"
                                                    style={{
                                                        backgroundColor: label.color + '15',
                                                        borderColor: label.color + '40',
                                                        color: label.color
                                                    }}
                                                >
                                                    {label.name}
                                                </Badge>
                                            </div>

                                            <div className="flex space-x-2">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleEdit(label)}
                                                >
                                                    <Edit className="h-4 w-4" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleDelete(label.id)}
                                                    className="text-red-500 hover:text-red-700"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}

                            {labels.length === 0 && !loading && (
                                <div className="text-center py-8 text-gray-500">
                                    {t('label.noLabels')}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
};

export default LabelManager; 
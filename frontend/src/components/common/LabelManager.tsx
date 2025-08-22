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

interface LabelManagerProps {
    isOpen: boolean;
    onClose: () => void;
}

interface FormData {
    nom: string;
    couleur: string;
}

const LabelManager = ({ isOpen, onClose }: LabelManagerProps) => {
    const [labels, setLabels] = useState<LabelType[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [editingLabel, setEditingLabel] = useState<LabelType | null>(null);
    const [showForm, setShowForm] = useState<boolean>(false);
    const [formData, setFormData] = useState<FormData>({
        nom: '',
        couleur: '#3B82F6'
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
                title: "Erreur",
                description: "Impossible de charger les libellés",
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
                    title: "Libellé modifié avec succès",
                    variant: "success"
                });
            } else {
                await labelService.createLabel(formData);
                toast({
                    title: "Libellé créé avec succès",
                    variant: "success"
                });
            }
            setShowForm(false);
            setEditingLabel(null);
            setFormData({ nom: '', couleur: '#3B82F6' });
            loadLabels();
        } catch (error: any) {
            toast({
                title: "Erreur",
                description: "Impossible de sauvegarder le libellé",
                variant: "destructive"
            });
        }
    };

    const handleEdit = (label: LabelType): void => {
        setEditingLabel(label);
        setFormData({
            nom: label.nom,
            couleur: label.couleur
        });
        setShowForm(true);
    };

    const handleDelete = async (labelId: number): Promise<void> => {
        if (!confirm('Êtes-vous sûr de vouloir supprimer ce libellé ?')) {
            return;
        }

        try {
            await labelService.deleteLabel(labelId);
            toast({
                title: "Libellé supprimé avec succès",
                variant: "success"
            });
            loadLabels();
        } catch (error: any) {
            toast({
                title: "Erreur",
                description: "Impossible de supprimer le libellé",
                variant: "destructive"
            });
        }
    };

    const handleCreate = (): void => {
        setEditingLabel(null);
        setFormData({ nom: '', couleur: '#3B82F6' });
        setShowForm(true);
    };

    const handleCloseForm = (): void => {
        setShowForm(false);
        setEditingLabel(null);
        setFormData({ nom: '', couleur: '#3B82F6' });
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Gestion des libellés</DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    {/* Bouton d'ajout */}
                    <div className="flex justify-end">
                        <Button onClick={handleCreate}>
                            <Plus className="h-4 w-4 mr-2" />
                            Nouveau libellé
                        </Button>
                    </div>

                    {/* Formulaire */}
                    {showForm && (
                        <Card>
                            <CardHeader>
                                <CardTitle>
                                    {editingLabel ? 'Modifier le libellé' : 'Nouveau libellé'}
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <form onSubmit={handleSubmit} className="space-y-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="nom">Nom</Label>
                                        <Input
                                            id="nom"
                                            value={formData.nom}
                                            onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                                            placeholder="Nom du libellé"
                                            maxLength={32}
                                            required
                                        />
                                        <p className="text-xs text-gray-500">
                                            {formData.nom.length}/32 caractères maximum
                                        </p>
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="couleur">Couleur</Label>
                                        <div className="flex items-center space-x-2">
                                            <Input
                                                id="couleur"
                                                type="color"
                                                value={formData.couleur}
                                                onChange={(e) => setFormData({ ...formData, couleur: e.target.value })}
                                                className="w-16 h-10 p-1"
                                            />
                                            <Input
                                                value={formData.couleur}
                                                onChange={(e) => setFormData({ ...formData, couleur: e.target.value })}
                                                placeholder="#3B82F6"
                                                className="flex-1"
                                            />
                                        </div>
                                    </div>

                                    <div className="flex justify-end space-x-2">
                                        <Button type="button" variant="outline" onClick={handleCloseForm}>
                                            Annuler
                                        </Button>
                                        <Button type="submit">
                                            {editingLabel ? 'Modifier' : 'Créer'}
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
                                                    style={{ backgroundColor: label.couleur }}
                                                />
                                                <Badge
                                                    key={label.id}
                                                    variant="outline"
                                                    className="text-xs px-2 py-0.5 font-medium border-opacity-50"
                                                    style={{
                                                        backgroundColor: label.couleur + '15',
                                                        borderColor: label.couleur + '40',
                                                        color: label.couleur
                                                    }}
                                                >
                                                    {label.nom}
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
                                    Aucun libellé créé pour le moment
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
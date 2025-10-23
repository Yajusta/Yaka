import { useState, useEffect, FormEvent } from 'react';
import { Button } from '../ui/button.tsx';
import { Input } from '../ui/input.tsx';
import { Label } from '../ui/label.tsx';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card.tsx';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog.tsx';
import { Trash2, Edit, Plus } from 'lucide-react';
import { globalDictionaryService } from '@shared/services/api.tsx';
import { useToast } from '@shared/hooks/use-toast.tsx';
import { GlobalDictionaryEntry } from '@shared/types/index.ts';
import { useTranslation } from 'react-i18next';

interface GlobalDictionaryManagerProps {
    isOpen: boolean;
    onClose: () => void;
}

interface FormData {
    term: string;
    definition: string;
}

const GlobalDictionaryManager = ({ isOpen, onClose }: GlobalDictionaryManagerProps) => {
    const { t } = useTranslation();
    const [entries, setEntries] = useState<GlobalDictionaryEntry[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [editingEntry, setEditingEntry] = useState<GlobalDictionaryEntry | null>(null);
    const [showForm, setShowForm] = useState<boolean>(false);
    const [formData, setFormData] = useState<FormData>({
        term: '',
        definition: ''
    });
    const { toast } = useToast();

    useEffect(() => {
        if (isOpen) {
            loadEntries();
        }
    }, [isOpen]);

    const loadEntries = async (): Promise<void> => {
        try {
            setLoading(true);
            const data = await globalDictionaryService.getEntries();
            setEntries(data);
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
            if (editingEntry) {
                await globalDictionaryService.updateEntry(editingEntry.id, formData);
                toast({
                    title: t('dictionary.entryUpdated'),
                    variant: "success"
                });
            } else {
                await globalDictionaryService.createEntry(formData);
                toast({
                    title: t('dictionary.entryCreated'),
                    variant: "success"
                });
            }
            setShowForm(false);
            setEditingEntry(null);
            setFormData({ term: '', definition: '' });
            loadEntries();
        } catch (error: any) {
            toast({
                title: t('common.error'),
                description: t('errors.saveError'),
                variant: "destructive"
            });
        }
    };

    const handleEdit = (entry: GlobalDictionaryEntry): void => {
        setEditingEntry(entry);
        setFormData({
            term: entry.term,
            definition: entry.definition
        });
        setShowForm(true);
    };

    const handleDelete = async (entryId: number): Promise<void> => {
        if (!confirm(t('dictionary.confirmDeleteEntry'))) {
            return;
        }

        try {
            await globalDictionaryService.deleteEntry(entryId);
            toast({
                title: t('dictionary.entryDeleted'),
                variant: "success"
            });
            loadEntries();
        } catch (error: any) {
            toast({
                title: t('common.error'),
                description: t('errors.deleteError'),
                variant: "destructive"
            });
        }
    };

    const handleCreate = (): void => {
        setEditingEntry(null);
        setFormData({ term: '', definition: '' });
        setShowForm(true);
    };

    const handleCloseForm = (): void => {
        setShowForm(false);
        setEditingEntry(null);
        setFormData({ term: '', definition: '' });
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
                <DialogHeader>
                    <DialogTitle>{t('dictionary.globalDictionary')}</DialogTitle>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto space-y-4">
                    {/* Info hint */}
                    <div className="text-sm text-blue-600 p-3 bg-blue-50 rounded-md border border-blue-200">
                        ℹ️ {t('dictionary.globalHint')}
                    </div>

                    {/* Bouton d'ajout */}
                    <div className="flex justify-end">
                        <Button onClick={handleCreate}>
                            <Plus className="h-4 w-4 mr-2" />
                            {t('dictionary.newEntry')}
                        </Button>
                    </div>

                    {/* Formulaire */}
                    {showForm && (
                        <Card>
                            <CardHeader>
                                <CardTitle>
                                    {editingEntry ? t('dictionary.editEntry') : t('dictionary.newEntry')}
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <form onSubmit={handleSubmit} className="space-y-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="term">{t('dictionary.term')}</Label>
                                        <Input
                                            id="term"
                                            value={formData.term}
                                            onChange={(e) => setFormData({ ...formData, term: e.target.value })}
                                            placeholder={t('dictionary.term')}
                                            maxLength={32}
                                            required
                                        />
                                        <p className="text-xs text-gray-500">
                                            {formData.term.length}/32 {t('common.charactersMax')}
                                        </p>
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="definition">{t('dictionary.definition')}</Label>
                                        <textarea
                                            id="definition"
                                            value={formData.definition}
                                            onChange={(e) => setFormData({ ...formData, definition: e.target.value })}
                                            placeholder={t('dictionary.definition')}
                                            maxLength={250}
                                            rows={4}
                                            required
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                                        />
                                        <p className="text-xs text-gray-500">
                                            {formData.definition.length}/250 {t('common.charactersMax')}
                                        </p>
                                    </div>

                                    <div className="flex justify-end space-x-2">
                                        <Button type="button" variant="outline" onClick={handleCloseForm}>
                                            {t('common.cancel')}
                                        </Button>
                                        <Button type="submit">
                                            {editingEntry ? t('common.update') : t('common.create')}
                                        </Button>
                                    </div>
                                </form>
                            </CardContent>
                        </Card>
                    )}

                    {/* Liste des entrées */}
                    {loading ? (
                        <div className="flex justify-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {entries.map((entry) => (
                                <Card key={entry.id}>
                                    <CardContent>
                                        <div className="flex items-start justify-between">
                                            <div className="flex-1 space-y-1">
                                                <div className="font-semibold">{entry.term}</div>
                                                <div className="text-sm text-gray-600">{entry.definition}</div>
                                            </div>

                                            <div className="flex space-x-2 ml-4">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleEdit(entry)}
                                                >
                                                    <Edit className="h-4 w-4" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleDelete(entry.id)}
                                                    className="text-red-500 hover:text-red-700"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}

                            {entries.length === 0 && !loading && (
                                <div className="text-center py-8 text-gray-500">
                                    {t('dictionary.noEntries')}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
};

export default GlobalDictionaryManager;


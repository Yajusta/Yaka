import { useState, useEffect } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { useBoardSettings } from '../../hooks/useBoardSettingsContext';
import { Loader2, CheckCircle } from 'lucide-react';

interface InterfaceDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export const InterfaceDialog = ({ open, onOpenChange }: InterfaceDialogProps) => {
    const { boardTitle, updateBoardTitle, error: hookError } = useBoardSettings();
    const [newTitle, setNewTitle] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [saveSuccess, setSaveSuccess] = useState(false);

    useEffect(() => {
        if (open) {
            setNewTitle(boardTitle || '');
            setSaveSuccess(false);
        }
    }, [open, boardTitle]);

    const handleSave = async () => {
        if (!newTitle?.trim()) return;

        setIsSaving(true);
        setSaveSuccess(false);

        try {
            const titleToSave = newTitle?.trim() || 'Yaka (Yet Another Kanban App)';
            const success = await updateBoardTitle(titleToSave);

            if (success) {
                setSaveSuccess(true);
                // Fermer le dialogue après 1.5 secondes seulement si il n'y a pas d'erreur
                setTimeout(() => {
                    if (!hookError) {
                        onOpenChange(false);
                    }
                }, 1500);
            }
        } catch (error) {
            console.error('Error saving title:', error);
        } finally {
            setIsSaving(false);
        }
    };

    const handleCancel = () => {
        setNewTitle(boardTitle || '');
        setSaveSuccess(false);
        onOpenChange(false);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Paramètres d'interface</DialogTitle>
                    <DialogDescription>
                        Modifiez le titre affiché de votre tableau Kanban.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="title" className="text-right">
                            Titre
                        </Label>
                        <Input
                            id="title"
                            value={newTitle}
                            onChange={(e) => setNewTitle(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    e.preventDefault();
                                    handleSave();
                                }
                            }}
                            className="col-span-3"
                            placeholder="Entrez le titre du tableau"
                            disabled={isSaving}
                            maxLength={64}
                        />
                        <div className="col-span-3 col-start-2 text-xs text-muted-foreground">
                            {newTitle?.length || 0}/64 caractères
                        </div>
                    </div>

                    {hookError && (
                        <div className="text-sm text-destructive text-center bg-destructive/10 p-2 rounded-md">
                            Erreur: {hookError}
                        </div>
                    )}

                    {saveSuccess && (
                        <div className="flex items-center justify-center text-sm text-green-600">
                            <CheckCircle className="h-4 w-4 mr-2" />
                            Titre mis à jour avec succès !
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={handleCancel} disabled={isSaving}>
                        Annuler
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={isSaving || !newTitle?.trim() || newTitle === boardTitle}
                    >
                        {isSaving ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Enregistrement...
                            </>
                        ) : (
                            'Enregistrer'
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
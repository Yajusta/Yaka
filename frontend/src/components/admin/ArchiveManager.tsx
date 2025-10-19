import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, KanbanList } from '../../types/index';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { cardService } from '../../services/api';
import { useToast } from '../../hooks/use-toast';
import { ArchiveRestore, Calendar, User, RotateCcw } from 'lucide-react';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';

interface ArchiveManagerProps {
    isOpen: boolean;
    onClose: () => void;
    onCardRestored?: (card: Card) => void;
    availableLists: KanbanList[];
}

type ArchivedCard = Card;

export const ArchiveManager = ({
    isOpen,
    onClose,
    onCardRestored,
    availableLists
}: ArchiveManagerProps) => {
    const [archivedCards, setArchivedCards] = useState<ArchivedCard[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [restoringCardId, setRestoringCardId] = useState<number | null>(null);
    const { toast } = useToast();
    const { t } = useTranslation();

    // Load archived cards when dialog opens
    useEffect(() => {
        if (isOpen) {
            loadArchivedCards();
        }
    }, [isOpen]);

    const loadArchivedCards = async () => {
        try {
            setLoading(true);
            const cards = await cardService.getArchivedCards();
            setArchivedCards(cards);
        } catch (error) {
            console.error('Erreur lors du chargement des cartes archivées:', error);
            toast({
                title: t('common.error'),
                description: t('archive.loadError'),
                variant: "destructive"
            });
        } finally {
            setLoading(false);
        }
    };

    const handleRestoreCard = async (card: ArchivedCard) => {
        try {
            setRestoringCardId(card.id);

            // Find the original list or use the first available list
            const targetList = availableLists.find(list => list.id === card.list_id) || availableLists[0];

            if (!targetList) {
                toast({
                    title: t('common.error'),
                    description: t('archive.noListAvailable'),
                    variant: "destructive"
                });
                return;
            }

            // Restore the card to the target list
            const restoredCard = await cardService.unarchiveCard(card.id);

            // Update local state
            setArchivedCards(prev => prev.filter(c => c.id !== card.id));

            // Notify parent component
            onCardRestored?.(restoredCard);

            toast({
                title: t('archive.cardRestored'),
                description: t('archive.cardRestoredDescription', { 
                    cardTitle: card.title, 
                    listName: targetList.name 
                }),
                variant: "success"
            });
        } catch (error: any) {
            console.error('Erreur lors de la restauration:', error);
            toast({
                title: t('archive.restoreError'),
                description: error.response?.data?.detail || t('archive.restoreErrorDescription'),
                variant: "destructive"
            });
        } finally {
            setRestoringCardId(null);
        }
    };

    const formatDate = (dateString?: string): string => {
        if (!dateString) {
            return t('common.unknownDate');
        }
        try {
            return format(new Date(dateString), 'dd MMMM yyyy à HH:mm', { locale: fr });
        } catch {
            return t('common.unknownDate');
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[80vh]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <ArchiveRestore className="h-5 w-5" />
                        {t('archive.title')} ({archivedCards.length})
                    </DialogTitle>
                    <DialogDescription>
                        {t('archive.description')}
                    </DialogDescription>
                </DialogHeader>

                <ScrollArea className="max-h-[60vh] pr-4">
                    {loading ? (
                        <div className="flex items-center justify-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                            <span className="ml-2">{t('archive.loading')}</span>
                        </div>
                    ) : archivedCards.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                            <ArchiveRestore className="h-12 w-12 mx-auto mb-4 opacity-50" />
                            <p>{t('archive.noCards')}</p>
                            <p className="text-sm mt-1">{t('archive.noCardsDescription')}</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {archivedCards
                                .sort((a, b) => {
                                    // Sort by updated date (most recent first)
                                    const dateA = a.updated_at ? new Date(a.updated_at).getTime() : 0;
                                    const dateB = b.updated_at ? new Date(b.updated_at).getTime() : 0;
                                    return dateB - dateA;
                                })
                                .map((card) => (
                                    <div
                                        key={card.id}
                                        className="border rounded-lg p-4 bg-card hover:bg-accent/50 transition-colors"
                                    >
                                        <div className="flex items-start justify-between gap-4">
                                            <div className="flex-1 min-w-0">
                                                <h3 className="font-semibold text-sm leading-tight mb-2">
                                                    {card.title}
                                                </h3>

                                                {card.description && (
                                                    <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                                                        {card.description}
                                                    </p>
                                                )}

                                                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                                                    <div className="flex items-center gap-1">
                                                        <Calendar className="h-3 w-3" />
                                                        <span>{t('archive.archivedOn', { date: formatDate(card.updated_at) })}</span>
                                                    </div>

                                                    {card.assignee_id && (
                                                        <div className="flex items-center gap-1">
                                                            <User className="h-3 w-3" />
                                                            <span>{card.assignee_name || "-"}</span>
                                                        </div>
                                                    )}
                                                </div>

                                                {card.labels && card.labels.length > 0 && (
                                                    <div className="flex flex-wrap gap-1 mt-2">
                                                        {card.labels.slice(0, 3).map(label => (
                                                            <Badge
                                                                key={label.id}
                                                                variant="outline"
                                                                className="text-xs px-2 py-0.5"
                                                                style={{
                                                                    backgroundColor: label.color + '15',
                                                                    borderColor: label.color + '40',
                                                                    color: label.color
                                                                }}
                                                            >
                                                                {label.name}
                                                            </Badge>
                                                        ))}
                                                        {card.labels.length > 3 && (
                                                            <Badge variant="outline" className="text-xs px-2 py-0.5">
                                                                +{card.labels.length - 3}
                                                            </Badge>
                                                        )}
                                                    </div>
                                                )}
                                            </div>

                                            <Button
                                                onClick={() => handleRestoreCard(card)}
                                                disabled={restoringCardId === card.id}
                                                size="sm"
                                                className="flex items-center gap-2"
                                            >
                                                {restoringCardId === card.id ? (
                                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                                                ) : (
                                                    <RotateCcw className="h-4 w-4" />
                                                )}
                                                {t('archive.restore')}
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                        </div>
                    )}
                </ScrollArea>
            </DialogContent>
        </Dialog>
    );
};
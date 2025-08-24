import React, { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { CardHistoryEntry } from '../../types';
import api from '../../services/api';
import { format, parseISO } from 'date-fns';
import { fr } from 'date-fns/locale';
import { Clock } from 'lucide-react';

interface CardHistoryModalProps {
    isOpen: boolean;
    onClose: () => void;
    cardId: number;
    cardTitle: string;
}

export const CardHistoryModal: React.FC<CardHistoryModalProps> = ({
    isOpen,
    onClose,
    cardId,
    cardTitle
}) => {
    const [history, setHistory] = useState<CardHistoryEntry[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen && cardId) {
            fetchHistory();
        }
    }, [isOpen, cardId]);

    const fetchHistory = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await api.get(`/cards/${cardId}/history`);
            setHistory(response.data);
        } catch (err) {
            console.error('Error fetching card history:', err);
            setError('Erreur lors du chargement de l\'historique');
        } finally {
            setLoading(false);
        }
    };

    const formatAction = (action: string): string => {
        const actionLabels: Record<string, string> = {
            'create': 'Création',
            'update': 'Modification',
            'priority_change': 'Changement de priorité',
            'assignee_change': 'Changement d\'assigné',
            'move': 'Déplacement',
            'archive': 'Archivage',
            'unarchive': 'Restauration'
        };
        return actionLabels[action] || action;
    };

    const getActionColor = (action: string): string => {
        const colors: Record<string, string> = {
            'create': 'text-green-600',
            'update': 'text-blue-600',
            'priority_change': 'text-orange-600',
            'assignee_change': 'text-purple-600',
            'move': 'text-indigo-600',
            'archive': 'text-red-600',
            'unarchive': 'text-green-600'
        };
        return colors[action] || 'text-gray-600';
    };

    const formatDateWithTimezone = (dateString: string): string => {
        try {
            // Parser la date ISO depuis le backend
            const date = parseISO(dateString);
            // Convertir vers le timezone local en ajoutant le décalage
            const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
            // Formater avec le locale français
            return format(localDate, "d MMMM yyyy 'à' HH:mm", {
                locale: fr
            });
        } catch (error) {
            console.error('Error formatting date:', error);
            // Fallback en cas d'erreur
            return format(new Date(dateString), "d MMMM yyyy 'à' HH:mm", {
                locale: fr
            });
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Clock className="h-5 w-5" />
                        Historique de la carte "{cardTitle}"
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    {loading && (
                        <div className="text-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                            <p className="mt-2 text-muted-foreground">Chargement de l'historique...</p>
                        </div>
                    )}

                    {error && (
                        <div className="text-center py-8">
                            <p className="text-destructive">{error}</p>
                        </div>
                    )}

                    {!loading && !error && history.length === 0 && (
                        <div className="text-center py-8">
                            <p className="text-muted-foreground">Aucun historique disponible pour cette carte.</p>
                        </div>
                    )}

                    {!loading && !error && history.length > 0 && (
                        <div className="space-y-3">
                            {history.map((entry) => (
                                <div
                                    key={entry.id}
                                    className="flex items-start gap-3 p-3 rounded-lg border bg-card"
                                >
                                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                                        <Clock className="h-4 w-4 text-muted-foreground" />
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span
                                                className={`text-sm font-medium ${getActionColor(entry.action)}`}
                                            >
                                                {formatAction(entry.action)}
                                            </span>
                                            <span className="text-xs text-muted-foreground">
                                                {formatDateWithTimezone(entry.created_at)}
                                            </span>
                                        </div>

                                        <p className="text-sm text-foreground">
                                            {entry.description}
                                        </p>

                                        {entry.user && (
                                            <p className="text-xs text-muted-foreground mt-1">
                                                par {entry.user.display_name || entry.user.email}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
};
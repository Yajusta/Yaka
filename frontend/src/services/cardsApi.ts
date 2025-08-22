import { AxiosResponse } from 'axios';
import api from './api';
import { Card } from '../types';

// Error handling utility
class CardsApiError extends Error {
    constructor(
        message: string,
        public status?: number,
        public code?: string
    ) {
        super(message);
        this.name = 'CardsApiError';
    }
}

// Helper function to handle API errors
const handleApiError = (error: any): never => {
    // Handle network errors
    if (!error.response) {
        throw new CardsApiError(
            'Erreur de connexion. Vérifiez votre connexion internet et réessayez.',
            0,
            'NETWORK_ERROR'
        );
    }

    // Handle specific HTTP status codes with user-friendly messages
    const status = error.response.status;
    const detail = error.response.data?.detail;
    
    switch (status) {
        case 400:
            throw new CardsApiError(
                detail || 'Données invalides. Vérifiez les informations saisies.',
                status,
                'VALIDATION_ERROR'
            );
        case 401:
            throw new CardsApiError(
                'Vous n\'êtes pas autorisé à effectuer cette action. Veuillez vous reconnecter.',
                status,
                'UNAUTHORIZED'
            );
        case 403:
            throw new CardsApiError(
                'Vous n\'avez pas les permissions nécessaires pour effectuer cette action.',
                status,
                'FORBIDDEN'
            );
        case 404:
            throw new CardsApiError(
                detail || 'La ressource demandée n\'a pas été trouvée.',
                status,
                'NOT_FOUND'
            );
        case 409:
            throw new CardsApiError(
                detail || 'Conflit détecté. Cette action ne peut pas être effectuée en raison d\'un conflit avec l\'état actuel.',
                status,
                'CONFLICT'
            );
        case 422:
            throw new CardsApiError(
                detail || 'Données de validation incorrectes.',
                status,
                'UNPROCESSABLE_ENTITY'
            );
        case 500:
            throw new CardsApiError(
                'Erreur interne du serveur. Veuillez réessayer plus tard.',
                status,
                'INTERNAL_SERVER_ERROR'
            );
        case 503:
            throw new CardsApiError(
                'Service temporairement indisponible. Veuillez réessayer plus tard.',
                status,
                'SERVICE_UNAVAILABLE'
            );
        default:
            throw new CardsApiError(
                detail || 'Une erreur inattendue s\'est produite.',
                status,
                'UNKNOWN_ERROR'
            );
    }
};

// Cards API service
export const cardsApi = {
    /**
     * Récupérer toutes les cartes d'une liste spécifique
     */
    async getCardsByList(listId: number): Promise<Card[]> {
        try {
            const response: AxiosResponse<Card[]> = await api.get(`/cards/?list_id=${listId}&include_archived=false`);
            return response.data;
        } catch (error) {
            return handleApiError(error);
        }
    },

    /**
     * Déplacer une carte vers une autre liste
     */
    async moveCard(cardId: number, sourceListId: number, targetListId: number, position?: number): Promise<Card> {
        try {
            const moveRequest = {
                source_list_id: sourceListId,
                target_list_id: targetListId,
                position: position
            };
            const response: AxiosResponse<Card> = await api.patch(`/cards/${cardId}/move`, moveRequest);
            return response.data;
        } catch (error) {
            return handleApiError(error);
        }
    }
};

// Export error class for error handling in components
export { CardsApiError };

// Export default
export default cardsApi;
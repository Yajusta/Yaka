import { AxiosResponse } from 'axios';
import api from './api';
import { 
    KanbanList, 
    KanbanListCreate, 
    KanbanListUpdate, 
    ListDeletionRequest,
    ListWithCardCount,
    Card 
} from '../types';
import { cardsApi } from './cardsApi';
import { handleApiError, ApiError } from './errorHandler';

// Types for API responses
interface ListCardsCountResponse {
    list_id: number;
    list_name: string;
    cards_count: number;
}

interface ListReorderRequest {
    list_orders: Record<number, number>;
}

// Cache management for lists data
class ListsCache {
    private static instance: ListsCache;
    private cache: KanbanList[] | null = null;
    private lastFetch: number = 0;
    private readonly CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

    static getInstance(): ListsCache {
        if (!ListsCache.instance) {
            ListsCache.instance = new ListsCache();
        }
        return ListsCache.instance;
    }

    isValid(): boolean {
        return this.cache !== null && (Date.now() - this.lastFetch) < this.CACHE_DURATION;
    }

    get(): KanbanList[] | null {
        return this.isValid() ? this.cache : null;
    }

    set(lists: KanbanList[]): void {
        this.cache = lists;
        this.lastFetch = Date.now();
    }

    invalidate(): void {
        this.cache = null;
        this.lastFetch = 0;
    }

    updateList(updatedList: KanbanList): void {
        if (this.cache) {
            const index = this.cache.findIndex(list => list.id === updatedList.id);
            if (index !== -1) {
                this.cache[index] = updatedList;
            }
        }
    }

    removeList(listId: number): void {
        if (this.cache) {
            this.cache = this.cache.filter(list => list.id !== listId);
        }
    }

    addList(newList: KanbanList): void {
        if (this.cache) {
            this.cache.push(newList);
            // Re-sort by order
            this.cache.sort((a, b) => a.order - b.order);
        }
    }
}

// Lists API service
export const listsApi = {
    /**
     * Récupérer toutes les listes ordonnées par ordre d'affichage
     * Utilise le cache si disponible et valide
     */
    async getLists(useCache: boolean = true): Promise<KanbanList[]> {
        try {
            const cache = ListsCache.getInstance();
            
            if (useCache) {
                const cachedLists = cache.get();
                if (cachedLists) {
                    return cachedLists;
                }
            }

            const response: AxiosResponse<KanbanList[]> = await api.get('/lists/');
            const lists = response.data;
            
            // Sort by order to ensure consistency
            lists.sort((a, b) => a.order - b.order);
            
            cache.set(lists);
            return lists;
        } catch (error) {
            return handleApiError(error);
        }
    },

    /**
     * Créer une nouvelle liste (admin seulement)
     */
    async createList(listData: KanbanListCreate): Promise<KanbanList> {
        try {
            const response: AxiosResponse<KanbanList> = await api.post('/lists/', listData);
            const newList = response.data;
            
            // Update cache
            const cache = ListsCache.getInstance();
            cache.addList(newList);
            
            return newList;
        } catch (error) {
            return handleApiError(error);
        }
    },

    /**
     * Récupérer une liste par son ID
     */
    async getList(listId: number): Promise<KanbanList> {
        try {
            const response: AxiosResponse<KanbanList> = await api.get(`/lists/${listId}`);
            return response.data;
        } catch (error) {
            return handleApiError(error);
        }
    },

    /**
     * Mettre à jour une liste (admin seulement)
     */
    async updateList(listId: number, listData: KanbanListUpdate): Promise<KanbanList> {
        try {
            const response: AxiosResponse<KanbanList> = await api.put(`/lists/${listId}`, listData);
            const updatedList = response.data;
            
            // Update cache
            const cache = ListsCache.getInstance();
            cache.updateList(updatedList);
            
            return updatedList;
        } catch (error) {
            return handleApiError(error);
        }
    },

    /**
     * Supprimer une liste après avoir déplacé ses cartes (admin seulement)
     */
    async deleteList(listId: number, targetListId: number): Promise<void> {
        try {
            const deletionRequest: ListDeletionRequest = {
                target_list_id: targetListId
            };
            
            await api.delete(`/lists/${listId}`, { data: deletionRequest });
            
            // Update cache
            const cache = ListsCache.getInstance();
            cache.removeList(listId);
        } catch (error) {
            handleApiError(error);
        }
    },

    /**
     * Récupérer le nombre de cartes dans une liste
     */
    async getListCardsCount(listId: number): Promise<ListWithCardCount> {
        try {
            const response: AxiosResponse<ListCardsCountResponse> = await api.get(`/lists/${listId}/cards-count`);
            const {data} = response;
            
            return {
                list: {
                    id: data.list_id,
                    name: data.list_name,
                    order: 0, // Order not provided in this endpoint
                    created_at: '',
                    updated_at: ''
                },
                card_count: data.cards_count
            };
        } catch (error) {
            return handleApiError(error);
        }
    },

    /**
     * Réorganiser l'ordre des listes (admin seulement)
     */
    async reorderLists(listOrders: Record<number, number>): Promise<void> {
        try {
            const reorderRequest: ListReorderRequest = {
                list_orders: listOrders
            };
            
            await api.post('/lists/reorder', reorderRequest);
            
            // Invalidate cache to force refresh
            const cache = ListsCache.getInstance();
            cache.invalidate();
        } catch (error) {
            handleApiError(error);
        }
    },

    /**
     * Récupérer les cartes d'une liste spécifique
     */
    async getListCards(listId: number): Promise<Card[]> {
        try {
            return await cardsApi.getCardsByList(listId);
        } catch (error) {
            return handleApiError(error);
        }
    },

    /**
     * Déplacer toutes les cartes d'une liste vers une autre avec suivi de progression
     */
    async moveListCardsWithProgress(
        sourceListId: number, 
        targetListId: number, 
        onProgress?: (current: number, total: number, cardName: string) => void
    ): Promise<void> {
        try {
            // Récupérer toutes les cartes de la liste source
            const cards = await this.getListCards(sourceListId);
            
            if (cards.length === 0) {
                return;
            }

            // Déplacer chaque carte une par une
            for (let i = 0; i < cards.length; i++) {
                const card = cards[i];
                
                // Notifier le progrès avant de déplacer la carte
                if (onProgress) {
                    onProgress(i, cards.length, card.title);
                }

                // Déplacer la carte à la fin de la liste cible
                await cardsApi.moveCard(card.id, sourceListId, targetListId);
                
                // Petite pause pour éviter de surcharger le serveur
                await new Promise(resolve => setTimeout(resolve, 100));
            }

            // Notifier la fin du processus
            if (onProgress) {
                onProgress(cards.length, cards.length, '');
            }
        } catch (error) {
            return handleApiError(error);
        }
    },

    /**
     * Supprimer une liste après avoir déplacé ses cartes avec suivi de progression
     */
    async deleteListWithProgress(
        listId: number, 
        targetListId: number,
        onProgress?: (current: number, total: number, cardName: string) => void
    ): Promise<void> {
        try {
            // D'abord déplacer toutes les cartes
            await this.moveListCardsWithProgress(listId, targetListId, onProgress);
            
            // Ensuite supprimer la liste vide
            const deletionRequest: ListDeletionRequest = {
                target_list_id: targetListId
            };
            
            await api.delete(`/lists/${listId}`, { data: deletionRequest });
            
            // Update cache
            const cache = ListsCache.getInstance();
            cache.removeList(listId);
        } catch (error) {
            handleApiError(error);
        }
    },

    /**
     * Invalider le cache des listes
     * Utile après des opérations qui modifient les listes
     */
    invalidateCache(): void {
        const cache = ListsCache.getInstance();
        cache.invalidate();
    },

    /**
     * Vérifier si le cache est valide
     */
    isCacheValid(): boolean {
        const cache = ListsCache.getInstance();
        return cache.isValid();
    }
};

// Export error class for error handling in components
export { ApiError as ListsApiError };

// Export default
export default listsApi;
import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { User, Card, Label, Filters, CreateCardData, UpdateCardData, CreateLabelData, UpdateLabelData, CardChecklistItem, CardComment } from '../types';

// Configuration de base d'Axios
// Utiliser la variable d'environnement si disponible, sinon la valeur par défaut
const API_BASE_URL = (window as any).API_BASE_URL || 'http://localhost:8000';

const api: AxiosInstance = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Intercepteur pour ajouter le token d'authentification
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Intercepteur pour gérer les erreurs d'authentification
api.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Clear auth artifacts
            localStorage.removeItem('token');
            localStorage.removeItem('user');

            const path = window.location.pathname || '';
            const onPublicAuthPage = path.startsWith('/login') || path.startsWith('/invite');
            const alreadyRedirecting = sessionStorage.getItem('auth_redirecting') === '1';

            if (!onPublicAuthPage && !alreadyRedirecting) {
                try { sessionStorage.setItem('auth_redirecting', '1'); } catch { }
                window.location.href = '/login';
            }
            // If we're already on login/invite, don't redirect again; let the page render the form
        }
        return Promise.reject(error);
    }
);

// Services d'authentification
export const authService = {
    async login(email: string, password: string): Promise<User> {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);

        const response = await api.post<{ access_token: string }>('/auth/login', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });

        const { access_token } = response.data;
        localStorage.setItem('token', access_token);

        // Récupérer les informations utilisateur
        const userResponse = await api.get<User>('/auth/me');
        const userData = userResponse.data;
        localStorage.setItem('user', JSON.stringify(userData));

        // Set the language from user preferences
        if (userData.language) {
            // Dynamically import i18n to avoid circular dependency
            const i18n = await import('../i18n').then(module => module.default);
            await i18n.changeLanguage(userData.language);
        }

        // Clear any redirect guard now that we're authenticated
        try { sessionStorage.removeItem('auth_redirecting'); } catch { }

        return userData;
    },

    async logout(): Promise<void> {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        await api.post('/auth/logout');
    },

    async getCurrentUser(): Promise<User> {
        const response = await api.get<User>('/auth/me');
        const userData = response.data;

        // Set the language from user preferences
        if (userData.language) {
            // Dynamically import i18n to avoid circular dependency
            const i18n = await import('../i18n').then(module => module.default);
            await i18n.changeLanguage(userData.language);
        }

        return userData;
    },

    isAuthenticated(): boolean {
        return !!localStorage.getItem('token');
    },

    getCurrentUserFromStorage(): User | null {
        try {
            const user = localStorage.getItem('user');
            if (!user) {
                return null;
            }

            // Vérifier que ce n'est pas un objet déjà parsé
            if (typeof user === 'object') {
                console.warn('Données utilisateur déjà parsées, nettoyage...');
                localStorage.removeItem('user');
                return null;
            }

            const parsedUser = JSON.parse(user);

            // Vérifier que l'objet parsé a la structure attendue
            if (typeof parsedUser === 'object' && parsedUser !== null && 'id' in parsedUser) {
                return parsedUser;
            } else {
                // Données corrompues, nettoyer
                localStorage.removeItem('user');
                return null;
            }
        } catch (error) {
            console.error('Erreur lors du parsing des données utilisateur:', error);
            localStorage.removeItem('user'); // Nettoyer les données corrompues
            return null;
        }
    },

    setCurrentUserToStorage(user: User): void {
        try {
            // S'assurer que user est un objet valide
            if (!user || typeof user !== 'object' || !('id' in user)) {
                console.error('Tentative de sauvegarde d\'un utilisateur invalide:', user);
                return;
            }

            const userString = JSON.stringify(user);
            localStorage.setItem('user', userString);
        } catch (error) {
            console.error('Erreur lors de la sauvegarde des données utilisateur:', error);
            // En cas d'erreur, essayer de nettoyer
            try {
                localStorage.removeItem('user');
            } catch (cleanupError) {
                console.error('Erreur lors du nettoyage du localStorage:', cleanupError);
            }
        }
    }
    ,

    async requestPasswordReset(email: string): Promise<void> {
        // Calls backend endpoint that returns a generic message regardless of existence
        await api.post('/auth/request-password-reset', { email });
    },

    async checkAIFeatures(): Promise<{ ai_available: boolean }> {
        const response = await api.get<{ ai_available: boolean }>('/auth/ai-features');
        return response.data;
    }
};

// Services pour les utilisateurs
export const userService = {
    async getUsers(): Promise<User[]> {
        return getUsersCached();
    },

    async createUser(userData: Partial<User>): Promise<User> {
        const response = await api.post<User>('/users', userData);
        resetUsersCache(); // Reset cache after creating user
        return response.data;
    },

    async inviteUser(payload: { email: string; display_name?: string; role?: string }) {
        const response = await api.post<User>('/users/invite', { email: payload.email, display_name: payload.display_name, role: payload.role });
        resetUsersCache(); // Reset cache after inviting user
        return response.data;
    },

    async resendInvitation(userId: number) {
        const response = await api.post<User>(`/users/${userId}/resend-invitation`);
        resetUsersCache(); // Reset cache after resending invitation
        return response.data;
    },

    async updateUser(userId: number, userData: Partial<User>): Promise<User> {
        const response = await api.put<User>(`/users/${userId}`, userData);
        resetUsersCache(); // Reset cache after updating user
        return response.data;
    },

    async updateLanguage(language: string): Promise<User> {
        const response = await api.put<User>('/users/me/language', { language });
        resetUsersCache(); // Reset cache after updating language
        return response.data;
    },

    async deleteUser(userId: number): Promise<void> {
        await api.delete(`/users/${userId}`);
        resetUsersCache(); // Reset cache after deleting user
    },

    // Function to manually reset users cache
    resetUsersCache: resetUsersCache
};

// Simple in-memory cache and in-flight deduplication for users list
let usersCache: User[] | null = null;
let usersCacheTime = 0;
let usersInFlight: Promise<User[]> | null = null;
const USERS_TTL_MS = 60_000; // 1 minute TTL

// Function to reset users cache
function resetUsersCache(): void {
    usersCache = null;
    usersCacheTime = 0;
    usersInFlight = null;
}

async function getUsersCached(): Promise<User[]> {
    const now = Date.now();
    if (usersCache && now - usersCacheTime < USERS_TTL_MS) {
        return usersCache;
    }
    if (usersInFlight) {
        return usersInFlight;
    }
    usersInFlight = api.get<User[]>('/users/').then((response) => {
        usersCache = response.data;
        usersCacheTime = Date.now();
        usersInFlight = null;
        return usersCache;
    }).catch((err) => {
        usersInFlight = null;
        throw err;
    });
    return usersInFlight;
}

// Services pour les cartes
export const cardService = {
    async getCards(filters: Filters = {}): Promise<Card[]> {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                params.append(key, value.toString());
            }
        });

        const response = await api.get<Card[]>(`/cards/?${params.toString()}`);
        return response.data;
    },

    async getArchivedCards(): Promise<Card[]> {
        const response = await api.get<Card[]>('/cards/archived');
        return response.data;
    },

    async getCard(cardId: number): Promise<Card | null> {
        try {
            const response = await api.get<Card>(`/cards/${cardId}`);
            return response.data;
        } catch (error: any) {
            if (error.response?.status === 404) {
                return null;
            }
            throw error;
        }
    },

    async createCard(cardData: CreateCardData): Promise<Card> {
        const response = await api.post<Card>('/cards/', cardData);
        return response.data;
    },

    async updateCard(cardId: number, cardData: UpdateCardData): Promise<Card> {
        const response = await api.put<Card>(`/cards/${cardId}`, cardData);
        return response.data;
    },

    async archiveCard(cardId: number): Promise<Card> {
        const response = await api.patch<Card>(`/cards/${cardId}/archive`);
        return response.data;
    },

    async unarchiveCard(cardId: number): Promise<Card> {
        const response = await api.patch<Card>(`/cards/${cardId}/unarchive`);
        return response.data;
    },

    async deleteCard(cardId: number): Promise<void> {
        await api.delete(`/cards/${cardId}`);
    },

    async moveCard(cardId: number, sourceListId: number, targetListId: number, position?: number): Promise<Card> {
        const moveRequest = {
            source_list_id: sourceListId,
            target_list_id: targetListId,
            position: position
        };
        const response = await api.patch<Card>(`/cards/${cardId}/move`, moveRequest);
        return response.data;
    }
};

// Services pour les libellés
export const labelService = {
    async getLabels(): Promise<Label[]> {
        const response = await api.get<Label[]>('/labels/');
        return response.data;
    },

    async createLabel(labelData: CreateLabelData): Promise<Label> {
        const response = await api.post<Label>('/labels/', labelData);
        return response.data;
    },

    async updateLabel(labelId: number, labelData: UpdateLabelData): Promise<Label> {
        const response = await api.put<Label>(`/labels/${labelId}`, labelData);
        return response.data;
    },

    async deleteLabel(labelId: number): Promise<void> {
        await api.delete(`/labels/${labelId}`);
    }
};

// Services pour les paramètres du tableau
export const boardSettingsService = {
    async getBoardTitle(): Promise<{ title: string }> {
        const response = await api.get<{ title: string }>('/board-settings/title');
        return response.data;
    },

    async updateBoardTitle(title: string): Promise<{ title: string }> {
        const response = await api.put('/board-settings/title', { title });
        const boardSetting = response.data;
        return { title: boardSetting.setting_value || title };
    }
};

// Services pour les éléments de checklist
export const cardItemsService = {
    async getItems(cardId: number): Promise<CardChecklistItem[]> {
        const response = await api.get<CardChecklistItem[]>(`/card-items/card/${cardId}`);
        return response.data;
    },
    async createItem(cardId: number, text: string, position?: number, is_done: boolean = false): Promise<CardChecklistItem> {
        const payload: any = { card_id: cardId, text, is_done };
        if (typeof position === 'number') {
            payload.position = position;
        }
        const response = await api.post<CardChecklistItem>('/card-items/', payload);
        return response.data;
    },
    async updateItem(itemId: number, data: Partial<Pick<CardChecklistItem, 'text' | 'is_done' | 'position'>>): Promise<CardChecklistItem> {
        const response = await api.put<CardChecklistItem>(`/card-items/${itemId}`, data);
        return response.data;
    },
    async deleteItem(itemId: number): Promise<void> {
        await api.delete(`/card-items/${itemId}`);
    }
};

// Services pour les commentaires
export const cardCommentsService = {
    async getComments(cardId: number): Promise<CardComment[]> {
        const response = await api.get<CardComment[]>(`/card-comments/card/${cardId}`);
        return response.data;
    },
    async createComment(cardId: number, comment: string): Promise<CardComment> {
        const response = await api.post<CardComment>('/card-comments/', { card_id: cardId, comment });
        return response.data;
    },
    async updateComment(commentId: number, comment: string): Promise<CardComment> {
        const response = await api.put<CardComment>(`/card-comments/${commentId}`, { comment });
        return response.data;
    },
    async deleteComment(commentId: number): Promise<void> {
        await api.delete(`/card-comments/${commentId}`);
    }
};

export default api;

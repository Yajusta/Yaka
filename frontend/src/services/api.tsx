import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { User, Card, Label, Filters, CreateCardData, UpdateCardData, CreateLabelData, UpdateLabelData, CardChecklistItem, CardComment, ViewScope, GlobalDictionaryEntry, PersonalDictionaryEntry } from '../types';

// Configuration de base d'Axios
// Utiliser la variable d'environnement si disponible, sinon la valeur par défaut
const API_BASE_URL = (window as any).API_BASE_URL || 'http://localhost:8000';

// Obtenir le board_uid depuis l'URL courante
const getBoardUidFromUrl = (): string | null => {
    const path = window.location.pathname;
    const match = path.match(/^\/board\/([^\/]+)/);
    return match ? match[1] : null;
};

// Créer l'instance API avec configuration dynamique
const createApiInstance = (): AxiosInstance => {
    const boardUid = getBoardUidFromUrl();
    const baseUrl = boardUid ? `${API_BASE_URL}/board/${boardUid}` : API_BASE_URL;

    return axios.create({
        baseURL: baseUrl,
        headers: {
            'Content-Type': 'application/json',
        },
    });
};

// Intercepteur pour ajouter le token d'authentification
const setupInterceptors = (apiInstance: AxiosInstance) => {
    apiInstance.interceptors.request.use(
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
    apiInstance.interceptors.response.use(
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
                    const boardUid = getBoardUidFromUrl();
                    if (boardUid) {
                        window.location.href = `/board/${boardUid}/login`;
                    } else {
                        window.location.href = '/login';
                    }
                }
            }
            return Promise.reject(error);
        }
    );
};

// Créer l'instance API avec les intercepteurs configurés
const createApiInstanceWithInterceptors = (): AxiosInstance => {
    const instance = createApiInstance();
    setupInterceptors(instance);
    return instance;
};

// Fonction pour obtenir l'instance API courante
export const getApiInstance = (): AxiosInstance => {
    return createApiInstanceWithInterceptors();
};

// Exporter une instance par défaut pour compatibilité
const api: AxiosInstance = getApiInstance();

// Services d'authentification
export const authService = {
    async login(email: string, password: string): Promise<User> {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);

        const apiInstance = getApiInstance();
        const response = await apiInstance.post<{ access_token: string }>('/auth/login', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });

        const { access_token } = response.data;
        localStorage.setItem('token', access_token);

        // Récupérer les informations utilisateur
        const userResponse = await apiInstance.get<User>('/auth/me');
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
        await getApiInstance().post('/auth/logout');
    },

    async getCurrentUser(): Promise<User> {
        const response = await getApiInstance().get<User>('/auth/me');
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
        await getApiInstance().post('/auth/request-password-reset', { email });
    },

    async checkAIFeatures(): Promise<{ ai_available: boolean }> {
        const response = await getApiInstance().get<{ ai_available: boolean }>('/auth/ai-features');
        return response.data;
    }
};

// Services pour les utilisateurs
export const userService = {
    async getUsers(): Promise<User[]> {
        return getUsersCached();
    },

    async createUser(userData: Partial<User>): Promise<User> {
        const response = await getApiInstance().post<User>('/users', userData);
        resetUsersCache(); // Reset cache after creating user
        return response.data;
    },

    async inviteUser(payload: { email: string; display_name?: string; role?: string }) {
        const response = await getApiInstance().post<User>('/users/invite', { email: payload.email, display_name: payload.display_name, role: payload.role });
        resetUsersCache(); // Reset cache after inviting user
        return response.data;
    },

    async resendInvitation(userId: number) {
        const response = await getApiInstance().post<User>(`/users/${userId}/resend-invitation`);
        resetUsersCache(); // Reset cache after resending invitation
        return response.data;
    },

    async updateUser(userId: number, userData: Partial<User>): Promise<User> {
        const response = await getApiInstance().put<User>(`/users/${userId}`, userData);
        resetUsersCache(); // Reset cache after updating user
        return response.data;
    },

    async updateLanguage(language: string): Promise<User> {
        const response = await getApiInstance().put<User>('/users/me/language', { language });
        resetUsersCache(); // Reset cache after updating language
        return response.data;
    },
    async updateViewScope(userId: number, viewScope: ViewScope): Promise<User> {
        const response = await getApiInstance().put<User>(`/users/${userId}/view-scope`, { view_scope: viewScope });
        resetUsersCache(); // Reset cache after updating view scope
        return response.data;
    },

    async deleteUser(userId: number): Promise<void> {
        await getApiInstance().delete(`/users/${userId}`);
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
    usersInFlight = getApiInstance().get<User[]>('/users/').then((response) => {
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

        const response = await getApiInstance().get<Card[]>(`/cards/?${params.toString()}`);
        return response.data;
    },

    async getArchivedCards(): Promise<Card[]> {
        const response = await getApiInstance().get<Card[]>('/cards/archived');
        return response.data;
    },

    async getCard(cardId: number): Promise<Card | null> {
        try {
            const response = await getApiInstance().get<Card>(`/cards/${cardId}`);
            return response.data;
        } catch (error: any) {
            if (error.response?.status === 404) {
                return null;
            }
            throw error;
        }
    },

    async createCard(cardData: CreateCardData): Promise<Card> {
        const response = await getApiInstance().post<Card>('/cards/', cardData);
        return response.data;
    },

    async updateCard(cardId: number, cardData: UpdateCardData): Promise<Card> {
        const response = await getApiInstance().put<Card>(`/cards/${cardId}`, cardData);
        return response.data;
    },

    async archiveCard(cardId: number): Promise<Card> {
        const response = await getApiInstance().patch<Card>(`/cards/${cardId}/archive`);
        return response.data;
    },

    async unarchiveCard(cardId: number): Promise<Card> {
        const response = await getApiInstance().patch<Card>(`/cards/${cardId}/unarchive`);
        return response.data;
    },

    async deleteCard(cardId: number): Promise<void> {
        await getApiInstance().delete(`/cards/${cardId}`);
    },

    async moveCard(cardId: number, sourceListId: number, targetListId: number, position?: number): Promise<Card> {
        const moveRequest = {
            source_list_id: sourceListId,
            target_list_id: targetListId,
            position: position
        };
        const response = await getApiInstance().patch<Card>(`/cards/${cardId}/move`, moveRequest);
        return response.data;
    }
};

// Services pour les libellés
export const labelService = {
    async getLabels(): Promise<Label[]> {
        const response = await getApiInstance().get<Label[]>('/labels/');
        return response.data;
    },

    async createLabel(labelData: CreateLabelData): Promise<Label> {
        const response = await getApiInstance().post<Label>('/labels/', labelData);
        return response.data;
    },

    async updateLabel(labelId: number, labelData: UpdateLabelData): Promise<Label> {
        const response = await getApiInstance().put<Label>(`/labels/${labelId}`, labelData);
        return response.data;
    },

    async deleteLabel(labelId: number): Promise<void> {
        await getApiInstance().delete(`/labels/${labelId}`);
    }
};

// Services pour les paramètres du tableau
export const boardSettingsService = {
    async getBoardTitle(): Promise<{ title: string }> {
        const response = await getApiInstance().get<{ title: string }>('/board-settings/title');
        return response.data;
    },

    async updateBoardTitle(title: string): Promise<{ title: string }> {
        const response = await getApiInstance().put('/board-settings/title', { title });
        const boardSetting = response.data;
        return { title: boardSetting.setting_value || title };
    }
};

// Services pour les éléments de checklist
export const cardItemsService = {
    async getItems(cardId: number): Promise<CardChecklistItem[]> {
        const response = await getApiInstance().get<CardChecklistItem[]>(`/card-items/card/${cardId}`);
        return response.data;
    },
    async createItem(cardId: number, text: string, position?: number, is_done: boolean = false): Promise<CardChecklistItem> {
        const payload: any = { card_id: cardId, text, is_done };
        if (typeof position === 'number') {
            payload.position = position;
        }
        const response = await getApiInstance().post<CardChecklistItem>('/card-items/', payload);
        return response.data;
    },
    async updateItem(itemId: number, data: Partial<Pick<CardChecklistItem, 'text' | 'is_done' | 'position'>>): Promise<CardChecklistItem> {
        const response = await getApiInstance().put<CardChecklistItem>(`/card-items/${itemId}`, data);
        return response.data;
    },
    async deleteItem(itemId: number): Promise<void> {
        await getApiInstance().delete(`/card-items/${itemId}`);
    }
};

// Services pour les commentaires
export const cardCommentsService = {
    async getComments(cardId: number): Promise<CardComment[]> {
        const response = await getApiInstance().get<CardComment[]>(`/card-comments/card/${cardId}`);
        return response.data;
    },
    async createComment(cardId: number, comment: string): Promise<CardComment> {
        const response = await getApiInstance().post<CardComment>('/card-comments/', { card_id: cardId, comment });
        return response.data;
    },
    async updateComment(commentId: number, comment: string): Promise<CardComment> {
        const response = await getApiInstance().put<CardComment>(`/card-comments/${commentId}`, { comment });
        return response.data;
    },
    async deleteComment(commentId: number): Promise<void> {
        await getApiInstance().delete(`/card-comments/${commentId}`);
    }
};

// Services for global dictionary
export const globalDictionaryService = {
    async getEntries(): Promise<GlobalDictionaryEntry[]> {
        const response = await getApiInstance().get<GlobalDictionaryEntry[]>('/global-dictionary/');
        return response.data;
    },
    async getEntry(entryId: number): Promise<GlobalDictionaryEntry> {
        const response = await getApiInstance().get<GlobalDictionaryEntry>(`/global-dictionary/${entryId}`);
        return response.data;
    },
    async createEntry(entry: { term: string; definition: string }): Promise<GlobalDictionaryEntry> {
        const response = await getApiInstance().post<GlobalDictionaryEntry>('/global-dictionary/', entry);
        return response.data;
    },
    async updateEntry(entryId: number, entry: { term?: string; definition?: string }): Promise<GlobalDictionaryEntry> {
        const response = await getApiInstance().put<GlobalDictionaryEntry>(`/global-dictionary/${entryId}`, entry);
        return response.data;
    },
    async deleteEntry(entryId: number): Promise<void> {
        await getApiInstance().delete(`/global-dictionary/${entryId}`);
    }
};

// Services for personal dictionary
export const personalDictionaryService = {
    async getEntries(): Promise<PersonalDictionaryEntry[]> {
        const response = await getApiInstance().get<PersonalDictionaryEntry[]>('/personal-dictionary/');
        return response.data;
    },
    async getEntry(entryId: number): Promise<PersonalDictionaryEntry> {
        const response = await getApiInstance().get<PersonalDictionaryEntry>(`/personal-dictionary/${entryId}`);
        return response.data;
    },
    async createEntry(entry: { term: string; definition: string }): Promise<PersonalDictionaryEntry> {
        const response = await getApiInstance().post<PersonalDictionaryEntry>('/personal-dictionary/', entry);
        return response.data;
    },
    async updateEntry(entryId: number, entry: { term?: string; definition?: string }): Promise<PersonalDictionaryEntry> {
        const response = await getApiInstance().put<PersonalDictionaryEntry>(`/personal-dictionary/${entryId}`, entry);
        return response.data;
    },
    async deleteEntry(entryId: number): Promise<void> {
        await getApiInstance().delete(`/personal-dictionary/${entryId}`);
    }
};

export default api;

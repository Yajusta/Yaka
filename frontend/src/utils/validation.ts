/**
 * Validation utilities for list management
 */

export interface ValidationResult {
    isValid: boolean;
    error?: string;
}

/**
 * Validate list name according to requirements
 */
export const validateListName = (name: string): ValidationResult => {
    // Trim whitespace
    const trimmedName = name.trim();
    
    // Check if empty (Requirement 2.4)
    if (!trimmedName) {
        return {
            isValid: false,
            error: 'Le nom de la liste ne peut pas être vide'
        };
    }
    
    // Check minimum length
    if (trimmedName.length < 1) {
        return {
            isValid: false,
            error: 'Le nom de la liste doit contenir au moins 1 caractère'
        };
    }
    
    // Check maximum length
    if (trimmedName.length > 100) {
        return {
            isValid: false,
            error: 'Le nom de la liste ne peut pas dépasser 100 caractères'
        };
    }
    
    // Check for invalid characters
    const invalidChars = /[<>"']/;
    if (invalidChars.test(trimmedName)) {
        return {
            isValid: false,
            error: 'Le nom de la liste contient des caractères non autorisés (<, >, ", \')'
        };
    }
    
    return { isValid: true };
};

/**
 * Validate list order
 */
export const validateListOrder = (order: number): ValidationResult => {
    // Check if positive integer
    if (!Number.isInteger(order) || order < 1) {
        return {
            isValid: false,
            error: 'L\'ordre doit être un nombre entier positif (≥ 1)'
        };
    }
    
    // Check maximum value
    if (order > 9999) {
        return {
            isValid: false,
            error: 'L\'ordre ne peut pas dépasser 9999'
        };
    }
    
    return { isValid: true };
};

/**
 * Check if list name is unique (case-insensitive)
 */
export const isListNameUnique = (name: string, existingLists: Array<{ name: string; id?: number }>, excludeId?: number): ValidationResult => {
    const trimmedName = name.trim().toLowerCase();
    
    const duplicate = existingLists.find(list => 
        list.name.toLowerCase() === trimmedName && 
        (excludeId === undefined || list.id !== excludeId)
    );
    
    if (duplicate) {
        return {
            isValid: false,
            error: `Une liste avec le nom "${name.trim()}" existe déjà (la casse est ignorée)`
        };
    }
    
    return { isValid: true };
};

/**
 * Validate deletion constraints (Requirements 4.1, 4.2)
 * This function is used for final validation before confirming deletion
 */
export const validateListDeletion = (
    listToDelete: { id: number; name: string },
    allLists: Array<{ id: number; name: string }>,
    cardCount: number,
    targetListId?: number
): ValidationResult => {
    // Check if this is the last list (Requirement 4.1)
    if (allLists.length <= 1) {
        return {
            isValid: false,
            error: 'Impossible de supprimer la dernière liste. Au moins une liste doit exister dans le système.'
        };
    }
    
    // If list has cards, target list must be specified (Requirement 4.2)
    if (cardCount > 0 && !targetListId) {
        return {
            isValid: false,
            error: 'Vous devez sélectionner une liste de destination pour les cartes existantes'
        };
    }
    
    // Target list must be different from the list being deleted
    if (targetListId && targetListId === listToDelete.id) {
        return {
            isValid: false,
            error: 'La liste de destination ne peut pas être la même que la liste à supprimer'
        };
    }
    
    // Target list must exist
    if (targetListId && !allLists.find(list => list.id === targetListId)) {
        return {
            isValid: false,
            error: 'La liste de destination sélectionnée n\'existe pas'
        };
    }
    
    return { isValid: true };
};

/**
 * Validate reorder operation
 */
export const validateListReorder = (listOrders: Record<number, number>): ValidationResult => {
    const orders = Object.values(listOrders);
    const listIds = Object.keys(listOrders).map(Number);
    
    // Check if any data provided
    if (orders.length === 0) {
        return {
            isValid: false,
            error: 'Au moins une liste doit être fournie pour la réorganisation'
        };
    }
    
    // Check if all orders are positive
    if (orders.some(order => order < 1)) {
        return {
            isValid: false,
            error: 'Tous les ordres doivent être des nombres entiers positifs (≥ 1)'
        };
    }
    
    // Check if all orders are unique
    const uniqueOrders = new Set(orders);
    if (uniqueOrders.size !== orders.length) {
        return {
            isValid: false,
            error: 'Les ordres doivent être uniques'
        };
    }
    
    // Check if all list IDs are positive
    if (listIds.some(id => id <= 0)) {
        return {
            isValid: false,
            error: 'Tous les IDs de liste doivent être des nombres entiers positifs'
        };
    }
    
    return { isValid: true };
};

/**
 * Get user-friendly error message for common API errors
 */
export const getErrorMessage = (error: any): string => {
    // Handle network errors
    if (!error.response) {
        return 'Erreur de connexion. Vérifiez votre connexion internet et réessayez.';
    }
    
    // Handle specific HTTP status codes
    switch (error.response.status) {
        case 400:
            return error.response.data?.detail || 'Données invalides. Vérifiez les informations saisies.';
        case 401:
            return 'Vous n\'êtes pas autorisé à effectuer cette action. Veuillez vous reconnecter.';
        case 403:
            return 'Vous n\'avez pas les permissions nécessaires pour effectuer cette action.';
        case 404:
            return 'La ressource demandée n\'a pas été trouvée.';
        case 409:
            return 'Conflit détecté. Cette action ne peut pas être effectuée en raison d\'un conflit avec l\'état actuel.';
        case 422:
            return error.response.data?.detail || 'Données de validation incorrectes.';
        case 500:
            return 'Erreur interne du serveur. Veuillez réessayer plus tard.';
        case 503:
            return 'Service temporairement indisponible. Veuillez réessayer plus tard.';
        default:
            return error.response.data?.detail || 'Une erreur inattendue s\'est produite.';
    }
};
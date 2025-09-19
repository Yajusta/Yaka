import React from 'react';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

export interface User {
    id: number;
    username?: string;
    email: string;
    display_name?: string;
    role?: string;
    language?: string;
    created_at: string;
    updated_at?: string;
}

export interface KanbanList {
    id: number;
    name: string;
    order: number;
    created_at: string;
    updated_at?: string;
}

export interface Card {
    id: number;
    title: string;
    description: string;
    priority: string;
    assignee_id: number | null;
    label_id: number | null;
    colonne: string;
    list_id: number;
    due_date?: string;
    assignee?: User;
    labels?: Label[];
    kanban_list?: KanbanList;
    created_at: string;
    updated_at: string;
    items?: CardChecklistItem[]; // éléments de checklist
    comments?: CardComment[]; // commentaires
}

export interface Label {
    id: number;
    name: string;
    color: string;
    created_at: string;
    updated_at: string;
}

// CardChecklistItem est défini plus bas pour éviter les références circulaires

export interface Filters {
    search?: string;
    assignee_id?: number | null;
    priority?: string | null;
    label_id?: number | null;
}

export interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
}

export interface ThemeContextType {
    theme: string;
    setTheme: (theme: string) => void;
}

export interface ApiResponse<T> {
    data: T;
    message?: string;
    error?: string;
}

export interface LoginCredentials {
    email: string;
    password: string;
}

export interface CreateCardData {
    title: string;
    // description can be null when not provided
    description: string | null;
    priority: string;
    assignee_id?: number | null;
    // Support multiple labels on create to match backend schema
    label_ids?: number[];
    // colonne is optional on the frontend; backend determines statut/colonne defaults
    colonne?: string;
    // list_id is required for new list-based system
    list_id: number;
    // due_date can be omitted or null
    due_date?: string | null;
}

// UpdateCardData is a partial CreateCardData; the id is provided via the route (not required in the body)
export interface UpdateCardData extends Partial<CreateCardData> { }

export interface CreateLabelData {
    name: string;
    color: string;
}

export interface UpdateLabelData extends Partial<CreateLabelData> {
    id: number;
}

export interface CardChecklistItem {
    id: number;
    card_id: number;
    text: string;
    is_done: boolean;
    position: number;
    created_at: string;
    updated_at: string;
}

export interface CardComment {
    id: number;
    card_id: number;
    user_id: number;
    comment: string;
    is_deleted: boolean;
    created_at: string;
    updated_at: string;
    user?: User;
}

export interface CardHistoryEntry {
    id: number;
    card_id: number;
    user_id: number;
    action: string;
    description: string;
    created_at: string;
    user?: User;
}

// List management types
export interface KanbanListCreate {
    name: string;
    order: number;
}

export interface KanbanListUpdate {
    name?: string;
    order?: number;
}

export interface ListDeletionRequest {
    target_list_id: number;
}

export interface ListWithCardCount {
    list: KanbanList;
    card_count: number;
}

export interface ListReorderRequest {
    list_orders: Record<number, number>;
}

export interface CardMoveRequest {
    source_list_id: number;
    target_list_id: number;
    position?: number;
}

export enum CardPriority {
    LOW = 'low',
    MEDIUM = 'medium',
    HIGH = 'high'
}

export const UserRole = {
    ADMIN: 'admin',
    USER: 'user'
} as const;

// Legacy function - kept for backward compatibility during transition
// This function is now moved to useTranslatedLabels hook for proper i18n support

// New function for getting list name from KanbanList
export const getListName = (list: KanbanList | undefined): string => {
    return list?.name || 'Unknown List';
};

export const getPriorityColor = (priority: string): string => {
    switch (priority) {
        case CardPriority.LOW:
            return 'bg-green-100 text-green-800';
        case CardPriority.MEDIUM:
            return 'bg-yellow-100 text-yellow-800';
        case CardPriority.HIGH:
            return 'bg-red-100 text-red-800';
        default:
            return 'bg-gray-100 text-gray-800';
    }
};

// This function is now moved to useTranslatedLabels hook for proper i18n support
// Kept for backward compatibility - use useTranslatedLabels hook instead

export const getPriorityIcon = (priority: string): React.ComponentType<{ className?: string }> => {
    switch (priority) {
        case CardPriority.HIGH:
            return ArrowUp;
        case CardPriority.MEDIUM:
            return Minus;
        case CardPriority.LOW:
            return ArrowDown;
        default:
            return Minus;
    }
};

export const getPriorityIconColor = (priority: string): string => {
    switch (priority) {
        case CardPriority.HIGH:
            return 'text-destructive';
        case CardPriority.MEDIUM:
            return 'text-sky-600';
        case CardPriority.LOW:
            return 'text-muted-foreground';
        default:
            return 'text-muted-foreground';
    }
};

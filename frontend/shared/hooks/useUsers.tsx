import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { userService } from '../services/api';
import { useAuth } from './useAuth';
import type { User as BaseUser } from '../types';

export type AppUser = BaseUser & { status?: string; invited_at?: string };

type UsersContextValue = {
    users: AppUser[];
    loading: boolean;
    error: string | null;
    forbidden: boolean;
    refresh: () => Promise<void>;
};

const UsersContext = createContext<UsersContextValue | undefined>(undefined);

export const UsersProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [users, setUsers] = useState<AppUser[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [forbidden, setForbidden] = useState<boolean>(false);
    const { user, loading: authLoading } = useAuth();

    const fetchUsers = useCallback(async () => {
        setLoading(true);
        setError(null);
        setForbidden(false);
        try {
            // Reset cache before fetching to ensure fresh data
            userService.resetUsersCache();
            const data = await userService.getUsers();
            setUsers(data);
        } catch (e: any) {
            if (e?.response?.status === 403) {
                setForbidden(true);
                setUsers([]);
            } else {
                setError(e?.message || 'Erreur lors du chargement des utilisateurs');
            }
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // Only attempt to load users when authentication state is known and a user is present
        if (authLoading) {
            return;
        }
        if (!user) {
            // Not authenticated: ensure clean state and stop loading
            setUsers([]);
            setLoading(false);
            setError(null);
            setForbidden(false);
            return;
        }
        fetchUsers();
    }, [authLoading, user, fetchUsers]);

    const value = useMemo<UsersContextValue>(() => ({
        users,
        loading,
        error,
        forbidden,
        refresh: fetchUsers,
    }), [users, loading, error, forbidden, fetchUsers]);

    return (
        <UsersContext.Provider value={value}>
            {children}
        </UsersContext.Provider>
    );
};

export const useUsers = (): UsersContextValue => {
    const ctx = useContext(UsersContext);
    if (!ctx) {
        throw new Error('useUsers must be used within a UsersProvider');
    }
    return ctx;
};

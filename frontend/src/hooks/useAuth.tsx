import { useState, useEffect, createContext, useContext, ReactNode, JSX } from 'react';
import { authService } from '../services/api';
import { User, AuthContextType } from '../types';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = (): AuthContextType => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

interface AuthProviderProps {
    children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps): JSX.Element => {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [aiAvailable, setAiAvailable] = useState<boolean>(false);

    useEffect(() => {
        const initAuth = async (): Promise<void> => {
            try {
                if (authService.isAuthenticated()) {
                    const userData = authService.getCurrentUserFromStorage();
                    if (userData && typeof userData === 'object' && 'id' in userData) {
                        setUser(userData);
                        // Check AI features availability
                        try {
                            const aiFeatures = await authService.checkAIFeatures();
                            setAiAvailable(aiFeatures.ai_available);
                        } catch (error) {
                            console.error('Erreur lors de la vérification des fonctionnalités IA:', error);
                            setAiAvailable(false);
                        }
                    } else {
                        // Données invalides, forcer la déconnexion
                        console.warn('Données utilisateur invalides, déconnexion forcée');
                        await authService.logout();
                    }
                }
            } catch (error) {
                console.error('Erreur lors de l\'initialisation de l\'authentification:', error);
                try {
                    await authService.logout();
                } catch (logoutError) {
                    console.error('Erreur lors de la déconnexion forcée:', logoutError);
                }
            } finally {
                setLoading(false);
            }
        };
        initAuth();
    }, []);

    const login = async (email: string, password: string): Promise<void> => {
        try {
            const userData = await authService.login(email, password);
            setUser(userData);
            // Check AI features availability after login
            try {
                const aiFeatures = await authService.checkAIFeatures();
                setAiAvailable(aiFeatures.ai_available);
            } catch (error) {
                console.error('Erreur lors de la vérification des fonctionnalités IA:', error);
                setAiAvailable(false);
            }
        } catch (error) {
            throw error;
        }
    };

    const logout = async (): Promise<void> => {
        try {
            await authService.logout();
            setUser(null);
            setAiAvailable(false);
        } catch (error) {
            console.error('Erreur lors de la déconnexion:', error);
        }
    };

    const value: AuthContextType = {
        user,
        login,
        logout,
        loading,
        aiAvailable,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}; 
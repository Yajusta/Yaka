import { useEffect } from 'react';
import { authService } from '../services/api';
import i18n from '../i18n';

export const useUserLanguage = () => {
    useEffect(() => {
        const initializeUserLanguage = async () => {
            try {
                // Check if user is authenticated
                if (authService.isAuthenticated()) {
                    // Try to get user from localStorage first
                    const currentUser = authService.getCurrentUserFromStorage();
                    
                    if (currentUser?.language) {
                        // Set language from localStorage user data
                        await i18n.changeLanguage(currentUser.language);
                    } else {
                        // If no user in localStorage, fetch from API
                        try {
                            const userData = await authService.getCurrentUser();
                            if (userData?.language) {
                                await i18n.changeLanguage(userData.language);
                            }
                        } catch (error) {
                            console.error('Failed to fetch user language:', error);
                            // Fallback to browser language or default
                            const browserLang = navigator.language.split('-')[0];
                            await i18n.changeLanguage(browserLang === 'en' ? 'en' : 'fr');
                        }
                    }
                } else {
                    // User not authenticated, use browser language or default
                    const browserLang = navigator.language.split('-')[0];
                    await i18n.changeLanguage(browserLang === 'en' ? 'en' : 'fr');
                }
            } catch (error) {
                console.error('Error initializing user language:', error);
                // Fallback to French
                await i18n.changeLanguage('fr');
            }
        };

        initializeUserLanguage();
    }, []);
};
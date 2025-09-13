import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Languages } from 'lucide-react';
import { userService, authService } from '@/services/api';

const LanguageSelector: React.FC = () => {
    const { i18n, t } = useTranslation();
    const [isLoading, setIsLoading] = useState(false);

    const changeLanguage = async (lng: string) => {
        setIsLoading(true);
        try {
            // Change language in i18next
            await i18n.changeLanguage(lng);

            // Check if user is authenticated
            if (authService.isAuthenticated()) {
                try {
                    // Update language in database
                    await userService.updateLanguage(lng);

                    // Update user in localStorage
                    const currentUser = authService.getCurrentUserFromStorage();
                    if (currentUser) {
                        const updatedUser = { ...currentUser, language: lng };
                        authService.setCurrentUserToStorage(updatedUser);
                    }
                } catch (error) {
                    console.error('Failed to update language in database:', error);
                    // Don't revert the language change, just log the error
                }
            }
        } catch (error) {
            console.error('Failed to change language:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const currentLanguage = i18n.language;
    const isFrench = currentLanguage === 'fr';

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-9 w-9 p-0"
                    title={t('language.switchLanguage')}
                    disabled={isLoading}
                >
                    <Languages className="h-4 w-4" />
                    <span className="sr-only">{t('language.switchLanguage')}</span>
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => changeLanguage('fr')} disabled={isLoading}>
                    <span className="mr-2">🇫🇷</span>
                    Français
                    {isFrench && <span className="ml-2">✓</span>}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => changeLanguage('en')} disabled={isLoading}>
                    <span className="mr-2">🇬🇧</span>
                    English
                    {!isFrench && <span className="ml-2">✓</span>}
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    );
};

export default LanguageSelector;
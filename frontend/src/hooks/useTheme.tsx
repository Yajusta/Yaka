import { useState, useEffect } from 'react';

type Theme = 'light' | 'dark';

interface UseThemeReturn {
    theme: Theme;
    toggleTheme: () => void;
}

export const useTheme = (): UseThemeReturn => {
    const [theme, setTheme] = useState<Theme>(() => {
        // Vérifier s'il y a un thème sauvegardé dans localStorage
        const savedTheme = localStorage.getItem('theme') as Theme;
        if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
            return savedTheme;
        }
        // Forcer le mode clair par défaut
        return 'light';
    });

    useEffect(() => {
        const root = window.document.documentElement;

        // Supprimer toutes les classes de thème
        root.classList.remove('dark', 'theme-light', 'theme-dark');

        if (theme === 'dark') {
            root.classList.add('dark', 'theme-dark');
        } else {
            root.classList.add('theme-light');
        }

        localStorage.setItem('theme', theme);
    }, [theme]);

    const toggleTheme = (): void => {
        const newTheme: Theme = theme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
    };

    return { theme, toggleTheme };
}; 
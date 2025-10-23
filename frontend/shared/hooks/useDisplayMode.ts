import { useEffect, useState } from 'react';

export type DisplayMode = 'extended' | 'compact';

const STORAGE_KEY = 'yaka-display-mode';
const DEFAULT_MODE: DisplayMode = 'extended';

/**
 * Hook to manage card display mode (Extended/Compact) with localStorage persistence
 */
export const useDisplayMode = () => {
    const [displayMode, setDisplayMode] = useState<DisplayMode>(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored === 'extended' || stored === 'compact') {
                return stored;
            }
        } catch (error) {
            console.error('Error reading display mode from localStorage:', error);
        }
        return DEFAULT_MODE;
    });

    useEffect(() => {
        try {
            localStorage.setItem(STORAGE_KEY, displayMode);
        } catch (error) {
            console.error('Error saving display mode to localStorage:', error);
        }
    }, [displayMode]);

    const toggleDisplayMode = () => {
        setDisplayMode(prev => prev === 'extended' ? 'compact' : 'extended');
    };

    const isCompact = displayMode === 'compact';
    const isExtended = displayMode === 'extended';

    return {
        displayMode,
        setDisplayMode,
        toggleDisplayMode,
        isCompact,
        isExtended
    };
};


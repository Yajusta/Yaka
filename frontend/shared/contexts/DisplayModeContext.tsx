import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';

export type DisplayMode = 'extended' | 'compact';

interface DisplayModeContextType {
  displayMode: DisplayMode;
  setDisplayMode: (mode: DisplayMode) => void;
  toggleDisplayMode: () => void;
  isCompact: boolean;
  isExtended: boolean;
}

const DisplayModeContext = createContext<DisplayModeContextType | undefined>(undefined);

const STORAGE_KEY = 'yaka-display-mode';
const DEFAULT_MODE: DisplayMode = 'extended';

interface DisplayModeProviderProps {
  children: ReactNode;
}

export const DisplayModeProvider = ({ children }: DisplayModeProviderProps) => {
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

  const value: DisplayModeContextType = {
    displayMode,
    setDisplayMode,
    toggleDisplayMode,
    isCompact,
    isExtended
  };

  return (
    <DisplayModeContext.Provider value={value}>
      {children}
    </DisplayModeContext.Provider>
  );
};

export const useDisplayMode = () => {
  const context = useContext(DisplayModeContext);
  if (context === undefined) {
    throw new Error('useDisplayMode must be used within a DisplayModeProvider');
  }
  return context;
};
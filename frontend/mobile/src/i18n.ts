import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import des fichiers de traduction
import en from '@shared/i18n/locales/en.json';
import fr from '@shared/i18n/locales/fr.json';

const resources = {
    en: {
        translation: en
    },
    fr: {
        translation: fr
    }
};

// Initialize i18n - use initImmediate to ensure synchronous initialization
i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
        resources,
        lng: undefined, // Laisser indéfini pour être déterminé dynamiquement
        fallbackLng: 'fr',
        debug: false,
        
        // Force synchronous initialization
        initImmediate: false,

        interpolation: {
            escapeValue: false // React échappe déjà les valeurs
        },

        detection: {
            order: ['localStorage', 'navigator', 'htmlTag'],
            caches: ['localStorage']
        },
        
        react: {
            useSuspense: false // Disable suspense to avoid timing issues
        }
    });

export default i18n;
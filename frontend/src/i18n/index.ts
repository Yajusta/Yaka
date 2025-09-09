import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import des fichiers de traduction
import en from './locales/en.json';
import fr from './locales/fr.json';

const resources = {
    en: {
        translation: en
    },
    fr: {
        translation: fr
    }
};

i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
        resources,
        lng: undefined, // Laisser indéfini pour être déterminé dynamiquement
        fallbackLng: 'fr',
        debug: process.env.NODE_ENV === 'development',
        
        interpolation: {
            escapeValue: false // React échappe déjà les valeurs
        },
        
        detection: {
            order: ['localStorage', 'navigator', 'htmlTag'],
            caches: ['localStorage']
        }
    });

export default i18n;
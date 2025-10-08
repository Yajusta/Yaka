/**
 * Service API pour l'export des cartes
 */

import api from './api';

/**
 * Exporte les cartes au format CSV
 * Télécharge automatiquement le fichier
 * @returns Le nom du fichier téléchargé
 */
export const exportCardsAsCSV = async (): Promise<string> => {
    try {
        const response = await api.get('/export/', {
            params: { format: 'csv' },
            responseType: 'blob'
        });

        // Créer un lien de téléchargement
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;

        // Extraire le nom de fichier des headers ou utiliser un nom par défaut
        const contentDisposition = response.headers['content-disposition'];
        let filename = 'yaka_export.csv';

        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1].replace(/['"]/g, '');
            }
        }

        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);

        return filename;
    } catch (error: any) {
        console.error('Erreur lors de l\'export CSV:', error);
        throw new Error(
            error.response?.data?.detail ||
            'Erreur lors de l\'export CSV. Veuillez réessayer.'
        );
    }
};

/**
 * Exporte les cartes au format Excel (XLSX)
 * Télécharge automatiquement le fichier
 * @returns Le nom du fichier téléchargé
 */
export const exportCardsAsExcel = async (): Promise<string> => {
    try {
        const response = await api.get('/export/', {
            params: { format: 'xlsx' },
            responseType: 'blob'
        });

        // Créer un lien de téléchargement
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;

        // Extraire le nom de fichier des headers ou utiliser un nom par défaut
        const contentDisposition = response.headers['content-disposition'];
        let filename = 'yaka_export.xlsx';

        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1].replace(/['"]/g, '');
            }
        }

        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);

        return filename;
    } catch (error: any) {
        console.error('Erreur lors de l\'export Excel:', error);
        throw new Error(
            error.response?.data?.detail ||
            'Erreur lors de l\'export Excel. Veuillez réessayer.'
        );
    }
};

// Export groupé
export const exportApi = {
    exportCSV: exportCardsAsCSV,
    exportExcel: exportCardsAsExcel
};


import { useTranslation } from 'react-i18next';
import { CardPriority } from '../types';

export const useTranslatedLabels = () => {
    const { t } = useTranslation();

    const getPriorityLabel = (priority: string): string => {
        switch (priority) {
            case CardPriority.LOW:
                return t('priority.low');
            case CardPriority.MEDIUM:
                return t('priority.medium');
            case CardPriority.HIGH:
                return t('priority.high');
            default:
                return t('priority.none');
        }
    };

    return {
        getPriorityLabel
    };
};
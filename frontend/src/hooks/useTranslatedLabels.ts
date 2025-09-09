import { useTranslation } from 'react-i18next';
import { CardPriority, CardStatus } from '../types';

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

    const getStatusLabel = (status: string): string => {
        switch (status) {
            case CardStatus.A_FAIRE:
                return t('status.todo');
            case CardStatus.EN_COURS:
                return t('status.inProgress');
            case CardStatus.TERMINE:
                return t('status.done');
            default:
                return status;
        }
    };

    return {
        getPriorityLabel,
        getStatusLabel
    };
};
import { useCallback } from 'react';
import { toast as sonnerToast } from 'sonner';

interface ToastOptions {
    title: string;
    description?: string;
    variant?: 'default' | 'destructive' | 'success' | 'warning';
}

export const useToast = () => {
    const toast = useCallback(({ title, description, variant = 'default' }: ToastOptions): void => {
        const message = description ? `${title} - ${description}` : title;

        switch (variant) {
            case 'success':
                sonnerToast.success(message);
                break;
            case 'destructive':
                sonnerToast.error(message);
                break;
            case 'warning':
                sonnerToast.warning(message);
                break;
            default:
                sonnerToast(message);
                break;
        }
    }, []);

    const dismiss = useCallback((id?: string) => {
        // Sonner exposes a dismiss function that can dismiss by id or all
        sonnerToast.dismiss(id as any);
    }, []);

    return {
        toast,
        dismiss,
    };
};
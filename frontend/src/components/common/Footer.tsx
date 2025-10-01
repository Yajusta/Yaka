import { useTranslation } from 'react-i18next';

export const Footer = () => {
    const { t } = useTranslation();
    return (
        <footer className="mt-auto border-border/50 bg-background">
            <div className="px-4 sm:px-6 lg:px-8 py-4">
                <div className="flex items-center justify-center">
                    <p className="text-sm text-muted-foreground">
                        {t('footer.poweredBy')} <span className="font-semibold text-primary"><a href="https://yaka.yajusta.fr" target="_blank" className="inline-flex items-center gap-1 hover:text-primary/80 transition-colors">Yaka (Yet Another Kanban App)</a></span>
                    </p>
                </div>
            </div>
        </footer>
    );
};
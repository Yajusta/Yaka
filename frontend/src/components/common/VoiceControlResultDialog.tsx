import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { VoiceControlResponse } from '../../services/voiceControlApi';

interface VoiceControlResultDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    result: VoiceControlResponse | null;
}

export const VoiceControlResultDialog = ({ open, onOpenChange, result }: VoiceControlResultDialogProps) => {
    const { t } = useTranslation();

    if (!result) {
        return null;
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>{t('voice.resultTitle')}</DialogTitle>
                    <DialogDescription>
                        {t('voice.resultDescription')}
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    {/* Affichage du résultat brut pour l'instant */}
                    <div className="bg-muted/50 rounded-lg p-4">
                        <pre className="text-sm whitespace-pre-wrap overflow-auto max-h-[400px]">
                            {JSON.stringify(result, null, 2)}
                        </pre>
                    </div>

                    {/* Bouton de fermeture */}
                    <div className="flex justify-end">
                        <Button
                            onClick={() => onOpenChange(false)}
                            variant="outline"
                        >
                            <X className="h-4 w-4 mr-2" />
                            {t('common.close')}
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
};

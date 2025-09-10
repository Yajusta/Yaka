import { useState, FormEvent, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth.tsx';
import { authService, boardSettingsService } from '../../services/api.tsx';
import { Button } from '../ui/button.tsx';
import { Input } from '../ui/input.tsx';
import { Label } from '../ui/label.tsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card.tsx';
import { Alert, AlertDescription } from '../ui/alert.tsx';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog.tsx';
import { Loader2, AlertTriangle, Eye, Trash } from 'lucide-react';
import { Footer } from '../common/Footer.tsx';
import LanguageSelector from '../common/LanguageSelector.tsx';
import { useTranslation } from 'react-i18next';

// Déclaration pour les variables globales injectées par nginx
declare global {
    interface Window {
        DEMO_MODE: string;
    }
}

const LoginForm = () => {
    const { t } = useTranslation();
    const [email, setEmail] = useState<string>('');
    const [password, setPassword] = useState<string>('');
    const [error, setError] = useState<string>('');
    const [loading, setLoading] = useState<boolean>(false);
    const [resetEmail, setResetEmail] = useState<string>('');
    const [resetLoading, setResetLoading] = useState<boolean>(false);
    const [resetSuccess, setResetSuccess] = useState<boolean>(false);
    const [resetError, setResetError] = useState<string>('');
    const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
    const [boardTitle, setBoardTitle] = useState<string>('Yaka (Yet Another Kanban App)');
    const { login } = useAuth();

    useEffect(() => {
        // Charger le fichier de configuration demo de manière sécurisée
        fetch('/demo-config.js')
            .then(response => response.text())
            .then(script => {
                // Parser le script pour extraire la valeur DEMO_MODE sans utiliser eval
                const match = script.match(/window\.DEMO_MODE\s*=\s*['"]([^'"]*)['"]/);
                const demoMode = match ? match[1] === 'true' : false;
                setIsDemoMode(demoMode);
            })
            .catch(_error => {
                setIsDemoMode(false);
            });

        // Récupérer le titre du board
        boardSettingsService.getBoardTitle()
            .then(data => {
                setBoardTitle(data.title);
            })
            .catch(_error => {
                setBoardTitle('Yaka (Yet Another Kanban App)');
            });
    }, []);

    const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await login(email, password);
        } catch (error: any) {
            setError(error.response?.data?.detail || t('auth.loginError'));
        } finally {
            setLoading(false);
        }
    };

    const handlePasswordReset = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
        e.preventDefault();
        setResetError('');
        setResetLoading(true);

        try {
            await authService.requestPasswordReset(resetEmail);
            setResetSuccess(true);
        } catch (error: any) {
            setResetError(error.response?.data?.detail || t('auth.resetPasswordError'));
        } finally {
            setResetLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            {/* Language selector en haut à droite */}
            <div className="absolute top-4 right-4">
                <LanguageSelector />
            </div>

            {/* Logo et titre du board */}
            <div className="flex flex-col items-center mb-6">
                <img
                    src="/yaka.svg"
                    alt="Logo Yaka"
                    className="h-32 w-32 mb-3"
                />
                <h1 className="text-3xl font-bold text-gray-900 mb-4">
                    {boardTitle}
                </h1>
            </div>

            <div className="flex-1 flex items-center justify-center">
                <Card className="w-full max-w-md">
                    <CardHeader className="space-y-1">
                        <CardTitle className="text-2xl text-center">{t('auth.login')}</CardTitle>
                        <CardDescription className="text-center">
                            {t('auth.connectToAccount')}
                        </CardDescription>
                        {isDemoMode && (
                            <div className="mt-4 space-y-3">
                                {/* Message principal avec icône */}
                                <div className="p-4 bg-amber-50 border border-amber-200 rounded-md">
                                    <div className="flex items-start gap-2">
                                        <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                                        <div>
                                            <div className="text-amber-800 text-sm font-medium">
                                                🔄 {t('auth.demoModeEnabled')}
                                            </div>
                                            <div className="text-amber-700 text-sm mt-1">
                                                {t('auth.email')} : <strong>admin@yaka.local</strong><br />
                                                {t('auth.password')} : <strong>admin123</strong>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Avertissement base de données */}
                                <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
                                    <Trash className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                                    <div className="text-red-700 text-sm">
                                        <strong>{t('auth.databaseDeletedRegularly')}</strong><br />
                                        {t('auth.dataResetHourly')}
                                    </div>
                                </div>

                                {/* Avertissement environnement public */}
                                <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
                                    <Eye className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                                    <div className="text-red-700 text-sm">
                                        <strong>{t('auth.publicEnvironment')}</strong><br />
                                        {t('auth.noSensitiveInfo')}
                                    </div>
                                </div>
                            </div>
                        )}
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {error && (
                                <Alert variant="destructive">
                                    <AlertDescription>{error}</AlertDescription>
                                </Alert>
                            )}

                            <div className="space-y-2">
                                <Label htmlFor="email">{t('auth.email')}</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    placeholder="admin@yaka.local"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="password">{t('auth.password')}</Label>
                                <Input
                                    id="password"
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    placeholder="••••••••"
                                />
                            </div>

                            <Button type="submit" className="w-full" disabled={loading}>
                                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                {t('auth.login')}
                            </Button>
                        </form>

                        <div className="mt-4 text-center">
                            <Dialog>
                                <DialogTrigger asChild>
                                    <Button variant="link" className="text-sm">
                                        {t('auth.forgotPassword')}
                                    </Button>
                                </DialogTrigger>
                                <DialogContent>
                                    <DialogHeader>
                                        <DialogTitle>{t('auth.resetPasswordDialogTitle')}</DialogTitle>
                                        <DialogDescription>
                                            {t('auth.resetPasswordDialogDescription')}
                                        </DialogDescription>
                                    </DialogHeader>

                                    {resetSuccess ? (
                                        <div className="text-center py-4">
                                            <Alert>
                                                <AlertDescription>
                                                    {t('auth.resetPasswordSuccess')}
                                                </AlertDescription>
                                            </Alert>
                                        </div>
                                    ) : (
                                        <form onSubmit={handlePasswordReset} className="space-y-4">
                                            {resetError && (
                                                <Alert variant="destructive">
                                                    <AlertDescription>{resetError}</AlertDescription>
                                                </Alert>
                                            )}

                                            <div className="space-y-2">
                                                <Label htmlFor="resetEmail">{t('auth.email')}</Label>
                                                <Input
                                                    id="resetEmail"
                                                    type="email"
                                                    value={resetEmail}
                                                    onChange={(e) => setResetEmail(e.target.value)}
                                                    required
                                                    placeholder={t('auth.emailPlaceholder')}
                                                />
                                            </div>

                                            <Button type="submit" className="w-full" disabled={resetLoading}>
                                                {resetLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                                {t('auth.sendResetLink')}
                                            </Button>
                                        </form>
                                    )}
                                </DialogContent>
                            </Dialog>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Footer */}
            <Footer />
        </div>
    );
};

export default LoginForm; 
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams, useNavigate } from 'react-router-dom';
import api from '../../services/api.tsx';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Alert, AlertDescription } from '../ui/alert';
import { Eye, EyeOff, Lock, Mail } from 'lucide-react';
import LanguageSelector from '../common/LanguageSelector.tsx';

const InvitePage = () => {
    const { t } = useTranslation();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    const token = searchParams.get('token');
    const isResetPassword = searchParams.get('reset') === 'true';

    useEffect(() => {
        if (!token) {
            setError(t('invite.missingToken'));
        }
    }, [token]);

    const validatePassword = (pwd: string): string | null => {
        if (pwd.length < 8) {
            return t('invite.passwordTooShort');
        }
        if (!/(?=.*[a-z])/.test(pwd)) {
            return t('invite.passwordMissingLowercase');
        }
        if (!/(?=.*[A-Z])/.test(pwd)) {
            return t('invite.passwordMissingUppercase');
        }
        if (!/(?=.*\d)/.test(pwd)) {
            return t('invite.passwordMissingNumber');
        }
        return null;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();


        if (!token) {
            setError(t('invite.missingToken'));
            return;
        }

        if (password !== confirmPassword) {
            setError(t('invite.passwordsDoNotMatch'));
            return;
        }

        const passwordError = validatePassword(password);
        if (passwordError) {
            setError(passwordError);
            return;
        }

        setLoading(true);
        setError('');

        try {
            // Utiliser directement l'API si authService ne fonctionne pas
            await api.post('/users/set-password', {
                token,
                password
            });
            setSuccess(true);

            // Rediriger vers la page de connexion après 5 secondes
            setTimeout(() => {
                navigate('/login');
            }, 5 * 1000);
        } catch (err: any) {
            console.error('Erreur lors de la définition du mot de passe:', err);
            setError(err?.response?.data?.detail || t('invite.setPasswordError'));
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-muted/20">
                {/* Language selector en haut à droite */}
                <div className="absolute top-4 right-4">
                    <LanguageSelector />
                </div>
                <Card className="w-full max-w-md">
                    <CardHeader className="text-center">
                        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
                            <Mail className="h-6 w-6 text-green-600 dark:text-green-400" />
                        </div>
                        <CardTitle className="text-2xl font-bold">{t('invite.passwordSetSuccess')}</CardTitle>
                        <CardDescription>
                            {t('invite.passwordSetSuccessDescription')}
                        </CardDescription>
                    </CardHeader>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-muted/20">
            {/* Language selector en haut à droite */}
            <div className="absolute top-4 right-4">
                <LanguageSelector />
            </div>
            <Card className="w-full max-w-md">
                <CardHeader className="text-center">
                    <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                        <Lock className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle className="text-2xl font-bold">
                        {isResetPassword ? t('invite.resetPassword') : t('invite.setPassword')}
                    </CardTitle>
                    <CardDescription>
                        {isResetPassword
                            ? t('invite.resetPasswordDescription')
                            : t('invite.setPasswordDescription')
                        }
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        {error && (
                            <Alert variant="destructive">
                                <AlertDescription>{error}</AlertDescription>
                            </Alert>
                        )}

                        <div className="space-y-2">
                            <label htmlFor="password" className="text-sm font-medium">
                                {t('invite.newPassword')}
                            </label>
                            <div className="relative">
                                <Input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    required
                                    className="pr-10"
                                />
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                    onClick={() => setShowPassword(!showPassword)}
                                >
                                    {showPassword ? (
                                        <EyeOff className="h-4 w-4" />
                                    ) : (
                                        <Eye className="h-4 w-4" />
                                    )}
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label htmlFor="confirmPassword" className="text-sm font-medium">
                                {t('invite.confirmPassword')}
                            </label>
                            <div className="relative">
                                <Input
                                    id="confirmPassword"
                                    type={showConfirmPassword ? 'text' : 'password'}
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    placeholder="••••••••"
                                    required
                                    className="pr-10"
                                />
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                >
                                    {showConfirmPassword ? (
                                        <EyeOff className="h-4 w-4" />
                                    ) : (
                                        <Eye className="h-4 w-4" />
                                    )}
                                </Button>
                            </div>
                        </div>

                        <div className="text-xs text-muted-foreground space-y-1">
                            <p>{t('invite.passwordRequirements')}</p>
                            <ul className="list-disc list-inside space-y-1 ml-2">
                                <li>{t('invite.passwordMinLength')}</li>
                                <li>{t('invite.passwordLowercase')}</li>
                                <li>{t('invite.passwordUppercase')}</li>
                                <li>{t('invite.passwordNumber')}</li>
                            </ul>
                        </div>

                        <Button
                            type="submit"
                            className="w-full"
                            disabled={loading || !token}
                        >
                            {loading ? (
                                <div className="flex items-center space-x-2">
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                    <span>{t('invite.settingPassword')}</span>
                                </div>
                            ) : (
                                t('invite.setPasswordButton')
                            )}
                        </Button>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
};

export default InvitePage;
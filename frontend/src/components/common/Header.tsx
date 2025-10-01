import { Button } from '../ui/button';

import { List, LogOut, Moon, Palette, Settings, Sun, Tag, User, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useBoardSettings } from '../../hooks/useBoardSettingsContext';
import { UserRole, UserRoleValue } from '../../types';
import { Avatar, AvatarFallback } from '../ui/avatar';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger
} from '../ui/dropdown-menu';
import { GlassmorphicCard } from '../ui/GlassmorphicCard';
import LanguageSelector from './LanguageSelector';

interface User {
    id: number;
    display_name?: string;
    email: string;
    role?: UserRoleValue;
}

interface HeaderProps {
    user: User;
    theme: 'light' | 'dark';
    onShowUsers: () => void;
    onShowLabels: () => void;
    onShowLists: () => void;
    onShowInterface: () => void;
    onToggleTheme: () => void;
    onLogout: () => void;
}

export const Header = ({
    user,
    theme,
    onShowUsers,
    onShowLabels,
    onShowLists,
    onShowInterface,
    onToggleTheme,
    onLogout
}: HeaderProps) => {
    const { boardTitle, loading } = useBoardSettings();
    const { t } = useTranslation();

    const getUserInitials = (): string => {
        if (!user) {
            return 'U';
        }
        const name = user.display_name || user.email;
        return `${name.split(' ')[0]?.[0] || ''}${name.split(' ')[1]?.[0] || ''}`.toUpperCase();
    };

    const getRoleLabel = (role?: UserRoleValue) => {
        switch (role) {
            case UserRole.ADMIN:
                return t('role.admin');
            case UserRole.SUPERVISOR:
                return t('role.supervisor');
            case UserRole.EDITOR:
                return t('role.editor');
            case UserRole.CONTRIBUTOR:
                return t('role.contributor');
            case UserRole.COMMENTER:
                return t('role.commenter');
            case UserRole.VISITOR:
                return t('role.visitor');
            default:
                return t('role.visitor');
        }
    };

    const getRoleIndicatorClass = (role?: UserRoleValue) => {
        switch (role) {
            case UserRole.ADMIN:
                return 'bg-green-500';
            case UserRole.SUPERVISOR:
                return 'bg-cyan-500';
            case UserRole.EDITOR:
                return 'bg-blue-500';
            case UserRole.CONTRIBUTOR:
                return 'bg-amber-500';
            case UserRole.COMMENTER:
                return 'bg-purple-500';
            case UserRole.VISITOR:
                return 'bg-gray-500';
            default:
                return 'bg-gray-500';
        }
    };

    const isAdmin = (): boolean => user?.role === UserRole.ADMIN;

    return (
        <GlassmorphicCard className="border-b border-border/50 rounded-none shadow-sm py-0">
            <div className="px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <div className="flex items-center space-x-3">
                        <img
                            src="/yaka.svg"
                            alt="Yaka Logo"
                            className="w-16 h-16"
                        />
                    </div>

                    {/* Centered title */}
                    <div className="flex-1 text-center">
                        <h1 className="text-xl font-bold text-foreground">
                            {loading ? 'Yaka (Yet Another Kanban App)' : (boardTitle || 'Yaka (Yet Another Kanban App)')}
                        </h1>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center space-x-3">
                        {/* Admin actions */}
                        {isAdmin() && (
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="bg-background/50 border-border/50 hover:bg-background"
                                        title={t('settings.admin')}
                                    >
                                        <Settings className="h-4 w-4" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="w-48">
                                    <DropdownMenuItem onClick={onShowInterface}>
                                        <Palette className="h-4 w-4 mr-2" />
                                        {t('settings.interface')}
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={onShowUsers}>
                                        <Users className="h-4 w-4 mr-2" />
                                        {t('navigation.users')}
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={onShowLists}>
                                        <List className="h-4 w-4 mr-2" />
                                        {t('navigation.lists')}
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={onShowLabels}>
                                        <Tag className="h-4 w-4 mr-2" />
                                        {t('navigation.labels')}
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        )}

                        {/* Language selector */}
                        <LanguageSelector />

                        {/* Theme toggle */}
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onToggleTheme}
                            className="h-9 w-9 p-0 hover:bg-primary/10"
                            title={t('settings.theme')}
                        >
                            {theme === 'light' ? (
                                <Moon className="h-4 w-4" />
                            ) : (
                                <Sun className="h-4 w-4" />
                            )}
                        </Button>


                        {/* User menu */}
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                                    <Avatar className="h-9 w-9 border-2 border-primary/20">
                                        <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                                            {getUserInitials()}
                                        </AvatarFallback>
                                    </Avatar>
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent className="w-64" align="end" forceMount>
                                <div className="flex items-center justify-start gap-2 p-3">
                                    <Avatar className="h-10 w-10 border border-border/50">
                                        <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                                            {getUserInitials()}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="flex flex-col space-y-1 leading-none">
                                        <p className="font-medium text-sm">{user?.display_name || ''}</p>
                                        <p className="w-[180px] truncate text-xs text-muted-foreground">
                                            {user?.email}
                                        </p>
                                        <div className="flex items-center mt-1">
                                            <div className={`w-2 h-2 rounded-full mr-2 ${getRoleIndicatorClass(user?.role)}
                                                `} />
                                            <p className="text-xs text-muted-foreground">
                                                {getRoleLabel(user?.role)}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={onLogout} className="text-destructive focus:text-destructive">
                                    <LogOut className="mr-2 h-4 w-4" />
                                    <span>{t('auth.logout')}</span>
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                </div>
            </div>
        </GlassmorphicCard>
    );
}; 
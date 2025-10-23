import { Button } from '../ui/button';
import * as React from 'react';
import { BookOpen, Check, ChevronDown, ChevronLeft, Download, Eye, FileSpreadsheet, FileText, Languages, List, LogOut, Moon, MoreHorizontal, Palette, Settings, ShieldCheck, Sun, Tag, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useBoardSettings } from '@shared/hooks/useBoardSettingsContext';
import { UserRole, UserRoleValue, User, ViewScope } from '@shared/types';
import { Avatar, AvatarFallback } from '../ui/avatar';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuSub,
    DropdownMenuSubContent,
    DropdownMenuSubTrigger,
    DropdownMenuTrigger
} from '../ui/dropdown-menu';
import { GlassmorphicCard } from '../ui/GlassmorphicCard';
import { DisplayMode } from '@shared/hooks/useDisplayMode';
import { cn } from '@shared/lib/utils';
import { exportApi } from '@shared/services/exportApi';
import { useToast } from '@shared/hooks/use-toast';
import { authService, userService } from '@shared/services/api';

interface HeaderProps {
    user: User;
    theme: 'light' | 'dark';
    onShowUsers: () => void;
    onShowLabels: () => void;
    onShowGlobalDictionary: () => void;
    onShowPersonalDictionary: () => void;
    onShowLists: () => void;
    onShowInterface: () => void;
    onToggleTheme: () => void;
    onLogout: () => void;
    displayMode?: DisplayMode;
    onDisplayModeChange?: (mode: DisplayMode) => void;
}

export const Header = ({
    user,
    theme,
    onShowUsers,
    onShowLabels,
    onShowGlobalDictionary,
    onShowPersonalDictionary,
    onShowLists,
    onShowInterface,
    onToggleTheme,
    onLogout,
    displayMode = 'extended',
    onDisplayModeChange
}: HeaderProps) => {
    const { boardTitle, loading } = useBoardSettings();
    const { t, i18n } = useTranslation();
    const { toast } = useToast();
    const [isLanguageMenuHovered, setIsLanguageMenuHovered] = React.useState(false);
    const [isDisplayMenuHovered, setIsDisplayMenuHovered] = React.useState(false);
    const [isThemeMenuHovered, setIsThemeMenuHovered] = React.useState(false);
    const [isExportMenuHovered, setIsExportMenuHovered] = React.useState(false);
    const [isSettingsMenuHovered, setIsSettingsMenuHovered] = React.useState(false);
    const [isPersonalDictionaryHovered, setIsPersonalDictionaryHovered] = React.useState(false);
    const [isChangingLanguage, setIsChangingLanguage] = React.useState(false);
    const [isUserSettingsExpanded, setIsUserSettingsExpanded] = React.useState(false);

    const handleExportCSV = async () => {
        try {
            const filename = await exportApi.exportCSV();
            toast({
                title: t('export.success'),
                description: t('export.csvDownloaded', { filename }),
            });
        } catch (error: any) {
            toast({
                title: t('export.error'),
                description: error.message || t('export.errorMessage'),
                variant: 'destructive',
            });
        }
    };

    const handleExportExcel = async () => {
        try {
            const filename = await exportApi.exportExcel();
            toast({
                title: t('export.success'),
                description: t('export.excelDownloaded', { filename }),
            });
        } catch (error: any) {
            toast({
                title: t('export.error'),
                description: error.message || t('export.errorMessage'),
                variant: 'destructive',
            });
        }
    };

    const handleChangeLanguage = async (lng: string) => {
        setIsChangingLanguage(true);
        try {
            // Change language in i18next
            await i18n.changeLanguage(lng);

            // Check if user is authenticated
            if (authService.isAuthenticated()) {
                try {
                    // Update language in database
                    await userService.updateLanguage(lng);

                    // Update user in localStorage
                    const currentUser = authService.getCurrentUserFromStorage();
                    if (currentUser) {
                        const updatedUser = { ...currentUser, language: lng };
                        authService.setCurrentUserToStorage(updatedUser);
                    }
                } catch (error) {
                    console.error('Failed to update language in database:', error);
                    // Don't revert the language change, just log the error
                }
            }
        } catch (error) {
            console.error('Failed to change language:', error);
        } finally {
            setIsChangingLanguage(false);
        }
    };

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

    const getViewScopeLabel = (viewScope?: ViewScope) => {
        switch (viewScope) {
            case ViewScope.ALL:
                return t('viewScope.all');
            case ViewScope.UNASSIGNED_PLUS_MINE:
                return t('viewScope.unassigned_plus_mine');
            case ViewScope.MINE_ONLY:
                return t('viewScope.mine_only');
            default:
                return t('viewScope.all');
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
        <GlassmorphicCard className="border-b border-border/50 !rounded-none shadow-sm py-0 w-full">
            <div className="px-2 sm:px-4 md:px-6 lg:px-8 w-full">
                <div className="flex items-center justify-between h-16 w-full">
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
                                        <div className="flex items-center mt-1">
                                            <Eye className="w-3 h-3 mr-2 text-muted-foreground" />
                                            <p className="text-xs text-muted-foreground">
                                                {getViewScopeLabel(user?.view_scope)}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                                <DropdownMenuSeparator />

                                {/* Export submenu */}
                                <DropdownMenuSub>
                                    <DropdownMenuSubTrigger
                                        className="cursor-pointer [&>svg:last-child]:hidden [&_svg:not([class*='text-'])]:text-muted-foreground"
                                        onMouseEnter={() => setIsExportMenuHovered(true)}
                                        onMouseLeave={() => setIsExportMenuHovered(false)}
                                    >
                                        {isExportMenuHovered ? (
                                            <ChevronLeft className="mr-2 h-4 w-4" />
                                        ) : (
                                            <Download className="mr-2 h-4 w-4" />
                                        )}
                                        <span>{t('export.title')}</span>
                                    </DropdownMenuSubTrigger>
                                    <DropdownMenuSubContent
                                        onMouseEnter={() => setIsExportMenuHovered(true)}
                                        onMouseLeave={() => setIsExportMenuHovered(false)}
                                    >
                                        <DropdownMenuItem
                                            onClick={handleExportCSV}
                                            className="cursor-pointer"
                                        >
                                            <FileText className="mr-2 h-4 w-4" />
                                            {t('export.csv')}
                                        </DropdownMenuItem>
                                        <DropdownMenuItem
                                            onClick={handleExportExcel}
                                            className="cursor-pointer"
                                        >
                                            <FileSpreadsheet className="mr-2 h-4 w-4" />
                                            {t('export.excel')}
                                        </DropdownMenuItem>
                                    </DropdownMenuSubContent>
                                </DropdownMenuSub>

                                {/* User Settings - Collapsible menu */}
                                <DropdownMenuItem
                                    onClick={(e) => {
                                        e.preventDefault();
                                        setIsUserSettingsExpanded(!isUserSettingsExpanded);
                                    }}
                                    onSelect={(e) => {
                                        e.preventDefault();
                                    }}
                                    className="cursor-pointer gap-2"
                                >
                                    <Settings className="h-4 w-4" />
                                    <span>{t('settings.userSettings')}</span>
                                    <ChevronDown className={cn(
                                        "ml-auto h-4 w-4 transition-transform",
                                        isUserSettingsExpanded && "rotate-180"
                                    )} />
                                </DropdownMenuItem>

                                {/* Collapsible settings items */}
                                {isUserSettingsExpanded && (
                                    <>
                                        {/* Language submenu */}
                                        <DropdownMenuSub>
                                            <DropdownMenuSubTrigger
                                                className="cursor-pointer [&>svg:last-child]:hidden [&_svg:not([class*='text-'])]:text-muted-foreground pl-8"
                                                onMouseEnter={() => setIsLanguageMenuHovered(true)}
                                                onMouseLeave={() => setIsLanguageMenuHovered(false)}
                                            >
                                                {isLanguageMenuHovered ? (
                                                    <ChevronLeft className="mr-2 h-4 w-4" />
                                                ) : (
                                                    <Languages className="mr-2 h-4 w-4" />
                                                )}
                                                <span>{t('language.switchLanguage')}</span>
                                            </DropdownMenuSubTrigger>
                                            <DropdownMenuSubContent
                                                onMouseEnter={() => setIsLanguageMenuHovered(true)}
                                                onMouseLeave={() => setIsLanguageMenuHovered(false)}
                                            >
                                                <DropdownMenuItem
                                                    onClick={() => handleChangeLanguage('fr')}
                                                    disabled={isChangingLanguage}
                                                    className={cn(
                                                        "cursor-pointer",
                                                        i18n.language === 'fr' && "bg-primary/10 text-primary font-medium"
                                                    )}
                                                >
                                                    <span className="mr-2">🇫🇷</span>
                                                    Français
                                                    {i18n.language === 'fr' && <Check className="ml-auto h-4 w-4" />}
                                                </DropdownMenuItem>
                                                <DropdownMenuItem
                                                    onClick={() => handleChangeLanguage('en')}
                                                    disabled={isChangingLanguage}
                                                    className={cn(
                                                        "cursor-pointer",
                                                        i18n.language === 'en' && "bg-primary/10 text-primary font-medium"
                                                    )}
                                                >
                                                    <span className="mr-2">🇬🇧</span>
                                                    English
                                                    {i18n.language === 'en' && <Check className="ml-auto h-4 w-4" />}
                                                </DropdownMenuItem>
                                            </DropdownMenuSubContent>
                                        </DropdownMenuSub>

                                        {/* Display mode submenu */}
                                        {onDisplayModeChange && (
                                            <DropdownMenuSub>
                                                <DropdownMenuSubTrigger
                                                    className="cursor-pointer [&>svg:last-child]:hidden [&_svg:not([class*='text-'])]:text-muted-foreground pl-8"
                                                    onMouseEnter={() => setIsDisplayMenuHovered(true)}
                                                    onMouseLeave={() => setIsDisplayMenuHovered(false)}
                                                >
                                                    {isDisplayMenuHovered ? (
                                                        <ChevronLeft className="mr-2 h-4 w-4" />
                                                    ) : (
                                                        <Eye className="mr-2 h-4 w-4" />
                                                    )}
                                                    <span>{t('display.title')}</span>
                                                </DropdownMenuSubTrigger>
                                                <DropdownMenuSubContent
                                                    onMouseEnter={() => setIsDisplayMenuHovered(true)}
                                                    onMouseLeave={() => setIsDisplayMenuHovered(false)}
                                                >
                                                    <DropdownMenuItem
                                                        onClick={() => onDisplayModeChange('extended')}
                                                        className={cn(
                                                            "cursor-pointer",
                                                            displayMode === 'extended' && "bg-primary/10 text-primary font-medium"
                                                        )}
                                                    >
                                                        {t('display.extended')}
                                                        {displayMode === 'extended' && <Check className="ml-auto h-4 w-4" />}
                                                    </DropdownMenuItem>
                                                    <DropdownMenuItem
                                                        onClick={() => onDisplayModeChange('compact')}
                                                        className={cn(
                                                            "cursor-pointer",
                                                            displayMode === 'compact' && "bg-primary/10 text-primary font-medium"
                                                        )}
                                                    >
                                                        {t('display.compact')}
                                                        {displayMode === 'compact' && <Check className="ml-auto h-4 w-4" />}
                                                    </DropdownMenuItem>
                                                </DropdownMenuSubContent>
                                            </DropdownMenuSub>
                                        )}

                                        {/* Theme submenu */}
                                        <DropdownMenuSub>
                                            <DropdownMenuSubTrigger
                                                className="cursor-pointer [&>svg:last-child]:hidden [&_svg:not([class*='text-'])]:text-muted-foreground pl-8"
                                                onMouseEnter={() => setIsThemeMenuHovered(true)}
                                                onMouseLeave={() => setIsThemeMenuHovered(false)}
                                            >
                                                {isThemeMenuHovered ? (
                                                    <ChevronLeft className="mr-2 h-4 w-4" />
                                                ) : (
                                                    <Palette className="mr-2 h-4 w-4" />
                                                )}
                                                <span>{t('settings.theme')}</span>
                                            </DropdownMenuSubTrigger>
                                            <DropdownMenuSubContent
                                                onMouseEnter={() => setIsThemeMenuHovered(true)}
                                                onMouseLeave={() => setIsThemeMenuHovered(false)}
                                            >
                                                <DropdownMenuItem
                                                    onClick={onToggleTheme}
                                                    className={cn(
                                                        "cursor-pointer",
                                                        theme === 'light' && "bg-primary/10 text-primary font-medium"
                                                    )}
                                                >
                                                    <Sun className="mr-2 h-4 w-4" />
                                                    {t('settings.lightTheme')}
                                                    {theme === 'light' && <Check className="ml-auto h-4 w-4" />}
                                                </DropdownMenuItem>
                                                <DropdownMenuItem
                                                    onClick={onToggleTheme}
                                                    className={cn(
                                                        "cursor-pointer",
                                                        theme === 'dark' && "bg-primary/10 text-primary font-medium"
                                                    )}
                                                >
                                                    <Moon className="mr-2 h-4 w-4" />
                                                    {t('settings.darkTheme')}
                                                    {theme === 'dark' && <Check className="ml-auto h-4 w-4" />}
                                                </DropdownMenuItem>
                                            </DropdownMenuSubContent>
                                        </DropdownMenuSub>

                                        {/* Personal Dictionary Menu Item - available for editors and above */}
                                        {user?.role && (user.role === UserRole.EDITOR || user.role === UserRole.SUPERVISOR || user.role === UserRole.ADMIN) && (
                                            <DropdownMenuItem
                                                onClick={onShowPersonalDictionary}
                                                className="cursor-pointer pl-8"
                                                onMouseEnter={() => setIsPersonalDictionaryHovered(true)}
                                                onMouseLeave={() => setIsPersonalDictionaryHovered(false)}
                                            >
                                                {isPersonalDictionaryHovered ? (
                                                    <MoreHorizontal className="h-4 w-4" />
                                                ) : (
                                                    <BookOpen className="h-4 w-4" />
                                                )}
                                                {t('dictionary.personalDictionary')}
                                            </DropdownMenuItem>
                                        )}
                                    </>
                                )}

                                {/* Settings submenu - Admin only */}
                                {isAdmin() && (
                                    <>
                                        <DropdownMenuSeparator />
                                        <DropdownMenuSub>
                                            <DropdownMenuSubTrigger
                                                className="cursor-pointer [&>svg:last-child]:hidden [&_svg:not([class*='text-'])]:text-muted-foreground"
                                                onMouseEnter={() => setIsSettingsMenuHovered(true)}
                                                onMouseLeave={() => setIsSettingsMenuHovered(false)}
                                            >
                                                {isSettingsMenuHovered ? (
                                                    <ChevronLeft className="mr-2 h-4 w-4" />
                                                ) : (
                                                    <ShieldCheck className="mr-2 h-4 w-4" />
                                                )}
                                                <span>{t('settings.admin')}</span>
                                            </DropdownMenuSubTrigger>
                                            <DropdownMenuSubContent
                                                onMouseEnter={() => setIsSettingsMenuHovered(true)}
                                                onMouseLeave={() => setIsSettingsMenuHovered(false)}
                                            >
                                                <DropdownMenuItem
                                                    onClick={onShowInterface}
                                                    className="cursor-pointer"
                                                >
                                                    <Palette className="mr-2 h-4 w-4" />
                                                    {t('settings.interface')}
                                                    <MoreHorizontal className="ml-auto h-4 w-4 opacity-50" />
                                                </DropdownMenuItem>
                                                <DropdownMenuItem
                                                    onClick={onShowUsers}
                                                    className="cursor-pointer"
                                                >
                                                    <Users className="mr-2 h-4 w-4" />
                                                    {t('navigation.users')}
                                                    <MoreHorizontal className="ml-auto h-4 w-4 opacity-50" />
                                                </DropdownMenuItem>
                                                <DropdownMenuItem
                                                    onClick={onShowLists}
                                                    className="cursor-pointer"
                                                >
                                                    <List className="mr-2 h-4 w-4" />
                                                    {t('navigation.lists')}
                                                    <MoreHorizontal className="ml-auto h-4 w-4 opacity-50" />
                                                </DropdownMenuItem>
                                                <DropdownMenuItem
                                                    onClick={onShowLabels}
                                                    className="cursor-pointer"
                                                >
                                                    <Tag className="mr-2 h-4 w-4" />
                                                    {t('navigation.labels')}
                                                    <MoreHorizontal className="ml-auto h-4 w-4 opacity-50" />
                                                </DropdownMenuItem>
                                                <DropdownMenuItem
                                                    onClick={onShowGlobalDictionary}
                                                    className="cursor-pointer"
                                                >
                                                    <BookOpen className="mr-2 h-4 w-4" />
                                                    {t('dictionary.globalDictionary')}
                                                    <MoreHorizontal className="ml-auto h-4 w-4 opacity-50" />
                                                </DropdownMenuItem>
                                            </DropdownMenuSubContent>
                                        </DropdownMenuSub>
                                    </>
                                )}


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

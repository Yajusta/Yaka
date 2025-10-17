import { Check, Eye, Key, Mail, MessageSquare, MoreHorizontal, PenTool, RefreshCw, Shield, Trash2, User, Users, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useToast } from '../../hooks/use-toast.tsx';
import { useAuth } from '../../hooks/useAuth';
import { AppUser, useUsers } from '../../hooks/useUsers';
import { userService } from '../../services/api';
import { UserRole, UserRoleValue, ViewScope } from '../../types';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSub, DropdownMenuSubContent, DropdownMenuSubTrigger, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';

type UserItem = AppUser;

export default function UsersManager({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
    const { t } = useTranslation();
    const { user: currentUser } = useAuth();
    const { users, loading, forbidden, refresh } = useUsers();
    const [email, setEmail] = useState('');
    const [displayName, setDisplayName] = useState('');
    const [role, setRole] = useState<UserRoleValue>(UserRole.VISITOR);
    const [editingUser, setEditingUser] = useState<UserItem | null>(null);
    const [editingDisplayName, setEditingDisplayName] = useState('');
    const [showAddUserForm, setShowAddUserForm] = useState(false);

    const roleOptions = useMemo(() => ([
        { value: UserRole.VISITOR, label: t('role.visitor') },
        { value: UserRole.COMMENTER, label: t('role.commenter') },
        { value: UserRole.CONTRIBUTOR, label: t('role.contributor') },
        { value: UserRole.EDITOR, label: t('role.editor') },
        { value: UserRole.SUPERVISOR, label: t('role.supervisor') },
        { value: UserRole.ADMIN, label: t('role.admin') },
    ]), [t]);

    const roleLabelMap = useMemo(() => new Map(roleOptions.map(option => [option.value, option.label])), [roleOptions]);

    const getRoleLabel = (value?: string | null): string => {
        if (!value) {
            return t('role.visitor');
        }
        return roleLabelMap.get(value as UserRoleValue) || t('role.visitor');
    };

    const viewScopeOptions = useMemo(() => ([
        { 
            value: ViewScope.MINE_ONLY, 
            label: t('viewScope.mine_only'), 
            description: t('viewScope.description.mine_only'),
            permissions: {
                mine: true,
                unassigned: false,
                others: false
            }
        },
        { 
            value: ViewScope.UNASSIGNED_PLUS_MINE, 
            label: t('viewScope.unassigned_plus_mine'), 
            description: t('viewScope.description.unassigned_plus_mine'),
            permissions: {
                mine: true,
                unassigned: true,
                others: false
            }
        },
        { 
            value: ViewScope.ALL, 
            label: t('viewScope.all'), 
            description: t('viewScope.description.all'),
            permissions: {
                mine: true,
                unassigned: true,
                others: true
            }
        },
    ]), [t]);
    
    const getRoleIcon = (role: UserRoleValue) => {
        switch (role) {
            case UserRole.ADMIN:
                return Key;
            case UserRole.SUPERVISOR:
                return Shield;
            case UserRole.EDITOR:
                return PenTool;
            case UserRole.CONTRIBUTOR:
                return Users;
            case UserRole.COMMENTER:
                return MessageSquare;
            case UserRole.VISITOR:
                return Eye;
            default:
                return User;
        }
    };

    const getRolePermissions = (role: UserRoleValue) => {
        const permissions = {
            view: true,
            comment: false,
            selfAssign: false,
            checkItems: false,
            moveOwn: false,
            createTask: false,
            modifyOwn: false,
            modifyAll: false,
            delete: false,
            admin: false
        };

        switch (role) {
            case UserRole.ADMIN:
                return { ...permissions, comment: true, selfAssign: true, checkItems: true, moveOwn: true, createTask: true, modifyOwn: true, modifyAll: true, delete: true, admin: true };
            case UserRole.SUPERVISOR:
                return { ...permissions, comment: true, selfAssign: true, checkItems: true, moveOwn: true, createTask: true, modifyOwn: true, modifyAll: true, delete: true };
            case UserRole.EDITOR:
                return { ...permissions, comment: true, selfAssign: true, checkItems: true, moveOwn: true, createTask: true, modifyOwn: true };
            case UserRole.CONTRIBUTOR:
                return { ...permissions, comment: true, selfAssign: true, checkItems: true, moveOwn: true };
            case UserRole.COMMENTER:
                return { ...permissions, comment: true };
            case UserRole.VISITOR:
            default:
                return permissions;
        }
    };

    const getViewScopeIcon = (viewScope?: ViewScope | string) => {
        // Icône personnalisée avec 1 trait horizontal
        const OneLine = () => (
            <svg className="h-full w-full" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="4" y1="12" x2="20" y2="12" />
            </svg>
        );
        
        // Icône personnalisée avec 2 traits horizontaux
        const TwoLines = () => (
            <svg className="h-full w-full" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="4" y1="9" x2="20" y2="9" />
                <line x1="4" y1="15" x2="20" y2="15" />
            </svg>
        );
        
        // Icône personnalisée avec 3 traits horizontaux
        const ThreeLines = () => (
            <svg className="h-full w-full" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="4" y1="7" x2="20" y2="7" />
                <line x1="4" y1="12" x2="20" y2="12" />
                <line x1="4" y1="17" x2="20" y2="17" />
            </svg>
        );

        switch (viewScope) {
            case ViewScope.MINE_ONLY:
                return OneLine;
            case ViewScope.UNASSIGNED_PLUS_MINE:
                return TwoLines;
            case ViewScope.ALL:
            default:
                return ThreeLines;
        }
    };

    const getViewScopeLabel = (viewScope?: ViewScope | string): string => {
        const option = viewScopeOptions.find(opt => opt.value === viewScope);
        return option?.label || t('viewScope.all');
    };


    useEffect(() => {
        if (isOpen) {
            refresh();
        }
    }, [isOpen]);

    const [error, setError] = useState<string | null>(null);
    const { toast } = useToast();

    const validateEmail = (e: string) => {
        return /\S+@\S+\.\S+/.test(e);
    };

    const isFormValid = validateEmail(email) && displayName.trim().length > 0;

    const handleInvite = async () => {
        setError(null);
        if (!validateEmail(email)) {
            setError(t('user.invalidEmail'));
            return;
        }
        try {
            await userService.inviteUser({ email, display_name: displayName, role });
            setEmail('');
            setDisplayName('');
            setRole(UserRole.VISITOR);
            setShowAddUserForm(false);
            await refresh();
            toast({
                title: t('user.invitationSent'),
                variant: 'success'
            });
        } catch (e: any) {
            console.error('Erreur invite', e);
            setError(e?.response?.data?.detail || t('user.invitationError'));
            toast({
                title: t('common.error'),
                description: e?.response?.data?.detail || t('user.invitationError'),
                variant: 'destructive'
            });
        }
    };

    const handleCancelAddUser = () => {
        setEmail('');
        setDisplayName('');
        setRole(UserRole.VISITOR);
        setError(null);
        setShowAddUserForm(false);
    };

    const handleDelete = async (id: number) => {
        try {
            await userService.deleteUser(id);
            await refresh();
            toast({
                title: t('user.userDeleted'),
                variant: 'success'
            });
        } catch (e) {
            console.error('Erreur delete', e);
            toast({
                title: t('common.error'),
                description: t('user.deleteUserError'),
                variant: 'destructive'
            });
        }
    };

    const handleResendInvitation = async (userId: number) => {
        try {
            await userService.resendInvitation(userId);
            await refresh();
            toast({
                title: t('user.invitationResent'),
                variant: 'success'
            });
        } catch (e: any) {
            console.error('Erreur resend invitation', e);
            const errorMessage = e?.response?.data?.detail || t('user.invitationError');
            toast({
                title: t('common.error'),
                description: errorMessage,
                variant: 'destructive'
            });
        }
    };

    const handleSaveDisplayName = async () => {
        if (!editingUser || !editingDisplayName.trim()) {
            return;
        }

        try {
            await userService.updateUser(editingUser.id, { display_name: editingDisplayName.trim() });
            await refresh();
            setEditingUser(null);
            setEditingDisplayName('');
            toast({
                title: t('user.nameUpdated'),
                variant: 'success'
            });
        } catch (e: any) {
            console.error('Erreur update user', e);
            const errorMessage = e?.response?.data?.detail || t('user.updateNameError');
            toast({
                title: t('common.error'),
                description: errorMessage,
                variant: 'destructive'
            });
        }
    };

    const handleChangeRole = async (userId: number, newRole: UserRoleValue) => {
        if (userId === currentUser?.id) {
            return;
        }
        const targetUser = users.find((existing) => existing.id === userId);
        if (targetUser?.role === newRole) {
            return;
        }
        try {
            await userService.updateUser(userId, { role: newRole });
            await refresh();
            toast({
                title: t('user.roleUpdated'),
                variant: 'success'
            });
        } catch (e: any) {
            console.error('Erreur update user role', e);
            const errorMessage = e?.response?.data?.detail || t('user.updateRoleError');
            toast({
                title: t('common.error'),
                description: errorMessage,
                variant: 'destructive'
            });
        }
    };

    const handleChangeViewScope = async (userId: number, newViewScope: ViewScope) => {
        const targetUser = users.find((existing) => existing.id === userId);
        if (targetUser?.view_scope === newViewScope) {
            return;
        }
        try {
            await userService.updateViewScope(userId, newViewScope);
            await refresh();
            toast({
                title: 'Périmètre de vue mis à jour',
                variant: 'success'
            });
        } catch (e: any) {
            console.error('Erreur update user view scope', e);
            const errorMessage = e?.response?.data?.detail || 'Erreur lors de la mise à jour du périmètre de vue';
            toast({
                title: t('common.error'),
                description: errorMessage,
                variant: 'destructive'
            });
        }
    };

    const handleCancelEdit = () => {
        setEditingUser(null);
        setEditingDisplayName('');
    };

    const canResendInvitation = (invitedAt?: string): boolean => {
        if (!invitedAt) {
            return true;
        }
        const invitedTime = new Date(invitedAt);
        const now = new Date();
        const diffInMinutes = (now.getTime() - invitedTime.getTime()) / (1000 * 60);
        return diffInMinutes >= 1;
    };

    return (
        <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
            <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col p-0">
                <DialogHeader className="px-6 py-4 border-b">
                    <DialogTitle>{t('user.userManagement')}</DialogTitle>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto px-6 py-4">
                    <div className="space-y-4">
                        <div>
                            <h3 className="font-medium mb-2">{t('user.userList')}</h3>
                            {loading ? (
                                <div className="flex justify-center py-4">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                                </div>
                            ) : forbidden ? (
                                <div className="text-sm text-muted-foreground">{t('user.noPermission')}</div>
                            ) : (
                                <div className="border rounded-lg overflow-hidden">
                                    <div className="grid grid-cols-[1fr_1fr_auto_auto_auto_auto] gap-2 p-3 bg-muted/50 font-medium text-sm">
                                        <div className="min-w-0">{t('user.name')}</div>
                                        <div className="min-w-0">{t('user.email')}</div>
                                        <div></div>
                                        <div></div>
                                        <div></div>
                                        <div></div>
                                    </div>
                                    <div className="divide-y">
                                        <TooltipProvider>
                                            {users.map(u => (
                                                <div key={u.id} className="group grid grid-cols-[1fr_1fr_auto_auto_auto_auto] gap-2 p-3 items-center hover:bg-muted/30">
                                                    <div className="font-medium min-w-0 truncate">
                                                        {u.display_name || t('user.noName')}
                                                    </div>
                                                    <div className="text-sm text-muted-foreground truncate min-w-0">
                                                        {u.email}
                                                    </div>
                                                    <div className="flex justify-center">
                                                        <Tooltip>
                                                            <TooltipTrigger asChild>
                                                                {(() => {
                                                                    const IconComponent = getRoleIcon(u.role as UserRoleValue);
                                                                    return <IconComponent className={`h-4 w-4 cursor-help ${u.role === 'admin' ? 'text-destructive' : 'text-muted-foreground'}`} />;
                                                                })()}
                                                            </TooltipTrigger>
                                                            <TooltipContent>
                                                                <p>{getRoleLabel(u.role)}</p>
                                                            </TooltipContent>
                                                        </Tooltip>
                                                    </div>
                                                    <div className="flex justify-center">
                                                        <Tooltip>
                                                            <TooltipTrigger asChild>
                                                                <div className="h-4 w-4 text-muted-foreground cursor-help">
                                                                    {(() => {
                                                                        const ViewScopeIconComponent = getViewScopeIcon(u.view_scope);
                                                                        return <ViewScopeIconComponent />;
                                                                    })()}
                                                                </div>
                                                            </TooltipTrigger>
                                                            <TooltipContent>
                                                                <p>{getViewScopeLabel(u.view_scope)}</p>
                                                            </TooltipContent>
                                                        </Tooltip>
                                                    </div>
                                                    <div className="flex justify-center">
                                                        <Tooltip>
                                                            <TooltipTrigger asChild>
                                                                {(() => {
                                                                    const status = u.status?.toLowerCase();
                                                                    if (status === 'active') return <Check className="h-4 w-4 text-green-600 cursor-help" />;
                                                                    if (status === 'invited') return <Mail className="h-4 w-4 text-yellow-600 cursor-help" />;
                                                                    return <Check className="h-4 w-4 text-green-600 cursor-help" />;
                                                                })()}
                                                            </TooltipTrigger>
                                                            <TooltipContent>
                                                                <p>{(() => {
                                                                    const status = u.status?.toLowerCase();
                                                                    if (status === 'active') {
                                                                        return t('user.activeUser');
                                                                    }
                                                                    if (status === 'invited') {
                                                                        return t('user.invitationPending');
                                                                    }
                                                                    return t('user.activeUser');
                                                                })()}</p>
                                                            </TooltipContent>
                                                        </Tooltip>
                                                    </div>
                                                    <div className="flex justify-center">
                                                        <DropdownMenu>
                                                            <DropdownMenuTrigger asChild>
                                                                <Button
                                                                    variant="ghost"
                                                                    size="sm"
                                                                    className="h-6 w-6 p-0"
                                                                    title={t('common.actions')}
                                                                >
                                                                    <MoreHorizontal className="h-3 w-3" />
                                                                </Button>
                                                            </DropdownMenuTrigger>
                                                            <DropdownMenuContent align="end" className="w-48">
                                                                {u.status?.toLowerCase() === 'invited' && (
                                                                    <DropdownMenuItem
                                                                        onClick={() => handleResendInvitation(u.id)}
                                                                        disabled={!canResendInvitation(u.invited_at)}
                                                                        className="flex items-center gap-2"
                                                                    >
                                                                        <RefreshCw className="h-4 w-4" />
                                                                        {t('user.resendInvitation')}
                                                                        {!canResendInvitation(u.invited_at) && (
                                                                            <span className="text-xs text-muted-foreground ml-auto">
                                                                                {t('user.availableInMinute')}
                                                                            </span>
                                                                        )}
                                                                    </DropdownMenuItem>
                                                                )}
                                                                <DropdownMenuItem
                                                                    onClick={() => {
                                                                        setEditingUser(u);
                                                                        setEditingDisplayName(u.display_name || '');
                                                                    }}
                                                                    className="flex items-center gap-2"
                                                                >
                                                                    <User className="h-4 w-4" />
                                                                    {t('user.modifyName')}
                                                                </DropdownMenuItem>
                                                                <DropdownMenuSub>
                                                                    <Tooltip>
                                                                        <TooltipTrigger asChild>
                                                                            <DropdownMenuSubTrigger
                                                                                disabled={u.id === currentUser?.id}
                                                                                className={`flex items-center gap-2 ${u.id === currentUser?.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                                                                            >
                                                                                <Key className="h-4 w-4" />
                                                                                <span className="flex-1">{t('user.changeRole')}</span>
                                                                            </DropdownMenuSubTrigger>
                                                                        </TooltipTrigger>
                                                                        {u.id === currentUser?.id && (
                                                                            <TooltipContent>
                                                                                <p>{t('user.cannotChangeOwnRole')}</p>
                                                                            </TooltipContent>
                                                                        )}
                                                                    </Tooltip>
                                                                    <DropdownMenuSubContent className="w-48">
                                                                        {roleOptions.map((option) => {
                                                                            const IconComponent = getRoleIcon(option.value);
                                                                            const perms = getRolePermissions(option.value);
                                                                            return (
                                                                                <Tooltip key={option.value}>
                                                                                    <TooltipTrigger asChild>
                                                                                        <div>
                                                                                            <DropdownMenuItem
                                                                                                onClick={() => handleChangeRole(u.id, option.value)}
                                                                                                disabled={u.id === currentUser?.id || u.role === option.value}
                                                                                                className="flex items-center gap-2"
                                                                                            >
                                                                                                <IconComponent className="h-3.5 w-3.5" />
                                                                                                <span>{option.label}</span>
                                                                                                {u.role === option.value && <Check className="ml-auto h-3.5 w-3.5 text-primary" />}
                                                                                            </DropdownMenuItem>
                                                                                        </div>
                                                                                    </TooltipTrigger>
                                                                                    <TooltipContent side="right" className="p-3 bg-popover border-border">
                                                                                        <div className="flex flex-col gap-y-1 text-xs">
                                                                                            <div className="flex items-center gap-2">
                                                                                                {perms.view ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('permissions.view')}</span>
                                                                                            </div>

                                                                                            <div className="flex items-center gap-2">
                                                                                                {perms.comment ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('permissions.comment')}</span>
                                                                                            </div>

                                                                                            <div className="flex items-center gap-2">
                                                                                                {perms.selfAssign ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('permissions.selfAssign')}</span>
                                                                                            </div>

                                                                                            <div className="flex items-center gap-2">
                                                                                                {perms.checkItems ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('permissions.checkItems')}</span>
                                                                                            </div>

                                                                                            <div className="flex items-center gap-2">
                                                                                                {perms.moveOwn ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('permissions.moveOwn')}</span>
                                                                                            </div>

                                                                                            <div className="flex items-center gap-2">
                                                                                                {perms.createTask ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('permissions.createTask')}</span>
                                                                                            </div>

                                                                                            <div className="flex items-center gap-2">
                                                                                                {perms.modifyOwn ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('permissions.modifyOwn')}</span>
                                                                                            </div>

                                                                                            <div className="flex items-center gap-2">
                                                                                                {perms.modifyAll ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('permissions.modifyAll')}</span>
                                                                                            </div>

                                                                                            <div className="flex items-center gap-2">
                                                                                                {perms.delete ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('permissions.delete')}</span>
                                                                                            </div>

                                                                                            <div className="flex items-center gap-2">
                                                                                                {perms.admin ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('permissions.admin')}</span>
                                                                                            </div>
                                                                                        </div>
                                                                                    </TooltipContent>
                                                                                </Tooltip>
                                                                            );
                                                                        })}
                                                                    </DropdownMenuSubContent>
                                                                </DropdownMenuSub>
                                                                <DropdownMenuSub>
                                                                    <Tooltip>
                                                                        <TooltipTrigger asChild>
                                                                            <DropdownMenuSubTrigger
                                                                                className="flex items-center gap-2"
                                                                            >
                                                                                <Eye className="h-4 w-4" />
                                                                                <span className="flex-1">{t('viewScope.title')}</span>
                                                                            </DropdownMenuSubTrigger>
                                                                        </TooltipTrigger>
                                                                        <TooltipContent>
                                                                            <p>Modifier le périmètre de vue des cartes</p>
                                                                        </TooltipContent>
                                                                    </Tooltip>
                                                                    <DropdownMenuSubContent className="w-64">
                                                                        {viewScopeOptions.map((option) => {
                                                                            const ViewScopeIconComponent = getViewScopeIcon(option.value);
                                                                            return (
                                                                            <Tooltip key={option.value}>
                                                                                <TooltipTrigger asChild>
                                                                                    <div>
                                                                                        <DropdownMenuItem
                                                                                            onClick={() => handleChangeViewScope(u.id, option.value)}
                                                                                            disabled={u.view_scope === option.value}
                                                                                            className="flex items-center gap-2"
                                                                                        >
                                                                                            <div className="h-3.5 w-3.5 flex items-center justify-center">
                                                                                                <ViewScopeIconComponent />
                                                                                            </div>
                                                                                            <span>{option.label}</span>
                                                                                            {u.view_scope === option.value && <Check className="ml-auto h-3.5 w-3.5 text-primary" />}
                                                                                        </DropdownMenuItem>
                                                                                    </div>
                                                                                </TooltipTrigger>
                                                                                <TooltipContent side="right" className="p-3 bg-popover border-border">
                                                                                    <div className="flex flex-col gap-2">
                                                                                        <div className="flex flex-col gap-1">
                                                                                            <div className="flex items-center gap-2 text-xs">
                                                                                                {option.permissions.mine ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('viewScope.permissions.mine')}</span>
                                                                                            </div>
                                                                                            <div className="flex items-center gap-2 text-xs">
                                                                                                {option.permissions.unassigned ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('viewScope.permissions.unassigned')}</span>
                                                                                            </div>
                                                                                            <div className="flex items-center gap-2 text-xs">
                                                                                                {option.permissions.others ? <Check className="h-3 w-3 text-green-600" /> : <X className="h-3 w-3 text-red-600" />}
                                                                                                <span className="text-muted-foreground">{t('viewScope.permissions.others')}</span>
                                                                                            </div>
                                                                                        </div>
                                                                                    </div>
                                                                                </TooltipContent>
                                                                            </Tooltip>
                                                                            );
                                                                        })}
                                                                    </DropdownMenuSubContent>
                                                                </DropdownMenuSub>
                                                                <DropdownMenuItem
                                                                    variant="destructive"
                                                                    onClick={() => {
                                                                        if (u.id === currentUser?.id) return;
                                                                        handleDelete(u.id);
                                                                    }}
                                                                    className={`flex items-center gap-2 ${u.id === currentUser?.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                                                                >
                                                                    <Tooltip>
                                                                        <TooltipTrigger asChild>
                                                                            <div className="flex items-center gap-2 w-full">
                                                                                <Trash2 className="h-4 w-4" />
                                                                                {t('common.delete')}
                                                                            </div>
                                                                        </TooltipTrigger>
                                                                        {u.id === currentUser?.id && (
                                                                            <TooltipContent>
                                                                                <p>{t('user.cannotDeleteSelf')}</p>
                                                                            </TooltipContent>
                                                                        )}
                                                                    </Tooltip>
                                                                </DropdownMenuItem>
                                                            </DropdownMenuContent>
                                                        </DropdownMenu>
                                                    </div>
                                                </div>
                                            ))}
                                        </TooltipProvider>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Add User Button or Form */}
                        {!showAddUserForm ? (
                            <div className="flex justify-start">
                                <Button onClick={() => setShowAddUserForm(true)} variant="outline">
                                    {t('user.addNewUser')}
                                </Button>
                            </div>
                        ) : (
                            <div className="border rounded-lg p-4">
                                <h3 className="font-medium text-sm mb-3">{t('user.addNewUser')}</h3>
                                <div className="grid gap-3">
                                    <div className="space-y-1">
                                        <Label htmlFor="email" className="text-sm font-medium">
                                            {t('user.email')} <span className="text-red-500">*</span>
                                        </Label>
                                        <Input
                                            id="email"
                                            value={email}
                                            onChange={(e) => setEmail((e.target as HTMLInputElement).value)}
                                            placeholder={t('user.email')}
                                        />
                                    </div>
                                    <div className="space-y-1">
                                        <Label htmlFor="displayName" className="text-sm font-medium">
                                            {t('user.name')} <span className="text-red-500">*</span>
                                        </Label>
                                        <Input
                                            id="displayName"
                                            value={displayName}
                                            onChange={(e) => setDisplayName((e.target as HTMLInputElement).value)}
                                            placeholder={t('user.name')}
                                            maxLength={32}
                                        />
                                        <p className="text-xs text-gray-500">
                                            {displayName.length}/32 {t('common.charactersMax')}
                                        </p>
                                    </div>
                                    <div className="space-y-1">
                                        <Label htmlFor="roleSelect" className="text-sm font-medium">
                                            {t('user.role')}
                                        </Label>
                                        <select
                                            id="roleSelect"
                                            value={role}
                                            onChange={(e) => setRole((e.target as HTMLSelectElement).value as UserRoleValue)}
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                                        >
                                            {roleOptions.map((option) => (
                                                <option key={option.value} value={option.value}>
                                                    {option.label}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    {error && <div className="text-sm text-destructive">{error}</div>}
                                    <div className="flex items-center gap-2">
                                        <Button onClick={handleInvite} disabled={!isFormValid}>
                                            {t('user.inviteUser')}
                                        </Button>
                                        <Button onClick={handleCancelAddUser} variant="outline">
                                            {t('common.cancel')}
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Edit Display Name Dialog */}
                        {editingUser && (
                            <div className="border-t pt-4 mt-4">
                                <h3 className="font-medium text-sm mb-3">{t('user.editName', { email: editingUser.email })}</h3>
                                <div className="space-y-3">
                                    <div className="space-y-1">
                                        <Label htmlFor="editDisplayName" className="text-sm font-medium">
                                            {t('user.newDisplayName')} <span className="text-red-500">*</span>
                                        </Label>
                                        <Input
                                            id="editDisplayName"
                                            value={editingDisplayName}
                                            onChange={(e) => setEditingDisplayName(e.target.value)}
                                            placeholder={t('user.newDisplayName')}
                                            maxLength={32}
                                        />
                                        <p className="text-xs text-gray-500">
                                            {editingDisplayName.length}/32 {t('common.charactersMax')}
                                        </p>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <Button
                                            onClick={handleSaveDisplayName}
                                            disabled={!editingDisplayName.trim()}
                                            size="sm"
                                        >
                                            {t('common.save')}
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            onClick={handleCancelEdit}
                                            size="sm"
                                        >
                                            {t('common.cancel')}
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                <DialogFooter className="px-6 py-4 border-t">
                    <Button variant="ghost" onClick={onClose}>{t('common.close')}</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

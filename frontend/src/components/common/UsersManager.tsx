import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { MoreHorizontal, Trash2, User, Key, Check, Mail, RefreshCw } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { userService } from '../../services/api';
import { useToast } from '../../hooks/use-toast.tsx';
import { useAuth } from '../../hooks/useAuth';
import { useUsers, AppUser } from '../../hooks/useUsers';
import { useTranslation } from 'react-i18next';

type UserItem = AppUser;

export default function UsersManager({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
    const { t } = useTranslation();
    const { user: currentUser } = useAuth();
    const { users, loading, forbidden, refresh } = useUsers();
    const [email, setEmail] = useState('');
    const [displayName, setDisplayName] = useState('');
    const [role, setRole] = useState<'user' | 'admin'>('user');
    const [editingUser, setEditingUser] = useState<UserItem | null>(null);
    const [editingDisplayName, setEditingDisplayName] = useState('');

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

    const handleChangeRole = async (userId: number, newRole: 'user' | 'admin') => {
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
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{t('user.userManagement')}</DialogTitle>
                </DialogHeader>

                <div className="space-y-4 mt-4">
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
                                <div className="grid grid-cols-[1fr_1fr_auto_auto_auto] gap-2 p-3 bg-muted/50 font-medium text-sm">
                                    <div className="min-w-0">{t('user.name')}</div>
                                    <div className="min-w-0">{t('user.email')}</div>
                                    <div></div>
                                    <div></div>
                                    <div></div>
                                </div>
                                <div className="divide-y">
                                    <TooltipProvider>
                                        {users.map(u => (
                                            <div key={u.id} className="grid grid-cols-[1fr_1fr_auto_auto_auto] gap-2 p-3 items-center hover:bg-muted/30">
                                                <div className="font-medium min-w-0 truncate">
                                                    {u.display_name || t('user.noName')}
                                                </div>
                                                <div className="text-sm text-muted-foreground truncate min-w-0">
                                                    {u.email}
                                                </div>
                                                <div className="flex justify-center">
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            {u.role === 'admin' ? (
                                                                <Key className="h-4 w-4 text-destructive cursor-help" />
                                                            ) : (
                                                                <User className="h-4 w-4 text-muted-foreground cursor-help" />
                                                            )}
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            <p>{u.role === 'admin' ? t('role.admin') : t('user.member')}</p>
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
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                className="h-6 w-6 p-0 cursor-help"
                                                            >
                                                                <MoreHorizontal className="h-3 w-3" />
                                                            </Button>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            <p>{t('common.actions')}</p>
                                                        </TooltipContent>
                                                    </Tooltip>
                                                    <DropdownMenu>
                                                        <DropdownMenuTrigger asChild>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity absolute"
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
                                                            <DropdownMenuItem
                                                                onClick={() => {
                                                                    if (u.id === currentUser?.id) return;
                                                                    handleChangeRole(u.id, u.role === 'admin' ? 'user' : 'admin');
                                                                }}
                                                                className={`flex items-center gap-2 ${u.id === currentUser?.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                                                            >
                                                                <Tooltip>
                                                                    <TooltipTrigger asChild>
                                                                        <div className="flex items-center gap-2 w-full">
                                                                            <Key className="h-4 w-4" />
                                                                            {u.role === 'admin' ? t('user.demoteToMember') : t('user.promoteToAdmin')}
                                                                        </div>
                                                                    </TooltipTrigger>
                                                                    {u.id === currentUser?.id && (
                                                                        <TooltipContent>
                                                                            <p>{t('user.cannotChangeOwnRole')}</p>
                                                                        </TooltipContent>
                                                                    )}
                                                                </Tooltip>
                                                            </DropdownMenuItem>
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

                    <div>
                        <h3 className="font-medium text-sm">{t('user.addNewUser')}</h3>
                        <div className="grid gap-2 mt-2">
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
                            <div className="space-y-2">
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
                            <select value={role} onChange={(e) => setRole((e.target as HTMLSelectElement).value as any)} className="input">
                                <option value="user">{t('user.member')}</option>
                                <option value="admin">{t('role.admin')}</option>
                            </select>
                            <div className="flex items-center space-x-2">
                                <Button onClick={handleInvite} disabled={!isFormValid}>{t('user.inviteUser')}</Button>
                                {error && <div className="text-sm text-destructive">{error}</div>}
                            </div>
                        </div>
                    </div>

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

                <DialogFooter>
                    <Button variant="ghost" onClick={onClose}>{t('common.close')}</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

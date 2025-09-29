import { MessageSquare, Pencil, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useToast } from '../../hooks/use-toast';
import { useAuth } from '../../hooks/useAuth';
import { cardCommentsService } from '../../services/api';
import { CardComment } from '../../types/index';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Textarea } from '../ui/textarea';

interface CommentsFormProps {
    cardId: number;
    isOpen: boolean;
    onClose: () => void;
    canAdd?: boolean;
    canManageOwn?: boolean;
}

const CommentsForm = ({ cardId, isOpen, onClose, canAdd = true, canManageOwn = true }: CommentsFormProps) => {
    const { t } = useTranslation();
    const { toast } = useToast();
    const { user: currentUser } = useAuth();
    const [comments, setComments] = useState<CardComment[]>([]);
    const [newCommentText, setNewCommentText] = useState<string>('');
    const [editingCommentId, setEditingCommentId] = useState<number | null>(null);
    const [editingCommentText, setEditingCommentText] = useState<string>('');
    const [loading, setLoading] = useState<boolean>(false);

    const loadComments = useCallback(async (): Promise<void> => {
        try {
            const cardComments = await cardCommentsService.getComments(cardId);
            setComments(cardComments);
        } catch (error: any) {
            toast({
                title: t('common.error'),
                description: error.response?.data?.detail || t('card.loadCommentsError'),
                variant: "destructive"
            });
        }
    }, [cardId, toast, t]);

    useEffect(() => {
        if (isOpen) {
            loadComments();
            setNewCommentText('');
            setEditingCommentId(null);
            setEditingCommentText('');
        }
    }, [isOpen, loadComments]);

    const addComment = async (): Promise<void> => {
        if (!canAdd) {
            return;
        }
        const text = newCommentText.trim();
        if (!text) {
            return;
        }

        setLoading(true);
        try {
            const newComment = await cardCommentsService.createComment(cardId, text);
            setComments(prev => [newComment, ...prev]);
            setNewCommentText('');
            toast({ title: t('card.commentAdded'), variant: "success" });
        } catch (error: any) {
            toast({
                title: t('common.error'),
                description: error.response?.data?.detail || t('card.addCommentError'),
                variant: "destructive"
            });
        } finally {
            setLoading(false);
        }
    };

    const editComment = (commentId: number): void => {
        if (!canManageOwn) {
            return;
        }
        const comment = comments.find(c => c.id === commentId);
        if (comment) {
            setEditingCommentId(commentId);
            setEditingCommentText(comment.comment);
        }
    };

    const saveCommentEdit = async (): Promise<void> => {
        if (editingCommentId === null) {
            return;
        }

        if (!canManageOwn) {
            return;
        }

        const text = editingCommentText.trim();
        if (!text) {
            return;
        }

        setLoading(true);
        try {
            const updatedComment = await cardCommentsService.updateComment(editingCommentId, text);
            setComments(prev => prev.map(c => c.id === editingCommentId ? updatedComment : c));
            setEditingCommentId(null);
            setEditingCommentText('');
            toast({ title: t('card.commentUpdated'), variant: "success" });
        } catch (error: any) {
            toast({
                title: t('common.error'),
                description: error.response?.data?.detail || t('card.updateCommentError'),
                variant: "destructive"
            });
        } finally {
            setLoading(false);
        }
    };

    const deleteComment = async (commentId: number): Promise<void> => {
        if (!canManageOwn) {
            return;
        }
        setLoading(true);
        try {
            await cardCommentsService.deleteComment(commentId);
            setComments(prev => prev.filter(c => c.id !== commentId));
            toast({ title: t('card.commentDeleted'), variant: "success" });
        } catch (error: any) {
            toast({
                title: t('common.error'),
                description: error.response?.data?.detail || t('card.deleteCommentError'),
                variant: "destructive"
            });
        } finally {
            setLoading(false);
        }
    };

    const formatCommentDate = (dateString: string): string => {
        return new Date(dateString).toLocaleString('fr-FR', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-h-[90vh] max-w-2xl flex flex-col">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <MessageSquare className="h-5 w-5" />
                        {t('card.comments')}
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-4 flex flex-col min-h-0">
                    {/* Add Comment Section */}
                    <div className="space-y-2">
                        {!canAdd && (
                            <p className="text-sm text-muted-foreground">{t('card.commentsReadOnlyNotice')}</p>
                        )}
                        <div className="flex gap-2">
                            <Textarea
                                id="new-comment"
                                value={newCommentText}
                                onChange={(e) => setNewCommentText(e.target.value)}
                                placeholder={t('card.addCommentPlaceholder')}
                                className="flex-1"
                                rows={3}
                                maxLength={1000}
                                disabled={loading || !canAdd}
                            />
                            <Button
                                onClick={addComment}
                                disabled={!newCommentText.trim() || loading || !canAdd}
                                className="self-end"
                            >
                                {t('card.add')}
                            </Button>
                        </div>
                    </div>

                    {/* Comments List */}
                    <div className="space-y-3 overflow-y-auto flex-grow min-h-0">
                        {comments.map((comment) => (
                            <div key={comment.id} className="p-3 bg-muted rounded-md space-y-2">
                                <div className="flex justify-between items-start">
                                    <div className="text-sm font-medium">
                                        {comment.user?.display_name || t('user.unknownUser')}
                                        <span className="text-muted-foreground ml-2">
                                            {formatCommentDate(comment.created_at)}
                                        </span>
                                    </div>
                                    {canManageOwn && currentUser?.id === comment.user_id && (
                                        <div className="flex gap-1">
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => editComment(comment.id)}
                                                title={t('common.edit')}
                                                disabled={loading}
                                            >
                                                <Pencil className="h-3.5 w-3.5" />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => deleteComment(comment.id)}
                                                title={t('common.delete')}
                                                disabled={loading || !canManageOwn}
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </Button>
                                        </div>
                                    )}
                                </div>

                                {editingCommentId === comment.id ? (
                                    <div className="space-y-2">
                                        <Textarea
                                            value={editingCommentText}
                                            onChange={(e) => setEditingCommentText(e.target.value)}
                                            placeholder={t('card.editCommentPlaceholder')}
                                            className="w-full"
                                            rows={3}
                                            maxLength={1000}
                                            disabled={loading}
                                        />
                                        <div className="flex gap-2 justify-end">
                                            <Button
                                                variant="outline"
                                                onClick={() => {
                                                    setEditingCommentId(null);
                                                    setEditingCommentText('');
                                                }}
                                                disabled={loading}
                                            >
                                                {t('common.cancel')}
                                            </Button>
                                            <Button
                                                onClick={saveCommentEdit}
                                                disabled={!editingCommentText.trim() || loading || !canManageOwn}
                                            >
                                                {t('common.save')}
                                            </Button>
                                        </div>
                                    </div>
                                ) : (
                                    <p className="text-sm whitespace-pre-wrap">{comment.comment}</p>
                                )}
                            </div>
                        ))}

                        {comments.length === 0 && (
                            <div className="text-sm text-muted-foreground text-center py-8">
                                {t('card.noComments')}
                            </div>
                        )}
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={onClose}>
                        {t('common.close')}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

export { CommentsForm };

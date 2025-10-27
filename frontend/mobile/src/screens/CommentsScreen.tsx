import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, MessageSquare } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useToast } from '@shared/hooks/use-toast';
import { useAuth } from '@shared/hooks/useAuth';
import { usePermissions } from '@shared/hooks/usePermissions';
import { cardCommentsService } from '@shared/services/api';
import { CardComment } from '@shared/types/index';
import { Loader2 } from 'lucide-react';

interface CommentsScreenProps {
  cardId?: string;
  boardId?: string;
}

const CommentsScreen = ({ cardId: propCardId, boardId: propBoardId }: CommentsScreenProps) => {
  const { cardId: paramCardId, boardId: paramBoardId } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { toast } = useToast();
  const { user: currentUser } = useAuth();
  const permissions = usePermissions(currentUser);

  const cardId = propCardId || paramCardId;
  const boardId = propBoardId || paramBoardId;

  const [comments, setComments] = useState<CardComment[]>([]);
  const [newCommentText, setNewCommentText] = useState<string>('');
  const [editingCommentId, setEditingCommentId] = useState<number | null>(null);
  const [editingCommentText, setEditingCommentText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  const loadComments = useCallback(async (): Promise<void> => {
    if (!cardId) return;

    try {
      const cardComments = await cardCommentsService.getComments(parseInt(cardId));
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
    loadComments();
  }, [loadComments]);

  const addComment = async (): Promise<void> => {
    if (!cardId) return;

    const text = newCommentText.trim();
    if (!text) {
      return;
    }

    setLoading(true);
    try {
      const newComment = await cardCommentsService.createComment(parseInt(cardId), text);
      const updatedComments = [newComment, ...comments];
      setComments(updatedComments);
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
    const comment = comments.find(c => c.id === commentId);
    if (comment && permissions.canEditComment(comment)) {
      setEditingCommentId(commentId);
      setEditingCommentText(comment.comment);
    }
  };

  const saveCommentEdit = async (): Promise<void> => {
    if (editingCommentId === null) {
      return;
    }

    const comment = comments.find(c => c.id === editingCommentId);
    if (!comment || !permissions.canEditComment(comment)) {
      return;
    }

    const text = editingCommentText.trim();
    if (!text) {
      return;
    }

    setLoading(true);
    try {
      const updatedComment = await cardCommentsService.updateComment(editingCommentId, text);
      const updatedComments = comments.map(c => c.id === editingCommentId ? updatedComment : c);
      setComments(updatedComments);
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
    const comment = comments.find(c => c.id === commentId);
    if (!comment || !permissions.canDeleteComment(comment)) {
      return;
    }
    setLoading(true);
    try {
      await cardCommentsService.deleteComment(commentId);
      const updatedComments = comments.filter(c => c.id !== commentId);
      setComments(updatedComments);
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

  const goBack = () => {
    if (boardId) {
      navigate(`/board/${boardId}`);
    } else {
      navigate(-1);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background border-b">
        <div className="flex items-center gap-3 p-4">
          <button
            onClick={goBack}
            className="shrink-0 p-2 rounded-full hover:bg-muted transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <MessageSquare className="h-5 w-5 text-muted-foreground shrink-0" />
            <h1 className="text-lg font-semibold truncate">
              {t('card.comments')}
            </h1>
          </div>
        </div>
      </div>

      <div className="flex flex-col h-[calc(100vh-73px)]">
        {/* Add Comment Section */}
        <div className="p-4 border-b bg-card">
          <div className="space-y-3">
            <textarea
              value={newCommentText}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNewCommentText(e.target.value)}
              placeholder={t('card.addCommentPlaceholder')}
              className="w-full bg-card border-2 border-border rounded-lg px-4 py-3 text-foreground disabled:opacity-50 resize-none"
              rows={3}
              maxLength={1000}
              disabled={loading}
            />
            <button
              onClick={addComment}
              disabled={!newCommentText.trim() || loading}
              className="w-full btn-touch bg-primary text-primary-foreground rounded-lg px-4 py-3 disabled:opacity-50 font-medium"
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('card.add')}
            </button>
          </div>
        </div>

        {/* Comments List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {comments.map((comment) => (
            <div key={comment.id} className="p-4 bg-card rounded-lg border space-y-3">
              <div className="flex justify-between items-start">
                <div className="text-sm font-medium">
                  {comment.user?.display_name || t('user.unknownUser')}
                  <span className="text-muted-foreground ml-2">
                    {formatCommentDate(comment.created_at)}
                  </span>
                </div>
                {permissions.canEditComment(comment) && (
                  <div className="flex gap-1">
                    <button
                      onClick={() => editComment(comment.id)}
                      title={t('common.edit')}
                      disabled={loading}
                      className="h-8 w-8 p-1 rounded hover:bg-muted transition-colors"
                    >
                      <MessageSquare className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => deleteComment(comment.id)}
                      title={t('common.delete')}
                      disabled={loading || !permissions.canDeleteComment(comment)}
                      className="h-8 w-8 p-1 rounded hover:bg-muted transition-colors text-destructive"
                    >
                      <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                )}
              </div>

              {editingCommentId === comment.id ? (
                <div className="space-y-3">
                  <textarea
                    value={editingCommentText}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setEditingCommentText(e.target.value)}
                    placeholder={t('card.editCommentPlaceholder')}
                    className="w-full bg-card border-2 border-border rounded-lg px-4 py-3 text-foreground disabled:opacity-50 resize-none"
                    rows={3}
                    maxLength={1000}
                    disabled={loading}
                  />
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={() => {
                        setEditingCommentId(null);
                        setEditingCommentText('');
                      }}
                      disabled={loading}
                      className="btn-touch bg-muted text-muted-foreground rounded-lg px-4 py-2 disabled:opacity-50 font-medium"
                    >
                      {t('common.cancel')}
                    </button>
                    <button
                      onClick={saveCommentEdit}
                      disabled={!editingCommentText.trim() || loading || !permissions.canEditComment(comment)}
                      className="btn-touch bg-primary text-primary-foreground rounded-lg px-4 py-2 disabled:opacity-50 font-medium"
                    >
                      {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {t('common.save')}
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {comment.comment}
                </p>
              )}
            </div>
          ))}

          {comments.length === 0 && (
            <div className="text-sm text-muted-foreground text-center py-12">
              <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>{t('card.noComments')}</p>
              <p className="text-xs mt-2">{t('card.beFirstToComment')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export { CommentsScreen };
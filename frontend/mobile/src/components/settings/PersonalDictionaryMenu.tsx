import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Edit, Trash2, Loader2, Save, X } from 'lucide-react';
import { personalDictionaryService } from '@shared/services/api';
import { PersonalDictionaryEntry } from '@shared/types';

interface PersonalDictionaryMenuProps {
  onBack: () => void;
}

const PersonalDictionaryMenu = ({ onBack }: PersonalDictionaryMenuProps) => {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<PersonalDictionaryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingEntry, setEditingEntry] = useState<PersonalDictionaryEntry | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ term: '', definition: '' });
  const [error, setError] = useState('');

  useEffect(() => {
    loadEntries();
  }, []);

  const loadEntries = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await personalDictionaryService.getEntries();
      setEntries(data);
    } catch (err) {
      console.error('Error loading dictionary entries:', err);
      setError(t('errors.loadingError'));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingEntry) {
        await personalDictionaryService.updateEntry(editingEntry.id, formData);
      } else {
        await personalDictionaryService.createEntry(formData);
      }
      setShowForm(false);
      setEditingEntry(null);
      setFormData({ term: '', definition: '' });
      loadEntries();
    } catch (err) {
      console.error('Error saving entry:', err);
      setError(t('errors.saveError'));
    }
  };

  const handleEdit = (entry: PersonalDictionaryEntry) => {
    setEditingEntry(entry);
    setFormData({ term: entry.term, definition: entry.definition });
    setShowForm(true);
  };

  const handleDelete = async (entryId: number) => {
    if (!confirm(t('dictionary.confirmDeleteEntry'))) return;

    try {
      await personalDictionaryService.deleteEntry(entryId);
      loadEntries();
    } catch (err) {
      console.error('Error deleting entry:', err);
      setError(t('errors.deleteError'));
    }
  };

  const handleCreate = () => {
    setEditingEntry(null);
    setFormData({ term: '', definition: '' });
    setShowForm(true);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingEntry(null);
    setFormData({ term: '', definition: '' });
  };

  return (
    <div className="p-4 space-y-4">
      {/* Info hint */}
      <div className="text-xs p-3 bg-primary/10 rounded-lg border border-primary/20">
        <span className="text-foreground">ℹ️ {t('dictionary.personalHint')}</span>
      </div>

      {/* Add button */}
      {!showForm && (
        <button
          onClick={handleCreate}
          className="w-full flex items-center justify-center gap-2 p-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 active:bg-primary/80 transition-colors"
        >
          <Plus className="w-5 h-5" />
          {t('dictionary.newEntry')}
        </button>
      )}

      {/* Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="space-y-3 p-4 bg-muted/50 rounded-lg">
          <h3 className="text-sm font-semibold">
            {editingEntry ? t('dictionary.editEntry') : t('dictionary.newEntry')}
          </h3>

          <div className="space-y-2">
            <label htmlFor="term" className="text-xs font-medium text-muted-foreground">
              {t('dictionary.term')}
            </label>
            <input
              id="term"
              type="text"
              value={formData.term}
              onChange={(e) => setFormData({ ...formData, term: e.target.value })}
              placeholder={t('dictionary.term')}
              maxLength={32}
              required
              className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <p className="text-xs text-muted-foreground">
              {formData.term.length}/32 {t('common.charactersMax')}
            </p>
          </div>

          <div className="space-y-2">
            <label htmlFor="definition" className="text-xs font-medium text-muted-foreground">
              {t('dictionary.definition')}
            </label>
            <textarea
              id="definition"
              value={formData.definition}
              onChange={(e) => setFormData({ ...formData, definition: e.target.value })}
              placeholder={t('dictionary.definition')}
              maxLength={250}
              rows={4}
              required
              className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            />
            <p className="text-xs text-muted-foreground">
              {formData.definition.length}/250 {t('common.charactersMax')}
            </p>
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleCancel}
              className="flex-1 flex items-center justify-center gap-2 p-2 bg-muted text-foreground rounded-lg hover:bg-muted/80 active:bg-muted/60 transition-colors"
            >
              <X className="w-4 h-4" />
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              className="flex-1 flex items-center justify-center gap-2 p-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 active:bg-primary/80 transition-colors"
            >
              <Save className="w-4 h-4" />
              {editingEntry ? t('common.update') : t('common.create')}
            </button>
          </div>
        </form>
      )}

      {/* Error message */}
      {error && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-xs">
          <span className="text-red-600 dark:text-red-400">{error}</span>
        </div>
      )}

      {/* Entries list */}
      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : entries.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground text-sm">
          {t('dictionary.noEntries')}
        </div>
      ) : (
        <div className="space-y-2">
          {entries.map((entry) => (
            <div
              key={entry.id}
              className="p-3 bg-muted/30 rounded-lg border border-border"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-sm truncate">{entry.term}</div>
                  <div className="text-xs text-muted-foreground mt-1 line-clamp-2">
                    {entry.definition}
                  </div>
                </div>

                <div className="flex gap-1 flex-shrink-0">
                  <button
                    onClick={() => handleEdit(entry)}
                    className="p-2 text-muted-foreground hover:text-foreground active:bg-accent rounded-lg transition-colors"
                    aria-label={t('common.edit')}
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(entry.id)}
                    className="p-2 text-destructive hover:text-destructive/80 active:bg-destructive/10 rounded-lg transition-colors"
                    aria-label={t('common.delete')}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PersonalDictionaryMenu;


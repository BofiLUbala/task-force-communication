import { useRef } from 'react';
import usePreferences from '../hooks/usePreferences';
import { MEDIA_LABELS, classifyFile } from '../utils/publicationTargets';
import './AttachmentManager.css';

const ICONS = { PHOTO: 'image', VIDEO: 'movie', DOCUMENT: 'description', AUDIO: 'audiotrack' };

function humanSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

/**
 * Attachment list for the composer: images, videos and documents in one place,
 * each one removable and reorderable, with its upload progress while saving.
 *
 * `items` mixes files chosen locally (not yet uploaded) with attachments that
 * already exist on the server when editing.
 */
export default function AttachmentManager({ items, onAdd, onRemove, onMove, progress = {}, disabled }) {
  const { tr } = usePreferences();
  const inputRef = useRef(null);

  function handleFiles(event) {
    const chosen = Array.from(event.target.files || []);
    if (chosen.length) {
      onAdd(chosen.map((file) => ({
        key: `${file.name}-${file.size}-${Math.random().toString(36).slice(2, 8)}`,
        file,
        media_type: classifyFile(file),
        name: file.name,
        size: file.size,
      })));
    }
    event.target.value = '';
  }

  return (
    <div className="attachment-manager">
      <div className="attachment-manager-head">
        <div>
          <strong>{tr('Pièces jointes', 'Attachments')}</strong>
          <p>
            {tr(
              'Images, vidéos et documents. Chaque destination ne reprendra que ce qu’elle sait publier.',
              'Images, videos and documents. Each destination only takes what it can publish.',
            )}
          </p>
        </div>
        <button
          type="button"
          className="btn btn-navy attachment-add"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
        >
          <span className="material-symbols-outlined">add</span>
          {tr('Ajouter des fichiers', 'Add files')}
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          onChange={handleFiles}
          accept="image/*,video/*,application/pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,audio/*"
        />
      </div>

      {items.length === 0 ? (
        <p className="attachment-empty">{tr('Aucune pièce jointe.', 'No attachments yet.')}</p>
      ) : (
        <ul className="attachment-list">
          {items.map((item, index) => {
            const percent = progress[item.key];
            return (
              <li key={item.key} className={item.error ? 'attachment-row attachment-row-error' : 'attachment-row'}>
                <span className="material-symbols-outlined attachment-icon">
                  {ICONS[item.media_type] || 'attach_file'}
                </span>
                <div className="attachment-info">
                  <strong>{item.name}</strong>
                  <small>
                    {MEDIA_LABELS[item.media_type] || item.media_type}
                    {item.size ? ` · ${humanSize(item.size)}` : ''}
                    {item.uploaded ? ` · ${tr('déjà en ligne', 'already online')}` : ''}
                  </small>
                  {item.error && <small className="attachment-error">{item.error}</small>}
                  {percent !== undefined && percent < 100 && (
                    <div className="attachment-progress"><div style={{ width: `${percent}%` }} /></div>
                  )}
                </div>
                <div className="attachment-actions">
                  <button
                    type="button"
                    aria-label={tr('Monter', 'Move up')}
                    disabled={disabled || index === 0}
                    onClick={() => onMove(index, index - 1)}
                  >
                    <span className="material-symbols-outlined">arrow_upward</span>
                  </button>
                  <button
                    type="button"
                    aria-label={tr('Descendre', 'Move down')}
                    disabled={disabled || index === items.length - 1}
                    onClick={() => onMove(index, index + 1)}
                  >
                    <span className="material-symbols-outlined">arrow_downward</span>
                  </button>
                  <button
                    type="button"
                    aria-label={tr('Retirer', 'Remove')}
                    className="attachment-remove"
                    disabled={disabled}
                    onClick={() => onRemove(item)}
                  >
                    <span className="material-symbols-outlined">close</span>
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

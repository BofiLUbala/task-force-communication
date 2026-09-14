import { useState } from 'react';
import usePreferences from '../hooks/usePreferences';
import './AttachmentManager.css';

function isValidUrl(value) {
  try {
    const parsed = new URL(value);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

/** External links carried by a publication — added and removed one by one. */
export default function LinkManager({ links, onChange, disabled }) {
  const { tr } = usePreferences();
  const [url, setUrl] = useState('');
  const [label, setLabel] = useState('');
  const [error, setError] = useState('');

  function add() {
    const trimmed = url.trim();
    if (!trimmed) return;
    if (!isValidUrl(trimmed)) {
      setError(tr('Adresse invalide : elle doit commencer par http:// ou https://',
        'Invalid address: it must start with http:// or https://'));
      return;
    }
    if (links.some((link) => link.url === trimmed)) {
      setError(tr('Ce lien est déjà présent.', 'This link is already in the list.'));
      return;
    }
    setError('');
    onChange([...links, { url: trimmed, label: label.trim() }]);
    setUrl('');
    setLabel('');
  }

  return (
    <div className="attachment-manager">
      <div className="attachment-manager-head">
        <div>
          <strong>{tr('Liens externes', 'External links')}</strong>
          <p>{tr('Site officiel, article, ressource à ouvrir depuis la publication.',
            'Official site, article or resource to open from the publication.')}</p>
        </div>
      </div>

      <div className="link-form">
        <input
          type="url"
          value={url}
          disabled={disabled}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://presidence.cd"
          aria-label={tr('Adresse du lien', 'Link address')}
        />
        <input
          type="text"
          value={label}
          disabled={disabled}
          onChange={(event) => setLabel(event.target.value)}
          placeholder={tr('Intitulé (facultatif)', 'Label (optional)')}
          aria-label={tr('Intitulé du lien', 'Link label')}
        />
        <button type="button" className="btn btn-navy" onClick={add} disabled={disabled}>
          {tr('Ajouter', 'Add')}
        </button>
      </div>
      {error && <p className="attachment-error">{error}</p>}

      {links.length === 0 ? (
        <p className="attachment-empty">{tr('Aucun lien.', 'No links yet.')}</p>
      ) : (
        <ul className="attachment-list">
          {links.map((link, index) => (
            <li className="attachment-row" key={link.url}>
              <span className="material-symbols-outlined attachment-icon">link</span>
              <div className="attachment-info">
                <strong>{link.label || link.url}</strong>
                {link.label && <small>{link.url}</small>}
              </div>
              <div className="attachment-actions">
                <button
                  type="button"
                  className="attachment-remove"
                  aria-label={tr('Retirer le lien', 'Remove link')}
                  disabled={disabled}
                  onClick={() => onChange(links.filter((_, position) => position !== index))}
                >
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

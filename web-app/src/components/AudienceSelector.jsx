import { useMemo, useState } from 'react';
import usePreferences from '../hooks/usePreferences';
import { AUDIENCES } from '../utils/publicationTargets';
import './AttachmentManager.css';

/**
 * "Who is concerned by this publication?"
 *
 * This picker only decides what the composer *asks for*. The backend resolves
 * the audience itself and filters every feed against it, so a publication
 * cannot be read by someone it was not addressed to even if this component is
 * bypassed entirely.
 */
export default function AudienceSelector({
  audience, unit, userIds, units = [], users = [], onChange, disabled,
}) {
  const { tr } = usePreferences();
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return users;
    return users.filter(
      (user) => user.name.toLowerCase().includes(needle)
        || (user.unit || '').toLowerCase().includes(needle),
    );
  }, [search, users]);

  const estimate = useMemo(() => {
    if (audience === 'SPECIFIC_USERS') return userIds.length;
    if (audience === 'SPECIFIC_GROUP') {
      return unit ? users.filter((user) => user.unit === unit).length : 0;
    }
    if (audience === 'ALL_AGENTS') return users.filter((user) => user.role === 'AGENT').length;
    if (audience === 'HIERARCHY_ONLY') return users.filter((user) => user.role !== 'AGENT').length;
    return users.length;
  }, [audience, unit, userIds, users]);

  function toggleUser(id) {
    onChange({
      userIds: userIds.includes(id)
        ? userIds.filter((item) => item !== id)
        : [...userIds, id],
    });
  }

  return (
    <div className="attachment-manager audience-panel">
      <div className="attachment-manager-head">
        <div>
          <strong>{tr('Qui est concerné ?', 'Who is concerned?')}</strong>
          <p>
            {tr(
              'Seuls les destinataires choisis verront cette publication dans l’application.',
              'Only the chosen recipients will see this publication in the app.',
            )}
          </p>
        </div>
        <span className="audience-estimate">
          <b>{estimate}</b> {tr('destinataire(s)', 'recipient(s)')}
        </span>
      </div>

      <ul className="audience-options">
        {AUDIENCES.map((option) => (
          <li key={option.value}>
            <label className="audience-choice">
              <input
                type="radio"
                name="audience"
                value={option.value}
                // The visible text sits in a sibling span, so the control
                // needs its own name to be announced.
                aria-label={option.label}
                checked={audience === option.value}
                disabled={disabled}
                onChange={() => onChange({ audience: option.value })}
              />
              <span>
                <strong>{option.label}</strong>
                <small>{option.hint}</small>
              </span>
            </label>
          </li>
        ))}
      </ul>

      {audience === 'SPECIFIC_GROUP' && (
        <div className="audience-detail">
          <label htmlFor="audience-unit">{tr('Unité concernée', 'Unit concerned')}</label>
          <select
            id="audience-unit"
            value={unit}
            disabled={disabled}
            onChange={(event) => onChange({ unit: event.target.value })}
          >
            <option value="">{tr('— Choisir une unité —', '— Choose a unit —')}</option>
            {units.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
          {units.length === 0 && (
            <p className="audience-warning">
              {tr(
                'Aucune unité renseignée sur les comptes agents pour le moment.',
                'No unit is set on any agent account yet.',
              )}
            </p>
          )}
        </div>
      )}

      {audience === 'SPECIFIC_USERS' && (
        <div className="audience-detail">
          <label htmlFor="audience-search">{tr('Rechercher une personne', 'Search for a person')}</label>
          <input
            id="audience-search"
            value={search}
            disabled={disabled}
            placeholder={tr('Nom ou unité...', 'Name or unit...')}
            onChange={(event) => setSearch(event.target.value)}
          />
          <ul className="audience-user-list">
            {filtered.map((user) => (
              <li key={user.id}>
                <label>
                  <input
                    type="checkbox"
                    aria-label={user.name}
                    checked={userIds.includes(user.id)}
                    disabled={disabled}
                    onChange={() => toggleUser(user.id)}
                  />
                  <span className="audience-user-name">{user.name}</span>
                  <small>
                    {user.unit || tr('sans unité', 'no unit')}
                    {/* Contact gaps are shown here rather than discovered at
                        send time, when it is too late to fix them. */}
                    {!user.has_email && ` · ${tr('sans e-mail', 'no e-mail')}`}
                    {!user.has_phone && ` · ${tr('sans WhatsApp', 'no WhatsApp')}`}
                  </small>
                </label>
              </li>
            ))}
            {filtered.length === 0 && (
              <li className="audience-empty">{tr('Aucun compte trouvé.', 'No account found.')}</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

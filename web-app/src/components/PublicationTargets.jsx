import usePreferences from '../hooks/usePreferences';
import { STATUS_LABELS, automaticStatus } from '../utils/publicationTargets';
import './AttachmentManager.css';

const PLATFORM_ICONS = {
  WEB: 'public', WEBSITE: 'public', MOBILE: 'smartphone', EMAIL: 'mail',
  WHATSAPP: 'chat', LINKEDIN: 'work', YOUTUBE: 'smart_display',
};

/**
 * Destination picker and, after publishing, the outcome of each one.
 *
 * Two kinds of row live here. Channels the author *chooses* (the apps, and
 * the mass-mailing ones) keep a checkbox, and one that cannot carry the
 * content is disabled *and* says why. Social channels are not a choice at
 * all: the server publishes to every connected provider that fits, so they
 * are listed as a read-only summary of what is about to happen. Showing them
 * as unticked boxes would be a lie — the publication goes out either way.
 */
export default function PublicationTargets({
  plans, selected, onToggle, results, disabled, blocked = [], blockedReason = '',
}) {
  const { tr } = usePreferences();
  // Results arrive as deliveries (keyed by `channel`) from the new publish
  // endpoint, and as social attempts (keyed by `platform`) from the old one.
  const resultByPlatform = Object.fromEntries(
    (results || []).map((row) => [row.channel || row.platform, row]),
  );
  const chosenPlans = plans.filter((plan) => !plan.automatic);
  const autoPlans = plans.filter((plan) => plan.automatic);

  return (
    <div className="attachment-manager targets-panel">
      <div className="attachment-manager-head">
        <div>
          <strong>{tr('Destinations', 'Destinations')}</strong>
          <p>{tr('Ce que chaque plateforme recevra de cette publication.',
            'What each platform will receive from this publication.')}</p>
        </div>
      </div>

      <ul className="targets-list">
        {chosenPlans.map((plan) => {
          const result = resultByPlatform[plan.platform];
          const isBlocked = blocked.includes(plan.platform);
          const selectable = plan.available && !isBlocked;
          const checked = selected.includes(plan.platform);
          return (
            <li
              key={plan.platform}
              className={`target-row${selectable ? '' : ' target-row-unavailable'}`}
            >
              <label className="target-choice">
                <input
                  type="checkbox"
                  // The label also holds an icon glyph, which would otherwise
                  // be read out as part of the control's name.
                  aria-label={plan.label}
                  checked={checked && selectable}
                  disabled={disabled || !selectable}
                  onChange={() => onToggle(plan.platform)}
                />
                <span className="material-symbols-outlined target-icon">
                  {PLATFORM_ICONS[plan.platform] || 'share'}
                </span>
                <span className="target-name">{plan.label}</span>
                {result && (
                  <span className={`badge badge-result-${result.status}`}>
                    {STATUS_LABELS[result.status] || result.status}
                  </span>
                )}
              </label>

              <div className="target-detail">
                {isBlocked ? (
                  <p className="target-reason">{blockedReason}</p>
                ) : plan.available ? (
                  <p className="target-included">
                    {tr('Sera publié : ', 'Will publish: ')}
                    {plan.included.join(', ')}
                  </p>
                ) : (
                  <p className="target-reason">{plan.reason}</p>
                )}

                {plan.excluded?.map((item) => (
                  <p className="target-excluded" key={`${plan.platform}-${item.item}`}>
                    <span className="material-symbols-outlined">info</span>
                    <span><b>{item.item}</b> — {item.reason}</span>
                  </p>
                ))}

                {result && (
                  <p className={`target-result target-result-${result.status}`}>
                    {result.detail}
                    {result.external_url && (
                      <>
                        {' '}
                        <a href={result.external_url} target="_blank" rel="noopener noreferrer">
                          {tr('Voir la publication', 'View publication')}
                        </a>
                      </>
                    )}
                    {result.error_code && <em> ({result.error_code})</em>}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      {autoPlans.length > 0 && (
        <div className="targets-auto">
          <div className="targets-auto-head">
            <span className="material-symbols-outlined">bolt</span>
            <div>
              <strong>{tr('Diffusion sociale automatique', 'Automatic social distribution')}</strong>
              <p>{tr(
                'Aucune case à cocher : chaque réseau connecté qui peut porter ce contenu le reçoit.',
                'Nothing to tick: every connected network that can carry this content receives it.',
              )}</p>
            </div>
          </div>

          <ul className="targets-list targets-list-readonly">
            {autoPlans.map((plan) => {
              const result = resultByPlatform[plan.platform];
              const status = automaticStatus(plan);
              return (
                <li key={plan.platform} className={`target-row target-auto target-auto-${status.tone}`}>
                  <div className="target-choice">
                    <span className="material-symbols-outlined target-icon">
                      {PLATFORM_ICONS[plan.platform] || 'share'}
                    </span>
                    <span className="target-name">{plan.label}</span>
                    {result && (
                      <span className={`badge badge-result-${result.status}`}>
                        {STATUS_LABELS[result.status] || result.status}
                      </span>
                    )}
                  </div>

                  <div className="target-detail">
                    <p className="target-auto-status">{status.text}</p>

                    {plan.excluded?.map((item) => (
                      <p className="target-excluded" key={`${plan.platform}-${item.item}`}>
                        <span className="material-symbols-outlined">info</span>
                        <span><b>{item.item}</b> — {item.reason}</span>
                      </p>
                    ))}

                    {result && (
                      <p className={`target-result target-result-${result.status}`}>
                        {result.detail}
                        {result.external_url && (
                          <>
                            {' '}
                            <a href={result.external_url} target="_blank" rel="noopener noreferrer">
                              {tr('Voir la publication', 'View publication')}
                            </a>
                          </>
                        )}
                        {result.error_code && <em> ({result.error_code})</em>}
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

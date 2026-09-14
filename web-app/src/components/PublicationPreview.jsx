import { useState } from 'react';
import usePreferences from '../hooks/usePreferences';
import { channelPreview } from '../utils/publicationTargets';
import './AttachmentManager.css';

/**
 * Step 3 of the composer: exactly what each destination will receive.
 *
 * Transformations are shown, never hidden. If WhatsApp is going to reduce a
 * four-image communiqué to a headline and a link, the author sees that here
 * and not after 2 000 messages have gone out.
 */
export default function PublicationPreview({ plans, selected, content, audienceLabel, audienceSize }) {
  const { tr } = usePreferences();
  // Automatic social channels are never in `selected` — the server adds them —
  // but the author still needs to see what they are about to receive.
  const chosen = plans.filter(
    (plan) => plan.available && (plan.automatic || selected.includes(plan.channel)),
  );
  const [tab, setTab] = useState(chosen[0]?.channel || '');
  const active = chosen.find((plan) => plan.channel === tab) || chosen[0];

  if (!chosen.length) {
    return (
      <div className="attachment-manager preview-panel">
        <p className="attachment-empty">
          {tr('Aucune destination compatible sélectionnée.', 'No compatible destination selected.')}
        </p>
      </div>
    );
  }

  return (
    <div className="attachment-manager preview-panel">
      <div className="attachment-manager-head">
        <div>
          <strong>{tr('Aperçu par destination', 'Preview per destination')}</strong>
          <p>{tr('Ce que chaque canal recevra exactement.', 'Exactly what each channel will receive.')}</p>
        </div>
      </div>

      <div className="preview-tabs" role="tablist">
        {chosen.map((plan) => (
          <button
            key={plan.channel}
            type="button"
            role="tab"
            aria-selected={active?.channel === plan.channel}
            className={active?.channel === plan.channel ? 'preview-tab preview-tab-active' : 'preview-tab'}
            onClick={() => setTab(plan.channel)}
          >
            <span className="material-symbols-outlined">{plan.icon}</span>
            {plan.label}
          </button>
        ))}
      </div>

      {active && (
        <div className="preview-body">
          <h4>{content.title || tr('(sans titre)', '(untitled)')}</h4>
          <p className="preview-lead">
            {tr('Contiendra :', 'Will contain:')}
          </p>
          <ul className="preview-included">
            {channelPreview(active, content).map((item) => (
              <li key={item}>
                <span className="material-symbols-outlined">check</span>{item}
              </li>
            ))}
          </ul>
          {active.excluded?.length > 0 && (
            <>
              <p className="preview-lead">{tr('Ne contiendra pas :', 'Will not contain:')}</p>
              <ul className="preview-excluded">
                {active.excluded.map((item) => (
                  <li key={item.item}>
                    <span className="material-symbols-outlined">info</span>
                    <span><b>{item.item}</b> — {item.reason}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      <div className="preview-summary">
        <div>
          <small>{tr('Audience', 'Audience')}</small>
          <strong>{audienceLabel}</strong>
        </div>
        <div>
          <small>{tr('Destinataires concernés', 'Concerned recipients')}</small>
          <strong>{audienceSize}</strong>
        </div>
        <div>
          <small>{tr('Canaux', 'Channels')}</small>
          <strong>{chosen.map((plan) => plan.label).join(', ')}</strong>
        </div>
      </div>
    </div>
  );
}

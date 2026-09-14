import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';
import DashboardShell from '../../components/DashboardShell';
import RichTextEditor from '../../components/RichTextEditor';
import AttachmentManager from '../../components/AttachmentManager';
import LinkManager from '../../components/LinkManager';
import AudienceSelector from '../../components/AudienceSelector';
import PublicationTargets from '../../components/PublicationTargets';
import PublicationPreview from '../../components/PublicationPreview';
import {
  evaluateTargets, isAutomaticChannel, AUDIENCES, PUBLICATION_TYPES,
} from '../../utils/publicationTargets';
import { internalLinks } from '../../utils/publicationNav';
import { useAuth } from '../../context/AuthContext';
import usePreferences from '../../hooks/usePreferences';
import './Internal.css';

const STEPS = [
  { key: 'content', label: 'Contenu', icon: 'edit_note' },
  { key: 'audience', label: 'Audience & diffusion', icon: 'groups' },
  { key: 'review', label: 'Aperçu & confirmation', icon: 'preview' },
];

const emptyForm = {
  title: '', excerpt: '', body: '', category: 'ACTUALITE', cover: null,
  newsletterSubject: '', previewText: '', senderName: 'Task Force Présidentielle',
  scheduledFor: '',
};

function isBodyEmpty(html) {
  return !html || html.replace(/<[^>]*>/g, '').trim() === '';
}

/**
 * One composer for every publication.
 *
 * There is no longer a separate form for news, images, videos, releases and
 * newsletters — the type is a field in step 1, and the same three steps
 * (content → audience & channels → preview & confirm) produce all of them.
 */
export default function PublicationComposer() {
  const { user } = useAuth();
  const { tr } = usePreferences();
  const { slug: editSlug } = useParams();
  const navigate = useNavigate();
  const isEditMode = Boolean(editSlug);
  const links = internalLinks(user?.role, tr);
  const isHierarchy = user?.role === 'HIERARCHY' || user?.role === 'SUPER_ADMIN';

  const [step, setStep] = useState(0);
  const [form, setForm] = useState(emptyForm);
  const [attachments, setAttachments] = useState([]);
  const [removedIds, setRemovedIds] = useState([]);
  const [postLinks, setPostLinks] = useState([]);
  const [progress, setProgress] = useState({});

  const [audience, setAudience] = useState('EVERYONE');
  const [audienceUnit, setAudienceUnit] = useState('');
  const [audienceUserIds, setAudienceUserIds] = useState([]);
  const [options, setOptions] = useState({ units: [], users: [], channels: [] });
  const [channels, setChannels] = useState(['WEB', 'MOBILE']);

  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [results, setResults] = useState(null);
  const [overall, setOverall] = useState('');
  const [loadingExisting, setLoadingExisting] = useState(isEditMode);
  const [existingCover, setExistingCover] = useState('');
  const [testEmail, setTestEmail] = useState('');

  const availableChannels = useMemo(
    () => options.channels.filter((row) => row.available).map((row) => row.channel),
    [options.channels],
  );

  useEffect(() => {
    client.get('/publications/audience-options/')
      .then(({ data }) => setOptions(data))
      .catch(() => setOptions({ units: [], users: [], channels: [] }));
  }, []);

  useEffect(() => {
    if (!isEditMode) return;
    setLoadingExisting(true);
    client.get(`/publications/${editSlug}/`)
      .then(({ data }) => {
        setForm({
          ...emptyForm,
          title: data.title,
          excerpt: data.excerpt || '',
          body: data.body || '',
          category: data.category,
          newsletterSubject: data.newsletter_subject || data.title,
          previewText: data.newsletter_preview_text || data.excerpt || '',
          senderName: data.newsletter_sender_name || 'Task Force Présidentielle',
          scheduledFor: data.scheduled_for ? data.scheduled_for.slice(0, 16) : '',
        });
        setExistingCover(data.cover_image || data.attachment || '');
        setAudience(data.audience || 'EVERYONE');
        setAudienceUnit(data.audience_unit || '');
        setAudienceUserIds(data.audience_user_ids || []);
        // A published post records the social channels the server added; they
        // are not choices, so they must not come back as if the author picked
        // them.
        const chosen = (data.channels || []).filter((item) => !isAutomaticChannel(item));
        if (chosen.length) setChannels(chosen);
        setAttachments((data.gallery || []).map((media) => ({
          key: `saved-${media.id}`,
          id: media.id,
          media_type: media.media_type,
          name: media.original_filename || media.title || 'Fichier',
          size: media.file_size,
          uploaded: true,
        })));
        setPostLinks((data.links || []).map((link) => ({ url: link.url, label: link.label || '' })));
      })
      .catch(() => setError(tr('Impossible de charger cette publication.', 'Could not load this publication.')))
      .finally(() => setLoadingExisting(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEditMode, editSlug]);

  // Compatibility is recomputed from what is attached right now. The backend
  // re-runs the very same rules before it sends anything anywhere.
  const content = {
    hasText: Boolean(form.title || form.excerpt || !isBodyEmpty(form.body)),
    images: attachments.filter((item) => item.media_type === 'PHOTO').length,
    videos: attachments.filter((item) => item.media_type === 'VIDEO').length,
    documents: attachments.filter((item) => item.media_type === 'DOCUMENT').length,
    links: postLinks.length,
    hasCover: Boolean(form.cover) || Boolean(existingCover),
    title: form.title,
  };
  const plans = evaluateTargets(content, availableChannels);

  const audienceLabel = AUDIENCES.find((entry) => entry.value === audience)?.label || audience;
  const audienceSize = useMemo(() => {
    const users = options.users || [];
    if (audience === 'SPECIFIC_USERS') return audienceUserIds.length;
    if (audience === 'SPECIFIC_GROUP') {
      return audienceUnit ? users.filter((item) => item.unit === audienceUnit).length : 0;
    }
    if (audience === 'ALL_AGENTS') return users.filter((item) => item.role === 'AGENT').length;
    if (audience === 'HIERARCHY_ONLY') return users.filter((item) => item.role !== 'AGENT').length;
    return users.length;
  }, [audience, audienceUnit, audienceUserIds, options.users]);

  // Mailing an official newsletter is a hierarchy act. The button is hidden
  // for agents, and the server refuses it regardless of what the client sends.
  const emailBlocked = form.category === 'NEWSLETTER' && !isHierarchy;

  // Social channels are added by the server on every publish, so they are not
  // part of this state and cannot be toggled off from here.
  function toggleChannel(channel) {
    if (isAutomaticChannel(channel)) return;
    setChannels((current) => (
      current.includes(channel)
        ? current.filter((item) => item !== channel)
        : [...current, channel]
    ));
  }

  function update(event) {
    const { name, value, files } = event.target;
    setForm((current) => ({ ...current, [name]: files ? files[0] : value }));
  }

  function updateAudience(patch) {
    if ('audience' in patch) setAudience(patch.audience);
    if ('unit' in patch) setAudienceUnit(patch.unit);
    if ('userIds' in patch) setAudienceUserIds(patch.userIds);
  }

  async function savePost() {
    const payload = new FormData();
    payload.append('title', form.title);
    payload.append('category', form.category);
    payload.append('excerpt', form.excerpt);
    payload.append('body', form.body || form.excerpt);
    payload.append('audience', audience);
    payload.append('audience_unit', audience === 'SPECIFIC_GROUP' ? audienceUnit : '');
    payload.append('audience_users_payload', JSON.stringify(
      audience === 'SPECIFIC_USERS' ? audienceUserIds : [],
    ));
    payload.append('links_payload', JSON.stringify(postLinks));
    payload.append('channels', JSON.stringify(channels));
    if (form.category === 'NEWSLETTER') {
      payload.append('newsletter_subject', form.newsletterSubject || form.title);
      payload.append('newsletter_preview_text', form.previewText || form.excerpt);
      payload.append('newsletter_sender_name', form.senderName);
    }
    if (form.cover) payload.append('cover_image', form.cover);

    const { data } = isEditMode
      ? await client.patch(`/publications/${editSlug}/`, payload)
      : await client.post('/publications/', payload);
    return data;
  }

  async function syncAttachments(post) {
    for (const id of removedIds) {
      try {
        await client.delete(`/publications/${post.slug}/media/${id}/`);
      } catch {
        // Already gone server-side: nothing left to remove.
      }
    }
    const failures = [];
    for (const [index, item] of attachments.entries()) {
      if (!item.file) continue;
      const data = new FormData();
      data.append('file', item.file);
      data.append('media_type', item.media_type);
      data.append('order', String(index));
      if (item.title) data.append('title', item.title);
      try {
        await client.post(`/publications/${post.slug}/upload-media/`, data, {
          onUploadProgress: (event) => {
            if (!event.total) return;
            setProgress((current) => ({
              ...current, [item.key]: Math.round((event.loaded * 100) / event.total),
            }));
          },
        });
      } catch (uploadError) {
        failures.push(`${item.name} : ${uploadError.response?.data?.detail || tr('envoi impossible', 'upload failed')}`);
      }
    }
    setRemovedIds([]);
    return failures;
  }

  async function sendTestEmail() {
    setSubmitting(true);
    setError('');
    setMessage('');
    try {
      // The preview renders the saved publication, so the draft has to exist
      // before the server can turn it into an e-mail.
      const post = await savePost();
      await client.post(`/publications/${post.slug}/test-newsletter/`, { email: testEmail.trim() });
      setMessage(tr(`E-mail de test envoyé à ${testEmail}.`, `Test e-mail sent to ${testEmail}.`));
      if (!isEditMode) navigate(`/espace/publications/${post.slug}/modifier`, { replace: true });
    } catch (requestError) {
      setError(requestError.response?.data?.detail
        || tr('L’envoi de test a échoué.', 'The test send failed.'));
    } finally {
      setSubmitting(false);
    }
  }

  async function run(action) {
    setSubmitting(true);
    setError('');
    setMessage('');
    try {
      const post = await savePost();
      const failures = await syncAttachments(post);
      if (failures.length) setError(failures.join(' · '));

      if (action === 'draft') {
        setMessage(tr('Brouillon enregistré.', 'Draft saved.'));
        navigate(`/espace/publications/${post.slug}/modifier`, { replace: true });
        return;
      }

      if (action === 'schedule') {
        if (!form.scheduledFor) {
          setError(tr('Choisissez une date de programmation.', 'Choose a scheduling date.'));
          return;
        }
        await client.post(`/publications/${post.slug}/schedule/`, {
          scheduled_for: new Date(form.scheduledFor).toISOString(),
          channels,
        });
        setMessage(tr('Publication programmée.', 'Publication scheduled.'));
        navigate('/espace/publications/programmees');
        return;
      }

      // Attachments must all be in place before any provider is called, or a
      // video destination would be asked to publish a post with no file yet.
      const { data } = await client.post(`/publications/${post.slug}/publish/`, { channels });
      setResults(data.deliveries || []);
      setOverall(data.overall_status || '');
      setMessage(tr('Publication diffusée.', 'Publication distributed.'));
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(typeof detail === 'string'
        ? detail
        : tr('La publication a échoué. Vérifiez les champs et les fichiers.',
          'Publication failed. Check the fields and files.'));
    } finally {
      setSubmitting(false);
    }
  }

  function canLeaveContentStep() {
    if (!form.title.trim()) {
      setError(tr('Le titre est requis.', 'A title is required.'));
      return false;
    }
    if (isBodyEmpty(form.body) && !form.excerpt.trim()) {
      setError(tr('Ajoutez un contenu ou un résumé.', 'Add content or a summary.'));
      return false;
    }
    setError('');
    return true;
  }

  if (loadingExisting) {
    return (
      <DashboardShell links={links}>
        <div className="dash-topbar"><h1>{tr('Publication', 'Publication')}</h1></div>
        <p className="feed-state">{tr('Chargement...', 'Loading...')}</p>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell links={links}>
      <div className="dash-topbar">
        <h1>{isEditMode ? tr('Modifier la publication', 'Edit publication') : tr('Nouvelle publication', 'New publication')}</h1>
      </div>

      <ol className="composer-steps">
        {STEPS.map((entry, index) => (
          <li
            key={entry.key}
            className={
              index === step ? 'composer-step composer-step-active'
                : index < step ? 'composer-step composer-step-done' : 'composer-step'
            }
          >
            <span className="material-symbols-outlined">{entry.icon}</span>
            <span>{index + 1}. {entry.label}</span>
          </li>
        ))}
      </ol>

      {message && <div className="publication-success">{message}</div>}
      {error && <div className="publication-error">{error}</div>}

      <div className="publication-layout">
        <div className="publication-form">
          {step === 0 && (
            <>
              <label htmlFor="pub-type">{tr('Type de publication', 'Publication type')}</label>
              <select id="pub-type" name="category" value={form.category} onChange={update}>
                {PUBLICATION_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>

              <label htmlFor="pub-title">{tr('Titre', 'Title')}</label>
              <input id="pub-title" name="title" value={form.title} onChange={update} required />

              <label htmlFor="pub-excerpt">{tr('Résumé', 'Summary')}</label>
              <input id="pub-excerpt" name="excerpt" value={form.excerpt} onChange={update} />

              <label htmlFor="pub-body">{tr('Contenu', 'Content')}</label>
              <RichTextEditor
                id="pub-body"
                value={form.body}
                onChange={(html) => setForm((current) => ({ ...current, body: html }))}
                placeholder={tr('Rédigez le contenu complet ici...', 'Write the full content here...')}
              />

              {form.category === 'NEWSLETTER' && (
                <fieldset className="newsletter-settings">
                  <legend>{tr('Paramètres de l’e-mail', 'Email settings')}</legend>
                  <label htmlFor="nl-subject">{tr('Objet de l’e-mail', 'Email subject')}</label>
                  <input id="nl-subject" name="newsletterSubject" value={form.newsletterSubject} onChange={update} />
                  <label htmlFor="nl-preview">{tr('Texte d’aperçu', 'Preview text')}</label>
                  <input id="nl-preview" name="previewText" value={form.previewText} onChange={update} maxLength="255" />
                  <label htmlFor="nl-sender">{tr('Nom de l’expéditeur', 'Sender name')}</label>
                  <input id="nl-sender" name="senderName" value={form.senderName} onChange={update} />
                </fieldset>
              )}

              <label htmlFor="pub-cover">{tr('Image de couverture (facultatif)', 'Cover image (optional)')}</label>
              {existingCover && (
                <a href={existingCover} target="_blank" rel="noopener noreferrer" className="publication-existing-file">
                  <span className="material-symbols-outlined">attach_file</span>
                  {tr('Couverture actuelle', 'Current cover')}
                </a>
              )}
              <input id="pub-cover" name="cover" type="file" accept="image/*" onChange={update} />

              <AttachmentManager
                items={attachments}
                onAdd={(added) => setAttachments((current) => [...current, ...added])}
                onRemove={(item) => {
                  if (item.id) setRemovedIds((current) => [...current, item.id]);
                  setAttachments((current) => current.filter((entry) => entry.key !== item.key));
                }}
                onMove={(from, to) => setAttachments((current) => {
                  const next = [...current];
                  const [moved] = next.splice(from, 1);
                  next.splice(to, 0, moved);
                  return next;
                })}
                progress={progress}
                disabled={submitting}
              />

              <LinkManager links={postLinks} onChange={setPostLinks} disabled={submitting} />
            </>
          )}

          {step === 1 && (
            <>
              <AudienceSelector
                audience={audience}
                unit={audienceUnit}
                userIds={audienceUserIds}
                units={options.units}
                users={options.users}
                onChange={updateAudience}
                disabled={submitting}
              />
              <PublicationTargets
                plans={plans}
                selected={channels}
                onToggle={toggleChannel}
                results={results}
                disabled={submitting}
                blocked={emailBlocked ? ['EMAIL'] : []}
                blockedReason={tr(
                  'Seule la hiérarchie peut envoyer une newsletter officielle par e-mail.',
                  'Only the hierarchy may send an official newsletter by e-mail.',
                )}
              />
            </>
          )}

          {step === 2 && (
            <>
              <PublicationPreview
                plans={plans}
                selected={channels}
                content={content}
                audienceLabel={audienceLabel}
                audienceSize={audienceSize}
              />

              <div className="confirm-panel">
                <h3>{tr('Prêt à publier', 'Ready to publish')}</h3>
                <dl>
                  <div><dt>{tr('Type', 'Type')}</dt><dd>{PUBLICATION_TYPES.find((t) => t.value === form.category)?.label}</dd></div>
                  <div><dt>{tr('Audience', 'Audience')}</dt><dd>{audienceLabel}</dd></div>
                  <div>
                    <dt>{tr('Destinataires', 'Recipients')}</dt>
                    <dd className={audienceSize > 100 ? 'confirm-large' : ''}>
                      {audienceSize} {tr('utilisateur(s) concerné(s)', 'concerned user(s)')}
                    </dd>
                  </div>
                  <div>
                    <dt>{tr('Canaux', 'Channels')}</dt>
                    <dd>{plans
                      .filter((p) => p.available && (p.automatic || channels.includes(p.channel)))
                      .map((p) => p.label).join(', ') || '—'}</dd>
                  </div>
                </dl>
                {audienceSize > 100 && (
                  <p className="confirm-warning">
                    <span className="material-symbols-outlined">warning</span>
                    {tr(
                      `Cette diffusion touchera ${audienceSize} personnes. Elle ne pourra pas être annulée une fois envoyée.`,
                      `This will reach ${audienceSize} people and cannot be recalled once sent.`,
                    )}
                  </p>
                )}

                {channels.includes('EMAIL') && !emailBlocked && (
                  <div className="confirm-test">
                    <label htmlFor="pub-test-email">
                      {tr('Envoyer un e-mail de test à', 'Send a test e-mail to')}
                    </label>
                    <div className="confirm-test-row">
                      <input
                        id="pub-test-email"
                        type="email"
                        value={testEmail}
                        placeholder="nom@exemple.cd"
                        onChange={(event) => setTestEmail(event.target.value)}
                      />
                      <button
                        type="button"
                        className="btn btn-navy"
                        disabled={submitting || !testEmail.trim()}
                        onClick={sendTestEmail}
                      >
                        <span className="material-symbols-outlined">send</span>
                        {tr('Tester', 'Test')}
                      </button>
                    </div>
                    <small>
                      {tr('Le test enregistre d’abord un brouillon ; aucun destinataire réel n’est contacté.',
                        'Testing saves a draft first; no real recipient is contacted.')}
                    </small>
                  </div>
                )}

                <label htmlFor="pub-schedule">{tr('Programmer pour (facultatif)', 'Schedule for (optional)')}</label>
                <input
                  id="pub-schedule"
                  name="scheduledFor"
                  type="datetime-local"
                  value={form.scheduledFor}
                  onChange={update}
                />
              </div>

              {overall && (
                <div className={`publication-overall publication-overall-${overall}`}>
                  {{
                    PUBLISHED: tr('Toutes les destinations ont abouti.', 'Every destination succeeded.'),
                    PARTIAL_SUCCESS: tr(
                      'Diffusion partielle : certains canaux ont échoué ou ont été ignorés.',
                      'Partial distribution: some channels failed or were skipped.',
                    ),
                    FAILED: tr('Aucun canal n’a abouti.', 'No channel succeeded.'),
                  }[overall] || overall}
                </div>
              )}
            </>
          )}

          <div className="composer-actions">
            {step > 0 && (
              <button type="button" className="btn btn-navy" disabled={submitting} onClick={() => setStep(step - 1)}>
                <span className="material-symbols-outlined">arrow_back</span>
                {tr('Retour', 'Back')}
              </button>
            )}
            {step < 2 ? (
              <button
                type="button"
                className="btn btn-gold"
                disabled={submitting}
                onClick={() => {
                  if (step === 0 && !canLeaveContentStep()) return;
                  setStep(step + 1);
                }}
              >
                {tr('Continuer', 'Continue')}
                <span className="material-symbols-outlined">arrow_forward</span>
              </button>
            ) : (
              <>
                <button type="button" className="btn btn-navy" disabled={submitting} onClick={() => run('draft')}>
                  <span className="material-symbols-outlined">draft</span>
                  {tr('Enregistrer brouillon', 'Save draft')}
                </button>
                <button
                  type="button"
                  className="btn btn-navy"
                  disabled={submitting || !form.scheduledFor}
                  onClick={() => run('schedule')}
                >
                  <span className="material-symbols-outlined">schedule</span>
                  {tr('Programmer', 'Schedule')}
                </button>
                <button type="button" className="btn btn-gold" disabled={submitting} onClick={() => run('publish')}>
                  <span className="material-symbols-outlined">publish</span>
                  {submitting ? tr('Diffusion...', 'Distributing...') : tr('Confirmer la publication', 'Confirm publication')}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}

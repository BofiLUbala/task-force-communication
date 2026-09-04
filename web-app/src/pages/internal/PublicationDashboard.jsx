import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';
import DashboardShell from '../../components/DashboardShell';
import RichTextEditor from '../../components/RichTextEditor';
import { useAuth } from '../../context/AuthContext';
import usePreferences from '../../hooks/usePreferences';
import './Internal.css';

function isBodyEmpty(html) {
  return !html || html.replace(/<[^>]*>/g, '').trim() === '';
}

const hierarchyLinks = [
  { to: '/espace/validation', label: 'Rapports en attente' },
  { to: '/espace/publications/actualite', label: 'Publier une actualité' },
  { to: '/espace/publications/image', label: 'Publier une image' },
  { to: '/espace/publications/video', label: 'Publier une vidéo' },
  { to: '/espace/publications/communique', label: 'Publier un communiqué' },
  { to: '/espace/publications/newsletter', label: 'Publier une newsletter' },
  { to: '/espace/reseaux-sociaux', label: 'Réseaux sociaux' },
  { to: '/espace/statistiques', label: 'Statistiques' },
];

const agentLinks = [
  { to: '/espace/rapports', label: 'Mes rapports' },
  { to: '/espace/publications/actualite', label: 'Publier une actualité' },
  { to: '/espace/publications/image', label: 'Publier une image' },
  { to: '/espace/publications/video', label: 'Publier une vidéo' },
  { to: '/espace/publications/communique', label: 'Publier un communiqué' },
  { to: '/espace/publications/newsletter', label: 'Publier une newsletter' },
  { to: '/espace/reseaux-sociaux', label: 'Réseaux sociaux' },
];

const publicationTypes = {
  actualite: {
    title: 'Publier une actualité', icon: 'newspaper', category: 'ACTUALITE',
    description: 'Rédigez une information officielle avec une image de couverture facultative.',
    fileLabel: 'Image de couverture', accept: 'image/*', requiredFile: false,
  },
  image: {
    title: 'Publier une image', icon: 'image', category: 'ACTIVITE',
    description: 'Ajoutez une photographie officielle accompagnée de sa légende.',
    fileLabel: 'Fichier image', accept: 'image/*', requiredFile: true,
  },
  video: {
    title: 'Publier une vidéo', icon: 'movie', category: 'ACTIVITE',
    description: 'Publiez une vidéo officielle avec un titre et une description.',
    fileLabel: 'Fichier vidéo', accept: 'video/*', requiredFile: true,
  },
  communique: {
    title: 'Publier un communiqué', icon: 'picture_as_pdf', category: 'COMMUNIQUE',
    description: 'Diffusez un communiqué officiel et joignez son document PDF.',
    fileLabel: 'Document PDF', accept: 'application/pdf', requiredFile: true,
  },
  newsletter: {
    title: 'Publier une newsletter', icon: 'forward_to_inbox', category: 'NEWSLETTER',
    description: 'Rédigez et publiez un message officiel dans l’espace Newsletter.',
    fileLabel: 'Image de couverture', accept: 'image/*', requiredFile: false,
  },
};

const emptyForm = {
  title: '', excerpt: '', body: '', file: null,
  youtubeUrl: '', facebookUrl: '', tiktokUrl: '', linkedinUrl: '',
  newsletterSubject: '', previewText: '', senderName: 'Task Force Présidentielle', testEmail: '',
};

export default function PublicationDashboard({ type }) {
  const { user } = useAuth();
  const { tr } = usePreferences();
  const { slug: editSlug } = useParams();
  const navigate = useNavigate();
  const isEditMode = Boolean(editSlug);
  const translateLink = (link) => ({ ...link, label: ({
    'Rapports en attente': 'Pending reports', 'Mes rapports': 'My reports',
    'Publier une actualité': 'Publish news', 'Publier une image': 'Publish an image',
    'Publier une vidéo': 'Publish a video', 'Publier un communiqué': 'Publish a release',
    'Publier une newsletter': 'Publish a newsletter',
    'Réseaux sociaux': 'Social media', Statistiques: 'Statistics',
  })[link.label] || link.label });
  const links = (user?.role === 'HIERARCHY' ? hierarchyLinks : agentLinks).map((link) => tr(link, translateLink(link)));
  const rawConfig = publicationTypes[type] || publicationTypes.actualite;
  const englishConfigs = {
    actualite: { title: 'Publish news', description: 'Write official news with an optional cover image.', fileLabel: 'Cover image' },
    image: { title: 'Publish an image', description: 'Add an official photo and its caption.', fileLabel: 'Image file' },
    video: { title: 'Publish a video', description: 'Publish an official video with a title and description.', fileLabel: 'Video file' },
    communique: { title: 'Publish a release', description: 'Share an official release and attach its PDF document.', fileLabel: 'PDF document' },
    newsletter: { title: 'Publish a newsletter', description: 'Write and publish an official message in the Newsletter section.', fileLabel: 'Cover image' },
  };
  const config = { ...rawConfig, ...(tr({}, englishConfigs[type] || englishConfigs.actualite)) };
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loadingExisting, setLoadingExisting] = useState(isEditMode);
  const [existingFileUrl, setExistingFileUrl] = useState('');
  const [newsletterSentAt, setNewsletterSentAt] = useState('');
  const [newsletterStats, setNewsletterStats] = useState(null);

  useEffect(() => {
    if (!isEditMode) return;
    setLoadingExisting(true);
    client.get(`/posts/${editSlug}/`)
      .then(({ data }) => {
        const video = (data.gallery || []).find((item) => item.media_type === 'VIDEO');
        const links = Object.fromEntries((video?.social_links || []).map((link) => [link.platform.toLowerCase(), link.url]));
        setForm({
          ...emptyForm,
          title: video?.title || data.title,
          excerpt: video?.caption || data.excerpt,
          body: data.body,
          youtubeUrl: links.youtube || '',
          facebookUrl: links.facebook || '',
          tiktokUrl: links.tiktok || '',
          linkedinUrl: links.linkedin || '',
          newsletterSubject: data.newsletter_subject || data.title,
          previewText: data.newsletter_preview_text || data.excerpt,
          senderName: data.newsletter_sender_name || 'Task Force Présidentielle',
        });
        setExistingFileUrl(data.cover_image || data.attachment || '');
        setNewsletterSentAt(data.newsletter_sent_at || '');
        if (type === 'newsletter') {
          client.get(`/posts/${data.slug}/newsletter-stats/`).then((response) => setNewsletterStats(response.data)).catch(() => {});
        }
      })
      .catch(() => setError(tr('Impossible de charger cette publication.', 'Could not load this publication.')))
      .finally(() => setLoadingExisting(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEditMode, editSlug]);

  function update(event) {
    const { name, value, files } = event.target;
    setForm((current) => ({ ...current, [name]: files ? files[0] : value }));
  }

  async function submit(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const newsletterAction = event.nativeEvent.submitter?.value || 'send';
    const bodyRequired = type === 'actualite' || type === 'communique' || type === 'video' || type === 'newsletter';
    if (bodyRequired && isBodyEmpty(form.body)) {
      setError(tr('La description complète est requise.', 'The full description is required.'));
      return;
    }
    setSubmitting(true);
    setMessage('');
    setError('');
    try {
      const postData = new FormData();
      postData.append('title', form.title);
      postData.append('category', config.category);
      postData.append('excerpt', form.excerpt);
      postData.append('body', form.body || form.excerpt);
      postData.append('is_published', type === 'newsletter' ? String(Boolean(newsletterSentAt)) : 'true');
      if (type === 'newsletter') {
        postData.append('newsletter_subject', form.newsletterSubject || form.title);
        postData.append('newsletter_preview_text', form.previewText || form.excerpt);
        postData.append('newsletter_sender_name', form.senderName || 'Task Force Présidentielle');
      }
      if (form.file && (type === 'actualite' || type === 'image' || type === 'newsletter')) postData.append('cover_image', form.file);
      if (form.file && type === 'communique') postData.append('attachment', form.file);

      if (isEditMode) {
        const { data: post } = await client.patch(`/posts/${editSlug}/`, postData);
        if (type === 'newsletter') {
          await finishNewsletterAction(post, newsletterAction, form.testEmail, setMessage, tr, navigate);
          return;
        }
        if (form.file && (type === 'video' || type === 'image')) {
          const mediaData = new FormData();
          mediaData.append('file', form.file);
          mediaData.append('media_type', type === 'video' ? 'VIDEO' : 'PHOTO');
          mediaData.append('title', form.title);
          mediaData.append('caption', form.excerpt);
          if (type === 'video') mediaData.append('social_links', JSON.stringify(videoSocialLinks(form)));
          await client.post(`/posts/${post.slug}/upload-media/`, mediaData);
        }
        setMessage(tr('Modifications enregistrées.', 'Changes saved.'));
        setTimeout(() => navigate(`/publications/${post.slug}`), 900);
        return;
      }

      const { data: post } = await client.post('/posts/', postData);
      if (type === 'newsletter') {
        await finishNewsletterAction(post, newsletterAction, form.testEmail, setMessage, tr, navigate);
        return;
      }
      if (form.file && (type === 'video' || type === 'image')) {
        const mediaData = new FormData();
        mediaData.append('file', form.file);
        mediaData.append('media_type', type === 'video' ? 'VIDEO' : 'PHOTO');
        mediaData.append('title', form.title);
        mediaData.append('caption', form.excerpt);
        if (type === 'video') mediaData.append('social_links', JSON.stringify(videoSocialLinks(form)));
        await client.post(`/posts/${post.slug}/upload-media/`, mediaData);
      }
      setForm(emptyForm);
      formElement.reset();

      let socialNote = '';
      try {
        const { data: attempts } = await client.post(`/posts/${post.slug}/push-social/`);
        const sent = attempts.filter((a) => a.status === 'SENT').map((a) => a.platform_display);
        if (sent.length) socialNote = tr(` Partagé sur ${sent.join(', ')}.`, ` Shared on ${sent.join(', ')}.`);
      } catch {
        // no connected social accounts, or a platform push failed — publication itself already succeeded
      }
      setMessage(tr('Publication réussie.', 'Published successfully.') + socialNote);
    } catch (requestError) {
      const detail = requestError.response?.data;
      setError(typeof detail?.detail === 'string' ? detail.detail : tr('La publication a échoué. Vérifiez les champs et le fichier.', 'Publication failed. Check the fields and file.'));
    } finally {
      setSubmitting(false);
    }
  }

  const editTitle = tr('Modifier : ', 'Edit: ') + config.title.replace(/^Publier (une |un )?/i, '').replace(/^Publish (an? )?/i, '');

  if (loadingExisting) {
    return (
      <DashboardShell links={links}>
        <div className="dash-topbar"><h1>{config.title}</h1></div>
        <p style={{ color: 'var(--text-muted)' }}>{tr('Chargement...', 'Loading...')}</p>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell links={links}>
      <div className="dash-topbar"><h1>{isEditMode ? editTitle : config.title}</h1></div>
      <div className="publication-layout">
        <form className="publication-form" onSubmit={submit} key={type}>
          <div className="publication-form-heading">
            <span className="material-symbols-outlined">{config.icon}</span>
            <div><h2>{isEditMode ? editTitle : config.title}</h2><p>{config.description}</p></div>
          </div>
          {message && <div className="publication-success">{message}</div>}
          {error && <div className="publication-error">{error}</div>}
          <label htmlFor={`${type}-title`}>{tr('Titre', 'Title')}</label>
          <input id={`${type}-title`} name="title" value={form.title} onChange={update} required />
          <label htmlFor={`${type}-excerpt`}>{type === 'image' ? tr('Légende', 'Caption') : tr('Résumé', 'Summary')}</label>
          <input id={`${type}-excerpt`} name="excerpt" value={form.excerpt} onChange={update} required />
          {type === 'newsletter' && (
            <fieldset className="newsletter-settings">
              <legend>{tr('Paramètres de l’e-mail', 'Email settings')}</legend>
              <label htmlFor="newsletter-subject">{tr('Objet de l’e-mail', 'Email subject')}</label>
              <input id="newsletter-subject" name="newsletterSubject" value={form.newsletterSubject} onChange={update} placeholder={form.title || tr('Objet visible dans la boîte de réception', 'Subject shown in the inbox')} required />
              <label htmlFor="newsletter-preview">{tr('Texte d’aperçu', 'Preview text')}</label>
              <input id="newsletter-preview" name="previewText" value={form.previewText} onChange={update} maxLength="255" placeholder={tr('Courte phrase visible après l’objet', 'Short sentence shown after the subject')} />
              <label htmlFor="newsletter-sender">{tr('Nom de l’expéditeur', 'Sender name')}</label>
              <input id="newsletter-sender" name="senderName" value={form.senderName} onChange={update} required />
            </fieldset>
          )}
          {(type === 'actualite' || type === 'communique' || type === 'video' || type === 'newsletter') && (
            <>
              <label htmlFor={`${type}-body`}>{tr('Description complète', 'Full description')}</label>
              <RichTextEditor
                id={`${type}-body`}
                value={form.body}
                onChange={(html) => setForm((current) => ({ ...current, body: html }))}
                placeholder={tr('Rédigez le contenu complet ici...', 'Write the full content here...')}
              />
            </>
          )}
          <label htmlFor={`${type}-file`}>
            {config.fileLabel}
            {(!config.requiredFile || isEditMode) && tr(' (facultatif)', ' (optional)')}
          </label>
          {isEditMode && existingFileUrl && (
            <a href={existingFileUrl} target="_blank" rel="noopener noreferrer" className="publication-existing-file">
              <span className="material-symbols-outlined">attach_file</span>
              {tr('Fichier actuel', 'Current file')}
            </a>
          )}
          <input id={`${type}-file`} name="file" type="file" accept={config.accept} onChange={update} required={config.requiredFile && !isEditMode} />
          {type === 'video' && (
            <fieldset className="video-social-fields">
              <legend>{tr('Liens de cette vidéo sur les réseaux sociaux', 'Social links for this video')}</legend>
              <p>{tr('Ajoutez uniquement les plateformes où cette vidéo est disponible.', 'Only add platforms where this video is available.')}</p>
              {[
                ['youtubeUrl', 'YouTube'], ['facebookUrl', 'Facebook'],
                ['tiktokUrl', 'TikTok'], ['linkedinUrl', 'LinkedIn'],
              ].map(([name, label]) => (
                <div className="video-social-field" key={name}>
                  <label htmlFor={`${type}-${name}`}>{label}</label>
                  <input
                    id={`${type}-${name}`}
                    name={name}
                    type="url"
                    value={form[name]}
                    onChange={update}
                    placeholder={`https://${label.toLowerCase()}.com/...`}
                  />
                </div>
              ))}
            </fieldset>
          )}
          {type === 'newsletter' && (
            <div className="newsletter-delivery-panel">
              <strong>{tr('Destinataires', 'Recipients')}</strong>
              <p>{tr('La newsletter sera envoyée à tous les abonnés actifs. Envoyez d’abord un test pour vérifier le rendu.', 'The newsletter will be sent to all active subscribers. Send a test first to check its appearance.')}</p>
              <label htmlFor="newsletter-test-email">{tr('Adresse pour l’envoi test', 'Test email address')}</label>
              <input id="newsletter-test-email" name="testEmail" type="email" value={form.testEmail} onChange={update} placeholder="nom@exemple.com" />
              {newsletterSentAt && <div className="newsletter-stats-summary">
                <span><b>{newsletterStats?.sent ?? 0}</b> {tr('envoyé(s)', 'sent')}</span>
                <span><b>{newsletterStats?.failed ?? 0}</b> {tr('échec(s)', 'failed')}</span>
                <span>{tr('Envoi effectué le', 'Sent on')} {new Date(newsletterSentAt).toLocaleString()}</span>
              </div>}
            </div>
          )}
          {type === 'newsletter' ? (
            <div className="newsletter-actions">
              <button type="submit" value="draft" className="btn newsletter-secondary" disabled={submitting}><span className="material-symbols-outlined">draft</span>{tr('Enregistrer le brouillon', 'Save draft')}</button>
              <button type="submit" value="test" className="btn newsletter-secondary" disabled={submitting}><span className="material-symbols-outlined">send</span>{tr('Envoyer un test', 'Send test')}</button>
              {!newsletterSentAt && <button type="submit" value="send" className="btn btn-gold" disabled={submitting}><span className="material-symbols-outlined">outgoing_mail</span>{tr('Publier et envoyer', 'Publish and send')}</button>}
            </div>
          ) : <button type="submit" className="btn btn-gold publication-submit" disabled={submitting}>
            <span className="material-symbols-outlined">{isEditMode ? 'save' : 'publish'}</span>
            {submitting
              ? tr('Enregistrement...', 'Saving...')
              : (isEditMode ? tr('Enregistrer les modifications', 'Save changes') : tr('Publier maintenant', 'Publish now'))}
          </button>}
        </form>
      </div>
    </DashboardShell>
  );
}

async function finishNewsletterAction(post, action, testEmail, setMessage, tr, navigate) {
  if (action === 'test') {
    if (!testEmail.trim()) throw new Error(tr('Indiquez une adresse e-mail de test.', 'Enter a test email address.'));
    await client.post(`/posts/${post.slug}/test-newsletter/`, { email: testEmail.trim() });
    setMessage(tr('Brouillon enregistré et e-mail test envoyé.', 'Draft saved and test email sent.'));
    if (!window.location.pathname.endsWith(`/${post.slug}`)) window.history.replaceState({}, '', `/espace/publications/newsletter/${post.slug}`);
    return;
  }
  if (action === 'draft') {
    setMessage(tr('Brouillon enregistré.', 'Draft saved.'));
    if (!window.location.pathname.endsWith(`/${post.slug}`)) window.history.replaceState({}, '', `/espace/publications/newsletter/${post.slug}`);
    return;
  }
  const { data } = await client.post(`/posts/${post.slug}/send-newsletter/`);
  setMessage(tr(`Newsletter publiée et envoyée à ${data.sent} abonné(s).`, `Newsletter published and sent to ${data.sent} subscriber(s).`));
  setTimeout(() => navigate('/newsletter'), 1000);
}

function videoSocialLinks(form) {
  return [
    ['YouTube', form.youtubeUrl], ['Facebook', form.facebookUrl],
    ['TikTok', form.tiktokUrl], ['LinkedIn', form.linkedinUrl],
  ].filter(([, url]) => url?.trim()).map(([platform, url]) => ({ platform, url: url.trim() }));
}

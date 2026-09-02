import { useState } from 'react';
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
  { to: '/espace/reseaux-sociaux', label: 'Réseaux sociaux' },
  { to: '/espace/statistiques', label: 'Statistiques' },
];

const agentLinks = [
  { to: '/espace/rapports', label: 'Mes rapports' },
  { to: '/espace/publications/actualite', label: 'Publier une actualité' },
  { to: '/espace/publications/image', label: 'Publier une image' },
  { to: '/espace/publications/video', label: 'Publier une vidéo' },
  { to: '/espace/publications/communique', label: 'Publier un communiqué' },
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
};

const emptyForm = { title: '', excerpt: '', body: '', file: null };

export default function PublicationDashboard({ type }) {
  const { user } = useAuth();
  const { tr } = usePreferences();
  const translateLink = (link) => ({ ...link, label: ({
    'Rapports en attente': 'Pending reports', 'Mes rapports': 'My reports',
    'Publier une actualité': 'Publish news', 'Publier une image': 'Publish an image',
    'Publier une vidéo': 'Publish a video', 'Publier un communiqué': 'Publish a release',
    'Réseaux sociaux': 'Social media', Statistiques: 'Statistics',
  })[link.label] || link.label });
  const links = (user?.role === 'HIERARCHY' ? hierarchyLinks : agentLinks).map((link) => tr(link, translateLink(link)));
  const rawConfig = publicationTypes[type] || publicationTypes.actualite;
  const englishConfigs = {
    actualite: { title: 'Publish news', description: 'Write official news with an optional cover image.', fileLabel: 'Cover image' },
    image: { title: 'Publish an image', description: 'Add an official photo and its caption.', fileLabel: 'Image file' },
    video: { title: 'Publish a video', description: 'Publish an official video with a title and description.', fileLabel: 'Video file' },
    communique: { title: 'Publish a release', description: 'Share an official release and attach its PDF document.', fileLabel: 'PDF document' },
  };
  const config = { ...rawConfig, ...(tr({}, englishConfigs[type] || englishConfigs.actualite)) };
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  function update(event) {
    const { name, value, files } = event.target;
    setForm((current) => ({ ...current, [name]: files ? files[0] : value }));
  }

  async function submit(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const bodyRequired = type === 'actualite' || type === 'communique' || type === 'video';
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
      postData.append('is_published', 'true');
      if (form.file && (type === 'actualite' || type === 'image')) postData.append('cover_image', form.file);
      if (form.file && type === 'communique') postData.append('attachment', form.file);

      const { data: post } = await client.post('/posts/', postData);
      if (form.file && (type === 'video' || type === 'image')) {
        const mediaData = new FormData();
        mediaData.append('file', form.file);
        mediaData.append('media_type', type === 'video' ? 'VIDEO' : 'PHOTO');
        mediaData.append('caption', form.excerpt);
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

  return (
    <DashboardShell links={links}>
      <div className="dash-topbar"><h1>{config.title}</h1></div>
      <div className="publication-layout">
        <form className="publication-form" onSubmit={submit} key={type}>
          <div className="publication-form-heading">
            <span className="material-symbols-outlined">{config.icon}</span>
            <div><h2>{config.title}</h2><p>{config.description}</p></div>
          </div>
          {message && <div className="publication-success">{message}</div>}
          {error && <div className="publication-error">{error}</div>}
          <label htmlFor={`${type}-title`}>{tr('Titre', 'Title')}</label>
          <input id={`${type}-title`} name="title" value={form.title} onChange={update} required />
          <label htmlFor={`${type}-excerpt`}>{type === 'image' ? tr('Légende', 'Caption') : tr('Résumé', 'Summary')}</label>
          <input id={`${type}-excerpt`} name="excerpt" value={form.excerpt} onChange={update} required />
          {(type === 'actualite' || type === 'communique' || type === 'video') && (
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
          <label htmlFor={`${type}-file`}>{config.fileLabel}{!config.requiredFile && tr(' (facultatif)', ' (optional)')}</label>
          <input id={`${type}-file`} name="file" type="file" accept={config.accept} onChange={update} required={config.requiredFile} />
          <button type="submit" className="btn btn-gold publication-submit" disabled={submitting}>
            <span className="material-symbols-outlined">publish</span>
            {submitting ? tr('Publication...', 'Publishing...') : tr('Publier maintenant', 'Publish now')}
          </button>
        </form>
      </div>
    </DashboardShell>
  );
}

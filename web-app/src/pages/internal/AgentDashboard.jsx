import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import DashboardShell from '../../components/DashboardShell';
import usePreferences from '../../hooks/usePreferences';
import './Internal.css';

const emptyForm = { title: '', incident_type: '', location: '', description: '' };

export default function AgentDashboard() {
  const { tr, language } = usePreferences();
  const links = [
    { to: '/espace/rapports', label: tr('Mes rapports', 'My reports') },
    { to: '/espace/publications/actualite', label: tr('Publier une actualité', 'Publish news') },
    { to: '/espace/publications/image', label: tr('Publier une image', 'Publish an image') },
    { to: '/espace/publications/video', label: tr('Publier une vidéo', 'Publish a video') },
    { to: '/espace/publications/communique', label: tr('Publier un communiqué', 'Publish a release') },
    { to: '/espace/reseaux-sociaux', label: tr('Réseaux sociaux', 'Social media') },
  ];
  const publishingFeatures = [
    { to: '/espace/publications/actualite', icon: 'newspaper', title: tr('Publier une actualité', 'Publish news'), text: tr('Rédiger et diffuser une information officielle.', 'Write and share official news.') },
    { to: '/espace/publications/image', icon: 'image', title: tr('Publier une image', 'Publish an image'), text: tr('Ajouter une photo dans la galerie publique.', 'Add a photo to the public gallery.') },
    { to: '/espace/publications/video', icon: 'movie', title: tr('Publier une vidéo', 'Publish a video'), text: tr('Mettre une nouvelle vidéo à la disposition du public.', 'Make a new video available to the public.') },
    { to: '/espace/publications/communique', icon: 'picture_as_pdf', title: tr('Publier un communiqué', 'Publish a release'), text: tr('Partager un communiqué officiel avec son PDF.', 'Share an official release and its PDF.') },
    { to: '/espace/reseaux-sociaux', icon: 'share', title: tr('Réseaux sociaux', 'Social media'), text: tr('Ajouter un lien vers un réseau social affiché sur l’accueil.', 'Add a social network link shown on the homepage.') },
  ];
  const [reports, setReports] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  function loadReports() {
    client.get('/reports/').then((res) => setReports(res.data.results || res.data)).catch(() => {});
  }

  useEffect(loadReports, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await client.post('/reports/', form);
      setForm(emptyForm);
      setShowForm(false);
      loadReports();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <DashboardShell links={links}>
      <div className="dash-topbar">
        <h1>{tr('Mes rapports', 'My reports')}</h1>
        <button className="btn btn-navy" onClick={() => setShowForm((s) => !s)}>
          {showForm ? tr('Annuler', 'Cancel') : tr('Nouveau rapport', 'New report')}
        </button>
      </div>

      <section className="publishing-features" aria-labelledby="publishing-title">
        <h2 id="publishing-title">{tr('Outils de publication', 'Publishing tools')}</h2>
        <div className="publishing-feature-grid">
          {publishingFeatures.map((feature) => (
            <Link className="publishing-feature-card" to={feature.to} key={feature.to}>
              <span className="material-symbols-outlined">{feature.icon}</span>
              <div><h3>{feature.title}</h3><p>{feature.text}</p></div>
              <span className="material-symbols-outlined feature-arrow">arrow_forward</span>
            </Link>
          ))}
        </div>
      </section>

      {showForm && (
        <form className="report-form" onSubmit={handleSubmit}>
          <label>{tr('Titre', 'Title')}</label>
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />

          <label>{tr("Type d'incident", 'Incident type')}</label>
          <input value={form.incident_type} onChange={(e) => setForm({ ...form, incident_type: e.target.value })} />

          <label>{tr('Lieu', 'Location')}</label>
          <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />

          <label>{tr('Description', 'Description')}</label>
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />

          <label>{tr('Pièce jointe (photo, vidéo, PDF)', 'Attachment (photo, video, PDF)')}</label>
          <input type="file" disabled title="Envoyez le fichier après création du rapport via l'application mobile ou l'API upload_media" />

          <button type="submit" className="btn btn-gold" style={{ marginTop: 16 }} disabled={submitting}>
            {submitting ? tr('Envoi...', 'Submitting...') : tr('Soumettre le rapport', 'Submit report')}
          </button>
        </form>
      )}

      <table className="data-table">
        <thead>
          <tr><th>{tr('Titre', 'Title')}</th><th>{tr('Lieu', 'Location')}</th><th>{tr('Date', 'Date')}</th><th>{tr('Statut', 'Status')}</th></tr>
        </thead>
        <tbody>
          {reports.map((r) => (
            <tr key={r.id}>
              <td>{r.title}</td>
              <td>{r.location || '—'}</td>
              <td>{new Date(r.created_at).toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-US')}</td>
              <td><span className={`badge badge-${r.status}`}>{r.status}</span></td>
            </tr>
          ))}
          {reports.length === 0 && (
            <tr><td colSpan={4} style={{ color: 'var(--text-muted)' }}>{tr('Aucun rapport soumis pour le moment.', 'No reports submitted yet.')}</td></tr>
          )}
        </tbody>
      </table>
    </DashboardShell>
  );
}

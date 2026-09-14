import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import DashboardShell from '../../components/DashboardShell';
import PublicationFeed from '../../components/PublicationFeed';
import usePreferences from '../../hooks/usePreferences';
import { internalLinks } from '../../utils/publicationNav';
import './Internal.css';

const emptyForm = { title: '', incident_type: '', location: '', description: '' };

export default function AgentDashboard() {
  const { tr, language } = usePreferences();
  const links = internalLinks('AGENT', tr);
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
        <h2 id="publishing-title">{tr('Publier', 'Publish')}</h2>
        <div className="publishing-feature-grid">
          <Link className="publishing-feature-card" to="/espace/publications/nouvelle">
            <span className="material-symbols-outlined">post_add</span>
            <div>
              <h3>{tr('Nouvelle publication', 'New publication')}</h3>
              <p>{tr('Un seul formulaire pour tout type de contenu et toutes les destinations.', 'One form for every content type and every destination.')}</p>
            </div>
            <span className="material-symbols-outlined feature-arrow">arrow_forward</span>
          </Link>
          <Link className="publishing-feature-card" to="/espace/publications">
            <span className="material-symbols-outlined">campaign</span>
            <div>
              <h3>{tr('Mes publications', 'My publications')}</h3>
              <p>{tr('Brouillons, programmées, publiées et état de diffusion.', 'Drafts, scheduled, published and delivery status.')}</p>
            </div>
            <span className="material-symbols-outlined feature-arrow">arrow_forward</span>
          </Link>
        </div>
      </section>

      <PublicationFeed />

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

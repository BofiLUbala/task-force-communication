import { useEffect, useState } from 'react';
import client from '../../api/client';
import DashboardShell from '../../components/DashboardShell';
import './Internal.css';

const links = [{ to: '/espace/rapports', label: 'Mes rapports' }];

const emptyForm = { title: '', incident_type: '', location: '', description: '' };

export default function AgentDashboard() {
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
        <h1>Mes rapports</h1>
        <button className="btn btn-navy" onClick={() => setShowForm((s) => !s)}>
          {showForm ? 'Annuler' : 'Nouveau rapport'}
        </button>
      </div>

      {showForm && (
        <form className="report-form" onSubmit={handleSubmit}>
          <label>Titre</label>
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />

          <label>Type d'incident</label>
          <input value={form.incident_type} onChange={(e) => setForm({ ...form, incident_type: e.target.value })} />

          <label>Lieu</label>
          <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />

          <label>Description</label>
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />

          <label>Pièce jointe (photo, vidéo, PDF)</label>
          <input type="file" disabled title="Envoyez le fichier après création du rapport via l'application mobile ou l'API upload_media" />

          <button type="submit" className="btn btn-gold" style={{ marginTop: 16 }} disabled={submitting}>
            {submitting ? 'Envoi...' : 'Soumettre le rapport'}
          </button>
        </form>
      )}

      <table className="data-table">
        <thead>
          <tr><th>Titre</th><th>Lieu</th><th>Date</th><th>Statut</th></tr>
        </thead>
        <tbody>
          {reports.map((r) => (
            <tr key={r.id}>
              <td>{r.title}</td>
              <td>{r.location || '—'}</td>
              <td>{new Date(r.created_at).toLocaleDateString('fr-FR')}</td>
              <td><span className={`badge badge-${r.status}`}>{r.status}</span></td>
            </tr>
          ))}
          {reports.length === 0 && (
            <tr><td colSpan={4} style={{ color: 'var(--text-muted)' }}>Aucun rapport soumis pour le moment.</td></tr>
          )}
        </tbody>
      </table>
    </DashboardShell>
  );
}

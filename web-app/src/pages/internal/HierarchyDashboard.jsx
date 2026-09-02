import { useEffect, useMemo, useState } from 'react';
import client from '../../api/client';
import DashboardShell from '../../components/DashboardShell';
import './Internal.css';

const links = [
  { to: '/espace/validation', label: 'Rapports en attente' },
  { to: '/espace/statistiques', label: 'Statistiques' },
];

export default function HierarchyDashboard() {
  const [reports, setReports] = useState([]);
  const [statusFilter, setStatusFilter] = useState('PENDING');

  function loadReports(status) {
    client.get('/reports/', { params: status ? { status } : {} })
      .then((res) => setReports(res.data.results || res.data))
      .catch(() => {});
  }

  useEffect(() => loadReports(statusFilter), [statusFilter]);

  async function review(id, action) {
    await client.post(`/reports/${id}/review/`, { action });
    loadReports(statusFilter);
  }

  const stats = useMemo(() => ({
    pending: reports.filter((r) => r.status === 'PENDING').length,
    validated: reports.filter((r) => r.status === 'VALIDATED').length,
    rejected: reports.filter((r) => r.status === 'REJECTED').length,
  }), [reports]);

  return (
    <DashboardShell links={links}>
      <div className="dash-topbar">
        <h1>Validation des rapports</h1>
      </div>

      <div className="stats-bar">
        <div className="stat-box"><div className="stat-value">{stats.pending}</div><div className="stat-label">En attente</div></div>
        <div className="stat-box"><div className="stat-value">{stats.validated}</div><div className="stat-label">Validés</div></div>
        <div className="stat-box"><div className="stat-value">{stats.rejected}</div><div className="stat-label">Rejetés</div></div>
      </div>

      <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
        {[['PENDING', 'En attente'], ['VALIDATED', 'Validés'], ['REJECTED', 'Rejetés'], ['', 'Tous']].map(([v, l]) => (
          <button
            key={v}
            className="btn"
            style={{ background: statusFilter === v ? 'var(--navy)' : '#e6e6ea', color: statusFilter === v ? '#fff' : '#333', padding: '8px 16px' }}
            onClick={() => setStatusFilter(v)}
          >
            {l}
          </button>
        ))}
      </div>

      <table className="data-table">
        <thead>
          <tr><th>Titre</th><th>Agent</th><th>Date</th><th>Statut</th><th>Actions</th></tr>
        </thead>
        <tbody>
          {reports.map((r) => (
            <tr key={r.id}>
              <td>{r.title}</td>
              <td>{r.submitted_by_name}</td>
              <td>{new Date(r.created_at).toLocaleDateString('fr-FR')}</td>
              <td><span className={`badge badge-${r.status}`}>{r.status}</span></td>
              <td className="actions">
                {r.status === 'PENDING' && (
                  <>
                    <button className="action-btn action-approve" onClick={() => review(r.id, 'VALIDATE')}>Approuver</button>
                    <button className="action-btn action-reject" onClick={() => review(r.id, 'REJECT')}>Rejeter</button>
                  </>
                )}
              </td>
            </tr>
          ))}
          {reports.length === 0 && (
            <tr><td colSpan={5} style={{ color: 'var(--text-muted)' }}>Aucun rapport à afficher.</td></tr>
          )}
        </tbody>
      </table>
    </DashboardShell>
  );
}

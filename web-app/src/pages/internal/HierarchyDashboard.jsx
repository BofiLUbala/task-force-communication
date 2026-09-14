import { useEffect, useMemo, useState } from 'react';
import client from '../../api/client';
import DashboardShell from '../../components/DashboardShell';
import PublicationFeed from '../../components/PublicationFeed';
import usePreferences from '../../hooks/usePreferences';
import { internalLinks } from '../../utils/publicationNav';
import './Internal.css';

export default function HierarchyDashboard() {
  const { tr, language } = usePreferences();
  const links = internalLinks('HIERARCHY', tr);
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
        <h1>{tr('Validation des rapports', 'Report review')}</h1>
      </div>

      <PublicationFeed limit={3} />

      <div className="stats-bar">
        <div className="stat-box"><div className="stat-value">{stats.pending}</div><div className="stat-label">{tr('En attente', 'Pending')}</div></div>
        <div className="stat-box"><div className="stat-value">{stats.validated}</div><div className="stat-label">{tr('Validés', 'Approved')}</div></div>
        <div className="stat-box"><div className="stat-value">{stats.rejected}</div><div className="stat-label">{tr('Rejetés', 'Rejected')}</div></div>
      </div>

      <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
        {[['PENDING', tr('En attente', 'Pending')], ['VALIDATED', tr('Validés', 'Approved')], ['REJECTED', tr('Rejetés', 'Rejected')], ['', tr('Tous', 'All')]].map(([v, l]) => (
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
          <tr><th>{tr('Titre', 'Title')}</th><th>{tr('Agent', 'Agent')}</th><th>{tr('Date', 'Date')}</th><th>{tr('Statut', 'Status')}</th><th>{tr('Actions', 'Actions')}</th></tr>
        </thead>
        <tbody>
          {reports.map((r) => (
            <tr key={r.id}>
              <td>{r.title}</td>
              <td>{r.submitted_by_name}</td>
              <td>{new Date(r.created_at).toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-US')}</td>
              <td><span className={`badge badge-${r.status}`}>{r.status}</span></td>
              <td className="actions">
                {r.status === 'PENDING' && (
                  <>
                    <button className="action-btn action-approve" onClick={() => review(r.id, 'VALIDATE')}>{tr('Approuver', 'Approve')}</button>
                    <button className="action-btn action-reject" onClick={() => review(r.id, 'REJECT')}>{tr('Rejeter', 'Reject')}</button>
                  </>
                )}
              </td>
            </tr>
          ))}
          {reports.length === 0 && (
            <tr><td colSpan={5} style={{ color: 'var(--text-muted)' }}>{tr('Aucun rapport à afficher.', 'No reports to display.')}</td></tr>
          )}
        </tbody>
      </table>
    </DashboardShell>
  );
}

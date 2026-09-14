import { useCallback, useEffect, useState } from 'react';
import client from '../../api/client';
import apiError from '../../utils/apiError';
import DashboardShell from '../../components/DashboardShell';
import { useAuth } from '../../context/AuthContext';
import usePreferences from '../../hooks/usePreferences';
import { roleLabel } from '../../utils/roles';
import './Internal.css';

const emptyInvite = { email: '', first_name: '', last_name: '' };

/**
 * Account management, shared by the two managing posts: the super admin
 * provisions the single hierarchy account, the hierarchy staffs the field.
 * Which one is in play comes from the API, not from the route.
 */
export default function AccountsDashboard() {
  const { user } = useAuth();
  const { tr, language } = usePreferences();
  const isSuperAdmin = user?.role === 'SUPER_ADMIN';

  const links = isSuperAdmin
    ? [{ to: '/espace/admin', label: tr('Administration', 'Administration') }]
    : [
      { to: '/espace/validation', label: tr('Rapports en attente', 'Pending reports') },
      { to: '/espace/agents', label: tr('Comptes agents', 'Agent accounts') },
      { to: '/espace/publications/actualite', label: tr('Publier une actualité', 'Publish news') },
      { to: '/espace/publications/image', label: tr('Publier une image', 'Publish an image') },
      { to: '/espace/publications/video', label: tr('Publier une vidéo', 'Publish a video') },
      { to: '/espace/publications/communique', label: tr('Publier un communiqué', 'Publish a release') },
      { to: '/espace/publications/newsletter', label: tr('Publier une newsletter', 'Publish a newsletter') },
      { to: '/espace/reseaux-sociaux', label: tr('Réseaux sociaux', 'Social media') },
    ];

  const [accounts, setAccounts] = useState([]);
  const [overview, setOverview] = useState(null);
  const [form, setForm] = useState(emptyInvite);
  const [showForm, setShowForm] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loadFailed, setLoadFailed] = useState(false);

  // Kept free of `tr` so that merely switching theme or language never
  // re-fetches the account list; the failure is translated at render time.
  const load = useCallback(() => {
    client.get('/auth/users/')
      .then((res) => {
        setAccounts(res.data.results || res.data);
        setLoadFailed(false);
      })
      .catch(() => setLoadFailed(true));
    client.get('/auth/users/overview/')
      .then((res) => setOverview(res.data))
      .catch(() => setLoadFailed(true));
  }, []);

  useEffect(load, [load]);

  async function invite(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await client.post('/auth/invitations/', form);
      setMessage(tr(`Invitation envoyée à ${form.email}.`, `Invitation sent to ${form.email}.`));
      setForm(emptyInvite);
      setShowForm(false);
      load();
    } catch (requestError) {
      setError(apiError(requestError, tr('Envoi de l’invitation impossible.', 'Unable to send the invitation.'), tr));
    } finally {
      setBusy(false);
    }
  }

  async function act(account, path, successText) {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await client.post(`/auth/users/${account.id}/${path}/`);
      setMessage(successText);
      load();
    } catch (requestError) {
      setError(apiError(requestError, tr('Action impossible.', 'Action failed.'), tr));
    } finally {
      setBusy(false);
    }
  }

  async function confirmDelete() {
    const account = pendingDelete;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const { data } = await client.delete(`/auth/users/${account.id}/purge/`);
      setMessage(data.detail);
      setPendingDelete(null);
      load();
    } catch (requestError) {
      setError(apiError(requestError, tr('Suppression impossible.', 'Unable to delete.'), tr));
    } finally {
      setBusy(false);
    }
  }

  const managedLabel = overview ? roleLabel(overview.managed_role, tr) : '';
  const canInvite = overview ? overview.post_is_vacant || overview.managed_role === 'AGENT' : false;
  const counts = overview?.by_status || {};
  const locale = language === 'fr' ? 'fr-FR' : 'en-US';

  return (
    <DashboardShell links={links}>
      <div className="dash-topbar">
        <h1>
          {isSuperAdmin
            ? tr('Administration de la plateforme', 'Platform administration')
            : tr('Comptes agents', 'Agent accounts')}
        </h1>
        {canInvite && (
          <button className="btn btn-navy" onClick={() => setShowForm((open) => !open)}>
            {showForm
              ? tr('Annuler', 'Cancel')
              : tr(`Inviter ${managedLabel.toLowerCase()}`, `Invite ${managedLabel.toLowerCase()}`)}
          </button>
        )}
      </div>

      {message && <div className="account-notice account-notice-ok">{message}</div>}
      {error && <div className="account-notice account-notice-error">{error}</div>}
      {loadFailed && (
        <div className="account-notice account-notice-error">
          {tr('Chargement des comptes impossible.', 'Unable to load the accounts.')}
        </div>
      )}

      <div className="stats-bar">
        <div className="stat-box">
          <div className="stat-value">{counts.ACTIVE || 0}</div>
          <div className="stat-label">{tr('Actifs', 'Active')}</div>
        </div>
        <div className="stat-box">
          <div className="stat-value">{counts.INVITED || 0}</div>
          <div className="stat-label">{tr('Invitations en attente', 'Pending invitations')}</div>
        </div>
        <div className="stat-box">
          <div className="stat-value">{counts.REVOKED || 0}</div>
          <div className="stat-label">{tr('Accès révoqués', 'Revoked access')}</div>
        </div>
        {isSuperAdmin && overview && (
          <>
            <div className="stat-box">
              <div className="stat-value">{overview.platform.agents}</div>
              <div className="stat-label">{tr('Agents sur le terrain', 'Field agents')}</div>
            </div>
            <div className="stat-box">
              <div className="stat-value">{overview.platform.publications}</div>
              <div className="stat-label">{tr('Publications', 'Publications')}</div>
            </div>
          </>
        )}
      </div>

      {isSuperAdmin && overview?.post_is_vacant && (
        <div className="account-notice account-notice-warn">
          {tr(
            'Aucun compte hiérarchie n’existe actuellement. Invitez le responsable, ou laissez-le créer son compte depuis la page d’inscription — elle est rouverte tant que le poste est vacant.',
            'There is currently no hierarchy account. Invite the lead, or let them register from the signup page — it stays open while the post is vacant.',
          )}
        </div>
      )}

      {showForm && (
        <form className="report-form" onSubmit={invite}>
          <label htmlFor="invite-email">{tr('Adresse e-mail', 'Email address')}</label>
          <input
            id="invite-email"
            type="email"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            required
          />
          <label htmlFor="invite-first-name">{tr('Prénom (facultatif)', 'First name (optional)')}</label>
          <input
            id="invite-first-name"
            value={form.first_name}
            onChange={(event) => setForm({ ...form, first_name: event.target.value })}
          />
          <label htmlFor="invite-last-name">{tr('Nom (facultatif)', 'Last name (optional)')}</label>
          <input
            id="invite-last-name"
            value={form.last_name}
            onChange={(event) => setForm({ ...form, last_name: event.target.value })}
          />
          <p className="auth-note">
            {tr(
              'La personne recevra un lien valable 7 jours pour choisir son mot de passe et activer son compte.',
              'They will receive a link valid for 7 days to choose a password and activate their account.',
            )}
          </p>
          <button className="btn btn-gold" type="submit" style={{ marginTop: 16 }} disabled={busy}>
            {busy ? tr('Envoi...', 'Sending...') : tr('Envoyer l’invitation', 'Send invitation')}
          </button>
        </form>
      )}

      <table className="data-table">
        <thead>
          <tr>
            <th>{tr('Nom', 'Name')}</th>
            <th>{tr('E-mail', 'Email')}</th>
            <th>{tr('Statut', 'Status')}</th>
            <th>{tr('Dernière connexion', 'Last sign-in')}</th>
            <th>{tr('Actions', 'Actions')}</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => (
            <tr key={account.id}>
              <td>{account.full_name}</td>
              <td>{account.email}</td>
              <td><span className={`badge badge-${account.status}`}>{account.status_label}</span></td>
              <td>{account.last_login ? new Date(account.last_login).toLocaleDateString(locale) : '—'}</td>
              <td className="actions">
                {account.status === 'INVITED' && (
                  <button
                    className="action-btn action-approve"
                    disabled={busy}
                    onClick={() => act(account, 'resend-invitation', tr('Invitation renvoyée.', 'Invitation resent.'))}
                  >
                    {tr('Renvoyer', 'Resend')}
                  </button>
                )}
                {account.status === 'ACTIVE' && (
                  <button
                    className="action-btn action-reject"
                    disabled={busy}
                    onClick={() => act(account, 'revoke', tr('Accès révoqué.', 'Access revoked.'))}
                  >
                    {tr('Révoquer', 'Revoke')}
                  </button>
                )}
                {account.status === 'REVOKED' && (
                  <button
                    className="action-btn action-approve"
                    disabled={busy}
                    onClick={() => act(account, 'reactivate', tr('Accès rétabli.', 'Access restored.'))}
                  >
                    {tr('Réactiver', 'Reactivate')}
                  </button>
                )}
                <button className="action-btn action-delete" disabled={busy} onClick={() => setPendingDelete(account)}>
                  {tr('Supprimer', 'Delete')}
                </button>
              </td>
            </tr>
          ))}
          {accounts.length === 0 && (
            <tr>
              <td colSpan={5} style={{ color: 'var(--text-muted)' }}>
                {tr('Aucun compte pour le moment.', 'No accounts yet.')}
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {pendingDelete && (
        <div className="account-modal-backdrop" role="dialog" aria-modal="true">
          <div className="account-modal">
            <h2>{tr('Supprimer définitivement ce compte ?', 'Permanently delete this account?')}</h2>
            <p>
              {tr(
                `Le compte ${pendingDelete.email} sera supprimé, ainsi que tous ses rapports de terrain et toutes les publications qu’il a mises en ligne — y compris celles encore visibles sur le site public. Cette action est irréversible.`,
                `The account ${pendingDelete.email} will be deleted, along with all its field reports and every publication it put online — including those still visible on the public site. This cannot be undone.`,
              )}
            </p>
            <p className="account-modal-hint">
              {tr(
                'Pour simplement couper l’accès en conservant les données, utilisez « Révoquer ».',
                'To simply cut access while keeping the data, use “Revoke”.',
              )}
            </p>
            <div className="account-modal-actions">
              <button className="btn btn-navy" disabled={busy} onClick={() => setPendingDelete(null)}>
                {tr('Annuler', 'Cancel')}
              </button>
              <button className="btn btn-danger" disabled={busy} onClick={confirmDelete}>
                {busy ? tr('Suppression...', 'Deleting...') : tr('Supprimer définitivement', 'Delete permanently')}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardShell>
  );
}

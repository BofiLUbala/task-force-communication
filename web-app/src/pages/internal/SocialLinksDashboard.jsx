import { useEffect, useState } from 'react';
import client from '../../api/client';
import DashboardShell from '../../components/DashboardShell';
import { useAuth } from '../../context/AuthContext';
import usePreferences from '../../hooks/usePreferences';
import './Internal.css';

const emptyForm = { name: '', url: '' };

export default function SocialLinksDashboard() {
  const { user } = useAuth();
  const { tr } = usePreferences();
  const isHierarchy = user?.role === 'HIERARCHY';

  const links = [
    { to: '/espace/rapports', label: tr('Mes rapports', 'My reports') },
    { to: '/espace/validation', label: tr('Rapports en attente', 'Pending reports') },
    { to: '/espace/publications/actualite', label: tr('Publier une actualité', 'Publish news') },
    { to: '/espace/publications/image', label: tr('Publier une image', 'Publish an image') },
    { to: '/espace/publications/video', label: tr('Publier une vidéo', 'Publish a video') },
    { to: '/espace/publications/communique', label: tr('Publier un communiqué', 'Publish a release') },
    { to: '/espace/publications/newsletter', label: tr('Publier une newsletter', 'Publish a newsletter') },
    { to: '/espace/reseaux-sociaux', label: tr('Réseaux sociaux', 'Social media') },
  ].filter((link) => {
    if (link.to === '/espace/rapports') return !isHierarchy;
    if (link.to === '/espace/validation') return isHierarchy;
    return true;
  });

  const [socialLinks, setSocialLinks] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const [platforms, setPlatforms] = useState([]);
  const [connectError, setConnectError] = useState('');
  const params = new URLSearchParams(window.location.search);
  const socialConnected = params.get('social_connected');
  const socialError = params.get('social_error');

  function load() {
    client.get('/social-links/')
      .then((res) => setSocialLinks(res.data.results || res.data))
      .catch(() => {});
  }

  function loadPlatforms() {
    client.get('/social-accounts/platforms/')
      .then((res) => setPlatforms(res.data))
      .catch(() => {});
  }

  useEffect(load, []);
  useEffect(loadPlatforms, []);

  async function connect(platform) {
    setConnectError('');
    try {
      const { data } = await client.get(`/social-accounts/oauth/${platform.toLowerCase()}/start/`);
      window.location.href = data.authorize_url;
    } catch (requestError) {
      setConnectError(requestError.response?.data?.detail || tr('Connexion impossible.', 'Could not connect.'));
    }
  }

  async function disconnect(platform) {
    const account = platforms.find((p) => p.platform === platform);
    if (!account?.connected) return;
    if (!window.confirm(tr('Déconnecter ce compte ?', 'Disconnect this account?'))) return;
    const { data } = await client.get('/social-accounts/');
    const target = (data.results || data).find((a) => a.platform === platform);
    if (target) {
      await client.post(`/social-accounts/${target.id}/disconnect/`);
      loadPlatforms();
    }
  }

  async function submit(event) {
    event.preventDefault();
    setSubmitting(true);
    setMessage('');
    setError('');
    try {
      await client.post('/social-links/', form);
      setForm(emptyForm);
      setMessage(tr('Lien ajouté avec succès.', 'Link added successfully.'));
      load();
    } catch (requestError) {
      const detail = requestError.response?.data;
      setError(typeof detail?.detail === 'string' ? detail.detail : tr('L’ajout a échoué. Vérifiez le nom et le lien.', 'Adding the link failed. Check the name and URL.'));
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleActive(link) {
    await client.patch(`/social-links/${link.id}/`, { is_active: !link.is_active });
    load();
  }

  async function remove(link) {
    if (!window.confirm(tr('Supprimer ce lien ?', 'Delete this link?'))) return;
    await client.delete(`/social-links/${link.id}/`);
    load();
  }

  return (
    <DashboardShell links={links}>
      <div className="dash-topbar"><h1>{tr('Réseaux sociaux', 'Social media')}</h1></div>

      <div className="publication-layout" style={{ marginBottom: 28 }}>
        <div className="publication-form-heading">
          <span className="material-symbols-outlined">autorenew</span>
            <div>
              <h2>{tr('Publication automatique', 'Auto-publishing')}</h2>
              <p>{tr(
                'Connectez un compte LinkedIn, YouTube ou TikTok : chaque publication future y sera automatiquement partagée. YouTube et TikTok ne reçoivent que les vidéos.',
                'Connect a LinkedIn, YouTube or TikTok account: every future publication will be shared there automatically. YouTube and TikTok only receive video posts.',
              )}</p>
            </div>
          </div>
          {socialConnected && <div className="publication-success">{tr(`Compte ${socialConnected} connecté avec succès.`, `${socialConnected} account connected successfully.`)}</div>}
          {socialError && <div className="publication-error">{tr('La connexion au réseau social a échoué.', 'Connecting to the social network failed.')}</div>}
          {connectError && <div className="publication-error">{connectError}</div>}
          <table className="data-table" style={{ marginTop: 16 }}>
            <thead>
              <tr>
                <th>{tr('Plateforme', 'Platform')}</th>
                <th>{tr('Statut', 'Status')}</th>
                <th>{tr('Actions', 'Actions')}</th>
              </tr>
            </thead>
            <tbody>
              {platforms.map((p) => (
                <tr key={p.platform}>
                  <td>{p.label}</td>
                  <td>
                    {!p.configured ? (
                      <span className="badge badge-REJECTED">{tr('Non configuré', 'Not configured')}</span>
                    ) : p.connected ? (
                      <span className="badge badge-VALIDATED">{tr('Connecté', 'Connected')}{p.account_name ? ` — ${p.account_name}` : ''}</span>
                    ) : (
                      <span className="badge badge-PENDING">{tr('Non connecté', 'Not connected')}</span>
                    )}
                  </td>
                  <td className="actions">
                    {p.configured && !p.connected && (
                      <button className="action-btn action-approve" onClick={() => connect(p.platform)}>
                        {tr('Connecter', 'Connect')}
                      </button>
                    )}
                    {p.connected && (
                      <button className="action-btn action-reject" onClick={() => disconnect(p.platform)}>
                        {tr('Déconnecter', 'Disconnect')}
                      </button>
                    )}
                    {!p.configured && (
                      <span style={{ color: 'var(--text-muted)' }}>
                        {tr('Clés API à configurer côté serveur', 'API keys need server-side configuration')}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
      </div>

      <div className="publication-layout">
        <form className="publication-form" onSubmit={submit}>
          <div className="publication-form-heading">
            <span className="material-symbols-outlined">share</span>
            <div>
              <h2>{tr('Ajouter un réseau social', 'Add a social network')}</h2>
              <p>{tr('Le lien apparaîtra immédiatement dans l’espace « Suivez-nous » de la page d’accueil.', 'The link will appear immediately in the “Follow us” section of the homepage.')}</p>
            </div>
          </div>
          {message && <div className="publication-success">{message}</div>}
          {error && <div className="publication-error">{error}</div>}
          <label htmlFor="social-name">{tr('Nom du réseau', 'Network name')}</label>
          <input
            id="social-name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder={tr('Ex. Facebook, YouTube, Instagram...', 'E.g. Facebook, YouTube, Instagram...')}
            required
          />
          <label htmlFor="social-url">{tr('Lien du profil', 'Profile link')}</label>
          <input
            id="social-url"
            type="url"
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
            placeholder="https://..."
            required
          />
          <button type="submit" className="btn btn-gold publication-submit" disabled={submitting}>
            <span className="material-symbols-outlined">add_link</span>
            {submitting ? tr('Ajout...', 'Adding...') : tr('Ajouter le lien', 'Add link')}
          </button>
        </form>

        <table className="data-table" style={{ marginTop: 28 }}>
          <thead>
            <tr>
              <th>{tr('Nom', 'Name')}</th>
              <th>{tr('Lien', 'Link')}</th>
              <th>{tr('Statut', 'Status')}</th>
              <th>{tr('Ajouté par', 'Added by')}</th>
              {isHierarchy && <th>{tr('Actions', 'Actions')}</th>}
            </tr>
          </thead>
          <tbody>
            {socialLinks.map((link) => (
              <tr key={link.id}>
                <td>{link.name}</td>
                <td><a href={link.url} target="_blank" rel="noopener noreferrer">{link.url}</a></td>
                <td>
                  <span className={`badge badge-${link.is_active ? 'VALIDATED' : 'REJECTED'}`}>
                    {link.is_active ? tr('Actif', 'Active') : tr('Inactif', 'Inactive')}
                  </span>
                </td>
                <td>{link.added_by_name || '—'}</td>
                {isHierarchy && (
                  <td className="actions">
                    <button className="action-btn action-approve" onClick={() => toggleActive(link)}>
                      {link.is_active ? tr('Désactiver', 'Deactivate') : tr('Activer', 'Activate')}
                    </button>
                    <button className="action-btn action-reject" onClick={() => remove(link)}>
                      {tr('Supprimer', 'Delete')}
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {socialLinks.length === 0 && (
              <tr><td colSpan={isHierarchy ? 5 : 4} style={{ color: 'var(--text-muted)' }}>{tr('Aucun réseau social ajouté pour le moment.', 'No social network added yet.')}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </DashboardShell>
  );
}

import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import client from '../../api/client';
import DashboardShell from '../../components/DashboardShell';
import { useAuth } from '../../context/AuthContext';
import usePreferences from '../../hooks/usePreferences';
import { internalLinks } from '../../utils/publicationNav';
import { MEDIA_LABELS, STATUS_LABELS } from '../../utils/publicationTargets';
import './Internal.css';

const CHANNEL_ICONS = {
  WEB: 'public', MOBILE: 'smartphone', EMAIL: 'mail',
  WHATSAPP: 'chat', LINKEDIN: 'work', YOUTUBE: 'smart_display',
};

/**
 * One publication, end to end: its content, its audience, and what actually
 * happened on every channel it was sent to.
 *
 * Retry is offered only where the server says it is safe — a channel that
 * already delivered is never re-runnable from here, because re-sending is
 * worse than the failure it would try to fix.
 */
export default function PublicationDetail() {
  const { slug } = useParams();
  const { user } = useAuth();
  const { tr } = usePreferences();
  const links = internalLinks(user?.role, tr);

  const [post, setPost] = useState(null);
  const [deliveries, setDeliveries] = useState([]);
  const [state, setState] = useState('loading');
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  function loadDeliveries() {
    client.get(`/publications/${slug}/deliveries/`)
      .then(({ data }) => setDeliveries(data.deliveries || []))
      // An agent who is not the author may read the publication without being
      // entitled to its delivery report; that is not an error worth showing.
      .catch(() => setDeliveries([]));
  }

  useEffect(() => {
    setState('loading');
    client.get(`/publications/${slug}/`)
      .then(({ data }) => {
        setPost(data);
        setState('ready');
        // Opening the page is what "read" means for the unread badge.
        client.post(`/publications/${slug}/mark-read/`).catch(() => {});
        loadDeliveries();
      })
      .catch(() => setState('error'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  async function retry(delivery) {
    setBusy(delivery.channel);
    setNotice('');
    setError('');
    try {
      await client.post(`/publications/${slug}/deliveries/${delivery.id}/retry/`);
      setNotice(tr(`Canal ${delivery.channel} relancé.`, `Channel ${delivery.channel} retried.`));
      loadDeliveries();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || tr('Relance impossible.', 'Retry failed.'));
    } finally {
      setBusy('');
    }
  }

  if (state === 'loading') {
    return (
      <DashboardShell links={links}>
        <p className="feed-state">{tr('Chargement...', 'Loading...')}</p>
      </DashboardShell>
    );
  }
  if (state === 'error') {
    return (
      <DashboardShell links={links}>
        <div className="dash-topbar"><h1>{tr('Publication', 'Publication')}</h1></div>
        <p className="feed-state feed-state-error">
          {tr('Cette publication est introuvable ou ne vous est pas destinée.',
            'This publication does not exist, or is not addressed to you.')}
        </p>
      </DashboardShell>
    );
  }

  const photos = (post.gallery || []).filter((item) => item.media_type === 'PHOTO');
  const others = (post.gallery || []).filter((item) => item.media_type !== 'PHOTO');

  return (
    <DashboardShell links={links}>
      <div className="dash-topbar">
        <h1>{post.title}</h1>
        <Link className="btn btn-navy" to={`/espace/publications/${post.slug}/modifier`}>
          <span className="material-symbols-outlined">edit</span>
          {tr('Modifier', 'Edit')}
        </Link>
      </div>

      {notice && <div className="publication-success">{notice}</div>}
      {error && <div className="publication-error">{error}</div>}

      <div className="detail-meta">
        <span className={`badge badge-type badge-type-${post.category}`}>
          {post.category_display || post.category}
        </span>
        <span className={`badge badge-status badge-status-${post.status}`}>{post.status}</span>
        <small>{post.published_by_name}</small>
        <small>{post.published_at ? new Date(post.published_at).toLocaleString() : tr('non publiée', 'unpublished')}</small>
        <small>
          <span className="material-symbols-outlined">groups</span>
          {post.audience_display} · {post.audience_size} {tr('destinataire(s)', 'recipient(s)')}
        </small>
      </div>

      {post.cover_image && <img className="detail-cover" src={post.cover_image} alt="" />}

      <article className="detail-body" dangerouslySetInnerHTML={{ __html: post.body }} />

      {photos.length > 0 && (
        <div className="detail-gallery">
          {photos.map((photo) => (
            <figure key={photo.id}>
              <img src={photo.file} alt={photo.alt_text || ''} loading="lazy" />
              {photo.caption && <figcaption>{photo.caption}</figcaption>}
            </figure>
          ))}
        </div>
      )}

      {(others.length > 0 || (post.links || []).length > 0) && (
        <ul className="detail-attachments">
          {others.map((item) => (
            <li key={item.id}>
              <span className="material-symbols-outlined">
                {item.media_type === 'VIDEO' ? 'movie' : 'description'}
              </span>
              <a href={item.file} target="_blank" rel="noopener noreferrer">
                {item.title || item.original_filename || MEDIA_LABELS[item.media_type]}
              </a>
            </li>
          ))}
          {(post.links || []).map((link) => (
            <li key={link.id}>
              <span className="material-symbols-outlined">link</span>
              <a href={link.url} target="_blank" rel="noopener noreferrer">{link.label || link.url}</a>
            </li>
          ))}
        </ul>
      )}

      <section className="delivery-report">
        <h2>{tr('Diffusion', 'Distribution')}</h2>
        {deliveries.length === 0 ? (
          <p className="feed-state">{tr('Aucune diffusion enregistrée.', 'No distribution recorded.')}</p>
        ) : (
          <ul className="delivery-list">
            {deliveries.map((delivery) => (
              <li key={delivery.id} className={`delivery-row delivery-${delivery.status}`}>
                <span className="material-symbols-outlined delivery-icon">
                  {CHANNEL_ICONS[delivery.channel] || 'share'}
                </span>
                <div className="delivery-main">
                  <strong>{delivery.channel_label}</strong>
                  <span className={`badge badge-result-${delivery.status}`}>
                    {STATUS_LABELS[delivery.status] || delivery.status}
                  </span>
                  <p>{delivery.detail}</p>
                  {delivery.recipient_count > 0 && (
                    <small>
                      {delivery.success_count} {tr('remis', 'delivered')}
                      {delivery.failure_count > 0 && ` · ${delivery.failure_count} ${tr('échec(s)', 'failed')}`}
                      {` / ${delivery.recipient_count}`}
                    </small>
                  )}
                  {delivery.error_message && (
                    <small className="delivery-error">
                      {delivery.error_message} {delivery.error_code && <em>({delivery.error_code})</em>}
                    </small>
                  )}
                  {delivery.external_url && (
                    <a href={delivery.external_url} target="_blank" rel="noopener noreferrer">
                      {tr('Voir la publication', 'View post')}
                    </a>
                  )}
                </div>
                {delivery.is_retryable && (
                  <button
                    type="button"
                    className="btn btn-navy"
                    disabled={busy === delivery.channel}
                    onClick={() => retry(delivery)}
                  >
                    <span className="material-symbols-outlined">refresh</span>
                    {tr('Relancer', 'Retry')}
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </DashboardShell>
  );
}

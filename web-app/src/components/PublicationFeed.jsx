import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../api/client';
import usePreferences from '../hooks/usePreferences';
import './AttachmentManager.css';

const TYPE_LABELS = {
  ACTUALITE: 'Actualité',
  COMMUNIQUE: 'Communiqué',
  ACTIVITE: 'Activité',
  NEWSLETTER: 'Newsletter',
};

function relativeTime(value, tr) {
  if (!value) return '';
  const minutes = Math.round((Date.now() - new Date(value).getTime()) / 60000);
  if (minutes < 1) return tr('à l’instant', 'just now');
  if (minutes < 60) return tr(`il y a ${minutes} min`, `${minutes} min ago`);
  const hours = Math.round(minutes / 60);
  if (hours < 24) return tr(`il y a ${hours} h`, `${hours} h ago`);
  const days = Math.round(hours / 24);
  return tr(`il y a ${days} j`, `${days} d ago`);
}

function previewText(post) {
  if (post.excerpt) return post.excerpt;
  return (post.body || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 180);
}

function coverOf(post) {
  if (post.cover_image) return post.cover_image;
  const photo = (post.gallery || []).find((item) => item.media_type === 'PHOTO');
  return photo?.file || '';
}

/**
 * The internal feed shown on the signed-in home page.
 *
 * The list comes from `/publications/feed/`, which the server has already
 * filtered against the reader's audience — this component never decides who
 * may see what.
 */
export default function PublicationFeed({ limit = 5 }) {
  const { tr } = usePreferences();
  const [posts, setPosts] = useState([]);
  const [unread, setUnread] = useState(0);
  const [state, setState] = useState('loading');

  useEffect(() => {
    let cancelled = false;
    client.get('/publications/feed/')
      .then(({ data }) => {
        if (cancelled) return;
        setPosts((data.results || []).slice(0, limit));
        setUnread(data.unread_count || 0);
        setState('ready');
      })
      .catch(() => !cancelled && setState('error'));
    return () => { cancelled = true; };
  }, [limit]);

  if (state === 'loading') {
    return <p className="feed-state">{tr('Chargement des publications...', 'Loading publications...')}</p>;
  }
  if (state === 'error') {
    return (
      <p className="feed-state feed-state-error">
        {tr('Impossible de charger les publications.', 'Could not load publications.')}
      </p>
    );
  }

  return (
    <section className="publication-feed">
      <div className="feed-head">
        <h2>{tr('Publications récentes', 'Recent publications')}</h2>
        {unread > 0 && (
          <span className="feed-unread">
            {tr(`${unread} nouvelle(s) publication(s)`, `${unread} new publication(s)`)}
          </span>
        )}
      </div>

      {posts.length === 0 ? (
        <p className="feed-state">
          {tr('Aucune publication ne vous concerne pour le moment.', 'No publication concerns you yet.')}
        </p>
      ) : (
        <ul className="feed-list">
          {posts.map((post) => {
            const cover = coverOf(post);
            return (
              <li key={post.id} className={post.is_read ? 'feed-card' : 'feed-card feed-card-unread'}>
                <div className="feed-card-head">
                  <span className={`badge badge-type badge-type-${post.category}`}>
                    {TYPE_LABELS[post.category] || post.category}
                  </span>
                  <small>{relativeTime(post.published_at || post.created_at, tr)}</small>
                </div>
                <h3>{post.title}</h3>
                {cover && <img className="feed-cover" src={cover} alt="" loading="lazy" />}
                <p className="feed-preview">{previewText(post)}</p>
                <div className="feed-card-foot">
                  {post.published_by_name && <small>{post.published_by_name}</small>}
                  <Link className="feed-read" to={`/espace/publications/${post.slug}`}>
                    {tr('Lire la publication', 'Read publication')}
                    <span className="material-symbols-outlined">arrow_forward</span>
                  </Link>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

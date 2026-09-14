import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import DashboardShell from '../../components/DashboardShell';
import { useAuth } from '../../context/AuthContext';
import usePreferences from '../../hooks/usePreferences';
import { internalLinks } from '../../utils/publicationNav';
import { CHANNELS, PUBLICATION_TYPES } from '../../utils/publicationTargets';
import './Internal.css';

const FILTERS = [
  { value: 'all', label: 'Toutes' },
  { value: 'drafts', label: 'Brouillons' },
  { value: 'scheduled', label: 'Programmées' },
  { value: 'published', label: 'Publiées' },
  { value: 'failed', label: 'Échecs de diffusion' },
];

const CHANNEL_ORDER = CHANNELS.map((entry) => entry.channel);

function matchesFilter(post, filter) {
  if (filter === 'drafts') return !post.is_published && post.status === 'DRAFT';
  if (filter === 'scheduled') return post.status === 'SCHEDULED';
  if (filter === 'published') return post.is_published;
  if (filter === 'failed') {
    return (post.deliveries || []).some((row) => row.status === 'FAILED');
  }
  return true;
}

/**
 * The single publications dashboard.
 *
 * It replaces the five per-type screens: type is a filter here, not a separate
 * feature with its own form, its own route and its own publishing path.
 */
export default function PublicationsHome({ initialFilter = 'all' }) {
  const { user } = useAuth();
  const { tr } = usePreferences();
  const links = internalLinks(user?.role, tr);

  const [posts, setPosts] = useState([]);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState(initialFilter);
  const [category, setCategory] = useState('');
  const [mineOnly, setMineOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => setFilter(initialFilter), [initialFilter]);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      // The management list must include drafts, which `/publications/` hides
      // from anonymous callers but serves to their author and the hierarchy.
      client.get('/publications/', { params: { page_size: 100 } }),
      client.get('/publications/stats/'),
    ])
      .then(([list, counters]) => {
        setPosts(list.data.results || list.data);
        setStats(counters.data);
      })
      .catch(() => setPosts([]))
      .finally(() => setLoading(false));
  }, []);

  const visible = useMemo(() => posts.filter((post) => (
    matchesFilter(post, filter)
    && (!category || post.category === category)
    && (!mineOnly || post.published_by === user?.id)
  )), [posts, filter, category, mineOnly, user]);

  return (
    <DashboardShell links={links}>
      <div className="dash-topbar">
        <h1>{tr('Publications', 'Publications')}</h1>
        <Link className="btn btn-gold" to="/espace/publications/nouvelle">
          <span className="material-symbols-outlined">add</span>
          {tr('Nouvelle publication', 'New publication')}
        </Link>
      </div>

      <div className="pub-stat-grid">
        {[
          ['published', tr('Publiées', 'Published'), 'publish'],
          ['drafts', tr('Brouillons', 'Drafts'), 'draft'],
          ['scheduled', tr('Programmées', 'Scheduled'), 'schedule'],
          ['failed_deliveries', tr('Diffusions en échec', 'Failed deliveries'), 'error'],
        ].map(([key, label, icon]) => (
          <div className={`pub-stat pub-stat-${key}`} key={key}>
            <span className="material-symbols-outlined">{icon}</span>
            <div>
              <strong>{stats ? stats[key] : '—'}</strong>
              <small>{label}</small>
            </div>
          </div>
        ))}
      </div>

      <div className="pub-filters">
        <div className="pub-filter-tabs" role="tablist">
          {FILTERS.map((entry) => (
            <button
              key={entry.value}
              type="button"
              role="tab"
              aria-selected={filter === entry.value}
              className={filter === entry.value ? 'pub-tab pub-tab-active' : 'pub-tab'}
              onClick={() => setFilter(entry.value)}
            >
              {entry.label}
            </button>
          ))}
        </div>
        <div className="pub-filter-side">
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">{tr('Tous les types', 'All types')}</option>
            {PUBLICATION_TYPES.map((type) => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
          <label className="pub-mine">
            <input
              type="checkbox"
              checked={mineOnly}
              onChange={(event) => setMineOnly(event.target.checked)}
            />
            {tr('Mes publications', 'My publications')}
          </label>
        </div>
      </div>

      {loading ? (
        <p className="feed-state">{tr('Chargement...', 'Loading...')}</p>
      ) : visible.length === 0 ? (
        <p className="feed-state">{tr('Aucune publication pour ce filtre.', 'No publication for this filter.')}</p>
      ) : (
        <ul className="pub-list">
          {visible.map((post) => {
            const byChannel = Object.fromEntries(
              (post.deliveries || []).map((row) => [row.channel, row]),
            );
            return (
              <li className="pub-row" key={post.id}>
                <div className="pub-row-main">
                  <Link className="pub-row-title" to={`/espace/publications/${post.slug}`}>
                    {post.title}
                  </Link>
                  <div className="pub-row-meta">
                    <span className={`badge badge-type badge-type-${post.category}`}>
                      {post.category_display || post.category}
                    </span>
                    <span className={`badge badge-status badge-status-${post.status}`}>
                      {post.status}
                    </span>
                    <small>{post.audience_display}</small>
                    {post.published_by_name && <small>· {post.published_by_name}</small>}
                  </div>
                </div>

                <ul className="pub-channel-strip">
                  {CHANNEL_ORDER.map((channel) => {
                    const row = byChannel[channel];
                    const state = row ? row.status : 'NONE';
                    return (
                      <li key={channel} className={`chan chan-${state}`} title={row?.detail || channel}>
                        <span className="chan-name">{channel}</span>
                        <span className="material-symbols-outlined">
                          {{
                            SUCCESS: 'check_circle', FAILED: 'cancel', SKIPPED: 'remove_circle',
                            PENDING: 'schedule', PROCESSING: 'sync',
                          }[state] || 'remove'}
                        </span>
                      </li>
                    );
                  })}
                </ul>

                <div className="pub-row-actions">
                  <Link className="btn btn-navy" to={`/espace/publications/${post.slug}/modifier`}>
                    <span className="material-symbols-outlined">edit</span>
                    {tr('Modifier', 'Edit')}
                  </Link>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </DashboardShell>
  );
}

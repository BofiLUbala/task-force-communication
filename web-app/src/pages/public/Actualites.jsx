import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import './Listing.css';
import usePreferences from '../../hooks/usePreferences';

const categories = [
  { value: '', label: 'Toutes' },
  { value: 'COMMUNIQUE', label: 'Communiqués' },
  { value: 'ACTUALITE', label: 'Actualités' },
  { value: 'ACTIVITE', label: 'Activités' },
];

export default function Actualites() {
  const { tr, language } = usePreferences();
  const [posts, setPosts] = useState([]);
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    client.get('/posts/', { params: category ? { category } : {} })
      .then((res) => setPosts(res.data.results || res.data))
      .catch(() => setPosts([]));
  }, [category]);

  const filtered = posts.filter((p) => p.title.toLowerCase().includes(search.toLowerCase()));

  return (
    <>
      <div className="page-header">
        <div className="container">
          <Link to="/" className="page-back-link">
            <span className="material-symbols-outlined">arrow_back</span>
            {tr('Retour à l’accueil', 'Back to home')}
          </Link>
          <h1>{tr('Actualités', 'News')}</h1>
          <p>{tr('Communiqués officiels et annonces de la Task Force Présidentielle.', 'Official releases and Presidential Task Force announcements.')}</p>
        </div>
      </div>
      <div className="listing-layout">
        <div className="news-list">
          {filtered.length === 0 && <p style={{ color: 'var(--text-muted)' }}>{tr('Aucune publication trouvée.', 'No publications found.')}</p>}
          {filtered.map((post) => (
            <article className="news-item" key={post.id}>
              <div className="news-thumb" style={post.cover_image ? { backgroundImage: `url(${post.cover_image})`, backgroundSize: 'cover' } : undefined} />
              <div className="news-body">
                <div className="news-date">
                  <span className="material-symbols-outlined">calendar_today</span>
                  {new Date(post.published_at || post.created_at).toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-US')}
                </div>
                <h3 className="news-title">{post.title}</h3>
                <p className="news-excerpt">{post.excerpt}</p>
              </div>
            </article>
          ))}
        </div>
        <aside className="sidebar">
          <input
            className="search-input"
            placeholder={tr('Rechercher...', 'Search...')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="sidebar-box">
            <h4>{tr('Catégories', 'Categories')}</h4>
            <ul>
              {categories.map((c) => (
                <li
                  key={c.value}
                  style={{ cursor: 'pointer', fontWeight: category === c.value ? 700 : 400 }}
                  onClick={() => setCategory(c.value)}
                >
                  {tr(c.label, ({ Toutes: 'All', Communiqués: 'Releases', Actualités: 'News', Activités: 'Activities' })[c.label] || c.label)}
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </>
  );
}

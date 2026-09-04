import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import Pagination from '../../components/Pagination';
import './Listing.css';
import usePreferences from '../../hooks/usePreferences';

const PAGE_SIZE = 20;

const categories = [
  { value: '', label: 'Toutes' },
  { value: 'COMMUNIQUE', label: 'Communiqués' },
  { value: 'ACTUALITE', label: 'Actualités' },
  { value: 'ACTIVITE', label: 'Activités' },
];

export default function Actualites() {
  const { tr, language } = usePreferences();
  const [posts, setPosts] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    client.get('/posts/', { params: { ...(category ? { category } : { exclude_category: 'NEWSLETTER' }), page } })
      .then((res) => {
        setPosts(res.data.results || res.data);
        setCount(res.data.count ?? (res.data.results || res.data).length);
      })
      .catch(() => { setPosts([]); setCount(0); })
      .finally(() => setLoading(false));
  }, [category, page]);

  const filtered = search ? posts.filter((p) => p.title.toLowerCase().includes(search.toLowerCase())) : posts;

  function selectCategory(value) {
    setCategory(value);
    setPage(1);
  }

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
          {!loading && filtered.length === 0 && <p style={{ color: 'var(--text-muted)' }}>{tr('Aucune publication trouvée.', 'No publications found.')}</p>}
          {filtered.map((post) => (
            <Link to={`/publications/${post.slug}`} className="news-item-title-only" key={post.id}>
              <div className="news-date">
                <span className="material-symbols-outlined">calendar_today</span>
                {new Date(post.published_at || post.created_at).toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-US')}
              </div>
              <h3>{post.title}</h3>
              <span className="material-symbols-outlined news-item-arrow">chevron_right</span>
            </Link>
          ))}

          {!search && <Pagination page={page} pageSize={PAGE_SIZE} count={count} onChange={setPage} />}
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
                  onClick={() => selectCategory(c.value)}
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

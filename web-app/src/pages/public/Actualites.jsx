import { useEffect, useState } from 'react';
import client from '../../api/client';
import './Listing.css';

const categories = [
  { value: '', label: 'Toutes' },
  { value: 'COMMUNIQUE', label: 'Communiqués' },
  { value: 'ACTUALITE', label: 'Actualités' },
  { value: 'ACTIVITE', label: 'Activités' },
];

export default function Actualites() {
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
          <h1>Actualités</h1>
          <p>Communiqués officiels et annonces de la Task Force Présidentielle.</p>
        </div>
      </div>
      <div className="listing-layout">
        <div className="news-list">
          {filtered.length === 0 && <p style={{ color: 'var(--text-muted)' }}>Aucune publication trouvée.</p>}
          {filtered.map((post) => (
            <article className="news-item" key={post.id}>
              <div className="news-thumb" style={post.cover_image ? { backgroundImage: `url(${post.cover_image})`, backgroundSize: 'cover' } : undefined} />
              <div className="news-body">
                <div className="news-date">
                  <span className="material-symbols-outlined">calendar_today</span>
                  {new Date(post.published_at || post.created_at).toLocaleDateString('fr-FR')}
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
            placeholder="Rechercher..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="sidebar-box">
            <h4>Catégories</h4>
            <ul>
              {categories.map((c) => (
                <li
                  key={c.value}
                  style={{ cursor: 'pointer', fontWeight: category === c.value ? 700 : 400 }}
                  onClick={() => setCategory(c.value)}
                >
                  {c.label}
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </>
  );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import Pagination from '../../components/Pagination';
import './Listing.css';
import usePreferences from '../../hooks/usePreferences';

const PAGE_SIZE = 20;

export default function Activites() {
  const { tr, language } = usePreferences();
  const [posts, setPosts] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    client.get('/posts/', { params: { category: 'ACTIVITE', page } })
      .then((res) => {
        setPosts(res.data.results || res.data);
        setCount(res.data.count ?? (res.data.results || res.data).length);
      })
      .catch(() => { setPosts([]); setCount(0); })
      .finally(() => setLoading(false));
  }, [page]);

  return (
    <>
      <div className="page-header">
        <div className="container">
          <Link to="/" className="page-back-link">
            <span className="material-symbols-outlined">arrow_back</span>
            {tr('Retour à l’accueil', 'Back to home')}
          </Link>
          <h1>{tr('Activités', 'Activities')}</h1>
          <p>{tr('Suivi des projets prioritaires impulsés par la Présidence de la République.', 'Monitoring priority projects led by the Presidency of the Republic.')}</p>
        </div>
      </div>
      <div className="listing-layout">
        <div className="news-list">
          {!loading && posts.length === 0 && <p style={{ color: 'var(--text-muted)' }}>{tr('Aucune activité publiée pour le moment.', 'No activities have been published yet.')}</p>}
          {posts.map((post) => (
            <Link to={`/publications/${post.slug}`} className="news-item-title-only" key={post.id}>
              <div className="news-date">
                <span className="material-symbols-outlined">calendar_today</span>
                {new Date(post.published_at || post.created_at).toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-US')}
              </div>
              <h3>{post.title}</h3>
              <span className="material-symbols-outlined news-item-arrow">chevron_right</span>
            </Link>
          ))}

          <Pagination page={page} pageSize={PAGE_SIZE} count={count} onChange={setPage} />
        </div>
        <aside className="sidebar">
          <div className="sidebar-box">
            <h4>{tr('Catégories', 'Categories')}</h4>
            <ul>
              <li>{tr('Infrastructures', 'Infrastructure')}</li>
              <li>{tr('Économie', 'Economy')}</li>
              <li>{tr('Social', 'Social')}</li>
              <li>{tr('Gouvernance', 'Governance')}</li>
            </ul>
          </div>
        </aside>
      </div>
    </>
  );
}

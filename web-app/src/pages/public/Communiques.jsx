import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import Pagination from '../../components/Pagination';
import usePreferences from '../../hooks/usePreferences';
import './Listing.css';

const PAGE_SIZE = 20;

export default function Communiques() {
  const { tr, language } = usePreferences();
  const [posts, setPosts] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    client.get('/posts/', { params: { category: 'COMMUNIQUE', page } })
      .then(({ data }) => {
        setPosts(data.results || data);
        setCount(data.count ?? (data.results || data).length);
      })
      .catch(() => { setPosts([]); setCount(0); })
      .finally(() => setLoading(false));
  }, [page]);

  return <main>
    <div className="page-header communiques-page-header">
      <div className="container">
        <Link to="/" className="page-back-link"><span className="material-symbols-outlined">arrow_back</span>{tr('Retour à l’accueil', 'Back to home')}</Link>
        <span className="communiques-eyebrow">{tr('PUBLICATIONS OFFICIELLES', 'OFFICIAL PUBLICATIONS')}</span>
        <h1>{tr('Communiqués', 'Releases')}</h1>
        <p>{tr('Tous les communiqués officiels de la Task Force Présidentielle.', 'All official Presidential Task Force releases.')}</p>
      </div>
    </div>
    <section className="communiques-section">
      <div className="communiques-list-heading">
        <div><span className="material-symbols-outlined">campaign</span><div><h2>{tr('Derniers communiqués', 'Latest releases')}</h2><p>{tr('Informations et annonces officielles', 'Official information and announcements')}</p></div></div>
        {!loading && <span className="communiques-count">{count} {tr(count > 1 ? 'communiqués' : 'communiqué', count === 1 ? 'release' : 'releases')}</span>}
      </div>
      <div className="news-list">
        {!loading && posts.length === 0 && <p className="newsletter-list-empty">{tr('Aucun communiqué publié pour le moment.', 'No release has been published yet.')}</p>}
        {posts.map((post) => <Link to={`/publications/${post.slug}`} className="communique-row" key={post.id}>
          <time dateTime={post.published_at || post.created_at} className="communique-date">
            <strong>{new Date(post.published_at || post.created_at).toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-US', { day: '2-digit' })}</strong>
            <span>{new Date(post.published_at || post.created_at).toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-US', { month: 'short', year: 'numeric' })}</span>
          </time>
          <div className="communique-row-copy">
            <span className="communique-type">{tr('Communiqué officiel', 'Official release')}</span>
            <h3>{post.title}</h3>
            {post.excerpt && <p>{post.excerpt}</p>}
          </div>
          <span className="communique-open"><span className="material-symbols-outlined">arrow_forward</span></span>
        </Link>)}
        <Pagination page={page} pageSize={PAGE_SIZE} count={count} onChange={setPage} />
      </div>
    </section>
  </main>;
}

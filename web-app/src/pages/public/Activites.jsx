import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import './Listing.css';
import usePreferences from '../../hooks/usePreferences';

export default function Activites() {
  const { tr, language } = usePreferences();
  const [posts, setPosts] = useState([]);

  useEffect(() => {
    client.get('/posts/', { params: { category: 'ACTIVITE' } })
      .then((res) => setPosts(res.data.results || res.data))
      .catch(() => setPosts([]));
  }, []);

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
          {posts.length === 0 && <p style={{ color: 'var(--text-muted)' }}>{tr('Aucune activité publiée pour le moment.', 'No activities have been published yet.')}</p>}
          {posts.map((post) => (
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

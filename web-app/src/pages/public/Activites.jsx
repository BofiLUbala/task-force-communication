import { useEffect, useState } from 'react';
import client from '../../api/client';
import './Listing.css';

export default function Activites() {
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
          <h1>Activités</h1>
          <p>Suivi des projets prioritaires impulsés par la Présidence de la République.</p>
        </div>
      </div>
      <div className="listing-layout">
        <div className="news-list">
          {posts.length === 0 && <p style={{ color: 'var(--text-muted)' }}>Aucune activité publiée pour le moment.</p>}
          {posts.map((post) => (
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
          <div className="sidebar-box">
            <h4>Catégories</h4>
            <ul>
              <li>Infrastructures</li>
              <li>Économie</li>
              <li>Social</li>
              <li>Gouvernance</li>
            </ul>
          </div>
        </aside>
      </div>
    </>
  );
}

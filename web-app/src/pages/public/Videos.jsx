import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import './Listing.css';
import usePreferences from '../../hooks/usePreferences';

export default function Videos() {
  const { tr, language } = usePreferences();
  const [videos, setVideos] = useState([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    client.get('/posts/')
      .then((res) => {
        const posts = res.data.results || res.data;
        setVideos(posts.flatMap((post) => (post.gallery || [])
          .filter((media) => media.media_type === 'VIDEO')
          .map((media) => ({
            id: media.id,
            title: post.title,
            caption: media.caption || post.excerpt,
            date: post.published_at || post.created_at,
            src: media.file,
          }))));
      })
      .catch(() => setVideos([]))
      .finally(() => setLoaded(true));
  }, []);

  return (
    <div className="gallery-page">
      <div className="page-header" style={{ maxWidth: 1440, margin: '0 auto' }}>
        <Link to="/" className="page-back-link">
          <span className="material-symbols-outlined">arrow_back</span>
          {tr('Retour à l’accueil', 'Back to home')}
        </Link>
        <h1>{tr('Vidéos', 'Videos')}</h1>
        <p>{tr('Toutes les vidéos officielles publiées par la Task Force Présidentielle.', 'All official videos published by the Presidential Task Force.')}</p>
      </div>
      <div className="masonry">
        {loaded && videos.length === 0 && (
          <p className="masonry-empty">{tr('Aucune vidéo publiée pour le moment.', 'No video published yet.')}</p>
        )}
        {videos.map((item) => (
          <div className="masonry-item" key={item.id}>
            <video controls preload="metadata" playsInline aria-label={item.title}>
              <source src={item.src} />
              Votre navigateur ne prend pas en charge la lecture vidéo.
            </video>
            <div className="video-caption">
              <strong>{item.title}</strong>
              <span>{new Date(item.date).toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-US')}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

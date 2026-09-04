import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import './Listing.css';
import usePreferences from '../../hooks/usePreferences';
import { socialIconFor } from '../../utils/socialIcons';

export default function Videos() {
  const { tr, language } = usePreferences();
  const [videos, setVideos] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    client.get('/posts/')
      .then((res) => {
        const posts = res.data.results || res.data;
        setVideos(posts.flatMap((post) => (post.gallery || [])
          .filter((media) => media.media_type === 'VIDEO')
          .map((media) => ({
            id: media.id,
            title: media.title || post.title,
            caption: media.caption || post.excerpt,
            date: post.published_at || post.created_at,
            src: media.file,
            platformLinks: media.social_links?.length ? media.social_links : (post.platform_links || []),
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
        {videos.map((item) => {
          const expanded = expandedId === item.id;
          return (
            <div className="masonry-item" key={item.id}>
              <video controls preload="metadata" playsInline aria-label={item.title}>
                <source src={item.src} />
                Votre navigateur ne prend pas en charge la lecture vidéo.
              </video>
              <div className="video-caption">
                <button
                  type="button"
                  className="video-name-toggle"
                  onClick={() => setExpandedId(expanded ? null : item.id)}
                  aria-expanded={expanded}
                >
                  <strong>{item.title}</strong>
                  <span className="material-symbols-outlined">{expanded ? 'expand_less' : 'expand_more'}</span>
                </button>
                <span>{new Date(item.date).toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-US')}</span>

                {expanded && (
                  <div className="video-platforms">
                    <p className="video-platforms-label">{tr('Regarder sur', 'Watch on')}</p>
                    {item.platformLinks.length > 0 ? (
                      <div className="video-platform-links">
                        {item.platformLinks.map((link) => {
                          const platformName = link.platform_display || link.platform;
                          const { icon, color } = socialIconFor(platformName);
                          return (
                            <a
                              key={link.platform}
                              href={link.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="video-platform-link"
                              style={{ '--social-color': color }}
                            >
                              <span className="material-symbols-outlined">{icon}</span>
                              {platformName}
                            </a>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="video-platforms-empty">
                        {tr('Pas encore disponible sur les réseaux sociaux.', 'Not yet available on social media.')}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

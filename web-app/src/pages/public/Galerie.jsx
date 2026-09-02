import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import './Listing.css';
import usePreferences from '../../hooks/usePreferences';

export default function Galerie() {
  const { tr } = usePreferences();
  const [media, setMedia] = useState([]);
  const [filter, setFilter] = useState('ALL');

  useEffect(() => {
    client.get('/posts/')
      .then((res) => {
        const posts = res.data.results || res.data;
        const items = posts.flatMap((p) => p.gallery || []);
        setMedia(items);
      })
      .catch(() => setMedia([]));
  }, []);

  const filtered = media.filter((m) => filter === 'ALL' || m.media_type === filter);

  return (
    <div className="gallery-page">
      <div className="page-header" style={{ maxWidth: 1440, margin: '0 auto' }}>
        <Link to="/" className="page-back-link">
          <span className="material-symbols-outlined">arrow_back</span>
          {tr('Retour à l’accueil', 'Back to home')}
        </Link>
        <h1>{tr('Galerie', 'Gallery')}</h1>
        <p>{tr('Photothèque et vidéothèque officielle des activités de terrain.', 'Official photo and video gallery of field activities.')}</p>
      </div>
      <div className="gallery-tabs">
        {[['ALL', tr('Toutes', 'All')], ['PHOTO', tr('Photos', 'Photos')], ['VIDEO', tr('Vidéos', 'Videos')]].map(([value, label]) => (
          <button key={value} className={`gallery-tab ${filter === value ? 'active' : ''}`} onClick={() => setFilter(value)}>
            {label}
          </button>
        ))}
      </div>
      <div className="masonry">
        {filtered.length === 0 && <p className="masonry-empty">{tr('Aucun média disponible.', 'No media available.')}</p>}
        {filtered.map((item) => (
          <div className="masonry-item" key={item.id}>
            {item.media_type === 'PHOTO' ? (
              <img src={item.file} alt={item.caption} />
            ) : (
              <video controls preload="metadata" playsInline aria-label={item.caption || 'Vidéo de la Task Force'}>
                <source src={item.file} />
                Votre navigateur ne prend pas en charge la lecture vidéo.
              </video>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

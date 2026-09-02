import { useEffect, useState } from 'react';
import client from '../../api/client';
import './Listing.css';

export default function Galerie() {
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
        <h1>Galerie</h1>
        <p>Photothèque et vidéothèque officielle des activités de terrain.</p>
      </div>
      <div className="gallery-tabs">
        {[['ALL', 'Toutes'], ['PHOTO', 'Photos'], ['VIDEO', 'Vidéos']].map(([value, label]) => (
          <button key={value} className={`gallery-tab ${filter === value ? 'active' : ''}`} onClick={() => setFilter(value)}>
            {label}
          </button>
        ))}
      </div>
      <div className="masonry">
        {filtered.length === 0 && <p className="masonry-empty">Aucun média disponible.</p>}
        {filtered.map((item) => (
          <div className="masonry-item" key={item.id}>
            {item.media_type === 'PHOTO' ? (
              <img src={item.file} alt={item.caption} />
            ) : (
              <div className="play-icon"><span className="material-symbols-outlined">play_circle</span></div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

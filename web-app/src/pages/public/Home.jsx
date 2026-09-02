import { useEffect, useState } from 'react';
import client from '../../api/client';
import './Home.css';
import usePreferences from '../../hooks/usePreferences';

const SOCIAL_ICONS = [
  { match: /facebook/i, icon: 'thumb_up', color: '#1877F2' },
  { match: /instagram/i, icon: 'photo_camera', color: '#E1306C' },
  { match: /twitter|^x$|\bx\b/i, icon: 'tag', color: '#000000' },
  { match: /youtube/i, icon: 'smart_display', color: '#FF0000' },
  { match: /linkedin/i, icon: 'work', color: '#0A66C2' },
  { match: /tiktok/i, icon: 'music_note', color: '#000000' },
  { match: /whatsapp/i, icon: 'chat', color: '#25D366' },
  { match: /telegram/i, icon: 'send', color: '#26A5E4' },
];

function socialIconFor(name) {
  const found = SOCIAL_ICONS.find((entry) => entry.match.test(name || ''));
  return found || { icon: 'public', color: 'var(--primary)' };
}

export default function Home() {
  const { tr } = usePreferences();
  const [briefs, setBriefs] = useState([]);
  const [videos, setVideos] = useState([]);
  const [activeVideo, setActiveVideo] = useState(0);
  const [socialLinks, setSocialLinks] = useState([]);
  const [newsletterEmail, setNewsletterEmail] = useState('');
  const [newsletterSent, setNewsletterSent] = useState(false);

  useEffect(() => {
    client.get('/posts/')
      .then((res) => {
        const posts = res.data.results || res.data;
        setBriefs(posts.slice(0, 2));
        setVideos(posts.flatMap((post) => (post.gallery || [])
          .filter((media) => media.media_type === 'VIDEO')
          .map((media) => ({
            id: media.id,
            title: post.title,
            description: media.caption || post.excerpt,
            src: media.file,
          }))));
      })
      .catch(() => {});
    client.get('/social-links/')
      .then((res) => setSocialLinks(res.data.results || res.data))
      .catch(() => {});
  }, []);

  function handleNewsletterSubmit(e) {
    e.preventDefault();
    if (!newsletterEmail.trim()) return;
    setNewsletterSent(true);
    setNewsletterEmail('');
  }

  return (
    <>
      <section className="hero">
        <div className="hero-bg" />
        <div className="hero-gradient" />
        <div className="hero-content">
          <img className="hero-flag" src="/flag-drc.svg" alt="Drapeau de la RDC" />
          <h2 className="hero-title">{tr('Task Force Présidentielle', 'Presidential Task Force')}</h2>
          <p className="hero-subtitle">
            {tr('Supervision, Coordination et Transparence des Projets Stratégiques de la Nation.', 'Supervision, coordination and transparency for the nation’s strategic projects.')}
          </p>
          <div className="hero-actions">
            <button className="btn btn-gold hero-btn">
              <span className="material-symbols-outlined">description</span>
              {tr('Derniers rapports', 'Latest reports')}
            </button>
            <button className="btn btn-outline hero-btn">
              <span className="material-symbols-outlined">announcement</span>
              {tr('Communiqués', 'Releases')}
            </button>
          </div>
        </div>
      </section>

      {socialLinks.length > 0 && (
        <section className="social-follow-bar" aria-labelledby="social-follow-title">
          <div className="social-follow-inner">
            <div className="social-follow-heading">
              <span className="material-symbols-outlined">groups</span>
              <div>
                <h3 id="social-follow-title">{tr('Suivez-nous', 'Follow us')}</h3>
                <p>{tr('Retrouvez la Task Force Présidentielle sur les réseaux sociaux.', 'Find the Presidential Task Force on social media.')}</p>
              </div>
            </div>
            <div className="social-follow-links">
              {socialLinks.map((link) => {
                const { icon, color } = socialIconFor(link.name);
                return (
                  <a
                    key={link.id}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="social-follow-link"
                    style={{ '--social-color': color }}
                    aria-label={link.name}
                  >
                    <span className="material-symbols-outlined">{icon}</span>
                    <span className="social-follow-name">{link.name}</span>
                  </a>
                );
              })}
            </div>
          </div>
        </section>
      )}

      <div className="content-wrap">
        <div className="mobile-search">
          <span className="material-symbols-outlined">search</span>
          <input type="text" placeholder={tr('Recherche officielle...', 'Official search...')} />
        </div>

        <div className="bento-grid">
          <div className="bento-main">
            <div className="section-heading">
              <h3>{tr('Vidéos récentes', 'Recent videos')}</h3>
              <a href="/videos">{tr('Voir toutes les vidéos', 'See all videos')} <span className="material-symbols-outlined">chevron_right</span></a>
            </div>

            {videos.length > 0 ? (
              <article className="featured-card video-demo-card">
                <div className="video-player-wrap">
                  <video
                    key={videos[activeVideo].id}
                    controls
                    preload="metadata"
                    playsInline
                    autoPlay={activeVideo !== 0}
                    aria-label={videos[activeVideo].title}
                    onEnded={() => setActiveVideo((activeVideo + 1) % videos.length)}
                  >
                    <source src={videos[activeVideo].src} />
                    Votre navigateur ne prend pas en charge la lecture vidéo.
                  </video>
                  <div className="active-video-info">
                    <span className="video-index">{String(activeVideo + 1).padStart(2, '0')}</span>
                    <div>
                      <h5>{videos[activeVideo].title}</h5>
                      <p>{videos[activeVideo].description}</p>
                    </div>
                    <span className="video-position">{activeVideo + 1} / {videos.length}</span>
                  </div>
                </div>

                <div className="video-playlist" aria-label={tr('Liste des vidéos publiées', 'List of published videos')}>
                  {videos.map((video, index) => (
                    <button
                      type="button"
                      className={index === activeVideo ? 'active' : ''}
                      key={video.id}
                      onClick={() => setActiveVideo(index)}
                      aria-current={index === activeVideo ? 'true' : undefined}
                    >
                      <span>{String(index + 1).padStart(2, '0')}</span>
                      {video.title}
                    </button>
                  ))}
                </div>
              </article>
            ) : (
              <article className="featured-card video-demo-card video-empty">
                <span className="material-symbols-outlined">videocam_off</span>
                <p>{tr('Aucune vidéo publiée pour le moment.', 'No video published yet.')}</p>
              </article>
            )}

            <div className="brief-grid">
              {(briefs.length ? briefs : placeholderBriefs).map((b, i) => (
                <div className={`brief-card ${i % 2 === 0 ? 'accent-gold' : 'accent-navy'}`} key={b.id || i}>
                  <div>
                    <h5>{b.title}</h5>
                    <p>{b.excerpt}</p>
                  </div>
                  <a href="/actualites">Lire la suite <span className="material-symbols-outlined">chevron_right</span></a>
                </div>
              ))}
            </div>
          </div>

          <aside className="bento-side">
            <div className="directives-card">
              <h3><span className="material-symbols-outlined">policy</span>{tr('Directives officielles', 'Official directives')}</h3>
              <ul>
                <li>
                  <span className="material-symbols-outlined pdf-icon">picture_as_pdf</span>
                  <div>
                    <p className="li-title">Circulaire N°004/2023</p>
                    <p className="li-sub">Procédures de passation de marchés</p>
                  </div>
                </li>
                <li>
                  <span className="material-symbols-outlined pdf-icon">picture_as_pdf</span>
                  <div>
                    <p className="li-title">Arrêté Ministériel 45B</p>
                    <p className="li-sub">Normes de construction publique</p>
                  </div>
                </li>
                <li>
                  <span className="material-symbols-outlined pdf-icon">picture_as_pdf</span>
                  <div>
                    <p className="li-title">Rapport Annuel 2022</p>
                    <p className="li-sub">Bilan des réalisations</p>
                  </div>
                </li>
              </ul>
            </div>

            <div className="newsletter-card">
              <span className="material-symbols-outlined newsletter-icon">mail</span>
              <h3>{tr('Communiqués & Newsletter', 'Releases & Newsletter')}</h3>
              <p>
                {tr(
                  'Recevez les communiqués officiels et les actualités de la Task Force directement par e-mail.',
                  'Get official releases and Task Force news delivered straight to your inbox.',
                )}
              </p>
              {newsletterSent ? (
                <p className="newsletter-success">
                  <span className="material-symbols-outlined">check_circle</span>
                  {tr('Merci ! Vous êtes inscrit.', 'Thank you! You are now subscribed.')}
                </p>
              ) : (
                <form className="newsletter-form" onSubmit={handleNewsletterSubmit}>
                  <input
                    type="email"
                    required
                    value={newsletterEmail}
                    onChange={(e) => setNewsletterEmail(e.target.value)}
                    placeholder={tr('Votre adresse e-mail', 'Your email address')}
                  />
                  <button type="submit" className="btn btn-navy">
                    {tr("S'abonner", 'Subscribe')}
                  </button>
                </form>
              )}
            </div>

            <div className="transparency-card">
              <span className="material-symbols-outlined bg-icon">account_balance</span>
              <h3>{tr('Transparence totale', 'Full transparency')}</h3>
              <p>{tr('Accédez au portail de données ouvertes pour suivre l’avancement des projets en temps réel.', 'Use the open data portal to monitor project progress in real time.')}</p>
              <button className="btn" style={{ background: 'var(--white)', color: 'var(--primary)', width: '100%' }}>
                {tr('Portail Open Data', 'Open Data portal')}
              </button>
            </div>
          </aside>
        </div>
      </div>
    </>
  );
}

const placeholderBriefs = [
  { id: 'b1', title: 'Audit des Fonds Alloués : Rapport T3 Disponible', excerpt: 'Consultez le rapport détaillé de l’audit trimestriel sur l’utilisation des fonds publics pour les projets d’énergie.' },
  { id: 'b2', title: 'Nomination de nouveaux coordonnateurs régionaux', excerpt: 'Le Président a signé l’ordonnance nommant de nouveaux responsables pour superviser l’exécution des travaux en province.' },
];

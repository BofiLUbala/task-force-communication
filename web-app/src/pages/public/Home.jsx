import { useEffect, useState } from 'react';
import client from '../../api/client';
import './Home.css';

export default function Home() {
  const [briefs, setBriefs] = useState([]);
  const [activeVideo, setActiveVideo] = useState(0);

  useEffect(() => {
    client.get('/posts/')
      .then((res) => {
        const posts = res.data.results || res.data;
        setBriefs(posts.slice(0, 2));
      })
      .catch(() => {});
  }, []);

  return (
    <>
      <section className="hero">
        <div className="hero-bg" />
        <div className="hero-gradient" />
        <div className="hero-content">
          <img className="hero-flag" src="/flag-drc.svg" alt="Drapeau de la RDC" />
          <h2 className="hero-title">Task Force Présidentielle</h2>
          <p className="hero-subtitle">
            Supervision, Coordination et Transparence des Projets Stratégiques de la Nation.
          </p>
          <div className="hero-actions">
            <button className="btn btn-gold hero-btn">
              <span className="material-symbols-outlined">description</span>
              Derniers Rapports
            </button>
            <button className="btn btn-outline hero-btn">
              <span className="material-symbols-outlined">announcement</span>
              Communiqués
            </button>
          </div>
        </div>
      </section>

      <div className="content-wrap">
        <div className="mobile-search">
          <span className="material-symbols-outlined">search</span>
          <input type="text" placeholder="Recherche officielle..." />
        </div>

        <div className="bento-grid">
          <div className="bento-main">
            <div className="section-heading">
              <h3>Vidéos récentes</h3>
            </div>

            <article className="featured-card video-demo-card">
              <div className="video-player-wrap">
                <video
                  key={demoVideos[activeVideo].id}
                  controls
                  preload="metadata"
                  playsInline
                  autoPlay={activeVideo !== 0}
                  aria-label={demoVideos[activeVideo].title}
                  onEnded={() => setActiveVideo((activeVideo + 1) % demoVideos.length)}
                >
                  <source src={demoVideos[activeVideo].src} type="video/mp4" />
                  Votre navigateur ne prend pas en charge la lecture vidéo.
                </video>
                <div className="active-video-info">
                  <span className="video-index">{String(activeVideo + 1).padStart(2, '0')}</span>
                  <div>
                    <h5>{demoVideos[activeVideo].title}</h5>
                    <p>{demoVideos[activeVideo].description}</p>
                  </div>
                  <span className="video-position">{activeVideo + 1} / {demoVideos.length}</span>
                </div>
              </div>

              <div className="video-playlist" aria-label="Liste des vidéos de démonstration">
                {demoVideos.map((video, index) => (
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
              <h3><span className="material-symbols-outlined">policy</span>Directives Officielles</h3>
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

            <div className="transparency-card">
              <span className="material-symbols-outlined bg-icon">account_balance</span>
              <h3>Transparence Totale</h3>
              <p>Accédez au portail de données ouvertes pour suivre l’avancement des projets en temps réel.</p>
              <button className="btn" style={{ background: 'var(--white)', color: 'var(--primary)', width: '100%' }}>
                Portail Open Data
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

const demoVideos = [
  {
    id: 'demo-1',
    title: 'Présentation de la Task Force',
    description: 'Découvrez les missions et les priorités de la Task Force Présidentielle.',
    src: 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4',
  },
  {
    id: 'demo-2',
    title: 'Suivi des projets sur le terrain',
    description: 'Exemple de suivi vidéo des travaux et des infrastructures publiques.',
    src: 'https://www.w3schools.com/html/mov_bbb.mp4',
  },
  {
    id: 'demo-3',
    title: 'Rapport vidéo hebdomadaire',
    description: 'Une démonstration du format utilisé pour présenter l’avancement des projets.',
    src: 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4',
  },
];

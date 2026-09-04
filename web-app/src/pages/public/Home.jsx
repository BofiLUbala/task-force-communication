import { useEffect, useState } from 'react';
import client from '../../api/client';
import './Home.css';
import usePreferences from '../../hooks/usePreferences';
import { socialIconFor } from '../../utils/socialIcons';

const heroImages = [
  '/couverture.jpeg',
  '/couverture2.jpeg',
  '/couverture3.jpeg',
  '/couverture4.jpeg',
  '/img1.jpeg',
];

const staffImages = [
  '/img1.jpeg',
  '/couverture2.jpeg',
  '/couverture3.jpeg',
  '/couverture4.jpeg',
];

export default function Home() {
  const { tr } = usePreferences();
  const [latestNewsletter, setLatestNewsletter] = useState(null);
  const [videos, setVideos] = useState([]);
  const [socialLinks, setSocialLinks] = useState([]);
  const [heroImageIndex, setHeroImageIndex] = useState(0);
  const [activeVideoIndex, setActiveVideoIndex] = useState(0);
  const [staffImageIndex, setStaffImageIndex] = useState(0);
  const [contactForm, setContactForm] = useState({ name: '', email: '', subject: '', message: '' });
  const [contactStatus, setContactStatus] = useState({ sending: false, message: '', error: '' });

  async function sendContactMessage(event) {
    event.preventDefault();
    setContactStatus({ sending: true, message: '', error: '' });
    try {
      const { data } = await client.post('/contact/', contactForm);
      setContactForm({ name: '', email: '', subject: '', message: '' });
      setContactStatus({ sending: false, message: data.detail, error: '' });
    } catch (requestError) {
      setContactStatus({ sending: false, message: '', error: requestError.response?.data?.detail || tr('Envoi impossible. Réessayez plus tard.', 'Unable to send. Please try again later.') });
    }
  }

  useEffect(() => {
    client.get('/posts/')
      .then((res) => {
        const posts = res.data.results || res.data;
        setVideos(posts.flatMap((post) => (post.gallery || [])
          .filter((media) => media.media_type === 'VIDEO')
          .map((media) => ({
            id: media.id,
            title: media.title || post.title,
            description: media.caption || post.excerpt,
            src: media.file,
            socialLinks: media.social_links?.length ? media.social_links : (post.platform_links || []),
          }))));
      })
      .catch(() => {});
    client.get('/posts/', { params: { category: 'NEWSLETTER' } })
      .then((res) => setLatestNewsletter((res.data.results || res.data)[0] || null))
      .catch(() => setLatestNewsletter(null));
    client.get('/social-links/')
      .then((res) => setSocialLinks(res.data.results || res.data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setStaffImageIndex((current) => (current + 1) % staffImages.length);
    }, 6000);
    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    heroImages.forEach((src) => {
      const image = new Image();
      image.src = src;
    });
    const intervalId = window.setInterval(() => {
      setHeroImageIndex((current) => (current + 1) % heroImages.length);
    }, 10000);
    return () => window.clearInterval(intervalId);
  }, []);

  return (
    <>
      <section className="hero">
        <div className="hero-slideshow" aria-hidden="true">
          {heroImages.map((src, index) => (
            <div
              className={`hero-bg${index === heroImageIndex ? ' is-active' : ''}`}
              style={{ backgroundImage: `url(${src})` }}
              key={src}
            />
          ))}
        </div>
        <div className="hero-gradient" />
        <div className="hero-content">
          <img className="hero-flag" src="/flag-drc.svg" alt="Drapeau de la RDC" />
          <h2 className="hero-title">
            <span className="hero-title-main">{tr('Task Force Présidentielle', 'Presidential Task Force')}</span>
          </h2>
          <div className="hero-actions">
            <a href="/newsletter" className="btn btn-gold hero-btn">
              <span className="material-symbols-outlined">mail</span>
              {tr('Newsletter', 'Newsletter')}
            </a>
            <a href="/communiques" className="btn btn-outline hero-btn">
              <span className="material-symbols-outlined">announcement</span>
              {tr('Communiqués', 'Releases')}
            </a>
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

            <div className="media-staff-grid">
              <article className="featured-card video-demo-card videos-collection-card">
                <div className="collection-card-heading">
                  <span className="material-symbols-outlined">video_library</span>
                  <div>
                    <span>{tr('Médiathèque', 'Media library')}</span>
                    <h4>{tr('Nos vidéos', 'Our videos')}</h4>
                  </div>
                </div>
                {videos.length > 0 ? (
                  <>
                    <div className="video-player-wrap">
                      <video key={videos[activeVideoIndex].id} controls preload="metadata" playsInline aria-label={videos[activeVideoIndex].title}>
                        <source src={videos[activeVideoIndex].src} />
                        Votre navigateur ne prend pas en charge la lecture vidéo.
                      </video>
                    </div>
                  </>
                ) : (
                  <div className="video-empty">
                    <span className="material-symbols-outlined">videocam_off</span>
                    <p>{tr('Aucune vidéo publiée pour le moment.', 'No video published yet.')}</p>
                  </div>
                )}
              </article>

              <article className="staff-photo-card staff-collection-card">
                <div className="collection-card-heading staff-heading">
                  <span className="material-symbols-outlined">groups</span>
                  <div>
                    <span>{tr('Notre équipe', 'Our team')}</span>
                    <h4>{tr('Membres du staff', 'Staff members')}</h4>
                  </div>
                </div>
                <div className="staff-photo-stage">
                  {staffImages.map((src, index) => (
                    <img
                      className={index === staffImageIndex ? 'is-active' : ''}
                      src={src}
                      alt={tr(`Équipe de la Task Force — photo ${index + 1}`, `Task Force team — photo ${index + 1}`)}
                      key={src}
                    />
                  ))}
                </div>
                <div className="active-video-info staff-photo-info">
                  <h5>{tr('Au service de la salubrité de Kinshasa', 'Serving a cleaner Kinshasa')}</h5>
                  <p>{tr('Découvrez les membres mobilisés sur le terrain.', 'Meet the team members working in the field.')}</p>
                  <div className="staff-photo-dots" aria-label={tr('Choisir une photo', 'Choose a photo')}>
                    {staffImages.map((src, index) => (
                      <button
                        type="button"
                        className={index === staffImageIndex ? 'is-active' : ''}
                        onClick={() => setStaffImageIndex(index)}
                        aria-label={tr(`Photo ${index + 1}`, `Photo ${index + 1}`)}
                        key={src}
                      />
                    ))}
                  </div>
                </div>
              </article>
            </div>

            <section className="home-contact-card">
              <div className="home-contact-icon"><span className="material-symbols-outlined">support_agent</span></div>
              <div className="home-contact-copy">
                <span>{tr('Besoin d’une information ?', 'Need information?')}</span>
                <h3>{tr('Contactez la Task Force Présidentielle', 'Contact the Presidential Task Force')}</h3>
                <p>{tr('Notre équipe est disponible pour recevoir vos questions et vos préoccupations.', 'Our team is available to receive your questions and concerns.')}</p>
              </div>
              <form className="home-contact-form" onSubmit={sendContactMessage}>
                <input aria-label={tr('Nom complet', 'Full name')} placeholder={tr('Nom complet', 'Full name')} value={contactForm.name} onChange={(e) => setContactForm((form) => ({ ...form, name: e.target.value }))} required />
                <input aria-label={tr('Adresse e-mail', 'Email address')} type="email" placeholder={tr('Adresse e-mail', 'Email address')} value={contactForm.email} onChange={(e) => setContactForm((form) => ({ ...form, email: e.target.value }))} required />
                <input className="home-contact-form-wide" aria-label={tr('Objet', 'Subject')} placeholder={tr('Objet de votre message', 'Message subject')} value={contactForm.subject} onChange={(e) => setContactForm((form) => ({ ...form, subject: e.target.value }))} required />
                <textarea className="home-contact-form-wide" aria-label={tr('Votre message', 'Your message')} placeholder={tr('Écrivez votre message...', 'Write your message...')} value={contactForm.message} onChange={(e) => setContactForm((form) => ({ ...form, message: e.target.value }))} required />
                <button type="submit" className="btn btn-gold home-contact-action" disabled={contactStatus.sending}>
                  {contactStatus.sending ? tr('Envoi...', 'Sending...') : tr('Envoyer le message', 'Send message')}
                  <span className="material-symbols-outlined">send</span>
                </button>
                {contactStatus.message && <p className="home-contact-feedback is-success">{contactStatus.message}</p>}
                {contactStatus.error && <p className="home-contact-feedback is-error">{contactStatus.error}</p>}
              </form>
            </section>

            <section className="latest-newsletter-card">
              <div className="latest-newsletter-icon"><span className="material-symbols-outlined">forward_to_inbox</span></div>
              <div className="latest-newsletter-copy">
                <span>{tr('Dernière newsletter', 'Latest newsletter')}</span>
                {latestNewsletter ? (
                  <>
                    <h3>{latestNewsletter.title}</h3>
                    {latestNewsletter.excerpt && <p>{latestNewsletter.excerpt}</p>}
                  </>
                ) : (
                  <h3>{tr('Aucune newsletter publiée pour le moment.', 'No newsletter has been published yet.')}</h3>
                )}
              </div>
              <a href={latestNewsletter ? `/publications/${latestNewsletter.slug}` : '/newsletter'} className="latest-newsletter-action">
                {tr(latestNewsletter ? 'Lire le message' : 'Voir les newsletters', latestNewsletter ? 'Read message' : 'View newsletters')}
                <span className="material-symbols-outlined">arrow_forward</span>
              </a>
            </section>
          </div>

        </div>
      </div>
    </>
  );
}

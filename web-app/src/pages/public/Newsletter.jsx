import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../../api/client';
import Pagination from '../../components/Pagination';
import usePreferences from '../../hooks/usePreferences';
import './Listing.css';

const PAGE_SIZE = 20;

export default function Newsletter() {
  const { tr, language } = usePreferences();
  const [posts, setPosts] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState({ name: '', email: '' });
  const [subscriptionMessage, setSubscriptionMessage] = useState('');
  const [subscriptionError, setSubscriptionError] = useState('');

  async function subscribe(event) {
    event.preventDefault();
    setSubscriptionMessage(''); setSubscriptionError('');
    try {
      await client.post('/newsletter/subscribe/', subscription);
      setSubscriptionMessage(tr('Votre inscription est confirmée.', 'Your subscription is confirmed.'));
      setSubscription({ name: '', email: '' });
    } catch (requestError) {
      setSubscriptionError(requestError.response?.data?.detail || tr('Inscription impossible. Vérifiez votre adresse.', 'Could not subscribe. Check your address.'));
    }
  }

  useEffect(() => {
    setLoading(true);
    client.get('/posts/', { params: { category: 'NEWSLETTER', page } })
      .then((res) => {
        setPosts(res.data.results || res.data);
        setCount(res.data.count ?? (res.data.results || res.data).length);
      })
      .catch(() => { setPosts([]); setCount(0); })
      .finally(() => setLoading(false));
  }, [page]);

  return (
    <main>
      <div className="page-header newsletter-page-header">
        <div className="container">
          <Link to="/" className="page-back-link">
            <span className="material-symbols-outlined">arrow_back</span>
            {tr('Retour à l’accueil', 'Back to home')}
          </Link>
          <h1>Newsletter</h1>
          <p>{tr('Les derniers messages officiels de la Task Force Présidentielle.', 'The latest official messages from the Presidential Task Force.')}</p>
        </div>
      </div>
      <section className="newsletter-subscribe-section">
        <div className="newsletter-subscribe-copy">
          <span>{tr('RESTEZ INFORMÉ', 'STAY INFORMED')}</span>
          <h2>{tr('Recevez les nouvelles de la salubrité à Kinshasa', 'Receive sanitation news from Kinshasa')}</h2>
          <p>{tr('Les messages officiels de la Task Force Présidentielle directement dans votre boîte e-mail.', 'Official Presidential Task Force messages directly in your inbox.')}</p>
        </div>
        <form className="newsletter-subscribe-form" onSubmit={subscribe}>
          <label htmlFor="subscriber-name">{tr('Nom (facultatif)', 'Name (optional)')}</label>
          <input id="subscriber-name" value={subscription.name} onChange={(e) => setSubscription((s) => ({ ...s, name: e.target.value }))} />
          <label htmlFor="subscriber-email">{tr('Adresse e-mail', 'Email address')}</label>
          <input id="subscriber-email" type="email" value={subscription.email} onChange={(e) => setSubscription((s) => ({ ...s, email: e.target.value }))} required />
          <button className="btn btn-gold" type="submit">{tr('S’abonner', 'Subscribe')}</button>
          {subscriptionMessage && <p className="newsletter-form-success">{subscriptionMessage}</p>}
          {subscriptionError && <p className="newsletter-form-error">{subscriptionError}</p>}
          <small>{tr('Vous pourrez vous désabonner à tout moment depuis chaque e-mail.', 'You can unsubscribe at any time from every email.')}</small>
        </form>
      </section>
      <section className="newsletter-listing">
        {!loading && posts.length === 0 && <p className="newsletter-list-empty">{tr('Aucune newsletter publiée pour le moment.', 'No newsletter has been published yet.')}</p>}
        {posts.map((post) => (
          <article className="newsletter-public-card" key={post.id}>
            <div className="newsletter-public-meta">
              <span className="material-symbols-outlined">mail</span>
              {new Date(post.published_at || post.created_at).toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-US')}
            </div>
            <h2>{post.title}</h2>
            {post.excerpt && <p>{post.excerpt}</p>}
            <Link to={`/publications/${post.slug}`}>{tr('Lire la newsletter', 'Read newsletter')} <span className="material-symbols-outlined">arrow_forward</span></Link>
          </article>
        ))}
        <Pagination page={page} pageSize={PAGE_SIZE} count={count} onChange={setPage} />
      </section>
    </main>
  );
}

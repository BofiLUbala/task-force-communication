import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import client from '../../api/client';
import usePreferences from '../../hooks/usePreferences';
import './Listing.css';

export default function NewsletterUnsubscribe() {
  const { token } = useParams();
  const { tr } = usePreferences();
  const [status, setStatus] = useState('idle');

  async function unsubscribe() {
    setStatus('loading');
    try {
      await client.post(`/newsletter/unsubscribe/${token}/`);
      setStatus('done');
    } catch { setStatus('error'); }
  }

  return <main className="unsubscribe-page">
    <span className="material-symbols-outlined">unsubscribe</span>
    <h1>{tr('Se désabonner de la newsletter', 'Unsubscribe from the newsletter')}</h1>
    {status === 'done' ? <p>{tr('Votre désabonnement est confirmé.', 'Your unsubscribe request is confirmed.')}</p> : <>
      <p>{tr('Vous ne recevrez plus les newsletters de la Task Force Présidentielle.', 'You will no longer receive Presidential Task Force newsletters.')}</p>
      {status === 'error' && <p className="newsletter-form-error">{tr('Ce lien est invalide ou a expiré.', 'This link is invalid or has expired.')}</p>}
      <button className="btn btn-gold" onClick={unsubscribe} disabled={status === 'loading'}>{tr('Confirmer le désabonnement', 'Confirm unsubscribe')}</button>
    </>}
    <Link to="/newsletter">{tr('Retour aux newsletters', 'Back to newsletters')}</Link>
  </main>;
}

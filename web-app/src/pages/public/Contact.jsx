import { useState } from 'react';
import './Listing.css';
import usePreferences from '../../hooks/usePreferences';

export default function Contact() {
  const { tr } = usePreferences();
  const [sent, setSent] = useState(false);

  function handleSubmit(e) {
    e.preventDefault();
    setSent(true);
  }

  return (
    <div className="contact-page">
      <h1>{tr('Contact', 'Contact')}</h1>
      <p style={{ color: 'var(--text-muted)' }}>
        {tr("Pour toute question ou demande d'information, contactez-nous via le formulaire ci-dessous.", 'For any question or information request, contact us using the form below.')}
      </p>

      {sent ? (
        <p style={{ color: 'var(--status-validated)', fontWeight: 600 }}>{tr('Votre message a bien été envoyé.', 'Your message has been sent.')}</p>
      ) : (
        <form className="contact-form" onSubmit={handleSubmit}>
          <input type="text" placeholder={tr('Nom complet', 'Full name')} required />
          <input type="email" placeholder={tr('Adresse e-mail', 'Email address')} required />
          <input type="text" placeholder={tr('Objet', 'Subject')} required />
          <textarea placeholder={tr('Votre message', 'Your message')} required />
          <button type="submit" className="btn btn-navy" style={{ width: 'fit-content' }}>{tr('Envoyer', 'Send')}</button>
        </form>
      )}

      <div className="contact-info">
        <p><strong>{tr('Adresse :', 'Address:')}</strong> Palais de la Nation, Kinshasa, RDC</p>
        <p><strong>Email :</strong> contact@taskforce-presidentielle.cd</p>
      </div>
    </div>
  );
}

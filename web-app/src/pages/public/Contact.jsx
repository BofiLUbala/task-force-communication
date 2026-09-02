import { useState } from 'react';
import './Listing.css';

export default function Contact() {
  const [sent, setSent] = useState(false);

  function handleSubmit(e) {
    e.preventDefault();
    setSent(true);
  }

  return (
    <div className="contact-page">
      <h1>Contact</h1>
      <p style={{ color: 'var(--text-muted)' }}>
        Pour toute question ou demande d'information, contactez-nous via le formulaire ci-dessous.
      </p>

      {sent ? (
        <p style={{ color: 'var(--status-validated)', fontWeight: 600 }}>Votre message a bien été envoyé.</p>
      ) : (
        <form className="contact-form" onSubmit={handleSubmit}>
          <input type="text" placeholder="Nom complet" required />
          <input type="email" placeholder="Adresse email" required />
          <input type="text" placeholder="Objet" required />
          <textarea placeholder="Votre message" required />
          <button type="submit" className="btn btn-navy" style={{ width: 'fit-content' }}>Envoyer</button>
        </form>
      )}

      <div className="contact-info">
        <p><strong>Adresse :</strong> Palais de la Nation, Kinshasa, RDC</p>
        <p><strong>Email :</strong> contact@taskforce-presidentielle.cd</p>
      </div>
    </div>
  );
}

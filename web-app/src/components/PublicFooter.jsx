import './PublicFooter.css';
import { Link } from 'react-router-dom';
import usePreferences from '../hooks/usePreferences';

export default function PublicFooter() {
  const { tr } = usePreferences();
  return (
    <footer className="public-footer">
      <div className="footer-inner">
        <div className="footer-identity">
          <div className="footer-brand">
            <div className="footer-emblem">
              <img src="/logo-taskforce.jpg" alt="Logo officiel de la Task Force Présidentielle" />
            </div>
            <div>
              <strong>Task Force Présidentielle</strong>
              <span>{tr('Salubrité et Assainissement', 'Sanitation and Public Cleanliness')}</span>
            </div>
          </div>
          <p>{tr(
            'Au service de la salubrité et de l’assainissement de la Ville de Kinshasa, pour une capitale propre, saine et durable.',
            'Serving sanitation and public cleanliness in the City of Kinshasa, for a clean, healthy and sustainable capital.',
          )}</p>
        </div>
        <nav className="footer-navigation" aria-label={tr('Navigation du pied de page', 'Footer navigation')}>
          <h5>{tr('Découvrir', 'Explore')}</h5>
          <Link to="/a-propos">{tr('À propos', 'About')}</Link>
          <Link to="/newsletter">Newsletter</Link>
          <Link to="/videos">{tr('Vidéos', 'Videos')}</Link>
          <Link to="/contact">Contact</Link>
        </nav>
        <div className="footer-commitment">
          <span className="material-symbols-outlined">eco</span>
          <div>
            <h5>{tr('Notre engagement', 'Our commitment')}</h5>
            <p>{tr('Kinshasa propre, notre responsabilité commune.', 'A clean Kinshasa is our shared responsibility.')}</p>
          </div>
        </div>
      </div>
      <div className="footer-bottom">
        <span>© {new Date().getFullYear()} Task Force Présidentielle, RDC. {tr('Tous droits réservés.', 'All rights reserved.')}</span>
        <span className="footer-credit">
          {tr('Conception et développement :', 'Designed and developed by:')}{' '}
          <strong>Gauthier Bofi</strong>
          {' — '}
          <a href="https://btmi.ai" target="_blank" rel="noopener noreferrer">BTMI.AI</a>
        </span>
      </div>
    </footer>
  );
}

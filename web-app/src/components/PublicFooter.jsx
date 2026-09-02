import './PublicFooter.css';
import usePreferences from '../hooks/usePreferences';

export default function PublicFooter() {
  const { tr } = usePreferences();
  return (
    <footer className="public-footer">
      <div className="footer-inner">
        <div className="footer-col-wide">
          <div className="footer-brand">
            <div className="footer-emblem">
              <img src="/logo-taskforce.jpg" alt="Logo officiel de la Task Force Présidentielle" />
            </div>
          </div>
          <p>
            {tr(
              "Task Force Présidentielle chargée du suivi et de l'évaluation des projets d'infrastructures de la République Démocratique du Congo.",
              'Presidential Task Force responsible for monitoring and evaluating infrastructure projects in the Democratic Republic of the Congo.',
            )}
          </p>
        </div>
        <div>
          <h5>{tr('Liens utiles', 'Useful links')}</h5>
          <a href="#">{tr('Portail du Gouvernement', 'Government portal')}</a>
          <a href="#">{tr('Ministère des Finances', 'Ministry of Finance')}</a>
          <a href="#">{tr('Journal officiel', 'Official Gazette')}</a>
          <a href="#">{tr('Mentions légales', 'Legal notice')}</a>
        </div>
        <div>
          <h5>Contact</h5>
          <p className="contact-line"><span className="material-symbols-outlined">location_on</span> Palais de la Nation, Kinshasa, RDC</p>
          <p className="contact-line"><span className="material-symbols-outlined">mail</span> contact@taskforce.rdc.cd</p>
        </div>
      </div>
      <div className="footer-bottom">
        © {new Date().getFullYear()} Task Force Présidentielle, RDC. {tr('Tous droits réservés.', 'All rights reserved.')}
      </div>
    </footer>
  );
}

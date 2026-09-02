import './PublicFooter.css';

export default function PublicFooter() {
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
            Task Force Présidentielle chargée du suivi et de l'évaluation des projets
            d'infrastructures de la République Démocratique du Congo.
          </p>
        </div>
        <div>
          <h5>Liens Utiles</h5>
          <a href="#">Portail du Gouvernement</a>
          <a href="#">Ministère des Finances</a>
          <a href="#">Journal Officiel</a>
          <a href="#">Mentions Légales</a>
        </div>
        <div>
          <h5>Contact</h5>
          <p className="contact-line"><span className="material-symbols-outlined">location_on</span> Palais de la Nation, Kinshasa, RDC</p>
          <p className="contact-line"><span className="material-symbols-outlined">mail</span> contact@taskforce.rdc.cd</p>
        </div>
      </div>
      <div className="footer-bottom">
        © {new Date().getFullYear()} Task Force Présidentielle, RDC. Tous droits réservés.
      </div>
    </footer>
  );
}

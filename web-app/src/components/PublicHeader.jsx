import { NavLink } from 'react-router-dom';
import './PublicHeader.css';

const links = [
  { to: '/', label: 'Accueil', end: true },
  { to: '/actualites', label: 'Actualités' },
  { to: '/activites', label: 'Rapports Publics' },
  { to: '/contact', label: 'Contact' },
];

export default function PublicHeader() {
  return (
    <header className="public-header">
      <div className="header-inner">
        <div className="brand">
          <div className="brand-emblem">
            <img src="/logo-taskforce.jpg" alt="Logo officiel de la Task Force Présidentielle" />
          </div>
        </div>

        <nav>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? 'active' : '')}>
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="header-actions">
          <div className="search-box">
            <span className="material-symbols-outlined">search</span>
            <input type="text" placeholder="Recherche officielle..." />
          </div>
          <NavLink to="/connexion" className="btn btn-navy" style={{ padding: '10px 20px', fontSize: '0.85rem' }}>
            Espace agents
          </NavLink>
        </div>
      </div>
    </header>
  );
}

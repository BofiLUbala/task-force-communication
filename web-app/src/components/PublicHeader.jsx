import { NavLink } from 'react-router-dom';
import './PublicHeader.css';
import PreferenceControls from './PreferenceControls';
import usePreferences from '../hooks/usePreferences';

export default function PublicHeader() {
  const { tr } = usePreferences();
  const links = [
    { to: '/', label: tr('Accueil', 'Home'), end: true },
    { to: '/actualites', label: tr('Actualités', 'News') },
    { to: '/activites', label: tr('Rapports publics', 'Public reports') },
    { to: '/contact', label: tr('Contact', 'Contact') },
  ];
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
            <input type="text" placeholder={tr('Recherche officielle...', 'Official search...')} />
          </div>
          <PreferenceControls compact />
          <NavLink to="/connexion" className="btn btn-navy header-cta">
            {tr('Espace agents', 'Agent portal')}
          </NavLink>
        </div>
      </div>
    </header>
  );
}

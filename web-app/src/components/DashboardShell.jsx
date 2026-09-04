import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import PreferenceControls from './PreferenceControls';
import usePreferences from '../hooks/usePreferences';
import '../pages/internal/Internal.css';

const NAV_ICONS = [
  [/\/rapports$/, 'assignment_turned_in'],
  [/\/validation$/, 'fact_check'],
  [/\/publications\/actualite$/, 'newspaper'],
  [/\/publications\/image$/, 'image'],
  [/\/publications\/video$/, 'movie'],
  [/\/publications\/communique$/, 'picture_as_pdf'],
  [/\/publications\/newsletter$/, 'forward_to_inbox'],
  [/\/reseaux-sociaux$/, 'share'],
  [/\/statistiques$/, 'bar_chart'],
];

function iconFor(to) {
  const match = NAV_ICONS.find(([pattern]) => pattern.test(to));
  return match ? match[1] : 'chevron_right';
}

export default function DashboardShell({ links, children }) {
  const { user, logout } = useAuth();
  const { tr } = usePreferences();

  return (
    <div className="dash-shell">
      <aside className="dash-sidebar">
        <div className="dash-logo">
          <img src="/logo-taskforce.jpg" alt="Task Force Présidentielle" />
        </div>
        <nav>
          <div className="dash-nav-group">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} className={({ isActive }) => (isActive ? 'active' : '')}>
                <span className="material-symbols-outlined">{iconFor(l.to)}</span>
                <span>{l.label}</span>
              </NavLink>
            ))}
          </div>
          <div className="dash-nav-spacer" />
          <button className="dash-nav-logout" onClick={logout}>
            <span className="material-symbols-outlined">logout</span>
            <span>{tr('Déconnexion', 'Sign out')}</span>
          </button>
        </nav>
      </aside>
      <div className="dash-workspace">
        <header className="dash-header">
          <div className="dash-user">
            <span className="material-symbols-outlined">account_circle</span>
            <div><small>{tr('Utilisateur connecté', 'Signed-in user')}</small><strong>{user?.full_name || tr('Agent', 'Agent')}</strong></div>
          </div>
          <PreferenceControls />
        </header>
        <main className="dash-main">{children}</main>
      </div>
    </div>
  );
}

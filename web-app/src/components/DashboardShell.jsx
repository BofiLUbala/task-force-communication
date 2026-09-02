import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../pages/internal/Internal.css';

export default function DashboardShell({ links, children }) {
  const { user, logout } = useAuth();

  return (
    <div className="dash-shell">
      <aside className="dash-sidebar">
        <div className="brand-text">Task Force — Espace</div>
        <nav>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} className={({ isActive }) => (isActive ? 'active' : '')}>
              {l.label}
            </NavLink>
          ))}
          <button onClick={logout}>Déconnexion ({user?.full_name})</button>
        </nav>
      </aside>
      <main className="dash-main">{children}</main>
    </div>
  );
}

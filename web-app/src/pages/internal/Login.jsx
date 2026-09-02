import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './Internal.css';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(username, password);
      navigate(user.role === 'HIERARCHY' ? '/espace/validation' : '/espace/rapports');
    } catch {
      setError('Identifiants incorrects. Veuillez réessayer.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-emblem">
          <img src="/logo-taskforce.jpg" alt="Logo officiel de la Task Force Présidentielle" />
        </div>
        <h1>Espace de travail</h1>
        <p className="subtitle">Task Force Présidentielle — accès réservé</p>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label htmlFor="username">Identifiant</label>
          <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="matricule ou identifiant" required />

          <label htmlFor="password">Mot de passe</label>
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />

          <div className="auth-inline-link">
            <Link to="/mot-de-passe-oublie">Mot de passe oublié&nbsp;?</Link>
          </div>

          <button type="submit" className="btn btn-gold" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Connexion...' : 'Se connecter'}
          </button>
        </form>

        <p className="auth-switch">Pas encore de compte&nbsp;? <Link to="/inscription">Créer un compte</Link></p>

        <p className="login-notice">
          Accès strictement réservé aux agents et personnel autorisé de la Task Force Présidentielle.
          Toute tentative d'accès non autorisée est enregistrée.
        </p>
      </div>
    </div>
  );
}

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import PreferenceControls from '../../components/PreferenceControls';
import usePreferences from '../../hooks/usePreferences';
import './Internal.css';

export default function Login() {
  const { login } = useAuth();
  const { tr } = usePreferences();
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
      setError(tr('Identifiants incorrects. Veuillez réessayer.', 'Incorrect credentials. Please try again.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="auth-preferences"><PreferenceControls /></div>
      <Link to="/" className="auth-back-home">
        <span className="material-symbols-outlined">arrow_back</span>
        {tr('Retour à l’accueil', 'Back to home')}
      </Link>
      <div className="login-card">
        <div className="login-emblem">
          <img src="/logo-taskforce.jpg" alt="Logo officiel de la Task Force Présidentielle" />
        </div>
        <h1>{tr('Espace de travail', 'Workspace')}</h1>
        <p className="subtitle">{tr('Task Force Présidentielle — accès réservé', 'Presidential Task Force — restricted access')}</p>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label htmlFor="username">{tr('Adresse e-mail ou identifiant', 'Email address or username')}</label>
          <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} placeholder={tr('votre adresse e-mail', 'your email address')} required />

          <label htmlFor="password">{tr('Mot de passe', 'Password')}</label>
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />

          <div className="auth-inline-link">
            <Link to="/mot-de-passe-oublie">{tr('Mot de passe oublié ?', 'Forgot password?')}</Link>
          </div>

          <button type="submit" className="btn btn-gold" style={{ width: '100%' }} disabled={loading}>
            {loading ? tr('Connexion...', 'Signing in...') : tr('Se connecter', 'Sign in')}
          </button>
        </form>

        <p className="auth-switch">{tr('Pas encore de compte ?', 'No account yet?')} <Link to="/inscription">{tr('Créer un compte', 'Create account')}</Link></p>

        <p className="login-notice">
          {tr(
            "Accès strictement réservé aux agents et personnel autorisé de la Task Force Présidentielle. Toute tentative d'accès non autorisée est enregistrée.",
            'Access is strictly restricted to authorized Presidential Task Force agents and personnel. Unauthorized access attempts are logged.',
          )}
        </p>
      </div>
    </div>
  );
}

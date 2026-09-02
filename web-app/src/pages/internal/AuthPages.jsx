import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import client from '../../api/client';
import PreferenceControls from '../../components/PreferenceControls';
import usePreferences from '../../hooks/usePreferences';
import './Internal.css';

function AuthShell({ title, subtitle, children }) {
  return (
    <div className="login-page auth-page">
      <div className="auth-preferences"><PreferenceControls /></div>
      <div className="login-card auth-card">
        <div className="login-emblem">
          <img src="/logo-taskforce.jpg" alt="Logo officiel de la Task Force Présidentielle" />
        </div>
        <h1>{title}</h1>
        <p className="subtitle">{subtitle}</p>
        {children}
      </div>
    </div>
  );
}

function apiError(error, fallback) {
  const data = error.response?.data;
  if (typeof data?.detail === 'string') return data.detail;
  if (data && typeof data === 'object') {
    const first = Object.values(data).flat()[0];
    if (first) return String(first);
  }
  return fallback;
}

export function Register() {
  const { tr } = usePreferences();
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone_number: '', password: '', confirmPassword: '',
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function update(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  async function submit(event) {
    event.preventDefault();
    setError('');
    setMessage('');
    if (form.password !== form.confirmPassword) {
      setError(tr('Les deux mots de passe ne correspondent pas.', 'The passwords do not match.'));
      return;
    }
    setLoading(true);
    try {
      const payload = { ...form };
      delete payload.confirmPassword;
      const { data } = await client.post('/auth/register/', payload);
      setMessage(data.detail);
    } catch (requestError) {
      setError(apiError(requestError, tr('Impossible de créer le compte. Veuillez réessayer.', 'Unable to create the account. Please try again.')));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title={tr('Créer un compte agent', 'Create an agent account')} subtitle={tr('Un lien d’activation valable 48 heures vous sera envoyé.', 'A 48-hour activation link will be emailed to you.')}>
      {message ? (
        <div className="auth-success">{message}<Link to="/connexion">{tr('Retour à la connexion', 'Back to sign in')}</Link></div>
      ) : (
        <form onSubmit={submit}>
          {error && <div className="login-error">{error}</div>}
          <div className="auth-field-grid">
            <div><label htmlFor="first_name">{tr('Prénom', 'First name')}</label><input id="first_name" name="first_name" value={form.first_name} onChange={update} required /></div>
            <div><label htmlFor="last_name">{tr('Nom', 'Last name')}</label><input id="last_name" name="last_name" value={form.last_name} onChange={update} required /></div>
          </div>
          <label htmlFor="email">{tr('Adresse e-mail', 'Email address')}</label>
          <input id="email" name="email" type="email" value={form.email} onChange={update} required />
          <label htmlFor="phone_number">{tr('Téléphone', 'Phone')}</label>
          <input id="phone_number" name="phone_number" type="tel" value={form.phone_number} onChange={update} />
          <div className="auth-field-grid">
            <div>
              <label htmlFor="register-password">{tr('Mot de passe', 'Password')}</label>
              <input id="register-password" name="password" type="password" value={form.password} onChange={update} required />
            </div>
            <div>
              <label htmlFor="confirm-password">{tr('Confirmation', 'Confirmation')}</label>
              <input id="confirm-password" name="confirmPassword" type="password" value={form.confirmPassword} onChange={update} required />
            </div>
          </div>
          <button className="btn btn-gold auth-submit" type="submit" disabled={loading}>{loading ? tr('Création...', 'Creating...') : tr('Créer mon compte', 'Create my account')}</button>
          <p className="auth-switch">{tr('Déjà inscrit ?', 'Already registered?')} <Link to="/connexion">{tr('Se connecter', 'Sign in')}</Link></p>
        </form>
      )}
    </AuthShell>
  );
}

export function VerifyEmail() {
  const { tr } = usePreferences();
  const [params] = useSearchParams();
  const token = params.get('token');
  const [state, setState] = useState(() => token
    ? { loading: true, success: false, message: 'Validation de votre adresse e-mail...' }
    : { loading: false, success: false, message: 'Le lien de confirmation est incomplet.' });
  const requested = useRef(false);

  useEffect(() => {
    if (!token || requested.current) return;
    requested.current = true;
    client.post('/auth/verify-email/', { token })
      .then(({ data }) => setState({ loading: false, success: true, message: data.detail }))
      .catch((error) => setState({ loading: false, success: false, message: apiError(error, 'Impossible de confirmer ce compte.') }));
  }, [token]);

  return (
    <AuthShell title={tr('Activation du compte', 'Account activation')} subtitle={tr('Confirmation sécurisée de votre adresse e-mail', 'Secure email address confirmation')}>
      <div className={state.success ? 'auth-success' : state.loading ? 'auth-status' : 'login-error'}>
        {state.message}
        {!state.loading && <Link to="/connexion">{tr('Aller à la connexion', 'Go to sign in')}</Link>}
      </div>
    </AuthShell>
  );
}

export function ForgotPassword() {
  const { tr } = usePreferences();
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const { data } = await client.post('/auth/password-reset/', { email });
      setMessage(data.detail);
    } catch (requestError) {
      setError(apiError(requestError, 'Impossible d’envoyer la demande.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title={tr('Mot de passe oublié', 'Forgot password')} subtitle={tr('Recevez un lien sécurisé pour choisir un nouveau mot de passe.', 'Receive a secure link to choose a new password.')}>
      {message ? <div className="auth-success">{message}<Link to="/connexion">{tr('Retour à la connexion', 'Back to sign in')}</Link></div> : (
        <form onSubmit={submit}>
          {error && <div className="login-error">{error}</div>}
          <label htmlFor="reset-email">{tr('Adresse e-mail', 'Email address')}</label>
          <input id="reset-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <button className="btn btn-gold auth-submit" type="submit" disabled={loading}>{loading ? tr('Envoi...', 'Sending...') : tr('Envoyer le lien', 'Send link')}</button>
          <p className="auth-switch"><Link to="/connexion">{tr('Retour à la connexion', 'Back to sign in')}</Link></p>
        </form>
      )}
    </AuthShell>
  );
}

export function ResetPassword() {
  const { tr } = usePreferences();
  const [params] = useSearchParams();
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError('');
    if (password !== confirmation) {
      setError('Les deux mots de passe ne correspondent pas.');
      return;
    }
    const token = params.get('token');
    if (!token) {
      setError('Le lien de réinitialisation est incomplet.');
      return;
    }
    setLoading(true);
    try {
      const { data } = await client.post('/auth/password-reset/confirm/', { token, password });
      setMessage(data.detail);
    } catch (requestError) {
      setError(apiError(requestError, 'Impossible de modifier le mot de passe.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title={tr('Nouveau mot de passe', 'New password')} subtitle={tr('Choisissez un nouveau mot de passe sécurisé.', 'Choose a secure new password.')}>
      {message ? <div className="auth-success">{message}<Link to="/connexion">{tr('Se connecter', 'Sign in')}</Link></div> : (
        <form onSubmit={submit}>
          {error && <div className="login-error">{error}</div>}
          <label htmlFor="new-password">{tr('Nouveau mot de passe', 'New password')}</label>
          <input id="new-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          <label htmlFor="new-password-confirmation">{tr('Confirmer le mot de passe', 'Confirm password')}</label>
          <input id="new-password-confirmation" type="password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required />
          <button className="btn btn-gold auth-submit" type="submit" disabled={loading}>{loading ? tr('Modification...', 'Updating...') : tr('Modifier le mot de passe', 'Update password')}</button>
        </form>
      )}
    </AuthShell>
  );
}

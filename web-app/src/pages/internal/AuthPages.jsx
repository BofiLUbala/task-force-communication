import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import client from '../../api/client';
import './Internal.css';

function AuthShell({ title, subtitle, children }) {
  return (
    <div className="login-page auth-page">
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
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', matricule: '', phone_number: '', unit: '', password: '', confirmPassword: '',
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
      setError('Les deux mots de passe ne correspondent pas.');
      return;
    }
    setLoading(true);
    try {
      const payload = { ...form };
      delete payload.confirmPassword;
      const { data } = await client.post('/auth/register/', payload);
      setMessage(data.detail);
    } catch (requestError) {
      setError(apiError(requestError, 'Impossible de créer le compte. Veuillez réessayer.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Créer un compte agent" subtitle="Un lien d’activation valable 48 heures vous sera envoyé.">
      {message ? (
        <div className="auth-success">{message}<Link to="/connexion">Retour à la connexion</Link></div>
      ) : (
        <form onSubmit={submit}>
          {error && <div className="login-error">{error}</div>}
          <div className="auth-field-grid">
            <div><label htmlFor="first_name">Prénom</label><input id="first_name" name="first_name" value={form.first_name} onChange={update} required /></div>
            <div><label htmlFor="last_name">Nom</label><input id="last_name" name="last_name" value={form.last_name} onChange={update} required /></div>
          </div>
          <label htmlFor="email">Adresse e-mail</label>
          <input id="email" name="email" type="email" value={form.email} onChange={update} required />
          <div className="auth-field-grid">
            <div><label htmlFor="matricule">Matricule</label><input id="matricule" name="matricule" value={form.matricule} onChange={update} required /></div>
            <div><label htmlFor="unit">Unité / service</label><input id="unit" name="unit" value={form.unit} onChange={update} required /></div>
          </div>
          <label htmlFor="phone_number">Téléphone</label>
          <input id="phone_number" name="phone_number" type="tel" value={form.phone_number} onChange={update} />
          <div className="auth-field-grid">
            <div><label htmlFor="register-password">Mot de passe</label><input id="register-password" name="password" type="password" value={form.password} onChange={update} required /></div>
            <div><label htmlFor="confirm-password">Confirmation</label><input id="confirm-password" name="confirmPassword" type="password" value={form.confirmPassword} onChange={update} required /></div>
          </div>
          <button className="btn btn-gold auth-submit" type="submit" disabled={loading}>{loading ? 'Création...' : 'Créer mon compte'}</button>
          <p className="auth-switch">Déjà inscrit&nbsp;? <Link to="/connexion">Se connecter</Link></p>
        </form>
      )}
    </AuthShell>
  );
}

export function VerifyEmail() {
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
    <AuthShell title="Activation du compte" subtitle="Confirmation sécurisée de votre adresse e-mail">
      <div className={state.success ? 'auth-success' : state.loading ? 'auth-status' : 'login-error'}>
        {state.message}
        {!state.loading && <Link to="/connexion">Aller à la connexion</Link>}
      </div>
    </AuthShell>
  );
}

export function ForgotPassword() {
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
    <AuthShell title="Mot de passe oublié" subtitle="Recevez un lien sécurisé pour choisir un nouveau mot de passe.">
      {message ? <div className="auth-success">{message}<Link to="/connexion">Retour à la connexion</Link></div> : (
        <form onSubmit={submit}>
          {error && <div className="login-error">{error}</div>}
          <label htmlFor="reset-email">Adresse e-mail</label>
          <input id="reset-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <button className="btn btn-gold auth-submit" type="submit" disabled={loading}>{loading ? 'Envoi...' : 'Envoyer le lien'}</button>
          <p className="auth-switch"><Link to="/connexion">Retour à la connexion</Link></p>
        </form>
      )}
    </AuthShell>
  );
}

export function ResetPassword() {
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
    <AuthShell title="Nouveau mot de passe" subtitle="Choisissez un nouveau mot de passe sécurisé.">
      {message ? <div className="auth-success">{message}<Link to="/connexion">Se connecter</Link></div> : (
        <form onSubmit={submit}>
          {error && <div className="login-error">{error}</div>}
          <label htmlFor="new-password">Nouveau mot de passe</label>
          <input id="new-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          <label htmlFor="new-password-confirmation">Confirmer le mot de passe</label>
          <input id="new-password-confirmation" type="password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required />
          <button className="btn btn-gold auth-submit" type="submit" disabled={loading}>{loading ? 'Modification...' : 'Modifier le mot de passe'}</button>
        </form>
      )}
    </AuthShell>
  );
}

import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import client from '../../api/client';
import PreferenceControls from '../../components/PreferenceControls';
import usePreferences from '../../hooks/usePreferences';
import apiError from '../../utils/apiError';
import { roleLabel } from '../../utils/roles';
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

export function Register() {
  const { tr } = usePreferences();
  const [registration, setRegistration] = useState(null);
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone_number: '', password: '', confirmPassword: '',
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    client.get('/auth/registration-status/')
      .then(({ data }) => setRegistration(data))
      .catch(() => setRegistration({ open: false, role: null, detail: '' }));
  }, []);

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
      setError(apiError(requestError, tr('Impossible de créer le compte. Veuillez réessayer.', 'Unable to create the account. Please try again.'), tr));
    } finally {
      setLoading(false);
    }
  }

  if (registration === null) {
    return (
      <AuthShell title={tr('Créer un compte', 'Create an account')} subtitle={tr('Vérification des accès disponibles...', 'Checking available access...')}>
        <div className="auth-status">{tr('Chargement...', 'Loading...')}</div>
      </AuthShell>
    );
  }

  if (!registration.open) {
    return (
      <AuthShell
        title={tr('Inscriptions fermées', 'Registration closed')}
        subtitle={tr('Les comptes sont créés sur invitation', 'Accounts are created by invitation')}
      >
        <div className="auth-status">
          {registration.detail || tr(
            'Les inscriptions publiques sont fermées. Demandez à votre responsable de vous inviter par e-mail.',
            'Public registration is closed. Ask your manager to invite you by email.',
          )}
          <Link to="/connexion">{tr('Aller à la connexion', 'Go to sign in')}</Link>
        </div>
      </AuthShell>
    );
  }

  const post = roleLabel(registration.role, tr);

  return (
    <AuthShell
      title={tr(`Créer le compte ${post}`, `Create the ${post} account`)}
      subtitle={tr(
        'Ce poste est encore vacant : votre inscription le pourvoit définitivement.',
        'This post is still vacant: your registration fills it for good.',
      )}
    >
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

export function AcceptInvitation() {
  const { tr } = usePreferences();
  const [params] = useSearchParams();
  const token = params.get('token');
  const [invitation, setInvitation] = useState(null);
  const [invalid, setInvalid] = useState('');
  const [form, setForm] = useState({
    first_name: '', last_name: '', phone_number: '', password: '', confirmPassword: '',
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      setInvalid(tr('Le lien d’invitation est incomplet.', 'The invitation link is incomplete.'));
      return;
    }
    client.get('/auth/invitations/detail/', { params: { token } })
      .then(({ data }) => {
        setInvitation(data);
        setForm((current) => ({
          ...current, first_name: data.first_name || '', last_name: data.last_name || '',
        }));
      })
      .catch((requestError) => setInvalid(apiError(
        requestError,
        tr('Cette invitation est invalide ou expirée.', 'This invitation is invalid or expired.'),
        tr,
      )));
  }, [token, tr]);

  function update(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  async function submit(event) {
    event.preventDefault();
    setError('');
    if (form.password !== form.confirmPassword) {
      setError(tr('Les deux mots de passe ne correspondent pas.', 'The passwords do not match.'));
      return;
    }
    setLoading(true);
    try {
      const payload = { ...form, token };
      delete payload.confirmPassword;
      const { data } = await client.post('/auth/invitations/accept/', payload);
      setMessage(data.detail);
    } catch (requestError) {
      setError(apiError(requestError, tr('Impossible d’activer le compte.', 'Unable to activate the account.'), tr));
    } finally {
      setLoading(false);
    }
  }

  if (invalid) {
    return (
      <AuthShell title={tr('Invitation invalide', 'Invalid invitation')} subtitle={tr('Activation de votre accès', 'Activating your access')}>
        <div className="login-error">{invalid}<Link to="/connexion">{tr('Aller à la connexion', 'Go to sign in')}</Link></div>
      </AuthShell>
    );
  }

  if (!invitation) {
    return (
      <AuthShell title={tr('Activation du compte', 'Account activation')} subtitle={tr('Vérification de votre invitation...', 'Checking your invitation...')}>
        <div className="auth-status">{tr('Chargement...', 'Loading...')}</div>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title={tr('Activer mon compte', 'Activate my account')}
      subtitle={tr(
        `Accès ${roleLabel(invitation.role, tr).toLowerCase()} pour ${invitation.email}`,
        `${roleLabel(invitation.role, tr)} access for ${invitation.email}`,
      )}
    >
      {message ? (
        <div className="auth-success">{message}<Link to="/connexion">{tr('Se connecter', 'Sign in')}</Link></div>
      ) : (
        <form onSubmit={submit}>
          {error && <div className="login-error">{error}</div>}
          {invitation.invited_by && (
            <p className="auth-note">
              {tr(`Invitation envoyée par ${invitation.invited_by}.`, `Invitation sent by ${invitation.invited_by}.`)}
            </p>
          )}
          <div className="auth-field-grid">
            <div><label htmlFor="invite-first">{tr('Prénom', 'First name')}</label><input id="invite-first" name="first_name" value={form.first_name} onChange={update} required /></div>
            <div><label htmlFor="invite-last">{tr('Nom', 'Last name')}</label><input id="invite-last" name="last_name" value={form.last_name} onChange={update} required /></div>
          </div>
          <label htmlFor="invite-phone">{tr('Téléphone', 'Phone')}</label>
          <input id="invite-phone" name="phone_number" type="tel" value={form.phone_number} onChange={update} />
          <div className="auth-field-grid">
            <div>
              <label htmlFor="invite-password">{tr('Mot de passe', 'Password')}</label>
              <input id="invite-password" name="password" type="password" value={form.password} onChange={update} required />
            </div>
            <div>
              <label htmlFor="invite-confirm">{tr('Confirmation', 'Confirmation')}</label>
              <input id="invite-confirm" name="confirmPassword" type="password" value={form.confirmPassword} onChange={update} required />
            </div>
          </div>
          <button className="btn btn-gold auth-submit" type="submit" disabled={loading}>
            {loading ? tr('Activation...', 'Activating...') : tr('Activer mon compte', 'Activate my account')}
          </button>
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
      .catch((error) => setState({ loading: false, success: false, message: apiError(error, tr('Impossible de confirmer ce compte.', 'Unable to confirm this account.'), tr) }));
  }, [token, tr]);

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
      setError(apiError(requestError, tr('Impossible d’envoyer la demande.', 'Unable to send the request.'), tr));
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
      setError(apiError(requestError, tr('Impossible de modifier le mot de passe.', 'Unable to change the password.'), tr));
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

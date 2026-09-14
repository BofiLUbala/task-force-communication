/**
 * Turn an axios failure into a message a user can act on.
 *
 * The distinction that matters is "the server answered and said no" versus
 * "the request never reached the server". Collapsing the two into a single
 * credentials error sends people hunting for a wrong password when the real
 * cause is a backend that is down or a blocked CORS origin.
 */
export default function apiError(error, fallback, tr = (fr) => fr) {
  // No response at all: DNS, connection refused, timeout, or a preflight the
  // browser rejected. Axios reports CORS failures this way too — the browser
  // never exposes the response to JS.
  if (!error?.response) {
    if (error?.code === 'ECONNABORTED') {
      return tr(
        'Le serveur met trop de temps à répondre. Réessayez dans un instant.',
        'The server is taking too long to respond. Please try again shortly.',
      );
    }
    return tr(
      'Serveur injoignable. Vérifiez que le backend est démarré, puis réessayez.',
      'Cannot reach the server. Check that the backend is running, then try again.',
    );
  }

  if (error.response.status >= 500) {
    return tr(
      'Le serveur a rencontré une erreur. Réessayez dans un instant.',
      'The server hit an error. Please try again shortly.',
    );
  }

  const data = error.response.data;
  if (typeof data?.detail === 'string') return data.detail;
  if (data && typeof data === 'object') {
    const first = Object.values(data).flat()[0];
    if (first) return String(first);
  }
  return fallback;
}

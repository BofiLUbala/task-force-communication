import { Navigate, Route, Routes, useParams } from 'react-router-dom';
import PublicLayout from './components/PublicLayout';
import ProtectedRoute from './components/ProtectedRoute';
import Home from './pages/public/Home';
import Activites from './pages/public/Activites';
import Actualites from './pages/public/Actualites';
import Galerie from './pages/public/Galerie';
import Videos from './pages/public/Videos';
import Contact from './pages/public/Contact';
import About from './pages/public/About';
import Newsletter from './pages/public/Newsletter';
import NewsletterUnsubscribe from './pages/public/NewsletterUnsubscribe';
import Communiques from './pages/public/Communiques';
import PostDetail from './pages/public/PostDetail';
import Login from './pages/internal/Login';
import { AcceptInvitation, ForgotPassword, Register, ResetPassword, VerifyEmail } from './pages/internal/AuthPages';
import AgentDashboard from './pages/internal/AgentDashboard';
import HierarchyDashboard from './pages/internal/HierarchyDashboard';
import PublicationsHome from './pages/internal/PublicationsHome';
import PublicationComposer from './pages/internal/PublicationComposer';
import PublicationDetail from './pages/internal/PublicationDetail';
import SocialLinksDashboard from './pages/internal/SocialLinksDashboard';
import AccountsDashboard from './pages/internal/AccountsDashboard';

/**
 * The five per-type composer routes are gone, but people have them bookmarked
 * and the hierarchy has them in e-mails. Each one now lands on the single
 * composer instead of 404-ing.
 */
function LegacyTypeRedirect() {
  const { slug } = useParams();
  return <Navigate replace to={slug ? `/espace/publications/${slug}/modifier` : '/espace/publications/nouvelle'} />;
}

const LEGACY_TYPES = ['actualite', 'image', 'video', 'communique', 'newsletter'];

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/activites" element={<Activites />} />
        <Route path="/actualites" element={<Actualites />} />
        <Route path="/galerie" element={<Galerie />} />
        <Route path="/videos" element={<Videos />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/a-propos" element={<About />} />
        <Route path="/newsletter" element={<Newsletter />} />
        <Route path="/newsletter/desabonnement/:token" element={<NewsletterUnsubscribe />} />
        <Route path="/communiques" element={<Communiques />} />
        <Route path="/publications/:slug" element={<PostDetail />} />
      </Route>

      <Route path="/connexion" element={<Login />} />
      <Route path="/inscription" element={<Register />} />
      <Route path="/confirmation-email" element={<VerifyEmail />} />
      <Route path="/activation-compte" element={<AcceptInvitation />} />
      <Route path="/mot-de-passe-oublie" element={<ForgotPassword />} />
      <Route path="/nouveau-mot-de-passe" element={<ResetPassword />} />

      <Route element={<ProtectedRoute role="SUPER_ADMIN" />}>
        <Route path="/espace/admin" element={<AccountsDashboard />} />
      </Route>

      <Route element={<ProtectedRoute role="AGENT" />}>
        <Route path="/espace/rapports" element={<AgentDashboard />} />
      </Route>

      <Route element={<ProtectedRoute role="HIERARCHY" />}>
        <Route path="/espace/validation" element={<HierarchyDashboard />} />
        <Route path="/espace/agents" element={<AccountsDashboard />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route path="/espace/publications" element={<PublicationsHome />} />
        <Route path="/espace/publications/nouvelle" element={<PublicationComposer />} />
        <Route path="/espace/publications/brouillons" element={<PublicationsHome initialFilter="drafts" />} />
        <Route path="/espace/publications/programmees" element={<PublicationsHome initialFilter="scheduled" />} />
        <Route path="/espace/publications/publiees" element={<PublicationsHome initialFilter="published" />} />

        {LEGACY_TYPES.map((type) => (
          <Route key={type} path={`/espace/publications/${type}`} element={<LegacyTypeRedirect />} />
        ))}
        {LEGACY_TYPES.map((type) => (
          <Route key={`${type}-slug`} path={`/espace/publications/${type}/:slug`} element={<LegacyTypeRedirect />} />
        ))}

        <Route path="/espace/publications/:slug" element={<PublicationDetail />} />
        <Route path="/espace/publications/:slug/modifier" element={<PublicationComposer />} />
        <Route path="/espace/reseaux-sociaux" element={<SocialLinksDashboard />} />
      </Route>
    </Routes>
  );
}

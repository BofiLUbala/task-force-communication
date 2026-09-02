import { Route, Routes } from 'react-router-dom';
import PublicLayout from './components/PublicLayout';
import ProtectedRoute from './components/ProtectedRoute';
import Home from './pages/public/Home';
import Activites from './pages/public/Activites';
import Actualites from './pages/public/Actualites';
import Galerie from './pages/public/Galerie';
import Videos from './pages/public/Videos';
import Contact from './pages/public/Contact';
import Login from './pages/internal/Login';
import { ForgotPassword, Register, ResetPassword, VerifyEmail } from './pages/internal/AuthPages';
import AgentDashboard from './pages/internal/AgentDashboard';
import HierarchyDashboard from './pages/internal/HierarchyDashboard';
import PublicationDashboard from './pages/internal/PublicationDashboard';
import SocialLinksDashboard from './pages/internal/SocialLinksDashboard';

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
      </Route>

      <Route path="/connexion" element={<Login />} />
      <Route path="/inscription" element={<Register />} />
      <Route path="/confirmation-email" element={<VerifyEmail />} />
      <Route path="/mot-de-passe-oublie" element={<ForgotPassword />} />
      <Route path="/nouveau-mot-de-passe" element={<ResetPassword />} />

      <Route element={<ProtectedRoute role="AGENT" />}>
        <Route path="/espace/rapports" element={<AgentDashboard />} />
      </Route>

      <Route element={<ProtectedRoute role="HIERARCHY" />}>
        <Route path="/espace/validation" element={<HierarchyDashboard />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route path="/espace/publications/actualite" element={<PublicationDashboard type="actualite" />} />
        <Route path="/espace/publications/image" element={<PublicationDashboard type="image" />} />
        <Route path="/espace/publications/video" element={<PublicationDashboard type="video" />} />
        <Route path="/espace/publications/communique" element={<PublicationDashboard type="communique" />} />
        <Route path="/espace/reseaux-sociaux" element={<SocialLinksDashboard />} />
      </Route>
    </Routes>
  );
}

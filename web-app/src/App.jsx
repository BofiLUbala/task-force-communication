import { Route, Routes } from 'react-router-dom';
import PublicLayout from './components/PublicLayout';
import ProtectedRoute from './components/ProtectedRoute';
import Home from './pages/public/Home';
import Activites from './pages/public/Activites';
import Actualites from './pages/public/Actualites';
import Galerie from './pages/public/Galerie';
import Contact from './pages/public/Contact';
import Login from './pages/internal/Login';
import AgentDashboard from './pages/internal/AgentDashboard';
import HierarchyDashboard from './pages/internal/HierarchyDashboard';

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/activites" element={<Activites />} />
        <Route path="/actualites" element={<Actualites />} />
        <Route path="/galerie" element={<Galerie />} />
        <Route path="/contact" element={<Contact />} />
      </Route>

      <Route path="/connexion" element={<Login />} />

      <Route element={<ProtectedRoute role="AGENT" />}>
        <Route path="/espace/rapports" element={<AgentDashboard />} />
      </Route>

      <Route element={<ProtectedRoute role="HIERARCHY" />}>
        <Route path="/espace/validation" element={<HierarchyDashboard />} />
      </Route>
    </Routes>
  );
}

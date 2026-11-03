/** Routes de l'application, protégées par authentification et par rôle. */
import { lazy, Suspense, type ReactNode } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { DataProvider } from "./components/DataContext";
import Layout from "./components/Layout";
import { Spinner, ToastProvider } from "./components/ui";
import { peut, PERMISSIONS } from "./lib/format";
import LoginPage from "./pages/LoginPage";
// Chargement à la demande : chaque page est un fichier JavaScript séparé (premier affichage plus rapide)
const AdminPage = lazy(() => import("./pages/AdminPage"));
const AnalysisPage = lazy(() => import("./pages/AnalysisPage"));
const AssistantPage = lazy(() => import("./pages/AssistantPage"));
const CohortsPage = lazy(() => import("./pages/CohortsPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const FundingsPage = lazy(() => import("./pages/FundingsPage"));
const ImportPage = lazy(() => import("./pages/ImportPage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));
const ProjectDetailPage = lazy(() => import("./pages/ProjectDetailPage"));
const ProjectsPage = lazy(() => import("./pages/ProjectsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const AlertsPage = lazy(() => import("./pages/AlertsPage"));
const ComparisonPage = lazy(() => import("./pages/ComparisonPage"));
const RisksPage = lazy(() => import("./pages/RisksPage"));
const ObjectivesPage = lazy(() => import("./pages/ObjectivesPage"));


function Protected({ children, perm }: { children: ReactNode; perm?: keyof typeof PERMISSIONS }) {
  const { user, loading } = useAuth();
  if (loading) return <Spinner label="Vérification de la session…" />;
  if (!user) return <Navigate to="/connexion" replace />;
  if (perm && !peut(user.role, perm)) {
    return (
      <div className="carte mx-auto mt-10 max-w-md p-6 text-center">
        <p className="font-semibold text-profond">Accès refusé</p>
        <p className="mt-1 text-sm text-muted">Votre rôle ne permet pas d'accéder à cette page.</p>
        <Link to="/" className="btn-lien mt-3 inline-block">Retour au tableau de bord</Link>
      </div>
    );
  }
  return <>{children}</>;
}

function Shell() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner label="Chargement de CIAT VISION…" />;
  return (
    <Routes>
      <Route path="/connexion" element={<LoginPage />} />
      <Route element={user ? <DataProvider><Suspense fallback={<Spinner />}><Layout /></Suspense></DataProvider> : <Navigate to="/connexion" replace />}>
        <Route index element={<DashboardPage />} />
        <Route path="projets" element={<ProjectsPage />} />
        <Route path="projets/:id" element={<ProjectDetailPage />} />
        <Route path="analyses" element={<AnalysisPage />} />
        <Route path="cohortes" element={<CohortsPage />} />
        <Route path="financements" element={<FundingsPage />} />
        <Route path="assistant" element={<AssistantPage />} />
        <Route path="rapports" element={<ReportsPage />} />
        <Route path="alertes" element={<AlertsPage />} />
        <Route path="comparaisons" element={<ComparisonPage />} />
        <Route path="risques" element={<RisksPage />} />
        <Route path="objectifs" element={<ObjectivesPage />} />
        <Route path="importation" element={<Protected perm="importer"><ImportPage /></Protected>} />
        <Route path="administration" element={<Protected perm="administrer"><AdminPage /></Protected>} />
        <Route path="profil" element={<ProfilePage />} />
        <Route path="*" element={<div className="carte p-8 text-center"><p className="font-semibold">Page introuvable</p><Link className="btn-lien" to="/">Retour à l'accueil</Link></div>} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <Shell />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}

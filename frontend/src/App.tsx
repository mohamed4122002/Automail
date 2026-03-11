import React, { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import LoginPage from "./auth/LoginPage";
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Campaigns = lazy(() => import("./pages/Campaigns"));
const CampaignCreate = lazy(() => import("./pages/CampaignCreate"));
const CampaignDetail = lazy(() => import("./pages/CampaignDetail"));
const UserDetail = lazy(() => import("./pages/UserDetail"));
const Users = lazy(() => import("./pages/Users"));
const Leads = lazy(() => import("./pages/Leads"));
const LeadsPipeline = lazy(() => import("./pages/LeadsPipeline"));
const LeadsList = lazy(() => import("./pages/LeadsList"));
const Settings = lazy(() => import("./pages/Settings"));
const WorkflowBuilder = lazy(() => import("./pages/WorkflowBuilder"));
const Workflows = lazy(() => import("./pages/Workflows"));
const Unsubscribe = lazy(() => import("./pages/Unsubscribe"));
const Templates = lazy(() => import("./pages/Templates"));
const TemplateEditor = lazy(() => import("./pages/TemplateEditor"));
const Contacts = lazy(() => import("./pages/Contacts"));
const LeadDetail = lazy(() => import("./pages/LeadDetail"));
const SystemStatus = lazy(() => import("./pages/SystemStatus"));
const AdminPortal = lazy(() => import("./pages/AdminPortal"));
const Performance = lazy(() => import("./pages/Performance"));
const CalendarIntegrations = lazy(() => import("@/pages/CalendarIntegrations"));
const GoogleCallback = lazy(() => import("@/pages/GoogleCallback"));
const Organizations = lazy(() => import("./pages/Organizations"));
const OrganizationDetail = lazy(() => import("./pages/OrganizationDetail"));
const MyDashboard = lazy(() => import("./pages/MyDashboard"));
const PermissionsMatrix = lazy(() => import("./pages/PermissionsMatrix"));
const LeadsPool = lazy(() => import("./pages/LeadsPool"));
const ActionCenter = lazy(() => import("./pages/ActionCenter"));

const PrivateRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { token, loading } = useAuth();
  if (loading) return <div className="p-8 text-slate-400">Verifying session...</div>;
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

const AdminRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { token, isAdmin, loading } = useAuth();
  if (loading) return <div className="p-8 text-slate-400">Verifying permissions...</div>;
  if (!token) return <Navigate to="/login" replace />;
  if (!isAdmin) return <Navigate to="/" replace />;
  return children;
};

const DashboardRedirect: React.FC = () => {
  const { isTeamMember } = useAuth();
  if (isTeamMember) return <Navigate to="/my-dashboard" replace />;
  return <Dashboard />;
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Suspense fallback={<div className="p-8 text-center">Loading...</div>}>
        <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Dashboard */}
        <Route
          path="/"
          element={
            <PrivateRoute>
              <DashboardRedirect />
            </PrivateRoute>
          }
        />

        <Route
          path="/action-center"
          element={
            <PrivateRoute>
              <ActionCenter />
            </PrivateRoute>
          }
        />

        <Route
          path="/my-dashboard"
          element={
            <PrivateRoute>
              <MyDashboard />
            </PrivateRoute>
          }
        />

        {/* Contacts & Leads */}
        <Route
          path="/contacts"
          element={
            <PrivateRoute>
              <Suspense fallback={<div className="p-8 text-slate-400">Loading contacts…</div>}>
                <Contacts />
              </Suspense>
            </PrivateRoute>
          }
        />
        <Route
          path="/leads"
          element={
            <PrivateRoute>
              <Navigate to="/leads/pipeline" replace />
            </PrivateRoute>
          }
        />
        <Route
          path="/leads/pipeline"
          element={
            <PrivateRoute>
              <Suspense fallback={<div className="p-8 text-slate-400">Loading pipeline…</div>}>
                <LeadsPipeline />
              </Suspense>
            </PrivateRoute>
          }
        />
        <Route
          path="/leads/list"
          element={
            <PrivateRoute>
              <Suspense fallback={<div className="p-8 text-slate-400">Loading list…</div>}>
                <LeadsList />
              </Suspense>
            </PrivateRoute>
          }
        />
        <Route
          path="/leads/:id"
          element={
            <PrivateRoute>
              <LeadDetail />
            </PrivateRoute>
          }
        />
        <Route
          path="/leads/pool"
          element={
            <PrivateRoute>
              <LeadsPool />
            </PrivateRoute>
          }
        />

        {/* Organizations */}
        <Route
          path="/organizations"
          element={
            <PrivateRoute>
              <Organizations />
            </PrivateRoute>
          }
        />
        <Route
          path="/organizations/:id"
          element={
            <PrivateRoute>
              <OrganizationDetail />
            </PrivateRoute>
          }
        />

        {/* Campaigns */}
        <Route
          path="/campaigns"
          element={
            <PrivateRoute>
              <Campaigns />
            </PrivateRoute>
          }
        />
        <Route
          path="/campaigns/new"
          element={
            <PrivateRoute>
              <CampaignCreate />
            </PrivateRoute>
          }
        />
        <Route
          path="/campaigns/:id"
          element={
            <PrivateRoute>
              <CampaignDetail />
            </PrivateRoute>
          }
        />

        {/* Workflows */}
        <Route
          path="/workflows"
          element={
            <PrivateRoute>
              <Workflows />
            </PrivateRoute>
          }
        />
        <Route
          path="/workflows/:id/edit"
          element={
            <PrivateRoute>
              <WorkflowBuilder />
            </PrivateRoute>
          }
        />

        {/* Users (Team) */}
        <Route
          path="/users"
          element={
            <PrivateRoute>
              <Users />
            </PrivateRoute>
          }
        />
        <Route
          path="/users/:id"
          element={
            <PrivateRoute>
              <UserDetail />
            </PrivateRoute>
          }
        />

        {/* Templates */}
        <Route
          path="/templates"
          element={
            <PrivateRoute>
              <Templates />
            </PrivateRoute>
          }
        />
        <Route
          path="/templates/:id/edit"
          element={
            <PrivateRoute>
              <TemplateEditor />
            </PrivateRoute>
          }
        />
        <Route
          path="/templates/new"
          element={
            <PrivateRoute>
              <TemplateEditor />
            </PrivateRoute>
          }
        />

        {/* Settings & System */}
        <Route
          path="/settings"
          element={
            <PrivateRoute>
              <Settings />
            </PrivateRoute>
          }
        />
        <Route
          path="/calendar"
          element={
            <PrivateRoute>
              <CalendarIntegrations />
            </PrivateRoute>
          }
        />
        <Route
          path="/auth/google/callback"
          element={
            <PrivateRoute>
              <GoogleCallback />
            </PrivateRoute>
          }
        />
        <Route
          path="/analytics/system"
          element={
            <PrivateRoute>
              <SystemStatus />
            </PrivateRoute>
          }
        />
        <Route
          path="/analytics/performance"
          element={
            <PrivateRoute>
              <Performance />
            </PrivateRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <AdminPortal />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/permissions"
          element={
            <AdminRoute>
              <PermissionsMatrix />
            </AdminRoute>
          }
        />

        {/* Redirects for refactored routes */}
        <Route path="/system-status" element={<Navigate to="/analytics/system" replace />} />
        <Route path="/performance" element={<Navigate to="/analytics/performance" replace />} />

        {/* Public Routes */}
        <Route path="/unsubscribe/:token" element={<Unsubscribe />} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
    </AuthProvider>
  );
};

export default App;

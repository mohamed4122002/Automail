import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import LoginPage from "./auth/LoginPage";
import Dashboard from "./pages/Dashboard";
import Campaigns from "./pages/Campaigns";
import CampaignCreate from "./pages/CampaignCreate";
import CampaignDetail from "./pages/CampaignDetail";
import UserDetail from "./pages/UserDetail";
import Users from "./pages/Users";
import Leads from "./pages/Leads";
import Settings from "./pages/Settings";
import WorkflowBuilder from "./pages/WorkflowBuilder";
import Workflows from "./pages/Workflows";
import Unsubscribe from "./pages/Unsubscribe";
import Templates from "./pages/Templates";
import TemplateEditor from "./pages/TemplateEditor";
import Contacts from "./pages/Contacts";
import LeadDetail from "./pages/LeadDetail";
import SystemStatus from "./pages/SystemStatus";

const PrivateRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { token } = useAuth();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Dashboard */}
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Dashboard />
            </PrivateRoute>
          }
        />

        {/* Contacts & Leads */}
        <Route
          path="/contacts"
          element={
            <PrivateRoute>
              <Contacts />
            </PrivateRoute>
          }
        />
        <Route
          path="/leads"
          element={
            <PrivateRoute>
              <Leads />
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
          path="/system-status"
          element={
            <PrivateRoute>
              <SystemStatus />
            </PrivateRoute>
          }
        />

        {/* Public Routes */}
        <Route path="/unsubscribe/:token" element={<Unsubscribe />} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
};

export default App;

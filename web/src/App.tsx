import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import Login from "./pages/Login";
import Chat from "./pages/Chat";
import Scan from "./pages/Scan";
import Settings from "./pages/Settings";
import ApplianceDetail from "./pages/ApplianceDetail";
import BottomNav from "./components/BottomNav";

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#1a237e]">
        <span className="text-white text-lg">Chargement...</span>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-hidden">{children}</div>
      <BottomNav />
    </div>
  );
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#1a237e]">
        <span className="text-white text-lg">Chargement...</span>
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/scan" replace /> : <Login />}
      />
      <Route
        path="/chat"
        element={
          <AuthGuard>
            <AppLayout><Chat /></AppLayout>
          </AuthGuard>
        }
      />
      <Route
        path="/scan"
        element={
          <AuthGuard>
            <AppLayout><Scan /></AppLayout>
          </AuthGuard>
        }
      />
      <Route
        path="/scan/:id"
        element={
          <AuthGuard>
            <AppLayout><ApplianceDetail /></AppLayout>
          </AuthGuard>
        }
      />
      <Route
        path="/settings"
        element={
          <AuthGuard>
            <AppLayout><Settings /></AppLayout>
          </AuthGuard>
        }
      />
      <Route path="/" element={<Navigate to={user ? "/scan" : "/login"} replace />} />
      <Route path="*" element={<Navigate to={user ? "/scan" : "/login"} replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

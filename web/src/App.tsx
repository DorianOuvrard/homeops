import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { AppProvider } from "./AppContext";
import Login from "./pages/Login";
import Chat from "./pages/Chat";
import Scan from "./pages/Scan";
import Maintenance from "./pages/Maintenance";
import Settings from "./pages/Settings";
import Bran from "./pages/Bran";
import ApplianceDetail from "./pages/ApplianceDetail";
import Header from "./components/Header";
import BottomNav from "./components/BottomNav";
import { useEffect } from "react";
import { syncMaintenanceNotifications } from "./notifications";

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#faf8f5]">
        <span className="text-white text-lg">Chargement...</span>
      </div>
    );
  }
  if (!user) {
    // Auto-login is handled by AuthProvider; avoid redirect loop since login page is removed
    return (
      <div className="flex items-center justify-center h-screen bg-[#faf8f5]">
        <span className="text-[#8b7355] text-lg">Connexion en cours...</span>
      </div>
    );
  }
  return <>{children}</>;
}

function AppLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();

  useEffect(() => {
    if (!user) return;
    syncMaintenanceNotifications().catch((err) => {
      console.warn("Unable to schedule notifications", err);
    });
  }, [user]);

  return (
    <AppProvider>
      <div className="flex flex-col h-screen">
        <Header />
        <div className="flex-1 overflow-hidden">{children}</div>
        <BottomNav />
      </div>
    </AppProvider>
  );
}

function PersistentTabs() {
  const path = useLocation().pathname;

  return (
    <>
      {/* Main tabs stay mounted, hidden via CSS to preserve state */}
      <div className="h-full" style={{ display: path === "/scan" ? undefined : "none" }}>
        <Scan />
      </div>
      <div className="h-full" style={{ display: path === "/chat" ? undefined : "none" }}>
        <Chat visible={path === "/chat"} />
      </div>
      <div className="h-full" style={{ display: path === "/maintenance" ? undefined : "none" }}>
        <Maintenance />
      </div>
      <div className="h-full" style={{ display: path === "/bran" ? undefined : "none" }}>
        <Bran />
      </div>
      <div className="h-full" style={{ display: path === "/settings" ? undefined : "none" }}>
        <Settings />
      </div>
      {/* Detail routes mount/unmount normally */}
      <Routes>
        <Route path="/scan/:id" element={<ApplianceDetail />} />
      </Routes>
    </>
  );
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#faf8f5]">
        <span className="text-white text-lg">Chargement...</span>
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={<Navigate to="/scan" replace />}
      />
      <Route
        path="/*"
        element={
          <AuthGuard>
            <AppLayout><PersistentTabs /></AppLayout>
          </AuthGuard>
        }
      />
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

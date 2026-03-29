import React, { createContext, useContext, useEffect, useState } from "react";
import { api, type User } from "./api";

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("hodoor_token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      api.auth
        .me()
        .then(setUser)
        .catch(() => {
          localStorage.removeItem("hodoor_token");
          setToken(null);
        })
        .finally(() => setLoading(false));
      return;
    }
    // Auto-login: create anonymous user silently
    const email = "demo@hodoor.dev";
    const password = "hodoor-demo-2026";
    api.auth
      .login(email, password)
      .catch(() => api.auth.signup(email, password).then(() => api.auth.login(email, password)))
      .then((res) => {
        if (res) {
          localStorage.setItem("hodoor_token", res.access_token);
          setToken(res.access_token);
        }
      })
      .catch((err) => console.error("Auto-login failed:", err))
      .finally(() => setLoading(false));
  }, [token]);

  const login = async (email: string, password: string) => {
    const res = await api.auth.login(email, password);
    localStorage.setItem("hodoor_token", res.access_token);
    setToken(res.access_token);
    const me = await api.auth.me();
    setUser(me);
  };

  const signup = async (email: string, password: string) => {
    await api.auth.signup(email, password);
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem("hodoor_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

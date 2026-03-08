import React, { createContext, useContext, useEffect, useState } from "react";
import axios from "axios";

interface UserProfile {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role: string;
  roles: string[];
}

interface AuthContextValue {
  token: string | null;
  user: UserProfile | null;
  loading: boolean;
  login: (token: string) => void;
  logout: () => void;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem("auth_token");
  });
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      localStorage.setItem("auth_token", token);
      axios.get("/api/auth/me", {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then((res: { data: UserProfile }) => setUser(res.data))
        .catch(() => logout())
        .finally(() => setLoading(false));
    } else {
      localStorage.removeItem("auth_token");
      setUser(null);
      setLoading(false);
    }
  }, [token]);

  const login = (newToken: string) => setToken(newToken);
  const logout = () => setToken(null);

  const isAdmin = user?.role === "admin" || (user?.roles || []).includes("admin");

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
};


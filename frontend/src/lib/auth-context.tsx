// Auth state lives here as a convenience for the UI: which nav links to
// show, which routes to redirect from. None of this is an enforcement
// boundary (Requirement 2.2) -- the API is the only place access is
// actually decided. A user who forges a token or edits local storage gains
// nothing; every request still gets checked server-side.

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, setAuthToken } from "./api";
import type { Role, TokenResponse, User } from "./types";

const STORAGE_KEY = "support_portal_token";

interface DecodedToken {
  sub: string;
  role: Role;
  exp: number;
}

function decodeToken(token: string): DecodedToken | null {
  try {
    const [, payload] = token.split(".");
    return JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

interface AuthState {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setAuthToken(token);
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    const decoded = decodeToken(token);
    if (!decoded || decoded.exp * 1000 < Date.now()) {
      localStorage.removeItem(STORAGE_KEY);
      setToken(null);
      setUser(null);
      setIsLoading(false);
      return;
    }

    api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => {
        localStorage.removeItem(STORAGE_KEY);
        setToken(null);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  const applyToken = (next: string) => {
    localStorage.setItem(STORAGE_KEY, next);
    setToken(next);
  };

  const login = async (email: string, password: string) => {
    const result = await api.post<TokenResponse>("/auth/login", { email, password });
    applyToken(result.access_token);
  };

  const register = async (email: string, password: string, fullName: string) => {
    await api.post("/auth/register", { email, password, full_name: fullName });
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setAuthToken(null);
    setToken(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({ token, user, isLoading, login, register, logout }),
    [token, user, isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

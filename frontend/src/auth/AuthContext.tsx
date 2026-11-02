/**
 * Contexte d'authentification : utilisateur connecté, connexion, déconnexion,
 * renouvellement automatique du jeton tant que l'utilisateur est actif.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api, setUnauthorizedHandler, tokenStore } from "../api/client";
import type { TokenOut, User } from "../api/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: (reason?: string) => void;
  setUser: (u: User) => void;
  sessionMessage: string | null;
}

const AuthContext = createContext<AuthState | null>(null);
const EXPIRY_KEY = "ciat_vision_expiry";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionMessage, setSessionMessage] = useState<string | null>(null);
  const lastActivity = useRef(Date.now());

  const saveToken = (t: TokenOut) => {
    tokenStore.set(t.access_token);
    try { sessionStorage.setItem(EXPIRY_KEY, t.expires_at); } catch { /* indisponible */ }
    setUser(t.user);
  };

  const logout = useCallback((reason?: string) => {
    if (tokenStore.get()) api.post("/auth/logout").catch(() => undefined);
    tokenStore.clear();
    setUser(null);
    setSessionMessage(reason ?? null);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const t = await api.post<TokenOut>("/auth/login", { username, password });
    setSessionMessage(null);
    saveToken(t);
  }, []);

  // Restauration de la session au rechargement de la page
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setSessionMessage("Votre session a expiré. Veuillez vous reconnecter.");
    });
    if (!tokenStore.get()) { setLoading(false); return; }
    api.get<User>("/auth/me").then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);

  // Renouvellement : si l'utilisateur a été actif récemment et que le jeton expire dans < 10 min
  useEffect(() => {
    if (!user) return;
    const activite = () => { lastActivity.current = Date.now(); };
    window.addEventListener("pointerdown", activite);
    window.addEventListener("keydown", activite);
    const timer = window.setInterval(() => {
      let exp = 0;
      try { exp = new Date(sessionStorage.getItem(EXPIRY_KEY) ?? 0).getTime(); } catch { /* indisponible */ }
      const actif = Date.now() - lastActivity.current < 15 * 60_000;
      if (exp && exp - Date.now() < 10 * 60_000 && actif) {
        api.post<TokenOut>("/auth/refresh").then(saveToken).catch(() => undefined);
      }
    }, 60_000);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("pointerdown", activite);
      window.removeEventListener("keydown", activite);
    };
  }, [user]);

  const value = useMemo(() => ({ user, loading, login, logout, setUser, sessionMessage }),
    [user, loading, login, logout, sessionMessage]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans <AuthProvider>");
  return ctx;
}

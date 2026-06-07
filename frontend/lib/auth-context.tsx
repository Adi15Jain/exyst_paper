/**
 * Authentication context — provides user state to all components.
 *
 * Wraps the app with AuthProvider to get:
 * - user: Current user data (null if not logged in)
 * - loading: Whether auth state is being resolved
 * - login/register/logout functions
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { auth as authApi, User, getAccessToken, clearTokens } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const token = getAccessToken();
    if (token) {
      authApi
        .me()
        .then(setUser)
        .catch(() => {
          clearTokens();
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await authApi.login(email, password);
    const userData = await authApi.me();
    setUser(userData);
  }, []);

  const register = useCallback(async (email: string, password: string, name: string) => {
    await authApi.register(email, password, name);
    await authApi.login(email, password);
    const userData = await authApi.me();
    setUser(userData);
  }, []);

  const logout = useCallback(() => {
    authApi.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

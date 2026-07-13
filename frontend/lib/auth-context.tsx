/**
 * Authentication context — provides user state to all components.
 *
 * Wraps the app with AuthProvider to get:
 * - user: Current user data (null if not logged in)
 * - loading: Whether auth state is being resolved
 * - login/register/logout functions
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { auth as authApi, User } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  refreshUser: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore the session on mount: the access token lives in memory only, so
  // a page load exchanges the httpOnly refresh cookie for a new one.
  useEffect(() => {
    authApi
      .restore()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
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
    // Server revocation is fire-and-forget; local state clears immediately.
    void authApi.logout();
    setUser(null);
  }, []);

  // Re-read the profile after the user edits it (e.g. renames themselves).
  const refreshUser = useCallback(async () => {
    setUser(await authApi.me());
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

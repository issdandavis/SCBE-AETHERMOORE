/**
 * @file useAuth.ts
 * @module conference/frontend/hooks
 *
 * Auth context and hook for the conference app.
 */

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { setAuthToken } from './useApi';
import type { User } from '../../shared/types/index.js';

interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string) => Promise<boolean>;
  register: (email: string, displayName: string, role: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  login: async () => false,
  register: async () => false,
  logout: () => {},
});

export function useAuth(): AuthState {
  return useContext(AuthContext);
}

export { AuthContext };

export function useAuthProvider(): AuthState {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const login = useCallback(async (email: string): Promise<boolean> => {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (data.success) {
        setUser(data.data.user);
        setToken(data.data.token);
        setAuthToken(data.data.token);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, []);

  const register = useCallback(async (email: string, displayName: string, role: string): Promise<boolean> => {
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, displayName, role }),
      });
      const data = await res.json();
      if (data.success) {
        setUser(data.data.user);
        setToken(data.data.token);
        setAuthToken(data.data.token);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    setAuthToken(null);
  }, []);

  return { user, token, login, register, logout };
}

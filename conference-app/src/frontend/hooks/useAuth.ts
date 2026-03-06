/**
 * @file useAuth.ts
 * @module conference/frontend/hooks
 *
 * Auth context and hook for the conference app.
 * JWT access tokens (15min) + refresh tokens (7d) with auto-refresh.
 */

import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react';
import { setAuthToken } from './useApi';
import type { User } from '../../shared/types/index.js';

interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  register: (email: string, displayName: string, role: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  login: async () => ({ ok: false }),
  register: async () => ({ ok: false }),
  logout: () => {},
});

export function useAuth(): AuthState {
  return useContext(AuthContext);
}

export { AuthContext };

/** Store refresh token in localStorage (httpOnly cookie would be better in prod) */
function storeRefreshToken(token: string | null) {
  if (token) {
    localStorage.setItem('vc_refresh_token', token);
  } else {
    localStorage.removeItem('vc_refresh_token');
  }
}

function getRefreshToken(): string | null {
  return localStorage.getItem('vc_refresh_token');
}

export function useAuthProvider(): AuthState {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /** Schedule a token refresh 1 minute before expiry (14 min) */
  const scheduleRefresh = useCallback(() => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(async () => {
      const rt = getRefreshToken();
      if (!rt) return;
      try {
        const res = await fetch('/api/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refreshToken: rt }),
        });
        const data = await res.json();
        if (data.success) {
          setUser(data.data.user);
          setToken(data.data.token);
          setAuthToken(data.data.token);
          storeRefreshToken(data.data.refreshToken);
          scheduleRefresh();
        } else {
          // Refresh failed — log out
          setUser(null);
          setToken(null);
          setAuthToken(null);
          storeRefreshToken(null);
        }
      } catch {
        // Network error — will retry on next interaction
      }
    }, 14 * 60 * 1000); // 14 minutes
  }, []);

  /** On mount, try to restore session from refresh token */
  useEffect(() => {
    const rt = getRefreshToken();
    if (rt) {
      fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken: rt }),
      })
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            setUser(data.data.user);
            setToken(data.data.token);
            setAuthToken(data.data.token);
            storeRefreshToken(data.data.refreshToken);
            scheduleRefresh();
          } else {
            storeRefreshToken(null);
          }
        })
        .catch(() => {});
    }
    return () => {
      if (refreshTimer.current) clearTimeout(refreshTimer.current);
    };
  }, [scheduleRefresh]);

  const login = useCallback(async (email: string, password: string): Promise<{ ok: boolean; error?: string }> => {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (data.success) {
        setUser(data.data.user);
        setToken(data.data.token);
        setAuthToken(data.data.token);
        storeRefreshToken(data.data.refreshToken);
        scheduleRefresh();
        return { ok: true };
      }
      return { ok: false, error: data.error ?? 'Login failed' };
    } catch {
      return { ok: false, error: 'Network error' };
    }
  }, [scheduleRefresh]);

  const register = useCallback(async (email: string, displayName: string, role: string, password: string): Promise<{ ok: boolean; error?: string }> => {
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, displayName, role, password }),
      });
      const data = await res.json();
      if (data.success) {
        setUser(data.data.user);
        setToken(data.data.token);
        setAuthToken(data.data.token);
        storeRefreshToken(data.data.refreshToken);
        scheduleRefresh();
        return { ok: true };
      }
      return { ok: false, error: data.error ?? 'Registration failed' };
    } catch {
      return { ok: false, error: 'Network error' };
    }
  }, [scheduleRefresh]);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    setAuthToken(null);
    storeRefreshToken(null);
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
  }, []);

  return { user, token, login, register, logout };
}

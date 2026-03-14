/**
 * @file useApi.ts
 * @module conference/frontend/hooks
 *
 * API client hook for the conference app.
 */

import { useState, useCallback } from 'react';
import type { ApiResponse } from '../../shared/types/index.js';

const API_BASE = '/api';

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> ?? {}),
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  return res.json() as Promise<ApiResponse<T>>;
}

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const request = useCallback(async <T>(
    path: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<T>(path, options);
      if (!result.success && result.error) {
        setError(result.error);
      }
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Network error';
      setError(message);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  }, []);

  const get = useCallback(<T>(path: string) => request<T>(path), [request]);

  const post = useCallback(<T>(path: string, body: unknown) =>
    request<T>(path, {
      method: 'POST',
      body: JSON.stringify(body),
    }), [request]);

  return { get, post, loading, error };
}

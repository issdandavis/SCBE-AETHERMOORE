import { useSyncExternalStore } from 'react';

const HF_TOKEN_KEY = 'aethermoor.hf_token';
const BACKEND_KEY = 'aethermoor.backend_url';

let listeners: Array<() => void> = [];
const subscribe = (cb: () => void) => {
  listeners.push(cb);
  return () => {
    listeners = listeners.filter((l) => l !== cb);
  };
};
const notify = () => listeners.forEach((l) => l());

const read = () => ({
  token: localStorage.getItem(HF_TOKEN_KEY),
  backendUrl: localStorage.getItem(BACKEND_KEY),
});

export function useAuth() {
  const snap = useSyncExternalStore(subscribe, read, read);
  return {
    ...snap,
    signIn(token: string, backendUrl: string) {
      localStorage.setItem(HF_TOKEN_KEY, token.trim());
      localStorage.setItem(BACKEND_KEY, backendUrl.replace(/\/+$/, ''));
      notify();
    },
    signOut() {
      localStorage.removeItem(HF_TOKEN_KEY);
      localStorage.removeItem(BACKEND_KEY);
      notify();
    },
  };
}

// Light-touch helper — stay independent of any HTTP library.
export async function authedFetch(path: string, init?: RequestInit) {
  const { token, backendUrl } = read();
  if (!token || !backendUrl) {
    throw new Error('Not authenticated');
  }
  const url = path.startsWith('http') ? path : `${backendUrl}${path.startsWith('/') ? '' : '/'}${path}`;
  const headers = new Headers(init?.headers);
  headers.set('Authorization', `Bearer ${token}`);
  if (!headers.has('Content-Type') && init?.body) headers.set('Content-Type', 'application/json');
  return fetch(url, { ...init, headers });
}

// re-export for any hook that wants the snapshot without subscribing
export const useAuthSnapshot = () => useSyncExternalStore(subscribe, read, read);

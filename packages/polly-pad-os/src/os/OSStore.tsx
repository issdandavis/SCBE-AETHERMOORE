import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import type { WindowState, DesktopIcon, Notification, Theme, AppDefinition } from '@/types';
import { generateAppRegistry } from './appRegistry';

interface OSContextType {
  windows: WindowState[];
  desktopIcons: DesktopIcon[];
  notifications: Notification[];
  theme: Theme;
  startMenuOpen: boolean;
  activeWindowId: string | null;
  zIndexCounter: React.MutableRefObject<number>;
  appRegistry: Map<string, AppDefinition>;

  openApp: (appId: string, data?: any) => string | null;
  closeWindow: (windowId: string) => void;
  focusWindow: (windowId: string) => void;
  minimizeWindow: (windowId: string) => void;
  maximizeWindow: (windowId: string) => void;
  restoreWindow: (windowId: string) => void;
  setWindowSize: (windowId: string, w: number, h: number) => void;
  setWindowPos: (windowId: string, x: number, y: number) => void;
  setWindowTitle: (windowId: string, title: string) => void;

  setStartMenuOpen: (open: boolean) => void;
  setTheme: (theme: Theme) => void;
  addNotification: (n: Omit<Notification, 'id' | 'timestamp'>) => void;
  dismissNotification: (id: string) => void;

  getApp: (appId: string) => AppDefinition | undefined;
  getWindowsForApp: (appId: string) => WindowState[];
  isAppOpen: (appId: string) => boolean;
}

const OSContext = createContext<OSContextType | null>(null);

const defaultIcons: DesktopIcon[] = [
  { id: 'd1', appId: 'files', name: 'Files', icon: 'FolderOpen', x: 20, y: 20 },
  { id: 'd2', appId: 'terminal', name: 'Terminal', icon: 'Terminal', x: 20, y: 110 },
  { id: 'd3', appId: 'texteditor', name: 'Text Editor', icon: 'FileText', x: 20, y: 200 },
  { id: 'd4', appId: 'browser', name: 'Browser', icon: 'Globe', x: 20, y: 290 },
  { id: 'd5', appId: 'calculator', name: 'Calculator', icon: 'Calculator', x: 20, y: 380 },
  { id: 'd6', appId: 'settings', name: 'Settings', icon: 'Settings', x: 20, y: 470 },
];

export function OSProvider({ children }: { children: React.ReactNode }) {
  const [windows, setWindows] = useState<WindowState[]>([]);
  const [desktopIcons] = useState<DesktopIcon[]>(defaultIcons);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [theme, setTheme] = useState<Theme>('dark');
  const [startMenuOpen, setStartMenuOpen] = useState(false);
  const [activeWindowId, setActiveWindowId] = useState<string | null>(null);
  const zIndexCounter = useRef(100);
  const appRegistry = useRef(generateAppRegistry()).current;

  const openApp = useCallback(
    (appId: string, data?: any): string | null => {
      const app = appRegistry.get(appId);
      if (!app) return null;

      if (app.singleton) {
        const existing = windows.find((w) => w.appId === appId && !w.isMinimized);
        if (existing) {
          focusWindow(existing.id);
          return existing.id;
        }
      }

      const zIndex = ++zIndexCounter.current;
      const windowId = `win_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      const existingCount = windows.filter((w) => w.appId === appId).length;
      const title = existingCount > 0 ? `${app.name} (${existingCount + 1})` : app.name;

      const offsetX = (windows.length % 5) * 30;
      const offsetY = (windows.length % 5) * 30;

      const centerX = Math.max(50, (window.innerWidth - app.defaultSize.width) / 2 + offsetX);
      const centerY = Math.max(
        30,
        (window.innerHeight - app.defaultSize.height - 50) / 2 + offsetY
      );

      const newWindow: WindowState = {
        id: windowId,
        appId,
        title,
        x: Math.min(centerX, window.innerWidth - app.defaultSize.width - 20),
        y: Math.min(centerY, window.innerHeight - app.defaultSize.height - 80),
        width: app.defaultSize.width,
        height: app.defaultSize.height,
        isMinimized: false,
        isMaximized: false,
        isFocused: true,
        zIndex,
        data,
      };

      setWindows((prev) => {
        const updated = prev.map((w) => ({ ...w, isFocused: false }));
        return [...updated, newWindow];
      });
      setActiveWindowId(windowId);
      setStartMenuOpen(false);
      return windowId;
    },
    [windows, appRegistry]
  );

  const closeWindow = useCallback(
    (windowId: string) => {
      setWindows((prev) => {
        const filtered = prev.filter((w) => w.id !== windowId);
        if (filtered.length > 0) {
          const top = filtered.reduce((a, b) => (a.zIndex > b.zIndex ? a : b));
          return filtered.map((w) => ({ ...w, isFocused: w.id === top.id }));
        }
        return filtered;
      });
      if (activeWindowId === windowId) {
        setActiveWindowId(null);
      }
    },
    [activeWindowId]
  );

  const focusWindow = useCallback((windowId: string) => {
    const zIndex = ++zIndexCounter.current;
    setWindows((prev) =>
      prev.map((w) => ({
        ...w,
        isFocused: w.id === windowId,
        zIndex: w.id === windowId ? zIndex : w.zIndex,
        isMinimized: w.id === windowId ? false : w.isMinimized,
      }))
    );
    setActiveWindowId(windowId);
  }, []);

  const minimizeWindow = useCallback((windowId: string) => {
    setWindows((prev) => {
      const updated = prev.map((w) =>
        w.id === windowId ? { ...w, isMinimized: true, isFocused: false } : w
      );
      const visible = updated.filter((w) => !w.isMinimized);
      if (visible.length > 0) {
        const top = visible.reduce((a, b) => (a.zIndex > b.zIndex ? a : b));
        return updated.map((w) => ({ ...w, isFocused: w.id === top.id }));
      }
      return updated;
    });
    setActiveWindowId(null);
  }, []);

  const maximizeWindow = useCallback((windowId: string) => {
    setWindows((prev) =>
      prev.map((w) =>
        w.id === windowId
          ? {
              ...w,
              isMaximized: true,
              x: 0,
              y: 0,
              width: window.innerWidth,
              height: window.innerHeight - 48,
            }
          : w
      )
    );
  }, []);

  const restoreWindow = useCallback(
    (windowId: string) => {
      const app = appRegistry.get(windows.find((w) => w.id === windowId)?.appId || '');
      if (!app) return;
      setWindows((prev) =>
        prev.map((w) =>
          w.id === windowId
            ? {
                ...w,
                isMaximized: false,
                width: app.defaultSize.width,
                height: app.defaultSize.height,
                x: Math.max(50, (window.innerWidth - app.defaultSize.width) / 2),
                y: Math.max(30, (window.innerHeight - app.defaultSize.height - 50) / 2),
              }
            : w
        )
      );
    },
    [windows, appRegistry]
  );

  const setWindowSize = useCallback((windowId: string, width: number, height: number) => {
    setWindows((prev) => prev.map((w) => (w.id === windowId ? { ...w, width, height } : w)));
  }, []);

  const setWindowPos = useCallback((windowId: string, x: number, y: number) => {
    setWindows((prev) => prev.map((w) => (w.id === windowId ? { ...w, x, y } : w)));
  }, []);

  const setWindowTitle = useCallback((windowId: string, title: string) => {
    setWindows((prev) => prev.map((w) => (w.id === windowId ? { ...w, title } : w)));
  }, []);

  const addNotification = useCallback((n: Omit<Notification, 'id' | 'timestamp'>) => {
    const notif: Notification = {
      ...n,
      id: `notif_${Date.now()}`,
      timestamp: Date.now(),
    };
    setNotifications((prev) => [...prev.slice(-9), notif]);
    setTimeout(() => {
      setNotifications((prev) => prev.filter((x) => x.id !== notif.id));
    }, 5000);
  }, []);

  const dismissNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const getApp = useCallback((appId: string) => appRegistry.get(appId), [appRegistry]);
  const getWindowsForApp = useCallback(
    (appId: string) => windows.filter((w) => w.appId === appId),
    [windows]
  );
  const isAppOpen = useCallback(
    (appId: string) => windows.some((w) => w.appId === appId && !w.isMinimized),
    [windows]
  );

  return (
    <OSContext.Provider
      value={{
        windows,
        desktopIcons,
        notifications,
        theme,
        startMenuOpen,
        activeWindowId,
        zIndexCounter,
        appRegistry,
        openApp,
        closeWindow,
        focusWindow,
        minimizeWindow,
        maximizeWindow,
        restoreWindow,
        setWindowSize,
        setWindowPos,
        setWindowTitle,
        setStartMenuOpen,
        setTheme,
        addNotification,
        dismissNotification,
        getApp,
        getWindowsForApp,
        isAppOpen,
      }}
    >
      {children}
    </OSContext.Provider>
  );
}

export function useOS() {
  const ctx = useContext(OSContext);
  if (!ctx) throw new Error('useOS must be used within OSProvider');
  return ctx;
}

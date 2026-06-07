import type {
  AppDefinition,
  DesktopIcon,
  Notification,
  Theme,
  WindowState,
} from '../types/index.ts';
import {
  addAbacusLayer,
  calculateAbacusTotals,
  normalizeAbacusState,
  resetAbacus,
  setAbacusRow as setAbacusModelRow,
  type AddAbacusLayerInput,
  type LayeredAbacusState,
} from '../lib/layeredAbacus.ts';
import { generateAppRegistry } from './appRegistry.ts';
import { DEFAULT_THEME, DEFAULT_VIEWPORT, defaultDesktopIcons } from './defaultState.ts';

export type PollyPadAction =
  | 'snapshot'
  | 'listApps'
  | 'open'
  | 'close'
  | 'focus'
  | 'minimize'
  | 'maximize'
  | 'restore'
  | 'move'
  | 'resize'
  | 'setTitle'
  | 'setTheme'
  | 'setStartMenu'
  | 'notify'
  | 'abacusSetRow'
  | 'abacusAddLayer'
  | 'abacusReset';

export interface PollyPadInvokeArgs {
  windowId?: string;
  data?: unknown;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  title?: string;
  theme?: Theme;
  open?: boolean;
  notification?: Omit<Notification, 'id' | 'timestamp'>;
  rowId?: string;
  layerId?: string;
  label?: string;
  value?: number;
  count?: number;
  name?: string;
  rows?: AddAbacusLayerInput['rows'];
}

export interface PollyPadAppSnapshot {
  id: string;
  name: string;
  icon: string;
  category: string;
  defaultSize: AppDefinition['defaultSize'];
  minSize?: AppDefinition['minSize'];
  canResize: boolean;
  singleton: boolean;
  openCount: number;
}

export interface PollyPadSnapshot {
  activeWindowId: string | null;
  appCount: number;
  apps: PollyPadAppSnapshot[];
  desktopIcons: DesktopIcon[];
  notifications: Notification[];
  startMenuOpen: boolean;
  theme: Theme;
  viewport: { width: number; height: number };
  windows: WindowState[];
}

export interface PollyPadInvokeResult {
  action: PollyPadAction;
  appId: string;
  error?: string;
  ok: boolean;
  snapshot: PollyPadSnapshot;
  windowId?: string;
}

export interface PollyPadRuntimeOptions {
  now?: () => number;
  random?: () => number;
  viewport?: { width: number; height: number };
}

const SYSTEM_APP_ID = 'os';

export class PollyPadRuntime {
  private activeWindowId: string | null = null;
  private readonly appRegistry = generateAppRegistry();
  private readonly desktopIcons = defaultDesktopIcons.map((icon) => ({ ...icon }));
  private readonly now: () => number;
  private readonly random: () => number;
  private notifications: Notification[] = [];
  private sequence = 0;
  private startMenuOpen = false;
  private theme: Theme = DEFAULT_THEME;
  private viewport: { width: number; height: number };
  private windows: WindowState[] = [];
  private zIndexCounter = 100;

  constructor(options: PollyPadRuntimeOptions = {}) {
    this.now = options.now ?? (() => Date.now());
    this.random = options.random ?? Math.random;
    this.viewport = { ...(options.viewport ?? DEFAULT_VIEWPORT) };
  }

  invoke(
    appId: string,
    action: PollyPadAction,
    args: PollyPadInvokeArgs = {}
  ): PollyPadInvokeResult {
    const targetAppId = appId || SYSTEM_APP_ID;

    try {
      const windowId = this.dispatch(targetAppId, action, args);
      return {
        action,
        appId: targetAppId,
        ok: true,
        snapshot: this.snapshot(),
        windowId,
      };
    } catch (error) {
      return {
        action,
        appId: targetAppId,
        error: error instanceof Error ? error.message : String(error),
        ok: false,
        snapshot: this.snapshot(),
      };
    }
  }

  snapshot(): PollyPadSnapshot {
    const apps = Array.from(this.appRegistry.values())
      .map((app) => ({
        id: app.id,
        name: app.name,
        icon: app.icon,
        category: app.category,
        defaultSize: { ...app.defaultSize },
        minSize: app.minSize ? { ...app.minSize } : undefined,
        canResize: app.canResize ?? true,
        singleton: app.singleton ?? false,
        openCount: this.windows.filter((window) => window.appId === app.id).length,
      }))
      .sort((a, b) => a.name.localeCompare(b.name));

    return {
      activeWindowId: this.activeWindowId,
      appCount: this.appRegistry.size,
      apps,
      desktopIcons: this.desktopIcons.map((icon) => ({ ...icon })),
      notifications: this.notifications.map((notification) => ({ ...notification })),
      startMenuOpen: this.startMenuOpen,
      theme: this.theme,
      viewport: { ...this.viewport },
      windows: this.windows.map((window) => ({
        ...window,
        data: cloneData(window.data),
      })),
    };
  }

  private dispatch(
    appId: string,
    action: PollyPadAction,
    args: PollyPadInvokeArgs
  ): string | undefined {
    switch (action) {
      case 'snapshot':
      case 'listApps':
        return undefined;
      case 'open':
        return this.openApp(appId, args.data);
      case 'close':
        this.closeWindow(this.requireWindowId(appId, args.windowId));
        return undefined;
      case 'focus':
        return this.focusWindow(this.requireWindowId(appId, args.windowId));
      case 'minimize':
        this.minimizeWindow(this.requireWindowId(appId, args.windowId));
        return undefined;
      case 'maximize':
        return this.maximizeWindow(this.requireWindowId(appId, args.windowId));
      case 'restore':
        return this.restoreWindow(this.requireWindowId(appId, args.windowId));
      case 'move':
        return this.moveWindow(this.requireWindowId(appId, args.windowId), args);
      case 'resize':
        return this.resizeWindow(this.requireWindowId(appId, args.windowId), args);
      case 'setTitle':
        return this.setWindowTitle(this.requireWindowId(appId, args.windowId), args.title);
      case 'setTheme':
        this.setTheme(args.theme);
        return undefined;
      case 'setStartMenu':
        this.startMenuOpen = Boolean(args.open);
        return undefined;
      case 'notify':
        this.addNotification(args.notification);
        return undefined;
      case 'abacusSetRow':
        requireAppAction(appId, 'layeredabacus', action);
        return this.setAbacusRow(this.requireWindowId(appId, args.windowId), args);
      case 'abacusAddLayer':
        requireAppAction(appId, 'layeredabacus', action);
        return this.addAbacusLayer(this.requireWindowId(appId, args.windowId), args);
      case 'abacusReset':
        requireAppAction(appId, 'layeredabacus', action);
        return this.resetAbacusWindow(this.requireWindowId(appId, args.windowId));
      default:
        throw new Error(`Unsupported action: ${action satisfies never}`);
    }
  }

  private openApp(appId: string, data?: unknown): string {
    const app = this.appRegistry.get(appId);
    if (!app) {
      throw new Error(`Unknown app: ${appId}`);
    }

    if (app.singleton) {
      const existing = this.windows.find((window) => window.appId === appId && !window.isMinimized);
      if (existing) {
        return this.focusWindow(existing.id);
      }
    }

    const existingCount = this.windows.filter((window) => window.appId === appId).length;
    const title = existingCount > 0 ? `${app.name} (${existingCount + 1})` : app.name;
    const offsetX = (this.windows.length % 5) * 30;
    const offsetY = (this.windows.length % 5) * 30;
    const centerX = Math.max(50, (this.viewport.width - app.defaultSize.width) / 2 + offsetX);
    const centerY = Math.max(
      30,
      (this.viewport.height - app.defaultSize.height - 50) / 2 + offsetY
    );
    const width = app.defaultSize.width;
    const height = app.defaultSize.height;
    const idSuffix = Math.floor(this.random() * 1_000_000).toString(36);
    const windowId = `win_${++this.sequence}_${appId}_${idSuffix}`;

    const nextWindow: WindowState = {
      id: windowId,
      appId,
      title,
      x: Math.min(centerX, this.viewport.width - width - 20),
      y: Math.min(centerY, this.viewport.height - height - 80),
      width,
      height,
      isMinimized: false,
      isMaximized: false,
      isFocused: true,
      zIndex: ++this.zIndexCounter,
      data: hydrateAppData(appId, data),
    };

    this.windows = [...this.windows.map((window) => ({ ...window, isFocused: false })), nextWindow];
    this.activeWindowId = windowId;
    this.startMenuOpen = false;
    return windowId;
  }

  private closeWindow(windowId: string): void {
    this.windows = this.windows.filter((window) => window.id !== windowId);
    const visible = this.windows.filter((window) => !window.isMinimized);
    const top = visible.sort((a, b) => b.zIndex - a.zIndex)[0];
    this.activeWindowId = top?.id ?? null;
    this.windows = this.windows.map((window) => ({
      ...window,
      isFocused: window.id === this.activeWindowId,
    }));
  }

  private focusWindow(windowId: string): string {
    this.requireWindow(windowId);
    this.activeWindowId = windowId;
    this.windows = this.windows.map((window) => ({
      ...window,
      isFocused: window.id === windowId,
      isMinimized: window.id === windowId ? false : window.isMinimized,
      zIndex: window.id === windowId ? ++this.zIndexCounter : window.zIndex,
    }));
    return windowId;
  }

  private minimizeWindow(windowId: string): void {
    this.requireWindow(windowId);
    this.windows = this.windows.map((window) =>
      window.id === windowId ? { ...window, isMinimized: true, isFocused: false } : window
    );
    const visible = this.windows
      .filter((window) => !window.isMinimized)
      .sort((a, b) => b.zIndex - a.zIndex);
    this.activeWindowId = visible[0]?.id ?? null;
    this.windows = this.windows.map((window) => ({
      ...window,
      isFocused: window.id === this.activeWindowId,
    }));
  }

  private maximizeWindow(windowId: string): string {
    this.requireWindow(windowId);
    this.windows = this.windows.map((window) =>
      window.id === windowId
        ? {
            ...window,
            isMaximized: true,
            x: 0,
            y: 0,
            width: this.viewport.width,
            height: this.viewport.height - 48,
          }
        : window
    );
    return this.focusWindow(windowId);
  }

  private restoreWindow(windowId: string): string {
    const window = this.requireWindow(windowId);
    const app = this.appRegistry.get(window.appId);
    if (!app) {
      throw new Error(`Unknown app for window: ${window.appId}`);
    }

    this.windows = this.windows.map((candidate) =>
      candidate.id === windowId
        ? {
            ...candidate,
            isMaximized: false,
            width: app.defaultSize.width,
            height: app.defaultSize.height,
            x: Math.max(50, (this.viewport.width - app.defaultSize.width) / 2),
            y: Math.max(30, (this.viewport.height - app.defaultSize.height - 50) / 2),
          }
        : candidate
    );
    return this.focusWindow(windowId);
  }

  private moveWindow(windowId: string, args: PollyPadInvokeArgs): string {
    const x = requireNumber(args.x, 'x');
    const y = requireNumber(args.y, 'y');
    this.requireWindow(windowId);
    this.windows = this.windows.map((window) =>
      window.id === windowId ? { ...window, x, y } : window
    );
    return this.focusWindow(windowId);
  }

  private resizeWindow(windowId: string, args: PollyPadInvokeArgs): string {
    const width = requireNumber(args.width, 'width');
    const height = requireNumber(args.height, 'height');
    const window = this.requireWindow(windowId);
    const app = this.appRegistry.get(window.appId);
    const minWidth = app?.minSize?.width ?? 200;
    const minHeight = app?.minSize?.height ?? 120;

    this.windows = this.windows.map((candidate) =>
      candidate.id === windowId
        ? {
            ...candidate,
            width: Math.max(width, minWidth),
            height: Math.max(height, minHeight),
          }
        : candidate
    );
    return this.focusWindow(windowId);
  }

  private setWindowTitle(windowId: string, title?: string): string {
    if (!title) {
      throw new Error('setTitle requires args.title');
    }
    this.requireWindow(windowId);
    this.windows = this.windows.map((window) =>
      window.id === windowId ? { ...window, title } : window
    );
    return this.focusWindow(windowId);
  }

  private setTheme(theme?: Theme): void {
    if (!theme) {
      throw new Error('setTheme requires args.theme');
    }
    this.theme = theme;
  }

  private addNotification(notification?: Omit<Notification, 'id' | 'timestamp'>): void {
    if (!notification) {
      throw new Error('notify requires args.notification');
    }
    this.notifications = [
      ...this.notifications.slice(-9),
      {
        ...notification,
        id: `notif_${++this.sequence}`,
        timestamp: this.now(),
      },
    ];
  }

  private setAbacusRow(windowId: string, args: PollyPadInvokeArgs): string {
    const rowId = requireString(args.rowId, 'rowId');
    const window = this.requireWindow(windowId);
    const state = readAbacusState(window.data);
    const nextState = setAbacusModelRow(state, {
      count: args.count,
      label: args.label,
      layerId: args.layerId,
      rowId,
      value: args.value,
    });

    this.setWindowData(windowId, createAbacusWindowData(asRecord(window.data), nextState));
    return this.focusWindow(windowId);
  }

  private addAbacusLayer(windowId: string, args: PollyPadInvokeArgs): string {
    const window = this.requireWindow(windowId);
    const state = readAbacusState(window.data);
    const nextState = addAbacusLayer(state, {
      layerId: args.layerId,
      name: args.name,
      rows: args.rows,
    });

    this.setWindowData(windowId, createAbacusWindowData(asRecord(window.data), nextState));
    return this.focusWindow(windowId);
  }

  private resetAbacusWindow(windowId: string): string {
    const window = this.requireWindow(windowId);
    this.setWindowData(windowId, createAbacusWindowData(asRecord(window.data), resetAbacus()));
    return this.focusWindow(windowId);
  }

  private setWindowData(windowId: string, data: unknown): void {
    this.requireWindow(windowId);
    this.windows = this.windows.map((window) =>
      window.id === windowId ? { ...window, data } : window
    );
  }

  private requireWindowId(appId: string, requestedWindowId?: string): string {
    if (requestedWindowId) {
      this.requireWindow(requestedWindowId);
      return requestedWindowId;
    }

    if (appId !== SYSTEM_APP_ID) {
      const appWindow = this.windows
        .filter((window) => window.appId === appId)
        .sort((a, b) => b.zIndex - a.zIndex)[0];
      if (appWindow) {
        return appWindow.id;
      }
    }

    if (!this.activeWindowId) {
      throw new Error('No active window');
    }
    this.requireWindow(this.activeWindowId);
    return this.activeWindowId;
  }

  private requireWindow(windowId: string): WindowState {
    const window = this.windows.find((candidate) => candidate.id === windowId);
    if (!window) {
      throw new Error(`Unknown window: ${windowId}`);
    }
    return window;
  }
}

export function createPollyPadRuntime(options?: PollyPadRuntimeOptions): PollyPadRuntime {
  return new PollyPadRuntime(options);
}

function requireNumber(value: unknown, name: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(`${name} must be a finite number`);
  }
  return value;
}

function requireString(value: unknown, name: string): string {
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`${name} must be a non-empty string`);
  }
  return value;
}

function requireAppAction(appId: string, expectedAppId: string, action: PollyPadAction): void {
  if (appId !== expectedAppId) {
    throw new Error(`${action} is only supported by ${expectedAppId}`);
  }
}

function hydrateAppData(appId: string, data: unknown): unknown {
  if (appId !== 'layeredabacus') {
    return cloneData(data);
  }

  return createAbacusWindowData(asRecord(data), readAbacusState(data));
}

function createAbacusWindowData(
  base: Record<string, unknown>,
  state = resetAbacus()
): Record<string, unknown> {
  return {
    ...cloneData(base),
    abacus: state,
    totals: calculateAbacusTotals(state),
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function readAbacusState(value: unknown): LayeredAbacusState {
  return normalizeAbacusState(asRecord(value).abacus as Partial<LayeredAbacusState> | undefined);
}

function cloneData<T>(value: T): T {
  if (value === undefined || value === null) {
    return value;
  }
  return JSON.parse(JSON.stringify(value)) as T;
}

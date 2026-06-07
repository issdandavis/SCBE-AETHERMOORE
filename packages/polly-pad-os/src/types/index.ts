export interface AppDefinition {
  id: string;
  name: string;
  icon: string;
  category: string;
  component: React.ComponentType<any>;
  defaultSize: { width: number; height: number };
  minSize?: { width: number; height: number };
  canResize?: boolean;
  singleton?: boolean;
}

export interface WindowState {
  id: string;
  appId: string;
  title: string;
  x: number;
  y: number;
  width: number;
  height: number;
  isMinimized: boolean;
  isMaximized: boolean;
  isFocused: boolean;
  zIndex: number;
  data?: any;
}

export interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'directory';
  parentId: string | null;
  content?: string;
  createdAt: number;
  modifiedAt: number;
  size?: number;
  mimeType?: string;
}

export interface DesktopIcon {
  id: string;
  appId: string;
  name: string;
  icon: string;
  x: number;
  y: number;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  timestamp: number;
}

export interface TaskbarItem {
  windowId: string;
  appId: string;
  title: string;
  icon: string;
  isFocused: boolean;
  isMinimized: boolean;
}

export type Theme = 'dark' | 'light' | 'blue' | 'purple' | 'green';

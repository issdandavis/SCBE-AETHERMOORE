import type { DesktopIcon, Theme } from '../types/index.ts';

export const DEFAULT_VIEWPORT = {
  width: 1440,
  height: 900,
};

export const DEFAULT_THEME: Theme = 'dark';

export const defaultDesktopIcons: DesktopIcon[] = [
  { id: 'd1', appId: 'files', name: 'Files', icon: 'FolderOpen', x: 20, y: 20 },
  { id: 'd2', appId: 'terminal', name: 'Terminal', icon: 'Terminal', x: 20, y: 110 },
  { id: 'd3', appId: 'texteditor', name: 'Text Editor', icon: 'FileText', x: 20, y: 200 },
  { id: 'd4', appId: 'browser', name: 'Internet', icon: 'Globe', x: 20, y: 290 },
  { id: 'd5', appId: 'calculator', name: 'Calculator', icon: 'Calculator', x: 20, y: 380 },
  { id: 'd6', appId: 'settings', name: 'Settings', icon: 'Settings', x: 20, y: 470 },
];

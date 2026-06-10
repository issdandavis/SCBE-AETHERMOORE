import type { DesktopIcon, Theme } from '../types/index.ts';

export const DEFAULT_VIEWPORT = {
  width: 1440,
  height: 900,
};

export const DEFAULT_THEME: Theme = 'dark';

export const defaultDesktopIcons: DesktopIcon[] = [
  { id: 'd1', appId: 'terminal', name: 'PowerShell', icon: 'Terminal', x: 20, y: 20 },
  { id: 'd2', appId: 'multiagent', name: 'Tool Console', icon: 'Bot', x: 20, y: 110 },
  { id: 'd3', appId: 'browser', name: 'Internet', icon: 'Globe', x: 20, y: 200 },
  { id: 'd4', appId: 'layeredabacus', name: 'Abacus', icon: 'Sigma', x: 20, y: 290 },
];

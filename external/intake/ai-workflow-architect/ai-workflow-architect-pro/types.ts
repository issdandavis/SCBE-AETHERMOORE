
export interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'idle' | 'running' | 'error' | 'offline';
  capabilities: string[];
  lastActive: string;
}

export interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: { label: string; agentId?: string; config?: any };
}

export interface FigmaExportConfig {
  fileKey: string;
  pageName: string;
  frameName: string;
  includeComments: boolean;
  scale: number;
}

export interface UserPreferences {
  theme: 'dark' | 'light';
  voiceEnabled: boolean;
  notifications: boolean;
  figmaConnected: boolean;
  figmaToken?: string;
}

export interface AnalyticsData {
  name: string;
  executions: number;
  tokens: number;
  cost: number;
}

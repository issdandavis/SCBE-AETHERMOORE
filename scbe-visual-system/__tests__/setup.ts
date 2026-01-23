import { vi } from 'vitest';

// Mock window.scbeElectron for tests
Object.defineProperty(window, 'scbeElectron', {
  value: {
    getSystemInfo: vi.fn().mockResolvedValue({ platform: 'test' }),
    getSecurityStatus: vi.fn().mockResolvedValue({ secure: true }),
    license: {
      getStatus: vi.fn().mockResolvedValue({
        valid: true,
        plan: 'free',
        planInfo: {
          name: 'Free Trial',
          maxRequestsPerDay: 10,
          features: ['basic'],
          canAccessFleet: false,
          canAccessAgents: false,
          canAccessAdvancedAnalytics: false,
          canAccessWebhooks: false
        }
      }),
      activate: vi.fn(),
      login: vi.fn(),
      logout: vi.fn(),
      hasFeature: vi.fn(),
      canAccess: vi.fn(),
      getPlans: vi.fn(),
      openUpgrade: vi.fn(),
      onStatusChange: vi.fn()
    },
    onOpenApp: vi.fn(),
    onSecurityScan: vi.fn(),
    onPQCStatus: vi.fn(),
    onAuditLogs: vi.fn(),
    onFleetSync: vi.fn(),
    platform: 'test',
    isElectron: false
  },
  writable: true
});

// Mock process.env
process.env.API_KEY = 'test-api-key';
process.env.GEMINI_API_KEY = 'test-gemini-key';
process.env.SCBE_VERSION = '3.0.0';

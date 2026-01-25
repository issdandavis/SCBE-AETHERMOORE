import { describe, it, expect } from 'vitest';
import type {
  AppId,
  DesktopItem,
  Point,
  Stroke,
  Email,
  ToolAction,
  PlanInfo,
  LicenseStatus
} from '../types';

// ========== TYPE VALIDATION TESTS ==========
// These tests verify type contracts are respected at runtime

describe('AppId type', () => {
  it('accepts valid app IDs', () => {
    const validIds: AppId[] = [
      'home', 'mail', 'slides', 'snake', 'folder', 'notepad',
      'automator', 'code', 'sudoku', 'wordle', 'security',
      'cryptolab', 'defense', 'agents', 'fleet', 'knowledge', 'pollypad'
    ];

    validIds.forEach(id => {
      expect(typeof id).toBe('string');
    });
  });

  it('has 17 valid app types', () => {
    const appIds: AppId[] = [
      'home', 'mail', 'slides', 'snake', 'folder', 'notepad',
      'automator', 'code', 'sudoku', 'wordle', 'security',
      'cryptolab', 'defense', 'agents', 'fleet', 'knowledge', 'pollypad'
    ];
    expect(appIds.length).toBe(17);
  });
});

describe('DesktopItem interface', () => {
  it('creates valid desktop item with required fields', () => {
    const item: DesktopItem = {
      id: 'test-id',
      name: 'Test App',
      type: 'app',
      icon: {} as any // Mock LucideIcon
    };

    expect(item.id).toBe('test-id');
    expect(item.name).toBe('Test App');
    expect(item.type).toBe('app');
    expect(item.icon).toBeDefined();
  });

  it('supports folder type with contents', () => {
    const folder: DesktopItem = {
      id: 'folder-1',
      name: 'My Folder',
      type: 'folder',
      icon: {} as any,
      contents: [
        { id: 'nested-1', name: 'Nested', type: 'app', icon: {} as any }
      ]
    };

    expect(folder.type).toBe('folder');
    expect(folder.contents?.length).toBe(1);
  });

  it('supports optional appId', () => {
    const item: DesktopItem = {
      id: 'mail-app',
      name: 'Mail',
      type: 'app',
      icon: {} as any,
      appId: 'mail'
    };

    expect(item.appId).toBe('mail');
  });

  it('supports optional bgColor', () => {
    const item: DesktopItem = {
      id: 'colorful',
      name: 'Colorful App',
      type: 'app',
      icon: {} as any,
      bgColor: 'emerald-600'
    };

    expect(item.bgColor).toBe('emerald-600');
  });

  it('supports optional notepadInitialContent', () => {
    const item: DesktopItem = {
      id: 'notepad-1',
      name: 'Notes',
      type: 'app',
      icon: {} as any,
      appId: 'notepad',
      notepadInitialContent: 'Hello, World!'
    };

    expect(item.notepadInitialContent).toBe('Hello, World!');
  });
});

describe('Point interface', () => {
  it('creates valid point with x and y', () => {
    const point: Point = { x: 100, y: 200 };

    expect(point.x).toBe(100);
    expect(point.y).toBe(200);
  });

  it('supports negative coordinates', () => {
    const point: Point = { x: -50, y: -100 };

    expect(point.x).toBe(-50);
    expect(point.y).toBe(-100);
  });

  it('supports decimal coordinates', () => {
    const point: Point = { x: 10.5, y: 20.75 };

    expect(point.x).toBe(10.5);
    expect(point.y).toBe(20.75);
  });
});

describe('Stroke type', () => {
  it('is an array of points', () => {
    const stroke: Stroke = [
      { x: 0, y: 0 },
      { x: 10, y: 10 },
      { x: 20, y: 5 }
    ];

    expect(Array.isArray(stroke)).toBe(true);
    expect(stroke.length).toBe(3);
    stroke.forEach(point => {
      expect(point).toHaveProperty('x');
      expect(point).toHaveProperty('y');
    });
  });

  it('can be empty', () => {
    const stroke: Stroke = [];
    expect(stroke.length).toBe(0);
  });
});

describe('Email interface', () => {
  it('creates valid email with all fields', () => {
    const email: Email = {
      id: 1,
      from: 'sender@example.com',
      subject: 'Test Subject',
      preview: 'This is a preview...',
      body: 'Full email body content here.',
      time: '10:30 AM',
      unread: true
    };

    expect(email.id).toBe(1);
    expect(email.from).toBe('sender@example.com');
    expect(email.subject).toBe('Test Subject');
    expect(email.preview).toBe('This is a preview...');
    expect(email.body).toBe('Full email body content here.');
    expect(email.time).toBe('10:30 AM');
    expect(email.unread).toBe(true);
  });

  it('supports read emails (unread: false)', () => {
    const email: Email = {
      id: 2,
      from: 'other@example.com',
      subject: 'Read Email',
      preview: 'Preview',
      body: 'Body',
      time: '9:00 AM',
      unread: false
    };

    expect(email.unread).toBe(false);
  });
});

describe('ToolAction type', () => {
  it('supports DELETE_ITEM action', () => {
    const action: ToolAction = { type: 'DELETE_ITEM', itemId: 'item-123' };

    expect(action.type).toBe('DELETE_ITEM');
    if (action.type === 'DELETE_ITEM') {
      expect(action.itemId).toBe('item-123');
    }
  });

  it('supports EXPLODE_FOLDER action', () => {
    const action: ToolAction = { type: 'EXPLODE_FOLDER', folderId: 'folder-456' };

    expect(action.type).toBe('EXPLODE_FOLDER');
    if (action.type === 'EXPLODE_FOLDER') {
      expect(action.folderId).toBe('folder-456');
    }
  });

  it('supports EXPLAIN_ITEM action', () => {
    const action: ToolAction = { type: 'EXPLAIN_ITEM', itemId: 'item-789' };

    expect(action.type).toBe('EXPLAIN_ITEM');
    if (action.type === 'EXPLAIN_ITEM') {
      expect(action.itemId).toBe('item-789');
    }
  });

  it('supports NONE action', () => {
    const action: ToolAction = { type: 'NONE' };

    expect(action.type).toBe('NONE');
  });
});

describe('PlanInfo interface', () => {
  it('creates valid plan info', () => {
    const plan: PlanInfo = {
      name: 'Professional',
      maxRequestsPerDay: 1000,
      features: ['feature1', 'feature2'],
      canAccessFleet: true,
      canAccessAgents: true,
      canAccessAdvancedAnalytics: true,
      canAccessWebhooks: true
    };

    expect(plan.name).toBe('Professional');
    expect(plan.maxRequestsPerDay).toBe(1000);
    expect(plan.features).toEqual(['feature1', 'feature2']);
    expect(plan.canAccessFleet).toBe(true);
    expect(plan.canAccessAgents).toBe(true);
    expect(plan.canAccessAdvancedAnalytics).toBe(true);
    expect(plan.canAccessWebhooks).toBe(true);
  });

  it('supports free tier with limited access', () => {
    const plan: PlanInfo = {
      name: 'Free Trial',
      maxRequestsPerDay: 10,
      features: ['basic'],
      canAccessFleet: false,
      canAccessAgents: false,
      canAccessAdvancedAnalytics: false,
      canAccessWebhooks: false
    };

    expect(plan.canAccessFleet).toBe(false);
    expect(plan.canAccessAgents).toBe(false);
  });
});

describe('LicenseStatus interface', () => {
  it('creates valid free license status', () => {
    const status: LicenseStatus = {
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
    };

    expect(status.valid).toBe(true);
    expect(status.plan).toBe('free');
    expect(status.planInfo.name).toBe('Free Trial');
  });

  it('supports all plan types', () => {
    const plans: LicenseStatus['plan'][] = ['free', 'starter', 'professional', 'enterprise'];

    plans.forEach(plan => {
      const status: LicenseStatus = {
        valid: true,
        plan,
        planInfo: {} as PlanInfo
      };
      expect(status.plan).toBe(plan);
    });
  });

  it('supports optional email field', () => {
    const status: LicenseStatus = {
      valid: true,
      plan: 'professional',
      planInfo: {} as PlanInfo,
      email: 'user@company.com'
    };

    expect(status.email).toBe('user@company.com');
  });

  it('supports optional validUntil field', () => {
    const status: LicenseStatus = {
      valid: true,
      plan: 'enterprise',
      planInfo: {} as PlanInfo,
      validUntil: '2026-12-31'
    };

    expect(status.validUntil).toBe('2026-12-31');
  });

  it('supports offline mode fields', () => {
    const status: LicenseStatus = {
      valid: true,
      plan: 'professional',
      planInfo: {} as PlanInfo,
      offline: true,
      offlineWarning: 'Operating in offline mode'
    };

    expect(status.offline).toBe(true);
    expect(status.offlineWarning).toBe('Operating in offline mode');
  });

  it('supports message field for errors', () => {
    const status: LicenseStatus = {
      valid: false,
      plan: 'free',
      planInfo: {} as PlanInfo,
      message: 'License expired'
    };

    expect(status.valid).toBe(false);
    expect(status.message).toBe('License expired');
  });
});

// ========== MATHEMATICAL TESTS ==========

describe('Point calculations', () => {
  it('calculates distance between two points', () => {
    const p1: Point = { x: 0, y: 0 };
    const p2: Point = { x: 3, y: 4 };

    const distance = Math.sqrt(
      Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2)
    );

    expect(distance).toBe(5); // 3-4-5 triangle
  });

  it('calculates midpoint between two points', () => {
    const p1: Point = { x: 0, y: 0 };
    const p2: Point = { x: 10, y: 20 };

    const midpoint: Point = {
      x: (p1.x + p2.x) / 2,
      y: (p1.y + p2.y) / 2
    };

    expect(midpoint.x).toBe(5);
    expect(midpoint.y).toBe(10);
  });

  it('calculates stroke length (sum of segments)', () => {
    const stroke: Stroke = [
      { x: 0, y: 0 },
      { x: 3, y: 4 },  // 5 units from start
      { x: 3, y: 9 }   // 5 units from previous
    ];

    let length = 0;
    for (let i = 1; i < stroke.length; i++) {
      length += Math.sqrt(
        Math.pow(stroke[i].x - stroke[i - 1].x, 2) +
        Math.pow(stroke[i].y - stroke[i - 1].y, 2)
      );
    }

    expect(length).toBe(10);
  });

  it('calculates bounding box of stroke', () => {
    const stroke: Stroke = [
      { x: 5, y: 10 },
      { x: 15, y: 5 },
      { x: 10, y: 20 },
      { x: 3, y: 8 }
    ];

    const minX = Math.min(...stroke.map(p => p.x));
    const maxX = Math.max(...stroke.map(p => p.x));
    const minY = Math.min(...stroke.map(p => p.y));
    const maxY = Math.max(...stroke.map(p => p.y));

    expect(minX).toBe(3);
    expect(maxX).toBe(15);
    expect(minY).toBe(5);
    expect(maxY).toBe(20);

    const width = maxX - minX;
    const height = maxY - minY;

    expect(width).toBe(12);
    expect(height).toBe(15);
  });

  it('calculates centroid of stroke', () => {
    const stroke: Stroke = [
      { x: 0, y: 0 },
      { x: 10, y: 0 },
      { x: 10, y: 10 },
      { x: 0, y: 10 }
    ];

    const centroid: Point = {
      x: stroke.reduce((sum, p) => sum + p.x, 0) / stroke.length,
      y: stroke.reduce((sum, p) => sum + p.y, 0) / stroke.length
    };

    expect(centroid.x).toBe(5);
    expect(centroid.y).toBe(5);
  });
});

describe('Email data validation', () => {
  it('validates email ID is positive integer', () => {
    const email: Email = {
      id: 42,
      from: 'test@test.com',
      subject: 'Test',
      preview: '',
      body: '',
      time: '',
      unread: false
    };

    expect(Number.isInteger(email.id)).toBe(true);
    expect(email.id).toBeGreaterThan(0);
  });

  it('preview should be shorter than body', () => {
    const email: Email = {
      id: 1,
      from: 'test@test.com',
      subject: 'Test',
      preview: 'Short preview...',
      body: 'This is the full email body with much more content than the preview would show.',
      time: '12:00 PM',
      unread: true
    };

    expect(email.preview.length).toBeLessThan(email.body.length);
  });
});

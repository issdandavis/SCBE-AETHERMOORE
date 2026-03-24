/**
 * @file basin.ts
 * @module browser/basin
 * @layer Layer 13-14 (Risk Decision + Telemetry)
 * @component Basin — Central data lake where all rivers converge
 *
 * All storage rivers (Dropbox, OneDrive, Google Drive, Proton Mail, local FS)
 * flow into one governed basin. The browser controls the flow.
 *
 * Rivers:
 *   Dropbox   -> C:/Users/issda/Dropbox
 *   OneDrive  -> C:/Users/issda/OneDrive
 *   Google Drive -> C:/Users/issda/Drive (mounted path)
 *   Local FS  -> C:/Users/issda/SCBE-AETHERMOORE
 *   Proton Mail -> IMAP bridge (127.0.0.1:1143 when running)
 *
 * Basin:
 *   C:/Users/issda/SCBE-AETHERMOORE/training/intake  (processing)
 *   C:/Users/issda/Dropbox/SCBE                      (backup/sync)
 */

import * as fs from 'fs';
import * as path from 'path';

// ---------------------------------------------------------------------------
// River definitions — all your storage sources
// ---------------------------------------------------------------------------

export interface River {
  id: string;
  name: string;
  localPath: string;
  type: 'filesystem' | 'email' | 'api';
  status: 'connected' | 'disconnected' | 'unknown';
  syncDirection: 'inbound' | 'outbound' | 'bidirectional';
  policy?: RiverPolicy;
}

export interface RiverPolicy {
  readFromRiver: boolean;
  writeToRiver: boolean;
  allowedCategories: string[]; // Use ['*'] for unrestricted categories
  requireExplicitCategory: boolean;
}

export const RIVERS: River[] = [
  {
    id: 'dropbox',
    name: 'Dropbox',
    localPath: 'C:/Users/issda/Dropbox',
    type: 'filesystem',
    status: 'unknown',
    syncDirection: 'bidirectional',
    policy: {
      readFromRiver: true,
      writeToRiver: true,
      allowedCategories: ['research', 'content', 'products', 'assets', 'ops', 'archive', 'sync'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'onedrive',
    name: 'OneDrive',
    localPath: 'C:/Users/issda/OneDrive',
    type: 'filesystem',
    status: 'unknown',
    syncDirection: 'bidirectional',
    policy: {
      readFromRiver: true,
      writeToRiver: true,
      allowedCategories: ['research', 'content', 'products', 'assets', 'ops', 'archive', 'sync'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'googledrive',
    name: 'Google Drive',
    localPath: 'C:/Users/issda/Drive',
    type: 'filesystem',
    status: 'unknown',
    syncDirection: 'bidirectional',
    policy: {
      readFromRiver: true,
      writeToRiver: true,
      allowedCategories: ['research', 'content', 'products', 'assets', 'ops', 'archive', 'sync'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'googledrive-scbe',
    name: 'Google Drive / SCBE',
    localPath: 'C:/Users/issda/Drive/SCBE',
    type: 'filesystem',
    status: 'unknown',
    syncDirection: 'bidirectional',
    policy: {
      readFromRiver: true,
      writeToRiver: true,
      allowedCategories: ['research', 'content', 'products', 'assets', 'ops', 'archive', 'sync'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'googledrive-downloads',
    name: 'Google Drive / Downloads',
    localPath: 'C:/Users/issda/Drive/Downloads',
    type: 'filesystem',
    status: 'unknown',
    syncDirection: 'inbound',
    policy: {
      readFromRiver: true,
      writeToRiver: false,
      allowedCategories: ['downloads', 'intake', 'assets'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'googledrive-pictures',
    name: 'Google Drive / Pictures',
    localPath: 'C:/Users/issda/Drive/Pictures',
    type: 'filesystem',
    status: 'unknown',
    syncDirection: 'inbound',
    policy: {
      readFromRiver: true,
      writeToRiver: false,
      allowedCategories: ['images', 'assets', 'content'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'local-scbe',
    name: 'SCBE-AETHERMOORE',
    localPath: 'C:/Users/issda/SCBE-AETHERMOORE',
    type: 'filesystem',
    status: 'connected',
    syncDirection: 'bidirectional',
    policy: {
      readFromRiver: true,
      writeToRiver: true,
      allowedCategories: ['*'],
      requireExplicitCategory: false,
    },
  },
  {
    id: 'local-ai-hub',
    name: 'AI Evolution Hub',
    localPath: 'C:/Users/issda/AI_EVOLUTION_HUB',
    type: 'filesystem',
    status: 'unknown',
    syncDirection: 'inbound',
    policy: {
      readFromRiver: true,
      writeToRiver: false,
      allowedCategories: ['research', 'models', 'training', 'intake'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'dropbox-brain',
    name: 'Dropbox Brain',
    localPath: 'C:/Users/issda/dropbox_brain',
    type: 'filesystem',
    status: 'unknown',
    syncDirection: 'inbound',
    policy: {
      readFromRiver: true,
      writeToRiver: false,
      allowedCategories: ['brain', 'research', 'notes', 'archive'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'github-api',
    name: 'GitHub API',
    localPath: 'https://api.github.com',
    type: 'api',
    status: 'unknown',
    syncDirection: 'bidirectional',
    policy: {
      readFromRiver: true,
      writeToRiver: true,
      allowedCategories: ['code', 'issues', 'prs', 'release', 'ops'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'github-codespaces-api',
    name: 'GitHub Codespaces API',
    localPath: 'https://api.github.com/user/codespaces',
    type: 'api',
    status: 'unknown',
    syncDirection: 'bidirectional',
    policy: {
      readFromRiver: true,
      writeToRiver: true,
      allowedCategories: ['devenv', 'codespaces', 'code', 'ops'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'gamma-mcp',
    name: 'Gamma MCP',
    localPath: 'https://gamma.app',
    type: 'api',
    status: 'unknown',
    syncDirection: 'inbound',
    policy: {
      readFromRiver: true,
      writeToRiver: false,
      allowedCategories: ['slides', 'marketing', 'content', 'landing_pages', 'funnel'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'huggingface-api',
    name: 'Hugging Face API',
    localPath: 'https://huggingface.co',
    type: 'api',
    status: 'unknown',
    syncDirection: 'bidirectional',
    policy: {
      readFromRiver: true,
      writeToRiver: true,
      allowedCategories: ['datasets', 'models', 'training', 'research'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'firebase-hosting',
    name: 'Firebase Hosting',
    localPath: 'https://firebase.google.com',
    type: 'api',
    status: 'unknown',
    syncDirection: 'outbound',
    policy: {
      readFromRiver: false,
      writeToRiver: true,
      allowedCategories: ['deploy', 'hosting', 'ops'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'zapier-webhooks',
    name: 'Zapier Webhooks',
    localPath: 'https://hooks.zapier.com',
    type: 'api',
    status: 'unknown',
    syncDirection: 'outbound',
    policy: {
      readFromRiver: false,
      writeToRiver: true,
      allowedCategories: ['automation', 'posting', 'ops'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'n8n-local',
    name: 'n8n Local',
    localPath: 'http://127.0.0.1:5680',
    type: 'api',
    status: 'unknown',
    syncDirection: 'bidirectional',
    policy: {
      readFromRiver: true,
      writeToRiver: true,
      allowedCategories: ['automation', 'posting', 'ops', 'research'],
      requireExplicitCategory: true,
    },
  },
  {
    id: 'protonmail',
    name: 'Proton Mail (Bridge)',
    localPath: '127.0.0.1:1143',
    type: 'email',
    status: 'unknown',
    syncDirection: 'inbound',
    policy: {
      readFromRiver: true,
      writeToRiver: false,
      allowedCategories: ['inbox', 'research', 'ops'],
      requireExplicitCategory: true,
    },
  },
];

// ---------------------------------------------------------------------------
// Basin — the center island where all rivers converge
// ---------------------------------------------------------------------------

export interface BasinConfig {
  intakePath: string; // where incoming data lands for processing
  backupPath: string; // where processed data gets backed up
  archivePath: string; // long-term storage
}

const DEFAULT_BASIN: BasinConfig = {
  intakePath: 'C:/Users/issda/SCBE-AETHERMOORE/training/intake',
  backupPath: 'C:/Users/issda/Dropbox/SCBE',
  archivePath: 'C:/Users/issda/Dropbox/Backups',
};

export class Basin {
  private config: BasinConfig;
  private rivers: Map<string, River>;

  constructor(config: BasinConfig = DEFAULT_BASIN) {
    this.config = config;
    this.rivers = new Map(RIVERS.map((r) => [r.id, r]));
  }

  private normalizeCategory(category: string): string {
    return category.trim().toLowerCase();
  }

  private resolvePolicy(river: River): RiverPolicy {
    if (river.policy) {
      return river.policy;
    }
    return {
      readFromRiver: river.type !== 'api',
      writeToRiver: river.type !== 'api' && river.syncDirection !== 'inbound',
      allowedCategories: ['*'],
      requireExplicitCategory: false,
    };
  }

  private assertCategoryAllowed(river: River, category: string): void {
    const policy = this.resolvePolicy(river);
    const normalized = this.normalizeCategory(category);
    if (policy.requireExplicitCategory && normalized.length === 0) {
      throw new Error(`Category is required for river ${river.id}`);
    }
    if (policy.allowedCategories.includes('*')) {
      return;
    }
    if (!policy.allowedCategories.map((c) => c.toLowerCase()).includes(normalized)) {
      throw new Error(
        `Category '${category}' is not allowed for river ${river.id}. Allowed: ${policy.allowedCategories.join(', ')}`
      );
    }
  }

  private assertRiverAccess(river: River, mode: 'read' | 'write'): void {
    const policy = this.resolvePolicy(river);
    if (mode === 'read' && !policy.readFromRiver) {
      throw new Error(`Read access denied for river ${river.id}`);
    }
    if (mode === 'write' && !policy.writeToRiver) {
      throw new Error(`Write access denied for river ${river.id}`);
    }
  }

  /**
   * Probe all rivers and update their connection status.
   */
  probeRivers(): River[] {
    for (const river of Array.from(this.rivers.values())) {
      if (river.type === 'filesystem') {
        river.status = fs.existsSync(river.localPath) ? 'connected' : 'disconnected';
      } else if (river.type === 'email') {
        // Proton Bridge check would go here
        river.status = 'unknown';
      }
    }
    return Array.from(this.rivers.values());
  }

  /**
   * Guard against path traversal (../) in user-supplied path segments.
   */
  private assertNoTraversal(value: string, label: string): void {
    const normalized = path.normalize(value);
    if (
      normalized.startsWith('..') ||
      normalized.includes(`..${path.sep}`) ||
      path.isAbsolute(normalized)
    ) {
      throw new Error(`Path traversal detected in ${label}: ${value}`);
    }
  }

  /**
   * Deposit data into the basin from a river.
   * Creates the directory structure: intake/{riverId}/{category}/
   */
  deposit(riverId: string, category: string, filename: string, data: string | Buffer): string {
    const river = this.rivers.get(riverId);
    if (!river) throw new Error(`Unknown river: ${riverId}`);
    this.assertNoTraversal(category, 'category');
    this.assertNoTraversal(filename, 'filename');
    this.assertCategoryAllowed(river, category);

    const depositDir = path.join(this.config.intakePath, riverId, category);
    fs.mkdirSync(depositDir, { recursive: true });

    const fullPath = path.join(depositDir, filename);
    fs.writeFileSync(fullPath, data);

    // Mirror to backup if river supports it
    if (river.syncDirection === 'bidirectional') {
      const backupDir = path.join(this.config.backupPath, riverId, category);
      fs.mkdirSync(backupDir, { recursive: true });
      fs.writeFileSync(path.join(backupDir, filename), data);
    }

    return fullPath;
  }

  /**
   * Pull data from a river into the basin.
   * Scans a directory in the river and copies files to intake.
   */
  pull(riverId: string, sourcePath: string, category: string): string[] {
    const river = this.rivers.get(riverId);
    if (!river || river.type !== 'filesystem') {
      throw new Error(`Cannot pull from river: ${riverId}`);
    }
    this.assertRiverAccess(river, 'read');
    this.assertNoTraversal(sourcePath, 'sourcePath');
    this.assertCategoryAllowed(river, category);

    const fullSource = path.join(river.localPath, sourcePath);
    if (!fs.existsSync(fullSource)) return [];

    const files = fs.readdirSync(fullSource);
    const deposited: string[] = [];

    for (const file of files) {
      const filePath = path.join(fullSource, file);
      const stat = fs.statSync(filePath);
      if (stat.isFile()) {
        const data = fs.readFileSync(filePath);
        const dest = this.deposit(riverId, category, file, data);
        deposited.push(dest);
      }
    }

    return deposited;
  }

  /**
   * Push data from the basin to a river.
   */
  push(riverId: string, category: string, destPath: string): string[] {
    const river = this.rivers.get(riverId);
    if (!river || river.type !== 'filesystem') {
      throw new Error(`Cannot push to river: ${riverId}`);
    }
    this.assertRiverAccess(river, 'write');
    this.assertNoTraversal(destPath, 'destPath');
    this.assertCategoryAllowed(river, category);

    const sourceDir = path.join(this.config.intakePath, riverId, category);
    if (!fs.existsSync(sourceDir)) return [];

    const fullDest = path.join(river.localPath, destPath);
    fs.mkdirSync(fullDest, { recursive: true });

    const files = fs.readdirSync(sourceDir);
    const pushed: string[] = [];

    for (const file of files) {
      const src = path.join(sourceDir, file);
      const dst = path.join(fullDest, file);
      fs.copyFileSync(src, dst);
      pushed.push(dst);
    }

    return pushed;
  }

  /**
   * Get basin status — how much data is in intake, backup, archive.
   */
  status(): {
    rivers: River[];
    accessPoints: Array<{
      id: string;
      name: string;
      type: River['type'];
      readFromRiver: boolean;
      writeToRiver: boolean;
      allowedCategories: string[];
    }>;
    intake: { path: string; exists: boolean };
    backup: { path: string; exists: boolean };
    archive: { path: string; exists: boolean };
  } {
    return {
      rivers: this.probeRivers(),
      accessPoints: Array.from(this.rivers.values()).map((river) => {
        const policy = this.resolvePolicy(river);
        return {
          id: river.id,
          name: river.name,
          type: river.type,
          readFromRiver: policy.readFromRiver,
          writeToRiver: policy.writeToRiver,
          allowedCategories: policy.allowedCategories,
        };
      }),
      intake: {
        path: this.config.intakePath,
        exists: fs.existsSync(this.config.intakePath),
      },
      backup: {
        path: this.config.backupPath,
        exists: fs.existsSync(this.config.backupPath),
      },
      archive: {
        path: this.config.archivePath,
        exists: fs.existsSync(this.config.archivePath),
      },
    };
  }
}

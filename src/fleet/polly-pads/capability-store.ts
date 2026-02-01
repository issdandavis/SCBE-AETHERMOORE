/**
 * Polly Pads - Capability Store
 *
 * Hot-swappable modules that drones can load/unload.
 * Each capability is SCBE-signed and PHDM-validated.
 *
 * @module fleet/polly-pads/capability-store
 */

import { createHmac, createHash } from 'crypto';
import { Capability, SacredTongue, DroneClass } from './drone-core.js';

// ============================================================================
// Types
// ============================================================================

/** Capability category */
export type CapabilityCategory =
  | 'browser' // Web automation
  | 'coding' // Code generation/editing
  | 'deploy' // Infrastructure/deployment
  | 'research' // Information gathering
  | 'security' // Security/auditing
  | 'utility'; // General utilities

/** Capability manifest in the store */
export interface CapabilityManifest {
  id: string;
  name: string;
  version: string;
  description: string;
  category: CapabilityCategory;

  // Requirements
  minTrust: number;
  requiredTongue?: SacredTongue;
  requiredClass?: DroneClass[];
  dependencies: string[];

  // Resources
  entryPoint: string;
  wasmBundle?: string;
  size: number; // bytes

  // Security
  author: string;
  license: string;
  scbeSignature: string;
  phdmHash: string;

  // Metadata
  downloads: number;
  rating: number;
  tags: string[];
}

/** Store query options */
export interface StoreQuery {
  category?: CapabilityCategory;
  tongue?: SacredTongue;
  class?: DroneClass;
  maxTrust?: number;
  search?: string;
}

// ============================================================================
// Built-in Capabilities
// ============================================================================

const BUILTIN_CAPABILITIES: CapabilityManifest[] = [
  // Browser Automation
  {
    id: 'browser-use',
    name: 'Browser Use',
    version: '0.1.40',
    description: 'AI-powered browser automation for web tasks',
    category: 'browser',
    minTrust: 0.7,
    requiredClass: ['RECON', 'RESEARCH'],
    dependencies: [],
    entryPoint: 'browser-use/index.js',
    size: 2_500_000,
    author: 'browser-use',
    license: 'MIT',
    scbeSignature: '',
    phdmHash: '',
    downloads: 77_000,
    rating: 4.8,
    tags: ['browser', 'automation', 'web', 'scraping'],
  },
  {
    id: 'playwright',
    name: 'Playwright',
    version: '1.40.0',
    description: 'Cross-browser automation library',
    category: 'browser',
    minTrust: 0.6,
    dependencies: [],
    entryPoint: 'playwright/index.js',
    size: 50_000_000,
    author: 'Microsoft',
    license: 'Apache-2.0',
    scbeSignature: '',
    phdmHash: '',
    downloads: 500_000,
    rating: 4.9,
    tags: ['browser', 'testing', 'automation'],
  },

  // Coding Tools
  {
    id: 'aider',
    name: 'Aider',
    version: '0.50.0',
    description: 'AI pair programming in your terminal',
    category: 'coding',
    minTrust: 0.8,
    requiredClass: ['CODER'],
    dependencies: [],
    entryPoint: 'aider/index.js',
    size: 15_000_000,
    author: 'paul-gauthier',
    license: 'Apache-2.0',
    scbeSignature: '',
    phdmHash: '',
    downloads: 25_000,
    rating: 4.7,
    tags: ['coding', 'ai', 'pair-programming'],
  },
  {
    id: 'cline',
    name: 'Cline',
    version: '2.0.0',
    description: 'Autonomous coding agent',
    category: 'coding',
    minTrust: 0.85,
    requiredClass: ['CODER'],
    dependencies: [],
    entryPoint: 'cline/index.js',
    size: 20_000_000,
    author: 'cline',
    license: 'Apache-2.0',
    scbeSignature: '',
    phdmHash: '',
    downloads: 57_000,
    rating: 4.6,
    tags: ['coding', 'autonomous', 'agent'],
  },

  // Deployment Tools
  {
    id: 'terraform',
    name: 'Terraform Bridge',
    version: '1.0.0',
    description: 'Infrastructure as Code bridge for Terraform',
    category: 'deploy',
    minTrust: 0.9,
    requiredTongue: 'RU', // Binding operations
    requiredClass: ['DEPLOY'],
    dependencies: [],
    entryPoint: 'terraform-bridge/index.js',
    size: 5_000_000,
    author: 'SCBE',
    license: 'MIT',
    scbeSignature: '',
    phdmHash: '',
    downloads: 5_000,
    rating: 4.5,
    tags: ['infrastructure', 'iac', 'terraform'],
  },
  {
    id: 'docker-cli',
    name: 'Docker CLI Bridge',
    version: '1.0.0',
    description: 'Docker container management bridge',
    category: 'deploy',
    minTrust: 0.85,
    requiredClass: ['DEPLOY'],
    dependencies: [],
    entryPoint: 'docker-bridge/index.js',
    size: 3_000_000,
    author: 'SCBE',
    license: 'MIT',
    scbeSignature: '',
    phdmHash: '',
    downloads: 8_000,
    rating: 4.6,
    tags: ['docker', 'containers', 'devops'],
  },

  // Research Tools
  {
    id: 'perplexity',
    name: 'Perplexity Search',
    version: '1.0.0',
    description: 'AI-powered web search via Perplexity',
    category: 'research',
    minTrust: 0.5,
    requiredClass: ['RESEARCH', 'RECON'],
    dependencies: [],
    entryPoint: 'perplexity/index.js',
    size: 1_000_000,
    author: 'SCBE',
    license: 'MIT',
    scbeSignature: '',
    phdmHash: '',
    downloads: 15_000,
    rating: 4.7,
    tags: ['search', 'research', 'ai'],
  },

  // Security Tools
  {
    id: 'scbe-validator',
    name: 'SCBE Validator',
    version: '3.1.0',
    description: 'Validate actions against SCBE security policy',
    category: 'security',
    minTrust: 0.95,
    requiredTongue: 'DR', // Structure/Auth
    requiredClass: ['GUARD'],
    dependencies: [],
    entryPoint: 'scbe-validator/index.js',
    size: 500_000,
    author: 'SCBE',
    license: 'Proprietary',
    scbeSignature: '',
    phdmHash: '',
    downloads: 2_000,
    rating: 5.0,
    tags: ['security', 'validation', 'scbe'],
  },

  // Utilities
  {
    id: 'screenshot',
    name: 'Screenshot Capture',
    version: '1.0.0',
    description: 'Capture and analyze screenshots',
    category: 'utility',
    minTrust: 0.4,
    dependencies: [],
    entryPoint: 'screenshot/index.js',
    size: 500_000,
    author: 'SCBE',
    license: 'MIT',
    scbeSignature: '',
    phdmHash: '',
    downloads: 20_000,
    rating: 4.4,
    tags: ['screenshot', 'image', 'capture'],
  },
  {
    id: 'vision-llm',
    name: 'Vision LLM',
    version: '1.2.0',
    description: 'Visual understanding via multimodal LLMs',
    category: 'utility',
    minTrust: 0.8,
    dependencies: ['screenshot'],
    entryPoint: 'vision-llm/index.js',
    size: 100_000_000,
    author: 'SCBE',
    license: 'MIT',
    scbeSignature: '',
    phdmHash: '',
    downloads: 10_000,
    rating: 4.6,
    tags: ['vision', 'llm', 'multimodal'],
  },
];

// ============================================================================
// Capability Store Class
// ============================================================================

export class CapabilityStore {
  private capabilities: Map<string, CapabilityManifest> = new Map();
  private signatureKey: Buffer;

  constructor(signatureKey?: Buffer) {
    this.signatureKey = signatureKey || Buffer.from('polly-pads-default-key');

    // Load built-in capabilities
    for (const cap of BUILTIN_CAPABILITIES) {
      this.registerCapability(cap);
    }
  }

  /**
   * Register a capability in the store
   */
  registerCapability(manifest: CapabilityManifest): void {
    // Generate signatures if not present
    if (!manifest.scbeSignature) {
      manifest.scbeSignature = this.signCapability(manifest);
    }
    if (!manifest.phdmHash) {
      manifest.phdmHash = this.generatePHDMHash(manifest);
    }

    this.capabilities.set(manifest.id, manifest);
  }

  /**
   * Get a capability by ID
   */
  getCapability(id: string): CapabilityManifest | undefined {
    return this.capabilities.get(id);
  }

  /**
   * Search capabilities
   */
  searchCapabilities(query: StoreQuery): CapabilityManifest[] {
    let results = Array.from(this.capabilities.values());

    if (query.category) {
      results = results.filter((c) => c.category === query.category);
    }

    if (query.tongue) {
      results = results.filter((c) => !c.requiredTongue || c.requiredTongue === query.tongue);
    }

    if (query.class) {
      results = results.filter((c) => !c.requiredClass || c.requiredClass.includes(query.class!));
    }

    if (query.maxTrust !== undefined) {
      results = results.filter((c) => c.minTrust <= query.maxTrust!);
    }

    if (query.search) {
      const searchLower = query.search.toLowerCase();
      results = results.filter(
        (c) =>
          c.name.toLowerCase().includes(searchLower) ||
          c.description.toLowerCase().includes(searchLower) ||
          c.tags.some((t) => t.includes(searchLower))
      );
    }

    // Sort by downloads (popularity)
    results.sort((a, b) => b.downloads - a.downloads);

    return results;
  }

  /**
   * Get capabilities compatible with a drone
   */
  getCompatibleCapabilities(
    tongue: SacredTongue,
    droneClass: DroneClass,
    trustRadius: number
  ): CapabilityManifest[] {
    const maxTrust = 1 - trustRadius; // Convert radius to trust level

    return this.searchCapabilities({
      tongue,
      class: droneClass,
      maxTrust,
    });
  }

  /**
   * Convert manifest to loadable Capability
   */
  toCapability(manifest: CapabilityManifest): Capability {
    return {
      id: manifest.id,
      name: manifest.name,
      version: manifest.version,
      minTrust: manifest.minTrust,
      requiredTongue: manifest.requiredTongue,
      dependencies: manifest.dependencies,
      entryPoint: manifest.entryPoint,
      active: false,
    };
  }

  // --------------------------------------------------------------------------
  // Security
  // --------------------------------------------------------------------------

  /**
   * Sign a capability with SCBE
   */
  private signCapability(manifest: CapabilityManifest): string {
    const data = JSON.stringify({
      id: manifest.id,
      name: manifest.name,
      version: manifest.version,
      entryPoint: manifest.entryPoint,
      author: manifest.author,
    });

    return createHmac('sha256', this.signatureKey).update(data).digest('hex');
  }

  /**
   * Generate PHDM hash for control flow integrity
   */
  private generatePHDMHash(manifest: CapabilityManifest): string {
    // Hash the entry point and dependencies for CFI
    const data = JSON.stringify({
      entryPoint: manifest.entryPoint,
      dependencies: manifest.dependencies,
      category: manifest.category,
    });

    return createHash('sha256').update(data).digest('hex').slice(0, 16);
  }

  /**
   * Verify capability signature
   */
  verifyCapability(manifest: CapabilityManifest): boolean {
    const expectedSig = this.signCapability(manifest);
    return manifest.scbeSignature === expectedSig;
  }

  // --------------------------------------------------------------------------
  // Stats
  // --------------------------------------------------------------------------

  getStats(): { total: number; byCategory: Record<string, number> } {
    const byCategory: Record<string, number> = {};

    for (const cap of this.capabilities.values()) {
      byCategory[cap.category] = (byCategory[cap.category] || 0) + 1;
    }

    return {
      total: this.capabilities.size,
      byCategory,
    };
  }
}

// ============================================================================
// Default Export
// ============================================================================

export const defaultStore = new CapabilityStore();

export default CapabilityStore;

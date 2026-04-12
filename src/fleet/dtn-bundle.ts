/**
 * @file dtn-bundle.ts
 * @module fleet/dtn-bundle
 * @layer L7 (Store-and-Forward), L11 (Temporal Distance), L14 (Audio Axis)
 * @component DTN Bundle — Delay-Tolerant Network primitives for SCBE pipeline routing
 * @version 1.0.0
 *
 * Raw DTN primitives: bundle creation, relay nodes, contact graphs,
 * store-and-forward simulation, FEC encoding across 6 Sacred Tongues.
 *
 * This is the envelope and post office. The DTNBundleFactory (dtn-bundle-factory.ts)
 * is the mail room that decides WHAT gets packed and WHERE it goes.
 *
 * @axiom Unitarity — Bundle payload preserved through relay chain
 * @axiom Symmetry — All 6 tongue FEC encodings are equivalent representations
 * @axiom Causality — Custody chain enforces temporal ordering
 */

import type { MessagePriority } from './crawl-message-bus.js';

// ──────────────── Constants ────────────────

const PHI = (1 + Math.sqrt(5)) / 2;

/** Sacred Tongue phi weights */
const TONGUE_WEIGHTS: Record<BundleTongue, number> = {
  KO: 1.0,
  AV: PHI,
  RU: PHI ** 2,
  CA: PHI ** 3,
  UM: PHI ** 4,
  DR: PHI ** 5,
};

// ──────────────── Types ────────────────

/** The six Sacred Tongues as bundle classification */
export type BundleTongue = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** Bundle lifecycle status */
export type BundleStatus =
  | 'CREATED'
  | 'IN_TRANSIT'
  | 'STORED'
  | 'DELIVERED'
  | 'EXPIRED'
  | 'CORRUPTED';

/** Forward Error Correction block — one per tongue */
export interface FECBlock {
  tongue: BundleTongue;
  encoding: string;
  hash: string;
  weight: number;
}

/** Fragment metadata for reassembly */
export interface FragmentInfo {
  parentId: string;
  offset: number;
  totalSize: number;
  isLast: boolean;
}

/** Custody chain entry */
export interface CustodyEntry {
  nodeId: string;
  timestamp: number;
  action: 'received' | 'forwarded' | 'stored' | 'delivered';
}

/** A DTN Bundle — the atomic unit of SCBE pipeline routing */
export interface DTNBundle {
  /** Unique bundle identifier */
  readonly id: string;
  /** Source layer/node */
  readonly sourceEndpoint: string;
  /** Destination layer/node */
  readonly destinationEndpoint: string;
  /** Bundle payload (any serializable data) */
  readonly payload: unknown;
  /** Sacred Tongue classification */
  readonly tongue: BundleTongue;
  /** Message priority */
  readonly priority: MessagePriority;
  /** Assumptions about the bundle context */
  readonly assumptions: string[];
  /** Contingency plans if routing fails */
  readonly contingencies: string[];
  /** Forward Error Correction blocks (one per tongue) */
  readonly fecBlocks: FECBlock[];
  /** Governance score H(d,pd) = 1/(1+d_H+2*pd) */
  readonly governanceScore: number;
  /** Remaining lifetime in simulation steps */
  lifetime: number;
  /** Current status */
  status: BundleStatus;
  /** Fragment info (undefined if not fragmented) */
  fragment?: FragmentInfo;
  /** Ordered list of nodes this bundle has visited */
  custodyChain: CustodyEntry[];
  /** Creation timestamp */
  readonly createdAt: number;
  /** Arbitrary extension data */
  readonly extensions: Record<string, unknown>;
}

/** Per-node telemetry snapshot */
export interface RelayTelemetry {
  nodeId: string;
  storedBundles: number;
  forwarded: number;
  delivered: number;
  expired: number;
  occluded: boolean;
}

// ──────────────── Helpers ────────────────

/** Simple string hash for FEC integrity verification */
export function simpleHash(s: string): string {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h).toString(16).padStart(8, '0');
}

/** Generate a unique bundle ID */
function generateBundleId(): string {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).substring(2, 8);
  return `dtn-${ts}-${rand}`;
}

/**
 * Build FEC blocks — one per tongue.
 * Each block encodes the payload with the tongue's phi weight prefix,
 * then hashes the tongue:payload pair for integrity checking.
 *
 * A4: Symmetry — all 6 encodings carry equivalent information.
 */
function buildFECBlocks(payload: unknown, primaryTongue: BundleTongue): FECBlock[] {
  const payloadStr = typeof payload === 'string' ? payload : JSON.stringify(payload);
  const tongues: BundleTongue[] = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];

  return tongues.map((tongue) => {
    const weight = TONGUE_WEIGHTS[tongue];
    const encoding = `[${tongue}:${weight.toFixed(4)}] ${payloadStr}`;
    const hash = simpleHash(`${tongue}:${payloadStr}`);
    return { tongue, encoding, hash, weight };
  });
}

/**
 * Compute the harmonic wall governance score.
 * H(d, pd) = 1 / (1 + phi * d_H + 2 * pd)
 */
function computeGovernanceScore(d_H: number, pd: number): number {
  return 1 / (1 + PHI * d_H + 2 * pd);
}

// ──────────────── Bundle Creation ────────────────

/** Options for createBundle */
export interface CreateBundleOptions {
  assumptions?: string[];
  contingencies?: string[];
  lifetime?: number;
  priority?: MessagePriority;
  hyperbolicDistance?: number;
  perturbationDensity?: number;
  extensions?: Record<string, unknown>;
}

/**
 * Create a new DTN bundle.
 *
 * Bundles are the atomic unit of the SCBE pipeline network. Each carries:
 * - Payload (any serializable data)
 * - 6 FEC blocks (one per Sacred Tongue) for redundancy
 * - Governance score from the harmonic wall
 * - Custody chain for audit
 */
export function createBundle(
  source: string,
  destination: string,
  payload: unknown,
  tongue: BundleTongue,
  options: CreateBundleOptions = {}
): DTNBundle {
  const d_H = options.hyperbolicDistance ?? 0.1;
  const pd = options.perturbationDensity ?? 0.0;

  return {
    id: generateBundleId(),
    sourceEndpoint: source,
    destinationEndpoint: destination,
    payload,
    tongue,
    priority: options.priority ?? 'normal',
    assumptions: options.assumptions ?? [],
    contingencies: options.contingencies ?? [],
    fecBlocks: buildFECBlocks(payload, tongue),
    governanceScore: computeGovernanceScore(d_H, pd),
    lifetime: options.lifetime ?? 20,
    status: 'CREATED',
    fragment: undefined,
    custodyChain: [{ nodeId: source, timestamp: Date.now(), action: 'received' }],
    createdAt: Date.now(),
    extensions: options.extensions ?? {},
  };
}

// ──────────────── Bundle Store ────────────────

/**
 * BundleStore — per-node storage for bundles awaiting forwarding.
 *
 * Implements store-and-forward: when no contact window is available,
 * bundles are stored until a window opens. Capacity-limited to prevent
 * unbounded growth.
 */
export class BundleStore {
  private bundles: DTNBundle[] = [];
  private readonly capacity: number;

  constructor(capacity: number = 500) {
    this.capacity = capacity;
  }

  /** Store a bundle. Returns false if at capacity. */
  store(bundle: DTNBundle): boolean {
    if (this.bundles.length >= this.capacity) return false;
    bundle.status = 'STORED';
    this.bundles.push(bundle);
    return true;
  }

  /** Retrieve and remove bundles destined for a target node. */
  retrieve(targetNodeId: string, maxCount: number = Infinity): DTNBundle[] {
    const toForward: DTNBundle[] = [];
    const remaining: DTNBundle[] = [];

    for (const bundle of this.bundles) {
      if (toForward.length < maxCount && bundle.destinationEndpoint === targetNodeId) {
        toForward.push(bundle);
      } else if (toForward.length < maxCount && this.isOnRoute(bundle, targetNodeId)) {
        toForward.push(bundle);
      } else {
        remaining.push(bundle);
      }
    }

    this.bundles = remaining;
    return toForward;
  }

  /** Retrieve ALL stored bundles (for forwarding to any available neighbor) */
  retrieveAll(maxCount: number = Infinity): DTNBundle[] {
    const count = Math.min(maxCount, this.bundles.length);
    return this.bundles.splice(0, count);
  }

  /** Expire bundles whose lifetime has reached 0 */
  expireStale(): DTNBundle[] {
    const expired: DTNBundle[] = [];
    this.bundles = this.bundles.filter((b) => {
      if (b.lifetime <= 0) {
        b.status = 'EXPIRED';
        expired.push(b);
        return false;
      }
      return true;
    });
    return expired;
  }

  /** Decrement lifetime on all stored bundles */
  tick(): void {
    for (const b of this.bundles) {
      b.lifetime--;
    }
  }

  get count(): number {
    return this.bundles.length;
  }

  /** Simple route check — bundle heading toward a neighbor of target */
  private isOnRoute(bundle: DTNBundle, targetNodeId: string): boolean {
    // Extract layer numbers for comparison
    const destNum = this.layerNum(bundle.destinationEndpoint);
    const targetNum = this.layerNum(targetNodeId);
    if (destNum < 0 || targetNum < 0) return false;
    // Forward if target is between us and destination
    return targetNum <= destNum;
  }

  private layerNum(id: string): number {
    const m = id.match(/^L(\d+)$/);
    return m ? parseInt(m[1], 10) : -1;
  }
}

// ──────────────── Contact Graph ────────────────

/** A contact window between two relay nodes */
export interface ContactWindow {
  fromNode: string;
  toNode: string;
  openStep: number;
  closeStep: number;
  bandwidth: number; // bundles per step
}

/**
 * ContactGraph — manages contact windows between relay nodes.
 *
 * In DTN, contact windows represent predictable connectivity intervals.
 * In the SCBE pipeline, they represent the data flow capacity between layers.
 */
export class ContactGraph {
  private windows: ContactWindow[] = [];

  addWindow(
    from: string,
    to: string,
    openStep: number,
    closeStep: number,
    bandwidth: number
  ): void {
    this.windows.push({ fromNode: from, toNode: to, openStep, closeStep, bandwidth });
  }

  /** Get active windows from a given node at the current step */
  getActiveWindows(fromNode: string, currentStep: number): ContactWindow[] {
    return this.windows.filter(
      (w) => w.fromNode === fromNode && currentStep >= w.openStep && currentStep <= w.closeStep
    );
  }

  /** Get all neighbors reachable from a node at current step */
  getReachableNeighbors(fromNode: string, currentStep: number): string[] {
    return this.getActiveWindows(fromNode, currentStep).map((w) => w.toNode);
  }
}

// ──────────────── DTN Relay Node ────────────────

/**
 * DTNRelayNode — a single node (pipeline layer) in the DTN network.
 *
 * Each node has a bundle store and can receive, forward, or deliver bundles.
 */
export class DTNRelayNode {
  readonly id: string;
  readonly store: BundleStore;
  private forwarded = 0;
  private delivered = 0;
  private expiredCount = 0;
  occluded = false;

  constructor(id: string, storeCapacity: number = 500) {
    this.id = id;
    this.store = new BundleStore(storeCapacity);
  }

  /** Receive a bundle — deliver if we're the destination, else store */
  receive(bundle: DTNBundle): boolean {
    bundle.custodyChain.push({
      nodeId: this.id,
      timestamp: Date.now(),
      action: bundle.destinationEndpoint === this.id ? 'delivered' : 'received',
    });

    if (bundle.destinationEndpoint === this.id) {
      bundle.status = 'DELIVERED';
      this.delivered++;
      return true;
    }

    bundle.status = 'IN_TRANSIT';
    return this.store.store(bundle);
  }

  /** Forward bundles to a neighbor node */
  forwardTo(neighbor: DTNRelayNode, bandwidth: number): number {
    if (this.occluded || neighbor.occluded) return 0;

    const bundles = this.store.retrieveAll(bandwidth);
    let sent = 0;
    for (const bundle of bundles) {
      bundle.custodyChain.push({
        nodeId: this.id,
        timestamp: Date.now(),
        action: 'forwarded',
      });
      if (neighbor.receive(bundle)) {
        sent++;
      }
      this.forwarded++;
      sent++;
    }
    return sent;
  }

  /** Tick: decrement lifetimes, expire stale */
  tick(): void {
    this.store.tick();
    const expired = this.store.expireStale();
    this.expiredCount += expired.length;
  }

  getTelemetry(): RelayTelemetry {
    return {
      nodeId: this.id,
      storedBundles: this.store.count,
      forwarded: this.forwarded,
      delivered: this.delivered,
      expired: this.expiredCount,
      occluded: this.occluded,
    };
  }
}

// ──────────────── DTN Network Simulator ────────────────

/**
 * DTNNetworkSimulator — simulates the 14-layer SCBE pipeline as a DTN.
 *
 * Step-based simulation: each step, all nodes tick (decrement lifetimes),
 * then forward bundles through active contact windows.
 */
export class DTNNetworkSimulator {
  private nodes: Map<string, DTNRelayNode> = new Map();
  private graph: ContactGraph = new ContactGraph();
  private currentStep = 0;

  /** Add a relay node */
  addNode(id: string, storeCapacity: number = 500): void {
    this.nodes.set(id, new DTNRelayNode(id, storeCapacity));
  }

  /** Add a contact window between nodes */
  addContactWindow(
    from: string,
    to: string,
    openStep: number,
    closeStep: number,
    bandwidth: number
  ): void {
    this.graph.addWindow(from, to, openStep, closeStep, bandwidth);
  }

  /** Inject a bundle at a specific node */
  inject(bundle: DTNBundle, nodeId: string): boolean {
    const node = this.nodes.get(nodeId);
    if (!node) return false;
    return node.receive(bundle);
  }

  /** Set occlusion on a node (simulates context blackout) */
  setOcclusion(nodeId: string, occluded: boolean): void {
    const node = this.nodes.get(nodeId);
    if (node) node.occluded = occluded;
  }

  /** Run the simulation for N steps */
  run(steps: number): void {
    for (let s = 0; s < steps; s++) {
      this.currentStep++;

      // 1. Tick all nodes (decrement lifetimes, expire stale)
      for (const node of this.nodes.values()) {
        node.tick();
      }

      // 2. Forward bundles through active contact windows
      for (const node of this.nodes.values()) {
        if (node.occluded) continue;
        const windows = this.graph.getActiveWindows(node.id, this.currentStep);
        for (const window of windows) {
          const neighbor = this.nodes.get(window.toNode);
          if (neighbor && !neighbor.occluded) {
            node.forwardTo(neighbor, window.bandwidth);
          }
        }
      }
    }
  }

  /** Get telemetry from all nodes */
  getNodeTelemetry(): RelayTelemetry[] {
    return Array.from(this.nodes.values()).map((n) => n.getTelemetry());
  }

  /** Get current simulation step */
  get step(): number {
    return this.currentStep;
  }
}

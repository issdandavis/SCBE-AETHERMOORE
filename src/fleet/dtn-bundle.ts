/**
 * @file dtn-bundle.ts
 * @module fleet/dtn-bundle
 * @layer L7 (Store-and-Forward), L11 (Temporal Distance), L13 (Risk Decision)
 * @component DTN Bundle Protocol for Cognitive Thought Routing
 * @version 1.0.0
 *
 * Delay-Tolerant Networking applied to AI thought routing.
 *
 * NASA built DTN for Mars comms where TCP collapses: 3-22 minute
 * one-way latency, episodic occlusion, bursty connectivity.
 * LLM context collapse (window truncation, tool failures, prompt
 * injection) is mathematically identical.
 *
 * Core equations:
 *   P_TCP = (1-p)^n  — dies under occlusion
 *   P_DTN = 1 - p^n  — survives under occlusion
 *
 * At 30% occlusion over 10 steps: TCP = 2.8%, DTN = 99.997%.
 *
 * @axiom Causality — Bundle timestamps enforce temporal ordering
 * @axiom Composition — Bundles carry full pipeline state, self-contained
 * @axiom Unitarity — Custody transfer preserves total bundle count
 */

import type { CrawlChannel, CrawlMessage, MessagePriority } from './crawl-message-bus.js';
import type { KernelDecision, NodeState } from './node-kernel.js';

// ──────────────── Types ────────────────

/** Sacred Tongue assignment for bundle routing */
export type BundleTongue = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** Bundle delivery status */
export type BundleStatus =
  | 'CREATED'    // Bundle packed, not yet sent
  | 'IN_TRANSIT' // En route through pipeline layers
  | 'STORED'     // Held at relay node (occlusion/capacity)
  | 'DELIVERED'  // Reached destination
  | 'EXPIRED'    // TTL exceeded — harmonic decay consumed it
  | 'CORRUPTED'; // FEC could not recover

/** Custody transfer record — who held this bundle and when */
export interface CustodyRecord {
  /** Node/layer that held custody */
  readonly nodeId: string;
  /** When custody was accepted */
  readonly acceptedAt: number;
  /** When custody was released (undefined if still held) */
  readonly releasedAt?: number;
  /** Axiom group that governed this hop */
  readonly axiomGroup: 'unitarity' | 'locality' | 'causality' | 'symmetry' | 'composition';
}

/** Forward Error Correction — redundant encodings */
export interface FECBlock {
  /** Tongue used for this encoding */
  readonly tongue: BundleTongue;
  /** Encoded payload (same concept, different angle) */
  readonly encoding: string;
  /** Integrity hash */
  readonly hash: string;
}

/**
 * A DTN Bundle — self-contained thought package.
 *
 * Like a sealed envelope with full addressing, custody transfer,
 * lifetime metadata, and redundant encodings. If the environment
 * goes dark, the bundle doesn't die — it waits.
 */
export interface DTNBundle<T = unknown> {
  /** Unique bundle ID */
  readonly id: string;
  /** Source endpoint — which cognitive module originated the thought */
  readonly sourceEndpoint: string;
  /** Destination endpoint — target processing layer */
  readonly destinationEndpoint: string;
  /** Creation timestamp (ms) — temporal ordering for causality */
  readonly createdAt: number;
  /** Time-to-live in steps (not wall-clock) — maps to harmonic decay */
  readonly lifetime: number;
  /** Remaining lifetime (decremented each hop) */
  remainingLifetime: number;
  /** Primary tongue assignment */
  readonly tongue: BundleTongue;
  /** The actual cognitive payload */
  readonly payload: T;
  /** Assumptions packed into the bundle (context that might get occluded) */
  readonly assumptions: string[];
  /** Contingency plans — Plan B, C (forward error correction for reasoning) */
  readonly contingencies: string[];
  /** Forward error correction blocks — same payload encoded through multiple tongues */
  readonly fecBlocks: FECBlock[];
  /** Custody chain — every node that held this bundle */
  readonly custodyChain: CustodyRecord[];
  /** Current status */
  status: BundleStatus;
  /** Priority for store-and-forward queue ordering */
  readonly priority: MessagePriority;
  /** Fragment metadata (if this is a fragment of a larger bundle) */
  readonly fragment?: {
    parentId: string;
    offset: number;
    totalSize: number;
    isLast: boolean;
  };
  /** Governance score at creation — from harmonic wall */
  readonly governanceScore: number;
  /** Extension blocks — arbitrary metadata (tongue profile, axiom tags, etc.) */
  readonly extensions: Record<string, unknown>;
}

// ──────────────── Contact Graph ────────────────

/** A single contact window — when a link is available */
export interface ContactWindow {
  /** Source node */
  readonly from: string;
  /** Destination node */
  readonly to: string;
  /** Window opens at (ms) */
  readonly opensAt: number;
  /** Window closes at (ms) */
  readonly closesAt: number;
  /** Available bandwidth (bundles per step) */
  readonly bandwidth: number;
}

/**
 * Contact Graph — time-varying directed graph of communication windows.
 *
 * In space, you know when Mars is visible from Earth. In AI,
 * you know when each pipeline layer has processing capacity.
 */
export class ContactGraph {
  private windows: ContactWindow[] = [];

  addWindow(window: ContactWindow): void {
    this.windows.push(window);
  }

  /** Get available windows from a node at a given time */
  getAvailableWindows(fromNode: string, atTime: number): ContactWindow[] {
    return this.windows.filter(
      (w) => w.from === fromNode && w.opensAt <= atTime && w.closesAt > atTime
    );
  }

  /** Find the next available window from a node to a destination */
  getNextWindow(fromNode: string, toNode: string, afterTime: number): ContactWindow | undefined {
    return this.windows
      .filter((w) => w.from === fromNode && w.to === toNode && w.opensAt > afterTime)
      .sort((a, b) => a.opensAt - b.opensAt)[0];
  }

  /** Check if a route exists (multi-hop) from source to destination */
  hasRoute(source: string, destination: string, atTime: number, maxHops: number = 10): boolean {
    const visited = new Set<string>();
    const queue: Array<{ node: string; hops: number }> = [{ node: source, hops: 0 }];

    while (queue.length > 0) {
      const current = queue.shift()!;
      if (current.node === destination) return true;
      if (current.hops >= maxHops || visited.has(current.node)) continue;
      visited.add(current.node);

      for (const w of this.getAvailableWindows(current.node, atTime)) {
        if (!visited.has(w.to)) {
          queue.push({ node: w.to, hops: current.hops + 1 });
        }
      }
    }
    return false;
  }
}

// ──────────────── Bundle Store ────────────────

/**
 * BundleStore — per-node persistent storage for bundles.
 *
 * When the next hop is unreachable (occlusion), bundles
 * are stored here until a contact window opens.
 */
export class BundleStore {
  private bundles: Map<string, DTNBundle> = new Map();
  private maxCapacity: number;

  constructor(maxCapacity: number = 1000) {
    this.maxCapacity = maxCapacity;
  }

  /** Store a bundle. Returns false if at capacity. */
  store(bundle: DTNBundle): boolean {
    if (this.bundles.size >= this.maxCapacity) {
      // Evict lowest-priority expired bundles first
      this.evictExpired();
      if (this.bundles.size >= this.maxCapacity) return false;
    }
    bundle.status = 'STORED';
    this.bundles.set(bundle.id, bundle);
    return true;
  }

  /** Retrieve a bundle by ID */
  get(id: string): DTNBundle | undefined {
    return this.bundles.get(id);
  }

  /** Get all stored bundles for a destination, ordered by priority */
  getForDestination(destination: string): DTNBundle[] {
    const priorityOrder: Record<MessagePriority, number> = {
      critical: 0,
      high: 1,
      normal: 2,
      low: 3,
    };
    return Array.from(this.bundles.values())
      .filter((b) => b.destinationEndpoint === destination && b.status === 'STORED')
      .sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);
  }

  /** Remove a bundle (after successful forwarding) */
  release(id: string): boolean {
    return this.bundles.delete(id);
  }

  /** Evict expired bundles */
  evictExpired(): number {
    let evicted = 0;
    for (const [id, bundle] of this.bundles) {
      if (bundle.remainingLifetime <= 0) {
        bundle.status = 'EXPIRED';
        this.bundles.delete(id);
        evicted++;
      }
    }
    return evicted;
  }

  /** Current stored count */
  get size(): number {
    return this.bundles.size;
  }

  /** Get all bundles (for telemetry) */
  getAll(): DTNBundle[] {
    return Array.from(this.bundles.values());
  }
}

// ──────────────── DTN Relay Node ────────────────

/** Relay node telemetry */
export interface RelayTelemetry {
  nodeId: string;
  bundlesStored: number;
  bundlesForwarded: number;
  bundlesExpired: number;
  bundlesReceived: number;
  custodyTransfers: number;
  occlusionEvents: number;
  currentlyOccluded: boolean;
}

/**
 * DTNRelayNode — a single node in the delay-tolerant network.
 *
 * Each node in the 14-layer pipeline IS a relay node.
 * It stores bundles during occlusion, forwards them when
 * contact windows open, and tracks custody.
 */
export class DTNRelayNode {
  readonly nodeId: string;
  readonly store: BundleStore;
  private contactGraph: ContactGraph;
  private occluded: boolean = false;
  private telemetry: RelayTelemetry;

  constructor(nodeId: string, contactGraph: ContactGraph, storeCapacity: number = 500) {
    this.nodeId = nodeId;
    this.store = new BundleStore(storeCapacity);
    this.contactGraph = contactGraph;
    this.telemetry = {
      nodeId,
      bundlesStored: 0,
      bundlesForwarded: 0,
      bundlesExpired: 0,
      bundlesReceived: 0,
      custodyTransfers: 0,
      occlusionEvents: 0,
      currentlyOccluded: false,
    };
  }

  /** Simulate occlusion (Mars behind the Sun) */
  setOccluded(occluded: boolean): void {
    if (occluded && !this.occluded) {
      this.telemetry.occlusionEvents++;
    }
    this.occluded = occluded;
    this.telemetry.currentlyOccluded = occluded;
  }

  /** Receive a bundle — accept custody or reject */
  receive(bundle: DTNBundle): boolean {
    if (bundle.remainingLifetime <= 0) {
      bundle.status = 'EXPIRED';
      this.telemetry.bundlesExpired++;
      return false;
    }

    // Accept custody
    const custodyRecord: CustodyRecord = {
      nodeId: this.nodeId,
      acceptedAt: Date.now(),
      axiomGroup: this.inferAxiomGroup(),
    };
    bundle.custodyChain.push(custodyRecord);
    this.telemetry.bundlesReceived++;
    this.telemetry.custodyTransfers++;

    // If we're the destination, deliver
    if (bundle.destinationEndpoint === this.nodeId) {
      bundle.status = 'DELIVERED';
      // Release custody on the last holder
      const lastCustody = bundle.custodyChain[bundle.custodyChain.length - 1];
      if (lastCustody) {
        (lastCustody as { releasedAt?: number }).releasedAt = Date.now();
      }
      return true;
    }

    // Otherwise, store for forwarding
    const stored = this.store.store(bundle);
    if (stored) {
      this.telemetry.bundlesStored++;
    }
    return stored;
  }

  /**
   * Forward stored bundles through available contact windows.
   *
   * In multi-hop DTN, a relay forwards ANY stored bundle through
   * any available window — the next hop is not necessarily the final
   * destination. This is store-and-forward: push bundles closer to
   * their destination one hop at a time.
   */
  forward(currentTime: number): Array<{ bundle: DTNBundle; nextHop: string }> {
    if (this.occluded) return []; // Can't forward during occlusion

    const forwarded: Array<{ bundle: DTNBundle; nextHop: string }> = [];
    const windows = this.contactGraph.getAvailableWindows(this.nodeId, currentTime);
    const forwardedIds = new Set<string>();

    // Get all stored bundles, prioritized
    const allStored = this.store.getAll().filter((b) => b.status === 'STORED');
    const priorityOrder: Record<string, number> = { critical: 0, high: 1, normal: 2, low: 3 };
    allStored.sort((a, b) => (priorityOrder[a.priority] ?? 2) - (priorityOrder[b.priority] ?? 2));

    for (const window of windows) {
      let sent = 0;
      for (const bundle of allStored) {
        if (sent >= window.bandwidth) break;
        if (forwardedIds.has(bundle.id)) continue;

        // Forward through this window (next hop, not necessarily final destination)
        bundle.remainingLifetime--;

        // Release custody
        const lastCustody = bundle.custodyChain[bundle.custodyChain.length - 1];
        if (lastCustody) {
          (lastCustody as { releasedAt?: number }).releasedAt = Date.now();
        }

        bundle.status = 'IN_TRANSIT';
        this.store.release(bundle.id);
        this.telemetry.bundlesForwarded++;
        forwarded.push({ bundle, nextHop: window.to });
        forwardedIds.add(bundle.id);
        sent++;
      }
    }

    // Expire dead bundles
    const expired = this.store.evictExpired();
    this.telemetry.bundlesExpired += expired;

    return forwarded;
  }

  /** Get telemetry snapshot */
  getTelemetry(): Readonly<RelayTelemetry> {
    return { ...this.telemetry };
  }

  /** Infer which axiom group governs this node based on ID convention */
  private inferAxiomGroup(): CustodyRecord['axiomGroup'] {
    const id = this.nodeId.toLowerCase();
    if (id.includes('l2') || id.includes('l4') || id.includes('l7')) return 'unitarity';
    if (id.includes('l3') || id.includes('l8')) return 'locality';
    if (id.includes('l6') || id.includes('l11') || id.includes('l13')) return 'causality';
    if (id.includes('l5') || id.includes('l9') || id.includes('l10') || id.includes('l12'))
      return 'symmetry';
    return 'composition'; // L1, L14, or unknown
  }
}

// ──────────────── Bundle Factory ────────────────

/** Phi constant for harmonic scaling */
const PHI = (1 + Math.sqrt(5)) / 2;

/** Tongue weights (phi-scaled) */
const TONGUE_WEIGHTS: Record<BundleTongue, number> = {
  KO: 1.0,
  AV: PHI,
  RU: PHI * PHI,
  CA: PHI * PHI * PHI,
  UM: PHI ** 4,
  DR: PHI ** 5,
};

/** Generate a bundle ID */
function generateBundleId(): string {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).substring(2, 8);
  return `bndl-${ts}-${rand}`;
}

/** Simple string hash for FEC integrity */
function simpleHash(s: string): string {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h).toString(16).padStart(8, '0');
}

/**
 * Compute governance score using harmonic wall formula.
 * H(d, pd) = 1 / (1 + phi * d_H + 2 * pd)
 *
 * Higher score = safer operation, longer bundle lifetime.
 * Lower score = adversarial territory, bundle expires faster.
 */
function harmonicGovernanceScore(
  hyperbolicDistance: number,
  perturbationDensity: number
): number {
  return 1 / (1 + PHI * hyperbolicDistance + 2 * perturbationDensity);
}

/**
 * Create a DTN Bundle — pack a complete thought into a sealed envelope.
 *
 * @param source - Originating module/layer ID
 * @param destination - Target module/layer ID
 * @param payload - The cognitive content
 * @param tongue - Primary tongue assignment
 * @param options - Additional bundle options
 */
export function createBundle<T>(
  source: string,
  destination: string,
  payload: T,
  tongue: BundleTongue,
  options: {
    assumptions?: string[];
    contingencies?: string[];
    lifetime?: number;
    priority?: MessagePriority;
    hyperbolicDistance?: number;
    perturbationDensity?: number;
    extensions?: Record<string, unknown>;
  } = {}
): DTNBundle<T> {
  const d_H = options.hyperbolicDistance ?? 0.1;
  const pd = options.perturbationDensity ?? 0.0;
  const govScore = harmonicGovernanceScore(d_H, pd);

  // Lifetime scales with governance score — safe bundles live longer
  const baseLifetime = options.lifetime ?? 10;
  const scaledLifetime = Math.max(1, Math.round(baseLifetime * govScore * TONGUE_WEIGHTS[tongue]));

  // Generate FEC blocks — encode through all 6 tongues
  const payloadStr = JSON.stringify(payload);
  const fecBlocks: FECBlock[] = (['KO', 'AV', 'RU', 'CA', 'UM', 'DR'] as BundleTongue[]).map(
    (t) => ({
      tongue: t,
      encoding: `[${t}:${TONGUE_WEIGHTS[t].toFixed(4)}] ${payloadStr.substring(0, 200)}`,
      hash: simpleHash(`${t}:${payloadStr}`),
    })
  );

  return {
    id: generateBundleId(),
    sourceEndpoint: source,
    destinationEndpoint: destination,
    createdAt: Date.now(),
    lifetime: scaledLifetime,
    remainingLifetime: scaledLifetime,
    tongue,
    payload,
    assumptions: options.assumptions ?? [],
    contingencies: options.contingencies ?? [],
    fecBlocks,
    custodyChain: [],
    status: 'CREATED',
    priority: options.priority ?? 'normal',
    governanceScore: govScore,
    extensions: options.extensions ?? {},
  };
}

// ──────────────── DTN Network Simulator ────────────────

/** Simulation step result */
export interface SimulationStep {
  step: number;
  time: number;
  bundlesCreated: number;
  bundlesDelivered: number;
  bundlesExpired: number;
  bundlesInTransit: number;
  bundlesStored: number;
  occludedNodes: string[];
  deliveryRate: number;
}

/**
 * DTNNetworkSimulator — simulates a multi-node DTN network.
 *
 * Tests bundle routing under occlusion, capacity constraints,
 * and multi-hop forwarding. Use this to validate that the
 * store-and-forward architecture survives context blackouts.
 */
export class DTNNetworkSimulator {
  private nodes: Map<string, DTNRelayNode> = new Map();
  private contactGraph: ContactGraph;
  private stepCount: number = 0;
  private history: SimulationStep[] = [];
  private allBundles: DTNBundle[] = [];

  constructor() {
    this.contactGraph = new ContactGraph();
  }

  /** Add a node to the network */
  addNode(nodeId: string, storeCapacity: number = 500): DTNRelayNode {
    const node = new DTNRelayNode(nodeId, this.contactGraph, storeCapacity);
    this.nodes.set(nodeId, node);
    return node;
  }

  /** Add a contact window (scheduled link) */
  addContactWindow(from: string, to: string, opensAt: number, closesAt: number, bandwidth: number = 5): void {
    this.contactGraph.addWindow({ from, to, opensAt, closesAt, bandwidth });
  }

  /** Inject a bundle into the network at a source node */
  inject(bundle: DTNBundle, atNode: string): boolean {
    const node = this.nodes.get(atNode);
    if (!node) return false;
    this.allBundles.push(bundle);
    return node.receive(bundle);
  }

  /** Set occlusion state for a node */
  setOcclusion(nodeId: string, occluded: boolean): void {
    const node = this.nodes.get(nodeId);
    if (node) node.setOccluded(occluded);
  }

  /** Run one simulation step */
  step(): SimulationStep {
    this.stepCount++;
    const currentTime = this.stepCount;

    // Each node attempts to forward its stored bundles
    const allForwarded: Array<{ bundle: DTNBundle; nextHop: string }> = [];
    for (const node of this.nodes.values()) {
      const forwarded = node.forward(currentTime);
      allForwarded.push(...forwarded);
    }

    // Deliver forwarded bundles to next-hop nodes
    for (const { bundle, nextHop } of allForwarded) {
      const nextNode = this.nodes.get(nextHop);
      if (nextNode) {
        nextNode.receive(bundle);
      }
    }

    // Compute step metrics
    const delivered = this.allBundles.filter((b) => b.status === 'DELIVERED').length;
    const expired = this.allBundles.filter((b) => b.status === 'EXPIRED').length;
    const inTransit = this.allBundles.filter((b) => b.status === 'IN_TRANSIT').length;
    const stored = this.allBundles.filter((b) => b.status === 'STORED').length;
    const occludedNodes = Array.from(this.nodes.entries())
      .filter(([, n]) => n.getTelemetry().currentlyOccluded)
      .map(([id]) => id);

    const stepResult: SimulationStep = {
      step: this.stepCount,
      time: currentTime,
      bundlesCreated: this.allBundles.length,
      bundlesDelivered: delivered,
      bundlesExpired: expired,
      bundlesInTransit: inTransit,
      bundlesStored: stored,
      occludedNodes,
      deliveryRate: this.allBundles.length > 0 ? delivered / this.allBundles.length : 0,
    };

    this.history.push(stepResult);
    return stepResult;
  }

  /** Run N simulation steps */
  run(steps: number): SimulationStep[] {
    const results: SimulationStep[] = [];
    for (let i = 0; i < steps; i++) {
      results.push(this.step());
    }
    return results;
  }

  /** Get full simulation history */
  getHistory(): SimulationStep[] {
    return [...this.history];
  }

  /** Get per-node telemetry */
  getNodeTelemetry(): RelayTelemetry[] {
    return Array.from(this.nodes.values()).map((n) => n.getTelemetry());
  }

  /** Compare TCP vs DTN survival probability */
  static survivalComparison(
    occlusionProbability: number,
    steps: number
  ): { tcp: number; dtn: number; advantage: string } {
    const tcp = Math.pow(1 - occlusionProbability, steps);
    const dtn = 1 - Math.pow(occlusionProbability, steps);
    const ratio = dtn / Math.max(tcp, 1e-10);
    return {
      tcp: Math.round(tcp * 100000) / 100000,
      dtn: Math.round(dtn * 100000) / 100000,
      advantage: `DTN is ${ratio.toFixed(1)}x more reliable than TCP`,
    };
  }
}

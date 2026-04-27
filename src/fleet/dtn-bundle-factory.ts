/**
 * @file dtn-bundle-factory.ts
 * @module fleet/dtn-bundle-factory
 * @layer L7 (Store-and-Forward), L11 (Temporal Distance), L13 (Risk Decision)
 * @component DTN Bundle Factory — Fleet-Integrated Bundle Production
 * @version 1.0.0
 *
 * Higher-level factory that sits between the fleet task system and the
 * DTN protocol layer. Converts fleet tasks into routable bundles,
 * manages the 14-layer pipeline as a DTN network, handles fragmentation/
 * reassembly, FEC recovery, and batch operations.
 *
 * The raw DTN primitives (dtn-bundle.ts) are the envelope and post office.
 * This factory is the mail room — it decides WHAT gets packed, WHERE it
 * goes, and HOW to recover when things go dark.
 *
 * @axiom Composition — Factory composes task→bundle→route→deliver pipeline
 * @axiom Causality — Temporal ordering enforced across bundle batches
 * @axiom Unitarity — Fragment count preserved through reassembly
 */

import type { FleetTask, GovernanceTier, TaskPriority } from './types.js';
import type { MessagePriority } from './crawl-message-bus.js';
import {
  BundleTongue,
  DTNBundle,
  DTNNetworkSimulator,
  RelayTelemetry,
  createBundle,
} from './dtn-bundle.js';

// ──────────────── Constants ────────────────

/** Map fleet GovernanceTier to DTN BundleTongue */
const TIER_TO_TONGUE: Record<GovernanceTier, BundleTongue> = {
  KO: 'KO',
  AV: 'AV',
  RU: 'RU',
  CA: 'CA',
  UM: 'UM',
  DR: 'DR',
};

/** Map fleet TaskPriority to DTN MessagePriority */
const PRIORITY_MAP: Record<TaskPriority, MessagePriority> = {
  critical: 'critical',
  high: 'high',
  medium: 'normal',
  low: 'low',
};

/** Default fragment size (characters of serialized payload) */
const DEFAULT_FRAGMENT_SIZE = 4096;

/** 14-layer pipeline node IDs */
const PIPELINE_LAYERS = Array.from({ length: 14 }, (_, i) => `L${i + 1}`);

// ──────────────── Fragment Reassembly ────────────────

/** Tracks fragments for reassembly */
interface FragmentTracker {
  parentId: string;
  totalSize: number;
  received: Map<number, DTNBundle>;
  expectedCount: number;
  createdAt: number;
}

/**
 * FragmentAssembler — collects fragments and reassembles complete bundles.
 *
 * When a payload exceeds the fragment threshold, the factory splits it
 * into numbered fragments. The assembler collects them (potentially
 * out of order, across different relay paths) and reconstructs the
 * original when all fragments arrive.
 *
 * A2: Unitarity — fragment count in equals fragment count out.
 */
export class FragmentAssembler {
  private trackers: Map<string, FragmentTracker> = new Map();
  private completed: Map<string, unknown> = new Map();
  private readonly ttlMs: number;

  constructor(ttlMs: number = 60_000) {
    this.ttlMs = ttlMs;
  }

  /** Register a fragment. Returns the reassembled payload if complete. */
  addFragment(bundle: DTNBundle): unknown | undefined {
    const frag = bundle.fragment;
    if (!frag) return bundle.payload; // Not a fragment — return as-is

    let tracker = this.trackers.get(frag.parentId);
    if (!tracker) {
      tracker = {
        parentId: frag.parentId,
        totalSize: frag.totalSize,
        received: new Map(),
        // Unknown count until we see isLast — set to Infinity as sentinel
        expectedCount: Infinity,
        createdAt: Date.now(),
      };
      this.trackers.set(frag.parentId, tracker);
    }

    tracker.received.set(frag.offset, bundle);

    // Once we see the last fragment, we know the total count
    if (frag.isLast) {
      tracker.expectedCount = frag.offset + 1;
    }

    if (tracker.received.size >= tracker.expectedCount) {
      // Reassemble in order
      const sorted = Array.from(tracker.received.entries())
        .sort(([a], [b]) => a - b)
        .map(([, b]) => b);

      const payloadChunks = sorted.map((b) =>
        typeof b.payload === 'string' ? b.payload : JSON.stringify(b.payload)
      );
      const reassembled = payloadChunks.join('');

      try {
        const parsed = JSON.parse(reassembled);
        this.completed.set(frag.parentId, parsed);
        this.trackers.delete(frag.parentId);
        return parsed;
      } catch {
        // Payload was a raw string, not JSON
        this.completed.set(frag.parentId, reassembled);
        this.trackers.delete(frag.parentId);
        return reassembled;
      }
    }

    return undefined; // Still waiting for more fragments
  }

  /** Evict stale incomplete fragment sets */
  evictStale(): number {
    const now = Date.now();
    let evicted = 0;
    for (const [id, tracker] of this.trackers) {
      if (now - tracker.createdAt > this.ttlMs) {
        this.trackers.delete(id);
        evicted++;
      }
    }
    return evicted;
  }

  /** How many fragment sets are in progress */
  get pendingCount(): number {
    return this.trackers.size;
  }

  /** How many reassemblies completed */
  get completedCount(): number {
    return this.completed.size;
  }
}

// ──────────────── FEC Recovery ────────────────

/**
 * Attempt FEC recovery on a corrupted bundle using its redundant tongue encodings.
 *
 * Each bundle carries 6 FEC blocks (one per tongue). If the primary payload
 * is corrupted, we check each FEC block's integrity hash against its encoding.
 * The first intact block provides the recovery payload.
 *
 * A4: Symmetry — all 6 tongue encodings are equivalent representations.
 */
export function attemptFECRecovery(bundle: DTNBundle): {
  recovered: boolean;
  usedTongue?: BundleTongue;
  payload?: string;
} {
  for (const block of bundle.fecBlocks) {
    const recomputed = simpleHash(`${block.tongue}:${extractPayloadFromEncoding(block.encoding)}`);
    if (recomputed === block.hash) {
      return {
        recovered: true,
        usedTongue: block.tongue,
        payload: extractPayloadFromEncoding(block.encoding),
      };
    }
  }
  return { recovered: false };
}

/** Extract the raw payload portion from an FEC encoding string */
function extractPayloadFromEncoding(encoding: string): string {
  // FEC encoding format: "[TONGUE:weight] payload..."
  const bracketEnd = encoding.indexOf('] ');
  return bracketEnd >= 0 ? encoding.substring(bracketEnd + 2) : encoding;
}

/** Simple string hash (same as dtn-bundle.ts for consistency) */
function simpleHash(s: string): string {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h).toString(16).padStart(8, '0');
}

// ──────────────── Pipeline Network ────────────────

/** Pipeline network configuration */
export interface PipelineNetworkConfig {
  /** Store capacity per layer node (default: 500) */
  storeCapacity?: number;
  /** Default contact window bandwidth (bundles/step) (default: 10) */
  bandwidth?: number;
  /** Whether to create skip connections (L1→L5, L5→L12, etc.) (default: true) */
  skipConnections?: boolean;
  /** Custom occlusion schedule: step → list of occluded layer numbers */
  occlusionSchedule?: Map<number, number[]>;
}

/**
 * Create a DTNNetworkSimulator pre-wired as the 14-layer SCBE pipeline.
 *
 * Each layer is a relay node. Contact windows connect consecutive layers
 * (L1→L2→...→L14) plus optional skip connections for priority bundles.
 * Occlusion can be scheduled to simulate context blackouts at specific layers.
 */
export function createPipelineNetwork(config: PipelineNetworkConfig = {}): DTNNetworkSimulator {
  const { storeCapacity = 500, bandwidth = 10, skipConnections = true } = config;

  const sim = new DTNNetworkSimulator();

  // Create all 14 pipeline layers
  for (const layer of PIPELINE_LAYERS) {
    sim.addNode(layer, storeCapacity);
  }

  // Sequential contact windows (always open, high bandwidth)
  for (let i = 0; i < PIPELINE_LAYERS.length - 1; i++) {
    sim.addContactWindow(
      PIPELINE_LAYERS[i],
      PIPELINE_LAYERS[i + 1],
      1,
      10000, // Open for 10000 steps
      bandwidth
    );
  }

  // Skip connections for priority routing
  if (skipConnections) {
    // L1 → L5 (fast-track past initial transforms for critical bundles)
    sim.addContactWindow('L1', 'L5', 1, 10000, Math.ceil(bandwidth / 2));
    // L5 → L12 (skip mid-pipeline to harmonic wall for urgent governance)
    sim.addContactWindow('L5', 'L12', 1, 10000, Math.ceil(bandwidth / 3));
    // L1 → L13 (emergency escalation — direct to risk decision)
    sim.addContactWindow('L1', 'L13', 1, 10000, 1); // Very low bandwidth — emergency only
    // L8 → L13 (Hamiltonian to risk decision shortcut)
    sim.addContactWindow('L8', 'L13', 1, 10000, Math.ceil(bandwidth / 2));
  }

  return sim;
}

// ──────────────── Bundle Factory ────────────────

/** Factory configuration */
export interface BundleFactoryConfig {
  /** Max payload size before fragmentation (chars) */
  fragmentThreshold?: number;
  /** Default bundle lifetime in steps */
  defaultLifetime?: number;
  /** Default hyperbolic distance for governance scoring */
  defaultHyperbolicDistance?: number;
  /** Pipeline network config */
  pipeline?: PipelineNetworkConfig;
}

/** Result of a factory bundle operation */
export interface BundleFactoryResult {
  /** The produced bundles (may be multiple if fragmented) */
  bundles: DTNBundle[];
  /** Whether the payload was fragmented */
  fragmented: boolean;
  /** Fragment count (1 if not fragmented) */
  fragmentCount: number;
  /** Governance score assigned */
  governanceScore: number;
  /** Assigned tongue */
  tongue: BundleTongue;
  /** Route plan: which layers the bundle targets */
  route: string[];
}

/** Batch production result */
export interface BatchResult {
  /** Total bundles produced */
  totalBundles: number;
  /** Per-task results */
  results: Map<string, BundleFactoryResult>;
  /** Timestamp */
  timestamp: number;
  /** Any tasks that failed to convert */
  failures: Array<{ taskId: string; reason: string }>;
}

/** Delivery report after simulation */
export interface DeliveryReport {
  /** Bundles that reached their destination */
  delivered: DTNBundle[];
  /** Bundles still in transit or stored */
  pending: DTNBundle[];
  /** Bundles that expired */
  expired: DTNBundle[];
  /** Bundles that were corrupted (FEC recovery attempted) */
  corrupted: Array<{ bundle: DTNBundle; recovered: boolean; recoveryTongue?: BundleTongue }>;
  /** Per-layer telemetry */
  layerTelemetry: RelayTelemetry[];
  /** Overall delivery rate */
  deliveryRate: number;
  /** Simulation steps run */
  steps: number;
}

/**
 * DTNBundleFactory — Fleet-integrated bundle production system.
 *
 * Converts fleet tasks into DTN bundles, manages the 14-layer pipeline
 * as a delay-tolerant network, handles fragmentation/reassembly, and
 * provides batch operations for fleet-wide bundle routing.
 *
 * Usage:
 *   const factory = new DTNBundleFactory();
 *   const result = factory.fromTask(myFleetTask);
 *   factory.inject(result.bundles);
 *   const report = factory.simulate(20);
 */
export class DTNBundleFactory {
  private readonly config: Required<BundleFactoryConfig>;
  private readonly pipeline: DTNNetworkSimulator;
  private readonly assembler: FragmentAssembler;
  private readonly allBundles: DTNBundle[] = [];
  private batchCounter = 0;

  constructor(config: BundleFactoryConfig = {}) {
    this.config = {
      fragmentThreshold: config.fragmentThreshold ?? DEFAULT_FRAGMENT_SIZE,
      defaultLifetime: config.defaultLifetime ?? 20,
      defaultHyperbolicDistance: config.defaultHyperbolicDistance ?? 0.1,
      pipeline: config.pipeline ?? {},
    };
    this.pipeline = createPipelineNetwork(this.config.pipeline);
    this.assembler = new FragmentAssembler();
  }

  // ──── Single Task → Bundle(s) ────

  /**
   * Convert a FleetTask into one or more DTN bundles.
   *
   * Maps governance tier → tongue, priority → message priority,
   * task input → payload. Fragments large payloads automatically.
   */
  fromTask(
    task: FleetTask,
    options: {
      /** Override destination (default: L13 for governance decision) */
      destination?: string;
      /** Override source (default: L1 for pipeline entry) */
      source?: string;
      /** Hyperbolic distance for governance scoring */
      hyperbolicDistance?: number;
      /** Perturbation density */
      perturbationDensity?: number;
      /** Additional assumptions */
      assumptions?: string[];
      /** Contingency plans */
      contingencies?: string[];
    } = {}
  ): BundleFactoryResult {
    const tongue = TIER_TO_TONGUE[task.requiredTier] ?? 'KO';
    const priority = PRIORITY_MAP[task.priority] ?? 'normal';
    const source = options.source ?? 'L1';
    const destination = options.destination ?? 'L13';
    const d_H = options.hyperbolicDistance ?? this.config.defaultHyperbolicDistance;
    const pd = options.perturbationDensity ?? 0.0;

    // Build assumptions from task context
    const assumptions = [
      `Task: ${task.name}`,
      `Tier: ${task.requiredTier}`,
      `MinTrust: ${task.minTrustScore}`,
      ...(options.assumptions ?? []),
    ];

    const contingencies = options.contingencies ?? [
      `Retry at L8 if Hamiltonian check fails`,
      `Escalate to L13 if trust below ${task.minTrustScore}`,
    ];

    const payloadStr = JSON.stringify(task.input);

    // Check if fragmentation needed
    if (payloadStr.length > this.config.fragmentThreshold) {
      return this.fragmentTask(
        task,
        source,
        destination,
        tongue,
        priority,
        d_H,
        pd,
        assumptions,
        contingencies
      );
    }

    // Single bundle
    const bundle = createBundle(source, destination, task.input, tongue, {
      assumptions,
      contingencies,
      lifetime: this.config.defaultLifetime,
      priority,
      hyperbolicDistance: d_H,
      perturbationDensity: pd,
      extensions: {
        taskId: task.id,
        taskName: task.name,
        requiredCapability: task.requiredCapability,
        batchId: undefined,
      },
    });

    const route = this.planRoute(source, destination, priority);

    return {
      bundles: [bundle],
      fragmented: false,
      fragmentCount: 1,
      governanceScore: bundle.governanceScore,
      tongue,
      route,
    };
  }

  /**
   * Create a bundle from raw payload (not tied to a fleet task).
   *
   * Useful for ad-hoc bundles: telemetry, governance alerts,
   * inter-agent messages, training signals.
   */
  create<T>(
    source: string,
    destination: string,
    payload: T,
    tongue: BundleTongue,
    options: {
      priority?: MessagePriority;
      assumptions?: string[];
      contingencies?: string[];
      lifetime?: number;
      hyperbolicDistance?: number;
      perturbationDensity?: number;
      extensions?: Record<string, unknown>;
    } = {}
  ): BundleFactoryResult {
    const bundle = createBundle(source, destination, payload, tongue, {
      ...options,
      lifetime: options.lifetime ?? this.config.defaultLifetime,
      hyperbolicDistance: options.hyperbolicDistance ?? this.config.defaultHyperbolicDistance,
    });

    const route = this.planRoute(source, destination, options.priority ?? 'normal');

    return {
      bundles: [bundle],
      fragmented: false,
      fragmentCount: 1,
      governanceScore: bundle.governanceScore,
      tongue,
      route,
    };
  }

  // ──── Batch Operations ────

  /**
   * Convert multiple fleet tasks into bundles in a single batch.
   *
   * All bundles in a batch share a batchId for correlation.
   * Tasks are sorted by priority — critical tasks get processed first.
   */
  fromTaskBatch(tasks: FleetTask[]): BatchResult {
    const batchId = `batch-${++this.batchCounter}-${Date.now().toString(36)}`;
    const results = new Map<string, BundleFactoryResult>();
    const failures: Array<{ taskId: string; reason: string }> = [];

    // Sort by priority (critical first)
    const priorityOrder: Record<TaskPriority, number> = {
      critical: 0,
      high: 1,
      medium: 2,
      low: 3,
    };
    const sorted = [...tasks].sort(
      (a, b) => (priorityOrder[a.priority] ?? 2) - (priorityOrder[b.priority] ?? 2)
    );

    for (const task of sorted) {
      try {
        const result = this.fromTask(task);
        // Tag all bundles with batch ID
        for (const bundle of result.bundles) {
          (bundle.extensions as Record<string, unknown>).batchId = batchId;
        }
        results.set(task.id, result);
      } catch (err) {
        failures.push({
          taskId: task.id,
          reason: err instanceof Error ? err.message : String(err),
        });
      }
    }

    let totalBundles = 0;
    for (const r of results.values()) {
      totalBundles += r.bundles.length;
    }

    return {
      totalBundles,
      results,
      timestamp: Date.now(),
      failures,
    };
  }

  // ──── Pipeline Injection & Simulation ────

  /**
   * Inject bundles into the 14-layer pipeline at their source layer.
   */
  inject(bundles: DTNBundle[]): number {
    let injected = 0;
    for (const bundle of bundles) {
      const source = bundle.sourceEndpoint;
      if (this.pipeline.inject(bundle, source)) {
        this.allBundles.push(bundle);
        injected++;
      }
    }
    return injected;
  }

  /**
   * Inject a BundleFactoryResult directly.
   */
  injectResult(result: BundleFactoryResult): number {
    return this.inject(result.bundles);
  }

  /**
   * Set occlusion on specific pipeline layers.
   * Simulates context blackouts (tool failures, prompt truncation, etc.)
   */
  occlude(layers: number[], occluded: boolean): void {
    for (const layer of layers) {
      if (layer >= 1 && layer <= 14) {
        this.pipeline.setOcclusion(`L${layer}`, occluded);
      }
    }
  }

  /**
   * Run the pipeline simulation for N steps and collect a delivery report.
   */
  simulate(steps: number): DeliveryReport {
    this.pipeline.run(steps);

    const delivered = this.allBundles.filter((b) => b.status === 'DELIVERED');
    const pending = this.allBundles.filter(
      (b) => b.status === 'IN_TRANSIT' || b.status === 'STORED'
    );
    const expired = this.allBundles.filter((b) => b.status === 'EXPIRED');
    const corrupted: DeliveryReport['corrupted'] = [];

    // Attempt FEC recovery on corrupted bundles
    for (const bundle of this.allBundles.filter((b) => b.status === 'CORRUPTED')) {
      const recovery = attemptFECRecovery(bundle);
      corrupted.push({
        bundle,
        recovered: recovery.recovered,
        recoveryTongue: recovery.usedTongue,
      });
    }

    // Reassemble delivered fragments
    for (const bundle of delivered) {
      if (bundle.fragment) {
        this.assembler.addFragment(bundle);
      }
    }

    return {
      delivered,
      pending,
      expired,
      corrupted,
      layerTelemetry: this.pipeline.getNodeTelemetry(),
      deliveryRate: this.allBundles.length > 0 ? delivered.length / this.allBundles.length : 0,
      steps,
    };
  }

  /**
   * Run a full pipeline pass: inject → simulate → report.
   * Convenience method for fire-and-forget bundle routing.
   */
  routeThrough(bundles: DTNBundle[], steps: number = 20): DeliveryReport {
    this.inject(bundles);
    return this.simulate(steps);
  }

  // ──── Telemetry ────

  /** Get the fragment assembler (for checking reassembly status) */
  getAssembler(): FragmentAssembler {
    return this.assembler;
  }

  /** Total bundles ever produced by this factory */
  get totalBundles(): number {
    return this.allBundles.length;
  }

  /** Get the underlying pipeline simulator */
  getPipeline(): DTNNetworkSimulator {
    return this.pipeline;
  }

  // ──── Private Methods ────

  /** Fragment a large task payload into multiple bundles */
  private fragmentTask(
    task: FleetTask,
    source: string,
    destination: string,
    tongue: BundleTongue,
    priority: MessagePriority,
    d_H: number,
    pd: number,
    assumptions: string[],
    contingencies: string[]
  ): BundleFactoryResult {
    const payloadStr = JSON.stringify(task.input);
    const chunks: string[] = [];

    for (let i = 0; i < payloadStr.length; i += this.config.fragmentThreshold) {
      chunks.push(payloadStr.substring(i, i + this.config.fragmentThreshold));
    }

    const parentId = `frag-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
    const bundles: DTNBundle[] = [];

    for (let i = 0; i < chunks.length; i++) {
      const bundle = createBundle(source, destination, chunks[i], tongue, {
        assumptions: i === 0 ? assumptions : [`Fragment ${i + 1}/${chunks.length}`],
        contingencies: i === 0 ? contingencies : [],
        lifetime: this.config.defaultLifetime,
        priority,
        hyperbolicDistance: d_H,
        perturbationDensity: pd,
        extensions: {
          taskId: task.id,
          taskName: task.name,
        },
      });

      // Set fragment metadata (cast to mutable for initialization)
      (bundle as { fragment: DTNBundle['fragment'] }).fragment = {
        parentId,
        offset: i,
        totalSize: chunks.length,
        isLast: i === chunks.length - 1,
      };

      bundles.push(bundle);
    }

    const route = this.planRoute(source, destination, priority);

    return {
      bundles,
      fragmented: true,
      fragmentCount: chunks.length,
      governanceScore: bundles[0]?.governanceScore ?? 0,
      tongue,
      route,
    };
  }

  /** Plan a route through the pipeline based on priority */
  private planRoute(source: string, destination: string, priority: MessagePriority): string[] {
    const srcIdx = this.layerIndex(source);
    const dstIdx = this.layerIndex(destination);

    if (srcIdx < 0 || dstIdx < 0 || srcIdx >= dstIdx) {
      return [source, destination];
    }

    // Critical bundles use skip connections
    if (priority === 'critical') {
      return this.criticalRoute(srcIdx, dstIdx);
    }

    // Normal bundles traverse sequentially
    const route: string[] = [];
    for (let i = srcIdx; i <= dstIdx; i++) {
      route.push(PIPELINE_LAYERS[i]);
    }
    return route;
  }

  /** Build a skip-connection route for critical bundles */
  private criticalRoute(srcIdx: number, dstIdx: number): string[] {
    const route: string[] = [PIPELINE_LAYERS[srcIdx]];

    // Skip connections: L1→L5, L5→L12, L8→L13
    let current = srcIdx;
    const skips: Array<[number, number]> = [
      [0, 4], // L1 → L5
      [4, 11], // L5 → L12
      [7, 12], // L8 → L13
      [0, 12], // L1 → L13 (emergency)
    ];

    while (current < dstIdx) {
      let jumped = false;
      for (const [from, to] of skips) {
        if (current === from && to <= dstIdx) {
          current = to;
          route.push(PIPELINE_LAYERS[current]);
          jumped = true;
          break;
        }
      }
      if (!jumped) {
        current++;
        if (current <= dstIdx) {
          route.push(PIPELINE_LAYERS[current]);
        }
      }
    }

    return route;
  }

  /** Convert layer ID (e.g. "L5") to 0-based index */
  private layerIndex(layerId: string): number {
    const match = layerId.match(/^L(\d+)$/);
    if (!match) return -1;
    const num = parseInt(match[1], 10);
    return num >= 1 && num <= 14 ? num - 1 : -1;
  }
}

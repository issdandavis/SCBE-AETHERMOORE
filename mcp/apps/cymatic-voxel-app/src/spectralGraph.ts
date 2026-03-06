export type Mode = "default" | "quasi" | "dense";

export type AuthorityLevel = "public" | "internal" | "restricted" | "sealed";

export type IntentTag =
  | "observe"
  | "route"
  | "govern"
  | "archive"
  | "publish"
  | "contain"
  | "research";

export interface BuildOptions {
  atUnixMs?: number;
  windowMs?: number;
  baseUnixMs?: number;
}

export interface SpectralNode {
  id: string;
  label: string;
  x: number;
  y: number;
  isMerge: boolean;
}

export interface SpectralEdge {
  from: string;
  to: string;
}

export interface Flow {
  id: string;
  sequence: number;
  wavelengthNm: number;
  authority: AuthorityLevel;
  intentTag: IntentTag;
  intentVector: [number, number, number];
  path: string[];
}

export interface Voxel {
  id: string;
  flowId: string;
  nodeId: string;
  x: number;
  y: number;
  z: number;
  phase: number;
  intensity: number;
  wavelengthNm: number;
  authority: AuthorityLevel;
  authoritySignature: string;
  intentTag: IntentTag;
  intentVector: [number, number, number];
  modeN: number;
  modeM: number;
  chladniValue: number;
  createdAtUnixMs: number;
  updatedAtUnixMs: number;
  tIndex: number;
}

export interface Collision {
  type: "node_overlap" | "hyperbolic_proximity";
  flows: [string, string];
  detail: string;
}

export interface TemporalSlice {
  atUnixMs: number;
  windowMs: number;
  activeVoxelCount: number;
  activeCollisionCount: number;
  authorityDistribution: Record<AuthorityLevel, number>;
  intentDistribution: Partial<Record<IntentTag, number>>;
}

export interface LayoutResult {
  mode: Mode;
  thresholds: {
    spectralIsolation: number;
    hyperbolicMinSeparation: number;
  };
  dimensions: {
    explicit: ["x", "y", "z", "spectral", "authority", "intent"];
    implied: ["timestamp"];
  };
  nodes: SpectralNode[];
  edges: SpectralEdge[];
  flows: Flow[];
  collisions: Collision[];
  voxels: Voxel[];
  temporal: TemporalSlice;
  metrics: {
    collisionCount: number;
    safeFlowCount: number;
    mergeNodeCount: number;
    sealedVoxelCount: number;
    authorityDiversity: number;
    intentDiversity: number;
  };
}

const PI = Math.PI;
const PHI = (1 + Math.sqrt(5)) / 2;
const TIME_STEP_MS = 45_000;

const AUTHORITY_LEVELS: AuthorityLevel[] = ["public", "internal", "restricted", "sealed"];
const INTENT_TAGS: IntentTag[] = ["observe", "route", "govern", "archive", "publish", "contain", "research"];
const AUTHORITY_WEIGHTS: Record<AuthorityLevel, number> = {
  public: 0.85,
  internal: 1.0,
  restricted: 1.1,
  sealed: 1.2,
};

const BASE_NODES: SpectralNode[] = [
  { id: "ingress_a", label: "Ingress A", x: -0.68, y: -0.24, isMerge: false },
  { id: "ingress_b", label: "Ingress B", x: -0.68, y: 0.24, isMerge: false },
  { id: "router_a", label: "Router A", x: -0.24, y: -0.26, isMerge: false },
  { id: "router_b", label: "Router B", x: -0.24, y: 0.26, isMerge: false },
  { id: "merge_hub", label: "Merge Hub", x: 0.0, y: 0.0, isMerge: true },
  { id: "audit", label: "Audit", x: 0.3, y: -0.18, isMerge: false },
  { id: "archive", label: "Archive", x: 0.62, y: 0.24, isMerge: false },
  { id: "publish", label: "Publish", x: 0.62, y: -0.24, isMerge: false },
  { id: "near_merge", label: "Near Merge Lane", x: 0.08, y: 0.08, isMerge: false },
];

const BASE_EDGES: SpectralEdge[] = [
  { from: "ingress_a", to: "router_a" },
  { from: "ingress_b", to: "router_b" },
  { from: "router_a", to: "merge_hub" },
  { from: "router_b", to: "merge_hub" },
  { from: "merge_hub", to: "audit" },
  { from: "merge_hub", to: "archive" },
  { from: "merge_hub", to: "publish" },
  { from: "router_a", to: "near_merge" },
  { from: "near_merge", to: "publish" },
  { from: "near_merge", to: "archive" },
  { from: "audit", to: "publish" },
];

const SPECTRAL_BANDS = [400, 455, 500, 540, 580, 617, 700];

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function hash32(input: string): number {
  let hash = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function nodeById(nodes: SpectralNode[], id: string): SpectralNode {
  const node = nodes.find((n) => n.id === id);
  if (!node) {
    throw new Error(`Unknown node: ${id}`);
  }
  return node;
}

function edgesToSet(edges: SpectralEdge[]): Set<string> {
  return new Set(edges.map((e) => `${e.from}->${e.to}`));
}

export function poincareDistance(a: Pick<SpectralNode, "x" | "y">, b: Pick<SpectralNode, "x" | "y">): number {
  const na2 = a.x * a.x + a.y * a.y;
  const nb2 = b.x * b.x + b.y * b.y;
  if (na2 >= 1 || nb2 >= 1) {
    throw new Error("Points must be strictly inside the unit ball");
  }

  const dx = a.x - b.x;
  const dy = a.y - b.y;
  const euclidSq = dx * dx + dy * dy;
  const denom = (1 - na2) * (1 - nb2);
  const arg = Math.max(1, 1 + (2 * euclidSq) / denom);
  return Math.acosh(arg);
}

function normalizedSpectralDistance(aNm: number, bNm: number): number {
  return Math.abs(aNm - bNm) / 400;
}

function deterministicPhase(flowId: string, depth: number): number {
  const seed = [...`${flowId}:${depth}`].reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  return ((seed % 360) / 180) * PI;
}

function deterministicIntentVector(flowId: string, authority: AuthorityLevel, intent: IntentTag): [number, number, number] {
  const h = hash32(`${flowId}|${authority}|${intent}`);
  const x = (((h & 0xff) / 255) * 2 - 1);
  const y = ((((h >> 8) & 0xff) / 255) * 2 - 1);
  const z = ((((h >> 16) & 0xff) / 255) * 2 - 1);
  return [Number(x.toFixed(4)), Number(y.toFixed(4)), Number(z.toFixed(4))];
}

function generateFlowPath(index: number, mode: Mode): string[] {
  if (mode === "dense") {
    if (index % 2 === 0) {
      return ["ingress_a", "router_a", "merge_hub", "publish"];
    }
    return ["ingress_b", "router_b", "merge_hub", "archive"];
  }

  if (mode === "quasi") {
    if (index % 3 === 0) {
      return ["ingress_a", "router_a", "near_merge", "publish"];
    }
    if (index % 3 === 1) {
      return ["ingress_b", "router_b", "merge_hub", "archive"];
    }
    return ["ingress_a", "router_a", "merge_hub", "audit", "publish"];
  }

  if (index % 3 === 0) {
    return ["ingress_a", "router_a", "merge_hub", "publish"];
  }
  if (index % 3 === 1) {
    return ["ingress_b", "router_b", "merge_hub", "archive"];
  }
  return ["ingress_a", "router_a", "near_merge", "archive"];
}

function validatePath(path: string[], edgeSet: Set<string>): void {
  for (let i = 0; i < path.length - 1; i += 1) {
    if (!edgeSet.has(`${path[i]}->${path[i + 1]}`)) {
      throw new Error(`Disconnected path at ${path[i]} -> ${path[i + 1]}`);
    }
  }
}

function generateAuthority(index: number, mode: Mode): AuthorityLevel {
  if (mode === "dense") {
    return AUTHORITY_LEVELS[index % 3] === "sealed" ? "restricted" : AUTHORITY_LEVELS[index % 3];
  }
  if (mode === "quasi" && index % 5 === 0) {
    return "sealed";
  }
  return AUTHORITY_LEVELS[index % AUTHORITY_LEVELS.length];
}

function generateIntent(index: number, mode: Mode): IntentTag {
  if (mode === "quasi") {
    return INTENT_TAGS[(index * 2 + 1) % INTENT_TAGS.length];
  }
  return INTENT_TAGS[index % INTENT_TAGS.length];
}

function generateFlows(flowCount: number, mode: Mode, edgeSet: Set<string>): Flow[] {
  const flows: Flow[] = [];
  for (let i = 0; i < flowCount; i += 1) {
    const base = SPECTRAL_BANDS[i % SPECTRAL_BANDS.length];
    const phiOffset = ((i * 13) % 17) - 8;
    const wavelengthNm = Math.max(380, Math.min(780, base + phiOffset));
    const path = generateFlowPath(i, mode);
    validatePath(path, edgeSet);

    const authority = generateAuthority(i, mode);
    const intentTag = generateIntent(i, mode);

    flows.push({
      id: `flow_${i + 1}`,
      sequence: i,
      wavelengthNm,
      authority,
      intentTag,
      intentVector: deterministicIntentVector(`flow_${i + 1}`, authority, intentTag),
      path,
    });
  }
  return flows;
}

function detectCollisions(
  flows: Flow[],
  nodes: SpectralNode[],
  spectralIsolation: number,
  hyperbolicMinSeparation: number,
): Collision[] {
  const collisions: Collision[] = [];
  const seen = new Set<string>();

  for (let i = 0; i < flows.length; i += 1) {
    for (let j = i + 1; j < flows.length; j += 1) {
      const a = flows[i];
      const b = flows[j];
      const spectral = normalizedSpectralDistance(a.wavelengthNm, b.wavelengthNm);
      if (spectral >= spectralIsolation) {
        continue;
      }

      const depth = Math.min(a.path.length, b.path.length);
      for (let d = 0; d < depth; d += 1) {
        const nodeA = nodeById(nodes, a.path[d]);
        const nodeB = nodeById(nodes, b.path[d]);
        const pairKey = `${a.id}|${b.id}|${d}`;

        if (nodeA.id === nodeB.id && !nodeA.isMerge) {
          if (!seen.has(`node:${pairKey}`)) {
            seen.add(`node:${pairKey}`);
            collisions.push({
              type: "node_overlap",
              flows: [a.id, b.id],
              detail: `Depth ${d} overlap at non-merge node ${nodeA.id}`,
            });
          }
          continue;
        }

        if (nodeA.id === nodeB.id && nodeA.isMerge) {
          continue;
        }

        const hd = poincareDistance(nodeA, nodeB);
        if (hd < hyperbolicMinSeparation && !seen.has(`hyp:${pairKey}`)) {
          seen.add(`hyp:${pairKey}`);
          collisions.push({
            type: "hyperbolic_proximity",
            flows: [a.id, b.id],
            detail: `Depth ${d} near-collision dH=${hd.toFixed(3)} (${nodeA.id} vs ${nodeB.id})`,
          });
        }
      }
    }
  }

  return collisions;
}

function authoritySignature(flow: Flow, nodeId: string, depth: number): string {
  const h = hash32(`${flow.id}|${flow.authority}|${flow.intentTag}|${nodeId}|${depth}`);
  return `sig_${h.toString(16).padStart(8, "0")}`;
}

function chladniValueAt(node: SpectralNode, n: number, m: number): number {
  const x = (node.x + 1) * 0.5;
  const y = (node.y + 1) * 0.5;
  const v = Math.cos(n * PI * x) * Math.cos(m * PI * y) - Math.cos(m * PI * x) * Math.cos(n * PI * y);
  return Number(v.toFixed(6));
}

function createVoxels(
  flows: Flow[],
  nodes: SpectralNode[],
  baseUnixMs: number,
): Voxel[] {
  const voxels: Voxel[] = [];

  for (const flow of flows) {
    for (let depth = 0; depth < flow.path.length; depth += 1) {
      const node = nodeById(nodes, flow.path[depth]);
      const phase = deterministicPhase(flow.id, depth);

      const authWeight = AUTHORITY_WEIGHTS[flow.authority];
      const intentWave = 0.85 + 0.15 * Math.cos(PHI * (depth + 1));
      const rawIntensity = (0.5 + 0.5 * Math.cos(phase)) * authWeight * intentWave;
      const intensity = Number(clamp(rawIntensity, 0, 1).toFixed(4));

      const modeN = (flow.sequence % 7) + 2;
      const modeM = ((flow.sequence + depth) % 11) + 3;
      const chladniValue = chladniValueAt(node, modeN, modeM);

      const createdAtUnixMs =
        baseUnixMs -
        (flow.sequence * 17 + (flow.path.length - depth) * 3) * TIME_STEP_MS;
      const updatedAtUnixMs = createdAtUnixMs + TIME_STEP_MS * 2 + depth * 1111;
      const tIndex = Math.floor((updatedAtUnixMs - (baseUnixMs - 12 * TIME_STEP_MS)) / TIME_STEP_MS);

      voxels.push({
        id: `${flow.id}_${node.id}_${depth}`,
        flowId: flow.id,
        nodeId: node.id,
        x: node.x,
        y: node.y,
        z: depth,
        phase,
        intensity,
        wavelengthNm: flow.wavelengthNm,
        authority: flow.authority,
        authoritySignature: authoritySignature(flow, node.id, depth),
        intentTag: flow.intentTag,
        intentVector: flow.intentVector,
        modeN,
        modeM,
        chladniValue,
        createdAtUnixMs,
        updatedAtUnixMs,
        tIndex,
      });
    }
  }

  return voxels;
}

function buildTemporalSlice(
  voxels: Voxel[],
  collisions: Collision[],
  atUnixMs: number,
  windowMs: number,
): TemporalSlice {
  const half = windowMs / 2;
  const active = voxels.filter(
    (v) =>
      Math.abs(v.updatedAtUnixMs - atUnixMs) <= half ||
      (v.createdAtUnixMs <= atUnixMs && atUnixMs <= v.updatedAtUnixMs + half),
  );

  const activeFlowIds = new Set(active.map((v) => v.flowId));

  const authorityDistribution: Record<AuthorityLevel, number> = {
    public: 0,
    internal: 0,
    restricted: 0,
    sealed: 0,
  };
  const intentDistribution: Partial<Record<IntentTag, number>> = {};

  for (const voxel of active) {
    authorityDistribution[voxel.authority] += 1;
    intentDistribution[voxel.intentTag] = (intentDistribution[voxel.intentTag] ?? 0) + 1;
  }

  const activeCollisionCount = collisions.filter(
    (c) => activeFlowIds.has(c.flows[0]) && activeFlowIds.has(c.flows[1]),
  ).length;

  return {
    atUnixMs,
    windowMs,
    activeVoxelCount: active.length,
    activeCollisionCount,
    authorityDistribution,
    intentDistribution,
  };
}

export function wavelengthToRgb(wl: number): [number, number, number] {
  let r = 0;
  let g = 0;
  let b = 0;

  if (wl >= 380 && wl < 440) {
    r = (440 - wl) / (440 - 380);
    b = 1;
  } else if (wl >= 440 && wl < 490) {
    g = (wl - 440) / (490 - 440);
    b = 1;
  } else if (wl >= 490 && wl < 510) {
    g = 1;
    b = (510 - wl) / (510 - 490);
  } else if (wl >= 510 && wl < 580) {
    r = (wl - 510) / (580 - 510);
    g = 1;
  } else if (wl >= 580 && wl < 645) {
    r = 1;
    g = (645 - wl) / (645 - 580);
  } else if (wl >= 645 && wl <= 780) {
    r = 1;
  }

  const factor =
    wl < 420 ? 0.3 + (0.7 * (wl - 380)) / (420 - 380)
      : wl > 645 ? 0.3 + (0.7 * (780 - wl)) / (780 - 645)
        : 1;
  return [
    Math.round(255 * r * factor),
    Math.round(255 * g * factor),
    Math.round(255 * b * factor),
  ];
}

export function buildCymaticVoxelLayout(
  flowCount: number,
  mode: Mode = "default",
  options: BuildOptions = {},
): LayoutResult {
  const boundedFlowCount = Math.max(1, Math.min(32, Math.floor(flowCount)));
  const edges = BASE_EDGES.slice();
  const nodes = BASE_NODES.slice();
  const edgeSet = edgesToSet(edges);

  const spectralIsolation = mode === "dense" ? 0.08 : 0.1;
  const hyperbolicMinSeparation = mode === "quasi" ? 0.25 : 0.3;

  const flows = generateFlows(boundedFlowCount, mode, edgeSet);
  const collisions = detectCollisions(flows, nodes, spectralIsolation, hyperbolicMinSeparation);

  const baseUnixMs =
    typeof options.baseUnixMs === "number" && Number.isFinite(options.baseUnixMs)
      ? options.baseUnixMs
      : Date.now();
  const windowMs = clamp(
    typeof options.windowMs === "number" && Number.isFinite(options.windowMs) ? options.windowMs : 60_000,
    1_000,
    86_400_000,
  );
  const atUnixMs =
    typeof options.atUnixMs === "number" && Number.isFinite(options.atUnixMs)
      ? options.atUnixMs
      : baseUnixMs;

  const voxels = createVoxels(flows, nodes, baseUnixMs);
  const temporal = buildTemporalSlice(voxels, collisions, atUnixMs, windowMs);

  const collidedFlows = new Set(collisions.flatMap((c) => c.flows));
  const authorityDiversity = new Set(voxels.map((v) => v.authority)).size;
  const intentDiversity = new Set(voxels.map((v) => v.intentTag)).size;

  return {
    mode,
    thresholds: {
      spectralIsolation,
      hyperbolicMinSeparation,
    },
    dimensions: {
      explicit: ["x", "y", "z", "spectral", "authority", "intent"],
      implied: ["timestamp"],
    },
    nodes,
    edges,
    flows,
    collisions,
    voxels,
    temporal,
    metrics: {
      collisionCount: collisions.length,
      safeFlowCount: flows.length - collidedFlows.size,
      mergeNodeCount: nodes.filter((n) => n.isMerge).length,
      sealedVoxelCount: voxels.filter((v) => v.authority === "sealed").length,
      authorityDiversity,
      intentDiversity,
    },
  };
}

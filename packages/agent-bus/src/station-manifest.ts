/**
 * @file station-manifest.ts
 * @module agent-bus/station-manifest
 * @layer Cross-layer shared station state
 * @component StationManifest — queryable map of zones, districts, agents, and transit
 *
 * The station manifest is the shared spatial contract that lets every module
 * answer "where am I?" and "how do I get there?" without coupling to each other.
 * It ties together:
 *   BoardFields (domain terrain) via zone domains
 *   StarPath (routing graph) via transit nodes
 *   LifeLedger (agent identity) via docking ports
 *   ReactionChain (autopilot) via cultural protocols
 *   Hermes (route classification) via zone districts
 *
 * All state updates are immutable — functions return a new StationManifest.
 * The manifest is JSON-serializable and can be checkpointed between runs.
 *
 * Architecture lane reference:
 *   VI       — narrow access, no autonomy
 *   Agent    — bounded autonomy within permitted zones
 *   Keeper   — maintenance-only, repair authority
 *   Squad    — quorum decision, shared zones
 *   Station  — shared state layer (this module)
 *   Core     — governance-protected primitives
 */

// ─── Primitive types ──────────────────────────────────────────────────────────

export type District =
  | 'writing'
  | 'code'
  | 'browser'
  | 'security'
  | 'research'
  | 'video'
  | 'commerce'
  | 'deployment';

export type ZoneState = 'active' | 'standby' | 'maintenance' | 'quarantined' | 'offline';

export type TransitMode = 'direct' | 'relay' | 'secure-channel' | 'broadcast';

export type AgentLane = 'vi' | 'agent' | 'keeper' | 'squad' | 'station' | 'core';

export type ZoneClearance = 'none' | 'read_only' | 'write' | 'execute' | 'admin';

export type PortProtocol = 'agent-pad' | 'artifact-ship' | 'data-transfer' | 'pr-dock';

export type HealthColor = 'green' | 'amber' | 'red' | 'critical';

// A4: gauge invariance — clearance forms a total order
const CLEARANCE_RANK: Record<ZoneClearance, number> = {
  none: 0,
  read_only: 1,
  write: 2,
  execute: 3,
  admin: 4,
};

export const ALL_DISTRICTS: District[] = [
  'writing',
  'code',
  'browser',
  'security',
  'research',
  'video',
  'commerce',
  'deployment',
];

// ─── Gravity frames ───────────────────────────────────────────────────────────

/**
 * Local orientation in a zone. Governs how tools cost, permissions flow,
 * and how important depth affects decision weight.
 */
export interface GravityFrame {
  zone_id: string;
  /** 0–1: higher = more security pressure toward zone center. */
  security_slope: number;
  /** Multiplier applied to tick cost for tools running here. */
  tool_cost_weight: number;
  /**
   * ascending  = clearance requirement increases toward zone center
   * descending = clearance requirement decreases toward zone center
   */
  permission_direction: 'ascending' | 'descending';
  /** 0–100: depth in the importance/priority stack. */
  importance_depth: number;
  /** Local rules overriding station defaults (informational). */
  coordinate_rules: string[];
}

export function defaultGravityFrame(zoneId: string): GravityFrame {
  return {
    zone_id: zoneId,
    security_slope: 0.2,
    tool_cost_weight: 1.0,
    permission_direction: 'ascending',
    importance_depth: 50,
    coordinate_rules: [],
  };
}

// ─── Cultural protocols ────────────────────────────────────────────────────────

/**
 * Per-district rules about command language, allowed agent lanes, and budgets.
 * The primary_tongue maps to the Sacred Tongue used for tokenization in this district.
 */
export interface CulturalProtocol {
  district: District;
  /** CLI prefix for commands in this district. */
  command_prefix: string;
  allowed_lanes: AgentLane[];
  /** Sacred Tongue: Kor'aelin | Avali | Runethic | Cassisivadan | Umbroth | Draumric */
  primary_tongue: string;
  /** Max tokens per operation in this district. */
  token_budget: number;
  blocked_actions: string[];
}

const DISTRICT_DEFAULTS: Record<
  District,
  Pick<CulturalProtocol, 'command_prefix' | 'allowed_lanes' | 'primary_tongue' | 'token_budget'>
> = {
  code: {
    command_prefix: 'scbe code',
    allowed_lanes: ['vi', 'agent', 'keeper'],
    primary_tongue: 'Cassisivadan',
    token_budget: 4096,
  },
  writing: {
    command_prefix: 'scbe write',
    allowed_lanes: ['vi', 'agent'],
    primary_tongue: 'Avali',
    token_budget: 8192,
  },
  browser: {
    command_prefix: 'scbe browse',
    allowed_lanes: ['agent', 'keeper'],
    primary_tongue: "Kor'aelin",
    token_budget: 2048,
  },
  security: {
    command_prefix: 'scbe sec',
    allowed_lanes: ['keeper', 'core'],
    primary_tongue: 'Umbroth',
    token_budget: 1024,
  },
  research: {
    command_prefix: 'scbe research',
    allowed_lanes: ['vi', 'agent', 'squad'],
    primary_tongue: 'Runethic',
    token_budget: 8192,
  },
  video: {
    command_prefix: 'scbe video',
    allowed_lanes: ['vi', 'agent'],
    primary_tongue: 'Avali',
    token_budget: 2048,
  },
  commerce: {
    command_prefix: 'scbe commerce',
    allowed_lanes: ['vi', 'agent'],
    primary_tongue: 'Cassisivadan',
    token_budget: 1024,
  },
  deployment: {
    command_prefix: 'scbe deploy',
    allowed_lanes: ['agent', 'keeper'],
    primary_tongue: 'Draumric',
    token_budget: 2048,
  },
};

export function defaultCulturalProtocol(district: District): CulturalProtocol {
  const d = DISTRICT_DEFAULTS[district];
  return {
    district,
    command_prefix: d.command_prefix,
    allowed_lanes: d.allowed_lanes,
    primary_tongue: d.primary_tongue,
    token_budget: d.token_budget,
    blocked_actions: [],
  };
}

// ─── Zone ─────────────────────────────────────────────────────────────────────

export interface StationZone {
  id: string;
  label: string;
  district: District;
  state: ZoneState;
  gravity: GravityFrame;
  /** Minimum clearance to enter this zone. */
  clearance: ZoneClearance;
  /** Max concurrent agents. */
  capacity: number;
  /** Agent IDs currently occupying this zone. */
  occupants: string[];
  /** IDs of zones directly connected. */
  linked_zones: string[];
  /** Polly Pad surface ID if this zone is backed by a pad. */
  pad_surface?: string;
  /** Last maintenance receipt ID. */
  audit_receipt?: string;
  /** ISO timestamp of last state change. */
  updated_at: string;
}

// ─── Transit ──────────────────────────────────────────────────────────────────

export interface TransitRoute {
  to: string;
  mode: TransitMode;
  cost: number;
}

export interface TransitNode {
  id: string;
  zone_id: string;
  label: string;
  routes: TransitRoute[];
}

// ─── Docking ──────────────────────────────────────────────────────────────────

export interface DockingPort {
  id: string;
  zone_id: string;
  protocol: PortProtocol;
  agent_id?: string;
  artifact_sha256?: string;
  docked_at?: string;
  receipt?: string;
}

// ─── Pad surface ──────────────────────────────────────────────────────────────

export interface PadSurface {
  pad_id: string;
  agent_id: string;
  district: District;
  last_seen: string;
  /** Tool names available on this pad. */
  inventory: string[];
  status_flags: string[];
}

// ─── Security boundary ────────────────────────────────────────────────────────

export interface SecurityBoundary {
  id: string;
  /** Zone IDs enclosed by this boundary. */
  zone_ids: string[];
  min_clearance: ZoneClearance;
  allowed_lanes: AgentLane[];
  breach_policy: 'quarantine' | 'escalate' | 'deny';
}

// ─── Station manifest ─────────────────────────────────────────────────────────

export interface StationManifest {
  schema_version: 'scbe_station_manifest_v1';
  station_id: string;
  created_at: string;
  updated_at: string;
  zones: Record<string, StationZone>;
  /** district → zone IDs in that district */
  districts: Partial<Record<District, string[]>>;
  /** zone_id → gravity frame (may override zone.gravity for external reads) */
  gravity_frames: Record<string, GravityFrame>;
  transit_nodes: Record<string, TransitNode>;
  docking_ports: Record<string, DockingPort>;
  cultural_protocols: Partial<Record<District, CulturalProtocol>>;
  pad_surfaces: Record<string, PadSurface>;
  security_boundaries: Record<string, SecurityBoundary>;
  /** Zone IDs not yet observed — fog of war. */
  fog_of_war: string[];
  /** Maintenance receipt IDs or paths. */
  audit_receipts: string[];
}

// ─── Station lifecycle ────────────────────────────────────────────────────────

export function createStation(
  stationId: string,
  opts: { districts?: District[]; now?: string } = {}
): StationManifest {
  const now = opts.now ?? new Date().toISOString();
  const districts = opts.districts ?? ALL_DISTRICTS;

  const cultural_protocols: Partial<Record<District, CulturalProtocol>> = {};
  for (const d of districts) {
    cultural_protocols[d] = defaultCulturalProtocol(d);
  }

  return {
    schema_version: 'scbe_station_manifest_v1',
    station_id: stationId,
    created_at: now,
    updated_at: now,
    zones: {},
    districts: {},
    gravity_frames: {},
    transit_nodes: {},
    docking_ports: {},
    cultural_protocols,
    pad_surfaces: {},
    security_boundaries: {},
    fog_of_war: [],
    audit_receipts: [],
  };
}

// ─── Zone operations ──────────────────────────────────────────────────────────

export function addZone(
  manifest: StationManifest,
  zone: StationZone,
  opts: { now?: string } = {}
): StationManifest {
  const now = opts.now ?? new Date().toISOString();
  const district = zone.district;
  const existing = manifest.districts[district] ?? [];
  const zones = { ...manifest.zones, [zone.id]: zone };
  const gravity_frames = {
    ...manifest.gravity_frames,
    [zone.id]: zone.gravity,
  };
  const newDistrictList = existing.includes(zone.id) ? existing : [...existing, zone.id];
  const districts = { ...manifest.districts, [district]: newDistrictList };

  // A new zone starts in fog of war if unknown
  const fog_of_war = manifest.fog_of_war.includes(zone.id)
    ? manifest.fog_of_war
    : [...manifest.fog_of_war, zone.id];

  return { ...manifest, zones, gravity_frames, districts, fog_of_war, updated_at: now };
}

export function removeZone(
  manifest: StationManifest,
  zoneId: string,
  opts: { now?: string } = {}
): StationManifest {
  const now = opts.now ?? new Date().toISOString();
  const zone = manifest.zones[zoneId];
  if (!zone) return manifest;

  const zones = { ...manifest.zones };
  delete zones[zoneId];

  const gravity_frames = { ...manifest.gravity_frames };
  delete gravity_frames[zoneId];

  const district = zone.district;
  const districts = { ...manifest.districts };
  if (districts[district]) {
    districts[district] = districts[district]!.filter((id) => id !== zoneId);
  }

  const fog_of_war = manifest.fog_of_war.filter((id) => id !== zoneId);

  return { ...manifest, zones, gravity_frames, districts, fog_of_war, updated_at: now };
}

export function updateZone(
  manifest: StationManifest,
  zone: StationZone,
  opts: { now?: string } = {}
): StationManifest {
  const now = opts.now ?? new Date().toISOString();
  if (!manifest.zones[zone.id]) return manifest;
  const zones = { ...manifest.zones, [zone.id]: zone };
  const gravity_frames = { ...manifest.gravity_frames, [zone.id]: zone.gravity };
  return { ...manifest, zones, gravity_frames, updated_at: now };
}

export function getZone(manifest: StationManifest, zoneId: string): StationZone | null {
  return manifest.zones[zoneId] ?? null;
}

export function observeZone(
  manifest: StationManifest,
  zoneId: string,
  opts: { now?: string } = {}
): StationManifest {
  const now = opts.now ?? new Date().toISOString();
  const fog_of_war = manifest.fog_of_war.filter((id) => id !== zoneId);
  return { ...manifest, fog_of_war, updated_at: now };
}

/** True if an agent with the given clearance is permitted to enter the zone. */
export function canEnterZone(zone: StationZone, agentClearance: ZoneClearance): boolean {
  if (zone.state === 'quarantined' || zone.state === 'offline') return false;
  if (zone.occupants.length >= zone.capacity) return false;
  return CLEARANCE_RANK[agentClearance] >= CLEARANCE_RANK[zone.clearance];
}

// ─── Gravity ──────────────────────────────────────────────────────────────────

export function resolveGravity(manifest: StationManifest, zoneId: string): GravityFrame | null {
  return manifest.gravity_frames[zoneId] ?? manifest.zones[zoneId]?.gravity ?? null;
}

// ─── Transit planning ─────────────────────────────────────────────────────────

export interface TransitHop {
  zone_id: string;
  node_id: string;
  mode: TransitMode;
  cost: number;
}

export interface TransitPlan {
  schema_version: 'scbe_transit_plan_v1';
  station_id: string;
  from_zone: string;
  to_zone: string;
  hops: TransitHop[];
  total_cost: number;
  blocked: boolean;
  block_reason?: string;
}

/**
 * Dijkstra over transit nodes to find the cheapest route between two zones.
 * Returns a blocked plan if no path exists.
 */
export function planTransit(
  manifest: StationManifest,
  fromZoneId: string,
  toZoneId: string
): TransitPlan {
  const base: Omit<TransitPlan, 'hops' | 'total_cost' | 'blocked' | 'block_reason'> = {
    schema_version: 'scbe_transit_plan_v1',
    station_id: manifest.station_id,
    from_zone: fromZoneId,
    to_zone: toZoneId,
  };

  if (fromZoneId === toZoneId) {
    return { ...base, hops: [], total_cost: 0, blocked: false };
  }

  const fromZone = manifest.zones[fromZoneId];
  const toZone = manifest.zones[toZoneId];
  if (!fromZone) {
    return { ...base, hops: [], total_cost: 0, blocked: true, block_reason: 'from_zone_unknown' };
  }
  if (!toZone) {
    return { ...base, hops: [], total_cost: 0, blocked: true, block_reason: 'to_zone_unknown' };
  }

  // Build zone→nodes index
  const zoneNodes: Record<string, string[]> = {};
  for (const node of Object.values(manifest.transit_nodes)) {
    if (!zoneNodes[node.zone_id]) zoneNodes[node.zone_id] = [];
    zoneNodes[node.zone_id].push(node.id);
  }

  // Fall back to zone.linked_zones if no transit nodes exist
  if (Object.keys(manifest.transit_nodes).length === 0) {
    const path = bfsZones(manifest, fromZoneId, toZoneId);
    if (!path) {
      return {
        ...base,
        hops: [],
        total_cost: 0,
        blocked: true,
        block_reason: 'no_route',
      };
    }
    const hops: TransitHop[] = path.map((zid) => ({
      zone_id: zid,
      node_id: '',
      mode: 'direct',
      cost: 1,
    }));
    return { ...base, hops, total_cost: hops.length, blocked: false };
  }

  // Dijkstra over transit nodes
  const dist: Record<string, number> = {};
  const prev: Record<string, { nodeId: string; route: TransitRoute } | null> = {};
  const visited = new Set<string>();

  for (const nodeId of Object.keys(manifest.transit_nodes)) {
    dist[nodeId] = Infinity;
    prev[nodeId] = null;
  }

  const startNodes = zoneNodes[fromZoneId] ?? [];
  for (const sn of startNodes) {
    dist[sn] = 0;
  }

  const queue: Array<[string, number]> = startNodes.map((id) => [id, 0]);

  while (queue.length > 0) {
    queue.sort((a, b) => a[1] - b[1]);
    const [current, cost] = queue.shift()!;
    if (visited.has(current)) continue;
    visited.add(current);

    const node = manifest.transit_nodes[current];
    if (!node) continue;

    for (const route of node.routes) {
      if (visited.has(route.to)) continue;
      const newCost = cost + route.cost;
      if (newCost < (dist[route.to] ?? Infinity)) {
        dist[route.to] = newCost;
        prev[route.to] = { nodeId: current, route };
        queue.push([route.to, newCost]);
      }
    }
  }

  // Find cheapest destination node in target zone
  const destNodes = zoneNodes[toZoneId] ?? [];
  let bestDest: string | null = null;
  let bestCost = Infinity;
  for (const dn of destNodes) {
    if ((dist[dn] ?? Infinity) < bestCost) {
      bestCost = dist[dn];
      bestDest = dn;
    }
  }

  if (!bestDest || bestCost === Infinity) {
    return { ...base, hops: [], total_cost: 0, blocked: true, block_reason: 'no_route' };
  }

  // Reconstruct path
  const hopNodeIds: string[] = [];
  let cur: string | null = bestDest;
  while (cur) {
    hopNodeIds.unshift(cur);
    const p: { nodeId: string; route: TransitRoute } | null = prev[cur] ?? null;
    cur = p ? p.nodeId : null;
  }

  const hops: TransitHop[] = hopNodeIds.map((nodeId) => {
    const node = manifest.transit_nodes[nodeId];
    const incoming = prev[nodeId];
    return {
      zone_id: node?.zone_id ?? '',
      node_id: nodeId,
      mode: incoming?.route.mode ?? 'direct',
      cost: incoming?.route.cost ?? 0,
    };
  });

  return { ...base, hops, total_cost: bestCost, blocked: false };
}

/** Simple BFS over zone.linked_zones when no transit nodes are defined. */
function bfsZones(manifest: StationManifest, from: string, to: string): string[] | null {
  const visited = new Set<string>([from]);
  const queue: Array<string[]> = [[from]];
  while (queue.length > 0) {
    const path = queue.shift()!;
    const curr = path[path.length - 1];
    const zone = manifest.zones[curr];
    if (!zone) continue;
    for (const linked of zone.linked_zones) {
      if (linked === to) return [...path, linked];
      if (!visited.has(linked)) {
        visited.add(linked);
        queue.push([...path, linked]);
      }
    }
  }
  return null;
}

// ─── Docking ──────────────────────────────────────────────────────────────────

export function getDockingPort(manifest: StationManifest, portId: string): DockingPort | null {
  return manifest.docking_ports[portId] ?? null;
}

export function dockAgent(
  manifest: StationManifest,
  agentId: string,
  portId: string,
  opts: { now?: string; receipt?: string } = {}
): StationManifest {
  const now = opts.now ?? new Date().toISOString();
  const port = manifest.docking_ports[portId];
  if (!port) return manifest;

  const updated_port: DockingPort = {
    ...port,
    agent_id: agentId,
    docked_at: now,
    receipt: opts.receipt,
  };

  // Also add agent to zone occupants
  const zone = manifest.zones[port.zone_id];
  let zones = manifest.zones;
  if (zone && !zone.occupants.includes(agentId)) {
    zones = {
      ...zones,
      [zone.id]: { ...zone, occupants: [...zone.occupants, agentId] },
    };
  }

  return {
    ...manifest,
    zones,
    docking_ports: { ...manifest.docking_ports, [portId]: updated_port },
    updated_at: now,
  };
}

export function undockAgent(
  manifest: StationManifest,
  portId: string,
  opts: { now?: string } = {}
): StationManifest {
  const now = opts.now ?? new Date().toISOString();
  const port = manifest.docking_ports[portId];
  if (!port || !port.agent_id) return manifest;

  const agentId = port.agent_id;
  const updated_port: DockingPort = {
    ...port,
    agent_id: undefined,
    docked_at: undefined,
    receipt: undefined,
  };

  // Remove agent from zone occupants
  const zone = manifest.zones[port.zone_id];
  let zones = manifest.zones;
  if (zone) {
    zones = {
      ...zones,
      [zone.id]: { ...zone, occupants: zone.occupants.filter((id) => id !== agentId) },
    };
  }

  return {
    ...manifest,
    zones,
    docking_ports: { ...manifest.docking_ports, [portId]: updated_port },
    updated_at: now,
  };
}

// ─── Keeper sweep ─────────────────────────────────────────────────────────────

export interface KeeperRepairAction {
  zone_id: string;
  action: string;
  priority: 'low' | 'medium' | 'high';
}

export interface KeeperSweepResult {
  schema_version: 'scbe_keeper_sweep_v1';
  station_id: string;
  swept_at: string;
  zones_checked: number;
  stale_zones: string[];
  quarantined_zones: string[];
  overcrowded_zones: string[];
  unroutable_zones: string[];
  repair_actions: KeeperRepairAction[];
  escalations: string[];
}

/**
 * Sweep all zones for maintenance needs.
 * Keeper can repair stale/overcrowded zones; escalates quarantined + unroutable.
 */
export function sweepKeepers(
  manifest: StationManifest,
  opts: { stale_threshold_ms?: number; now?: string } = {}
): KeeperSweepResult {
  const now = opts.now ?? new Date().toISOString();
  const staleMs = opts.stale_threshold_ms ?? 86_400_000; // 24h default
  const nowTs = new Date(now).getTime();

  const stale_zones: string[] = [];
  const quarantined_zones: string[] = [];
  const overcrowded_zones: string[] = [];
  const unroutable_zones: string[] = [];
  const repair_actions: KeeperRepairAction[] = [];
  const escalations: string[] = [];

  for (const zone of Object.values(manifest.zones)) {
    // Stale: no audit receipt and last updated beyond threshold
    const updatedTs = new Date(zone.updated_at).getTime();
    if (!zone.audit_receipt && nowTs - updatedTs > staleMs) {
      stale_zones.push(zone.id);
      repair_actions.push({ zone_id: zone.id, action: 'schedule_audit', priority: 'medium' });
    }

    // Quarantined: flag and escalate
    if (zone.state === 'quarantined') {
      quarantined_zones.push(zone.id);
      escalations.push(zone.id);
      repair_actions.push({ zone_id: zone.id, action: 'review_quarantine', priority: 'high' });
    }

    // Overcrowded: occupants exceed capacity
    if (zone.occupants.length > zone.capacity) {
      overcrowded_zones.push(zone.id);
      repair_actions.push({
        zone_id: zone.id,
        action: 'evict_excess_occupants',
        priority: 'medium',
      });
    }

    // Unroutable: zone has no links and no transit nodes pointing to it
    const hasLinks = zone.linked_zones.length > 0;
    const hasIncomingNodes = Object.values(manifest.transit_nodes).some(
      (n) => n.zone_id === zone.id
    );
    if (!hasLinks && !hasIncomingNodes && zone.state === 'active') {
      unroutable_zones.push(zone.id);
      // Only escalate if it's important (not offline/standby)
      escalations.push(zone.id);
      repair_actions.push({ zone_id: zone.id, action: 'add_transit_link', priority: 'low' });
    }
  }

  return {
    schema_version: 'scbe_keeper_sweep_v1',
    station_id: manifest.station_id,
    swept_at: now,
    zones_checked: Object.keys(manifest.zones).length,
    stale_zones,
    quarantined_zones,
    overcrowded_zones,
    unroutable_zones,
    repair_actions,
    escalations: [...new Set(escalations)],
  };
}

// ─── EVA station summary ──────────────────────────────────────────────────────

export interface DistrictHealthRecord {
  district: District;
  health: HealthColor;
  zone_count: number;
  active_count: number;
  quarantined_count: number;
}

export interface StationSummary {
  schema_version: 'scbe_station_summary_v1';
  station_id: string;
  generated_at: string;
  total_zones: number;
  active_zones: number;
  standby_zones: number;
  maintenance_zones: number;
  quarantined_zones: number;
  offline_zones: number;
  total_agents_docked: number;
  fog_of_war_count: number;
  district_health: DistrictHealthRecord[];
  top_alerts: string[];
  available_routes: number;
  pending_repair_actions: number;
}

export function summarizeStation(
  manifest: StationManifest,
  lastSweep?: KeeperSweepResult,
  opts: { now?: string } = {}
): StationSummary {
  const now = opts.now ?? new Date().toISOString();
  const zones = Object.values(manifest.zones);

  let active = 0,
    standby = 0,
    maintenance = 0,
    quarantined = 0,
    offline = 0;
  for (const z of zones) {
    if (z.state === 'active') active++;
    else if (z.state === 'standby') standby++;
    else if (z.state === 'maintenance') maintenance++;
    else if (z.state === 'quarantined') quarantined++;
    else if (z.state === 'offline') offline++;
  }

  const total_agents_docked = Object.values(manifest.docking_ports).filter(
    (p) => p.agent_id !== undefined
  ).length;

  const available_routes = Object.values(manifest.transit_nodes).reduce(
    (sum, n) => sum + n.routes.length,
    0
  );

  // District health: green if all active, amber if any maintenance/standby, red if any quarantined, critical if all offline
  const district_health: DistrictHealthRecord[] = [];
  for (const district of ALL_DISTRICTS) {
    const zoneIds = manifest.districts[district] ?? [];
    const distZones = zoneIds.map((id) => manifest.zones[id]).filter(Boolean) as StationZone[];
    const zCount = distZones.length;
    const aCount = distZones.filter((z) => z.state === 'active').length;
    const qCount = distZones.filter((z) => z.state === 'quarantined').length;
    const oCount = distZones.filter((z) => z.state === 'offline').length;

    let health: HealthColor = 'green';
    if (zCount === 0) health = 'amber';
    else if (oCount === zCount) health = 'critical';
    else if (qCount > 0) health = 'red';
    else if (aCount < zCount) health = 'amber';

    district_health.push({
      district,
      health,
      zone_count: zCount,
      active_count: aCount,
      quarantined_count: qCount,
    });
  }

  const top_alerts: string[] = [];
  if (quarantined > 0) top_alerts.push(`${quarantined} zone(s) quarantined`);
  if (lastSweep && lastSweep.escalations.length > 0) {
    top_alerts.push(`${lastSweep.escalations.length} zone(s) need escalation`);
  }
  if (manifest.fog_of_war.length > 0) {
    top_alerts.push(`${manifest.fog_of_war.length} zone(s) in fog of war`);
  }
  if (offline > 0) top_alerts.push(`${offline} zone(s) offline`);

  return {
    schema_version: 'scbe_station_summary_v1',
    station_id: manifest.station_id,
    generated_at: now,
    total_zones: zones.length,
    active_zones: active,
    standby_zones: standby,
    maintenance_zones: maintenance,
    quarantined_zones: quarantined,
    offline_zones: offline,
    total_agents_docked,
    fog_of_war_count: manifest.fog_of_war.length,
    district_health,
    top_alerts,
    available_routes,
    pending_repair_actions: lastSweep?.repair_actions.length ?? 0,
  };
}

// ─── Damage report ────────────────────────────────────────────────────────────

export interface DamageReport {
  schema_version: 'scbe_damage_report_v1';
  station_id: string;
  reported_at: string;
  critical_zones: string[];
  isolated_zones: string[];
  security_breaches: string[];
  stale_docking_ports: string[];
  missing_protocols: District[];
  overall_health: HealthColor;
  recommended_actions: string[];
}

/**
 * Identify structural damage: quarantined zones, isolated topology,
 * stale ports, missing protocols, security boundary violations.
 */
export function reportDamage(
  manifest: StationManifest,
  opts: { stale_port_threshold_ms?: number; now?: string } = {}
): DamageReport {
  const now = opts.now ?? new Date().toISOString();
  const staleMs = opts.stale_port_threshold_ms ?? 86_400_000;
  const nowTs = new Date(now).getTime();

  const critical_zones: string[] = [];
  const isolated_zones: string[] = [];
  const security_breaches: string[] = [];
  const stale_docking_ports: string[] = [];
  const missing_protocols: District[] = [];
  const recommended_actions: string[] = [];

  // Critical: quarantined or offline zones
  for (const zone of Object.values(manifest.zones)) {
    if (zone.state === 'quarantined' || zone.state === 'offline') {
      critical_zones.push(zone.id);
    }
    // Isolated: no links, no transit node, active state
    const hasLinks = zone.linked_zones.length > 0;
    const hasNode = Object.values(manifest.transit_nodes).some((n) => n.zone_id === zone.id);
    if (!hasLinks && !hasNode && zone.state === 'active') {
      isolated_zones.push(zone.id);
    }
  }

  // Security boundary violations: zones inside boundary that exceed min_clearance
  for (const boundary of Object.values(manifest.security_boundaries)) {
    for (const zoneId of boundary.zone_ids) {
      const zone = manifest.zones[zoneId];
      if (!zone) continue;
      if (CLEARANCE_RANK[zone.clearance] > CLEARANCE_RANK[boundary.min_clearance]) {
        security_breaches.push(`${zoneId} exceeds boundary ${boundary.id} clearance floor`);
      }
    }
  }

  // Stale docking ports: occupied but no recent dock timestamp
  for (const [portId, port] of Object.entries(manifest.docking_ports)) {
    if (port.agent_id && port.docked_at) {
      const dockedTs = new Date(port.docked_at).getTime();
      if (nowTs - dockedTs > staleMs) {
        stale_docking_ports.push(portId);
      }
    }
  }

  // Missing protocols: districts without a cultural protocol entry
  for (const district of ALL_DISTRICTS) {
    if (!manifest.cultural_protocols[district]) {
      missing_protocols.push(district);
    }
  }

  // Recommended actions
  if (critical_zones.length > 0) {
    recommended_actions.push(`Investigate ${critical_zones.length} critical zone(s)`);
  }
  if (isolated_zones.length > 0) {
    recommended_actions.push(`Add transit links to ${isolated_zones.length} isolated zone(s)`);
  }
  if (security_breaches.length > 0) {
    recommended_actions.push(`Resolve ${security_breaches.length} security boundary conflict(s)`);
  }
  if (stale_docking_ports.length > 0) {
    recommended_actions.push(`Review ${stale_docking_ports.length} stale docking port(s)`);
  }
  if (missing_protocols.length > 0) {
    recommended_actions.push(`Add cultural protocols for: ${missing_protocols.join(', ')}`);
  }

  // Overall health
  let overall_health: HealthColor = 'green';
  if (critical_zones.length > 0 || security_breaches.length > 0) overall_health = 'red';
  if (
    critical_zones.filter((id) => manifest.zones[id]?.state === 'quarantined').length >
    Object.keys(manifest.zones).length * 0.5
  ) {
    overall_health = 'critical';
  }
  if (overall_health === 'green' && (isolated_zones.length > 0 || stale_docking_ports.length > 0)) {
    overall_health = 'amber';
  }

  return {
    schema_version: 'scbe_damage_report_v1',
    station_id: manifest.station_id,
    reported_at: now,
    critical_zones,
    isolated_zones,
    security_breaches,
    stale_docking_ports,
    missing_protocols,
    overall_health,
    recommended_actions,
  };
}

import crypto from 'node:crypto';

export type SearchPlane =
  | 'local'
  | 'repo'
  | 'web'
  | 'tool'
  | 'model'
  | 'artifact'
  | 'security'
  | 'air'
  | 'surface'
  | 'subsurface'
  | 'space';

export type SearchNodeState =
  'open' | 'expanded' | 'contracted' | 'claimed' | 'complete' | 'blocked';

export type SearchColorGrade = 'blue' | 'green' | 'yellow' | 'orange' | 'red' | 'purple';

export interface SearchSector {
  x: number;
  y: number;
  z: number;
  width: number;
  height: number;
  depth: number;
}

export interface SearchSpaceNode {
  id: string;
  parent_id: string | null;
  depth: number;
  plane: SearchPlane;
  query: string;
  priority: number;
  risk: number;
  unknown_mass: number;
  confidence: number;
  owner: string | null;
  state: SearchNodeState;
  sector: SearchSector;
  tags: string[];
  color: SearchColorGrade;
}

export interface SearchAbridgement {
  parent_id: string | null;
  anchor_id: string;
  child_ids: string[];
  summary: string;
  max_priority: number;
  max_risk: number;
  unknown_mass: number;
  color: SearchColorGrade;
}

export interface SearchContractionResult {
  schema_version: 'scbe.agent_bus.search_space_contraction.v1';
  nodes: SearchSpaceNode[];
  abridgements: SearchAbridgement[];
  contracted_node_ids: string[];
}

export interface SearchLaneAgent {
  id: string;
  model_lane: 'local' | 'free' | 'paid' | string;
  planes?: SearchPlane[];
  risk_limit?: number;
  max_nodes?: number;
}

export interface SearchLane {
  agent_id: string;
  model_lane: string;
  assigned_node_ids: string[];
  query_order: string[];
  color_gradient: SearchColorGrade[];
  sector_keys: string[];
}

export interface SearchLaneAllocation {
  schema_version: 'scbe.agent_bus.parallel_search_lanes.v1';
  lanes: SearchLane[];
  unassigned_node_ids: string[];
  interference: Array<{ node_id: string; blocked_by: string; reason: string }>;
  coverage: {
    total_nodes: number;
    assigned_nodes: number;
    unassigned_nodes: number;
  };
  provenance_hash: string;
}

export interface SearchResult {
  node_id: string;
  agent_id: string;
  score: number;
  title: string;
  payload?: unknown;
}

export interface MergedSearchResult {
  key: string;
  node_ids: string[];
  agent_ids: string[];
  best_score: number;
  title: string;
  payloads: unknown[];
}

export interface SearchResultMerge {
  schema_version: 'scbe.agent_bus.search_result_merge.v1';
  results: MergedSearchResult[];
  duplicate_groups: number;
  provenance_hash: string;
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}

function stableHash(value: unknown): string {
  return crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function sectorKey(sector: SearchSector): string {
  return `${sector.x}:${sector.y}:${sector.z}:${sector.width}:${sector.height}:${sector.depth}`;
}

function overlaps(a: SearchSector, b: SearchSector): boolean {
  return (
    a.x < b.x + b.width &&
    a.x + a.width > b.x &&
    a.y < b.y + b.height &&
    a.y + a.height > b.y &&
    a.z < b.z + b.depth &&
    a.z + a.depth > b.z
  );
}

export function gradeSearchNode(
  node: Pick<SearchSpaceNode, 'priority' | 'risk' | 'unknown_mass' | 'state' | 'owner'>
): SearchColorGrade {
  if (node.state === 'blocked' || node.risk >= 0.85) return 'red';
  if (node.owner === 'shared') return 'purple';
  if (node.state === 'complete') return 'green';
  if (node.state === 'contracted') return 'blue';
  if (node.priority >= 0.75 || node.unknown_mass >= 0.65 || node.risk >= 0.55) return 'orange';
  return 'yellow';
}

export function createSearchNode(
  input: Omit<SearchSpaceNode, 'color'> & { color?: SearchColorGrade }
): SearchSpaceNode {
  const node: SearchSpaceNode = {
    ...input,
    priority: clamp01(input.priority),
    risk: clamp01(input.risk),
    unknown_mass: clamp01(input.unknown_mass),
    confidence: clamp01(input.confidence),
    tags: [...input.tags].sort(),
    color: input.color || 'yellow',
  };
  return { ...node, color: input.color || gradeSearchNode(node) };
}

export function reorderSearchQueries(
  nodes: SearchSpaceNode[],
  options: { risk_limit?: number; planes?: SearchPlane[] } = {}
): SearchSpaceNode[] {
  const planeSet = options.planes ? new Set(options.planes) : null;
  return nodes
    .filter((node) => node.state !== 'complete' && node.state !== 'blocked')
    .filter((node) => !planeSet || planeSet.has(node.plane))
    .filter((node) => options.risk_limit === undefined || node.risk <= options.risk_limit)
    .slice()
    .sort((a, b) => {
      const scoreA = a.priority * 4 + a.unknown_mass * 2 + a.confidence - a.risk;
      const scoreB = b.priority * 4 + b.unknown_mass * 2 + b.confidence - b.risk;
      if (scoreB !== scoreA) return scoreB - scoreA;
      if (a.depth !== b.depth) return a.depth - b.depth;
      return a.id.localeCompare(b.id);
    });
}

export function expandSearchNode(
  node: SearchSpaceNode,
  options: { branch_factor?: 2 | 4 | 8; query_prefix?: string } = {}
): SearchSpaceNode[] {
  const branchFactor = options.branch_factor || 8;
  const xParts = branchFactor === 2 ? 2 : 2;
  const yParts = branchFactor === 2 ? 1 : 2;
  const zParts = branchFactor === 8 ? 2 : 1;
  const children: SearchSpaceNode[] = [];
  let index = 0;
  for (let dz = 0; dz < zParts; dz++) {
    for (let dy = 0; dy < yParts; dy++) {
      for (let dx = 0; dx < xParts; dx++) {
        if (index >= branchFactor) continue;
        const child = createSearchNode({
          id: `${node.id}.${index}`,
          parent_id: node.id,
          depth: node.depth + 1,
          plane: node.plane,
          query: `${options.query_prefix || node.query} / sector ${index}`,
          priority: clamp01(node.priority - 0.03 + index * 0.01),
          risk: node.risk,
          unknown_mass: clamp01(node.unknown_mass * 0.8),
          confidence: clamp01(node.confidence * 0.95),
          owner: null,
          state: 'open',
          sector: {
            x: node.sector.x + (dx * node.sector.width) / xParts,
            y: node.sector.y + (dy * node.sector.height) / yParts,
            z: node.sector.z + (dz * node.sector.depth) / zParts,
            width: node.sector.width / xParts,
            height: node.sector.height / yParts,
            depth: node.sector.depth / zParts,
          },
          tags: [...node.tags, `octant:${index}`],
        });
        children.push(child);
        index += 1;
      }
    }
  }
  return children;
}

export function contractSearchSpace(
  nodes: SearchSpaceNode[],
  options: { keep_priority?: number; keep_risk?: number; max_depth?: number } = {}
): SearchContractionResult {
  const keepPriority = options.keep_priority ?? 0.7;
  const keepRisk = options.keep_risk ?? 0.6;
  const maxDepth = options.max_depth ?? 1;
  const kept: SearchSpaceNode[] = [];
  const groups = new Map<string, SearchSpaceNode[]>();

  for (const node of nodes) {
    const shouldKeep =
      node.depth <= maxDepth ||
      node.priority >= keepPriority ||
      node.risk >= keepRisk ||
      node.state === 'claimed' ||
      node.state === 'blocked';
    if (shouldKeep) {
      kept.push(node);
    } else {
      const key = node.parent_id || 'root';
      groups.set(key, [...(groups.get(key) || []), node]);
    }
  }

  const abridgements: SearchAbridgement[] = [...groups.entries()].map(([parentId, children]) => {
    const maxPriority = Math.max(...children.map((child) => child.priority));
    const maxRisk = Math.max(...children.map((child) => child.risk));
    const unknownMass = children.reduce((sum, child) => sum + child.unknown_mass, 0);
    const anchor = createSearchNode({
      id: `abridge.${parentId}.${stableHash(children.map((child) => child.id)).slice(0, 8)}`,
      parent_id: parentId === 'root' ? null : parentId,
      depth: Math.min(...children.map((child) => child.depth)),
      plane: children[0]!.plane,
      query: `abridged ${children.length} sparse sectors`,
      priority: maxPriority,
      risk: maxRisk,
      unknown_mass: clamp01(unknownMass / Math.max(1, children.length)),
      confidence: Math.max(...children.map((child) => child.confidence)),
      owner: 'shared',
      state: 'contracted',
      sector: children[0]!.sector,
      tags: ['abridgement', ...new Set(children.flatMap((child) => child.tags))],
    });
    return {
      parent_id: anchor.parent_id,
      anchor_id: anchor.id,
      child_ids: children.map((child) => child.id).sort(),
      summary: anchor.query,
      max_priority: maxPriority,
      max_risk: maxRisk,
      unknown_mass: anchor.unknown_mass,
      color: anchor.color,
    };
  });

  return {
    schema_version: 'scbe.agent_bus.search_space_contraction.v1',
    nodes: kept,
    abridgements,
    contracted_node_ids: abridgements.flatMap((item) => item.child_ids).sort(),
  };
}

export function repositionSearchNode(
  nodes: SearchSpaceNode[],
  nodeId: string,
  newParentId: string | null
): SearchSpaceNode[] {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  if (!byId.has(nodeId)) throw new Error(`node not found: ${nodeId}`);
  if (newParentId && !byId.has(newParentId))
    throw new Error(`new parent not found: ${newParentId}`);

  for (let cursor = newParentId; cursor; cursor = byId.get(cursor)?.parent_id || null) {
    if (cursor === nodeId) throw new Error('cannot reposition a node under its own descendant');
  }

  const clone = nodes.map((node) => ({
    ...node,
    tags: [...node.tags],
    sector: { ...node.sector },
  }));
  const clonedById = new Map(clone.map((node) => [node.id, node]));
  const moved = clonedById.get(nodeId)!;
  moved.parent_id = newParentId;
  moved.depth = newParentId ? clonedById.get(newParentId)!.depth + 1 : 0;

  let changed = true;
  while (changed) {
    changed = false;
    for (const node of clone) {
      if (!node.parent_id) continue;
      const parent = clonedById.get(node.parent_id);
      if (parent && node.depth !== parent.depth + 1) {
        node.depth = parent.depth + 1;
        changed = true;
      }
    }
  }
  return clone.map((node) => ({ ...node, color: gradeSearchNode(node) }));
}

export function allocateParallelSearchLanes(
  nodes: SearchSpaceNode[],
  agents: SearchLaneAgent[]
): SearchLaneAllocation {
  const lanes: SearchLane[] = agents.map((agent) => ({
    agent_id: agent.id,
    model_lane: agent.model_lane,
    assigned_node_ids: [],
    query_order: [],
    color_gradient: [],
    sector_keys: [],
  }));
  const assigned = new Set<string>();
  const assignedSectors: Array<{ node_id: string; sector: SearchSector }> = [];
  const interference: SearchLaneAllocation['interference'] = [];

  for (const agent of agents) {
    const lane = lanes.find((candidate) => candidate.agent_id === agent.id)!;
    const ordered = reorderSearchQueries(nodes, {
      planes: agent.planes,
      risk_limit: agent.risk_limit,
    });
    for (const node of ordered) {
      if (assigned.has(node.id)) continue;
      if (lane.assigned_node_ids.length >= (agent.max_nodes || 4)) break;
      const blocker = assignedSectors.find((item) => overlaps(item.sector, node.sector));
      if (blocker) {
        interference.push({
          node_id: node.id,
          blocked_by: blocker.node_id,
          reason: 'sector overlap would make two agents search the same space',
        });
        continue;
      }
      assigned.add(node.id);
      assignedSectors.push({ node_id: node.id, sector: node.sector });
      lane.assigned_node_ids.push(node.id);
      lane.query_order.push(node.query);
      lane.color_gradient.push(node.color);
      lane.sector_keys.push(sectorKey(node.sector));
    }
  }

  const unassigned = nodes
    .filter((node) => !assigned.has(node.id) && node.state !== 'complete')
    .map((node) => node.id)
    .sort();

  return {
    schema_version: 'scbe.agent_bus.parallel_search_lanes.v1',
    lanes,
    unassigned_node_ids: unassigned,
    interference,
    coverage: {
      total_nodes: nodes.length,
      assigned_nodes: assigned.size,
      unassigned_nodes: unassigned.length,
    },
    provenance_hash: stableHash({ lanes, unassigned, interference }),
  };
}

export function mergeSearchResults(results: SearchResult[]): SearchResultMerge {
  const groups = new Map<string, SearchResult[]>();
  for (const result of results) {
    const key = result.title.trim().toLowerCase();
    groups.set(key, [...(groups.get(key) || []), result]);
  }
  const merged: MergedSearchResult[] = [...groups.entries()]
    .map(([key, group]) => ({
      key,
      node_ids: [...new Set(group.map((item) => item.node_id))].sort(),
      agent_ids: [...new Set(group.map((item) => item.agent_id))].sort(),
      best_score: Math.max(...group.map((item) => item.score)),
      title: group.sort((a, b) => b.score - a.score)[0]!.title,
      payloads: group.map((item) => item.payload).filter((payload) => payload !== undefined),
    }))
    .sort((a, b) => b.best_score - a.best_score || a.key.localeCompare(b.key));

  return {
    schema_version: 'scbe.agent_bus.search_result_merge.v1',
    results: merged,
    duplicate_groups: merged.filter((item) => item.node_ids.length > 1 || item.agent_ids.length > 1)
      .length,
    provenance_hash: stableHash(merged),
  };
}

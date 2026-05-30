import crypto from 'node:crypto';

export type RubixBrowserPermission =
  | 'observe'
  | 'visual.read'
  | 'dom.read'
  | 'dom.write'
  | 'network.read'
  | 'network.write'
  | 'storage.read'
  | 'storage.write'
  | 'auth.read'
  | 'auth.write'
  | 'tool.call'
  | 'external.open'
  | string;

export interface RubixBrowserFace {
  id: string;
  label: string;
  axis: 'visual' | 'structure' | 'transport' | 'state' | 'identity' | 'execution' | 'memory';
  coordinate: [number, number, number, number];
  required_permission: RubixBrowserPermission;
  risk: 'low' | 'medium' | 'high';
  description: string;
}

export interface RubixBrowserMove {
  index: number;
  from: string;
  to: string;
  direction: string;
  required_permission: RubixBrowserPermission;
  allowed: boolean;
  reason: string;
}

export interface RubixBrowserPlan {
  schema_version: 'scbe.rubix_browser_plan.v1';
  task: string;
  mode: 'plan';
  generated_at: string;
  permissions: RubixBrowserPermission[];
  faces: RubixBrowserFace[];
  demanded_faces: string[];
  route: RubixBrowserMove[];
  blocked_moves: RubixBrowserMove[];
  closed_loop: boolean;
  route_reversible: boolean;
  cube_projection: {
    dimension_count: number;
    root_face: string;
    tip: [number, number];
    fog_of_war: string[];
    visible_faces: string[];
  };
  audit: {
    route_sha256: string;
    permission_sha256: string;
    verdict: 'PASS' | 'HOLD';
    reason: string;
  };
}

export interface RubixBrowserBenchmarkCase {
  id: string;
  task: string;
  permissions: RubixBrowserPermission[];
  expected_verdict: 'PASS' | 'HOLD';
  expected_blocked_faces?: string[];
}

export interface RubixBrowserBenchmarkRow {
  id: string;
  task: string;
  verdict: 'PASS' | 'HOLD';
  expected_verdict: 'PASS' | 'HOLD';
  ok: boolean;
  blocked_faces: string[];
  expected_blocked_faces: string[];
  route_sha256: string;
}

export interface RubixBrowserBenchmarkReport {
  schema_version: 'scbe.rubix_browser_benchmark.v1';
  mode: 'headless' | 'headed';
  generated_at: string;
  case_count: number;
  pass_count: number;
  score: number;
  rows: RubixBrowserBenchmarkRow[];
  recommendation: string;
}

export interface BuildRubixBrowserPlanOptions {
  task: string;
  permissions?: Iterable<RubixBrowserPermission>;
  generatedAt?: string;
}

export interface RunRubixBrowserBenchmarkOptions {
  mode?: 'headless' | 'headed';
  generatedAt?: string;
  cases?: readonly RubixBrowserBenchmarkCase[];
}

export const RUBIX_BROWSER_FACES: readonly RubixBrowserFace[] = [
  {
    id: 'viewport',
    label: 'Viewport Face',
    axis: 'visual',
    coordinate: [0, 0, 1, 0],
    required_permission: 'visual.read',
    risk: 'low',
    description: 'Pixels, visible text, screenshots, and spatial focus.',
  },
  {
    id: 'dom',
    label: 'DOM Face',
    axis: 'structure',
    coordinate: [1, 0, 0, 0],
    required_permission: 'dom.read',
    risk: 'low',
    description: 'Elements, attributes, labels, forms, and page structure.',
  },
  {
    id: 'network',
    label: 'Network Face',
    axis: 'transport',
    coordinate: [0, 1, 0, 0],
    required_permission: 'network.read',
    risk: 'medium',
    description: 'Requests, responses, external fetches, and navigation traffic.',
  },
  {
    id: 'storage',
    label: 'Storage Face',
    axis: 'state',
    coordinate: [-1, 0, 0, 0],
    required_permission: 'storage.read',
    risk: 'medium',
    description: 'Cookies, local storage, cache, and durable browser state.',
  },
  {
    id: 'auth',
    label: 'Auth Face',
    axis: 'identity',
    coordinate: [0, -1, 0, 0],
    required_permission: 'auth.read',
    risk: 'high',
    description: 'Session identity, login state, account boundaries, and credentials.',
  },
  {
    id: 'tool',
    label: 'Tool Face',
    axis: 'execution',
    coordinate: [0, 0, -1, 0],
    required_permission: 'tool.call',
    risk: 'high',
    description: 'Clicks, typing, downloads, uploads, and side-effectful browser actions.',
  },
  {
    id: 'memory',
    label: 'Memory Face',
    axis: 'memory',
    coordinate: [0, 0, 0, 1],
    required_permission: 'observe',
    risk: 'low',
    description: 'Deferred work, task ticker state, receipts, and loop context.',
  },
];

export const RUBIX_BROWSER_BENCHMARK_CASES: readonly RubixBrowserBenchmarkCase[] = [
  {
    id: 'read-visible-labels',
    task: 'inspect the pricing page and summarize visible labels',
    permissions: ['observe', 'visual.read', 'dom.read'],
    expected_verdict: 'PASS',
  },
  {
    id: 'submit-without-tool',
    task: 'open the upload page, fill the form, and submit the video',
    permissions: ['observe', 'visual.read', 'dom.read'],
    expected_verdict: 'HOLD',
    expected_blocked_faces: ['tool'],
  },
  {
    id: 'api-without-network',
    task: 'read the dashboard and call the API URL for account status',
    permissions: ['observe', 'visual.read', 'dom.read'],
    expected_verdict: 'HOLD',
    expected_blocked_faces: ['network'],
  },
  {
    id: 'stateful-auth-tool-route',
    task: 'login, read session storage, call the API URL, then click save',
    permissions: [
      'observe',
      'visual.read',
      'dom.read',
      'auth.read',
      'storage.read',
      'network.read',
      'tool.call',
    ],
    expected_verdict: 'PASS',
  },
];

function stableJson(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableJson(item)).join(',')}]`;
  }
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableJson(record[key])}`)
      .join(',')}}`;
  }
  return JSON.stringify(value);
}

function sha256(value: unknown): string {
  return crypto.createHash('sha256').update(stableJson(value)).digest('hex');
}

function normalizePermissions(values: Iterable<RubixBrowserPermission> | undefined): Set<string> {
  const permissions = new Set<string>(['observe']);
  for (const value of values || []) {
    const trimmed = String(value || '').trim();
    if (trimmed) permissions.add(trimmed);
  }
  if (permissions.has('visual')) permissions.add('visual.read');
  if (permissions.has('dom')) permissions.add('dom.read');
  if (permissions.has('network')) permissions.add('network.read');
  if (permissions.has('storage')) permissions.add('storage.read');
  if (permissions.has('auth')) permissions.add('auth.read');
  if (permissions.has('tool')) permissions.add('tool.call');
  return permissions;
}

function wants(task: string, patterns: RegExp[]): boolean {
  return patterns.some((pattern) => pattern.test(task));
}

function inferDemandedFaces(task: string): string[] {
  const text = task.toLowerCase();
  const demanded = new Set<string>(['viewport', 'dom', 'memory']);
  if (
    wants(text, [/\bclick\b/, /\btype\b/, /\bsubmit\b/, /\bupload\b/, /\bdownload\b/, /\bfill\b/])
  ) {
    demanded.add('tool');
  }
  if (wants(text, [/\blogin\b/, /\bsign[ -]?in\b/, /\bauth\b/, /\baccount\b/, /\bcredential\b/])) {
    demanded.add('auth');
  }
  if (wants(text, [/\bcookie\b/, /\blocal\s*storage\b/, /\bsession\b/, /\bcache\b/, /\bstate\b/])) {
    demanded.add('storage');
  }
  if (
    wants(text, [/\bapi\b/, /\bfetch\b/, /\brequest\b/, /\bnetwork\b/, /\bwebhook\b/, /\burl\b/])
  ) {
    demanded.add('network');
  }
  return Array.from(demanded);
}

function directionBetween(from: RubixBrowserFace, to: RubixBrowserFace): string {
  const delta = to.coordinate.map((value, index) => value - from.coordinate[index]);
  const names = ['x', 'y', 'z', 'w'];
  return (
    delta
      .map((value, index) => (value === 0 ? '' : `${value > 0 ? '+' : '-'}${names[index]}`))
      .filter(Boolean)
      .join('/') || 'hold'
  );
}

function canUse(face: RubixBrowserFace, permissions: Set<string>): boolean {
  return permissions.has(face.required_permission) || permissions.has('*');
}

function permissionForMove(face: RubixBrowserFace): RubixBrowserPermission {
  return face.required_permission;
}

export function buildRubixBrowserPlan(options: BuildRubixBrowserPlanOptions): RubixBrowserPlan {
  const task = String(options.task || '').trim();
  if (!task) {
    throw new Error('rubix browser plan requires a non-empty task');
  }

  const generatedAt = options.generatedAt || new Date().toISOString();
  const permissions = normalizePermissions(options.permissions);
  const demandedFaces = inferDemandedFaces(task);
  const faceById = new Map(RUBIX_BROWSER_FACES.map((face) => [face.id, face]));
  const routeIds = [
    'viewport',
    ...Array.from(new Set(demandedFaces.filter((id) => id !== 'viewport'))),
    'viewport',
  ];
  const route: RubixBrowserMove[] = [];

  for (let i = 0; i < routeIds.length - 1; i += 1) {
    const from = faceById.get(routeIds[i]);
    const to = faceById.get(routeIds[i + 1]);
    if (!from || !to) continue;
    const required = permissionForMove(to);
    const allowed = canUse(to, permissions);
    route.push({
      index: i + 1,
      from: from.id,
      to: to.id,
      direction: directionBetween(from, to),
      required_permission: required,
      allowed,
      reason: allowed
        ? `permission ${required} opens ${to.id}`
        : `missing permission ${required} for ${to.id}`,
    });
  }

  const visibleFaces = RUBIX_BROWSER_FACES.filter((face) => canUse(face, permissions)).map(
    (face) => face.id
  );
  const blockedMoves = route.filter((move) => !move.allowed);
  const closedLoop =
    route.length > 0 && route[0].from === 'viewport' && route.at(-1)?.to === 'viewport';
  const routeReversible = closedLoop && blockedMoves.length === 0;
  const routeSha = sha256({ task, route, demandedFaces });
  const permissionSha = sha256(Array.from(permissions).sort());

  return {
    schema_version: 'scbe.rubix_browser_plan.v1',
    task,
    mode: 'plan',
    generated_at: generatedAt,
    permissions: Array.from(permissions).sort(),
    faces: [...RUBIX_BROWSER_FACES],
    demanded_faces: demandedFaces,
    route,
    blocked_moves: blockedMoves,
    closed_loop: closedLoop,
    route_reversible: routeReversible,
    cube_projection: {
      dimension_count: 4,
      root_face: 'viewport',
      tip: [0, 0],
      fog_of_war: RUBIX_BROWSER_FACES.filter((face) => !canUse(face, permissions)).map(
        (face) => face.id
      ),
      visible_faces: visibleFaces,
    },
    audit: {
      route_sha256: routeSha,
      permission_sha256: permissionSha,
      verdict: routeReversible ? 'PASS' : 'HOLD',
      reason: routeReversible
        ? 'closed browser-control route is permission-complete'
        : 'route has blocked faces; add permissions or lower task scope',
    },
  };
}

export function runRubixBrowserBenchmark(
  options: RunRubixBrowserBenchmarkOptions = {}
): RubixBrowserBenchmarkReport {
  const mode = options.mode || 'headless';
  const generatedAt = options.generatedAt || new Date().toISOString();
  const cases = options.cases || RUBIX_BROWSER_BENCHMARK_CASES;
  const rows = cases.map((benchCase): RubixBrowserBenchmarkRow => {
    const plan = buildRubixBrowserPlan({
      task: benchCase.task,
      permissions: benchCase.permissions,
      generatedAt,
    });
    const blockedFaces = plan.blocked_moves.map((move) => move.to);
    const expectedBlockedFaces = benchCase.expected_blocked_faces || [];
    const expectedBlocksOk =
      expectedBlockedFaces.length === 0
        ? blockedFaces.length === 0
        : expectedBlockedFaces.every((face) => blockedFaces.includes(face));
    const ok = plan.audit.verdict === benchCase.expected_verdict && expectedBlocksOk;
    return {
      id: benchCase.id,
      task: benchCase.task,
      verdict: plan.audit.verdict,
      expected_verdict: benchCase.expected_verdict,
      ok,
      blocked_faces: blockedFaces,
      expected_blocked_faces: expectedBlockedFaces,
      route_sha256: plan.audit.route_sha256,
    };
  });
  const passCount = rows.filter((row) => row.ok).length;
  const score = rows.length === 0 ? 0 : passCount / rows.length;

  return {
    schema_version: 'scbe.rubix_browser_benchmark.v1',
    mode,
    generated_at: generatedAt,
    case_count: rows.length,
    pass_count: passCount,
    score,
    rows,
    recommendation:
      mode === 'headless'
        ? 'Use headless mode for CI and benchmark proof; rerun selected failures with headed replay.'
        : 'Use headed mode only for visual diagnosis and demo replay.',
  };
}

/**
 * @file triadic_manifold.ts
 * @module operator/triadic_manifold
 * @layer Layer 14
 * @component Triadic Operator Manifold
 *
 * A lightweight coordination model for the shared operating space between:
 * - human intent,
 * - machine state,
 * - AI inference.
 *
 * This is intentionally dependency-free. It is the operator surface contract
 * that heavier cloud, Codespaces, VM, local-Ollama, storage, and governance
 * adapters can hang from without forcing a large install onto every user.
 */

export type ActorKind = 'human' | 'machine' | 'ai';
export type OperatorMode = 'local_first' | 'cloud_assist' | 'hybrid';
export type PrivacyLevel = 'local_only' | 'remote_ok';
export type WorkloadSize = 'small' | 'medium' | 'large';
export type CompanionPackageName =
  | 'scbe-aethermoore'
  | 'scbe-agent-bus'
  | '@scbe/kernel'
  | 'scbe-sixtongues';

export interface OperatorActor {
  kind: ActorKind;
  role: string;
  constraints: string[];
}

export interface OperatorRequest {
  intent: string;
  features?: string[];
  privacy?: PrivacyLevel;
  workload?: WorkloadSize;
  preferCloud?: boolean;
  availablePackages?: CompanionPackageName[];
}

export interface OperatorPlan {
  schema_version: 'scbe-triadic-operator-plan-v1';
  mode: OperatorMode;
  actors: OperatorActor[];
  dimensions: string[];
  actions: string[];
  receipts: string[];
  companionRecommendations: CompanionRecommendation[];
}

export interface CompanionPackage {
  name: CompanionPackageName;
  ecosystem: 'npm' | 'pypi';
  install: string;
  purpose: string;
  features: string[];
  heavy: boolean;
}

export interface CompanionRecommendation {
  feature: string;
  package: CompanionPackageName;
  install: string;
  reason: string;
}

export const TRIADIC_DIMENSIONS = [
  'intent',
  'visual_layout',
  'filesystem_state',
  'process_state',
  'permissions',
  'context_window',
  'tool_affordances',
  'risk',
  'latency',
  'cost',
  'storage',
  'audit_receipts',
] as const;

export const COMPANION_PACKAGES: CompanionPackage[] = [
  {
    name: 'scbe-aethermoore',
    ecosystem: 'npm',
    install: 'npm install scbe-aethermoore',
    purpose: 'Core TypeScript governance, tokenizer, harmonic wall, and operator APIs.',
    features: ['governance', 'operator-manifold', 'tokenizer', 'browser', 'node'],
    heavy: false,
  },
  {
    name: 'scbe-agent-bus',
    ecosystem: 'pypi',
    install: 'pip install scbe-agent-bus',
    purpose: 'Python event runner surface for agent-bus workflows and governed batch dispatch.',
    features: ['agent-bus', 'python', 'batch-dispatch', 'workspace'],
    heavy: false,
  },
  {
    name: '@scbe/kernel',
    ecosystem: 'npm',
    install: 'npm install @scbe/kernel',
    purpose: 'Smaller kernel-level package for Sacred Tongues and core math without the full repo.',
    features: ['kernel', 'sacred-tongues', 'lightweight-math'],
    heavy: false,
  },
  {
    name: 'scbe-sixtongues',
    ecosystem: 'pypi',
    install: 'pip install scbe-sixtongues',
    purpose: 'Standalone Python Six Tongues tokenizer package for local scripts.',
    features: ['sacred-tongues', 'python', 'tokenizer'],
    heavy: false,
  },
];

function normalizeFeature(feature: string): string {
  return feature
    .trim()
    .toLowerCase()
    .replace(/[_\s]+/g, '-');
}

function selectMode(request: OperatorRequest): OperatorMode {
  if (request.privacy === 'local_only') return 'local_first';
  if (request.preferCloud || request.workload === 'large') return 'cloud_assist';
  if (request.workload === 'medium') return 'hybrid';
  return 'local_first';
}

function defaultActors(request: OperatorRequest): OperatorActor[] {
  return [
    {
      kind: 'human',
      role: 'sets intent, trust boundary, and final approval',
      constraints: ['time pressure', 'visual clarity', request.privacy ?? 'local_only'],
    },
    {
      kind: 'machine',
      role: 'executes real files, processes, storage, and network calls',
      constraints: ['permissions', 'disk', 'cpu', 'memory', 'available tools'],
    },
    {
      kind: 'ai',
      role: 'accelerates navigation, planning, synthesis, and verification',
      constraints: ['context window', 'tool access', 'policy', 'uncertainty'],
    },
  ];
}

export function recommendCompanionPackages(
  requestedFeatures: string[],
  availablePackages: CompanionPackageName[] = ['scbe-aethermoore']
): CompanionRecommendation[] {
  const available = new Set(availablePackages);
  const requested = requestedFeatures.map(normalizeFeature);
  const recommendations: CompanionRecommendation[] = [];

  for (const feature of requested) {
    const provider = COMPANION_PACKAGES.find(
      (pkg) => !available.has(pkg.name) && pkg.features.map(normalizeFeature).includes(feature)
    );
    if (!provider) continue;
    recommendations.push({
      feature,
      package: provider.name,
      install: provider.install,
      reason: `${provider.name} provides ${feature} without being installed as a forced dependency.`,
    });
  }

  return recommendations;
}

export function createTriadicOperatorPlan(request: OperatorRequest): OperatorPlan {
  const features = request.features ?? [];
  const mode = selectMode(request);
  const actions = [
    'project intent into the shared operator manifold',
    'bind actions to real machine objects instead of simulated UI state',
    'route cheap/low-risk work locally first',
  ];
  if (mode !== 'local_first') {
    actions.push('offload heavy or long-running work to a user-approved cloud lane');
  }
  actions.push('emit receipts before export, merge, release, or external storage handoff');

  return {
    schema_version: 'scbe-triadic-operator-plan-v1',
    mode,
    actors: defaultActors(request),
    dimensions: [...TRIADIC_DIMENSIONS],
    actions,
    receipts: [
      'SCBE_OPERATOR_PLAN_READY=1',
      'SCBE_WORKSPACE_READY=1',
      'SCBE_GATE_ALLOW=1',
      'SCBE_STORAGE_EXPORT_READY=1',
    ],
    companionRecommendations: recommendCompanionPackages(features, request.availablePackages),
  };
}

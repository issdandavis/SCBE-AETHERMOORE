/**
 * @file contextBundle.ts
 * @module harmonic/contextBundle
 * @layer Layer 1
 *
 * ContextBundle — the full ingestion payload for L1.
 *
 * The problem: layer1ComplexState(t, D) takes a flat float array derived
 * entirely from text tokenization. The imaginary axis ends up carrying
 * text-phase noise instead of real context signal.
 *
 * The fix: split the complex lift explicitly:
 *   REAL  components ← text intent features (what the prompt says)
 *   IMAG  components ← context features (who, when, system state)
 *
 * This means L5 hyperbolic distance is measuring drift in a space where
 * identity + history + env are first-class dimensions, not afterthoughts.
 * L11 temporal scoring then refines a premise that already knows the sequence.
 *
 * "Wrong size for the thing inside" — the mouth has to be wide enough
 * for what the pipeline is actually carrying.
 */

// ─── Context dimensions ───────────────────────────────────────────────────────

/**
 * Who is making the request.
 * Serializes into the imaginary axis of the L1 complex lift.
 */
export interface IdentityContext {
  /** Hashed user/service identity — never raw credentials. */
  principalHash: string;
  /** RBAC roles active at execution time. */
  roles: string[];
  /** Permission flags: can this principal write? deploy? destroy? */
  canWrite: boolean;
  canDeploy: boolean;
  canDestroy: boolean;
  /** Privilege escalation flag — sudo, admin override, etc. */
  elevated: boolean;
}

/**
 * Recent action sequence.
 * Feeds the imaginary axis so L5 hyperbolic distance sees the trajectory,
 * not just the current point. Decouples L1 from L11's temporal scoring —
 * L11 then confirms/corrects rather than constructing history from nothing.
 */
export interface TemporalContext {
  /** ISO timestamps of the N most recent actions (oldest first). */
  recentActionTimestamps: string[];
  /** Intent text of the N most recent actions (oldest first). */
  recentIntents: string[];
  /**
   * Risk class of each recent action: 'read' | 'write' | 'network' |
   * 'deploy' | 'destructive' | 'observe'
   */
  recentClasses: string[];
  /** Seconds since the last action (0 = immediate sequence). */
  secondsSinceLast: number;
}

/**
 * System state at time of ingestion.
 * Turns "delete database records" from abstract to concrete: what DB?
 * Is it connected? Is a migration running? Is the user in prod or dev?
 */
/**
 * Desk tether / physical governance surface (see scripts/sim_tether_rectifier.py).
 * Contributes to imaginary axis — phase variables for vibration, strain, flux, torque.
 */
export interface PhysicalTelemetryContext {
  vibrationAmplitude: number;
  tensionStrain: number;
  magneticFluxDrift: number;
  rectifiedTorque: number;
}

export interface EnvironmentContext {
  /** Runtime environment tier. */
  tier: 'production' | 'staging' | 'development' | 'local';
  /** Hashed connection strings for active data sources — existence only, no credentials. */
  activeConnectionHashes: string[];
  /** Whether a migration or batch job is currently running. */
  mutationInProgress: boolean;
  /** Number of currently open write transactions. */
  openWriteTransactions: number;
  /** Names of currently loaded environment variable groups (e.g. ['db', 'api']). */
  activeEnvGroups: string[];
}

/**
 * The full ingestion payload. Pass this to bundleToComplexLift() to get
 * a feature array suitable for layer1ComplexState().
 */
export interface ContextBundle {
  /** The raw text intent — becomes the REAL axis. */
  intentText: string;
  /** Normalized token embedding of intentText (caller provides; falls back to bag-of-chars). */
  intentEmbedding?: number[];
  /** Identity context — contributes to IMAGINARY axis. */
  identity?: Partial<IdentityContext>;
  /** Temporal history — contributes to IMAGINARY axis. */
  temporal?: Partial<TemporalContext>;
  /** Environment state — contributes to IMAGINARY axis. */
  environment?: Partial<EnvironmentContext>;
  /** Optional physical tether telemetry lane (L1 imaginary phase). */
  physical?: Partial<PhysicalTelemetryContext>;
}

// ─── Serializers ─────────────────────────────────────────────────────────────

/** Risk score for a move class (0=safe, 1=destructive). */
const CLASS_RISK: Record<string, number> = {
  observe: 0.0,
  read: 0.1,
  verify: 0.15,
  write: 0.4,
  network: 0.5,
  deploy: 0.7,
  destructive: 1.0,
  unknown: 0.3,
};

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.max(lo, Math.min(hi, v));
}

/**
 * Serialize identity context into a fixed-length float vector [0,1]^8.
 * Each element is a normalized signal the imaginary axis can use.
 */
function identityFeatures(id?: Partial<IdentityContext>): number[] {
  if (!id) return new Array(8).fill(0.0);
  // Principal hash → bit-scatter into 3 floats [0,1]
  const h = id.principalHash || '';
  const h0 = h.length > 0 ? parseInt(h.slice(0, 4) || '0', 16) / 0xffff : 0.5;
  const h1 = h.length > 4 ? parseInt(h.slice(4, 8) || '0', 16) / 0xffff : 0.5;
  const h2 = h.length > 8 ? parseInt(h.slice(8, 12) || '0', 16) / 0xffff : 0.5;
  return [
    h0,
    h1,
    h2,
    clamp((id.roles?.length ?? 0) / 10), // role count signal
    id.canWrite ? 0.5 : 0.0,
    id.canDeploy ? 0.75 : 0.0,
    id.canDestroy ? 1.0 : 0.0,
    id.elevated ? 1.0 : 0.0,
  ];
}

/**
 * Serialize temporal context into a fixed-length float vector [0,1]^8.
 */
function temporalFeatures(t?: Partial<TemporalContext>): number[] {
  if (!t) return new Array(8).fill(0.0);
  const classes = t.recentClasses ?? [];
  const n = Math.min(classes.length, 5);
  // Encode up to 5 prior move classes as risk scores
  const riskScores = Array.from({ length: 5 }, (_, i) =>
    i < n ? (CLASS_RISK[classes[classes.length - 1 - i]] ?? 0.3) : 0.0
  );
  // Recency signal: clamp secondsSinceLast to [0,300] → [0,1]
  const recency = 1.0 - clamp((t.secondsSinceLast ?? 60) / 300);
  // Escalation signal: is the most recent action more dangerous than the one before?
  const lastRisk = n > 0 ? (CLASS_RISK[classes[n - 1]] ?? 0.3) : 0.0;
  const prevRisk = n > 1 ? (CLASS_RISK[classes[n - 2]] ?? 0.3) : 0.0;
  const escalation = clamp(lastRisk - prevRisk + 0.5);
  return [
    ...riskScores, // 5 floats: prior action risk sequence
    recency, // how recent the last action was
    escalation, // is risk escalating?
    clamp(n / 5), // how much history we have
  ];
}

/**
 * Serialize environment context into a fixed-length float vector [0,1]^8.
 */
function environmentFeatures(e?: Partial<EnvironmentContext>): number[] {
  if (!e) return new Array(8).fill(0.0);
  const tierScore: Record<string, number> = {
    production: 1.0,
    staging: 0.66,
    development: 0.33,
    local: 0.0,
  };
  return [
    tierScore[e.tier ?? 'local'] ?? 0.0,
    clamp((e.activeConnectionHashes?.length ?? 0) / 8),
    e.mutationInProgress ? 1.0 : 0.0,
    clamp((e.openWriteTransactions ?? 0) / 10),
    clamp((e.activeEnvGroups?.length ?? 0) / 6),
    0.0,
    0.0,
    0.0,
  ];
}

const VIB_DENY = 0.008;
const TORQUE_FLOOR = 0.02;
const FLUX_DRIFT_QUARANTINE = 0.15;

/** Physical telemetry → imaginary phase slots [0,1]^8 */
export function physicalTelemetryFeatures(p?: Partial<PhysicalTelemetryContext>): number[] {
  if (!p) return new Array(8).fill(0.0);
  const vib = clamp((p.vibrationAmplitude ?? 0) / VIB_DENY);
  const strain = clamp((p.tensionStrain ?? 0) * 4);
  const flux = clamp(Math.abs(p.magneticFluxDrift ?? 0) / Math.max(FLUX_DRIFT_QUARANTINE, 1e-9));
  const torque = clamp((p.rectifiedTorque ?? 0) / Math.max(TORQUE_FLOOR * 3, 1e-9));
  const torqueDrop = clamp(1 - torque);
  return [
    vib,
    strain,
    flux,
    torque,
    torqueDrop,
    vib * strain,
    flux * torque,
    clamp(vib + torqueDrop),
  ];
}

/**
 * Encode intent text into a float vector via normalized char-code bag.
 * Used when no pre-computed embedding is provided.
 */
function intentToFeatures(text: string, D: number): number[] {
  const feats = new Array(D).fill(0.0);
  for (let i = 0; i < text.length; i++) {
    feats[i % D] += text.charCodeAt(i) / 127.0;
  }
  const mag = Math.hypot(...feats) || 1;
  // charCodes are non-negative so accumulated bins are non-negative;
  // explicit clamp guards against any Unicode edge case > 127.
  return feats.map((v) => clamp(v / mag));
}

// ─── Public API ───────────────────────────────────────────────────────────────

export const BUNDLE_REAL_DIM = 16; // real components (text intent)
export const BUNDLE_IMAG_DIM = 32; // imaginary: id(8) + temporal(8) + env(8) + physical(8)
export const BUNDLE_TOTAL_DIM = BUNDLE_REAL_DIM + BUNDLE_IMAG_DIM;

/**
 * Pass this as the pipeline config when using bundleToFeatures().
 * The pipeline default is D=6 — without this override it silently
 * uses only the first 12 of 40 features and discards all context signal.
 *
 * @example
 *   const t = bundleToFeatures(bundle);
 *   runFullPipeline14(t, BUNDLE_PIPELINE_CONFIG);
 */
export const BUNDLE_PIPELINE_CONFIG = { D: BUNDLE_REAL_DIM } as const;

/**
 * Convert a ContextBundle into a flat feature vector for layer1ComplexState().
 *
 * Format: [...real_features(16), ...imag_features(32)]
 *
 * The caller passes this directly as the `t` argument:
 *   const t = bundleToFeatures(bundle);
 *   const complexState = layer1ComplexState(t, BUNDLE_REAL_DIM);
 *
 * Layer 1 then constructs:
 *   real[i] = t[i] * cos(t[REAL_DIM + i])   ← text intent phase
 *   imag[i] = t[i] * sin(t[REAL_DIM + i])   ← context signal phase
 *
 * With this bundle, the imaginary components carry RBAC + history + env state
 * rather than text-derived phase noise.
 */
export function bundleToFeatures(bundle: ContextBundle): number[] {
  const D = BUNDLE_REAL_DIM;

  const real: number[] = bundle.intentEmbedding
    ? bundle.intentEmbedding
        .slice(0, D)
        .concat(new Array(Math.max(0, D - bundle.intentEmbedding.length)).fill(0))
        .map((v) => clamp(v)) // caller embeddings may be outside [0,1]
    : intentToFeatures(bundle.intentText, D);

  const imag: number[] = [
    ...identityFeatures(bundle.identity),
    ...temporalFeatures(bundle.temporal),
    ...environmentFeatures(bundle.environment),
    ...physicalTelemetryFeatures(bundle.physical),
  ];

  return [...real, ...imag];
}

/**
 * Convenience: build a minimal bundle from just the intent text.
 * Equivalent to the old behavior — real axis only, imaginary = zeros.
 * Use this as the drop-in replacement when callers haven't been updated yet.
 */
export function textOnlyBundle(intentText: string): ContextBundle {
  return { intentText };
}

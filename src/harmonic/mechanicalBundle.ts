/**
 * @file mechanicalBundle.ts
 * @module harmonic/mechanicalBundle
 * @layer Layer 1
 *
 * Maps physical tether telemetry into a ContextBundle so the 14-layer
 * pipeline can govern a real hardware system using the same geometry
 * it uses for AI agent drift.
 *
 * The mapping is exact:
 *   real axis  ← tether "intent" (operating mode description)
 *   imag[0..7] ← structural identity: braid chirality, bracket config, orientation
 *   imag[8..15]← temporal: recent strain history, torque sequence, curvature delta
 *   imag[16..23]← environment: plasma state, temp gradient, manifold pressure, phase spread
 *
 * High mechanical curvature (unexpected resonance, shear spike, backflow)
 * produces the same QUARANTINE or ESCALATE signal as a rogue AI agent.
 * The governance dashboard sees both on the same Poincaré disk.
 *
 * Source: docs/research/magnetic_sheathed_fiber_optic_space_tether_2026-06-01.md
 *         scripts/research/jansen_linkage_sim.py (simulation: σ=0.941, asym=1.000)
 */

import {
  ContextBundle,
  IdentityContext,
  TemporalContext,
  EnvironmentContext,
} from './contextBundle.js';

// ─── Tether telemetry payload ─────────────────────────────────────────────────

/**
 * Braid chirality: which helical winding direction is dominant.
 * Mirrors IdentityContext.elevated (asymmetric state = elevated risk).
 */
export type BraidChirality = 'CW' | 'CCW' | 'NEUTRAL';

/**
 * Operating mode of the tether: what it is nominally doing right now.
 * Becomes the real-axis intent text.
 */
export type TetherMode =
  | 'stable_orbit'
  | 'generating_power'
  | 'thrusting'
  | 'deployment'
  | 'retrieval'
  | 'reentry_transition'
  | 'emergency_damping';

/**
 * Live telemetry snapshot from a multifunction electrodynamic tether.
 *
 * FBG strain readings → temporal history (what the tether has been doing).
 * Strandbeest bracket torques → environmental state (what physics is happening now).
 * Plasma / thermal / manifold → environment context.
 * Braid state → identity/configuration.
 */
export interface TetherTelemetry {
  /** Operating mode at time of snapshot — maps to the real-axis intent text. */
  mode: TetherMode;

  /** Optional pre-computed intent embedding for the mode (caller provides). */
  modeEmbedding?: number[];

  // ── FBG strain readings ──────────────────────────────────────────────────
  /** Normalized strain at up to 8 sensing points along the tether (0=unstrained, 1=limit). */
  strainReadings: number[]; // length ≤ 8

  /** Seconds since the last N strain snapshots (oldest first, up to 5). */
  strainTimestamps: number[]; // length ≤ 5; maps to TemporalContext.recentActionTimestamps

  // ── Strandbeest bracket states ───────────────────────────────────────────
  /**
   * Normalized rectified torque output at each phi-graded bracket station (0=none, 1=max).
   * Non-zero values mean the linkage is actively converting wave energy.
   */
  bracketTorques: number[]; // length ≤ 8; up to 8 bracket stations

  /**
   * Phase spread across the bracket array (0=all in phase → bad, 1=maximally spread → good).
   * Near-zero means the tether is locking onto one resonant wavelength.
   */
  bracketPhaseSpread: number; // [0,1]

  // ── Curvature proxy ──────────────────────────────────────────────────────
  /**
   * Mechanical curvature proxy: weighted sum of strain deltas and torque variance.
   * Mirrors ContextBundleCurvature in the software pipeline.
   * 0 = perfectly flat/stable, 1 = maximum expected deviation.
   */
  curvatureProxy: number; // [0,1]

  /** Rate of change of curvature (0=steady, positive=growing, negative=damping). */
  curvatureDelta: number; // [-1,1] normalized

  // ── Plasma throat / electron funnel ─────────────────────────────────────
  /** Normalized plasma current at each throat segment (0=none, 1=max safe). */
  plasmaCurrent: number; // [0,1]

  /** Whether a plasma discharge event is active (risk=elevated). */
  dischargeActive: boolean;

  // ── Thermal / gas cell state ─────────────────────────────────────────────
  /** Normalized temperature gradient across the honeycomb capillary wall (0=uniform). */
  tempGradient: number; // [0,1]

  /** Manifold pressure relative to design operating point (0=nominal, 1=max). */
  manifoldPressure: number; // [0,1]

  /** Backflow fraction at pore layer (0=clean one-way, 1=full backflow). */
  poreBackflow: number; // [0,1]

  // ── Structural / braid identity ──────────────────────────────────────────
  /** Dominant braid chirality (CW / CCW / NEUTRAL). */
  chirality: BraidChirality;

  /** Whether the spine seam reference shows unexpected twist. */
  spineSeamTwisted: boolean;

  /** Number of active bracket stations (vs total deployed). */
  activeBrackets: number;

  /** Total bracket stations deployed. */
  totalBrackets: number;

  /** Whether the phi-graded lattice is intact (false = one or more stations jammed). */
  phiLatticeIntact: boolean;
}

// ─── Risk annotation ──────────────────────────────────────────────────────────

/**
 * Tether-specific risk classes. Map to TemporalContext.recentClasses.
 * Ordered from safe to adversarial to match CLASS_RISK in contextBundle.ts.
 */
const TETHER_CLASS_RISK: Record<string, string> = {
  stable_orbit: 'observe',
  generating_power: 'read',
  thrusting: 'write',
  deployment: 'write',
  retrieval: 'write',
  reentry_transition: 'deploy',
  emergency_damping: 'destructive',
  resonance_spike: 'deploy',
  plasma_discharge: 'deploy',
  pore_backflow: 'write',
  spine_twist: 'network',
  bracket_jam: 'deploy',
  curvature_high: 'deploy',
};

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.max(lo, Math.min(hi, v));
}

// ─── Identity context builder ─────────────────────────────────────────────────

/**
 * Maps structural identity of the tether to IdentityContext.
 *
 * IdentityContext fields used:
 *   principalHash   ← derived from chirality + bracket count (stable ID for this config)
 *   roles           ← active tether capabilities (generating, thrusting, sensing, damping)
 *   canWrite        ← tether can act on orbit (thrusting or deployment active)
 *   canDeploy       ← deployment mode
 *   canDestroy      ← emergency damping (high-risk state)
 *   elevated        ← unexpected twist or jammed brackets
 */
function tetherIdentityContext(t: TetherTelemetry): Partial<IdentityContext> {
  const chirMap: Record<BraidChirality, string> = { CW: 'a1b2', CCW: 'c3d4', NEUTRAL: 'e5f6' };
  const principalHash = `${chirMap[t.chirality]}${t.totalBrackets.toString(16).padStart(2, '0')}00`;

  const roles: string[] = [];
  if (t.plasmaCurrent > 0.1) roles.push('generating');
  if (t.mode === 'thrusting') roles.push('thrusting');
  if (t.strainReadings.length > 0) roles.push('sensing');
  if (t.bracketTorques.some((v) => v > 0.1)) roles.push('damping');
  if (t.mode === 'deployment' || t.mode === 'retrieval') roles.push('deployment_active');

  return {
    principalHash,
    roles,
    canWrite: t.mode === 'thrusting' || t.mode === 'deployment' || t.mode === 'retrieval',
    canDeploy: t.mode === 'deployment',
    canDestroy: t.mode === 'emergency_damping',
    elevated: t.spineSeamTwisted || !t.phiLatticeIntact,
  };
}

// ─── Temporal context builder ─────────────────────────────────────────────────

/**
 * Maps recent strain history + curvature sequence to TemporalContext.
 *
 * Each FBG strain reading becomes one "prior action" in the sequence.
 * High strain → destructive class. Low strain → observe class.
 */
function tetherTemporalContext(t: TetherTelemetry): Partial<TemporalContext> {
  const strainClasses = t.strainReadings.slice(0, 5).map((s) => {
    if (s > 0.8) return 'destructive';
    if (s > 0.6) return 'deploy';
    if (s > 0.4) return 'write';
    if (s > 0.2) return 'network';
    return 'observe';
  });

  // Recent intents: describe what the strain reading implied
  const recentIntents = t.strainReadings.slice(0, 5).map((s, i) => `strain_${i}:${s.toFixed(3)}`);

  const secondsSinceLast =
    t.strainTimestamps.length > 0 ? t.strainTimestamps[t.strainTimestamps.length - 1] : 60;

  return {
    recentActionTimestamps: t.strainTimestamps.map((dt) =>
      new Date(Date.now() - dt * 1000).toISOString()
    ),
    recentIntents,
    recentClasses: strainClasses,
    secondsSinceLast: clamp(secondsSinceLast, 0, 300),
  };
}

// ─── Environment context builder ─────────────────────────────────────────────

/**
 * Maps plasma/thermal/manifold/bracket state to EnvironmentContext.
 *
 * tier:
 *   production  = stable_orbit / generating_power (normal operations)
 *   staging     = thrusting / deployment (controlled elevated state)
 *   development = retrieval / reentry_transition (managed uncertain state)
 *   local       = emergency_damping (unplanned, degraded mode)
 */
function tetherEnvironmentContext(t: TetherTelemetry): Partial<EnvironmentContext> {
  const tierMap: Record<TetherMode, EnvironmentContext['tier']> = {
    stable_orbit: 'production',
    generating_power: 'production',
    thrusting: 'staging',
    deployment: 'staging',
    retrieval: 'development',
    reentry_transition: 'development',
    emergency_damping: 'local',
  };

  // Active connections: each bracket station + each plasma throat
  const activeSensors: string[] = [];
  t.bracketTorques.forEach((_, i) => activeSensors.push(`bracket_${i}`));
  if (t.plasmaCurrent > 0) activeSensors.push('plasma_throat');
  if (t.strainReadings.length > 0) activeSensors.push('fbg_array');

  const connectionHashes = activeSensors.map((s) =>
    s
      .split('')
      .reduce((h, c) => ((h << 5) - h + c.charCodeAt(0)) | 0, 0)
      .toString(16)
      .slice(0, 4)
  );

  return {
    tier: tierMap[t.mode],
    activeConnectionHashes: connectionHashes,
    mutationInProgress: t.mode === 'deployment' || t.mode === 'retrieval' || t.dischargeActive,
    openWriteTransactions: t.bracketTorques.filter((v) => v > 0.3).length,
    activeEnvGroups: [
      ...(t.plasmaCurrent > 0.1 ? ['plasma'] : []),
      ...(t.tempGradient > 0.3 ? ['thermal'] : []),
      ...(t.bracketPhaseSpread < 0.2 ? ['resonance_risk'] : []),
      ...(t.poreBackflow > 0.1 ? ['backflow'] : []),
      'fbg',
      'phi_lattice',
    ],
  };
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Convert a live tether telemetry snapshot to a ContextBundle.
 *
 * The resulting bundle feeds straight into bundleToFeatures() → layer1ComplexState()
 * → the full 14-layer pipeline → GeodesicDecisionBundle.
 *
 * @example
 *   const bundle = tetherTelemetryToBundle(snapshot);
 *   const features = bundleToFeatures(bundle);
 *   const result = runFullPipeline14(features, BUNDLE_PIPELINE_CONFIG);
 *   const decision = harmonicScoreToGeodesicDecision(result.H, result.d_H);
 *   // decision.decision is ALLOW | QUARANTINE | ESCALATE | DENY
 */
export function tetherTelemetryToBundle(t: TetherTelemetry): ContextBundle {
  return {
    intentText: t.mode.replace(/_/g, ' '),
    intentEmbedding: t.modeEmbedding,
    identity: tetherIdentityContext(t),
    temporal: tetherTemporalContext(t),
    environment: tetherEnvironmentContext(t),
  };
}

/**
 * Compute a standalone mechanical curvature risk score [0,1].
 *
 * This is the hardware analogue of ContextBundleCurvature in the
 * software pipeline. High score → QUARANTINE or ESCALATE on the dashboard.
 *
 * Formula:
 *   curvature = w_c * curvatureProxy
 *             + w_d * (curvatureDelta > 0 ? curvatureDelta : 0)   // growing only
 *             + w_p * poreBackflow
 *             + w_r * (1 - bracketPhaseSpread)                    // low spread = locked resonance
 *             + w_t * tempGradient
 *             + w_b * (1 - activeBrackets / totalBrackets)        // lost brackets
 */
export function mechanicalCurvatureScore(t: TetherTelemetry): number {
  const activeFrac = t.totalBrackets > 0 ? t.activeBrackets / t.totalBrackets : 0;

  const score =
    0.3 * clamp(t.curvatureProxy) +
    0.2 * clamp(t.curvatureDelta > 0 ? t.curvatureDelta : 0) +
    0.15 * clamp(t.poreBackflow) +
    0.15 * clamp(1 - t.bracketPhaseSpread) + // low spread → resonance risk
    0.1 * clamp(t.tempGradient) +
    0.1 * clamp(1 - activeFrac); // lost brackets → structural risk

  return clamp(score);
}

/**
 * Map mechanical curvature score to the same tier labels as the AI pipeline.
 * Thresholds mirror the harmonic wall / geodesic decision surface.
 */
export function mechanicalCurvatureTier(
  score: number
): 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY' {
  if (score < 0.2) return 'ALLOW';
  if (score < 0.45) return 'QUARANTINE';
  if (score < 0.72) return 'ESCALATE';
  return 'DENY';
}

/**
 * Summarize telemetry to a compact audit string for logging.
 * Same purpose as toAuditReceipt() in geodesicDecision.ts.
 */
export function tetherAuditLine(t: TetherTelemetry): string {
  const score = mechanicalCurvatureScore(t);
  const tier = mechanicalCurvatureTier(score);
  const maxStrain = t.strainReadings.length > 0 ? Math.max(...t.strainReadings).toFixed(3) : '—';
  const maxTorque = t.bracketTorques.length > 0 ? Math.max(...t.bracketTorques).toFixed(3) : '—';
  return (
    `[TETHER] mode=${t.mode} curv=${score.toFixed(3)} tier=${tier} ` +
    `strain_max=${maxStrain} torque_max=${maxTorque} ` +
    `phase_spread=${t.bracketPhaseSpread.toFixed(3)} ` +
    `plasma=${t.plasmaCurrent.toFixed(3)} backflow=${t.poreBackflow.toFixed(3)}`
  );
}

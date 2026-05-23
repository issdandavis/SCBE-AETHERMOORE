/**
 * @file geosealOperatorSpace.ts
 * @module geosealOperatorSpace
 * @layer Layer 3, Layer 13
 *
 * GeoSeal Operator System-Space Model
 *
 * Extends GeoSeal's geographic ring model to cover the operator's position in
 * **system topology space** — not physical coordinates, but the structural
 * location of the operator: which access plane they arrived through (web /
 * terminal / app / API) and whether they are authenticated.
 *
 * The access plane + auth state together determine:
 *   - A file-system topology (what paths are reachable and writable)
 *   - A governance ring (core / outer / restricted / blocked)
 *   - A deterministic space ID analogous to the geographic geoid
 *   - Governance flags that surface cross-plane claims and auth anomalies
 *
 * Why this matters:
 *   A web-anonymous operator claiming access to /home/user/documents is
 *   structurally impossible — their sandbox grants no native FS at all.
 *   The governance layer should catch the claim before it reaches the FS.
 *   Similarly, a terminal+sudo operator carries elevated risk that warrants
 *   its own flag even at high trust, so downstream layers can gate writes.
 */

import * as crypto from 'node:crypto';

// ─────────────────────────────────────────────────────────────────────────────
// Enumerations
// ─────────────────────────────────────────────────────────────────────────────

/**
 * The structural plane through which an operator connects to the system.
 * Each plane has a fixed, deterministic FS topology regardless of auth state.
 */
export type OperatorAccessPlane = 'web' | 'terminal' | 'app' | 'api';

/**
 * Authentication status of the operator at session time.
 * Drives trust score and writable-path access within each plane.
 */
export type OperatorAuthState = 'authenticated' | 'anonymous' | 'service_account' | 'sudo';

/** Degree to which the operator's file-system access is sandboxed. */
export type SandboxLevel = 'none' | 'partial' | 'full';

/** GeoSeal governance ring — mirrors the geographic ring vocabulary. */
export type OperatorRing = 'core' | 'outer' | 'restricted' | 'blocked';

// ─────────────────────────────────────────────────────────────────────────────
// FS Topology
// ─────────────────────────────────────────────────────────────────────────────

/**
 * File-system access topology derived from the operator's system-space position.
 * Describes structural constraints, not a list of guaranteed paths.
 */
export interface FsTopology {
  /** How tightly sandboxed is this operator's FS access? */
  sandboxLevel: SandboxLevel;
  /**
   * Root paths reachable in principle for this plane+auth combination.
   * Empty for full-sandbox planes (browser context).
   * These are canonical examples — real enforcement is the caller's job.
   */
  accessibleRoots: string[];
  /** Subset of accessibleRoots where writes are permitted by default. */
  writablePaths: string[];
  /** Whether FS state persists after the session ends. */
  persistsAcrossSessions: boolean;
  /**
   * True when the operator can only write to a temporary/ephemeral location
   * (e.g. /tmp or browser OPFS without explicit permission grant).
   */
  tempOnly: boolean;
  /**
   * OS-level mount points visible to this operator.
   * Empty for browser and anonymous-API planes.
   */
  mountPoints: string[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Input / Output types
// ─────────────────────────────────────────────────────────────────────────────

export interface OperatorSpaceInput {
  /** How the operator is connected. */
  accessPlane: OperatorAccessPlane;
  /** Auth state at session time. */
  authState: OperatorAuthState;
  /**
   * Opaque session fingerprint for space-ID derivation (e.g. session cookie
   * hash, terminal session UUID, app install ID). Must NOT contain PII.
   * If omitted, an anonymous fingerprint is derived from plane+auth only.
   */
  sessionFingerprint?: string;
  /** Unix epoch ms when the session was authenticated. Null for anonymous. */
  loginTimeMs?: number;
  /**
   * Paths the operator is claiming access to.
   * Used for cross-plane claim validation.
   */
  claimedPaths?: string[];
}

/** Governance flags surfaced by the space evaluation. */
export type GovernanceFlag =
  | 'ELEVATED_TERMINAL' // terminal + sudo
  | 'UNAUTHENTICATED_WEB' // web + anonymous (highest risk profile)
  | 'UNAUTHENTICATED_API' // api + anonymous
  | 'CROSS_PLANE_CLAIM' // claimed paths inconsistent with access plane
  | 'SESSION_MISSING_LOGIN_TIME' // auth says authenticated but no loginTimeMs
  | 'TEMP_FS_ONLY' // full sandbox, all writes are ephemeral
  | 'SERVICE_ACCOUNT_ELEVATED'; // service_account on terminal plane

export interface OperatorSpaceDecision {
  /** Canonical ring for downstream governance gates. */
  ring: OperatorRing;
  /** Composite trust score [0.0, 1.0]. Higher = more trusted. */
  trustScore: number;
  /**
   * Deterministic identifier for this operator's system-space position.
   * Analogous to the geographic geoid — stable across calls with the same
   * plane+auth+fingerprint, usable as a receipt anchor.
   */
  spaceId: string;
  /** Derived FS topology for this plane + auth combination. */
  fsTopology: FsTopology;
  /** Governance flags raised during evaluation. */
  governanceFlags: GovernanceFlag[];
  /** Machine-readable status tag. */
  status: string;
  /** Human-readable explanation. */
  reason: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// FS topology derivation
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Returns the structural FS topology for a given plane + auth combination.
 * These are deterministic governance constraints, not live filesystem probes.
 */
export function derivefsTopology(plane: OperatorAccessPlane, auth: OperatorAuthState): FsTopology {
  switch (plane) {
    case 'web':
      // Browser context — OPFS only (sandboxed, origin-scoped, no native FS)
      return {
        sandboxLevel: 'full',
        accessibleRoots: [], // no native root access
        writablePaths: [], // OPFS is not representable as a native path
        persistsAcrossSessions: auth === 'authenticated', // OPFS persists when logged in
        tempOnly: auth === 'anonymous',
        mountPoints: [], // no mount points visible in browser
      };

    case 'terminal':
      if (auth === 'sudo') {
        return {
          sandboxLevel: 'none',
          accessibleRoots: ['/', 'C:\\'],
          writablePaths: ['/', 'C:\\'],
          persistsAcrossSessions: true,
          tempOnly: false,
          mountPoints: ['/', '/proc', '/sys', '/dev', 'C:\\', 'D:\\'],
        };
      }
      if (auth === 'authenticated' || auth === 'service_account') {
        return {
          sandboxLevel: 'none',
          accessibleRoots: ['~', '/home', '/var', '/tmp', 'C:\\Users', 'C:\\ProgramData'],
          writablePaths: ['~', '/tmp', 'C:\\Users\\{user}', 'C:\\Temp'],
          persistsAcrossSessions: true,
          tempOnly: false,
          mountPoints: ['/', 'C:\\', 'D:\\'],
        };
      }
      // anonymous terminal — /tmp only, no persistent FS
      return {
        sandboxLevel: 'partial',
        accessibleRoots: ['/tmp', 'C:\\Temp'],
        writablePaths: ['/tmp', 'C:\\Temp'],
        persistsAcrossSessions: false,
        tempOnly: true,
        mountPoints: [],
      };

    case 'app':
      if (auth === 'anonymous') {
        return {
          sandboxLevel: 'partial',
          accessibleRoots: [],
          writablePaths: [],
          persistsAcrossSessions: false,
          tempOnly: true,
          mountPoints: [],
        };
      }
      // app sandbox — app-data directory only (no system paths)
      return {
        sandboxLevel: 'partial',
        accessibleRoots: ['~/AppData', '~/.local/share', '~/Library/Application Support'],
        writablePaths: ['~/AppData/{app}', '~/.local/share/{app}'],
        persistsAcrossSessions: true,
        tempOnly: false,
        mountPoints: [],
      };

    case 'api':
      // API callers have no direct FS — server-side FS only, mediated by the service
      return {
        sandboxLevel: auth === 'anonymous' ? 'full' : 'partial',
        accessibleRoots: [],
        writablePaths: [],
        persistsAcrossSessions: false,
        tempOnly: true,
        mountPoints: [],
      };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Ring + trust derivation
// ─────────────────────────────────────────────────────────────────────────────

interface RingProfile {
  ring: OperatorRing;
  trustScore: number;
}

/** Lookup table: plane → auth → ring + trust */
const RING_TABLE: Record<OperatorAccessPlane, Record<OperatorAuthState, RingProfile>> = {
  terminal: {
    sudo: { ring: 'core', trustScore: 0.95 },
    authenticated: { ring: 'core', trustScore: 0.85 },
    service_account: { ring: 'core', trustScore: 0.8 },
    anonymous: { ring: 'restricted', trustScore: 0.35 },
  },
  app: {
    authenticated: { ring: 'outer', trustScore: 0.7 },
    service_account: { ring: 'outer', trustScore: 0.65 },
    anonymous: { ring: 'restricted', trustScore: 0.25 },
    sudo: { ring: 'outer', trustScore: 0.7 }, // apps don't have sudo; treat as authenticated
  },
  api: {
    service_account: { ring: 'core', trustScore: 0.8 },
    authenticated: { ring: 'outer', trustScore: 0.7 },
    anonymous: { ring: 'blocked', trustScore: 0.05 },
    sudo: { ring: 'outer', trustScore: 0.7 }, // API + sudo treated as authenticated
  },
  web: {
    authenticated: { ring: 'outer', trustScore: 0.6 },
    anonymous: { ring: 'blocked', trustScore: 0.05 },
    service_account: { ring: 'outer', trustScore: 0.55 },
    sudo: { ring: 'outer', trustScore: 0.6 }, // web + sudo treated as authenticated
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Space ID
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Deterministic space identifier for this operator's system-space position.
 * Analogous to the geographic geoid — stable across calls with the same inputs,
 * usable as a receipt anchor in audit logs.
 */
function deriveSpaceId(
  plane: OperatorAccessPlane,
  auth: OperatorAuthState,
  fingerprint: string
): string {
  const payload = `${plane}|${auth}|${fingerprint}`;
  return crypto.createHash('sha256').update(payload, 'utf8').digest('hex').slice(0, 16);
}

// ─────────────────────────────────────────────────────────────────────────────
// Cross-plane claim validation
// ─────────────────────────────────────────────────────────────────────────────

const WEB_NATIVE_PATH_PATTERN = /^[/\\]|^[A-Za-z]:\\/;
const URL_PATTERN = /^https?:\/\//i;
const UNC_PATTERN = /^\\\\/;

/**
 * Returns true if the claimed path is structurally inconsistent with the
 * operator's access plane.
 *
 * - Web operators cannot claim native FS paths.
 * - API-anonymous operators cannot claim any paths.
 * - Terminal operators cannot claim bare HTTP URLs as file paths.
 */
function isPathCrossPlane(path: string, plane: OperatorAccessPlane): boolean {
  switch (plane) {
    case 'web':
      // Browser has no native FS — claiming any local or UNC path is a violation
      return WEB_NATIVE_PATH_PATTERN.test(path) || UNC_PATTERN.test(path);
    case 'api':
      // API callers have no direct FS at all
      return true;
    case 'terminal':
    case 'app':
      // Terminal/app operators should not be claiming bare HTTP URLs as file paths
      return URL_PATTERN.test(path);
    default:
      return false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Governance flag evaluation
// ─────────────────────────────────────────────────────────────────────────────

function evaluateFlags(
  plane: OperatorAccessPlane,
  auth: OperatorAuthState,
  fsTopology: FsTopology,
  claimedPaths: string[],
  loginTimeMs: number | undefined
): GovernanceFlag[] {
  const flags: GovernanceFlag[] = [];

  if (plane === 'terminal' && auth === 'sudo') flags.push('ELEVATED_TERMINAL');
  if (plane === 'terminal' && auth === 'service_account') flags.push('SERVICE_ACCOUNT_ELEVATED');
  if (plane === 'web' && auth === 'anonymous') flags.push('UNAUTHENTICATED_WEB');
  if (plane === 'api' && auth === 'anonymous') flags.push('UNAUTHENTICATED_API');
  if (fsTopology.tempOnly) flags.push('TEMP_FS_ONLY');

  if ((auth === 'authenticated' || auth === 'sudo') && loginTimeMs == null) {
    flags.push('SESSION_MISSING_LOGIN_TIME');
  }

  const crossPlanePaths = claimedPaths.filter((p) => isPathCrossPlane(p, plane));
  if (crossPlanePaths.length > 0) flags.push('CROSS_PLANE_CLAIM');

  return flags;
}

// ─────────────────────────────────────────────────────────────────────────────
// Primary evaluation function
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Evaluate an operator's system-space position and return a governance decision.
 *
 * The decision integrates with GeoSeal's ring model: `ring` maps directly to
 * the same ALLOW/QUARANTINE/ESCALATE/DENY tier thresholds used in L13.
 *
 * @example
 * ```ts
 * const decision = evaluateOperatorSpace({
 *   accessPlane: 'terminal',
 *   authState: 'authenticated',
 *   sessionFingerprint: sessionUUID,
 *   loginTimeMs: Date.now(),
 *   claimedPaths: ['/home/user/docs'],
 * });
 * // decision.ring === 'core', decision.trustScore === 0.85
 * ```
 */
export function evaluateOperatorSpace(input: OperatorSpaceInput): OperatorSpaceDecision {
  const { accessPlane, authState, sessionFingerprint, loginTimeMs, claimedPaths = [] } = input;

  const fingerprint =
    sessionFingerprint && sessionFingerprint.length > 0
      ? sessionFingerprint
      : `${accessPlane}:${authState}:anon`;

  const spaceId = deriveSpaceId(accessPlane, authState, fingerprint);
  const fsTopology = derivefsTopology(accessPlane, authState);
  const { ring, trustScore } = RING_TABLE[accessPlane][authState];

  const flags = evaluateFlags(accessPlane, authState, fsTopology, claimedPaths, loginTimeMs);

  // Penalize trust score for governance violations
  let effectiveTrust = trustScore;
  if (flags.includes('CROSS_PLANE_CLAIM')) effectiveTrust = Math.max(0, effectiveTrust - 0.3);
  if (flags.includes('SESSION_MISSING_LOGIN_TIME'))
    effectiveTrust = Math.max(0, effectiveTrust - 0.15);

  const effectiveRing: OperatorRing =
    effectiveTrust < 0.1 ? 'blocked' : effectiveTrust <= 0.4 ? 'restricted' : ring;

  const status = `operator_space_${accessPlane}_${authState}`;
  const reason =
    `plane=${accessPlane} auth=${authState} sandbox=${fsTopology.sandboxLevel}` +
    (flags.length > 0 ? ` flags=[${flags.join(',')}]` : '');

  return {
    ring: effectiveRing,
    trustScore: Math.round(effectiveTrust * 10000) / 10000,
    spaceId,
    fsTopology,
    governanceFlags: flags,
    status,
    reason,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Serialisation helpers
// ─────────────────────────────────────────────────────────────────────────────

/** Convert an OperatorSpaceDecision to a JSON-friendly plain object. */
export function operatorSpaceToRecord(decision: OperatorSpaceDecision): Record<string, unknown> {
  return {
    ring: decision.ring,
    trust_score: decision.trustScore,
    space_id: decision.spaceId,
    sandbox_level: decision.fsTopology.sandboxLevel,
    accessible_roots: decision.fsTopology.accessibleRoots,
    writable_paths: decision.fsTopology.writablePaths,
    persists_across_sessions: decision.fsTopology.persistsAcrossSessions,
    temp_only: decision.fsTopology.tempOnly,
    mount_points: decision.fsTopology.mountPoints,
    governance_flags: decision.governanceFlags,
    status: decision.status,
    reason: decision.reason,
  };
}

/**
 * Maps an OperatorRing to the L13 governance tier vocabulary.
 * Integrates operator-space decisions into the main 14-layer pipeline.
 */
export function ringToGovernanceTier(
  ring: OperatorRing
): 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY' {
  switch (ring) {
    case 'core':
      return 'ALLOW';
    case 'outer':
      return 'QUARANTINE';
    case 'restricted':
      return 'ESCALATE';
    case 'blocked':
      return 'DENY';
  }
}

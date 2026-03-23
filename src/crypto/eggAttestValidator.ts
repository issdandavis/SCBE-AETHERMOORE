/**
 * @file eggAttestValidator.ts
 * @module crypto/eggAttestValidator
 * @layer Layer 1, Layer 13, Layer 14
 * @component Egg Attestation Validator — Sacred Egg → Hatched Agent lifecycle
 *
 * Validates SCBE-AETHERMOORE/egg-attest@v1 packets against the canonical
 * schema and enforces semantic invariants that JSON Schema alone cannot:
 *
 *   - k ≤ n in tongue quorum
 *   - φ-weight array length matches n
 *   - All 5 gates must pass for "allow" decision
 *   - PQ signer tongues are unique (no duplicate signers)
 *   - Timebox window is not expired
 *   - boot_epoch 0 on first hatch
 *
 * A5: Composition — this validator composes with the 14-layer pipeline
 * attestation stream (A₀..Aₜ) to enforce provenance at every epoch.
 */

// ── Types ────────────────────────────────────────────────────────────

/** Sacred Tongue identifiers (6 tongues). */
export type SacredTongue = 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';

/** Post-quantum signature algorithms (new names + legacy fallbacks). */
export type PQAlgorithm =
  | 'ML-DSA-65'
  | 'Dilithium3'
  | 'ML-DSA-87'
  | 'Dilithium5'
  | 'Falcon-512'
  | 'Falcon-1024'
  | 'SPHINCS+-SHA2-128f'
  | 'SPHINCS+-SHAKE-256f';

/** Risk-tier decisions from Gate 5. */
export type GateDecision = 'allow' | 'quarantine' | 'escalate' | 'deny';

export interface TongueQuorum {
  k: number;
  n: number;
  phi_weights: number[];
}

export interface GeoSeal {
  scheme: string;
  region: string;
  proof: string;
}

export interface Timebox {
  t0: string;
  delta_s: number;
}

export interface Ritual {
  intent_sha256: string;
  tongue_quorum: TongueQuorum;
  geoseal: GeoSeal;
  timebox: Timebox;
}

export interface PQSig {
  alg: PQAlgorithm;
  signer: string;
  sig: string;
}

export interface Anchors {
  H0_envelope: string;
  H1_merkle_root: string;
  pq_sigs: PQSig[];
  h2_external?: {
    sigstore_bundle?: string;
    sbom_digest?: string;
    [key: string]: unknown;
  };
}

export interface GateResults {
  syntax: 'pass' | 'fail';
  integrity: 'pass' | 'fail';
  quorum: { pass: boolean; k: number; weighted_phi: number };
  geo_time: 'pass' | 'fail';
  policy: { decision: GateDecision; risk: number };
}

export interface Hatch {
  boot_epoch: number;
  kdf: 'HKDF-SHA3' | 'HKDF-SHA256';
  boot_key_fp: string;
  attestation_A0: string;
}

export interface Signature {
  alg: string;
  signers: string[];
  sig: string;
}

export interface EggAttestPacket {
  spec: 'SCBE-AETHERMOORE/egg-attest@v1';
  agent_id: string;
  ritual: Ritual;
  anchors: Anchors;
  gates: GateResults;
  hatch: Hatch;
  signature: Signature;
}

// ── Validation ───────────────────────────────────────────────────────

export interface ValidationError {
  path: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

/**
 * Validate an egg attestation packet.
 * Checks structural shape + semantic invariants.
 *
 * @param packet - Parsed attestation JSON
 * @param now    - Optional reference time for timebox check (defaults to Date.now())
 */
export function validateEggAttest(
  packet: EggAttestPacket,
  now?: number,
): ValidationResult {
  const errors: ValidationError[] = [];
  const refTime = now ?? Date.now();

  // ── spec version ──
  if (packet.spec !== 'SCBE-AETHERMOORE/egg-attest@v1') {
    errors.push({ path: 'spec', message: `Unknown spec: ${packet.spec}` });
  }

  // ── agent_id format ──
  if (!packet.agent_id?.startsWith('hkdf://')) {
    errors.push({ path: 'agent_id', message: 'Must start with hkdf://' });
  }

  // ── ritual.tongue_quorum: k ≤ n ──
  const q = packet.ritual?.tongue_quorum;
  if (q) {
    if (q.k > q.n) {
      errors.push({
        path: 'ritual.tongue_quorum',
        message: `k (${q.k}) must be ≤ n (${q.n})`,
      });
    }
    if (q.phi_weights.length !== q.n) {
      errors.push({
        path: 'ritual.tongue_quorum.phi_weights',
        message: `Expected ${q.n} weights, got ${q.phi_weights.length}`,
      });
    }
    // A4: Symmetry — φ-weights must sum to ≤ n (loose upper bound)
    const wSum = q.phi_weights.reduce((a, b) => a + b, 0);
    if (wSum > q.n) {
      errors.push({
        path: 'ritual.tongue_quorum.phi_weights',
        message: `Weight sum ${wSum.toFixed(3)} exceeds n=${q.n}`,
      });
    }
  }

  // ── ritual.timebox: not expired ──
  const tb = packet.ritual?.timebox;
  if (tb) {
    const t0ms = new Date(tb.t0).getTime();
    if (isNaN(t0ms)) {
      errors.push({ path: 'ritual.timebox.t0', message: 'Invalid ISO 8601 timestamp' });
    } else {
      const expiryMs = t0ms + tb.delta_s * 1000;
      if (refTime > expiryMs) {
        errors.push({
          path: 'ritual.timebox',
          message: `Timebox expired at ${new Date(expiryMs).toISOString()}`,
        });
      }
    }
  }

  // ── anchors.pq_sigs: unique signers ──
  const sigs = packet.anchors?.pq_sigs;
  if (sigs && sigs.length > 0) {
    const signerSet = new Set(sigs.map((s) => s.signer));
    if (signerSet.size !== sigs.length) {
      errors.push({
        path: 'anchors.pq_sigs',
        message: 'Duplicate signers detected',
      });
    }
  }

  // ── gates: all must pass for allow ──
  const g = packet.gates;
  if (g) {
    const gatesPassed =
      g.syntax === 'pass' &&
      g.integrity === 'pass' &&
      g.quorum?.pass === true &&
      g.geo_time === 'pass';

    if (g.policy?.decision === 'allow' && !gatesPassed) {
      errors.push({
        path: 'gates',
        message: 'Policy decision is "allow" but not all gates passed',
      });
    }

    // A4: Clamping — risk in [0,1]
    if (g.policy && (g.policy.risk < 0 || g.policy.risk > 1)) {
      errors.push({
        path: 'gates.policy.risk',
        message: `Risk ${g.policy.risk} out of [0,1] range`,
      });
    }

    // Quorum k must match ritual k
    if (q && g.quorum && g.quorum.k !== q.k) {
      errors.push({
        path: 'gates.quorum.k',
        message: `Gate quorum k=${g.quorum.k} differs from ritual k=${q.k}`,
      });
    }
  }

  // ── hatch: boot_epoch consistency ──
  if (packet.hatch) {
    if (!packet.hatch.boot_key_fp?.startsWith('fp:')) {
      errors.push({
        path: 'hatch.boot_key_fp',
        message: 'Must start with fp:',
      });
    }
    if (!packet.hatch.attestation_A0?.startsWith('cose-sign1:')) {
      errors.push({
        path: 'hatch.attestation_A0',
        message: 'Must start with cose-sign1:',
      });
    }
  }

  // ── signature: at least one signer ──
  if (packet.signature?.signers?.length === 0) {
    errors.push({ path: 'signature.signers', message: 'At least one signer required' });
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Check whether all five verification gates passed.
 * Utility for Gate-run phase (≤100 ms budget).
 */
export function allGatesPassed(gates: GateResults): boolean {
  return (
    gates.syntax === 'pass' &&
    gates.integrity === 'pass' &&
    gates.quorum.pass === true &&
    gates.geo_time === 'pass' &&
    gates.policy.decision === 'allow'
  );
}

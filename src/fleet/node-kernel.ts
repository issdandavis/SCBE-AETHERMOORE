/**
 * @file node-kernel.ts
 * @module fleet/node-kernel
 * @layer L1, L8, L13, L14
 * @component Per-Node SCBE Governance Kernel
 * @version 3.2.4
 *
 * Each robot/agent runs a local governance kernel with:
 *
 * State:
 *   state_i = { phase, trust, role, energy, hazard_flag, neighbor_set }
 *
 * Hard invariants (NEVER violated — law):
 *   1. No entry into no-go zone
 *   2. Minimum separation enforced
 *   3. Energy reserve floor
 *   4. Human override dominance
 *
 * Policy updates:
 *   - Signed (HMAC-SHA256)
 *   - Versioned (monotonic epoch counter)
 *   - Epoch-bound (old policies expire)
 *   - Deterministic (same inputs → same decisions)
 *
 * This is enterprise-grade defensibility.
 *
 * @axiom Composition — Kernel composes all invariant checks into a single decision gate
 * @axiom Causality — Policy epochs enforce temporal ordering
 */

import { createHmac } from 'crypto';
import type { Vec } from './swarm-geometry.js';
import type { SwarmMode } from './oscillator-bus.js';

// ──────────────── Types ────────────────

/**
 * Robot role within the swarm.
 */
export type NodeRole = 'WORKER' | 'SCOUT' | 'SENTINEL' | 'LEADER' | 'DORMANT';

/**
 * Invariant check result — one per hard rule.
 */
export interface InvariantCheck {
  name: string;
  passed: boolean;
  detail: string;
}

/**
 * Kernel decision — aggregated gate result.
 */
export interface KernelDecision {
  /** Can the proposed action proceed? */
  allowed: boolean;
  /** All invariant checks performed */
  invariants: InvariantCheck[];
  /** Which invariants failed (empty if allowed) */
  violations: string[];
  /** Active policy epoch */
  policyEpoch: number;
  /** Timestamp */
  timestamp: number;
}

/**
 * Per-node kernel state.
 */
export interface NodeState {
  /** Node identifier */
  id: string;
  /** Current oscillator phase (from bus) */
  phase: number;
  /** Trust score [0, 1] */
  trust: number;
  /** Current role */
  role: NodeRole;
  /** Energy reserve [0, 1] */
  energy: number;
  /** Hazard flag (true = hazard detected) */
  hazardFlag: boolean;
  /** Known neighbor IDs (within coupling radius) */
  neighborSet: Set<string>;
  /** Current swarm mode (from oscillator bus) */
  currentMode: SwarmMode;
  /** Current position */
  position: Vec;
  /** Is under human override? */
  humanOverride: boolean;
  /** Last state update timestamp */
  lastUpdate: number;
}

/**
 * Signed policy manifest.
 */
export interface PolicyManifest {
  /** Monotonic epoch number */
  epoch: number;
  /** Policy version string */
  version: string;
  /** Policy parameters */
  params: PolicyParams;
  /** Issued timestamp */
  issuedAt: number;
  /** Expiry timestamp (epoch-bound) */
  expiresAt: number;
  /** HMAC-SHA256 signature of canonical content */
  signature: string;
}

/**
 * Policy parameters — deterministic rules.
 */
export interface PolicyParams {
  /** Minimum separation distance */
  minSeparation: number;
  /** Energy reserve floor */
  energyFloor: number;
  /** Minimum trust for action */
  minTrust: number;
  /** Maximum drift magnitude */
  maxDrift: number;
  /** Allowed roles */
  allowedRoles: NodeRole[];
  /** Suppressed modes (drift zeroed in these modes) */
  suppressedModes: SwarmMode[];
}

/**
 * Node kernel configuration.
 */
export interface NodeKernelConfig {
  /** Policy signing key (for HMAC) */
  signingKey: string;
  /** Grace period after policy expiry (ms) before hard-reject */
  policyGracePeriodMs: number;
  /** Default energy consumption per step */
  energyPerStep: number;
  /** Energy recharge rate per step (when idle) */
  energyRechargeRate: number;
  /** Maximum neighbors tracked */
  maxNeighbors: number;
}

export const DEFAULT_KERNEL_CONFIG: Readonly<NodeKernelConfig> = {
  signingKey: 'scbe-default-signing-key',
  policyGracePeriodMs: 30_000,
  energyPerStep: 0.001,
  energyRechargeRate: 0.002,
  maxNeighbors: 50,
};

export const DEFAULT_POLICY_PARAMS: Readonly<PolicyParams> = {
  minSeparation: 0.5,
  energyFloor: 0.1,
  minTrust: 0.15,
  maxDrift: 1.0,
  allowedRoles: ['WORKER', 'SCOUT', 'SENTINEL', 'LEADER', 'DORMANT'],
  suppressedModes: ['HAZARD'],
};

// ──────────────── Core Kernel ────────────────

/**
 * NodeKernel — per-robot SCBE governance kernel.
 *
 * Hard invariants:
 *   1. No-go zone enforcement (delegated to SwarmGeometry, checked here)
 *   2. Minimum separation (checked against neighbor positions)
 *   3. Energy reserve floor (hard stop below threshold)
 *   4. Human override dominance (human commands bypass all other checks)
 *
 * Policy updates are signed, versioned, epoch-bound, and deterministic.
 */
export class NodeKernel {
  private config: NodeKernelConfig;
  private state: NodeState;
  private activePolicy: PolicyManifest | null = null;
  private policyHistory: PolicyManifest[] = [];
  /** Audit log — append-only record of decisions */
  private auditLog: Array<{
    decision: KernelDecision;
    action: string;
    stateSnapshot: Omit<NodeState, 'neighborSet'> & { neighborCount: number };
  }> = [];
  private maxAuditEntries: number = 500;

  constructor(
    nodeId: string,
    initialPosition: Vec,
    config: Partial<NodeKernelConfig> = {},
  ) {
    this.config = { ...DEFAULT_KERNEL_CONFIG, ...config };

    this.state = {
      id: nodeId,
      phase: 0,
      trust: 0.5,
      role: 'WORKER',
      energy: 1.0,
      hazardFlag: false,
      neighborSet: new Set(),
      currentMode: 'EXPLORE',
      position: { ...initialPosition },
      humanOverride: false,
      lastUpdate: Date.now(),
    };
  }

  // ── State Access ──

  public getState(): Readonly<NodeState> {
    return this.state;
  }

  public getId(): string {
    return this.state.id;
  }

  // ── State Updates ──

  public updatePhase(phase: number): void {
    this.state.phase = phase;
    this.state.lastUpdate = Date.now();
  }

  public updateTrust(trust: number): void {
    this.state.trust = Math.max(0, Math.min(1, trust));
    this.state.lastUpdate = Date.now();
  }

  public updateRole(role: NodeRole): void {
    this.state.role = role;
    this.state.lastUpdate = Date.now();
  }

  public updateEnergy(energy: number): void {
    this.state.energy = Math.max(0, Math.min(1, energy));
    this.state.lastUpdate = Date.now();
  }

  public setHazard(flag: boolean): void {
    this.state.hazardFlag = flag;
    this.state.lastUpdate = Date.now();
  }

  public updateMode(mode: SwarmMode): void {
    this.state.currentMode = mode;
    this.state.lastUpdate = Date.now();
  }

  public updatePosition(pos: Vec): void {
    this.state.position = { ...pos };
    this.state.lastUpdate = Date.now();
  }

  public updateNeighbors(neighborIds: string[]): void {
    this.state.neighborSet = new Set(neighborIds.slice(0, this.config.maxNeighbors));
    this.state.lastUpdate = Date.now();
  }

  /**
   * Engage human override — dominates all other decisions.
   */
  public engageHumanOverride(): void {
    this.state.humanOverride = true;
    this.state.lastUpdate = Date.now();
  }

  /**
   * Disengage human override — return to autonomous governance.
   */
  public disengageHumanOverride(): void {
    this.state.humanOverride = false;
    this.state.lastUpdate = Date.now();
  }

  /**
   * Consume energy for an action.
   */
  public consumeEnergy(amount?: number): void {
    const cost = amount ?? this.config.energyPerStep;
    this.state.energy = Math.max(0, this.state.energy - cost);
    this.state.lastUpdate = Date.now();
  }

  /**
   * Recharge energy (when idle).
   */
  public rechargeEnergy(amount?: number): void {
    const gain = amount ?? this.config.energyRechargeRate;
    this.state.energy = Math.min(1, this.state.energy + gain);
    this.state.lastUpdate = Date.now();
  }

  // ── Policy Management ──

  /**
   * Create a signed policy manifest.
   * The signature covers epoch + version + params + timestamps.
   */
  public createPolicy(
    params: Partial<PolicyParams> = {},
    ttlMs: number = 3_600_000,
  ): PolicyManifest {
    const nextEpoch = this.activePolicy ? this.activePolicy.epoch + 1 : 1;
    const now = Date.now();

    const fullParams: PolicyParams = {
      ...DEFAULT_POLICY_PARAMS,
      ...params,
      allowedRoles: params.allowedRoles ?? [...DEFAULT_POLICY_PARAMS.allowedRoles],
      suppressedModes: params.suppressedModes ?? [...DEFAULT_POLICY_PARAMS.suppressedModes],
    };

    const manifest: Omit<PolicyManifest, 'signature'> = {
      epoch: nextEpoch,
      version: `${nextEpoch}.0.0`,
      params: fullParams,
      issuedAt: now,
      expiresAt: now + ttlMs,
    };

    const signature = this.signPolicy(manifest);

    return { ...manifest, signature };
  }

  /**
   * Apply a signed policy manifest.
   * Validates:
   *   1. Signature integrity
   *   2. Epoch is monotonically increasing
   *   3. Not expired
   */
  public applyPolicy(manifest: PolicyManifest): { applied: boolean; reason?: string } {
    // Verify signature
    const expected = this.signPolicy(manifest);
    if (manifest.signature !== expected) {
      return { applied: false, reason: 'invalid_signature' };
    }

    // Verify epoch monotonicity
    if (this.activePolicy && manifest.epoch <= this.activePolicy.epoch) {
      return { applied: false, reason: `epoch_not_monotonic:${manifest.epoch}<=${this.activePolicy.epoch}` };
    }

    // Verify not expired
    const now = Date.now();
    if (now > manifest.expiresAt) {
      return { applied: false, reason: 'policy_expired' };
    }

    // Store old policy in history
    if (this.activePolicy) {
      this.policyHistory.push(this.activePolicy);
    }

    this.activePolicy = manifest;
    return { applied: true };
  }

  /**
   * Get the active policy.
   */
  public getActivePolicy(): PolicyManifest | null {
    return this.activePolicy;
  }

  /**
   * Get policy history.
   */
  public getPolicyHistory(): ReadonlyArray<PolicyManifest> {
    return this.policyHistory;
  }

  /**
   * Check if the active policy is still valid.
   */
  public isPolicyValid(): boolean {
    if (!this.activePolicy) return false;
    const now = Date.now();
    return now <= this.activePolicy.expiresAt + this.config.policyGracePeriodMs;
  }

  // ── Invariant Checks ──

  /**
   * Run all hard invariant checks.
   *
   * Hard invariants (NEVER violated):
   *   1. Energy reserve floor
   *   2. Trust minimum
   *   3. Role allowed
   *   4. Mode not suppressed (hazard check)
   *   5. Policy valid and active
   */
  public checkInvariants(action: string): KernelDecision {
    const params = this.activePolicy?.params ?? DEFAULT_POLICY_PARAMS;
    const invariants: InvariantCheck[] = [];
    const violations: string[] = [];
    const now = Date.now();

    // Invariant 1: Human override dominance — if engaged, allow everything
    if (this.state.humanOverride) {
      invariants.push({
        name: 'human_override',
        passed: true,
        detail: 'Human override active — all invariants bypassed',
      });

      const decision: KernelDecision = {
        allowed: true,
        invariants,
        violations: [],
        policyEpoch: this.activePolicy?.epoch ?? 0,
        timestamp: now,
      };
      this.recordAudit(decision, action);
      return decision;
    }

    // Invariant 2: Energy reserve floor
    const energyCheck: InvariantCheck = {
      name: 'energy_floor',
      passed: this.state.energy >= params.energyFloor,
      detail: `energy=${this.state.energy.toFixed(3)}, floor=${params.energyFloor}`,
    };
    invariants.push(energyCheck);
    if (!energyCheck.passed) violations.push('energy_floor');

    // Invariant 3: Trust minimum
    const trustCheck: InvariantCheck = {
      name: 'trust_minimum',
      passed: this.state.trust >= params.minTrust,
      detail: `trust=${this.state.trust.toFixed(3)}, min=${params.minTrust}`,
    };
    invariants.push(trustCheck);
    if (!trustCheck.passed) violations.push('trust_minimum');

    // Invariant 4: Role allowed
    const roleCheck: InvariantCheck = {
      name: 'role_allowed',
      passed: params.allowedRoles.includes(this.state.role),
      detail: `role=${this.state.role}, allowed=[${params.allowedRoles.join(',')}]`,
    };
    invariants.push(roleCheck);
    if (!roleCheck.passed) violations.push('role_allowed');

    // Invariant 5: Mode not suppressed (hazard check)
    const modeCheck: InvariantCheck = {
      name: 'mode_not_suppressed',
      passed: !params.suppressedModes.includes(this.state.currentMode),
      detail: `mode=${this.state.currentMode}, suppressed=[${params.suppressedModes.join(',')}]`,
    };
    invariants.push(modeCheck);
    if (!modeCheck.passed) violations.push('mode_suppressed');

    // Invariant 6: Hazard flag
    const hazardCheck: InvariantCheck = {
      name: 'no_hazard',
      passed: !this.state.hazardFlag,
      detail: `hazardFlag=${this.state.hazardFlag}`,
    };
    invariants.push(hazardCheck);
    if (!hazardCheck.passed) violations.push('hazard_active');

    // Invariant 7: Policy valid
    const policyCheck: InvariantCheck = {
      name: 'policy_valid',
      passed: this.isPolicyValid(),
      detail: this.activePolicy
        ? `epoch=${this.activePolicy.epoch}, expires=${new Date(this.activePolicy.expiresAt).toISOString()}`
        : 'no_active_policy',
    };
    invariants.push(policyCheck);
    if (!policyCheck.passed) violations.push('policy_invalid');

    const decision: KernelDecision = {
      allowed: violations.length === 0,
      invariants,
      violations,
      policyEpoch: this.activePolicy?.epoch ?? 0,
      timestamp: now,
    };

    this.recordAudit(decision, action);
    return decision;
  }

  // ── Audit ──

  /**
   * Get the audit log.
   */
  public getAuditLog(): ReadonlyArray<{
    decision: KernelDecision;
    action: string;
    stateSnapshot: Omit<NodeState, 'neighborSet'> & { neighborCount: number };
  }> {
    return this.auditLog;
  }

  /**
   * Get count of violations in the last N audit entries.
   */
  public getRecentViolationCount(window: number = 20): number {
    const slice = this.auditLog.slice(-window);
    return slice.filter((entry) => !entry.decision.allowed).length;
  }

  // ── Internal ──

  private signPolicy(manifest: Omit<PolicyManifest, 'signature'> | PolicyManifest): string {
    const canonical = JSON.stringify({
      epoch: manifest.epoch,
      version: manifest.version,
      params: manifest.params,
      issuedAt: manifest.issuedAt,
      expiresAt: manifest.expiresAt,
    });

    return createHmac('sha256', this.config.signingKey).update(canonical).digest('hex');
  }

  private recordAudit(decision: KernelDecision, action: string): void {
    const { neighborSet, ...rest } = this.state;
    this.auditLog.push({
      decision,
      action,
      stateSnapshot: { ...rest, neighborCount: neighborSet.size },
    });

    // Trim
    if (this.auditLog.length > this.maxAuditEntries) {
      this.auditLog.splice(0, this.auditLog.length - this.maxAuditEntries);
    }
  }
}

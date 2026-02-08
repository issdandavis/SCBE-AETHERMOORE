/**
 * @file attack-lib.ts
 * @module tests/cross-industry/common
 * @description Attack simulation library for red-team governance testing
 */

import { Context6D, Context9D, SealedEnvelope, AttackType } from './types.js';

/**
 * Generate a valid baseline context
 */
export function createValidContext(): Context9D {
  return {
    identity: [0.1, 0.2, 0.3],
    intentPhase: Math.PI / 4,
    trajectory: [0.1, 0.15, 0.12, 0.14],
    timestamp: Date.now(),
    commitment: 0.8,
    signatureFlag: true,
    timeFlow: 1.0,
    entropyDelta: 0.0,
    quantumState: [1, 0],
  };
}

/**
 * Generate a valid sealed envelope
 */
export function createValidEnvelope(aad?: Record<string, unknown>): SealedEnvelope {
  const hex = (n: number) =>
    Array.from({ length: n }, () =>
      Math.floor(Math.random() * 256)
        .toString(16)
        .padStart(2, '0')
    ).join('');

  return {
    version: 'scbe-v1',
    nonce: hex(12),
    timestamp: Date.now(),
    aad: aad ?? { action: 'transfer', amount: 100 },
    ciphertext: hex(48),
    tag: hex(16),
    hmacChain: hex(32),
    signatures: { primary: hex(64) },
  };
}

/**
 * Apply an attack transformation to context and/or envelope
 */
export function applyAttack(
  attackType: AttackType,
  context: Context9D,
  envelope: SealedEnvelope
): { context: Context9D; envelope: SealedEnvelope } {
  const attackedContext = { ...context };
  const attackedEnvelope = { ...envelope };

  switch (attackType) {
    case 'none':
      // No modification
      break;

    case 'replay':
      // Reuse old timestamp and nonce
      attackedContext.timestamp = Date.now() - 10 * 60 * 1000; // 10 minutes ago
      attackedEnvelope.timestamp = attackedContext.timestamp;
      attackedEnvelope.nonce = 'replayed_nonce_'; // Invalid/short nonce
      break;

    case 'tamper':
      // Modify payload without updating HMAC
      attackedEnvelope.aad = { ...envelope.aad, amount: 999999 };
      // Tag no longer matches ciphertext
      attackedEnvelope.tag = 'invalid_tag_short';
      break;

    case 'entropy':
      // Inject entropy anomaly
      attackedContext.entropyDelta = 0.9; // High entropy deviation
      attackedContext.quantumState = [0.5, 0.5]; // Non-normalized quantum state
      break;

    case 'time':
      // Time manipulation attack
      attackedContext.timeFlow = 0.1; // Abnormal time flow
      attackedContext.timestamp = Date.now() + 60 * 60 * 1000; // Future timestamp
      break;

    case 'topology':
      // Topological manipulation - move point outside trusted realm
      attackedContext.identity = [0.95, 0.95, 0.95]; // Near boundary
      attackedContext.trajectory = [0.9, 0.9, 0.9, 0.9]; // High variance trajectory
      break;

    case 'injection':
      // Injection attack - invalid coordinates
      attackedContext.identity = [2.0, 2.0, 2.0]; // Outside Poincare ball
      break;

    case 'privilege-escalation':
      // Attempt high-privilege action without proper auth
      attackedContext.signatureFlag = false;
      attackedContext.commitment = 0.1; // Low commitment
      break;
  }

  return { context: attackedContext, envelope: attackedEnvelope };
}

/**
 * Create a replay attack scenario
 */
export function createReplayAttack(
  originalContext: Context9D,
  originalEnvelope: SealedEnvelope
): { context: Context9D; envelope: SealedEnvelope } {
  return applyAttack('replay', originalContext, originalEnvelope);
}

/**
 * Create a tampering attack scenario
 */
export function createTamperAttack(
  originalContext: Context9D,
  originalEnvelope: SealedEnvelope,
  tamperedFields: Partial<SealedEnvelope['aad']>
): { context: Context9D; envelope: SealedEnvelope } {
  const { context, envelope } = applyAttack('tamper', originalContext, originalEnvelope);
  envelope.aad = { ...envelope.aad, ...tamperedFields };
  return { context, envelope };
}

/**
 * Create a time-based attack scenario
 */
export function createTimeAttack(
  originalContext: Context9D,
  originalEnvelope: SealedEnvelope,
  timeShiftMs: number
): { context: Context9D; envelope: SealedEnvelope } {
  const context = { ...originalContext };
  const envelope = { ...originalEnvelope };

  context.timestamp = Date.now() + timeShiftMs;
  context.timeFlow = timeShiftMs > 0 ? 2.5 : 0.1;
  envelope.timestamp = context.timestamp;

  return { context, envelope };
}

/**
 * Create an entropy injection attack
 */
export function createEntropyAttack(originalContext: Context9D, entropyLevel: number): Context9D {
  return {
    ...originalContext,
    entropyDelta: entropyLevel,
    quantumState: [Math.cos(entropyLevel * Math.PI), Math.sin(entropyLevel * Math.PI)],
  };
}

/**
 * Create a topology attack - move outside realm boundaries
 */
export function createTopologyAttack(
  originalContext: Context9D,
  targetPosition: number[]
): Context9D {
  return {
    ...originalContext,
    identity: targetPosition,
    trajectory: targetPosition.map((v) => v + 0.1),
  };
}

/**
 * Create a man-in-the-middle attack simulation
 */
export function createMitmAttack(
  originalContext: Context9D,
  originalEnvelope: SealedEnvelope
): { context: Context9D; envelope: SealedEnvelope } {
  const context = { ...originalContext };
  const envelope = { ...originalEnvelope };

  // MITM modifies the trajectory and signature
  context.trajectory = context.trajectory.map((v) => v * 1.5);
  context.signatureFlag = false;

  // Envelope is re-signed but with wrong key
  envelope.signatures = { attacker: 'forged_signature_' };
  envelope.hmacChain = 'modified_hmac_';

  // Time signature mismatch
  context.timeFlow = 1.8;

  return { context, envelope };
}

/**
 * Batch attack generator for comprehensive testing
 */
export function generateAttackBatch(
  baseContext: Context9D,
  baseEnvelope: SealedEnvelope
): Array<{
  name: string;
  attackType: AttackType;
  context: Context9D;
  envelope: SealedEnvelope;
  expectedDecision: 'DENY' | 'QUARANTINE';
}> {
  return [
    {
      name: 'Replay: Old nonce reuse',
      attackType: 'replay',
      ...applyAttack('replay', baseContext, baseEnvelope),
      expectedDecision: 'DENY',
    },
    {
      name: 'Tamper: Amount modification',
      attackType: 'tamper',
      ...applyAttack('tamper', baseContext, baseEnvelope),
      expectedDecision: 'DENY',
    },
    {
      name: 'Time: Future timestamp',
      attackType: 'time',
      ...applyAttack('time', baseContext, baseEnvelope),
      expectedDecision: 'DENY',
    },
    {
      name: 'Entropy: Anomalous randomness',
      attackType: 'entropy',
      ...applyAttack('entropy', baseContext, baseEnvelope),
      expectedDecision: 'QUARANTINE',
    },
    {
      name: 'Topology: Outside realm',
      attackType: 'topology',
      ...applyAttack('topology', baseContext, baseEnvelope),
      expectedDecision: 'QUARANTINE',
    },
    {
      name: 'Injection: Invalid Poincare coords',
      attackType: 'injection',
      ...applyAttack('injection', baseContext, baseEnvelope),
      expectedDecision: 'DENY',
    },
    {
      name: 'Privilege escalation: Missing auth',
      attackType: 'privilege-escalation',
      ...applyAttack('privilege-escalation', baseContext, baseEnvelope),
      expectedDecision: 'QUARANTINE',
    },
  ];
}

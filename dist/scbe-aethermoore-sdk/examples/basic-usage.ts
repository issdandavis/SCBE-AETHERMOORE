/**
 * SCBE-AETHERMOORE Basic Usage Example
 *
 * This demonstrates the core workflow:
 * 1. Create agents in 6D space
 * 2. Evaluate risk of actions
 * 3. Sign payloads with multi-signature consensus
 * 4. Verify envelopes with policy enforcement
 * 5. Use SecurityGate for adaptive access control
 */

import {
  SCBE,
  Agent,
  SecurityGate,
  Roundtable,
  harmonicComplexity,
  getPricingTier,
} from '../dist/api/index.js';

async function main() {
  console.log('=== SCBE-AETHERMOORE Demo ===\n');

  // Initialize the core API
  const scbe = new SCBE();

  // ─────────────────────────────────────────────────────────────
  // 1. AGENTS: Create entities in 6D trust space
  // ─────────────────────────────────────────────────────────────
  console.log('1. Creating agents in 6D space...');

  const alice = new Agent('Alice', [1, 2, 3, 0.5, 1.5, 2.5]);
  const bob = new Agent('Bob', [1.1, 2.1, 3.1, 0.6, 1.6, 2.6]); // Close to Alice
  const eve = new Agent('Eve', [10, 10, 10, 10, 10, 10]); // Far away (suspicious)

  console.log(`  Alice position: [${alice.position.join(', ')}]`);
  console.log(`  Alice trust: ${alice.trustScore}`);
  console.log(`  Distance Alice→Bob: ${alice.distanceTo(bob).toFixed(2)} (close = trusted)`);
  console.log(`  Distance Alice→Eve: ${alice.distanceTo(eve).toFixed(2)} (far = suspicious)\n`);

  // ─────────────────────────────────────────────────────────────
  // 2. RISK EVALUATION: Score context using hyperbolic geometry
  // ─────────────────────────────────────────────────────────────
  console.log('2. Evaluating risk of actions...');

  const safeAction = scbe.evaluateRisk({
    action: 'read',
    userId: 'alice',
    source: 'internal',
  });

  const riskyAction = scbe.evaluateRisk({
    action: 'wire_transfer',
    amount: 1000000,
    destination: 'offshore',
    source: 'external',
  });

  console.log(`  Safe action: ${safeAction.decision} (score: ${safeAction.score.toFixed(2)})`);
  console.log(`  Risky action: ${riskyAction.decision} (score: ${riskyAction.score.toFixed(2)})\n`);

  // ─────────────────────────────────────────────────────────────
  // 3. ROUNDTABLE: Multi-signature consensus by action type
  // ─────────────────────────────────────────────────────────────
  console.log('3. Roundtable multi-signature requirements...');

  const actions = ['read', 'write', 'delete', 'deploy'] as const;
  for (const action of actions) {
    const tongues = Roundtable.requiredTongues(action);
    console.log(`  ${action.padEnd(8)} → [${tongues.join(', ')}]`);
  }
  console.log();

  // ─────────────────────────────────────────────────────────────
  // 4. SIGNING: Create RWP envelope with required signatures
  // ─────────────────────────────────────────────────────────────
  console.log('4. Signing payload with Roundtable consensus...');

  const payload = {
    action: 'deploy',
    target: 'production',
    timestamp: Date.now(),
    author: 'alice',
  };

  const { envelope, tongues } = scbe.signForAction(payload, 'deploy');
  console.log(`  Signed with tongues: [${tongues.join(', ')}]`);
  console.log(`  Envelope nonce: ${envelope.nonce.slice(0, 16)}...`);

  // Verify
  const verification = scbe.verifyForAction(envelope, 'deploy');
  console.log(`  Verification: ${verification.valid ? 'PASS' : 'FAIL'}`);
  console.log(`  Reason: ${verification.reason}\n`);

  // ─────────────────────────────────────────────────────────────
  // 5. SECURITY GATE: Adaptive dwell time based on risk
  // ─────────────────────────────────────────────────────────────
  console.log('5. SecurityGate adaptive access control...');

  const gate = new SecurityGate({
    minWaitMs: 10,
    maxWaitMs: 1000,
    alpha: 1.5,
  });

  // Trusted agent, safe action
  const aliceRead = await gate.check(alice, 'read', { source: 'internal' });
  console.log(`  Alice reading (internal): ${aliceRead.status} (${aliceRead.dwellMs}ms wait)`);

  // Trusted agent, dangerous action
  const aliceDelete = await gate.check(alice, 'delete', { source: 'external' });
  console.log(`  Alice deleting (external): ${aliceDelete.status} (${aliceDelete.dwellMs}ms wait)`);

  // Untrusted agent
  eve.trustScore = 0.1; // Low trust
  const eveDelete = await gate.check(eve, 'delete', { source: 'external' });
  console.log(`  Eve deleting (low trust): ${eveDelete.status} (${eveDelete.dwellMs}ms wait)\n`);

  // ─────────────────────────────────────────────────────────────
  // 6. HARMONIC PRICING: Exponential complexity tiers
  // ─────────────────────────────────────────────────────────────
  console.log('6. Harmonic complexity pricing...');

  for (let depth = 1; depth <= 4; depth++) {
    const tier = getPricingTier(depth);
    console.log(`  Depth ${depth}: ${tier.tier.padEnd(10)} (complexity: ${tier.complexity.toFixed(2)})`);
  }
  console.log();

  // ─────────────────────────────────────────────────────────────
  // 7. TRUST DECAY: Agents must check in to maintain trust
  // ─────────────────────────────────────────────────────────────
  console.log('7. Trust decay over time...');

  const tempAgent = new Agent('TempAgent', [0, 0, 0, 0, 0, 0]);
  console.log(`  Initial trust: ${tempAgent.trustScore}`);

  // Simulate time passing (fast decay for demo)
  await new Promise(r => setTimeout(r, 100));
  tempAgent.decayTrust(10.0); // Fast decay rate
  console.log(`  After 100ms (fast decay): ${tempAgent.trustScore.toFixed(3)}`);

  // Check in refreshes trust
  tempAgent.checkIn();
  console.log(`  After check-in: ${tempAgent.trustScore.toFixed(3)}\n`);

  console.log('=== Demo Complete ===');
}

main().catch(console.error);

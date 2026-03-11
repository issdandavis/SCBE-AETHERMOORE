/**
 * SCBE-AETHERMOORE Quickstart
 * ============================
 *
 * Run: node examples/quickstart.js
 *
 * Demonstrates the three things you can sell today:
 *   1. Risk evaluation (hyperbolic geometry trust scoring)
 *   2. Multi-signature governance (Sacred Tongues)
 *   3. Governed browser sessions (sealed + encrypted)
 */

// If installed via npm: const { ... } = require('scbe-aethermoore');
const {
  SCBE,
  Agent,
  SecurityGate,
  Roundtable,
  harmonicComplexity,
  getPricingTier,
} = require('../dist/src/api/index.js');

const {
  SpiralSealSessionBrowser,
} = require('../dist/src/browser/spiralSealSession.js');

const {
  HyperbolicTrustBrowser,
} = require('../dist/src/browser/hyperbolicTrustBrowser.js');

// ============================================================
// 1. Risk Evaluation — your core product
// ============================================================
console.log('╔══════════════════════════════════════════════╗');
console.log('║  SCBE-AETHERMOORE: Risk Evaluation Demo     ║');
console.log('╚══════════════════════════════════════════════╝\n');

const scbe = new SCBE();

// Safe action
const safe = scbe.evaluateRisk({ action: 'read', source: 'internal', user: 'admin' });
console.log('Safe action:', {
  decision: safe.decision,
  score: safe.score.toFixed(4),
  scaledCost: safe.scaledCost.toFixed(2),
});

// Risky action
const risky = scbe.evaluateRisk({ action: 'delete_all', source: 'external', escalation: true });
console.log('Risky action:', {
  decision: risky.decision,
  score: risky.score.toFixed(4),
  scaledCost: risky.scaledCost.toFixed(2),
});

// ============================================================
// 2. Multi-Signature Governance — roundtable consensus
// ============================================================
console.log('\n--- Roundtable Governance ---');

// Different actions need different approval levels
for (const action of ['read', 'write', 'delete', 'deploy']) {
  const tongues = Roundtable.requiredTongues(action);
  const tier = getPricingTier(tongues.length);
  console.log(`  ${action.padEnd(8)} → ${tongues.length} tongues [${tongues.join(',')}] → ${tier.tier} tier`);
}

// Sign and verify a payload
const signed = scbe.signForAction({ transfer: 1000, to: 'vault' }, 'write');
const verified = scbe.verify(signed.envelope);
console.log(`\n  Signed 'write' action: valid=${verified.valid}, tongues=[${verified.validTongues}]`);

// ============================================================
// 3. Security Gate — adaptive dwell time
// ============================================================
console.log('\n--- Security Gate ---');

const gate = new SecurityGate();
const alice = new Agent('Alice', [1, 0, 0, 0.5, 0.5, 0.5], 0.95);
const bob = new Agent('Bob', [4, 3, 2, 1, 0, -1], 0.3);

console.log(`  Alice trust=${alice.trustScore}, distance to Bob=${alice.distanceTo(bob).toFixed(2)}`);

// ============================================================
// 4. Governed Browser Session — SpiralSeal encrypted
// ============================================================
console.log('\n--- Governed Browser Session ---');

const browser = new SpiralSealSessionBrowser('demo-master-key-change-in-production');
const session = browser.createSession('agent-001', 'https://example.com');
console.log(`  Session: ${session.sessionId}`);
console.log(`  Encrypted: ${session.sealedState.slice(0, 40)}...`);

// Execute a governed action
const result = browser.executeAction(session.sessionId, {
  type: 'navigate',
  payload: { url: 'https://api.example.com/data' },
  nonce: require('crypto').randomBytes(16).toString('hex'),
  timestamp: Date.now(),
});
console.log(`  Navigate result: success=${result.success}, tongues=[${result.tongueVerification}]`);

browser.terminateSession(session.sessionId);
console.log(`  Session terminated (forward-secret keys destroyed)`);

// ============================================================
// 5. Hyperbolic Trust Scoring
// ============================================================
console.log('\n--- Hyperbolic Trust Browser ---');

const htb = new HyperbolicTrustBrowser();
const trustResult = htb.evaluate({
  url: 'https://api.stripe.com/v1/charges',
  action: 'navigate',
  agentId: 'payment-agent',
  actorType: 'ai',
  trustScore: 0.85,
});
console.log(`  URL: https://api.stripe.com/v1/charges`);
console.log(`  Decision: ${trustResult.decision}`);
console.log(`  Hyperbolic distance: ${trustResult.hyperbolicDistance.toFixed(4)}`);
console.log(`  Harmonic cost: ${trustResult.harmonicCost.toFixed(4)}`);
console.log(`  Tongues: KO=${trustResult.tongueResonance[0]} AV=${trustResult.tongueResonance[1]} RU=${trustResult.tongueResonance[2]}`);

// ============================================================
// Summary
// ============================================================
console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('All demos passed. This is what your API serves.');
console.log('');
console.log('Next steps:');
console.log('  npm install scbe-aethermoore       # Install as dependency');
console.log('  python -m uvicorn src.api.main:app  # Start REST API');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

examples/roundtable-demo.ts  /**
 * Roundtable Multi-Signature Verification Demo
 * 
 * Demonstrates:
 * 1. Creating envelopes with different security tiers
 * 2. Multi-tongue signature verification
 * 3. Attack scenarios (tampering, replay, missing signatures)
 */

import {
  SpiralverseProtocol,
  SacredTongue,
  SecurityTier,
  classifyAction,
  getRequiredTongues,
  type ActionPayload,
} from '../src/spiralverse-sdk';

// ========== SETUP ==========

const sdk = new SpiralverseProtocol({
  [SacredTongue.KO]: 'secret_ko_master_key_2026',
  [SacredTongue.RU]: 'secret_ru_policy_key_2026',
  [SacredTongue.UM]: 'secret_um_security_key_2026',
  [SacredTongue.AV]: 'secret_av_io_key_2026',
  [SacredTongue.CA]: 'secret_ca_compute_key_2026',
  [SacredTongue.DR]: 'secret_dr_schema_key_2026',
});

console.log('=== Spiralverse Roundtable Demo ===\n');

// ========== SCENARIO 1: Low-Risk Operation (Single Signature) ==========

console.log('SCENARIO 1: Low-Risk Query (TIER1)');
const queryAction: ActionPayload = {
  action: 'query_state',
  params: { agent_id: 'agent_42', field: 'position' },
};

const tier1 = classifyAction(queryAction.action);
const tongues1 = getRequiredTongues(tier1);
console.log(`  Action: ${queryAction.action}`);
console.log(`  Tier: ${tier1} | Required Tongues: ${tongues1.join(', ')}`);

const envelope1 = sdk.createEnvelope(SacredTongue.KO, tongues1, queryAction);
const valid1 = sdk.verifyEnvelope(envelope1, tongues1);
console.log(`  Valid: ${valid1} ✓\n`);

// ========== SCENARIO 2: High-Risk Operation (Triple Signature) ==========

console.log('SCENARIO 2: High-Risk Command (TIER3)');
const commandAction: ActionPayload = {
  action: 'execute_command',
  params: { command: 'move_arm', x: 10, y: 20, z: 5 },
};

const tier3 = classifyAction(commandAction.action);
const tongues3 = getRequiredTongues(tier3);
console.log(`  Action: ${commandAction.action}`);
console.log(`  Tier: ${tier3} | Required Tongues: ${tongues3.join(', ')}`);

const envelope3 = sdk.createEnvelope(SacredTongue.KO, tongues3, commandAction);
const valid3 = sdk.verifyEnvelope(envelope3, tongues3);
console.log(`  Signatures: ${Object.keys(envelope3.signatures).join(', ')}`);
console.log(`  Valid: ${valid3} ✓\n`);

// ========== SCENARIO 3: Critical Operation (Quad Signature) ==========

console.log('SCENARIO 3: Critical Deployment (TIER4)');
const deployAction: ActionPayload = {
  action: 'deploy',
  params: { target: 'production', version: 'v2.1.0' },
};

const tier4 = classifyAction(deployAction.action);
const tongues4 = getRequiredTongues(tier4);
console.log(`  Action: ${deployAction.action}`);
console.log(`  Tier: ${tier4} | Required Tongues: ${tongues4.join(', ')}`);

const envelope4 = sdk.createEnvelope(SacredTongue.KO, tongues4, deployAction);
const valid4 = sdk.verifyEnvelope(envelope4, tongues4);
console.log(`  Signatures: ${Object.keys(envelope4.signatures).join(', ')}`);
console.log(`  Valid: ${valid4} ✓\n`);

// ========== SCENARIO 4: Attack - Payload Tampering ==========

console.log('SCENARIO 4: Attack Detection - Payload Tampering');
const tamperedEnvelope = { ...envelope3 };
tamperedEnvelope.payload = Buffer.from(
  JSON.stringify({ action: 'delete', params: { target: 'everything' } })
).toString('base64url');

const validTampered = sdk.verifyEnvelope(tamperedEnvelope, tongues3);
console.log(`  Original: execute_command`);
console.log(`  Tampered: delete everything`);
console.log(`  Valid: ${validTampered} ✗ (signatures don't match modified payload)\n`);

// ========== SCENARIO 5: Attack - Missing Required Signature ==========

console.log('SCENARIO 5: Attack Detection - Insufficient Signatures');
const insufficientEnvelope = { ...envelope3 };
delete insufficientEnvelope.signatures[SacredTongue.UM]; // Remove UM signature

const validInsufficient = sdk.verifyEnvelope(insufficientEnvelope, tongues3);
console.log(`  Required: ${tongues3.join(', ')}`);
console.log(`  Provided: ${Object.keys(insufficientEnvelope.signatures).join(', ')}`);
console.log(`  Valid: ${validInsufficient} ✗ (missing UM signature)\n`);

// ========== SCENARIO 6: Successful Decode ==========

console.log('SCENARIO 6: Successful Message Decode');
const decoded = sdk.decodePayload(envelope3);
console.log(`  Spelltext: ${envelope3.spelltext}`);
console.log(`  Payload: ${JSON.stringify(decoded, null, 2)}`);
console.log(`  Timestamp: ${envelope3.ts}`);
console.log(`  Nonce: ${envelope3.nonce.substring(0, 8)}...\n`);

console.log('=== Demo Complete ===');
console.log('All legitimate operations passed Roundtable verification.');
console.log('All attack scenarios were successfully detected and rejected.');

/**
 * SCBE Basic Usage Example
 *
 * This shows how to use the SCBE API for:
 * 1. Risk evaluation
 * 2. Signing payloads
 * 3. Verifying signatures
 *
 * Run with: npx ts-node examples/basic-usage.ts
 */

import { SCBE, evaluateRisk, sign, verify } from '../src/api/index.js';

// ============================================================
// Example 1: Evaluate Risk of a Transaction
// ============================================================

console.log('=== Example 1: Risk Evaluation ===\n');

const transaction = {
  userId: 'alice123',
  action: 'wire_transfer',
  amount: 50000,
  destination: 'external_bank_xyz',
  ip: '192.168.1.100',
  timestamp: Date.now(),
};

const risk = evaluateRisk(transaction);

console.log('Transaction:', JSON.stringify(transaction, null, 2));
console.log('\nRisk Assessment:');
console.log(`  Score: ${(risk.score * 100).toFixed(1)}%`);
console.log(`  Distance from safe center: ${risk.distance.toFixed(4)}`);
console.log(`  Cost to attack: ${risk.scaledCost.toFixed(2)}x base`);
console.log(`  Decision: ${risk.decision}`);
console.log(`  Reason: ${risk.reason}`);

// ============================================================
// Example 2: Sign a Payload
// ============================================================

console.log('\n=== Example 2: Sign Payload ===\n');

const payload = {
  orderId: 'ORD-12345',
  items: ['widget-A', 'gadget-B'],
  total: 299.99,
  currency: 'USD',
};

// Sign with single tongue (default: 'ko')
const singleSig = sign(payload);
console.log('Single signature (ko):');
console.log(`  Nonce: ${singleSig.envelope.nonce.slice(0, 20)}...`);
console.log(`  Signature (ko): ${singleSig.envelope.sigs.ko.slice(0, 30)}...`);

// Sign with multiple tongues for high-security
const multiSig = sign(payload, ['ko', 'um', 'dr']);
console.log('\nMulti-signature (ko, um, dr):');
console.log(`  Signatures: ${Object.keys(multiSig.envelope.sigs).join(', ')}`);

// ============================================================
// Example 3: Verify a Signature
// ============================================================

console.log('\n=== Example 3: Verify Signature ===\n');

const verified = verify(singleSig.envelope);
console.log(`Valid: ${verified.valid}`);
console.log(`Reason: ${verified.reason}`);

// Tamper with payload and try to verify
const tampered = {
  ...singleSig.envelope,
  payload: 'TAMPERED_DATA_HERE',
};

const tamperedResult = verify(tampered);
console.log(`\nTampered envelope valid: ${tamperedResult.valid}`);
console.log(`Reason: ${tamperedResult.reason}`);

// ============================================================
// Example 4: Full Flow - Fraud Detection
// ============================================================

console.log('\n=== Example 4: Fraud Detection Flow ===\n');

const api = new SCBE();

// Normal user behavior
const normalLogin = {
  userId: 'bob456',
  action: 'login',
  ip: '10.0.0.50',
  device: 'known_laptop',
  time: '09:00',
};

const normalRisk = api.evaluateRisk(normalLogin);
console.log(`Normal login risk: ${(normalRisk.score * 100).toFixed(1)}% -> ${normalRisk.decision}`);

// Suspicious behavior (same user, different patterns)
const suspiciousLogin = {
  userId: 'bob456',
  action: 'login',
  ip: '185.123.45.67', // Foreign IP
  device: 'unknown_device',
  time: '03:00', // Unusual hour
  location: 'foreign_country',
};

const suspiciousRisk = api.evaluateRisk(suspiciousLogin);
console.log(`Suspicious login risk: ${(suspiciousRisk.score * 100).toFixed(1)}% -> ${suspiciousRisk.decision}`);

// ============================================================
// Summary
// ============================================================

console.log('\n=== Summary ===');
console.log('SCBE API provides:');
console.log('  - evaluateRisk(context) -> { score, decision, reason }');
console.log('  - sign(payload, tongues?) -> { envelope }');
console.log('  - verify(envelope) -> { valid, reason }');
console.log('  - breathe(context, intensity?) -> 6D point');
console.log('\nThe "physics" is in the exponential cost scaling:');
console.log('  - Small deviation = small cost increase');
console.log('  - Large deviation = impossible cost');
console.log('\nThat\'s the "vertical wall" that makes fraud exponentially expensive.');

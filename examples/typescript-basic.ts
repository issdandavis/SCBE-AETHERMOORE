/**
 * SCBE-AETHERMOORE Basic TypeScript Examples
 *
 * Run with: npx ts-node examples/typescript-basic.ts
 */

import { DEFAULT_CONFIG, VERSION } from '../src/index.js';

console.log('='.repeat(60));
console.log(`SCBE-AETHERMOORE ${VERSION} - Basic Examples`);
console.log('='.repeat(60));
console.log();

// Example 1: Configuration
console.log('1. Default Configuration:');
console.log(JSON.stringify(DEFAULT_CONFIG, null, 2));
console.log();

// Example 2: Hyperbolic Distance (if implemented)
console.log('2. Hyperbolic Geometry:');
try {
  // This would work if harmonic module exports are complete
  // const { poincareDistance } = await import('../src/harmonic/hyperbolic.js');
  // const p1 = { x: 0.5, y: 0.3, z: 0.1 };
  // const p2 = { x: 0.2, y: 0.4, z: 0.2 };
  // const distance = poincareDistance(p1, p2);
  // console.log(`Distance: ${distance}`);
  console.log('  (Import harmonic module for full functionality)');
} catch (error) {
  console.log('  Harmonic module not yet fully exported');
}
console.log();

// Example 3: Nonce Management
console.log('3. Nonce Management:');
try {
  const { NonceManager } = await import('../src/crypto/nonceManager.js');
  const manager = new NonceManager();
  const nonce = manager.generate();
  console.log(`  Generated nonce: ${nonce}`);
  console.log(`  First validation: ${manager.validate(nonce)}`);
  console.log(`  Replay attempt: ${manager.validate(nonce)}`);
} catch (error) {
  console.log(`  Error: ${error}`);
}
console.log();

// Example 4: Circuit Breaker
console.log('4. Circuit Breaker Pattern:');
try {
  const { CircuitBreaker } = await import('../src/rollout/circuitBreaker.js');
  const breaker = new CircuitBreaker({
    failureThreshold: 3,
    resetTimeout: 5000,
  });

  console.log('  Circuit breaker initialized');
  console.log(`  State: ${breaker.getState()}`);
} catch (error) {
  console.log(`  Error: ${error}`);
}
console.log();

console.log('='.repeat(60));
console.log('Examples complete! Check QUICKSTART.md for more.');
console.log('='.repeat(60));

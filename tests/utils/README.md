# Test Utilities

Shared utilities, helpers, and mock generators for enterprise testing.

## Components

- `test_helpers.ts` - Common test assertion helpers
- `mock_generators.ts` - Test data and mock generators
- `quantum_simulator.ts` - Quantum algorithm simulators (Shor's, Grover's)
- `performance_monitor.ts` - Performance monitoring utilities

## Utilities

### Test Helpers

- Assertion helpers for common patterns
- Test fixture management
- Error handling utilities
- Logging and debugging tools

### Mock Generators

- Random data generation for property-based tests
- Cryptographic key generation
- AI intent generation
- Code artifact generation

### Quantum Simulator

- Classical simulation of quantum algorithms
- Shor's algorithm (RSA factoring)
- Grover's algorithm (key search)
- Quantum circuit simulation
- Security bit measurement

### Performance Monitor

- Throughput measurement
- Latency tracking (P50, P95, P99)
- Memory profiling
- Resource utilization monitoring

## Usage

```typescript
import { generateRandomKey, simulateShorAttack } from './utils';

// Generate test data
const key = generateRandomKey(2048);

// Simulate quantum attack
const result = simulateShorAttack(key, 20);
expect(result.success).toBe(false);
```

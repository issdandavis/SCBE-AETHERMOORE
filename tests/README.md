# SCBE-AETHERMOORE Test Suite

## Test Tier System (L1 - L6)

This repository uses a **6-tier test classification system** ranging from basic sanity checks to NSA-grade adversarial testing.

```
tests/
├── L1-basic/        # Tier 1: Basic sanity tests (High School level)
├── L2-unit/         # Tier 2: Standard unit tests (Junior Dev level)
├── L3-integration/  # Tier 3: Integration tests (Senior Dev level)
├── L4-property/     # Tier 4: Property-based tests (Staff Engineer level)
├── L5-security/     # Tier 5: Security & compliance (Security Engineer level)
├── L6-adversarial/  # Tier 6: Adversarial/Failable-by-design (NSA level)
└── README.md
```

---

## Tier Descriptions

### L1-BASIC (High School Project Level)
**Purpose**: Smoke tests and basic functionality verification
**Complexity**: Simple assertions, happy path only
**Who writes these**: Anyone, including newcomers

```typescript
// Example L1 test
it('should create an envelope', () => {
  const envelope = createEnvelope(data);
  expect(envelope).toBeDefined();
});
```

**What belongs here**:
- "Does it run?" tests
- Basic input/output verification
- Simple happy path scenarios
- Null/undefined checks

---

### L2-UNIT (Junior Developer Level)
**Purpose**: Test individual functions and modules in isolation
**Complexity**: Mock dependencies, test edge cases
**Who writes these**: All developers

```typescript
// Example L2 test
describe('computeSpectralCoherence', () => {
  it('should return S_spec in [0, 1] for any valid signal', () => {
    const signal = generateTestSignal(1000, 1, [{ freq: 100, amplitude: 1 }]);
    const result = computeSpectralCoherence(signal, 1000, 50);
    expect(result.S_spec).toBeGreaterThanOrEqual(0);
    expect(result.S_spec).toBeLessThanOrEqual(1);
  });
});
```

**What belongs here**:
- Single function tests
- Boundary value testing
- Error handling verification
- Input validation tests

---

### L3-INTEGRATION (Senior Developer Level)
**Purpose**: Test component interactions and system flows
**Complexity**: Multiple components working together
**Who writes these**: Senior developers, architects

```typescript
// Example L3 test
describe('14-Layer Pipeline Integration', () => {
  it('should process signal through all 14 layers', async () => {
    const input = generateComplexInput();
    const result = await pipeline.process(input);
    expect(result.decision).toMatch(/ALLOW|QUARANTINE|DENY/);
    expect(result.layers).toHaveLength(14);
  });
});
```

**What belongs here**:
- End-to-end workflow tests
- Multi-module interaction tests
- Database + API integration
- Performance under normal load

---

### L4-PROPERTY (Staff Engineer Level)
**Purpose**: Property-based testing with random inputs
**Complexity**: Mathematical invariants, fuzzing
**Who writes these**: Staff engineers, mathematicians

```typescript
// Example L4 test
import * as fc from 'fast-check';

it('S_spec is phase-invariant (property-based)', () => {
  fc.assert(
    fc.property(
      fc.double({ min: 1, max: 100, noNaN: true }),
      fc.double({ min: 0, max: 2 * Math.PI, noNaN: true }),
      (freq, phase) => {
        const signal1 = generateSignal(freq, 0);
        const signal2 = generateSignal(freq, phase);
        return Math.abs(coherence(signal1) - coherence(signal2)) < 0.01;
      }
    )
  );
});
```

**What belongs here**:
- fast-check property tests
- Mathematical invariant verification
- Fuzzing with random inputs
- Metamorphic testing
- Parseval's theorem verification

---

### L5-SECURITY (Security Engineer Level)
**Purpose**: Security boundaries, compliance, cryptographic correctness
**Complexity**: Attack simulation, compliance verification
**Who writes these**: Security engineers, compliance officers

```typescript
// Example L5 test
describe('Cryptographic Boundary Enforcement', () => {
  it('F01: Wrong key must fail decryption', () => {
    const ciphertext = encrypt(plaintext, correctKey);
    expect(() => decrypt(ciphertext, wrongKey)).toThrow('AUTH_FAILED');
  });

  it('F03: Tampered ciphertext must fail', () => {
    const ciphertext = encrypt(plaintext, key);
    ciphertext[10] ^= 0xFF; // Flip bits
    expect(() => decrypt(ciphertext, key)).toThrow('TAMPER_DETECTED');
  });
});
```

**What belongs here**:
- OWASP Top 10 verification
- Cryptographic boundary tests
- Access control tests
- Compliance verification (FIPS, NIST)
- Injection attack prevention
- Nonce reuse detection

---

### L6-ADVERSARIAL (NSA Level)
**Purpose**: Failable-by-design tests, adversarial scenarios, formal verification
**Complexity**: Sophisticated attack vectors, cryptanalysis
**Who writes these**: Cryptographers, security researchers

```typescript
// Example L6 test
describe('Failable-by-Design: Adversarial Crypto', () => {
  it('F-ADV-01: Timing attack resistance on comparison', () => {
    const times: number[] = [];
    for (let i = 0; i < 1000; i++) {
      const start = process.hrtime.bigint();
      constantTimeCompare(secret, guess);
      times.push(Number(process.hrtime.bigint() - start));
    }
    const variance = calculateVariance(times);
    expect(variance).toBeLessThan(TIMING_THRESHOLD);
  });

  it('F-ADV-02: Side-channel resistant key derivation', () => {
    // Verify no cache-timing leaks in HKDF
    const traces = collectPowerTraces(() => deriveKey(password, salt));
    expect(correlationAnalysis(traces)).toBeLessThan(0.1);
  });

  it('F-ADV-03: Post-quantum security reduction to LWE', () => {
    // Verify ML-KEM security reduces to Learning With Errors
    const { publicKey, secretKey } = mlKemKeyGen();
    const advantage = distinguishingAdvantage(publicKey, randomMatrix);
    expect(advantage).toBeLessThan(2 ** -128); // 128-bit security
  });
});
```

**What belongs here**:
- Timing attack resistance
- Side-channel analysis
- Cryptanalysis tests
- Formal verification stubs
- Post-quantum security reductions
- Byzantine fault tolerance
- Malicious input fuzzing
- Zero-knowledge proof verification

---

## Test Naming Convention

```
tests/L{1-6}-{category}/{module}.{type}.test.ts
```

Examples:
- `tests/L1-basic/envelope.smoke.test.ts`
- `tests/L2-unit/spectral-coherence.unit.test.ts`
- `tests/L3-integration/14-layer-pipeline.integration.test.ts`
- `tests/L4-property/hyperbolic-geometry.property.test.ts`
- `tests/L5-security/crypto-boundaries.security.test.ts`
- `tests/L6-adversarial/timing-attacks.adversarial.test.ts`

---

## Running Tests by Tier

```bash
# Run all tests
npm test

# Run specific tier
npm test -- --testPathPattern="L1-basic"
npm test -- --testPathPattern="L2-unit"
npm test -- --testPathPattern="L3-integration"
npm test -- --testPathPattern="L4-property"
npm test -- --testPathPattern="L5-security"
npm test -- --testPathPattern="L6-adversarial"

# Run tiers 1-3 (fast, for CI)
npm test -- --testPathPattern="L[1-3]"

# Run tiers 4-6 (thorough, for release)
npm test -- --testPathPattern="L[4-6]"
```

---

## CI/CD Pipeline Integration

| Stage | Tiers | Trigger | Timeout |
|-------|-------|---------|---------|
| Pre-commit | L1 | Every commit | 30s |
| PR Check | L1-L3 | Pull request | 5m |
| Nightly | L1-L5 | Scheduled | 30m |
| Release | L1-L6 | Tag/Release | 2h |

---

## Test Coverage by Tier

| Tier | Tests | Pass Rate | Coverage |
|------|-------|-----------|----------|
| L1-basic | ~50 | 100% | Smoke |
| L2-unit | ~200 | 99%+ | Functions |
| L3-integration | ~100 | 98%+ | Workflows |
| L4-property | ~50 | 99%+ | Invariants |
| L5-security | ~100 | 100% | Boundaries |
| L6-adversarial | ~30 | 100% | Attacks |

---

## Adding New Tests

1. **Determine the tier** based on complexity and purpose
2. **Create file** in appropriate `L{n}-{category}/` directory
3. **Follow naming convention**: `{module}.{type}.test.ts`
4. **Add appropriate markers**:

```typescript
/**
 * @tier L4
 * @category property
 * @axiom 9 (Spectral Coherence)
 * @requires fast-check
 */
describe('Spectral Coherence Property Tests', () => {
  // ...
});
```

---

## Axiom Coverage Matrix

| Axiom | L1 | L2 | L3 | L4 | L5 | L6 |
|-------|:--:|:--:|:--:|:--:|:--:|:--:|
| 1. Positivity of Cost | - | ✓ | ✓ | ✓ | - | - |
| 2. Monotonicity | - | ✓ | ✓ | ✓ | - | - |
| 3. Convexity | - | - | ✓ | ✓ | - | - |
| 4. Temporal Breathing | - | ✓ | ✓ | ✓ | - | - |
| 5. C-infinity Smoothness | - | - | - | ✓ | - | - |
| 6. Lyapunov Stability | - | - | ✓ | ✓ | - | - |
| 7. Harmonic Resonance | - | ✓ | ✓ | - | - | - |
| 8. Quantum Resistance | - | - | - | - | ✓ | ✓ |
| 9. Hyperbolic Geometry | - | ✓ | ✓ | ✓ | - | - |
| 10. Golden Ratio | - | ✓ | - | ✓ | - | - |
| 11. Fractional Flux | - | - | - | ✓ | - | - |
| 12. Topological Attack | - | - | - | - | ✓ | ✓ |
| 13. Atomic Rekeying | - | - | ✓ | - | ✓ | ✓ |

---

## Quality Gates

### L1-L3 (Must pass for merge)
- All tests green
- No regressions
- Coverage maintained

### L4 (Must pass for release)
- All property tests pass with 1000 iterations
- No invariant violations

### L5-L6 (Must pass for production)
- All security boundaries enforced
- Zero cryptographic failures
- Adversarial tests validated

---

## References

- [SCBE 14-Layer Architecture](../docs/ARCHITECTURE.md)
- [13 Axioms Documentation](../docs/AXIOMS.md)
- [Patent Claims](../docs/ENABLEMENT.md)
- [NIST PQC Standards](https://csrc.nist.gov/projects/post-quantum-cryptography)

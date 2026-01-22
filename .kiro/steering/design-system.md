# Design System Rules for Figma Integration

## Project Overview

This is the SCBE (Spectral Context-Bound Encryption) project - a security framework with both TypeScript and Python components. The project includes a demo UI built with Tailwind CSS.

## Frameworks & Libraries

- **Languages**: TypeScript, Python, JavaScript
- **UI Framework**: Vanilla HTML/JS with Tailwind CSS (CDN)
- **Build System**: TypeScript compiler (tsc), Vitest for testing
- **Testing**: Vitest (TypeScript), pytest (Python), fast-check (property-based), hypothesis (Python property-based)
- **Node Version**: 18.0.0+

## Testing Framework

### Property-Based Testing

- **TypeScript**: Use `fast-check` library with minimum 100 iterations per property
- **Python**: Use `hypothesis` library with minimum 100 iterations per property
- **Coverage Target**: 95% (lines, functions, branches, statements)

### Test Structure

```
tests/
├── enterprise/          # Enterprise-grade test suite
│   ├── quantum/        # Quantum attack simulations
│   ├── ai_brain/       # AI safety and governance
│   ├── agentic/        # Agentic coding system
│   ├── compliance/     # SOC 2, ISO 27001, FIPS 140-3
│   ├── stress/         # Load and stress testing
│   ├── security/       # Fuzzing, side-channel analysis
│   ├── formal/         # Formal verification
│   └── integration/    # End-to-end tests
├── orchestration/      # Test orchestration engine
├── reporting/          # Compliance dashboards
└── utils/              # Test utilities and helpers
```

### Test Requirements

- All tests must include requirement traceability comments
- Property tests must run minimum 100 iterations
- Use dual testing approach: unit tests + property-based tests
- Tag tests with markers: `@pytest.mark.quantum`, `@pytest.mark.property`, etc.

## Styling Approach

### Tailwind CSS

The project uses Tailwind CSS via CDN for the demo UI (`src/lambda/demo.html`).

**Custom Styles Pattern:**

```css
/* Custom animations */
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Utility classes */
.animate-pulse-slow {
  animation: pulse 2s ease-in-out infinite;
}
.animate-spin-slow {
  animation: spin 3s linear infinite;
}
.glass {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}
.gradient-bg {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.glow {
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.5);
}
.glow-green {
  box-shadow: 0 0 20px rgba(34, 197, 94, 0.5);
}
.glow-red {
  box-shadow: 0 0 20px rgba(239, 68, 68, 0.5);
}
```

### Color Palette

- **Primary Background**: Dark gradient (`#1a1a2e` → `#16213e` → `#0f3460`)
- **Text**: White (`text-white`), Gray variants (`text-gray-300`, `text-gray-400`)
- **Accent Colors**:
  - Blue: `bg-blue-600`, `text-blue-400` (primary actions)
  - Green: `bg-green-500`, `text-green-400` (success/safe states)
  - Red: `bg-red-500`, `text-red-400` (danger/critical states)
  - Yellow: `bg-yellow-500`, `text-yellow-400` (warnings)
  - Purple: `bg-purple-500`, `text-purple-400` (special features)

### Component Patterns

**Glass Card:**

```html
<section class="glass rounded-2xl p-8 mb-8 border border-white/10">
  <!-- content -->
</section>
```

**Status Badge:**

```html
<div class="inline-block px-4 py-1 bg-blue-600 rounded-full text-sm">Badge Text</div>
```

**Button:**

```html
<button class="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition">Button Text</button>
```

**Metric Card:**

```html
<div class="text-center p-4 bg-green-500/20 rounded-xl">
  <div class="text-3xl font-bold text-green-400">Value</div>
  <div class="text-sm text-gray-400">Label</div>
</div>
```

## Project Structure

```
src/
├── crypto/          # TypeScript cryptographic modules
├── lambda/          # AWS Lambda demo (HTML/JS)
├── metrics/         # Telemetry TypeScript modules
├── rollout/         # Deployment utilities
├── selfHealing/     # Self-healing orchestration
├── symphonic_cipher/ # Python cipher implementation
├── symphonic/       # TypeScript Symphonic Cipher (Complex, FFT, Feistel, ZBase32)
├── harmonic/        # PHDM (Polyhedral Hamiltonian Defense Manifold)
└── physics_sim/     # Python physics simulation

tests/
├── enterprise/      # Enterprise-grade testing suite (41 properties)
├── orchestration/   # Test scheduling and execution
├── reporting/       # Compliance dashboards and reports
├── utils/           # Test helpers and utilities
├── harmonic/        # PHDM tests
└── symphonic/       # Symphonic Cipher tests
```

## Enterprise Testing Suite

### Test Categories (41 Correctness Properties)

1. **Quantum (Properties 1-6)** - Shor's/Grover's resistance, ML-KEM, ML-DSA, lattice hardness
2. **AI Safety (Properties 7-12)** - Intent verification, governance, consensus, fail-safe
3. **Agentic (Properties 13-18)** - Code generation, vulnerability scanning, rollback
4. **Compliance (Properties 19-24)** - SOC 2, ISO 27001, FIPS 140-3, Common Criteria
5. **Stress (Properties 25-30)** - 1M req/s throughput, 10K concurrent attacks, latency
6. **Security (Properties 31-35)** - Fuzzing, side-channel, fault injection, oracle attacks
7. **Formal (Properties 36-39)** - Model checking, theorem proving, symbolic execution
8. **Integration (Properties 40-41)** - End-to-end security, requirements coverage

### Running Tests

```bash
# TypeScript tests
npm test                              # All tests
npm test -- tests/enterprise/quantum/ # Specific category
npm test -- --coverage                # With coverage

# Python tests
pytest tests/enterprise/ -v           # All tests
pytest -m quantum tests/enterprise/   # Specific marker
pytest tests/enterprise/ --cov=src    # With coverage
```

## Figma Integration Guidelines

When converting Figma designs to code:

1. **Use Tailwind utilities** - Match the existing Tailwind patterns
2. **Maintain dark theme** - Use the gradient background and glass effects
3. **Follow color semantics** - Green=safe, Red=danger, Yellow=warning, Blue=info
4. **Use rounded corners** - `rounded-lg`, `rounded-xl`, `rounded-2xl`
5. **Apply glass effect** for cards - `glass` class with `border border-white/10`
6. **Responsive design** - Use `md:` breakpoint for tablet/desktop layouts

## Asset Management

- Images stored alongside HTML files
- No CDN configuration (local assets)
- PNG format for screenshots and diagrams

## Compliance Dashboard Design

When creating compliance dashboards and reports:

1. **Use HTML + Tailwind CSS** - Match existing SCBE design system
2. **Dark theme with glass effects** - Use gradient background and glass cards
3. **Color semantics for status**:
   - Green: Compliant, secure, passing
   - Yellow: Warnings, partial compliance
   - Red: Critical issues, failures
   - Blue: Informational, metrics

**Dashboard Sections:**

- Executive Summary (overall score, standards status)
- Quantum Security Metrics (security bits, PQC status)
- AI Safety Dashboard (intent accuracy, governance violations)
- Performance Metrics (throughput, latency, uptime)
- Security Scorecard (vulnerabilities, fuzzing coverage)
- Test Execution Status (passed/failed/skipped)

**Example Dashboard Card:**

```html
<section class="glass rounded-2xl p-8 mb-8 border border-white/10">
  <h2 class="text-2xl font-bold text-white mb-6">Quantum Security</h2>
  <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
    <div class="text-center p-6 bg-blue-500/20 rounded-xl">
      <div class="text-4xl font-bold text-blue-400">256</div>
      <div class="text-sm text-gray-400">Security Bits</div>
      <div class="mt-2 inline-block px-3 py-1 bg-green-600 rounded-full text-xs">Target Met</div>
    </div>
  </div>
</section>
```

## Test Implementation Guidelines

### Property-Based Test Pattern

```typescript
// TypeScript with fast-check
import fc from 'fast-check';

// Feature: enterprise-grade-testing, Property 1: Shor's Algorithm Resistance
// Validates: Requirements AC-1.1
it("Property 1: Shor's Algorithm Resistance", () => {
  fc.assert(
    fc.property(
      fc.record({
        keySize: fc.integer({ min: 2048, max: 4096 }),
        qubits: fc.integer({ min: 10, max: 100 }),
      }),
      (params) => {
        const rsaKey = generateRSAKey(params.keySize);
        const result = simulateShorAttack(rsaKey, params.qubits);
        return !result.success; // Attack should fail
      }
    ),
    { numRuns: 100 } // Minimum 100 iterations
  );
});
```

```python
# Python with hypothesis
from hypothesis import given, strategies as st

# Feature: enterprise-grade-testing, Property 1: Shor's Algorithm Resistance
# Validates: Requirements AC-1.1
@pytest.mark.quantum
@pytest.mark.property
@given(
    key_size=st.integers(min_value=2048, max_value=4096),
    qubits=st.integers(min_value=10, max_value=100)
)
def test_property_1_shors_algorithm_resistance(key_size, qubits):
    """Property 1: Shor's Algorithm Resistance"""
    rsa_key = generate_rsa_key(key_size)
    result = simulate_shor_attack(rsa_key, qubits)
    assert not result.success  # Attack should fail
```

### Unit Test Pattern

```typescript
// TypeScript unit test
describe("Shor's Algorithm Edge Cases", () => {
  it('should fail to factor RSA-2048 key', () => {
    const rsaKey = generateRSAKey(2048);
    const result = simulateShorAttack(rsaKey, 20);
    expect(result.success).toBe(false);
    expect(result.timeComplexity).toBeGreaterThan(2 ** 80);
  });
});
```

### Test Markers (pytest)

- `@pytest.mark.quantum` - Quantum attack tests
- `@pytest.mark.ai_safety` - AI safety tests
- `@pytest.mark.agentic` - Agentic coding tests
- `@pytest.mark.compliance` - Compliance tests
- `@pytest.mark.stress` - Stress tests
- `@pytest.mark.security` - Security tests
- `@pytest.mark.formal` - Formal verification tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.property` - Property-based tests
- `@pytest.mark.slow` - Long-running tests (>1 minute)
- `@pytest.mark.unit` - Unit tests

## SCBE Architecture Integration

### 14-Layer Security Stack

When testing, ensure coverage of all layers:

1. **Context Layer** - Contextual encryption
2. **Metric Layer** - Distance-based security
3. **Breath Layer** - Temporal dynamics
4. **Phase Layer** - Phase space encryption
5. **Potential Layer** - Energy-based security
6. **Spectral Layer** - Frequency domain
7. **Spin Layer** - Quantum spin states
8. **Triadic Layer** - Three-way verification
9. **Harmonic Layer** - Resonance-based security
10. **Decision Layer** - Adaptive security
11. **Audio Layer** - Cymatic patterns
12. **Quantum Layer** - Post-quantum crypto (ML-KEM, ML-DSA)
13. **Anti-Fragile Layer** - Self-healing
14. **Topological CFI** - Control flow integrity

### Post-Quantum Cryptography

- **ML-KEM (Kyber768)** - Key encapsulation mechanism
- **ML-DSA (Dilithium3)** - Digital signature algorithm
- **Lattice-based primitives** - Foundation for PQC

### PHDM (Polyhedral Hamiltonian Defense Manifold)

- 16 canonical polyhedra for intrusion detection
- Hamiltonian path with HMAC chaining
- 6D geodesic distance for anomaly detection

### Symphonic Cipher

- Complex number encryption
- FFT-based transformations
- Feistel network structure
- ZBase32 encoding
- Hybrid cryptography integration

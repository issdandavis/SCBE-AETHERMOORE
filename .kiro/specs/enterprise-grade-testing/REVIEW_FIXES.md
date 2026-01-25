---
inclusion: fileMatch
fileMatchPattern: ['**/enterprise-grade-testing/**/*', '**/tests/enterprise/**/*', '**/tests/orchestration/**/*', '**/tests/reporting/**/*']
---

# Enterprise Testing Implementation Guidelines

This document provides critical guidance for implementing the enterprise-grade-testing spec. All fixes and clarifications documented here MUST be followed when working on enterprise testing tasks.

---

## Critical Implementation Rules

### 1. Compliance Certification Boundaries

**NEVER claim internal tests provide certification.** Compliance testing collects evidence for external audits only.

**Correct terminology:**
- ✅ "Evidence collection for SOC 2 audit"
- ✅ "Audit-ready compliance documentation"
- ✅ "Preparation for FIPS 140-3 certification"
- ❌ "SOC 2 certified"
- ❌ "FIPS 140-3 validated"
- ❌ "ISO 27001 compliant"

**Implementation:**
- Use "validation" for internal tests
- Use "certification" only when referring to external audit outcomes
- Include disclaimers in all compliance reports
- Success criteria: "audit-ready" not "certified"

**Affected tasks:** 22, 23, 25, 26, 27 (Phase 5 - Compliance)

---

### 2. Performance Testing Environment Specifications

**Baseline Environment (Required):**
- 8-core CPU, 32GB RAM
- 1Gbps network
- 24-hour soak tests
- 100K req/s throughput target
- 10M fuzzing iterations

**Stretch Environment (Optional):**
- 32-core CPU, 128GB RAM
- 10Gbps network, 10-node cluster
- 72-hour soak tests
- 1M req/s throughput target
- 1B fuzzing iterations
- Budget: $5K-$10K/month

**Implementation:**
- Always implement baseline targets first
- Mark stretch goals as optional in code comments
- Document environment requirements in test files
- Use environment variables to switch between baseline/stretch modes

**Affected tasks:** 31, 32, 33, 37 (Phase 6 - Stress & Security)

---

### 3. Quantum Security Validation Scope

**Simulator limitations:**
- Quantum simulators provide theoretical security analysis
- NOT physical quantum computer resistance proof
- Limited to small qubit counts (10-100 qubits)
- Extrapolation required for real-world security claims

**Implementation:**
- Always include "simulator-validated" qualifier
- Document qubit count limitations
- Add disclaimer: "Theoretical analysis, not physical quantum testing"
- Success criteria: "Simulator-validated 256-bit post-quantum security (theoretical)"

**Affected tasks:** 4, 5, 6 (Phase 2 - Quantum)

---

### 4. Consolidated Components (No Duplication)

**Test Orchestration:**
- Single implementation: Task 2 (Phase 1)
- Location: `tests/orchestration/test_scheduler.ts`
- Do NOT create duplicate orchestration in Phase 8

**Compliance Dashboard:**
- Single implementation: Task 27 (Phase 5)
- Location: `tests/reporting/compliance_dashboard.html`
- Do NOT create duplicate dashboard in Phase 8

**Implementation:**
- Check for existing implementations before creating new ones
- Reference consolidated tasks in later phases
- Update existing components rather than duplicating

---

### 5. Property-Based Testing Requirements

**Minimum standards:**
- 100 iterations per property test (fast-check/hypothesis)
- Dual testing: unit tests + property tests
- Requirement traceability comments in every test
- Test markers for categorization

**Test file structure:**
```typescript
// Feature: enterprise-grade-testing, Property X: [Name]
// Validates: Requirements AC-X.X
it('Property X: [Name]', () => {
  fc.assert(
    fc.property(/* generators */, (params) => {
      // Test logic
    }),
    { numRuns: 100 } // REQUIRED minimum
  );
});
```

**Python equivalent:**
```python
# Feature: enterprise-grade-testing, Property X: [Name]
# Validates: Requirements AC-X.X
@pytest.mark.[category]
@pytest.mark.property
@given(/* strategies */)
def test_property_x_name(params):
    """Property X: [Name]"""
    # Test logic
```

**Affected tasks:** All property test tasks (1-41)

---

### 6. Status and Version Consistency

**Current project state:**
- Version: 3.0.0 (NOT 3.2.0-enterprise)
- Status: "Ready for Implementation"
- Success criteria: Unchecked until task completion

**Implementation:**
- Use version 3.0.0 in all files
- Mark tasks as "Ready for Implementation" not "In Progress"
- Check success criteria only after validation
- Keep header/footer status synchronized

---

### 7. Requirement Traceability

**All requirements defined in:** `.kiro/specs/enterprise-grade-testing/requirements.md`

**Reference format:**
- TR-* : Technical Requirements
- AC-* : Acceptance Criteria
- TEST-* : Test Requirements
- DR-* : Design Requirements
- DOC-* : Documentation Requirements
- PR-* : Performance Requirements

**Implementation:**
- Link every test to specific requirements
- Use requirement IDs in test comments
- Validate requirement coverage in reports
- Update requirements.md if new requirements emerge

---

## Test Implementation Patterns

### Test File Organization

```
tests/enterprise/
├── quantum/              # Properties 1-6
│   ├── property_tests.test.ts
│   └── unit_tests.test.ts
├── ai_brain/             # Properties 7-12
│   ├── property_tests.test.ts
│   └── unit_tests.test.ts
├── agentic/              # Properties 13-18
│   ├── property_tests.test.ts
│   └── unit_tests.test.ts
├── compliance/           # Properties 19-24
│   ├── property_tests.test.ts
│   └── unit_tests.test.ts
├── stress/               # Properties 25-30
│   ├── property_tests.test.ts
│   └── unit_tests.test.ts
├── security/             # Properties 31-35
│   ├── property_tests.test.ts
│   └── unit_tests.test.ts
├── formal/               # Properties 36-39
│   ├── property_tests.test.ts
│   └── unit_tests.test.ts
└── integration/          # Properties 40-41
    ├── property_tests.test.ts
    └── unit_tests.test.ts
```

### Test Markers (pytest)

Use these markers to categorize tests:

```python
@pytest.mark.quantum        # Quantum attack tests
@pytest.mark.ai_safety      # AI safety tests
@pytest.mark.agentic        # Agentic coding tests
@pytest.mark.compliance     # Compliance tests
@pytest.mark.stress         # Stress tests
@pytest.mark.security       # Security tests
@pytest.mark.formal         # Formal verification tests
@pytest.mark.integration    # Integration tests
@pytest.mark.property       # Property-based tests
@pytest.mark.slow           # Long-running tests (>1 minute)
@pytest.mark.unit           # Unit tests
```

### Compliance Dashboard Structure

Use the SCBE design system (dark theme, glass effects, Tailwind CSS):

```html
<section class="glass rounded-2xl p-8 mb-8 border border-white/10">
  <h2 class="text-2xl font-bold text-white mb-6">[Section Title]</h2>
  <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
    <div class="text-center p-6 bg-blue-500/20 rounded-xl">
      <div class="text-4xl font-bold text-blue-400">[Value]</div>
      <div class="text-sm text-gray-400">[Label]</div>
      <div class="mt-2 inline-block px-3 py-1 bg-green-600 rounded-full text-xs">
        [Status]
      </div>
    </div>
  </div>
</section>
```

**Color semantics:**
- Green: Compliant, secure, passing
- Yellow: Warnings, partial compliance
- Red: Critical issues, failures
- Blue: Informational, metrics

---

## Architecture Integration

### 14-Layer SCBE Stack Coverage

Ensure tests cover all layers:

1. Context Layer - Contextual encryption
2. Metric Layer - Distance-based security
3. Breath Layer - Temporal dynamics
4. Phase Layer - Phase space encryption
5. Potential Layer - Energy-based security
6. Spectral Layer - Frequency domain
7. Spin Layer - Quantum spin states
8. Triadic Layer - Three-way verification
9. Harmonic Layer - Resonance-based security
10. Decision Layer - Adaptive security
11. Audio Layer - Cymatic patterns
12. Quantum Layer - Post-quantum crypto (ML-KEM, ML-DSA)
13. Anti-Fragile Layer - Self-healing
14. Topological CFI - Control flow integrity

### Post-Quantum Cryptography

**ML-KEM (Kyber768):**
- Key encapsulation mechanism
- 256-bit post-quantum security
- Test against Shor's algorithm simulation

**ML-DSA (Dilithium3):**
- Digital signature algorithm
- Lattice-based security
- Test signature forgery resistance

### PHDM Integration

**Polyhedral Hamiltonian Defense Manifold:**
- 16 canonical polyhedra for intrusion detection
- Hamiltonian path with HMAC chaining
- 6D geodesic distance for anomaly detection

**Test requirements:**
- Validate polyhedra geometry
- Test HMAC chain integrity
- Verify anomaly detection accuracy

---

## Common Pitfalls to Avoid

### ❌ Don't Do This

1. **Claiming certification without external audit**
   ```typescript
   // ❌ WRONG
   expect(result.certified).toBe(true);
   expect(result.status).toBe('SOC 2 Certified');
   ```

2. **Hard-coding unrealistic targets without environment context**
   ```typescript
   // ❌ WRONG
   const TARGET_THROUGHPUT = 1_000_000; // req/s
   expect(throughput).toBeGreaterThan(TARGET_THROUGHPUT);
   ```

3. **Duplicating existing implementations**
   ```typescript
   // ❌ WRONG - Task 2 already implements this
   class TestOrchestrator { /* ... */ }
   ```

4. **Skipping requirement traceability**
   ```typescript
   // ❌ WRONG - No requirement reference
   it('should resist quantum attacks', () => { /* ... */ });
   ```

### ✅ Do This Instead

1. **Use audit-ready terminology**
   ```typescript
   // ✅ CORRECT
   expect(result.auditReady).toBe(true);
   expect(result.status).toBe('Evidence Collected for SOC 2 Audit');
   ```

2. **Use environment-aware targets**
   ```typescript
   // ✅ CORRECT
   const TARGET_THROUGHPUT = process.env.STRETCH_MODE 
     ? 1_000_000  // Stretch goal
     : 100_000;   // Baseline
   expect(throughput).toBeGreaterThan(TARGET_THROUGHPUT);
   ```

3. **Reference existing implementations**
   ```typescript
   // ✅ CORRECT
   import { TestOrchestrator } from '../orchestration/test_scheduler';
   ```

4. **Include requirement traceability**
   ```typescript
   // ✅ CORRECT
   // Feature: enterprise-grade-testing, Property 1: Shor's Algorithm Resistance
   // Validates: Requirements AC-1.1
   it('Property 1: Shor\'s Algorithm Resistance', () => { /* ... */ });
   ```

---

## Quick Reference

### File Locations

- **Requirements:** `.kiro/specs/enterprise-grade-testing/requirements.md`
- **Design:** `.kiro/specs/enterprise-grade-testing/design.md`
- **Tasks:** `.kiro/specs/enterprise-grade-testing/tasks.md`
- **Test Orchestrator:** `tests/orchestration/test_scheduler.ts`
- **Compliance Dashboard:** `tests/reporting/compliance_dashboard.html`
- **Enterprise Tests:** `tests/enterprise/[category]/`

### Key Commands

```bash
# TypeScript tests
npm test                                    # All tests
npm test -- tests/enterprise/quantum/       # Specific category
npm test -- --coverage                      # With coverage

# Python tests
pytest tests/enterprise/ -v                 # All tests
pytest -m quantum tests/enterprise/         # Specific marker
pytest tests/enterprise/ --cov=src          # With coverage
```

### Environment Variables

```bash
# Performance testing mode
STRETCH_MODE=true          # Enable stretch goals
BASELINE_MODE=true         # Use baseline targets (default)

# Test configuration
MIN_ITERATIONS=100         # Minimum property test iterations
COVERAGE_TARGET=95         # Coverage percentage target
```

---

## Implementation Checklist

When implementing any enterprise testing task:

- [ ] Read requirements.md for requirement definitions
- [ ] Check for existing implementations (avoid duplication)
- [ ] Use correct compliance terminology (audit-ready, not certified)
- [ ] Implement baseline targets first, stretch goals optional
- [ ] Include requirement traceability comments
- [ ] Use minimum 100 iterations for property tests
- [ ] Add appropriate test markers (@pytest.mark.*)
- [ ] Document environment requirements
- [ ] Follow SCBE design system for dashboards
- [ ] Test against all 14 SCBE layers where applicable
- [ ] Use version 3.0.0 consistently
- [ ] Update success criteria only after validation

---

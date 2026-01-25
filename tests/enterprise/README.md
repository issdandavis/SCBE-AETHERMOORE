# Enterprise-Grade Testing Suite

This directory contains comprehensive enterprise-grade tests for SCBE-AETHERMOORE v3.0.0.

## Directory Structure

- **quantum/** - Quantum attack simulation tests (Shor's, Grover's, PQC validation)
- **ai_brain/** - AI safety and governance tests (intent verification, boundaries, consensus)
- **agentic/** - Agentic coding system tests (code generation, vulnerability scanning)
- **compliance/** - Enterprise compliance tests (SOC 2, ISO 27001, FIPS 140-3, Common Criteria)
- **stress/** - Stress and load testing (throughput, latency, memory leaks, DDoS)
- **security/** - Security testing (fuzzing, side-channel analysis, fault injection)
- **formal/** - Formal verification tests (model checking, theorem proving, property-based)
- **integration/** - Integration and end-to-end tests

## Test Categories

Each test file should include:
1. **Unit tests** - Specific examples and edge cases
2. **Property-based tests** - Universal properties with random inputs (min 100 iterations)

## Running Tests

```bash
# Run all enterprise tests (TypeScript)
npm test -- tests/enterprise/

# Run specific category
npm test -- tests/enterprise/quantum/

# Run with coverage
npm test -- --coverage

# Run Python tests
pytest tests/enterprise/ -v

# Run specific marker
pytest -m quantum tests/enterprise/
```

## Test Requirements

- All tests must include requirement traceability comments
- Property tests must run minimum 100 iterations
- Test coverage target: >95%
- Follow existing SCBE design patterns

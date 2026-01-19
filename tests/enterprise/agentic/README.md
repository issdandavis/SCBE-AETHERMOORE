# Agentic Coding System Tests

Tests for secure autonomous code generation, vulnerability scanning, and human-in-the-loop.

## Test Files

- `code_generation.test.ts` - Secure code generation with constraints
- `vulnerability_scan.test.ts` - Vulnerability detection (OWASP, CWE)
- `intent_code_alignment.test.ts` - Intent-code alignment verification
- `rollback.test.ts` - Code versioning and rollback
- `compliance_check.test.ts` - OWASP/CWE compliance checking
- `human_in_loop.test.ts` - Human approval for critical changes

## Properties Tested

- **Property 13**: Security Constraint Enforcement (AC-3.1)
- **Property 14**: Vulnerability Detection Rate >95% (AC-3.2)
- **Property 15**: Intent-Code Alignment (AC-3.3)
- **Property 16**: Rollback Correctness (AC-3.4)
- **Property 17**: Compliance Checking Completeness (AC-3.6)
- **Property 18**: Human-in-the-Loop Verification (AC-3.5)

## Target Metrics

- Vulnerability detection rate: >95%
- Security constraint violations: 0
- Rollback success rate: 100%
- Human approval timeout: Configurable (default: 5 minutes)

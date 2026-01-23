# What's Left To Do
## SCBE-AETHERMOORE Roadmap

---

## Immediate (This Week)

### Quick Wins (2-4 hours total)
- [ ] Fix 4 remaining edge case tests
  - Layer 4 boundary clamping tolerance
  - Layer 7 identity/rotation precision
  - Layer 9 FFT coherence threshold

### Patent Filing (by Jan 31, 2026)
- [ ] Submit USPTO provisional patent #63/961,403
- [ ] Compile 6 inventions into formal claims

---

## Short-Term (30-60 Days)

### Technical
- [ ] Complete mathematical review corrections (ACTION_ITEMS_FROM_REVIEW.md)
- [ ] Add explicit type annotations to Python code
- [ ] Improve error messages in API endpoints

### Documentation
- [ ] Create Security Data Sheet (SDS)
- [ ] Write customer onboarding guide
- [ ] Add production deployment runbook

---

## Medium-Term (60-180 Days)

### Post-Quantum Cryptography
- [ ] Integrate liboqs-python (ML-KEM-768)
- [ ] Implement ML-DSA-65 signatures
- [ ] Create hybrid classical+PQC mode
- [ ] Full test suite for PQC operations
- **Estimated effort**: 40-60 hours

### Observability
- [ ] Prometheus metrics exporters
- [ ] Datadog integration
- [ ] OpenTelemetry (OTLP) support
- [ ] SLA latency dashboards
- **Estimated effort**: 30-40 hours

### Enterprise Features
- [ ] Multi-tenant isolation
- [ ] API key rotation/expiration
- [ ] Admin management endpoints
- [ ] Webhook/event notifications
- **Estimated effort**: 50-70 hours

---

## Long-Term (6-12 Months)

### Certifications
- [ ] SOC 2 Type II audit ($100-150K, 6-9 months)
- [ ] ISO 27001:2022 ($50-100K, 6-12 months)
- [ ] HIPAA Business Associate (if healthcare)
- [ ] FedRAMP (if government)

### Business Infrastructure
- [ ] Define target customer profile (ICP)
- [ ] Create competitive positioning document
- [ ] Develop pricing/licensing model
- [ ] Build sales collateral
- [ ] Establish partner channel strategy

### Team Hiring
- [ ] Security Engineer (critical)
- [ ] DevOps/SRE Engineer (critical)
- [ ] Product Manager (high priority)
- [ ] Solutions Architect (medium priority)
- [ ] Technical Writer (medium priority)

---

## Known Issues to Fix

### 4 Failing Edge Case Tests
1. `test_layer4_boundary_clamping_tolerance` - Float precision at boundary
2. `test_layer7_identity_transform_precision` - Identity matrix edge case
3. `test_layer7_rotation_isometry_precision` - Quaternion rounding
4. `test_layer9_fft_coherence_threshold` - Threshold tuning needed

### Technical Debt
- `src/metrics/telemetry.ts:47` - "TODO: implement datadog/prom/otlp exporters"
- PQC placeholders using SHA3-256 hashes instead of real ML-KEM/ML-DSA

### Documentation Gaps
- No enterprise SLA commitments
- No incident response procedures
- No business continuity plan
- No vulnerability disclosure policy

---

## Priority Matrix

| Task | Impact | Effort | Priority |
|------|--------|--------|----------|
| Fix 4 failing tests | High | Low | **P0** |
| Patent filing | Critical | Medium | **P0** |
| PQC integration | High | High | **P1** |
| SOC 2 preparation | High | High | **P1** |
| Observability | Medium | Medium | **P2** |
| Enterprise features | Medium | High | **P2** |
| Documentation | Medium | Low | **P3** |

---

## Success Metrics

### Technical
- [ ] 100% test pass rate (currently 96%)
- [ ] <100ms p99 latency for core operations
- [ ] Zero security vulnerabilities in audit

### Business
- [ ] SOC 2 Type II certified
- [ ] 3+ enterprise POCs
- [ ] First paying customer

### Team
- [ ] 5+ FTEs hired
- [ ] Clear roadmap ownership

---

*Last Updated: January 23, 2026*

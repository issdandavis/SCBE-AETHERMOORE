# Enterprise Compliance Tests

Tests for SOC 2, ISO 27001, FIPS 140-3, Common Criteria EAL4+, NIST CSF, and PCI DSS compliance.

## Test Files

- `soc2.test.ts` - SOC 2 Trust Services Criteria validation
- `iso27001.test.ts` - ISO 27001:2022 control validation (93 controls)
- `fips140.test.ts` - FIPS 140-3 cryptographic validation
- `common_criteria.test.ts` - Common Criteria EAL4+ security targets
- `nist_csf.test.ts` - NIST Cybersecurity Framework alignment
- `pci_dss.test.ts` - PCI DSS Level 1 compliance (if applicable)

## Properties Tested

- **Property 19**: SOC 2 Control Compliance (AC-4.1)
- **Property 20**: ISO 27001 Control Compliance (AC-4.2)
- **Property 21**: FIPS 140-3 Test Vector Compliance (AC-4.3)
- **Property 22**: Common Criteria Security Target Compliance (AC-4.4)
- **Property 23**: NIST Cybersecurity Framework Alignment (AC-4.5)
- **Property 24**: PCI DSS Level 1 Compliance (AC-4.6)

## Target Metrics

- Control coverage: 100%
- Compliance score: >98%
- Evidence completeness: 100%
- Audit readiness: Pass

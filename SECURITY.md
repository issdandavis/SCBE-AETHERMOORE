# Security Policy

## Assurance status

SCBE has an engineering self-assessment against selected NIST SSDF 1.1 practices,
with explicit evidence and unresolved deployment requirements. It is **not NIST
certified or FIPS 140-3 validated**. Algorithm names, passing CI and Lean proofs
are not validation certificates. See [the current assessment](docs/security/NIST_READINESS.md).

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.x.x   | :white_check_mark: |
| 2.x.x   | :white_check_mark: (security fixes only) |
| 1.x.x   | :x:                |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

1. **DO NOT** open a public GitHub issue for security vulnerabilities
2. Email security concerns to: **aethermoregames@pm.me**
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes

### Response Timeline

| Severity | Initial Response | Resolution Target |
|----------|------------------|-------------------|
| Critical | 24 hours | 7 days |
| High | 48 hours | 14 days |
| Medium | 7 days | 30 days |
| Low | 14 days | 90 days |

### What to Expect

1. Acknowledgment of your report within the response time
2. Regular updates on our progress
3. Credit in the security advisory (unless you prefer anonymity)
4. Notification when the vulnerability is fixed

## Security Best Practices

### For Operators

1. **Never hardcode API keys** - Use environment variables
   ```bash
   export SCBE_API_KEY=$(openssl rand -hex 32)
   ```

2. **Use TLS 1.3** - Configure your reverse proxy appropriately

3. **Verify audit coverage** - Confirm the deployed entry point records final decisions and exports durable logs

4. **Rotate keys regularly** - Recommended: 90 days

5. **Monitor for anomalies** - Export logs to your SIEM

### For Developers

1. **No secrets in code** - Use environment variables or secret managers
2. **Pin dependencies** - Use lockfiles with hashes
3. **Run security scans** - Bandit for Python, npm audit for Node
4. **Review PRs** - All changes require review

## Security Features

### Cryptographic targets (backend and release configuration must be verified)

| Purpose | Algorithm | Standard |
|---------|-----------|----------|
| Symmetric Encryption | AES-256-GCM | AES: FIPS 197; GCM: SP 800-38D |
| Key Encapsulation | ML-KEM-768 | NIST FIPS 203 |
| Digital Signatures | ML-DSA-65 | NIST FIPS 204 |
| Hashing | SHA-3-256 | NIST FIPS 202 |
| Key Derivation | HKDF | RFC 5869 |

### Authorization and audit contracts

The reviewed Python pipelines preserve earlier REVIEW/DENY/SNAP restrictions in
final composition; only ALLOW updates their approved reference. Directed CFI
checks use frozen edges rather than geometry alone. The full-system HMAC audit
schema `scbe.full-system-decision.v2` binds both pipeline and final decisions.
Other entry points need a deployment-specific coverage and persistence audit.

## Known Limitations

1. RuntimeGate still has a five-request automatic calibration window. It is a
   heuristic risk layer, not sufficient authentication or authorization.
2. Runtime policies, calibration inputs, entry points, snapshot files and key
   material require trusted configuration and OS-level access controls.
3. This review does not establish that every service/tool call uses these guards,
   that capabilities are replay-safe, or that logs survive crashes/tampering.
4. PQC mocks provide no secrecy or signature security. The legacy `pqc_core`
   wrapper refuses mock operations by default. Only isolated tests may set both
   `SCBE_ENV=test` and `SCBE_ALLOW_MOCK_PQC=1`; never deploy those settings.
   The separate `src.crypto.pqc_liboqs` wrapper has its own
   `SCBE_ALLOW_INSECURE_PQC` override, which must also be absent in production.
5. Neither liboqs availability nor pure Python algorithm implementations establish
   FIPS module validation. Verify the actual module certificate, version,
   approved operating mode and deployment environment when validation is required.
6. Historical test and marketing documents are not assurance evidence. In
   particular, expected failures/skips and benchmark summaries cannot establish
   conformance. The dated assessment lists remaining release blockers.

### Entropy Surface Defense Layer

Experimental anti-extraction output mixing; no general security guarantee is established:

| Posture | Signal Retention | Trigger |
|---------|-----------------|---------|
| TRANSPARENT | ~100% | Normal operation |
| GUARDED | 50-95% | Mild anomaly detected |
| OPAQUE | 10-50% | Active probing or budget pressure |
| SILENT | <10% | Budget exhausted or confirmed extraction |

The output mixer `N(x) = σ · f(x) + (1 - σ) · U` retains some signal whenever σ is positive. Its effect on extraction must be measured against adaptive attacks; the formula does not prove that an attacker learns only uniform noise.

- TypeScript: `packages/kernel/src/entropySurface.ts`
- Python: `src/symphonic_cipher/scbe_aethermoore/entropy_surface.py`

## Security Contacts

For security-related inquiries:
- GitHub Security Advisories: enabled on this repository
- Email: **aethermoregames@pm.me** (Issac Daniel Davis, Founder)
- Patent: USPTO #63/961,403 (provisional)
- ORCID: 0009-0002-3936-9369

## Acknowledgments

We thank the following for responsible disclosure:
- (None yet — be the first!)

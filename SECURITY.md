# Security Policy

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

3. **Enable audit logging** - All decisions are logged by default

4. **Rotate keys regularly** - Recommended: 90 days

5. **Monitor for anomalies** - Export logs to your SIEM

### For Developers

1. **No secrets in code** - Use environment variables or secret managers
2. **Pin dependencies** - Use lockfiles with hashes
3. **Run security scans** - Bandit for Python, npm audit for Node
4. **Review PRs** - All changes require review

## Security Features

### Cryptographic Choices

| Purpose | Algorithm | Standard |
|---------|-----------|----------|
| Symmetric Encryption | AES-256-GCM | NIST FIPS 197 |
| Key Encapsulation | ML-KEM-768 | NIST FIPS 203 |
| Digital Signatures | ML-DSA-65 | NIST FIPS 204 |
| Hashing | SHA-3-256 | NIST FIPS 202 |
| Key Derivation | HKDF | RFC 5869 |

### Zero Trust Design

- Every request requires authentication
- No implicit trust between components
- All decisions are logged and auditable
- Fail-secure: defaults to DENY

### Audit Trail

All governance decisions include:
- Timestamp (ISO 8601)
- Agent identity
- Action attempted
- Decision (ALLOW/DENY/QUARANTINE)
- Score and explanation
- Correlation ID

## Known Limitations

1. **In-memory storage** - Production deployments should use persistent storage
2. **Single-node** - High availability requires external load balancing
3. **PQC fallback** - Full NIST PQC requires `liboqs` or `kyber-py`/`dilithium-py` (pure Python fallback available)
4. **Timestamp race condition** - `test_121_large_medical_image_transfer` has a known timing-dependent assertion under heavy load; tracked and non-exploitable

### Entropy Surface Defense Layer

Active anti-extraction defense using information-theoretic nullification:

| Posture | Signal Retention | Trigger |
|---------|-----------------|---------|
| TRANSPARENT | ~100% | Normal operation |
| GUARDED | 50-95% | Mild anomaly detected |
| OPAQUE | 10-50% | Active probing or budget pressure |
| SILENT | <10% | Budget exhausted or confirmed extraction |

The nullification function `N(x) = σ · f(x) + (1 - σ) · U` ensures surrogate models trained on probing pairs converge to the uniform distribution — they learn noise, not behavior.

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

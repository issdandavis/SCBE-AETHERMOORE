# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

1. **DO NOT** open a public GitHub issue for security vulnerabilities
2. Email security concerns to: [security contact - to be configured]
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
3. **PQC fallback** - Full NIST PQC requires `pypqc` library installation

## Security Contacts

For security-related inquiries:
- GitHub Security Advisories: [Configure in repo settings]
- Email: [To be configured]

## Acknowledgments

We thank the following for responsible disclosure:
- (None yet)

# SCBE-AETHERMOORE Security Hardening Checklist

**Purpose:** Bank procurement readiness
**Standard:** NIST 800-53, PCI-DSS, FFIEC, DORA
**Status:** In Progress

---

## 1. Cryptography, Authentication & Data Protection

### 1.1 Cryptographic Primitives

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| AES-256-GCM for symmetric encryption | ✅ Implemented | ✅ | - |
| TLS 1.3 only (no 1.2 fallback) | ⚠️ Not enforced | Required | HIGH |
| NIST PQC (ML-KEM-768, ML-DSA-65) | ⚠️ Fallback mode | Full implementation | HIGH |
| No custom/ad-hoc KDFs | ❌ Some custom code | Standard HKDF | HIGH |
| No XOR-based "encryption" | ❌ Demo code exists | Remove | CRITICAL |
| Secure random (CSPRNG only) | ✅ secrets module | ✅ | - |

**Action Items:**
- [ ] Replace all XOR cipher code with AES-256-GCM
- [ ] Implement HKDF (RFC 5869) for all key derivation
- [ ] Integrate `pypqc` or `liboqs` for real PQC
- [ ] Add TLS 1.3 enforcement in deployment config

### 1.2 Key Management

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| No hardcoded keys/secrets | ❌ Demo key in code | Environment only | CRITICAL |
| HSM/KMS integration | ❌ Not implemented | AWS KMS / HashiCorp Vault | HIGH |
| Automated key rotation | ❌ Not implemented | 90-day rotation | MEDIUM |
| Separation of duties | ❌ Single admin | Role-based | MEDIUM |
| Key escrow/recovery | ❌ Not implemented | Documented process | MEDIUM |

**Action Items:**
- [ ] Remove `sk_test_demo_key_12345` from source code
- [ ] Add environment variable loading for all secrets
- [ ] Create KMS integration module (AWS KMS / Vault)
- [ ] Document key rotation procedure
- [ ] Implement key versioning

### 1.3 Identity & Access Control

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| API key authentication | ✅ Implemented | ✅ | - |
| mTLS for service-to-service | ❌ Not implemented | Required for prod | HIGH |
| OAuth2/OIDC integration | ❌ Not implemented | Enterprise SSO | MEDIUM |
| MFA for admin access | ❌ N/A (no admin UI) | Required | HIGH |
| RBAC for operators | ❌ Not implemented | Role-based | MEDIUM |
| Machine identity (certs) | ❌ Not implemented | X.509 certs | HIGH |

**Action Items:**
- [ ] Add mTLS support to API server
- [ ] Create certificate management module
- [ ] Add OIDC client for enterprise SSO
- [ ] Implement RBAC middleware

---

## 2. Software & Infrastructure Hardening

### 2.1 Secure SDLC

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| Threat model documented | ⚠️ Partial | Full threat model | HIGH |
| Code review process | ⚠️ PR reviews | Mandatory 2-person | MEDIUM |
| Static analysis (SAST) | ❌ Not configured | Bandit, Semgrep | HIGH |
| Dynamic analysis (DAST) | ❌ Not configured | OWASP ZAP | MEDIUM |
| Dependency scanning | ⚠️ npm audit only | Snyk/Dependabot | HIGH |
| Secure coding guidelines | ❌ Not documented | OWASP ASVS | MEDIUM |

**Action Items:**
- [ ] Add Bandit to CI pipeline for Python SAST
- [ ] Add Semgrep rules for security patterns
- [ ] Configure Dependabot for all dependencies
- [ ] Create SECURITY.md with secure coding guidelines
- [ ] Document threat model in security whitepaper

### 2.2 Hardened Defaults

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| Minimal container image | ⚠️ python:slim | distroless | MEDIUM |
| Non-root container user | ❌ Runs as root | Non-root user | HIGH |
| Read-only filesystem | ❌ Not configured | Read-only where possible | MEDIUM |
| No debug mode in prod | ⚠️ Not enforced | Explicit prod mode | HIGH |
| Secure default config | ⚠️ Partial | Security-first defaults | HIGH |
| No demo secrets shipped | ❌ Demo key in code | No secrets in image | CRITICAL |

**Action Items:**
- [ ] Update Dockerfile to use non-root user
- [ ] Remove all demo/test secrets from code
- [ ] Add production mode flag with secure defaults
- [ ] Create hardened base image

### 2.3 Patch & Vulnerability Management

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| CVE tracking process | ❌ Not documented | Documented process | HIGH |
| Patch SLAs defined | ❌ Not defined | Critical: 24h, High: 7d | HIGH |
| Dependency update process | ⚠️ Manual | Automated PRs | MEDIUM |
| Security advisory process | ❌ Not defined | SECURITY.md + process | HIGH |

**Action Items:**
- [ ] Create vulnerability management policy
- [ ] Define patch SLAs by severity
- [ ] Enable Dependabot security updates
- [ ] Create SECURITY.md with disclosure process

---

## 3. Logging, Monitoring & Audit

### 3.1 Comprehensive Logging

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| Auth decisions logged | ✅ Implemented | ✅ | - |
| Policy changes logged | ❌ Not implemented | Required | HIGH |
| Key operations logged | ❌ Not implemented | Required | HIGH |
| Config changes logged | ❌ Not implemented | Required | MEDIUM |
| Admin actions logged | ❌ N/A (no admin) | Required | MEDIUM |
| Tamper-evident logs | ❌ Plain JSON | Signed/chained | HIGH |

**Action Items:**
- [ ] Add log signing (HMAC chain)
- [ ] Log all configuration changes
- [ ] Log key operations (generation, rotation)
- [ ] Add correlation IDs to all logs

### 3.2 SIEM Integration

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| Structured log format | ✅ JSON | ✅ | - |
| Correlation IDs | ⚠️ Partial | All requests | HIGH |
| Severity levels | ✅ Standard levels | ✅ | - |
| Log schema documented | ❌ Not documented | Full schema doc | MEDIUM |
| Splunk HEC support | ❌ Not implemented | HTTP Event Collector | HIGH |
| Syslog support | ❌ Not implemented | RFC 5424 | MEDIUM |

**Action Items:**
- [ ] Document log schema (JSON schema)
- [ ] Add Splunk HEC exporter
- [ ] Add syslog output option
- [ ] Ensure correlation ID in all logs

### 3.3 Audit & Forensics

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| Decision audit trail | ✅ In-memory | Persistent storage | HIGH |
| Who/what/when/why | ✅ Captured | ✅ | - |
| Export capability | ⚠️ API only | Bulk export | MEDIUM |
| Retention policy | ❌ Not defined | 7 years minimum | HIGH |

**Action Items:**
- [ ] Add persistent audit storage (database)
- [ ] Define retention policy (regulatory minimum)
- [ ] Add bulk export endpoint
- [ ] Add audit log search/filter

---

## 4. Zero Trust & Network Posture

### 4.1 Zero Trust Principles

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| Per-request authorization | ✅ Every call checked | ✅ | - |
| No implicit trust | ✅ All agents scored | ✅ | - |
| Continuous verification | ⚠️ Per-request only | + periodic re-auth | MEDIUM |
| Micro-segmentation ready | ⚠️ Single service | Network policies | MEDIUM |

### 4.2 Compromise Handling

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| Agent compromise response | ✅ Trust decay | ✅ | - |
| Relay compromise isolation | ⚠️ Theoretical | Documented procedure | HIGH |
| Lateral movement constraints | ⚠️ Not documented | Network isolation | MEDIUM |
| Fail-secure behavior | ✅ Fail to DENY | ✅ | - |

**Action Items:**
- [ ] Document compromise response procedures
- [ ] Add agent revocation endpoint
- [ ] Document network isolation requirements

### 4.3 Network Integration

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| TLS 1.3 support | ✅ Python default | Enforce only | HIGH |
| mTLS support | ❌ Not implemented | Required | HIGH |
| Proxy/firewall compatible | ✅ HTTP/HTTPS | ✅ | - |
| VPN/ZTNA compatible | ✅ Standard ports | ✅ | - |

---

## 5. Supply Chain & Vendor Risk

### 5.1 SBOM & Dependencies

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| SBOM generated | ❌ Not generated | CycloneDX/SPDX | HIGH |
| Signed builds | ❌ Not implemented | Sigstore/cosign | HIGH |
| License compliance | ⚠️ Apache 2.0 | Full audit | MEDIUM |
| Dependency pinning | ⚠️ Partial | Full lockfiles | HIGH |

**Action Items:**
- [ ] Generate SBOM with `syft` or `cdxgen`
- [ ] Sign container images with cosign
- [ ] Audit all dependency licenses
- [ ] Pin all dependencies with hashes

### 5.2 Attestations & Certifications

| Requirement | Current State | Target | Priority |
|-------------|---------------|--------|----------|
| SOC 2 Type I | ❌ Not started | Roadmap | HIGH |
| ISO 27001 | ❌ Not started | Roadmap | MEDIUM |
| Penetration test | ❌ Not done | Third-party required | HIGH |
| NIST 800-53 mapping | ⚠️ Partial | Full mapping | MEDIUM |

**Action Items:**
- [ ] Engage SOC 2 auditor (Type I first)
- [ ] Schedule third-party pentest
- [ ] Complete NIST 800-53 control mapping

---

## 6. Documentation for Procurement

### 6.1 Security Whitepaper

| Section | Status | Priority |
|---------|--------|----------|
| Threat model | ⚠️ Partial | HIGH |
| Protocol details | ✅ Documented | - |
| Crypto choices | ✅ Documented | - |
| Failure modes | ⚠️ Partial | HIGH |
| Attack resistance | ⚠️ Partial | HIGH |

### 6.2 Policy Documentation

| Document | Status | Priority |
|----------|--------|----------|
| Incident response plan | ❌ Not created | HIGH |
| Data retention policy | ❌ Not created | HIGH |
| Backup/restore procedure | ❌ Not created | MEDIUM |
| Business continuity | ❌ Not created | MEDIUM |

### 6.3 Regulatory Mapping

| Regulation | Status | Priority |
|------------|--------|----------|
| PCI-DSS mapping | ⚠️ Partial | HIGH |
| GLBA mapping | ⚠️ Partial | HIGH |
| FFIEC mapping | ❌ Not started | MEDIUM |
| DORA mapping | ⚠️ Partial | MEDIUM |

---

## Priority Summary

### CRITICAL (Block deployment)
1. Remove hardcoded demo API key
2. Remove XOR cipher code
3. Add non-root container user

### HIGH (Required for pilot)
4. Implement mTLS
5. Add Bandit/SAST to CI
6. Generate SBOM
7. Document threat model
8. Schedule penetration test
9. Add tamper-evident logging
10. Integrate real PQC library

### MEDIUM (Required for production)
11. HSM/KMS integration
12. OAuth2/OIDC support
13. SOC 2 Type I audit
14. Full regulatory mapping
15. Incident response plan

---

## Quick Wins (Can do today)

```bash
# 1. Remove hardcoded key (use environment)
export SCBE_API_KEY=$(openssl rand -hex 32)

# 2. Add Bandit to CI
pip install bandit
bandit -r src/ -f json -o bandit-report.json

# 3. Generate SBOM
pip install cyclonedx-bom
cyclonedx-py -r -o sbom.json

# 4. Pin dependencies
pip freeze > requirements.lock

# 5. Run container as non-root
# Add to Dockerfile: USER 1000:1000
```

---

## Deployment Mode Recommendation

For bank procurement, recommend **on-premise or private cloud** deployment:

| Mode | Pros | Cons |
|------|------|------|
| **On-Prem** | Full control, no data leaves bank | Bank manages infrastructure |
| **Private Cloud** | Bank's cloud account, isolated | Still cloud |
| **SaaS** | Easiest | Requires SOC 2, data concerns |

**Recommendation:** Start with on-prem/private cloud for pilots, then consider managed service after SOC 2.

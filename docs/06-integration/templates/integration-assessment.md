# Integration Assessment Template

Complete this assessment before integrating SCBE with your AI systems.

---

## Project Information

| Field | Value |
|-------|-------|
| Project Name | |
| Assessment Date | |
| Completed By | |
| Department | |

---

## 1. AI Agent Inventory

List all AI agents that will use SCBE:

| Agent ID | Description | Current Status | Priority |
|----------|-------------|----------------|----------|
| | | | |
| | | | |
| | | | |

---

## 2. Data Classification

What data will AI agents access?

| Data Type | Classification | Sensitivity | Volume/Day |
|-----------|----------------|-------------|------------|
| | Public / Internal / Confidential / Restricted | | |
| | | | |

---

## 3. Risk Assessment

### 3.1 What could go wrong if AI acts without governance?

- [ ] Unauthorized data access
- [ ] Financial loss
- [ ] Compliance violation
- [ ] Reputational damage
- [ ] Safety incident
- [ ] Other: ________________

### 3.2 Rate the risk level (1-5):

| Risk | Rating | Notes |
|------|--------|-------|
| Data breach | | |
| Unauthorized action | | |
| Compliance failure | | |
| Service disruption | | |

---

## 4. Compliance Requirements

Check all that apply:

- [ ] SOX
- [ ] HIPAA
- [ ] PCI-DSS
- [ ] GDPR
- [ ] CCPA
- [ ] FedRAMP
- [ ] SOC 2
- [ ] ISO 27001
- [ ] Other: ________________

---

## 5. Technical Requirements

### 5.1 Integration Method

- [ ] REST API
- [ ] SDK (Python/TypeScript)
- [ ] Message Queue
- [ ] Other: ________________

### 5.2 Performance Requirements

| Metric | Requirement |
|--------|-------------|
| Max latency | _____ ms |
| Requests/second | |
| Availability | _____ % |

### 5.3 Infrastructure

| Component | Technology |
|-----------|------------|
| Cloud provider | |
| Container platform | |
| CI/CD system | |
| Monitoring | |

---

## 6. Team Readiness

### 6.1 Security Team

- [ ] Identified security lead
- [ ] Policy expertise available
- [ ] Incident response process defined

### 6.2 Engineering Team

- [ ] Identified integration lead
- [ ] API integration experience
- [ ] Testing capacity available

---

## 7. Recommended Configuration

Based on assessment, recommended settings:

```yaml
# Recommended SCBE configuration
trust_thresholds:
  allow: ____
  quarantine: ____
  deny: ____

validators:
  count: ____
  quorum: ____
  timeout_ms: ____

audit:
  retention_days: ____
```

---

## 8. Action Items

| Item | Owner | Due Date | Status |
|------|-------|----------|--------|
| | | | |
| | | | |

---

## 9. Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Security Lead | | | |
| Engineering Lead | | | |
| Project Sponsor | | | |

---

*Template Version: 1.0*

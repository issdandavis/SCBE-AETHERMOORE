# AI Agent Onboarding Template

Use this template when adding a new AI agent to SCBE governance.

---

## Agent Information

| Field | Value |
|-------|-------|
| Agent ID | |
| Agent Name | |
| Department/Team | |
| Owner | |
| Onboarding Date | |

---

## 1. Agent Description

### 1.1 Purpose
*What does this AI agent do?*



### 1.2 Capabilities
*What actions can this agent perform?*

- [ ] Read data
- [ ] Write data
- [ ] Execute commands
- [ ] Make API calls
- [ ] Send communications
- [ ] Financial transactions
- [ ] Other: ________________

### 1.3 Data Access
*What data does this agent need?*

| Data Source | Access Type | Justification |
|-------------|-------------|---------------|
| | Read / Write | |
| | | |

---

## 2. Risk Profile

### 2.1 Risk Assessment

| Risk Category | Level (Low/Med/High) | Notes |
|---------------|----------------------|-------|
| Data sensitivity | | |
| Action impact | | |
| Frequency | | |
| Autonomy level | | |

### 2.2 Potential Harm
*What's the worst that could happen?*



---

## 3. Trust Configuration

### 3.1 Recommended Thresholds

Based on risk assessment:

| Threshold | Value | Rationale |
|-----------|-------|-----------|
| ALLOW | | |
| QUARANTINE | | |
| DENY | | |

### 3.2 Consensus Requirements

| Setting | Value |
|---------|-------|
| Validators required | |
| Quorum | |
| Timeout | |

---

## 4. Policy Rules

### 4.1 Allow Rules
*When should this agent's requests be auto-approved?*

```yaml
rules:
  - name: ""
    condition: ""
    action: "allow"
```

### 4.2 Escalation Rules
*When should requests require human review?*

```yaml
rules:
  - name: ""
    condition: ""
    action: "quarantine"
```

### 4.3 Deny Rules
*What should this agent never be allowed to do?*

```yaml
rules:
  - name: ""
    condition: ""
    action: "deny"
```

---

## 5. Integration Checklist

### 5.1 Engineering Tasks

- [ ] Generate agent credentials
- [ ] Configure API access
- [ ] Implement SCBE SDK integration
- [ ] Handle decision responses
- [ ] Add error handling
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Deploy to staging

### 5.2 Security Tasks

- [ ] Create agent policy
- [ ] Configure trust thresholds
- [ ] Set up monitoring alerts
- [ ] Define incident procedures
- [ ] Document in security inventory

### 5.3 Testing

- [ ] Test ALLOW scenarios
- [ ] Test QUARANTINE scenarios
- [ ] Test DENY scenarios
- [ ] Load testing
- [ ] Failure mode testing

---

## 6. Monitoring Setup

### 6.1 Alerts to Configure

| Alert | Threshold | Recipients |
|-------|-----------|------------|
| High DENY rate | > ___% | |
| Trust score drop | < ___ | |
| Error rate | > ___% | |

### 6.2 Dashboard Panels

- [ ] Request volume
- [ ] Decision distribution
- [ ] Trust score trend
- [ ] Latency metrics

---

## 7. Documentation

- [ ] Agent documented in registry
- [ ] Runbook created
- [ ] Escalation path defined
- [ ] Training materials updated

---

## 8. Approval

| Role | Name | Approved | Date |
|------|------|----------|------|
| Agent Owner | | [ ] | |
| Security Lead | | [ ] | |
| Engineering Lead | | [ ] | |

---

## 9. Post-Launch Review

*To be completed 2 weeks after launch*

| Metric | Expected | Actual | Notes |
|--------|----------|--------|-------|
| ALLOW rate | | | |
| QUARANTINE rate | | | |
| DENY rate | | | |
| False positives | | | |
| Incidents | | | |

---

*Template Version: 1.0*

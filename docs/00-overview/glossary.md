# Glossary

Technical terms and concepts used throughout SCBE-AETHERMOORE documentation.

---

## A

### Agent
An AI system or autonomous software component that performs actions on behalf of users or other systems.

### ALLOW
Decision outcome permitting an AI agent request to proceed. Issued when trust score is 0.70 or higher.

### Audit Trail
Immutable record of all decisions, including timestamps, trust scores, and consensus results.

---

## B

### BFT (Byzantine Fault Tolerance)
Protocol property that maintains correctness even when some validators are compromised or malicious.

### Behavioral Envelope
The bounded set of expected behaviors for an AI agent, defined by policy and historical patterns.

---

## C

### Consensus
Agreement among multiple validators on a decision. SCBE uses multi-signature consensus requiring 2f+1 validators.

### Cryptographic Envelope
Security wrapper around data using post-quantum cryptography algorithms.

---

## D

### DENY
Decision outcome blocking an AI agent request. Issued when trust score is below 0.30.

### Decision Engine
Core component that evaluates requests and produces ALLOW/QUARANTINE/DENY outcomes.

---

## F

### Fail-to-Noise
Security property where attack attempts receive random noise responses rather than error messages.

### Feistel Network
Cryptographic structure used in SCBE's encryption, providing reversible transformations.

---

## H

### Hyperbolic Geometry
Non-Euclidean geometry used in SCBE's trust scoring, where parallel lines diverge and distances grow exponentially.

### Hyperbolic Distance
Distance metric in Poincare ball model: d(u,v) = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))

---

## L

### Layer (14-Layer Pipeline)
One of 14 sequential processing stages in SCBE evaluation:
1. Input Validation
2. Authentication
3. Rate Limiting
4. Context Extraction
5. Historical Analysis
6. Behavioral Scoring
7. Risk Assessment
8. Policy Evaluation
9. Consensus Request
10. Validator Voting
11. Decision Aggregation
12. Audit Logging
13. Response Formation
14. Output Delivery

---

## M

### ML-DSA-65
NIST-approved post-quantum digital signature algorithm (formerly Dilithium).

### ML-KEM-768
NIST-approved post-quantum key encapsulation mechanism (formerly Kyber).

### Multi-Signature
Cryptographic scheme requiring multiple parties to approve a decision.

---

## P

### Pipeline
Sequential processing flow through SCBE's 14 layers.

### Poincare Ball
Mathematical model for hyperbolic space, used in trust calculations.

### Policy
Rules defining acceptable behaviors, thresholds, and decision criteria.

### Post-Quantum Cryptography (PQC)
Cryptographic algorithms resistant to attacks by quantum computers.

---

## Q

### QUARANTINE
Decision outcome holding an AI agent request for human review. Issued when trust score is between 0.30 and 0.70.

### Quantum-Resistant
Property of being secure against both classical and quantum computer attacks.

---

## R

### Risk Level
Categorization of request danger: LOW (0.70-1.00), MEDIUM (0.30-0.70), HIGH (0.00-0.30).

### RWP (Read-Write-Permit)
Policy framework defining what AI agents can read, write, and execute.

---

## S

### SCBE
Secure Cryptographic Behavioral Envelope - the core governance framework.

### Sentinel
Monitoring component that watches for anomalies and triggers alerts.

### Steward
Administrative component managing policy updates and system configuration.

---

## T

### Trust Score
Numerical value (0.0 to 1.0) quantifying confidence in an AI agent request.

### Trust Engine
Component computing trust scores using hyperbolic geometry and behavioral analysis.

---

## V

### Validator
Node participating in consensus decisions. Minimum 3 validators required (2f+1 where f=1).

---

## Z

### Zero Trust
Security model assuming no implicit trust; every request must be verified.

### ZBase32
Encoding scheme used for human-readable identifiers in SCBE.

---

## Mathematical Notation

| Symbol | Meaning |
|--------|---------|
| d(u,v) | Hyperbolic distance between points u and v |
| ||x|| | Euclidean norm of vector x |
| f | Maximum number of faulty validators |
| 2f+1 | Minimum validators for BFT consensus |
| arcosh | Inverse hyperbolic cosine |

---

## See Also

- [Architecture Overview](../01-architecture/README.md)
- [Technical Reference](../02-technical/README.md)
- [Security Model](../04-security/README.md)

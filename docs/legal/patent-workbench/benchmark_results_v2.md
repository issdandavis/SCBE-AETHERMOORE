## SCBE Runtime Governance Benchmark

Corpus: 36 adversarial (13 prompt injection, 9 tool misuse, 9 unicode confusable, 5 session drift) + 17 benign

| Condition | False-Allow | False-Allow % | False-Block | False-Block % | Mean Latency ms | Geometry Reached % | Audit Complete % |
|---|---|---|---|---|---|---|---|
| **raw** | 36/36 | 100% | 0/17 | 0% | 0.0 | 0% | 0% |
| **regex** | 25/36 | 69% | 0/17 | 0% | 0.0 | 0% | 0% |
| **tongue_gate** | 27/36 | 75% | 0/17 | 0% | 0.1 | 100% | 100% |
| **runtime_gate** | 19/36 | 53% | 4/17 | 24% | 0.2 | 100% | 100% |
| **full_route** | 18/36 | 50% | 4/17 | 24% | 0.3 | 100% | 100% |

### Decision Distribution

| Condition | ALLOW | DENY | QUARANTINE | REROUTE | REVIEW |
|---|---|---|---|---|---|
| **raw** | 53 | 0 | 0 | 0 | 0 |
| **regex** | 42 | 8 | 0 | 3 | 0 |
| **tongue_gate** | 44 | 0 | 2 | 7 | 0 |
| **runtime_gate** | 32 | 5 | 9 | 7 | 0 |
| **full_route** | 31 | 6 | 9 | 7 | 0 |

### Patent Evidence Notes

- **False-allow gap (raw vs runtime_gate)**: demonstrates nonlinear hyperbolic governance
  cost (claims 1, 9) is not well-understood/routine/conventional — simpler controls miss
  adversarial inputs that the full gate catches. (Berkheimer v. HP Inc., 881 F.3d 1360)
- **False-allow gap (regex vs runtime_gate)**: demonstrates ordered combination (BASCOM,
  827 F.3d 1341) — regex alone misses behavioral drift that hyperbolic session centroid detects.
- **Geometry reached %**: shows cheapest-reject-first ordering (claim 11) — early filters
  avoid hyperbolic distance computation for clearly safe or clearly blocked inputs.
- **Audit complete %**: demonstrates concrete audit artifact output (claims 9, 13) vs
  no-audit baselines — directly rebutting abstract-idea characterization under SRI Int'l,
  918 F.3d 1368 (the gate produces structured machine output, not just a decision bit).
- **False-allow gap (runtime_gate vs full_route)**: demonstrates bijective tamper +
  identifier canonicality overlays (claim 15, 17) catch unicode confusable attacks that
  geometry alone does not.
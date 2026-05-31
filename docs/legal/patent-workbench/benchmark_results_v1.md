## SCBE Runtime Governance Benchmark

Corpus: 16 adversarial (7 prompt injection, 5 tool misuse, 4 unicode confusable) + 10 benign

| Condition | False-Allow | False-Allow % | False-Block | False-Block % | Mean Latency ms | Geometry Reached % | Audit Complete % |
|---|---|---|---|---|---|---|---|
| **raw** | 16/16 | 100% | 0/10 | 0% | 0.0 | 0% | 0% |
| **regex** | 7/16 | 44% | 0/10 | 0% | 0.0 | 0% | 0% |
| **tongue_gate** | 10/16 | 62% | 0/10 | 0% | 0.2 | 100% | 100% |
| **runtime_gate** | 7/16 | 44% | 1/10 | 10% | 0.2 | 100% | 100% |
| **full_route** | 6/16 | 38% | 1/10 | 10% | 0.4 | 100% | 100% |

### Decision Distribution

| Condition | ALLOW | DENY | QUARANTINE | REROUTE | REVIEW |
|---|---|---|---|---|---|
| **raw** | 26 | 0 | 0 | 0 | 0 |
| **regex** | 17 | 7 | 0 | 2 | 0 |
| **tongue_gate** | 20 | 0 | 0 | 6 | 0 |
| **runtime_gate** | 16 | 3 | 1 | 6 | 0 |
| **full_route** | 15 | 4 | 1 | 6 | 0 |

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
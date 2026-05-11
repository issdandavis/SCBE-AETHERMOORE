# DARPA-Aligned Agentic System Requirements — 2026-05-10

Purpose: convert DARPA public-program language into concrete requirements for
the SCBE bus and swarm router.

This is not a claim that SCBE is DARPA-ready today. It is the quality bar the
bus should move toward before being used in a proposal or demo.

## Source-Derived Requirements

| DARPA signal | Practical requirement for SCBE bus |
|---|---|
| Assured Autonomy frames the hard problem as safe/correct autonomy in uncertain, dynamic environments where learned behavior evolves over time. | Every bus run must produce operation-time evidence, not only a design-time prompt. |
| Assured Autonomy defines continual assurance as design-time assurance plus operation-time monitoring, updating, and evaluation. | The router must emit `routing.json`, `results.json`, correction guides, rerun policy, and benchmark reports. |
| ANSR defines trustworthy systems as robust to domain-informed/adversarial perturbations, supported by heterogeneous evidence, and predictable against specs/models of fitness. | The bus needs path trust policy, quality flags, applicability scores, guard lanes, and explicit acceptance rules. |
| AIxCC prioritized patching while maintaining functionality, not merely finding bugs. | A generated patch is not promoted until it is repo-applicable and later passes `safe_apply` plus smoke tests. |
| I2O emphasizes formal methods, third-wave AI, repair/restore, and correctness guarantees for security-relevant software systems. | SCBE should treat models as candidate generators and the bus as the assurance layer around them. |

## Current SCBE Bus Mapping

The current swarm router now emits:

- `schema=scbe_swarm_routing_v1`
- `policy=tiered_free_first_guarded_builder_rotation`
- lane tiers: `helper`, `builder`, `guard`, `packager`, `escalation`
- path trust policy: allow / grey-requires-approval / black-blocked
- quality flags for fake paths, fake wrapper symbols, missing symbols, unsafe
  commands, and unreviewed external resources
- `applicability_score` per lane
- `correction_guide` for repeated failure modes
- `assurance_packet.schema=scbe_darpa_style_assurance_packet_v1`

## DARPA-Grade Gap List

1. Safe-apply tier.
   The benchmark must graduate from contract-level scoring to extracting a
   promotable diff and applying it in a sandbox.

2. Functionality-preserving score.
   The bus should report whether tests still pass after a candidate patch, not
   only whether the response looks applicable.

3. Challenge corpus.
   Create a small local benchmark with known bad proposals:
   fake file, fake symbol, unsafe command, greylisted package mutation, and a
   valid tiny patch. This gives the gate measurable precision/recall.

4. Rerun memory.
   Completed bad paths should become correction rules in a local ledger so the
   next cycle avoids repeating the same failure.

5. Proposal/demo framing.
   The honest claim is: "SCBE is an assurance bus for multi-model coding
   agents. It produces evidence packets and blocks non-applicable patches before
   mutation."

## Official Sources

- DARPA Assured Autonomy:
  https://www.darpa.mil/research/programs/assured-autonomy
- DARPA ANSR:
  https://www.darpa.mil/research/programs/assured-neuro-symbolic-learning-and-reasoning
- DARPA AIxCC scoring announcement:
  https://www.darpa.mil/news/2025/ai-cyber-challenge-scoring
- DARPA Information Innovation Office:
  https://www.darpa.mil/about/offices/i2o

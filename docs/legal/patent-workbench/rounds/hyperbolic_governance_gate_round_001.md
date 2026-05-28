# Patent Claim Round 001: Hyperbolic Governance Gate

Status: internal drafting round, not legal advice.
Skill tested: `thats-a-good-skill`.

## Renewal Menu

```text
need: test renewal/nested-skill structure on a real patent task
task: review hyperbolic governance gate as a primary non-provisional claim family
current_moment: provisional 63/961,403 filed; non-provisional workbench active
source_material: patent field, game roles, support scan, patent description, runtime code
desired_output: saved claim-round artifact with pitch, hit, call, crowd signals, cleanup
```

```text
% token allocation
sense: 15
plan: 15
execute: 40
validate: 15
cleanup: 5
final: 10
```

Escalation: local only. No bigger model, no subagent, no web search. The
official rule sources are already captured; this round only needed local support
evidence.

## Nested Skill Stack

```text
primary: pro-se-patent-workbench
support: thats-a-good-skill
checker: claim_support_scan, patent_game_roles
cleanup: manifest update, candidate follow-up list
```

## Ball

Hyperbolic governance gate.

## Pitch: Invention Advocate

A runtime gate receives an action and context, encodes or projects that input
into a geometric state, measures distance or drift in a hyperbolic/Poincare
domain from a trusted or session reference state, computes governance cost or
risk, and selects an execution decision such as `ALLOW`, `QUARANTINE`, or
`DENY`.

Inputs:

- candidate computational action;
- runtime context;
- session or trusted reference state;
- semantic, integrity, or coherence signals.

Changed state:

- execution decision;
- audit trail or receipt;
- session/reference gate state.

Support evidence:

- [docs/PATENT_DETAILED_DESCRIPTION.md](C:/Users/issda/SCBE-AETHERMOORE/docs/PATENT_DETAILED_DESCRIPTION.md:24) describes Poincare embedding, hyperbolic distance, harmonic scaling, and `ALLOW` / `QUARANTINE` / `DENY` regions.
- [docs/PATENT_DETAILED_DESCRIPTION.md](C:/Users/issda/SCBE-AETHERMOORE/docs/PATENT_DETAILED_DESCRIPTION.md:100) defines the Poincare ball and related hyperbolic terms.
- [src/governance/runtime_gate.py](C:/Users/issda/SCBE-AETHERMOORE/src/governance/runtime_gate.py:1) describes the runtime gate between intent and execution.
- [packages/kernel/src/hyperbolic.ts](C:/Users/issda/SCBE-AETHERMOORE/packages/kernel/src/hyperbolic.ts:74) implements hyperbolic distance in the Poincare ball model.
- [docs/legal/patent-workbench/claim_support_scan.md](C:/Users/issda/SCBE-AETHERMOORE/docs/legal/patent-workbench/claim_support_scan.md:5) reports hyperbolic-governance support across the patent description and implementation files.

## Hit: Client Advocate

Claim a computer-implemented runtime authorization method using a bounded
nonlinear geometric domain and distance/drift-based governance cost to control
execution of computational actions.

Safe broadening:

- `Poincare ball` -> `bounded nonlinear geometric domain` in the independent claim;
- `Sacred Tongues` -> `semantic weighting axes` or `context channels`;
- exact thresholds -> configured thresholds;
- CLI/API/agent bus -> computational action execution surface.

Keep Poincare ball, exact formulas, and six-dimensional embodiments in dependent
claims so the independent claim is not too easy to design around.

## Umpire Call

Call: `PRIMARY`.

Reason: the feature is title-level, heavily supported in the patent description
and implementation, and can be framed as a practical runtime enforcement method
rather than only a mathematical idea.

Risks:

- `101`: if drafted as only measuring distance, it may look abstract. Mitigation:
  recite execution control, quarantine/deny/allow states, audit receipt, and
  state update.
- `102/103`: embeddings, anomaly detection, access control, and audit logs exist
  separately. Mitigation: claim the ordered combination and enforcement path.
- `112`: broad terms need definitions and examples. Mitigation: tie terms to
  state vectors, formulas, Poincare embodiment, and runtime gate examples.

## Crowd Signals

These are advisory-only small-model style reactions, not authority.

| Crowd voice | Risk tag | Opinion |
|---|---|---|
| naive reader | confusing | "Hyperbolic governance gate" needs a plain definition: runtime gate measuring drift and controlling execution. |
| design-around reader | design_around | If the claim requires Poincare ball only, another nonlinear geometry could avoid it. |
| legal skeptic | too_broad | Do not claim all AI safety or all semantic distance gates. Require execution control and state update. |
| engineer | okay | Buildable if the spec includes vector encoding, distance formula, thresholds, and decision states. |

## Announcer Summary

The first ball was the core hyperbolic governance gate. The pitch defined it as a
runtime gate that turns action/context into geometric state, measures drift,
computes cost, and controls execution. The hit broadened it to bounded nonlinear
geometry while keeping Poincare and exact formulas as embodiments. The umpire
called it `PRIMARY`, with 101 and 112 cautions that the claim must stay tied to
runtime enforcement and concrete support.

## Next Action

Draft independent method claim language for the hyperbolic governance gate, then
map every element to provisional/spec/code support.

## Cleanup Byproducts

- Review [docs/PATENT_DETAILED_DESCRIPTION.md](C:/Users/issda/SCBE-AETHERMOORE/docs/PATENT_DETAILED_DESCRIPTION.md:24) for absolute phrases like computationally infeasible or indistinguishable before claim-facing use.
- Extend [claim_support_scan.md](C:/Users/issda/SCBE-AETHERMOORE/docs/legal/patent-workbench/claim_support_scan.md:5) into a full element-by-element claim chart.
- Later: wire the crowd role to real configured small models under cost thresholds.

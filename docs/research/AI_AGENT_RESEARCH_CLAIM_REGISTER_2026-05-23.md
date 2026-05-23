# AI Agent Research Claim Register

Status: evidence gate, not product copy.
Last researched: 2026-05-23.

This register separates usable research from claims that sound plausible but should not enter public SCBE/AetherMoore docs without stronger evidence. It supports the Aether Coding Score, agent-bus safety work, and the experimental NSM geometry lane.

Source of truth: `config/eval/aether_research_claim_registry.v1.json`.

## Decision Rule

| Status | Meaning | Allowed use |
| --- | --- | --- |
| `verified` | Supported by a primary source, official source, or paper page with enough detail to cite. | May be cited with source and scoped language. |
| `watch` | Plausible and useful, but supported only by a preprint, vendor blog, or single-source report. | May guide experiments; do not state as settled fact. |
| `reject_for_public_claims` | Unsupported or no source found in this pass. | Do not use as external authority. |

## Verified Lanes

| Claim | Status | What it means for SCBE |
| --- | --- | --- |
| SWE-Bench Pro has 1,865 long-horizon problems across 41 repositories, including commercial/proprietary sets. | `verified` | Keep it in Aether Coding Score real-repo-repair lane; no points until a run packet exists. |
| Terminal-Bench 2.0 has 89 hard terminal-environment tasks with tests and harness. | `verified` | Keep it in terminal-execution lane; build a small reproducible subset first. |
| Latent Fusion Jailbreak blends harmful and benign hidden states to mask malicious intent. | `verified` | Add semantic-blending attacks to the security backlog; no current coverage claim until tests exist. |
| Curvature-aware hyperbolic learning includes Riemannian AdamW and learnable-curvature stability concerns. | `verified` | Useful for experimental NSM geometry only; not canonical SCBE math. |
| Poincare and Lorentz hyperbolic models have different numerical stability and optimization tradeoffs. | `verified` | Add Lorentz parity only as a future comparison lane. |
| EU General-Purpose AI Code of Practice final version was received by the European Commission on 2025-07-10. | `verified` | Use for compliance-context mapping; do not imply certification. |
| NVIDIA OpenShell uses out-of-process policy enforcement, sandboxing, policy engine, privacy routing, deny-by-default posture, and audit trail. | `verified` | This is a concrete external pattern to benchmark against: policy outside the model, action gate before execution, audit trail. |

## Watch Lanes

| Claim | Status | Fence |
| --- | --- | --- |
| Aethelgard dynamic capability governance. | `watch` | Good design lead for capability-scoped agent bus work, but not an established standard. |
| April 2026 frontier model escape and version-control concealment. | `watch` | Treat as a preprint claim unless independent primary disclosure is found. Do not use as a confirmed incident in product docs. |

## Rejected For Public Claims

| Claim | Status | Replacement |
| --- | --- | --- |
| "First AI Programmer Index" is an established industry standard. | `reject_for_public_claims` | Say Aether Coding Score is our proposed composite scorecard. |
| "Gated Kertos" is the gold standard for AI governance. | `reject_for_public_claims` | Say gated governance workflow, ISO/IEC 42001 context, and EU AI Act/GPAI Code mapping. |

## Product Implications

1. The next scorecard work should be execution, not more prose: a small Terminal-Bench adapter and a SWE-Bench Pro/Verified subset runner with evidence packets.
2. Agent-bus safety should be compared against OpenShell-style controls: out-of-process policy, deny-by-default tool access, action-level audit, and privacy/cost routing outside the model.
3. NSM primes stay experimental. Learnable curvature, Riemannian AdamW, and Lorentz-model parity are research backlog items, not production claims.
4. Security backlog should add representation-blending attacks. The repo can say this is relevant; it cannot say it is already covered until regression tests exist.

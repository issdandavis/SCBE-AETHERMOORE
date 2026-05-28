# Layer Connection and Prior-Art Review -- 2026-05-28

Purpose: internal filing-readiness review for SCBE-2026-0001. This is not an
IDS, not legal advice, and not an upload document. It checks whether the
fourteen runtime layers are explained as a connected machine and whether the
prior-art distinction is framed conservatively.

## Bottom Line

The filing-ready story is the connected runtime gate:

1. represent a proposed action as structured machine state;
2. transform that state into a bounded geometric domain;
3. measure drift against a session reference state;
4. add temporal, spectral, spin, semantic, tamper, and policy signals;
5. convert measured drift to nonlinear governance cost;
6. route execution to allow, review, quarantine, reroute, or deny;
7. emit audit/receipt artifacts and optional fail-to-noise output.

That story is concrete enough for a software patent packet because it is tied to
processor-executed transformations, persisted state, execution routing, and
audit artifacts. It should not be presented as proving "safe AI" or as a general
mathematical discovery.

## Layer Chain

| Layer | Function in the machine | Feeds | Claim support | Prior-art distinction |
|---:|---|---|---|---|
| 1 | Converts request context into complex-valued state with amplitude and phase | L2 | Claims 1, 9 as context representation support | Different from RBAC/ABAC because it starts from measured request state, not static attributes alone |
| 2 | Realifies complex state into real vector form without losing phase information | L3 | Claims 1, 9 implementation detail | Standard math operation; useful as enablement, not the novelty by itself |
| 3 | Applies SPD/golden-ratio weighting to emphasize semantic/operational axes | L4, L9, Claim 4 | Claims 4, 26-28 | Differs from flat embeddings/wordlists by weighting semantic axes and preserving axis identity |
| 4 | Projects weighted vector into an open Poincare ball using tanh projection and epsilon clamp | L5 | Claims 1, 2, 9 | Hyperbolic embeddings are known; distinction is use as an execution-control gate |
| 5 | Computes Poincare hyperbolic distance from centroid/reference state | L6, L7, L8, L11, L12 | Claims 1, 2, 9 | Prior art often uses distance for clustering/detection; this uses distance to route execution |
| 6 | Applies bounded breathing diffeomorphism to tighten/relax geometry | L8 and risk modulation | Spec support, optional embodiment | Dynamic boundary adjustment is an embodiment; do not make it required for core claims |
| 7 | Applies Mobius/phase isometry for session/key rotation while preserving distances | L8 | Spec support, Claim 27 support by phase framing | Uses known hyperbolic isometry math in a runtime authorization context |
| 8 | Assigns the action to nearest operational realm/center | L9, L12 | Claims 1, 9 by reference-region/realm support | More specific than generic anomaly detection because realm distance feeds execution routing |
| 9 | Computes spectral coherence over trajectory/signal history | L10, L13 | Claim 1 auxiliary signal | Known signal processing; patent value is composition into governance decision |
| 10 | Computes spin/phase coherence across concurrent components | L11, L13 | Claim 1 auxiliary signal, Claim 27 | Known circular statistics; supports multi-signal governance, not standalone novelty |
| 11 | Aggregates instantaneous, historical, and governance-weighted temporal distance | L12, L13 | Claims 1, 5, 8 | Strong connection to persisted trajectory state and drift-over-time enforcement |
| 12 | Converts measured drift to harmonic/nonlinear governance cost | L13 | Claims 1, 3, 9 | Core distinction: cost increases with measured geometric drift and controls execution |
| 13 | Emits execution decision and routes action | L14, audit/receipt paths | Claims 1, 9-14, 21-24 | Practical application: allow/review/quarantine/reroute/deny changes machine behavior |
| 14 | Provides parallel telemetry/audio/spectral channel | audit/human monitoring | Spec support, auxiliary signal support | Optional telemetry embodiment; not necessary to carry the core claims |

## Cross-Cutting Components

| Component | Connected role | Claim support | Review note |
|---|---|---|---|
| Session centroid and durable RuntimeGate state | Makes the gate trajectory-aware instead of pointwise-only | Claims 1, 5, 8, 9 | Strong filing support; persisted centroid/count/cost/query/trust/immune are concrete machine state |
| Cheapest-reject-first stack | Filters cheap deterministic attacks before expensive model/crypto calls | Claim 11 | Strong operational distinction and useful evidence target |
| Bijective tamper detection | Compares encode/decode and canonical AST fingerprints before execution | Claims 15-20 | Strong computer-security mechanism; avoid calling it semantic equivalence proof |
| Identifier canonicality | Detects confusables, mixed scripts, invisible/bidi controls | Claims 15, 17 | Strong as an auxiliary governance signal |
| Sacred Tongues/tokenizer | Provides disjoint serialized axis vocabularies and entropy-domain routing | Claims 4, 26-28 | Claim 26 correctly relies on serialized axis-designated tokens, not raw unprefixed token strings |
| Sacred Eggs/deferred authorization | Requires N predicates before unlock; failure returns noise-like output | Claims 21-22 | Keep as embodiment; confirm priority support before making it central in argument |
| PQC receipt | Optional signed/encapsulated decision artifact | Claim 12 | Good embodiment, but should not be the only support for the core invention |
| Fleet/juggling scheduler | Optional multi-agent task coordination embodiment | Claim 25 | Useful breadth claim; not the filing's core patent value |

## Prior-Art Framing

Known or likely-close fields:

- RBAC, ABAC, capability systems: static policy/credential evaluation.
- ML anomaly detection: statistical detection based on learned baselines.
- Hyperbolic embeddings: representation or clustering in non-Euclidean space.
- Control-flow integrity: execution-graph monitoring/enforcement.
- HKDF, BIP-32/39/44: deterministic key derivation and mnemonic encoding.
- X.509 and W3C Verifiable Credentials: signed static identity assertions.
- ML-KEM and ML-DSA: standardized post-quantum primitives.
- Unicode/confusable detection: known source-code hardening technique.

Conservative distinction to use:

> The claimed system is not merely a hyperbolic embedding, tokenizer, KDF, or
> anomaly detector. It combines bounded geometric request state, persisted
> trajectory reference state, nonlinear drift-to-cost computation, auxiliary
> tamper/semantic/coherence signals, and an execution-routing gate that changes
> whether a proposed computational action runs.

Do not say:

- no prior art exists;
- no one has ever used hyperbolic space in security;
- the math proves unhackability;
- post-quantum primitives alone make the system novel;
- all 14 layers are required by every claim.

## Current Filing Judgment

The layer explanation is connected enough for filing after trimming legacy
appendices from the upload DOCX. The claims with the cleanest standing remain
Claims 1-11, 15-20, 24, 26, and 27. Claims 12, 21-23, 25, and 28 are useful
embodiments but should be argued carefully if challenged.

The best next evidence after filing is a benchmark table showing how attack
outcomes change across: raw model, regex only, KO/tongue gate, RuntimeGate
overlays, and full route.

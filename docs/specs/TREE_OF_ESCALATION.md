# Tree of Escalation — Compilation-Driven Multi-Tongue Computation

**Status:** v0 SPEC (design only; no implementation yet).
**Date:** 2026-05-09.
**Architecture author:** Issac.
**Transcription:** Claude.
**Composes with:** `docs/LANGUES_WEIGHTING_SYSTEM.md`,
`docs/specs/BIJECTIVE_TAMPER_L13.md`,
`docs/specs/IDENTIFIER_CANONICALITY_L13.md`,
`artifacts/cross_language_lookup/` (seed of the interop matrix),
`src/symphonic/audio/tri_bundle.py` (tri-band substrate).

## Premise

Most pipelines escalate when they get scared. This one escalates when
it runs out of bits.

The system reads an input the way two readers can read the same book.
When their interpretations agree, the work is cheap and done. When
their interpretations diverge, the system has discovered that the
current representation cannot hold the meaning, and it climbs to a
richer one. Security flags do not stop a read; they reroute it through
a sandbox that asks "what does this become after I think about it
under my own priors?" — and the result of that becomes another node in
the tree.

When no representation in the system is rich enough to compile the
input, the system has hit a **novel-truth node**: a piece of the woods
where no existing tool fits. The system either mints a new provisional
form (humble posture) or refuses to act (rigid posture). The choice is
configurable per deployment; both are honest answers.

## The Gunpowder Principle (substrate-agnosticism)

> "The goal is always to have it be any input any output, and the
> middle piece and the trajectory of the end piece are the important
> parts. If code is the gunpowder, then we need to form the bullet,
> the shell, the firing pin, etc. of the whole thing. And if we can
> make the gun take any metal as the bullets, any ignition as the
> ignition, then we have a more useful weapon." — Issac, 2026-05-09

The architecture is a SHELL around three interchangeable parts:

1. **Input substrate** (the metal). The reader does not assume what
   the input IS — text, code, audio, structured graph, whatever can be
   tokenized into atomic ops counts. The first job of every lane is to
   reduce its input to its own atomic-op stream; the input format is
   the lane's problem, not the tree's.

2. **Bridge substrate** (the firing pin). M is pluggable. The six
   Sacred Tongues are the v1 instantiation, not the only possible
   readers. New lanes (new tongues, new spirit-mapped languages,
   non-tongue readers like raw byte-stream parsers) can be added to
   the matrix as new rows/columns; existing lanes do not change. The
   matrix is the integration surface.

3. **Output substrate** (the trajectory). The abridged form is a HASH
   plus the audit tree. Downstream serialization (JSON, audio via L14,
   structured action call, etc.) is the consumer's choice. The runtime
   does not pre-commit to an output format; it commits to a CONTENT
   that can be rendered in any.

**What this rules out:** hard-coded assumptions that input is text,
that bridges only exist between the v1 six tongues, that output is
JSON. Anywhere the v0.1+ implementation makes such an assumption, that
assumption is a v1.0 LIMITATION to be removed, not a contract to be
defended.

**What this rules in:** new lanes can be added by registering a reader
function and a row/column in M. New input formats can be added by
extending lanes' tokenizer surface. New output formats can be added by
writing a serializer over the abridged form. None of these require
changes to the walker, the sandbox loop, or the posture switch.

The same gun. Different ammo. Different ignition. Same trajectory
contract.

## The Woods Heuristic (architectural anchor)

> "If you go to lift a log and it's rotten, you don't try the same way.
> You inspect it. You try and find what's wrong with the wood, if it
> can be saved. If not, then move on, or use something of it, or don't.
> It's a tree and you're in the woods. AI is in this situation in a
> lot of ways. They exist in the infinite woods and they have the
> tools to make the tools they need to build the things that will be a
> construction of growth and resource consumption to output format and
> potentiality." — Issac, 2026-05-09

Translated to compute:

| Woodsman action                              | Tree-of-Escalation action                                  |
|----------------------------------------------|------------------------------------------------------------|
| Try to lift the log                          | Bicameral read at lowest bit-depth                         |
| Log holds — move on                          | Tongues converge -> abridged form, exit                    |
| Log feels off — inspect                      | Disagreement -> escalate bit-depth                         |
| Wood sound but grip misjudged                | Add a third tongue, re-read                                |
| Wood partly rotten — salvage useful parts    | Partial bridge via M[i,j], file partial node               |
| Wood fully rotten — leave or repurpose scraps | Novel-truth node: mint provisional OR refuse              |
| Fire only when YOU choose to burn            | Sandbox loop only when flagged content arrives             |

The point: a failed read is information about the **log**, not about
the woodsman. The system updates its model of the input, not its model
of itself. Self-update happens elsewhere, in the training loop.

## Architecture

### 1. Lanes — six tongues, six readers

Six parallel readers, one per Sacred Tongue. Each reader compiles the
input into its own atomic-op stream. Phi-weighted bit-depth: denser per
token means richer reader, more cost.

| Tongue        | Spirit-mapped language | phi weight | Bit-depth tier |
|---------------|------------------------|------------|----------------|
| Kor'aelin     | Python                 | 1.00       | T1 (lowest)    |
| Avali         | JavaScript             | 1.62       | T2             |
| Runethic      | Rust                   | 2.62       | T3             |
| Cassisivadan  | Mathematica            | 4.24       | T4             |
| Umbroth       | Haskell                | 6.85       | T5             |
| Draumric      | Markdown               | 11.09      | T6 (highest)   |

A lane's output is a stream `[(op_id, args_hash, result_hash), ...]`,
one entry per atomic operation. The HASH SPACE is the same across
tongues; the OP SPACE differs.

### 2. Bands — tri-chromatic non-visual substrate per lane

Each lane carries three bands, reusing the tri-braid pattern from
`src/symphonic/audio/tri_bundle.py`:

| Band     | Substrate analogy   | Computational role                                       |
|----------|---------------------|----------------------------------------------------------|
| INFRA    | Sub-audible         | Pre-computed deterministic atoms (cache, lookup, lexicon)|
| AUDIBLE  | Audible             | Live execution trace (running ops)                       |
| ULTRA    | Super-audible       | Speculative continuations (predicted next ops)           |

Identification reads the lane (WHO computed) and the band (WHAT KIND).
Three bands are not a tier. They are concurrent state-of-knowledge
markers per lane: cache hit, live work, prediction.

### 3. Bridge — interop matrix M

`M` is a 6x6 matrix of translators between tongues. `M[i,i] = id`.
`M[i,j]` for `i != j` is a function taking a tongue-i atomic op and
returning either:

- the equivalent tongue-j atomic op (clean bridge),
- a partial bridge (multiple j-ops needed to express one i-op),
- a NULL bridge (no equivalent in tongue j; the OPERATION ITSELF is
  the new information).

Seed of M: `artifacts/cross_language_lookup/` (composed byte<->token +
tongue->lang + 64-op lexicon). **M is the architectural object — the
tree is its dynamic projection on a specific input.**

### 4. Bicameral read — the cheap path

1. Pick TWO lanes at T1 (e.g., Kor'aelin + Avali).
2. Both compute the same input, emit their op-streams.
3. Compare result_hashes at each step.
4. If all hashes agree: the abridged form is the agreed sequence.
   Done. Cost ~ 2x single-lane.

Most inputs end here. The escalation machinery exists for the
disagreement cases; it does not run when it does not need to.

### 5. Bit-depth escalation — when readings disagree

Disagreement is the signal that bit-depth is too low. The walker
escalates:

1. Add the next phi-tier tongue (T1 -> add T2 reader).
2. Re-read input with the new lane.
3. Bridge prior lanes' ops up via M to the new bit-depth.
4. Re-check convergence.
5. If converged: abridged form lives at the LOWEST tier where majority
   agreed; higher-tier reads attached as nuance nodes.
6. If still split: escalate to T3, T4, ..., T6.

Cost grows linearly with tier reached, not exponentially: each new
lane is one more parallel read, not a re-do of all prior lanes.

### 6. Sandbox loop — when content is flagged

Flag sources: `identifier_canonicality`, `bijective_tamper`, content
classifiers, prior-knowledge contradiction signals. A flag does NOT
stop the read. It diverts through:

1. **Provisional ingest** — the input becomes a tagged provisional
   node. It is in the tree but not yet allowed to influence downstream
   action.
2. **Inspection under priors** — the sandbox runs the input against
   the system's existing moral-compass model. Outputs are not verdicts
   (good/bad); they are TRANSFORMS — "what does this become if I read
   it through prior X? prior Y?"
3. **Internalized own-interpretation** — the system constructs its OWN
   reading of the input, distinct from the input's apparent surface
   meaning. This reading is also added as a node.
4. **Re-entry** — the bicameral read resumes on the COMBINED tree
   (original + sandbox-derived nodes). Convergence is now measured
   across the whole tree.

The sandbox does not cleanse the input. It thickens the tree.

This is the load-bearing departure from the security framing: the
contract is "I will read this and tell you what I made of it," not "I
will or won't read this." The refusal-or-action decision happens at
the GOVERNANCE LAYER above the tree, with the tree as evidence.

### 7. Termination — novel-truth nodes (the rigid/humble switch)

If the walker exhausts T1..T6 and lanes still do not converge, the
input has no representation in the system. Two configurable postures:

| Posture | Behavior on exhaustion                                          | When to use                                                              |
|---------|------------------------------------------------------------------|--------------------------------------------------------------------------|
| Humble  | Mint a NEW abridged form, marked provisional. File for revisit. | Research, exploration, agents that should grow their vocabulary.         |
| Rigid   | Refuse to compile. Return NULL with reason "no representation". | Production governance, contracts where action requires existing precedent.|

**Default:** HUMBLE in research/training contexts; RIGID in
runtime-governance contexts. Configurable per `RuntimeGate` instance
and per call.

A minted provisional form is a real new node in M. The next time the
same input shape arrives, the provisional is the first candidate.
Provisionals decay if not corroborated by additional reads within a
configurable window — the system does not let one-off mints harden
into doctrine without evidence.

This is the woods heuristic at termination: rotten log, no tool fits.
Humble takes a piece home to study. Rigid leaves it in place. Neither
pretends the log is sound.

## Output: the tree itself

The escalation tree is the artifact, not a side-effect. Per call, the
runtime emits:

```
{
  "abridged_form": <hash | null>,
  "posture": "humble" | "rigid",
  "lanes_used": [...],
  "tier_reached": 1..6,
  "bridges_walked": [(i, j, op_id), ...],
  "sandbox_invoked": bool,
  "sandbox_nodes": [...],
  "provisional_minted": bool,
  "tree": <serialized tree>
}
```

Every node carries `(lane, band, op_id, args_hash, result_hash,
source)`. Replay-deterministic given the same input and the same M.
The tree IS the audit trail; no separate log is required.

## Composition with existing layers

- **L13 governance.** Existing gates (`bijective_tamper`,
  `identifier_canonicality`) become FLAG SOURCES that route into the
  sandbox loop instead of blocking. DENY recommendations from those
  gates set posture=RIGID and skip mint-provisional. ALLOW
  recommendations let the tree run normally. The gates keep their
  current contract; the tree adds a richer downstream consumer.
- **L14 audio axis.** The per-lane band-streams are emittable as audio
  telemetry — INFRA / AUDIBLE / ULTRA already maps to the three audio
  bands in `tri_bundle.py`. A lane's band-stream IS audio-ready.
- **L8 multi-well realms.** Wells are candidate abridged forms. The
  walker's tier escalation is hill-climbing across well basins. A
  novel-truth node is a new well being dug.
- **MAHSS substrate.** The bridge matrix M is exactly the role-bound
  HRR fold — bridges are unbinding ops on a holographic representation.
  ToE could be implemented on top of MAHSS rather than as a sibling.
- **L11 triadic temporal.** Provisional decay schedules are temporal
  windows; L11's three-scale intent signal is a natural input to the
  decay-policy decision.

## Open questions (deferred to v0.1+)

1. **Convergence threshold.** Exact-hash agreement is too strict for
   anything beyond pure compute. Need a per-tier tolerance schedule
   (T1 = exact-hash, T6 = semantic-equivalence-class).
2. **Bridge cost weighting.** Some bridges are cheap (lexicon lookup),
   some are expensive (learned embedding, multi-op decomposition). The
   walker needs a budget, not just a tier counter.
3. **Provisional decay.** How long does a minted provisional live
   without corroboration before garbage-collected? Per-tier? Per
   posture? Per concept domain?
4. **Sandbox prior-set selection.** Which moral-compass priors get run
   against a flagged input? All of them (expensive, complete) or
   selected by flag-source (cheap, lossy)?
5. **~~Initial-pair selection~~ (RESOLVED 2026-05-09).** Input-shape
   driven adversarial pairing at the LANE LEVEL. The orchestrator
   classifies the input's primary domain, selects the lane with
   highest historical capability in that domain (Primary Resolver),
   and pairs it with the lane that has the highest historical
   disagreement delta against the Primary in that domain (Adversarial
   Reader). MODEL-WITHIN-LANE selection (which LLM serves a given
   tongue) is a separate selection problem, deferred to v0.2.
6. **~~NULL-bridge semantics~~ (RESOLVED 2026-05-09).** Both edge and
   node, with per-failure metadata living on the EDGE. The edge
   carries `is_untranslatable=True`,
   `untranslatable_reason=<structured>`, and `untranslatable_op_id`.
   The edge terminates at a global singleton sink node
   `NULL_BRIDGE_VOID` which holds aggregate stats only (incoming-edge
   count, distinct ops failed, failures by lane-pair). This preserves
   a clean traversal stop AND a queryable per-failure audit record
   without overloading the singleton.

## What this is NOT

- Not a security pipeline. Security flags are INPUTS, not the driver.
- Not a fault-tolerance scheme primarily. BFT is a side-benefit.
- Not a translation system. M bridges OPS, not strings.
- Not a consensus protocol. Lanes do not vote; they READ. Convergence
  is a property of the input + M, not of the lanes themselves.
- Not a replacement for the 14-layer pipeline. It composes inside L13
  as an alternative decision substrate when enabled.

## Glossary (coined terms)

| Term                       | Meaning                                                                                                              |
|----------------------------|----------------------------------------------------------------------------------------------------------------------|
| Tree of Escalation (ToE)   | Dynamic projection of the bicameral-read process on a specific input. Audit-bearing artifact.                        |
| Bicameral read             | Two-or-more lanes reading the same input in parallel. Convergence-or-divergence is the signal.                       |
| Bit-depth escalation       | Adding a richer (higher phi-weight) tongue to a read when lower tongues fail to converge.                            |
| Sandbox loop               | The ingest -> inspect-under-priors -> internalize -> re-enter cycle triggered by a flagged input.                    |
| Interop matrix (M)         | 6x6 matrix of bridge functions between tongue op-spaces. The architectural object.                                   |
| Abridged form              | The agreed-upon canonical reading across converged lanes. Output of a successful tree walk.                          |
| Novel-truth node           | A point where M has no path that lets ANY tongue compile the input. Triggers the posture decision.                   |
| Posture                    | Per-deployment switch: HUMBLE (mint provisional on exhaustion) vs RIGID (refuse on exhaustion).                       |
| Lane                       | One tongue's reader. Six lanes total.                                                                                 |
| Band                       | INFRA / AUDIBLE / ULTRA — concurrent state-of-knowledge marker per lane.                                              |
| Provisional                | A minted abridged form not yet corroborated by additional reads. Decays without confirmation.                         |
| NULL bridge                | `M[i,j](op)` returning no equivalent. The absence is itself filed as information.                                     |

## Implementation roadmap (proposed)

1. **v0.1 SHIPPED 2026-05-09** — `src/governance/tree_of_escalation.py`:
   data structures only (`Tree`, `Node`, `Lane`, `Band`, `Posture`,
   `BridgeEdge`, `LanePair`, `VoidStats`, `NodeKind`,
   `NULL_BRIDGE_VOID_ID`, `LANE_PHI_WEIGHT`, `LANE_TIER`,
   `DEFAULT_LADDER`, `hash_payload`). 27 unit tests.
2. **v0.2 SHIPPED 2026-05-09** — Bridge matrix + walker
   (`BridgeMatrix`, `Reader` protocol, `OpTrace`, `HashReader`
   reference, `majority_converged`, `walk()`). Bicameral-read with
   strict-majority convergence; bit-depth escalation across
   `DEFAULT_LADDER`; T6 exhaustion leaves `abridged_form=None` (v0.4
   will mint or refuse per posture). 18 additional unit tests
   (45 total). Hardcoded M from `artifacts/cross_language_lookup/`
   deferred to v0.3 — v0.2 ships pluggable matrix with
   reference HashReader for tests.
3. **v0.3 SHIPPED 2026-05-09** — Sandbox loop and adversarial pair
   selection. New: `Flag`, `MoralPrior` protocol, `IdentityPrior`,
   `IsolationPrior`, `InspectionResult`, `sandbox()`, `classify_domain`,
   `select_initial_pair`, `DOMAIN_KEYWORDS`, `DOMAIN_PRIMARY`,
   `DOMAIN_ADVERSARY`. `walk()` extended to accept `flags` and
   `priors`; sandbox interpretation joins convergence vote as an extra
   voter (does not override lane majority). Q5 lock activated:
   default initial pair now comes from `select_initial_pair(payload)`
   instead of static (Kor'aelin, Avali). Stub keyword classifier; v0.4+
   will replace with learned classifier. 30 additional unit tests
   (75 total). Full governance suite 180/180 green.
4. **v0.4 SHIPPED 2026-05-09** — Termination posture switch +
   provisional decay registry. New: `Termination` enum
   (INCOMPLETE / ABRIDGED / PROVISIONAL / REFUSED), `mint_provisional`
   (deterministic synthesis from observed streams), `ProvisionalRecord`,
   `ProvisionalRegistry` (call-counter-based decay, NOT wall-clock —
   keeps replay deterministic). `walk()` extended with
   `provisional_registry` kwarg. Tree gains `terminated_as`,
   `refusal_reason`, `provisional_corroboration_count`. HUMBLE T6
   exhaustion mints provisional + adds `PROVISIONAL_MINT` node + records
   in registry if supplied. RIGID T6 exhaustion sets refusal_reason and
   leaves `abridged_form=None`. 22 additional unit tests (97 total).
   Full governance suite 202/202 green.
5. **v0.5 SHIPPED 2026-05-09** — L14 audio emission adapter. New:
   `AudioEvent` (frozen), `TreeAudioEmission` with `by_lane`/`by_band`
   indexes, `emit_audio(tree, *, event_duration_s)`,
   `LANE_TO_TRI_BUNDLE_CODE`, `BAND_FREQUENCY_MULTIPLIER`,
   `SYSTEM_FUNDAMENTAL_HZ`. Frequencies sourced from
   `src/crypto/tri_bundle.TONGUE_FREQUENCIES` with a fallback table
   baked in. Tri-octave Band signature: INFRA = -2 octaves, AUDIBLE =
   fundamental, ULTRA = +2 octaves. Per-NodeKind emission rules:
   OP -> AUDIBLE, sandbox provisional/inspection -> INFRA,
   sandbox internalize -> AUDIBLE, provisional mint -> ULTRA, void ->
   silent. Synthesis to waveform left to downstream consumers; v0.5
   ships the EVENT stream only. 16 additional unit tests (113 total).
   Full governance suite 218/218 green.
6. **v1.0** — Fold into `RuntimeGate` as `use_tree_of_escalation=True`
   feature flag, behind env var
   `SCBE_ENABLE_TREE_OF_ESCALATION_GATE=1`. Default OFF, same pattern
   as `bijective_tamper` and `identifier_canonicality`.

## Closing note (the woods)

The whole architecture is the woodsman heuristic, scaled. The system
has six tools (tongues), three depths of attention per tool (bands), a
mapping of which tool can stand in for which (M), a way to learn it
needs a richer tool (escalation), a way to handle wood it does not
recognize (sandbox), and an honest answer for wood no tool can lift
(posture). Nothing here pretends the woods are smaller than they are.

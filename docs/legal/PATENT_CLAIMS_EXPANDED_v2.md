# Patent Claims — Expanded Set v2

## System and Method for Hyperbolic Geometry-Based Authorization with Fail-to-Noise Response, Bijective Tamper Detection, and Post-Quantum Decision Receipts

| Field | Value |
|---|---|
| **Applicant / Inventor** | Issac Davis (pro se) |
| **Entity status** | Micro-entity (to be re-verified at filing) |
| **Priority** | U.S. Provisional Application No. 63/961,403, filed January 15, 2026 |
| **Conversion deadline** | January 15, 2027 |
| **Internal docket** | SCBE-2026-0001 |
| **Status** | Inventor/counsel working draft. NOT legal advice. Internal claim-drafting workshop product. |
| **Supersedes** | This v2 expands and tightens the claim set in `docs/legal/SCBE_NONPROVISIONAL_WORKING_PACKET_2026-05-28.md` (claims 1-20 there are the looser predecessor of claims 1-20 here). |

This document maps every novel component of the implemented SCBE-AETHERMOORE
codebase to a 25-claim set (3 independent, 22 dependent), annotates the
§ 112 written-description support file-by-file, gives a § 101 (Alice) survival
note for each independent claim, and closes with an honest priority-date risk
assessment separating provisional-supported subject matter from likely new
matter / continuation-in-part (CIP) material.

---

## 1. Fee Schedule (Micro-Entity, USPTO schedule rev. May 1, 2026)

Electronic filing in Patent Center, DOCX specification (no paper / non-DOCX
surcharge).

| Item | Micro-entity fee |
|---|---|
| Basic utility filing fee | $70 |
| Utility search fee | $154 |
| Utility examination fee | $176 |
| **Base subtotal (≤ 3 independent, ≤ 20 total claims)** | **$400** |
| Independent claims over 3 (3 used → 0 over) | $0 |
| Claims over 20: 5 extra × $40 | $200 |
| Multiple-dependent-claim fee (none used) | $0 |
| **Total at filing** | **$600** |

Avoidable surcharges deliberately NOT incurred: paper filing ($200), non-DOCX
($86), multiple-dependent claim ($185).

The 5 paid extra claims (21-25) carry the five highest-value additions the
predecessor packet omitted: deferred-authorization (Sacred Eggs) gate,
same-length fail-to-noise composition, Byzantine-fault
swarm trust, Hopfield novel-intent energy, and physics-juggling task
coordination. See § 7 for which of those five carry new-matter risk.

---

## 2. Component → Claim Map

| # | SCBE Component | Primary file(s) | Claim(s) | Posture |
|---|---|---|---|---|
| 1 | Hyperbolic authorization gate (centroid, Poincaré embed, arcosh, π^(φd*) cost, immune/reflex, trajectory drift) | `src/governance/runtime_gate.py`; `packages/kernel/src/hyperbolic.ts`; `packages/kernel/src/languesMetric.ts` | 1, 2, 3, 4, 5, 6 | Priority-supported (core) |
| 2 | Fail-to-noise response | `src/governance/runtime_gate.py` `_fail_to_noise` | 7 | Support depends on provisional text (§ 7) |
| 3 | Bijective tamper detection (round-trip AST invariant, 4 divergence classes, NFC stub) | `src/governance/bijective_tamper.py` | 15, 16, 18, 19, 20 | Support uncertain (§ 7) |
| 4 | Identifier canonicality gate (confusable / mixed-script / invisible) | `src/governance/identifier_canonicality.py` | 17 | Support uncertain (§ 7) |
| 5 | Multi-layer pre-filter stack (cheapest-reject-first) | `src/cli/petri_pattern_filter.py`; `src/cli/slm_router.py`; `src/api/orderedRejection.ts` | 11 | Architecture support good; priority text TBD |
| 6 | Post-quantum decision receipt | `src/governance/offline_mode.ts` (`DecisionCapsule`, `AuditEvent`, `PQCrypto`); `src/crypto/` | 12 | Receipt mechanism implemented (TS); Python-gate wiring partial (§ 7) |
| 7 | Durable state + rollback | `src/governance/runtime_gate.py` `save_state`/`load_state`/`STATE_SCHEMA` | 8 | Priority-supported; one term mismatch (§ 7) |
| 8 | Quarantine non-error containment | `src/agentic/quarantine_lock.py` | 10, 13, 14 | Likely supportable |
| — | Deferred-authorization (Sacred Eggs) | `src/crypto/sacred_eggs.py`; `src/governance/tree_of_escalation.py` | 21, 22 | CIP candidate (§ 7) |
| — | Byzantine swarm trust | `hydra/` (BFT); demo/archive only for τ formula | 23 | CIP candidate (§ 7) |
| — | Hopfield novel-intent energy | L8 multi-well `hamiltonianCFI.ts`; explicit E(c) form in archive only | 24 | CIP candidate (§ 7) |
| — | Physics-juggling task coordination | `src/fleet/juggling-scheduler.ts` | 25 | Strong support |

---

## 3. The Claims

> Drafting convention: claim elements are set on separate indented lines with a
> trailing semicolon; the final element ends with a period; `wherein` clauses
> recite the distinguishing limitation. Antecedent basis is carried explicitly.

### CLAIM FAMILY A — METHOD (Independent Claim 1)

**1.** A computer-implemented method for governing execution of a computational
action, comprising:

&nbsp;&nbsp;&nbsp;&nbsp;receiving, by one or more processors, a request associated with the computational action;

&nbsp;&nbsp;&nbsp;&nbsp;generating a context representation comprising one or more semantic, operational, or temporal features;

&nbsp;&nbsp;&nbsp;&nbsp;transforming the context representation into an embedded point in a bounded hyperbolic space comprising a Poincaré ball model, via a tanh-normalized projection with epsilon clamping that constrains the embedded point to an open unit ball;

&nbsp;&nbsp;&nbsp;&nbsp;maintaining a session centroid as a trusted reference region, updated as a function of a plurality of embedded points corresponding to prior requests within a session;

&nbsp;&nbsp;&nbsp;&nbsp;computing a hyperbolic distance between the embedded point and the session centroid;

&nbsp;&nbsp;&nbsp;&nbsp;computing a governance cost from the hyperbolic distance using a nonlinear cost function that increases as the hyperbolic distance increases;

&nbsp;&nbsp;&nbsp;&nbsp;combining the governance cost with at least one additional governance signal from: semantic weighting, temporal drift, spectral coherence, spin coherence, identifier canonicality, or bijective tamper detection, to produce a composite risk value;

&nbsp;&nbsp;&nbsp;&nbsp;adjusting a severity of the composite risk value as a function of trajectory drift of the embedded points across the plurality of prior requests; and

&nbsp;&nbsp;&nbsp;&nbsp;emitting a governance decision, from: allow, review, quarantine, or deny, that controls whether the computational action is executed;

&nbsp;&nbsp;&nbsp;&nbsp;whereby the governance cost is a nonlinear increasing function of measured drift and is used to control execution of the computational action.

> *§ 101 survival:* Claim 1 is directed to a technological improvement in
> controlling machine execution — it *changes runtime behavior* (allows,
> reviews, quarantines, or denies execution of a computational action), not
> merely computes and displays a risk score. The recited tanh-normalized
> Poincaré projection, session-centroid update, nonlinear cost, and four-way
> execution-control decision are concrete computer operations on concrete data
> structures, taking the claim out of the "abstract idea on a generic computer"
> bucket (*Alice* step 2 / *Enfish*-style improvement-to-computer-functionality).
>
> *§ 112 support:* `transforming ... tanh-normalized projection with epsilon
> clamping` → `packages/kernel/src/hyperbolic.ts` `projectEmbeddingToBall`
> (`u = tanh(α‖x‖)·x/‖x‖`, `r = min(tanh(α n), 1 − eps)`); `session centroid
> ... updated as a function of ... prior requests` → `runtime_gate.py`
> `_update_centroid`; `hyperbolic distance` → `hyperbolic.ts`
> `hyperbolicDistance`; `nonlinear cost function` → `runtime_gate.py`
> `_harmonic_cost`; `trajectory drift` → `_cumulative_cost` accumulation +
> `cumulative_cost_quarantine/_deny` thresholds. **See § 7 risk note B on
> reconciling the disclosed cost-function embodiments.**

**2.** The method of claim 1, wherein the hyperbolic distance is computed as
`d_H = arccosh(1 + 2‖u − v‖² / ((1 − ‖u‖²)(1 − ‖v‖²)))`, where `u` is the
embedded point and `v` is the session centroid.

**3.** The method of claim 1, wherein the nonlinear cost function comprises one
of: (i) a function of the form `H(d, R) = R^(d²)`, where `d` is a distance
measure and `R` is a base greater than one; or (ii) a bounded safety-score
function of the form `H = 1 / (1 + d + 2·pd)`, where `pd` is a phase-deviation
term.

**4.** The method of claim 1, wherein the additional governance signal comprises
a six-axis semantic weighting in which each axis has a predetermined weight equal
to a power of the golden ratio, `φ^k` for `k = 0..5`, with `φ ≈ 1.618`.

**5.** The method of claim 1, wherein maintaining the session centroid comprises
an incremental update of the form
`centroid_new = (n · centroid_old + coord) / (n + 1)`, where `n` is a running
count of prior embedded points and `coord` is the embedded point of the current
request.

**6.** The method of claim 1, further comprising maintaining a hash-indexed
adversarial-memory set and a hash-indexed safe-memory set, and, prior to said
transforming, returning a deny decision for a request whose content hash is a
member of the adversarial-memory set, and returning an allow decision for a
request whose content hash is a member of the safe-memory set, in each case
without computing the hyperbolic distance.

> *§ 112 support, claims 2-6:* arcosh → `hyperbolic.ts` `hyperbolicDistance`
> (lines 84-98). Cost species (i) `R^(d²)` → root `symphonic_cipher/` per
> `CLAUDE.md` "Dual symphonic_cipher" table; species (ii) `1/(1+d+2·pd)` →
> `hyperbolic.ts` `phaseDistanceScore` (line 528) and `src/symphonic_cipher/`
> bounded variant. Golden-ratio weights → `languesMetric.ts` line 87
> (`Math.pow(PHI, i)`) and `runtime_gate.py` line 54
> (`tuple(PHI**k for k in range(6))`). Centroid update → `runtime_gate.py`
> `_update_centroid` (the implemented form `centroid·(n−1)/n + tc/n` is
> algebraically identical to the recited `(n·c_old + coord)/(n+1)`). Immune /
> reflex fast-path → `runtime_gate.py` `_immune` set + `_reflex` dict, evaluated
> before the full pipeline (lines 1219-1330).

**7.** The method of claim 1, further comprising, responsive to a deny decision,
generating a deterministic pseudorandom-looking noise output by computing a seed
as a cryptographic hash of a fixed prefix concatenated with a content hash of
the denied request, iteratively re-hashing the seed until a target length is
reached, and returning the noise output in place of an error response, such that
the noise output is identical for identical denied requests and is reproducible
by an auditor from the content hash.

> *§ 112 support:* `runtime_gate.py` `_fail_to_noise(action_hash, length=32)`
> — `h = sha256("fail-to-noise:" + action_hash)`, then `while len < length:
> block = sha256(block)`. The deterministic-on-input and auditor-reproducible
> properties are literally documented in that function's docstring. Wired on
> every DENY path (lines 1070, 1246, 1528, 1548, 1561, 1578, 1605).

**8.** The method of claim 1, further comprising periodically persisting, to a
durable store, at least the session centroid, a cumulative governance cost, a
query count, a trust history, and the adversarial-memory set of claim 6; and,
after a process restart, restoring the persisted values so that the session
continues from the restored trajectory rather than from a cold start.

> *§ 112 support:* `runtime_gate.py` `save_state` (atomic write,
> `keep_previous` rollback snapshot) + `load_state` + `STATE_SCHEMA =
> "runtime-gate-state/v1"` (lines 2278-2397). Persisted fields: `centroid`,
> `centroid_count`, `cumulative_cost`, `query_count`, `trust_history`,
> `immune`. **See § 7 risk note F: the implementation deliberately does NOT
> persist the reflex (safe-memory) set; claim 8 as drafted omits reflex from
> the persisted list and is therefore consistent — do not add reflex to this
> claim.**

---

### CLAIM FAMILY B — SYSTEM (Independent Claim 9)

**9.** A system for runtime governance of agentic or artificial-intelligence
actions, comprising:

&nbsp;&nbsp;&nbsp;&nbsp;at least one processor; and

&nbsp;&nbsp;&nbsp;&nbsp;a non-transitory memory storing a persistent runtime state and instructions that, when executed, cause the system to:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;classify a proposed action into a context representation;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;map the context representation into a point in a Poincaré ball model of bounded hyperbolic space;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;measure drift as hyperbolic distance between the point and a session centroid, the session centroid being part of the persistent runtime state and comprising at least a centroid vector, a cumulative cost, and a query count;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;calculate a harmonic governance cost from the measured drift using a nonlinear cost function that increases as the drift increases;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;apply a decision gate to the harmonic governance cost and one or more auxiliary signals; and

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;route the proposed action according to allow, review, quarantine, or deny;

&nbsp;&nbsp;&nbsp;&nbsp;wherein the session centroid is updated from prior proposed actions within a session, and the persistent runtime state is restored after a process restart.

> *§ 101 survival:* The system claim recites a machine (processor + memory)
> that enforces execution routing and maintains persistent governed state
> across restarts — a concrete runtime-control architecture, not a disembodied
> algorithm. The "restored after a process restart" limitation ties the claim
> to a physical, stateful machine improvement.
>
> *§ 112 support:* whole-pipeline `runtime_gate.py` `RuntimeGate.evaluate` +
> `save_state`/`load_state`; persistent-state composition (centroid vector,
> cumulative cost, query count) → `STATE_SCHEMA` snapshot (lines 2311-2322).

**10.** The system of claim 9, wherein the quarantine route applies a non-error
containment state that, without crashing or terminating the session, restricts
available tools to an allowed subset, enforces an execution-time deadline,
restricts execution permissions, and limits outbound network or filesystem
effects of the proposed action.

> *§ 112 support:* `src/agentic/quarantine_lock.py` —
> `QuarantineLockPolicy.inspect_only_tools` / `blocked_tool_classes` (tool
> filtering), `*_timeout_seconds` (deadline), `apply_quarantine_lock_to_dcp`
> (drops `ToolScope` to `RESTRICTED`/`DENIED`, clamps `gate.timeout_seconds`),
> and `block_execution`/`isolate` flags that contain rather than terminate. The
> module docstring expressly frames it as "a containment state that prevents
> execution while preserving enough evidence for review," not a token drain.

**11.** The system of claim 9, wherein the auxiliary signals are produced by a
multi-layer pre-filter stack ordered cheapest-reject-first, comprising:

&nbsp;&nbsp;&nbsp;&nbsp;(i) a script-origin gate computing a coverage score as a fraction of UTF-8 bytes of the proposed action falling within the printable ASCII range [0x20, 0x7E] and rejecting when the coverage score is below a threshold;

&nbsp;&nbsp;&nbsp;&nbsp;(ii) an instruction-safety gate matching compiled regular-expression patterns for instruction-override, persona-manipulation, or dangerous-tool-invocation text;

&nbsp;&nbsp;&nbsp;&nbsp;(iii) a semantic pattern filter matching the proposed action against an adversarial-intent corpus; and

&nbsp;&nbsp;&nbsp;&nbsp;(iv) a small-language-model router that rejects an input for which no applicable semantic band is classified;

&nbsp;&nbsp;&nbsp;&nbsp;wherein each gate operates before the hyperbolic-distance computation, and rejection by any gate prevents invocation of subsequent gates.

> *§ 112 support:* (i) `src/cli/petri_pattern_filter.py` `tongue_coverage_score`
> (`ascii_count = sum(1 for b in raw if 0x20 <= b <= 0x7E)`) +
> `is_non_latin_script_input` (`_KO_COVERAGE_THRESHOLD = 0.60`); (ii)
> `petri_pattern_filter.py` `is_high_risk_instruction_input` over
> `_HIGH_RISK_COMPILED`; (iii) Petri 173-seed corpus →
> `petri_pattern_filter.py` (94.8% v8 coverage) + `src/cli/petri_seed_loader.py`;
> (iv) `src/cli/slm_router.py` (three-tier band → op → tongue classification,
> raising `ClassificationFailure`). Cheapest-reject-first ordering with
> per-stage micro-cost budget → `src/api/orderedRejection.ts` (stages S0-S10,
> hyperbolic at S6-S7, PQ crypto last at S10).

**12.** The system of claim 9, wherein, responsive to an allow decision, the
system computes a content-addressed identifier of the proposed action as a
cryptographic hash of a canonical representation, signs the identifier together
with an authorization score and a timestamp using a post-quantum digital
signature algorithm in accordance with FIPS 204 (ML-DSA-65), encapsulates a
session key using a post-quantum key-encapsulation mechanism in accordance with
FIPS 203 (ML-KEM-768), and returns a structured receipt comprising the decision,
the score, signal identifiers, the timestamp, the signature, and a
key-encapsulation ciphertext; and wherein a downstream executor verifies the
signature before executing the allowed action.

> *§ 112 support:* `src/governance/offline_mode.ts` — `DecisionCapsule`
> (`{ state_root, decision, reason_codes, timestamp_monotonic, signature }`),
> `AuditEvent` (`signature: ML-DSA-65(event_hash)`), `DecisionResult.proof:
> DecisionCapsule`, and `PQCrypto.{sign, verify, encapsulate, decapsulate}`
> over `ml_dsa65` / `ml_kem768`. **See § 7 risk note C: the signed-decision-
> capsule mechanism is implemented in TypeScript, but the Python `RuntimeGate`
> does not yet call it (no `_issue_pqc_receipt`); claim 12 is best characterized
> as supported in combination, with integration into the Python gate partial.**

**13.** The system of claim 9, wherein the system emits an audit receipt
comprising at least the decision, the harmonic governance cost, signal
identifiers, and decision-relevant metadata including a session query count and
a cumulative cost.

> *§ 112 support:* `runtime_gate.py` `GateResult` dataclass (decision, cost,
> signals[], action_hash, timestamp, session_query_count, cumulative_cost) +
> per-decision receipt-signal formatters `_tamper_receipt_signal`,
> `_canonicality_receipt_signal`, `_toe_receipt_signal`.

**14.** The system of claim 9, wherein the system is deployed as at least one of:
a REST API endpoint, an agent bus service, a command-line interface, or a
programmatic client library.

> *§ 112 support:* `src/api/`, `packages/agent-bus/`, `packages/cli/bin/scbe.js`,
> and the `scbe-aethermoore/governance` package export per `CLAUDE.md`.

---

### CLAIM FAMILY C — COMPUTER-READABLE MEDIUM (Independent Claim 15)

**15.** A non-transitory computer-readable medium storing instructions that, when
executed, cause one or more processors to:

&nbsp;&nbsp;&nbsp;&nbsp;receive an input comprising source code or an identifier-containing input;

&nbsp;&nbsp;&nbsp;&nbsp;generate a re-encoded form of the input by applying a bijective encode operation followed by a decode operation mapping the input to a token sequence and back to a decoded input;

&nbsp;&nbsp;&nbsp;&nbsp;compute a first canonical abstract syntax tree (AST) representation of the input and a second canonical AST representation of the decoded input, each comprising a content-derived fingerprint;

&nbsp;&nbsp;&nbsp;&nbsp;compute a tamper signal based on at least one of: (i) a divergence between the first and second canonical AST representations; (ii) a failure of the decoded input to parse into a valid AST; (iii) a Unicode canonicality failure; or (iv) a confusable-identifier condition; and

&nbsp;&nbsp;&nbsp;&nbsp;provide the tamper signal to a governance gate that escalates or blocks a proposed computational action when the tamper signal exceeds a threshold;

&nbsp;&nbsp;&nbsp;&nbsp;wherein the tamper signal is distinct from a tokenizer reconstruction-quality measure in that it is derived from a comparison of abstract syntax tree representations and gates execution of a proposed action.

> *§ 101 survival:* The medium claim is directed to a security-detection
> improvement that *gates execution* of a computational action — the final
> "escalates or blocks" limitation supplies the practical application. The
> "distinct from a tokenizer reconstruction-quality measure" wherein clause
> pre-empts the most likely § 103 reference (a BLEU/round-trip-fidelity metric)
> by reciting that the signal is AST-derived and execution-gating.
>
> *§ 112 support:* `src/governance/bijective_tamper.py` `evaluate_code`
> (`src_canonical = ast.parse → ast.dump`; `decoded = decode(encode(src))`;
> compares `src_canonical` vs `decoded_canonical`; `src_fingerprint =
> sha256(src_canonical)`). **See § 7 risk note D for provisional support.**

**16.** The medium of claim 15, wherein each content-derived fingerprint
comprises a SHA-256 digest of the corresponding canonical AST, such that two
inputs that are semantically equal but differ in whitespace or comments produce
identical fingerprints.

**17.** The medium of claim 15, wherein the confusable-identifier condition is
detected by parsing the input into an AST, extracting identifier names, and, for
each identifier, determining whether any non-ASCII codepoint maps to an
ASCII-confusable codepoint, whether the identifier mixes two or more distinct
writing scripts, or whether the identifier contains an invisible or
bidirectional control codepoint; and computing a confusable-identifier score as
a function of the fraction of suspicious identifiers.

**18.** The medium of claim 15, wherein the governance gate denies the proposed
computational action on a syntax-divergence class in which the decoded input
fails to parse, quarantines the proposed computational action on a structural-
divergence class in which the canonical ASTs diverge while both parse, and
allows with annotation on a normalization-divergence class attributable to
Unicode NFC normalization.

**19.** The medium of claim 15, wherein, when a tokenizer artifact is absent, the
instructions substitute a normalization stub that performs the encode operation
by applying Unicode NFC normalization and encoding as UTF-8, the stub preserving
the bijective round-trip property for ASCII inputs.

**20.** The medium of claim 15, wherein the tamper signal, a divergence
classification, and the content-derived fingerprint are recorded in an audit
trail.

> *§ 112 support, claims 16-20:* fingerprint = SHA-256 of canonical AST →
> `bijective_tamper.py` line 222 + module docstring ("Two semantically-equal
> programs hash the same"). Confusable / mixed-script / invisible identifier
> detection → `src/governance/identifier_canonicality.py`
> (`_ASCII_CONFUSABLES`, `_codepoint_script`, `_INVISIBLE_CODEPOINTS`,
> `_BIDI_CODEPOINTS`, `_classify_identifier`, score table `_KIND_SCORE`).
> Divergence-class → action mapping → `bijective_tamper.py`
> `L13_MAPPING_RECOMMENDATION` (`syntax→DENY`, `structural→QUARANTINE`,
> `nfc→ALLOW`) and the four `kind`/`score` tiers in the module docstring.
> Normalization stub → `bijective_tamper.py` `_NfcStubTokenizer`
> (`unicodedata.normalize("NFC", text).encode("utf-8")`). Audit recording →
> `runtime_gate.py` `_tamper_receipt_signal` / `_canonicality_receipt_signal`
> appended to `GateResult.signals`.

---

### CLAIM FAMILY — EXTRA HIGH-VALUE DEPENDENTS (Claims 21-25, $40 each)

**21.** The method of claim 1, further comprising generating a cryptographic
authorization container that is unlocked only when all of N predetermined
predicates are satisfied, the predicates comprising at least: a semantic
predicate; a geometric predicate measuring distance from a known safe region; an
execution-path predicate verifying that the container was reached via an
authorized call chain; a quorum predicate requiring a threshold number of
approving agents; and a cryptographic predicate verifying a post-quantum
signature; wherein failure of any predicate returns a noise or
pseudorandom-looking output rather than a structured predicate-failure response.

**22.** The method of claim 21, wherein the noise output is generated by the
deterministic re-hashing of claim 7, such that a repeated failure path for the
same denied request produces an audit-reproducible output of a predetermined
length while avoiding disclosure of which predicate failed.

> *§ 112 support, claims 21-22:* deferred-unlock cryptographic container with
> ring-gated access and fail-to-noise-on-failure → `src/crypto/sacred_eggs.py`
> (yolk/shell/albumen, `EggRing` CORE/INNER/OUTER/CA, "Fail-to-Noise: On auth
> failure, regenerate shell"); tiered-unlock / provisional-mint substrate →
> `src/governance/tree_of_escalation.py`; deterministic noise → `_fail_to_noise`.
> **See § 7 risk note E: implemented model is a 3-ring + triadic-binding
> container, NOT the specific five-predicate (semantic / geometric / path /
> quorum / crypto) conjunction recited. Claims 21-22 are CIP candidates; counsel
> should consider reformulating to "N predetermined predicates including at
> least a semantic, a geometric, and a cryptographic predicate" to track the
> code more closely.**

**23.** The system of claim 9, wherein the system maintains a swarm trust score
for each participating governance agent, updates the trust score as
`τ_new = α·τ_old + (1 − α)·v`, where `v` is a validity factor for a most-recent
contribution and `α` is a smoothing constant, and automatically self-excludes
from the governance decision any agent whose trust score falls below a
participation threshold, thereby producing a Byzantine-fault-tolerant swarm
consensus without a central coordinator.

> *§ 112 support:* Byzantine-fault-tolerant multi-agent consensus → `hydra/`
> (Spine / Heads / Ledger / BFT per `CLAUDE.md`); a six-reviewer council
> consensus with fail-count thresholds → `runtime_gate.py` `_council_review`
> (0 fails → ALLOW, 1 → QUARANTINE, ≥2 → DENY). **See § 7 risk note E: the
> specific exponential-moving-average τ-update formula currently appears only in
> `demo/`, `archive/`, and `external_repos/` paths, not in production
> governance. CIP candidate.**

**24.** The method of claim 1, further comprising applying a Hopfield energy
function `E(c) = −½·(c')ᵀ·W·c' + θᵀ·c'` to the context representation `c`,
wherein `W` encodes patterns of known legitimate operations learned offline;
classifying the action as novel-intent when `E(c)` is above a threshold relative
to trained patterns; and incorporating the novel-intent indicator into the
composite risk value.

> *§ 112 support:* multi-well / Hamiltonian energy landscape over the context
> state (L8) → `packages/kernel/src/hyperbolic.ts` `multiWellPotential` /
> `multiWellGradient` and `hamiltonianCFI.ts` per `CLAUDE.md`; null-space /
> novel-intent anomaly scoring already in production → `runtime_gate.py`
> `_null_space_anomaly`. **See § 7 risk note E: the explicit Hopfield quadratic
> energy form `−½c'ᵀWc' + θᵀc'` currently appears only in archive/external
> paths. CIP candidate; the production analog is the multi-well potential, which
> counsel may prefer to claim instead.**

**25.** The system of claim 9, wherein the system coordinates task execution
across a plurality of agent slots using a physics-based juggling model in which
tasks are modeled as balls having inertia proportional to a task priority, agent
slots are modeled as hands having readiness states, handoffs are modeled as
throws having predicted catch windows, and a governance cost of a task increases
when a trajectory of the task deviates from a predicted flight arc, such that
higher-risk tasks are assigned higher arcs and fewer handoffs.

> *§ 112 support:* `src/fleet/juggling-scheduler.ts` — `FlightState`
> (HELD→THROWN→CAUGHT→VALIDATING→DONE), `inertiaPenalty`/`inertia`, siteswap-like
> arc descriptors with "predicted catch windows," and the seven juggling rules
> (rule 3 "high-inertia tasks have fewer handoffs"; rule 4 "higher arcs for
> risky tasks"). Strong, verbatim written-description support. Lowest-risk of
> the five extra claims.

---

## 4. Independent-Claim § 101 Summary (one line each)

| Claim | What it protects | Why it survives Alice |
|---|---|---|
| **1 (Method)** | The geometric-authorization execution-control loop: embed → measure drift from a learned centroid → nonlinear cost → four-way execution decision. | Controls *machine execution* (allow/review/quarantine/deny), not a displayed score; recites concrete projection, centroid-update, and cost operations — an improvement to computer functionality. |
| **9 (System)** | The deployed runtime gate as a stateful machine that persists governed state across restarts and routes execution. | A concrete processor+memory architecture whose "restored after process restart" limitation ties it to a physical, stateful improvement, not an abstraction. |
| **15 (CRM)** | AST-round-trip + identifier-canonicality tamper detection that gates execution. | The execution-gating limitation supplies the practical application; the "distinct from tokenizer reconstruction-quality" clause forecloses the nearest abstract/known reference. |

---

## 5. § 112 Written-Description Support Index (by claim group)

| Claim group | Load-bearing file(s) | Specific anchor |
|---|---|---|
| 1, 9 spine | `runtime_gate.py`; `hyperbolic.ts` | `RuntimeGate.evaluate`; `projectEmbeddingToBall`; `hyperbolicDistance`; `_harmonic_cost`; `_update_centroid` |
| 2 (arcosh) | `hyperbolic.ts` | `hyperbolicDistance` lines 84-98 |
| 3 (cost species) | root `symphonic_cipher/`; `hyperbolic.ts` | `R^(d²)`; `phaseDistanceScore` `1/(1+d_H+w·pd)` |
| 4, 6 (φ weights) | `languesMetric.ts`; `runtime_gate.py` | `Math.pow(PHI,i)`; `tuple(PHI**k for k in range(6))` |
| 5 (centroid update) | `runtime_gate.py` | `_update_centroid` |
| 6 (immune/reflex) | `runtime_gate.py` | `_immune` set; `_reflex` dict; pre-pipeline fast-paths (1219-1330) |
| 7, 22 (fail-to-noise) | `runtime_gate.py` | `_fail_to_noise` |
| 8 (durable state) | `runtime_gate.py` | `save_state`/`load_state`/`STATE_SCHEMA` (2278-2397) |
| 10, 13(quarantine), 14 | `quarantine_lock.py` | `QuarantineLockPolicy`; `apply_quarantine_lock_to_dcp` |
| 11 (pre-filter stack) | `petri_pattern_filter.py`; `slm_router.py`; `orderedRejection.ts` | `tongue_coverage_score` [0x20,0x7E]; `is_high_risk_instruction_input`; Petri 173; `slm_router`; S0-S10 ordering |
| 12 (PQC receipt) | `offline_mode.ts`; `src/crypto/` | `DecisionCapsule`; `AuditEvent` (ML-DSA-65); `PQCrypto.{sign,encapsulate}` |
| 13 (audit receipt) | `runtime_gate.py` | `GateResult`; `_*_receipt_signal` |
| 15-16, 18-20 (tamper) | `bijective_tamper.py` | `evaluate_code`; `_NfcStubTokenizer`; `L13_MAPPING_RECOMMENDATION` |
| 17 (canonicality) | `identifier_canonicality.py` | `_classify_identifier`; `_ASCII_CONFUSABLES`; `_INVISIBLE_CODEPOINTS`; `_BIDI_CODEPOINTS` |
| 21 (deferred auth) | `sacred_eggs.py`; `tree_of_escalation.py` | `EggRing`; triadic binding; fail-to-noise-on-failure |
| 23 (swarm trust) | `hydra/`; `runtime_gate.py` | BFT consensus; `_council_review` |
| 24 (Hopfield) | `hyperbolic.ts` | `multiWellPotential`; `_null_space_anomaly` |
| 25 (juggling) | `juggling-scheduler.ts` | `FlightState`; `inertia`; arcs; 7 rules |

---

## 6. Components NOT Claimed and Why

| Component | File(s) | Why omitted from this set | Add via CIP? |
|---|---|---|---|
| **14-layer pipeline as a whole** (breathing transform L6, Möbius phase L7, spectral/spin coherence L9-10, triadic temporal distance L11, audio axis L14) | `hyperbolic.ts`; `src/spectral/`; `audioAxis.ts`; `causality_axiom.py` | The individual layers are recited as *signals* feeding claim 1's composite risk (spectral coherence, spin coherence, temporal drift), so their value is captured without a separate, harder-to-defend "14-layer" claim that risks § 112 enablement and § 103 aggregation rejections. | Optional continuation if a competitor copies the full ordered stack. |
| **Trichromatic (IR/visible/UV) governance overlay** | `trichromatic_governance.py` | Experimental, opt-in (`use_trichromatic_governance=False` default); recited generically as an "additional governance signal" under claim 1. Claiming the specific 10-D trichromatic embedding now risks new matter vs. the provisional. | Strong CIP candidate once stabilized (see MEMORY: IR/UV color-spectrum). |
| **Negative Tongue Lattice; Council Manifold; Tree of Escalation (as decision-makers)** | `negative_tongue_lattice.py`; `council_manifold_backend.py`; `tree_of_escalation.py` | All are opt-in and, for ToE, expressly *observational only at v1.0* (does not veto decisions per the in-code comment). Claiming a decision contribution they do not yet make would be unsupported. | CIP once they contribute to decisions (ToE v1.1+). |
| **Fibonacci trust levels / trust-multiplier headroom** | `runtime_gate.py` `fibonacci_trust_level`; `primitives/phi_poincare.py` | Captured generically by claim 1's "trajectory drift" severity adjustment and claim 9's "trust history" state. A Fibonacci-specific claim adds narrowness without clear competitive value. | Low priority. |
| **Reroute (REROUTE) decision path** | `runtime_gate.py` `_check_reroute`, `DEFAULT_REROUTES` | A fifth decision mode (redirect-to-safer-action). Deliberately left out of the independent claims' four-way decision recitation to keep them clean; could be a dependent. | Add as a cheap dependent in a continuation if reroute proves commercially central. |
| **Sacred Tongues token grids / tokenizer** | `src/tokenizer/`; `packages/sixtongues/` | The 16×16 grids and bijective byte↔token map support claims 4 and 15-16 as embodiments; a standalone tokenizer claim is a separate invention with its own prior-art surface. | Separate application if pursued. |
| **Red/Blue adversarial arena** | `src/security-engine/redblue-arena.ts` | A test/simulation harness, not the governed runtime path; not a product claim. | No. |

**Honest overall:** the independent claims intentionally absorb most omitted
subsystems as generic "additional/auxiliary signals," which is the right
trade — it keeps the independents broad and defensible while leaving the
distinctive, still-maturing subsystems (trichromatic, ToE-as-decider, full
14-layer stack) for continuations once they are stable and clearly disclosed.

---

## 7. Priority-Date Risk Assessment

**Threshold caveat (must be resolved by counsel):** every "supported" call below
is contingent on what U.S. Provisional 63/961,403 *as filed January 15, 2026*
actually discloses. The code is the § 112 enablement/written-description
evidence for the **non-provisional**; it is the **provisional's text and
drawings** that fix the **priority date**. Several modules below were committed
to the repo *after* January 15, 2026 (e.g., the durable-state autosave/rollback
and the bijective-tamper/identifier-canonicality gates appear in recent branch
history). For any such subject matter, the claim is enabled but may take the
non-provisional's **filing date**, not the provisional's, unless the provisional
already disclosed it. Counsel must diff the filed provisional against this set.

### Tier 1 — Fully supported by the Jan 15, 2026 provisional (low priority-date risk)

These are the core hyperbolic-governance mechanism the provisional was filed to
protect:

- **Claims 1, 2, 3, 4, 5, 9 — Risk note A (core spine, low risk).** Poincaré
  embedding, arcosh distance, nonlinear cost, golden-ratio semantic weights,
  centroid drift, four-way decision, system architecture. This is the invention
  spine; strongest priority posture. The main seam within the spine is
  cost-function consistency across the Python RuntimeGate, TypeScript kernel,
  and older `R^(d²)` embodiments — carried separately as risk note B below.
- **Claim 6** (immune/reflex fast-path) and **claim 13** (audit receipt) — basic
  gate mechanics consistent with the original disclosure.

### Tier 2 — Supported by code; provisional support must be confirmed (moderate risk)

- **Claim 7 — Fail-to-noise.** Cleanly implemented (`_fail_to_noise`). Risk is
  purely whether the provisional described returning indistinguishable noise on
  DENY. If yes → Tier 1. If the provisional only said "deny/block," the
  *indistinguishable + auditor-reproducible* framing may be new characterization.
- **Claim 8 — Durable state + rollback.** Implemented (`save_state`/`load_state`,
  `keep_previous` rollback). **Risk note F:** the claim's persisted-field list
  (centroid, cumulative cost, query count, trust history, adversarial memory)
  matches the code, and correctly **omits the reflex/safe-memory set**, which the
  implementation deliberately does NOT persist (so a tightened policy is never
  bypassed by a stale "previously allowed" entry). Do not add reflex to claim 8.
  Autosave/rollback commits are recent; confirm provisional support or accept the
  non-provisional filing date for this claim.
- **Claim 10 — Quarantine containment.** `quarantine_lock.py` is `v1`
  (`scbe.quarantine_lock.v1`) and may post-date the provisional. The *concept*
  of a quarantine decision is likely in the provisional; the *specific
  containment mechanics* (tool filtering + deadline + privilege + sandbox) may be
  newer. Likely supportable; confirm.
- **Claim 11 — Pre-filter stack.** Each layer is implemented and verifiable, but
  the Petri filter file documents version dates **through 2026-05-27** and the
  SLM router and `[0x20,0x7E]` coverage gate appear to be post-provisional
  refinements. The *architecture* (cheapest-reject-first) is sound; the
  *specific four-layer composition* is at material risk of taking the
  non-provisional date. Strong candidate to keep but flag.

### Tier 3 — Risk note B: § 112 enablement seam in cost-function embodiments

The amended Claim 1 now closes with a broader and safer execution-control clause
instead of requiring all embodiments to be superexponential. This change avoids
forcing the Python RuntimeGate embodiment into a formula it does not implement.
The implemented `_harmonic_cost` returns
`π^(φ·d*)` with `d* = min(weighted_dist, 5.0)` — a **bounded exponential**
(base ≈ 4.06; saturates near `π^8.09 ≈ 9.0 × 10³` because `d*` is clamped at
5.0), not a superexponential or unbounded function. The TS langues metric
(`R^(d²)` form) IS superexponential in `d`, but the Python gate that the rest of
the claims describe is not. **Recommendation:** preserve dependent alternatives
for all three disclosed cost species: (a) `R^(d²)`, (b) bounded reciprocal
`1/(1+d+2·pd)`, and (c) clamped RuntimeGate cost
`π^(φ·min(d*, d_max))`. This is still a key § 112 review point.

### Tier 4 — Risk note C: Claim 12 PQC receipt — supported in combination, integration partial

The post-quantum **decision-receipt mechanism exists**: `offline_mode.ts`
defines a `DecisionCapsule` (signed decision proof) and an `AuditEvent` signed
with `ML-DSA-65(event_hash)`, plus full `ML-DSA-65` / `ML-KEM-768` primitives via
`PQCrypto`. **However, the Python `RuntimeGate.evaluate()` does NOT call any of
it** — there is no `_issue_pqc_receipt` method; the gate's "receipt" is the
plaintext `GateResult` (text signals, no signature). So:

- The claim is **enabled** (a skilled engineer can build it; the mechanism is in
  the repo).
- It is best characterized as **"supported as a combination,"** not as a
  fully-integrated single-module embodiment.
- **Priority risk:** confirm the provisional disclosed PQC-signed *governance/
  authorization* receipts (as opposed to PQC for data encryption generally). The
  novelty is the binding of PQC signatures to *action-authorization decisions*,
  not the primitives. Counsel may wish to recite "a downstream executor verifies
  the signature before executing" (kept in the claim) as the concrete tie, and
  to add the TS `DecisionCapsule`/`AuditEvent` embodiment explicitly in the
  specification so the support is unambiguous.

### Tier 5 — Risk note D: Claims 15-20 tamper/canonicality — support uncertain vs. provisional

`bijective_tamper.py` and `identifier_canonicality.py` are robustly implemented
and enabled, but per the predecessor packet's own caution and the recent branch
history, **these gates may be new matter relative to the January 15, 2026
provisional.** The 2026-05-28 packet expressly lists this family as "May be new
matter if not in provisional. Counsel should check," and the integration into
`runtime_gate.py` (the `_evaluate_bijective_tamper` / `_evaluate_identifier_
canonicality` overlays) is flag-gated and recent. **Recommendation:** counsel
should decide between (a) including Family C in this non-provisional and
accepting that claims 15-20 may carry the non-provisional filing date, or (b)
splitting Family C into a **continuation-in-part** so the Tier-1 core retains the
provisional date cleanly. Family C is independently valuable (homoglyph /
Trojan-Source / NFC tamper on *source code identifiers at the AST level* is a
genuine, narrowly-held niche) and survives on its own.

### Tier 6 — Risk note E: Claims 21-25 extra dependents — mostly CIP material

- **Claims 21-22 (Sacred Eggs five-predicate + all-paths-indistinguishable).**
  Production `sacred_eggs.py` implements a **3-ring (CORE/INNER/OUTER + CA)**
  container with **triadic binding** and **fail-to-noise on auth failure** — NOT
  the specific **five-predicate (P_tongue / P_geo / P_path / P_quorum / P_crypto)
  conjunction** the claim recites. **Partial support at best; CIP candidate.**
  Counsel should consider reformulating to "N predetermined predicates including
  at least a semantic, a geometric, and a cryptographic predicate," which tracks
  the implemented ring/triad/fail-to-noise model and the Mother-Avion living-
  credential direction without overclaiming a five-way conjunction that is not in
  code. Claim 22's "every output path indistinguishable" is supported in spirit
  by the egg's regenerate-shell-on-failure behavior + `_fail_to_noise`.
- **Claim 23 (swarm trust EMA `τ_new = α·τ_old + (1−α)·v`).** The *concept* of
  reputation-weighted, self-excluding swarm consensus is supported by HYDRA's BFT
  and the in-gate `_council_review`. The *specific EMA formula* appears only in
  `demo/`, `archive/`, and `external_repos/` — **CIP material vs. the
  provisional.** Either move to a continuation or recite the generic
  council-consensus (`_council_review` fail-count) instead of the EMA.
- **Claim 24 (Hopfield energy `−½c'ᵀWc' + θᵀc'`).** The production analog is the
  L8 **multi-well potential** (`multiWellPotential`) plus the null-space anomaly
  scorer; the *explicit Hopfield quadratic form* is archive/external only. **CIP
  material.** Counsel may prefer to claim the multi-well-potential novel-intent
  detector (which IS in production) rather than the Hopfield form.
- **Claim 25 (physics-juggling coordination).** **Strongly supported** by
  `src/fleet/juggling-scheduler.ts` (FlightState, inertia, catch windows, arcs,
  the seven rules verbatim). Lowest risk of the five; treat as a solid dependent,
  though confirm the scheduler predates the provisional or accept the
  non-provisional date.

### Recommended filing posture

1. **File now, provisional date secure:** claims 1-6, 9, 13 (Tier 1 core).
2. **File now, confirm provisional or accept non-provisional date:** claims 7, 8,
   10, 11, 12, 14 — verify each against the filed provisional; most are likely
   supportable, claim 11's specific composition and claim 12's gate-integration
   are the two to scrutinize.
3. **Confirm before filing (§ 112 seam):** keep the specification explicit that
   `R^(d²)`, bounded reciprocal scoring, and the clamped RuntimeGate cost are
   alternative embodiments, not one mandatory formula.
4. **Decide: include vs. CIP** for Family C (claims 15-20) — strong invention,
   but new-matter risk; a CIP cleanly preserves the Tier-1 priority date.
5. **Reserve for CIP / reformulate:** claims 21 (reformulate to 3-predicate),
   23 (use council consensus, not EMA), 24 (use multi-well, not Hopfield). Keep
   claim 22 tied to the egg + fail-to-noise; keep claim 25 as drafted.

---

## 8. Drafting Notes / Open Questions for Counsel

1. Confirm micro-entity status at filing (gross-income and prior-applications
   limits) — re-verify, do not assume.
2. Run the filed-provisional vs. this-set diff (Tiers 2-6) and reclassify each
   moderate/CIP claim as priority-supported or non-provisional-dated.
3. Confirm the cost-function embodiment language (risk note B) — this is the
   most examinable § 112 math issue in the set.
4. Decide Family C inclusion vs. CIP (risk note D).
5. Reformulate claims 21, 23, 24 to track production code, or move to a
   continuation (risk note E).
6. Confirm the specification expressly discloses the TS `DecisionCapsule` /
   `AuditEvent` PQC-receipt embodiment so claim 12's support is unambiguous.
7. Figures to prepare (carry from the 2026-05-28 packet, add three):
   (1) Poincaré embedding + arcosh distance; (2) harmonic-wall cost curve with
   the `d* = min(d,5)` saturation marked; (3) allow/review/quarantine/deny gate;
   (4) immune/reflex fast-path vs. full-pipeline flow; (5) **fail-to-noise data
   flow (DENY → seed = H(prefix‖hash) → iterate → noise)**; (6) bijective
   tamper + identifier-canonicality AST-comparison flow; (7) **cheapest-reject-
   first pre-filter stack (S0-S10)**; (8) quarantine-lock containment;
   (9) **PQC decision-receipt sign/verify (ML-DSA-65) + KEM (ML-KEM-768)**.

*End of working draft. Not legal advice.*

# Patent Claims — Fixed Set v3
## System and Method for Hyperbolic Geometry-Based Authorization with Topological Control-Flow Integrity

| Field | Value |
|---|---|
| **Priority** | U.S. Provisional Application No. 63/961,403, filed January 15, 2026 |
| **Internal docket** | SCBE-2026-0001 |
| **Conversion deadline** | January 15, 2027 |
| **Supersedes** | PATENT_CLAIMS_EXPANDED_v2.md |
| **Status** | Working draft. NOT legal advice. |

---

## Change Log from v2

| Claim | Change | Reason |
|---|---|---|
| **1** | `whereby` clause rewritten | `_harmonic_cost` = `π^(φ·d*)` (bounded exponential); "superexponentially" was unsupported and "approaches boundary" misdescribed the cost driver |
| **3** | Added species (iii) `π^(φ·d)` | Anchors the specific implemented formula as a named embodiment |
| **21** | 5-predicate → 3-predicate (N-predicate, ≥3 required) | Production code is a 3-ring structure (CORE/INNER/OUTER), not the 5-way conjunction; reformulation tracks code |
| **22** | Kept verbatim | Fail-to-noise on every path is well-supported |
| **23** | REPLACED EMA swarm trust → REROUTE decision | EMA formula (`τ_new = α·τ_old + (1−α)·v`) appears only in archive/demo; REROUTE is production code (`_check_reroute`, `DEFAULT_REROUTES`), unclaimed, commercially valuable |
| **24** | REPLACED Hopfield energy → null-space anomaly | Explicit Hopfield form only in archive; `_null_space_anomaly` is production code, unique, unclaimed |
| **25** | Kept verbatim | Strongly supported by `juggling-scheduler.ts` |
| **26** | NEW — bijective token alphabet per tongue axis | Closes gap: competitor using phi-weights with non-bijective tokenizer would not infringe 4 or 15-20; this claim locks the 16×16 prefix×suffix design |

**Fee impact:** 26 total claims. Extra claims over 20: 6 × $40 = $240. Total micro-entity: $400 base + $240 = **$640**.

---

## Formula Reference (verified against `runtime_gate.py`)

| Symbol | Value | Source |
|---|---|---|
| φ (golden ratio) | 1.618033988749895 | `PHI = 1.618033988749895` line 51 |
| π | 3.14159265358979… | `PI = math.pi` line 52 |
| Tongue weights | `(φ⁰, φ¹, φ², φ³, φ⁴, φ⁵)` = (1, 1.618, 2.618, 4.236, 6.854, 11.090) | `TONGUE_WEIGHTS = tuple(PHI**k for k in range(6))` line 54 |
| Cost formula | `cost = π^(φ·d*)` | `_harmonic_cost` lines 889-899 |
| d* | `min(weighted_dist, 5.0)` | clamp in `_harmonic_cost` line 898 |
| weighted_dist | `sqrt(Σ wₖ·(tcₖ − centroidₖ)²)` | `_harmonic_cost` lines 896-897 |
| Cost at d*=0 | 1.0 (baseline, safe) | |
| Cost at d*=1 | π^1.618 ≈ 5.05 | |
| Cost at d*=2 | π^3.236 ≈ 25.5 | |
| Cost at d*=5 | π^8.09 ≈ 9,070 (maximum) | |

The cost is a **bounded exponential** that saturates at ≈ 9,070× baseline at the clamp limit. The claim text now accurately reflects this.

---

## CLAIMS

### CLAIM FAMILY A — METHOD

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

&nbsp;&nbsp;&nbsp;&nbsp;whereby the governance cost follows a function of the form B^(k·d), where B is a base greater than one, k is a positive scaling constant, and d is a distance measure computed from the hyperbolic space, such that the governance cost increases monotonically as the embedded point deviates from the session centroid.

> *§ 101:* Controls machine execution via a four-way decision; not a displayed score.
> *§ 112:* `_harmonic_cost` (lines 889-899): `π^(φ·d*)` with `d*=min(weighted_dist,5.0)`; direct support for B=π, k=φ.
> **CHANGE FROM v2:** `whereby` clause replaced. v2 said "increases superexponentially as the embedded point approaches a boundary" — unsupported (actual formula is exponential, not superexponential; cost is distance-from-centroid, not proximity-to-boundary).

---

**2.** The method of claim 1, wherein the hyperbolic distance is computed as
`d_H = arccosh(1 + 2‖u − v‖² / ((1 − ‖u‖²)(1 − ‖v‖²)))`, where `u` is the
embedded point and `v` is the session centroid.

> *§ 112:* `hyperbolic.ts` `hyperbolicDistance` lines 84-98. Unchanged from v2.

---

**3.** The method of claim 1, wherein the nonlinear cost function comprises one
of: (i) a function of the form `H(d, R) = R^(d²)`, where `d` is a distance
measure and `R` is a base greater than one; (ii) a bounded safety-score function
of the form `H = 1 / (1 + d + 2·pd)`, where `pd` is a phase-deviation term; or
(iii) a function of the form `π^(φ·d)`, where `π` is the mathematical constant
pi and `φ` is the golden ratio.

> *§ 112:* Species (i) `R^(d²)` → root `symphonic_cipher/`; species (ii) → `hyperbolic.ts` `phaseDistanceScore`; **species (iii) NEW** → `runtime_gate.py` `_harmonic_cost` (`π^(φ·d*)`, lines 889-899).
> **CHANGE FROM v2:** Species (iii) added to anchor the implemented formula as a named embodiment and to resolve the § 112 seam in claim 1's `whereby` clause.

---

**4.** The method of claim 1, wherein the additional governance signal comprises
a six-axis semantic weighting in which each axis has a predetermined weight equal
to a power of the golden ratio, `φ^k` for `k = 0..5`, with `φ ≈ 1.618`.

> *§ 112:* `languesMetric.ts` `Math.pow(PHI,i)`; `runtime_gate.py` `TONGUE_WEIGHTS = tuple(PHI**k for k in range(6))`. Unchanged from v2.

---

**5.** The method of claim 1, wherein maintaining the session centroid comprises
an incremental update of the form
`centroid_new = (n · centroid_old + coord) / (n + 1)`, where `n` is a running
count of prior embedded points and `coord` is the embedded point of the current
request.

> *§ 112:* `runtime_gate.py` `_update_centroid` (lines 961-968): `centroid * ((n-1)/n) + tc/n` — algebraically equivalent. Unchanged from v2.

---

**6.** The method of claim 1, further comprising maintaining a hash-indexed
adversarial-memory set and a hash-indexed safe-memory set, and, prior to said
transforming, returning a deny decision for a request whose content hash is a
member of the adversarial-memory set, and returning an allow decision for a
request whose content hash is a member of the safe-memory set, in each case
without computing the hyperbolic distance.

> *§ 112:* `runtime_gate.py` `_immune` + `_reflex` dicts; fast-paths at lines 1219-1330. Unchanged from v2.

---

**7.** The method of claim 1, further comprising, responsive to a deny decision,
generating a deterministic pseudorandom noise output by computing a seed as a
cryptographic hash of a fixed prefix concatenated with a content hash of the
denied request, iteratively re-hashing the seed until a target length is reached,
and returning the noise output in place of an error response, such that the noise
output is indistinguishable from a valid output to an observer not holding the
governance keys, is identical for identical denied requests, and is reproducible
by an auditor from the content hash.

> *§ 112:* `runtime_gate.py` `_fail_to_noise` (lines 174-189): `sha256("fail-to-noise:"+hash)`, iterative re-hash until length reached. Unchanged from v2.

---

**8.** The method of claim 1, further comprising periodically persisting, to a
durable store, at least the session centroid, a cumulative governance cost, a
query count, a trust history, and the adversarial-memory set of claim 6; and,
after a process restart, restoring the persisted values so that the session
continues from the restored trajectory rather than from a cold start.

> *§ 112:* `runtime_gate.py` `save_state`/`load_state`/`STATE_SCHEMA = "runtime-gate-state/v1"` (lines 2278-2397). Note: reflex/safe-memory set is intentionally NOT persisted (code design decision — avoids stale bypass); claim correctly omits reflex. Unchanged from v2.

---

### CLAIM FAMILY B — SYSTEM

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

> *§ 101:* Physical processor+memory architecture with restored-after-restart limitation. *§ 112:* `RuntimeGate.evaluate` + `save_state`/`load_state`; `STATE_SCHEMA` snapshot. Unchanged from v2.

---

**10.** The system of claim 9, wherein the quarantine route applies a non-error
containment state that, without crashing or terminating the session, restricts
available tools to an allowed subset, enforces an execution-time deadline,
restricts execution permissions, and limits outbound network or filesystem effects
of the proposed action.

> *§ 112:* `quarantine_lock.py` `QuarantineLockPolicy`. Unchanged from v2.

---

**11.** The system of claim 9, wherein the auxiliary signals are produced by a
multi-layer pre-filter stack ordered cheapest-reject-first, comprising:

&nbsp;&nbsp;&nbsp;&nbsp;(i) a script-origin gate computing a coverage score as a fraction of UTF-8 bytes of the proposed action falling within the printable ASCII range [0x20, 0x7E] and rejecting when the coverage score is below a threshold;

&nbsp;&nbsp;&nbsp;&nbsp;(ii) an instruction-safety gate matching compiled regular-expression patterns for instruction-override, persona-manipulation, or dangerous-tool-invocation text;

&nbsp;&nbsp;&nbsp;&nbsp;(iii) a semantic pattern filter matching the proposed action against an adversarial-intent corpus; and

&nbsp;&nbsp;&nbsp;&nbsp;(iv) a small-language-model router that rejects an input for which no applicable semantic band is classified;

&nbsp;&nbsp;&nbsp;&nbsp;wherein each gate operates before the hyperbolic-distance computation, and rejection by any gate prevents invocation of subsequent gates.

> *§ 112:* `petri_pattern_filter.py`, `slm_router.py`, `orderedRejection.ts`. Unchanged from v2. Priority-date risk for specific four-layer composition (see v2 §7 risk note).

---

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

> *§ 112:* `offline_mode.ts` `DecisionCapsule`, `AuditEvent`, `PQCrypto`. Python gate integration partial (see v2 §7 risk note C). Unchanged from v2.

---

**13.** The system of claim 9, wherein the system emits an audit receipt
comprising at least the decision, the harmonic governance cost, signal
identifiers, and decision-relevant metadata including a session query count and
a cumulative cost.

> *§ 112:* `runtime_gate.py` `GateResult` dataclass + `_*_receipt_signal` formatters. Unchanged from v2.

---

**14.** The system of claim 9, wherein the system is deployed as at least one of:
a REST API endpoint, an agent bus service, a command-line interface, or a
programmatic client library.

> *§ 112:* `src/api/`, `packages/agent-bus/`, `packages/cli/bin/scbe.js`. Unchanged from v2.

---

### CLAIM FAMILY C — COMPUTER-READABLE MEDIUM

**15.** A non-transitory computer-readable medium storing instructions that, when
executed, cause one or more processors to:

&nbsp;&nbsp;&nbsp;&nbsp;receive an input comprising source code or an identifier-containing input;

&nbsp;&nbsp;&nbsp;&nbsp;generate a re-encoded form of the input by applying a bijective encode operation followed by a decode operation mapping the input to a token sequence and back to a decoded input;

&nbsp;&nbsp;&nbsp;&nbsp;compute a first canonical abstract syntax tree (AST) representation of the input and a second canonical AST representation of the decoded input, each comprising a content-derived fingerprint;

&nbsp;&nbsp;&nbsp;&nbsp;compute a tamper signal based on at least one of: (i) a divergence between the first and second canonical AST representations; (ii) a failure of the decoded input to parse into a valid AST; (iii) a Unicode canonicality failure; or (iv) a confusable-identifier condition; and

&nbsp;&nbsp;&nbsp;&nbsp;provide the tamper signal to a governance gate that escalates or blocks a proposed computational action when the tamper signal exceeds a threshold;

&nbsp;&nbsp;&nbsp;&nbsp;wherein the tamper signal is distinct from a tokenizer reconstruction-quality measure in that it is derived from a comparison of abstract syntax tree representations and gates execution of a proposed action.

> *§ 101:* Execution-gating practical application; "distinct from tokenizer quality" clause forecloses BLEU-type art. *§ 112:* `bijective_tamper.py`. Unchanged from v2. Priority-date risk: may be new matter vs. provisional (see v2 §7 risk note D).

---

**16.** The medium of claim 15, wherein each content-derived fingerprint
comprises a SHA-256 digest of the corresponding canonical AST, such that two
inputs that are semantically equal but differ in whitespace or comments produce
identical fingerprints.

> *§ 112:* `bijective_tamper.py` line 222. Unchanged from v2.

---

**17.** The medium of claim 15, wherein the confusable-identifier condition is
detected by parsing the input into an AST, extracting identifier names, and, for
each identifier, determining whether any non-ASCII codepoint maps to an
ASCII-confusable codepoint, whether the identifier mixes two or more distinct
writing scripts, or whether the identifier contains an invisible or bidirectional
control codepoint; and computing a confusable-identifier score as a function of
the fraction of suspicious identifiers.

> *§ 112:* `identifier_canonicality.py` `_classify_identifier`. Unchanged from v2.

---

**18.** The medium of claim 15, wherein the governance gate denies the proposed
computational action on a syntax-divergence class in which the decoded input
fails to parse, quarantines the proposed computational action on a structural-
divergence class in which the canonical ASTs diverge while both parse, and allows
with annotation on a normalization-divergence class attributable to Unicode NFC
normalization.

> *§ 112:* `bijective_tamper.py` `L13_MAPPING_RECOMMENDATION`. Unchanged from v2.

---

**19.** The medium of claim 15, wherein, when a tokenizer artifact is absent, the
instructions substitute a normalization stub that performs the encode operation
by applying Unicode NFC normalization and encoding as UTF-8, the stub preserving
the bijective round-trip property for ASCII inputs.

> *§ 112:* `bijective_tamper.py` `_NfcStubTokenizer`. Unchanged from v2.

---

**20.** The medium of claim 15, wherein the tamper signal, a divergence
classification, and the content-derived fingerprint are recorded in an audit trail.

> *§ 112:* `runtime_gate.py` `_tamper_receipt_signal` / `_canonicality_receipt_signal`. Unchanged from v2.

---

### CLAIM FAMILY — EXTRA HIGH-VALUE DEPENDENTS (Claims 21-25)

**21.** The method of claim 1, further comprising generating a cryptographic
authorization container that is unlocked only when N predetermined predicates are
satisfied, where N is at least three, the predicates including at least: a
semantic predicate evaluating whether the context representation of the proposed
action satisfies an authorized semantic profile; a geometric predicate measuring
whether the embedded point lies within a predetermined hyperbolic distance from
the session centroid; and a cryptographic predicate verifying a post-quantum
signature; wherein failure of any predicate causes the container to return a
noise output generated by the fail-to-noise function of claim 7, such that both
a successful unlock and any predicate failure produce outputs that are
indistinguishable to an observer not holding the authorization keys.

> *§ 112:* `src/crypto/sacred_eggs.py` — 3-ring structure (CORE/INNER/OUTER + CA) with triadic binding; fail-to-noise on auth failure; `tree_of_escalation.py` as escalation substrate. **CHANGE FROM v2:** Reformulated from five specific predicates (semantic/geometric/path/quorum/crypto) to N-predicate with minimum three required. Tracks the actual 3-ring production model. "Path predicate" and "quorum predicate" are deferred to CIP.

---

**22.** The method of claim 21, wherein the noise output is generated by the
deterministic re-hashing of claim 7, such that every output path — both a
successful unlock and a failure of any predicate — produces an output
indistinguishable, to an observer not holding the keys for all of the predicates,
from any other output path.

> *§ 112:* `sacred_eggs.py` regenerate-shell-on-failure behavior + `_fail_to_noise`. Unchanged from v2.

---

**23.** The method of claim 1, further comprising: prior to emitting the
governance decision, determining whether the computational action matches a
predetermined reroute rule associated with a class of actions; and, when a match
is found, substituting a replacement action for the proposed computational action
and emitting an allow decision for the replacement action, such that high-risk
classes of actions are redirected to lower-risk alternatives without exposing a
denial response to the requesting entity.

> *§ 112:* `runtime_gate.py` `_check_reroute` + `RerouteRule` dataclass (line 192+) + `DEFAULT_REROUTES` dict — production code mapping pattern classes to replacement actions (`redact_and_log`, `log_intent_only`, `soft_delete`, `sandbox_execute`, `file_read_denied`). Called in `evaluate()` before the main decision path. **REPLACES v2 claim 23** (EMA swarm trust τ formula, which appears only in archive/demo code).

---

**24.** The method of claim 1, further comprising computing a null-space anomaly
score by determining whether per-axis deviations of the context representation
from the session centroid each fall below a predetermined threshold; incrementing
the null-space anomaly score when all per-axis deviations are below the threshold;
and incorporating the null-space anomaly score into the composite risk value;
wherein a null-space anomaly score above a predetermined level is treated as a
governance signal indicating an action that is deliberately mimicking baseline
behavior to evade the governance cost.

> *§ 112:* `runtime_gate.py` `_null_space_anomaly` (lines 807-835): checks `np.all(deviations < NULL_SPACE_EPSILON)` — returns `1.0 - mean_dev/epsilon` when all axes are suspiciously close to baseline; also catches `coord_std < 0.03` uniform-coords case. Called as a governance signal in the main `evaluate()` path. **REPLACES v2 claim 24** (Hopfield energy `−½c'ᵀWc' + θᵀc'`, which appears only in archive/external paths, not in production gate).

---

**25.** The system of claim 9, wherein the system coordinates task execution
across a plurality of agent slots using a physics-based juggling model in which
tasks are modeled as balls having inertia proportional to a task priority, agent
slots are modeled as hands having readiness states, handoffs are modeled as
throws having predicted catch windows, and a governance cost of a task increases
when a trajectory of the task deviates from a predicted flight arc, such that
higher-risk tasks are assigned higher arcs and fewer handoffs.

> *§ 112:* `src/fleet/juggling-scheduler.ts` — `FlightState`, `inertiaPenalty`, seven juggling rules (verbatim). Unchanged from v2. Lowest-risk of the five extra claims.

---

**26.** The method of claim 4, wherein each axis of the six-axis semantic
weighting employs a bijective token alphabet in which each token is uniquely
identified by a prefix element selected from a first predetermined set and a
suffix element selected from a second predetermined set, such that the complete
token vocabulary for each axis is a bijective mapping between token strings and
integer indices, and the token vocabularies of distinct axes are disjoint.

> *§ 112:* `packages/sixtongues/` — 6 tongues × 16-prefix × 16-suffix = 256 tokens per tongue; each tongue's 256-token vocabulary is disjoint from the others; encode/decode is bijective by construction. Also supported by `runtime_gate.py` `TONGUE_WEIGHTS` and `src/tokenizer/`. Closes the coverage gap where a competitor implements phi-weighting with a non-bijective or merged-vocabulary tokenizer.

---

## What Has Been Deferred to CIP

| Feature | Why deferred | CIP readiness |
|---|---|---|
| EMA swarm trust `τ_new = α·τ_old + (1−α)·v` (former claim 23) | Formula only in archive/demo, not production gate | File CIP once `_council_review` uses the EMA formula in production |
| Hopfield energy `−½c'ᵀWc' + θᵀc'` (former claim 24) | Explicit form only in archive; production uses multi-well potential | Claim multi-well potential in CIP once `hamiltonianCFI.ts` feeds the Python gate directly |
| Claims 15-20 family C (bijective tamper + AST) | May be new matter vs. provisional | Include here (accepting non-provisional date) OR split into CIP; see v2 §7 risk note D |
| Trichromatic governance (IR/UV, 10D) | Opt-in, not default; `use_trichromatic_governance=False` | CIP once production-default |
| Tree of Escalation as decision-maker | Currently observational only (`v1.0` in-code comment) | CIP when ToE v1.1+ contributes to decisions |
| Full 14-layer pipeline as ordered composition | Risk of § 112 enablement + § 103 aggregation rejection | Optional continuation if competitor copies the specific layer order |
| Sacred Tongues tokenizer deeper architecture (e.g. tongue-specific harmonic frequency ratios, runic/particle dual-layer semantics) | Core grid structure claimed in claim 26; deeper semantic design is separate | Separate application if pursued |

---

## What Could Still Be Added (Costs $40 Each, Adds to Fee)

Adding any of these pushes past 25 claims. Each additional claim = $40 more micro-entity fee.

| Candidate | File | Strength | Recommended? |
|---|---|---|---|
| **Intent spike boosting** — detecting and amplifying specific intent signals prior to embedding | `runtime_gate.py` `_apply_intent_spike` | Production, unique | ✓ Add if budget allows (+$40 → $640) |
| **Spin quantization** — computing per-tongue deviation from centroid as a discrete spin vector used in governance decisions | `runtime_gate.py` `_spin` (lines 860-888) | Production, unique | ✓ Add if budget allows (+$40 → $640) |
| **REROUTE as a 5th decision mode system claim** | Same as new claim 23 but as a system claim dependent of claim 9 | Strong | Low priority; method claim 23 already covers it |
| **Fibonacci trust level multiplier** | `runtime_gate.py` `fibonacci_trust_level` | Production | Low priority; captured generically by "trajectory drift" in claim 1 |

**Recommended immediate action:** File with 25 claims as written ($600). Reserve intent-spike and spin as a continuation if a competitor introduces a similar evasion-detection mechanism.

---

## Fee Summary (26 claims)

| Item | Micro-entity fee |
|---|---|
| Basic utility filing | $70 |
| Search | $154 |
| Examination | $176 |
| **Base subtotal (≤3 independent, ≤20 total)** | **$400** |
| 6 extra claims × $40 (claims 21-26) | $240 |
| **Total** | **$640** |

---

*End of working draft. Not legal advice. v3 generated 2026-05-28.*

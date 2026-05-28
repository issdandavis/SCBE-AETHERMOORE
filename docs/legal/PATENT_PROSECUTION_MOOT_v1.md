# Patent Prosecution Moot Court — SCBE-AETHERMOORE

**Exercise:** Patentability moot of U.S. Non-Provisional (priority: Provisional No. 63/961,403, filed Jan. 15, 2026)
**Title:** System and Method for Hyperbolic Geometry-Based Authorization with Topological Control-Flow Integrity
**Inventor:** Issac Davis (pro se), Port Angeles, WA
**Conversion deadline:** January 15, 2027
**Status:** Teaching exercise / counsel working draft — not legal advice. Claim numbering follows the working packet (Claims 1, 9, 15).

---

## Round 1 — Opening Examination

**PROF. VANCE:** We have three independent claims and a January deadline. Examiner's table, open.

**MARCUS WEBB:** Claim 1 fails *35 U.S.C. § 101*. Under *Alice v. CLS Bank*, step one, it is directed to an abstract idea — a mathematical algorithm. Strip the verbs: "embed a point, measure a distance, plug it into a cost function, output a label." *Mayo* and *Gottschalk v. Benson* tell us math is not eligible. Step two adds nothing: "one or more processors" is a generic computer. They took hyperbolic geometry and said "do it on a computer."

**PROF. VANCE:** Which words carry the abstraction?

**MARCUS WEBB:** "Computing a hyperbolic distance" and "computing a governance cost... using a nonlinear cost function that increases as the distance increases." A formula and a comparison. The *emitting* step just outputs the result.

**PRIYA OKONKWO:** And if it survives § 101, it fails *§ 102/103*. Nickel & Kiela, *Poincaré Embeddings for Learning Hierarchical Representations* (2017), already embeds data into the Poincaré ball and computes hyperbolic distance. Ganea et al. (2018) built hyperbolic neural-network layers. The "nonlinear cost increasing with distance" is just an exponential — and under *KSR v. Teleflex*, a skilled artisan pairs a known embedding with a known monotone cost trivially.

**PROF. VANCE:** Ms. Okonkwo, does Nickel/Kiela disclose every limitation? Anticipation under § 102 requires all of them in one reference.

**PRIYA OKONKWO:** Not the decision gate, I concede. But under § 103 the gate is an obvious add-on — a threshold on a number.

**MARCUS WEBB:** And Claim 15 is worse on novelty. "Encode/decode round-trip comparison" is standard BPE tokenizer quality testing. Round-trip fidelity has been a tokenizer evaluation metric for years.

---

## Round 2 — Applicant's Response

**JORDAN REYES:** Two answers on § 101. *Enfish v. Microsoft*: a claim directed to a *specific improvement in computer functionality* is not abstract at step one. Ours is concrete — adversarial inputs become computationally prohibitive because hyperbolic distance diverges to infinity at the ball boundary, so cost scales superexponentially. No allow-list or classifier has that security property.

But our closer case is *McRO v. Bandai Namco*: using a *specific* mathematical relationship to reach a result not previously achieved is not abstract. We disclose the exact arcosh metric feeding a harmonic wall, combined with a *running session reference* that updates across requests. No prior authorization system used this mechanism. *Diamond v. Diehr* is the anchor — a formula applied to a specific technological process is eligible.

**PROF. VANCE:** Ms. Okonkwo's prior art?

**JORDAN REYES:** Nickel/Kiela embed *static, offline-learned* hierarchies for *representation* — organizing data. We use the ball for *enforcement* — making deviation expensive in real time. Our own specification cites Nickel/Kiela and draws exactly that line. They have no session state, no cost-as-security, no governance decision. Ganea is hyperbolic layers for *training* a model. Combine them and you still get a classifier — which the spec's Background distinguishes: classifiers fall to adversarial examples and give probabilistic, not geometric, guarantees.

**DAE-JUNG PARK:** To make that structural, not just argumentative, we amend. New limitation: the trusted reference is *a session centroid updated as a function of prior embedded points within the session*, with severity adjusting on *trajectory drift across a plurality of requests*. Static embeddings can't read on that — Nickel/Kiela's points never move per session. We pull the packet's accumulate-state dependent claim up into the independent claim.

**PROF. VANCE:** Now the hard one. Your specification has more than one cost formula. The detailed description claims `H(d,R) = R^(d²)`. It also discloses a bounded variant `H = 1/(1+d+2·pd)`. And your shipped Python gate, `runtime_gate.py`, computes `π^(φ·d*)` over a *weighted Euclidean* distance — not arcosh at all. Claim 1 says only "nonlinear cost function." Is that genus described under *§ 112(a)*?

**JORDAN REYES:** Three forms — we won't pretend otherwise. But that helps us. Under *Ariad v. Eli Lilly*, a genus is supported by disclosure of representative species that bound it. The spec expressly discloses two — the superexponential `R^(d²)` and the bounded reciprocal — both monotone in distance. That bounds the genus "a nonlinear cost function that increases as distance increases."

**DAE-JUNG PARK:** And we add a fallback dependent claim limiting the cost to those two disclosed forms, so if the genus falls, the species survive. The Python gate's `π^(φ·d*)` and weighted-Euclidean distance are *not* in the provisional — continuation-in-part material, not § 112 support here. The canonical hyperbolic embodiment is the TypeScript kernel, `packages/kernel/src/hyperbolic.ts`, which computes the arcosh distance the claim recites.

---

## Round 3 — Examiner's Rebuttal and Final Exchange

**MARCUS WEBB:** I'll concede the amended Claim 1 likely clears *Alice* — the session-centroid update is a specific mechanism, and *McRO* fits. But I press *§ 112(a)/(b)* on "bounded hyperbolic space." Is that the Poincaré ball only, or every hyperbolic model? If broader than the ball, the disclosure — which describes *only* the ball — doesn't support it, and the term is indefinite under *Nautilus v. Biosig*.

**JORDAN REYES:** The Definitions section defines the ball as `B^n = {u ∈ R^n : ‖u‖ < 1}` with its metric tensor, and recites the tanh-normalized projection with epsilon-clamping that keeps points inside the *open unit ball*. "Bounded" has antecedent meaning. To remove doubt we amend the independent claim to recite "a bounded hyperbolic space comprising a Poincaré ball model," preserving "bounded non-Euclidean manifold" in a dependent claim. Definite up top; genus still available.

**MARCUS WEBB:** And Claim 15 versus tokenizer round-trip?

**DAE-JUNG PARK:** Purpose and downstream signal — and it's in the code. BPE round-trip is a quality metric, does the tokenizer reconstruct the bytes, with no consumer. Our medium computes `parse(decode(encode(src))) ≡ parse(src)`, hashes the *canonical AST* with SHA-256, and *escalates a governance decision* when the fingerprint diverges or the decoded source fails to parse. We amend Claim 15 to recite the AST-canonical comparison and the escalation loop. A tokenizer evaluator never compiles an AST and never gates an action.

**PROF. VANCE:** Assessment. Claim 1 survives § 101 as amended — *Enfish* plus *McRO*, the session-centroid limitation separating you from Nickel/Kiela and Ganea on § 102/103. To survive § 112, recite the Poincaré ball up top and demote "bounded non-Euclidean manifold" and the two cost-function species to dependents — your *Ariad* fallback. Omit the `π^(φ·d*)` weighted-Euclidean runtime formula or file it as a CIP; it is not in the provisional and claiming it risks your January 15, 2026 priority date. Lead with Claim 15 — the AST-hash-plus-escalation mechanism is genuinely distinct from tokenizer literature. Narrow the independents, bank the breadth in dependents, preserve priority. The core is patentable.

---

## Amended Claims (Post-Debate Draft)

> Drafting notes: Independent claims narrowed to the disclosed Poincaré-ball embodiment for § 112 definiteness; breadth preserved in dependent claims (manifold genus, cost-function species) as *Ariad* fallbacks. Session-stateful centroid added to Claim 1 to distinguish static-embedding prior art (Nickel/Kiela, Ganea). Claim 15 recites AST-canonical comparison and the governance-escalation loop to distinguish tokenizer round-trip quality testing.

### Amended Claim 1 (Method)

1. A computer-implemented method for governing execution of a computational action, the method comprising:

&nbsp;&nbsp;&nbsp;&nbsp;receiving, by one or more processors, a request associated with the computational action;

&nbsp;&nbsp;&nbsp;&nbsp;generating, from the request, a context representation comprising one or more semantic, operational, or temporal features;

&nbsp;&nbsp;&nbsp;&nbsp;transforming the context representation into an embedded point in a bounded hyperbolic space comprising a Poincaré ball model, the transforming comprising a tanh-normalized projection with epsilon clamping that constrains the embedded point to an open unit ball;

&nbsp;&nbsp;&nbsp;&nbsp;maintaining a session centroid as a trusted reference region, the session centroid being updated as a function of a plurality of embedded points corresponding to prior requests received within a session;

&nbsp;&nbsp;&nbsp;&nbsp;computing a hyperbolic distance between the embedded point and the session centroid in the Poincaré ball model;

&nbsp;&nbsp;&nbsp;&nbsp;computing a governance cost from the hyperbolic distance using a nonlinear cost function that increases as the hyperbolic distance increases;

&nbsp;&nbsp;&nbsp;&nbsp;combining the governance cost with at least one additional governance signal selected from semantic weighting, temporal drift, spectral coherence, spin coherence, identifier canonicality, and bijective tamper detection, to produce a composite risk value;

&nbsp;&nbsp;&nbsp;&nbsp;adjusting a severity of the composite risk value as a function of trajectory drift of the embedded points across the plurality of prior requests; and

&nbsp;&nbsp;&nbsp;&nbsp;emitting a governance decision, selected from allow, review, quarantine, and deny, that controls whether the computational action is executed,

&nbsp;&nbsp;&nbsp;&nbsp;whereby the governance cost increases superexponentially as the embedded point approaches a boundary of the open unit ball, rendering adversarial deviation from the session centroid computationally prohibitive.

2. The method of claim 1, wherein the bounded hyperbolic space comprises a bounded non-Euclidean manifold other than a Poincaré ball.

3. The method of claim 1, wherein the hyperbolic distance is computed as `d_H = arccosh(1 + 2‖u − v‖² / ((1 − ‖u‖²)(1 − ‖v‖²)))`.

4. The method of claim 1, wherein the nonlinear cost function comprises one of: (i) a harmonic wall function `H(d, R) = R^(d²)` where R > 1; or (ii) a bounded reciprocal function `H = 1 / (1 + d + 2·pd)` where pd is a phase-deviation term.

5. The method of claim 1, wherein the additional governance signal comprises a six-axis semantic weighting system in which each semantic axis has a predetermined weight based on a power of the golden ratio and a predetermined phase offset.

### Amended Claim 9 (System)

9. A system for runtime governance of agentic or artificial-intelligence actions, the system comprising:

&nbsp;&nbsp;&nbsp;&nbsp;at least one processor; and

&nbsp;&nbsp;&nbsp;&nbsp;a non-transitory memory storing a persistent runtime state and storing instructions that, when executed by the at least one processor, cause the system to:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;classify a proposed action into a context representation;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;map the context representation into a point in a Poincaré ball model of a bounded hyperbolic space;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;measure a drift of the proposed action as a hyperbolic distance between the point and a trusted state, the trusted state comprising the persistent runtime state, and the persistent runtime state comprising at least a session centroid, a cumulative cost, and a query count;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;calculate a harmonic governance cost from the measured drift using a nonlinear cost function that increases as the measured drift increases;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;apply a decision gate to the harmonic governance cost and one or more auxiliary signals; and

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;route the proposed action according to a decision selected from at least allow, review, quarantine, and deny;

&nbsp;&nbsp;&nbsp;&nbsp;wherein the session centroid is updated from the points of prior proposed actions within a session, and wherein the persistent runtime state is restored after a process restart.

10. The system of claim 9, wherein a quarantine route applies a non-error containment state that limits subsequent execution resources, available tools, or outbound effects of the proposed action rather than treating the proposed action as a runtime crash.

11. The system of claim 9, wherein the system emits an audit receipt comprising at least the decision, the harmonic governance cost, one or more signal identifiers, and one or more decision-relevant metadata fields.

### Amended Claim 15 (Computer-Readable Medium)

15. A non-transitory computer-readable medium storing instructions that, when executed by one or more processors, cause the one or more processors to:

&nbsp;&nbsp;&nbsp;&nbsp;receive an input comprising source code or an identifier-containing input;

&nbsp;&nbsp;&nbsp;&nbsp;generate a re-encoded form of the input by applying a bijective encode operation followed by a decode operation that maps the input to a token sequence and back to a decoded input;

&nbsp;&nbsp;&nbsp;&nbsp;compute a first canonical abstract syntax tree (AST) representation of the input and a second canonical AST representation of the decoded input, each canonical AST representation comprising a content-derived fingerprint;

&nbsp;&nbsp;&nbsp;&nbsp;compute a tamper signal based on at least one of: (i) a divergence between the first canonical AST representation and the second canonical AST representation; (ii) a failure of the decoded input to parse into a valid AST; (iii) a Unicode canonicality failure; or (iv) a confusable-identifier condition in which every non-Latin codepoint of an identifier maps to an ASCII-confusable codepoint; and

&nbsp;&nbsp;&nbsp;&nbsp;provide the tamper signal to a governance gate configured to escalate or block a proposed computational action when the tamper signal exceeds a threshold,

&nbsp;&nbsp;&nbsp;&nbsp;wherein the tamper signal is distinct from a tokenizer reconstruction-quality measure in that the tamper signal is derived from a comparison of abstract syntax tree representations and gates execution of the proposed computational action.

16. The medium of claim 15, wherein the content-derived fingerprint comprises a SHA-256 hash of a canonical dump of the abstract syntax tree.

17. The medium of claim 15, wherein the governance gate denies the proposed computational action when the tamper signal indicates the decoded input fails to parse, and quarantines the proposed computational action when the tamper signal indicates the confusable-identifier condition.

18. The medium of claim 15, wherein the tamper signal and the governance decision are recorded in an audit trail.

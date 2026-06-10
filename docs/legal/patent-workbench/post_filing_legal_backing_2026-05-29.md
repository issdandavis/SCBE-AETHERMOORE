# SCBE-2026-0001 — Legal Backing for Red-Team Defense Positions
# App 19/691,526 — Internal prosecution-prep memo, not legal advice.

## Purpose

This document maps each attack surface from `post_filing_red_team_pass_1_2026-05-29.md`
to specific Federal Circuit holdings and MPEP sections that support the defense posture.
Citations confirmed via CourtListener (2026-05-29).

---

## I. §101 — Abstract Idea Attack

### The spine argument

SCBE should be argued as a **specific runtime execution-control pipeline that solves a
specific technological problem**: governing AI/agentic system actions against adversarial
behavioral drift, using bounded hyperbolic geometry to detect that drift and routing
execution through allow/review/quarantine/deny gates with durable persisted state and
tamper-detection artifacts.

This framing is not accidental. It mirrors the winning posture in the most directly
analogous Federal Circuit holding.

---

### Anchor case: SRI International, Inc. v. Cisco Systems, Inc.
**918 F.3d 1368 (Fed. Cir. 2019)**
CourtListener: /opinion/4601483/sri-international-inc-v-cisco-systems-inc/

SRI's claims covered network intrusion detection using multiple monitors analyzing
specific data types and integrating their reports. The district court had held the
claims patent-ineligible. The Federal Circuit reversed at **Alice Step 1** — it never
reached Step 2:

> "The claims are directed to using a **specific technique**—using a plurality of network
> monitors that each analyze **specific types of data** on the network and integrating
> reports from the monitors—to solve a **technological problem arising in computer
> networks**: identifying hackers or potential intruders into the network."
> *SRI Int'l, 918 F.3d at 1375.*

> "The district court concluded that the claims are more complex than merely reciting
> the performance of a known business practice on the Internet and are better understood
> as being **necessarily rooted in computer technology in order to solve a specific
> problem in the realm of computer networks**."
> *Id. (citing DDR Holdings, LLC v. Hotels.com, L.P., 773 F.3d 1245, 1257 (Fed. Cir. 2014)).*

**Mapping to SCBE claim 1:**

| SRI element | SCBE claim 1 element |
|---|---|
| Plurality of network monitors | Multi-layer pre-filter stack (claims 11) + hyperbolic distance gate |
| Analyze specific types of data | Context representation with semantic/operational/temporal features |
| Integrating reports | Composite risk value combining governance cost with auxiliary signals |
| Solve a problem in computer networks | Govern execution of AI/agentic actions against behavioral drift |
| Identify hackers | Detect adversarial intent, quarantine, or deny computational actions |

**The argument in a sentence:** SCBE claims are directed to using a specific technique —
embedding proposed actions in bounded hyperbolic space, measuring session-centroid drift,
and routing execution through a four-tier gate — to solve a technological problem in
AI/agentic systems: controlling execution when behavioral drift indicates adversarial
or misaligned action.

---

### Supporting case: Enfish, LLC v. Microsoft Corp.
**822 F.3d 1327 (Fed. Cir. 2016)**
CourtListener: /opinion/3203035/enfish-llc-v-microsoft-corporation/

Enfish held that claims directed to **a specific improvement to the way computers operate**
are not abstract under Step 1, regardless of the mathematical nature of the improvement:

> "We do not read Alice to broadly hold that all improvements in computer-related
> technology are inherently abstract and, therefore, must be considered at step two."
> *Enfish, 822 F.3d at 1335.*

> "The plain focus of the claims is on an improvement to computer functionality itself,
> not on economic or other tasks for which a computer is used in its ordinary capacity."
> *Id. at 1336.*

**SCBE application:** The plain focus of claims 1 and 9 is improving the **runtime
governance capability of AI/agentic systems** — not using a computer to perform an
abstract governance concept. The tanh-normalized Poincaré ball embedding with
epsilon clamping, session-centroid adaptive accumulation, and nonlinear cost function
are specific technical improvements to how the system measures and responds to behavioral
drift. These do not exist in prior AI safety or access-control systems.

---

### Supporting case: McRO, Inc. v. Bandai Namco Games America Inc.
**837 F.3d 1299 (Fed. Cir. 2016)**
CourtListener: /opinion/4255920/mcro-inc-v-bandai-namco-games-america-inc/

McRO held that claims reciting **specific mathematical rules** that produce a specific
technical result are not abstract merely because they involve math:

> "The claims here are limited to rules with specific characteristics... focused on
> a specific asserted improvement in computer animation."
> *McRO, 837 F.3d at 1315.*

> "We therefore look to whether the claims focus on a specific means or method that
> improves the relevant technology, or are instead directed to a result or effect
> that itself is the abstract idea and merely invokes generic processes and machinery."
> *Id. at 1314.*

**SCBE application:** Claims 2 and 3 recite specific mathematical formulas —
`d_H = arccosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))` (claim 2) and
`H(d,R) = R^(d²)` / `H = 1/(1+d+2*pd)` / `π^(φ·d)` (claim 3). These are not
generic math — they are the **specific means** by which adversarial cost scaling
is achieved in hyperbolic space. The exponential cost property near the Poincaré
ball boundary is a technical effect, not an abstract result.

**Caution:** Claims 3, 27, and 28 are the most vulnerable here. Under McRO's
"result vs. specific means" test, these dependents must be argued as specific
means, not just descriptions of what the math achieves.

---

### Step 2 fallback: BASCOM Global Internet Services, Inc. v. AT&T Mobility LLC
**827 F.3d 1341 (Fed. Cir. 2016)**
CourtListener: /opinion/3219555/bascom-global-internet-services-inc-v-att-mobility-llc/

If the examiner gets past Step 1 and asserts the claims are abstract, BASCOM provides
the Step 2 inventive-concept argument:

> "An inventive concept can be found in the **non-conventional and non-generic
> arrangement of known, conventional pieces**."
> *BASCOM, 827 F.3d at 1350.*

> "The inventive concept resides in the ordered combination of limitations... [which]
> allow[s] for specific, tailored filtering... rather than a more blunt, generic
> filtering approach."
> *Id.*

**SCBE application:** Even if each element (embeddings, distance metrics, access
control gates, session state) is individually known, their **ordered combination** in
SCBE is non-conventional:

1. tanh-normalized Poincaré embedding (not used in prior access control)
2. session-adaptive centroid with running-average update (specific state mgmt)
3. nonlinear hyperbolic cost function (specific mathematical relationship)
4. cheapest-reject-first pre-filter stack before geometry (specific ordering)
5. durable persisted state restored after restart (specific machine continuity)
6. fail-to-noise denial response (specific anti-disclosure behavior)
7. ML-DSA-65 / ML-KEM-768 audit receipts (specific post-quantum artifacts)

No prior system combines these elements. The ordered combination is the inventive
concept under BASCOM even if individual pieces are known.

---

### Step 2B factual inquiry: Berkheimer v. HP Inc.
**881 F.3d 1360 (Fed. Cir. 2018)**
CourtListener: /opinion/4466106/berkheimer-v-hp-inc/

Berkheimer established that the examiner cannot assert "well-understood, routine,
and conventional" without evidentiary support:

> "Whether something is well-understood, routine, and conventional to a skilled
> artisan at the time of the patent is a **factual determination**. Like any fact
> question, it must be proven by **clear and convincing evidence**."
> *Berkheimer, 881 F.3d at 1368.*

> "The mere fact that something is disclosed in a piece of prior art... does not mean
> it was well-understood, routine, and conventional."
> *Id.*

**SCBE application:** If the examiner asserts the Poincaré ball embedding, session
centroid, or nonlinear cost function are well-understood, routine, and conventional
in AI governance systems, that is a factual assertion requiring clear and convincing
evidence. The benchmark evidence packet (raw model vs. full gate, false-allow rates,
audit completeness) directly addresses this — it documents that these elements are
**not** conventional in deployed AI safety systems. Build this evidence before OA.

---

## II. §103 — Obviousness Attack

### Defense framework

The most likely combination: anomaly detection or behavioral analytics system (Ref A)
+ hyperbolic embedding paper, e.g., Nickel & Kiela (Ref B) + motivation: "improve
distance metrics."

**This combination fails for two reasons:**

**1. No motivation to use hyperbolic geometry for execution governance.**
Ref B (hyperbolic embedding papers) were developed for hierarchical data embedding in
knowledge graphs and taxonomy representation — not for adversarial cost scaling or
runtime execution control. A skilled person reading both references would not arrive
at session-centroid governance with execution routing. The **specific technical property
being exploited** — that adversarial drift costs exponentially more near the Poincaré
ball boundary due to the hyperbolic metric's divergence — does not appear in Ref B and
is not motivated by Ref A.

**2. Claim 24 (null-space anomaly) breaks any simple combination.**
Claim 24 detects inputs that deliberately mimic baseline behavior to **evade** the
governance cost — per-axis deviations all below threshold but cumulatively anomalous.
No anomaly detection system + hyperbolic embedding combination teaches this. It is
the specific adversarial model (baseline mimicry) that makes this element non-obvious.

**Key MPEP cite:** MPEP § 2143 requires a motivation to combine with a reasonable
expectation of success. The examiner must articulate *why* a skilled person would
combine hyperbolic geometry (from a knowledge-graph context) with runtime execution
governance (from an access control context) and arrive at the specific ordered
combination claimed.

---

## III. §112 — Written Description / Indefiniteness Attack

### Terms to pre-map to spec paragraphs before OA

| Term | Claim(s) | Defense / Spec anchor |
|---|---|---|
| "trajectory drift" | 1, 8 | = rate of change of successive hyperbolic distances across session requests. Map to spec para on session centroid evolution. |
| "harmonic governance cost" | 9 | "Harmonic" = from the harmonic wall cost functions defined in spec (H formulas). Argue "harmonic" is a defined term of art within the spec, not vague. |
| "nonlinear cost function that increases" | 1, 9 | Three specific species disclosed in claim 3. Functional claim language supported by disclosed structures. *In re Donaldson*, 16 F.3d 1189 (Fed. Cir. 1994) (en banc) — functional language permissible when adequately supported. |
| "N-predicate container" (claim 21) | 21 | Map to spec paragraphs on the five-predicate deferred authorization flowchart (FIG. 5). |
| "physics-based juggling model" (claim 25) | 25 | Translate: tasks = capsules with inertia, agent slots = hands with readiness, handoffs = throws with predicted catch windows. Map to spec section on fleet coordination. |
| "domain-specific entropy encoding" (claim 28) | 28 | Map to spec on bijective token alphabet construction — each byte maps uniquely to a token in that axis's vocabulary. |

**MPEP reference:** MPEP § 2173.05(b) — a claim term is not indefinite if "the
boundaries of the claim are determinable by reference to the specification."

**Glossary action item:** Replace coined names with examiner-language equivalents
in any response:

| Filed name | Prosecution language |
|---|---|
| Sacred Tongues | six-axis semantic weighting / disjoint token vocabularies |
| Sacred Egg | N-predicate authorization container |
| Fleet juggling scheduler | trajectory-based multi-agent task handoff coordinator |
| Harmonic wall | nonlinear hyperbolic governance cost function |

---

## IV. Evidence Packet Priority (Before OA)

Ordered by impact on prosecution:

1. **§101 evidence brief** — One page. Four bullet points: (a) claims control execution,
   not just classify; (b) quarantine state restricts tools without termination; (c)
   durable state persists and restores across restarts; (d) fail-to-noise response is
   a specific technical output, not an error code. No new matter — diagrams and code
   pointers only.

2. **Benchmark table** — Ground truth for Berkheimer Step 2B response. Corpus: prompt
   injection / Unicode confusable / benign developer requests. Controls: raw model,
   regex-only, full RuntimeGate. Metrics: false-allow rate, false-block rate, latency,
   SLM calls avoided, audit receipt completeness. This is the "not well-understood,
   routine, conventional" factual rebuttal.

3. **Claim support table** — For claims 12, 21, 23, 25, 28. Each claim element mapped
   to exact spec paragraph number (USPTO [XXXX] format) and code file+line. Purpose:
   §112(a) written description rebuttal, ready to file with response.

4. **Obviousness distinction brief** — One page per combination the examiner is likely
   to assert. Lead with the missing motivation to combine.

---

## V. Claim Family Priority for OA Response

If the examiner issues a restriction requirement, elect the **method claims (1–8, 21–24,
26–28)** first. Broadest scope; examiner must examine these. Pursue system (9–14) and
CRM (15–20) families in continuations.

If the examiner allows claim 15 before claim 1, that is a strong §101 signal —
the bijective tamper detection with AST comparison is the clearest practical-application
integration and the examiner may allow it first. Use that allowance as leverage in
arguing claim 1's practical application.

---

## VI. Citation Index

| Case | Citation | Holding used for |
|---|---|---|
| *Alice Corp. v. CLS Bank Int'l* | 573 U.S. 208 (2014) | Two-step framework baseline |
| *SRI Int'l, Inc. v. Cisco Sys., Inc.* | 918 F.3d 1368 (Fed. Cir. 2019) | Step 1 — specific technique for specific technological problem |
| *Enfish, LLC v. Microsoft Corp.* | 822 F.3d 1327 (Fed. Cir. 2016) | Step 1 — improvement to computer functionality itself |
| *McRO, Inc. v. Bandai Namco Games Am., Inc.* | 837 F.3d 1299 (Fed. Cir. 2016) | Step 1 — specific mathematical rules, not abstract result |
| *BASCOM Global Internet Servs., Inc. v. AT&T Mobility LLC* | 827 F.3d 1341 (Fed. Cir. 2016) | Step 2B — non-conventional ordered combination |
| *Berkheimer v. HP Inc.* | 881 F.3d 1360 (Fed. Cir. 2018) | Step 2B — factual inquiry, clear and convincing evidence |
| *DDR Holdings, LLC v. Hotels.com, L.P.* | 773 F.3d 1245 (Fed. Cir. 2014) | Rooted in computer technology |
| *In re Donaldson* | 16 F.3d 1189 (Fed. Cir. 1994) (en banc) | §112 functional language permissible with spec support |

| MPEP Section | Topic |
|---|---|
| MPEP § 2106 | Patent Subject Matter Eligibility |
| MPEP § 2106.04 | Identifying the Judicial Exception |
| MPEP § 2106.05 | Practical Application |
| MPEP § 2106.05(a) | Improvements to Computer Functionality |
| MPEP § 2143 | Obviousness — motivation to combine |
| MPEP § 2173.05(b) | Indefiniteness — claim terms defined by spec |

---

*Prepared 2026-05-29. Internal only. Not legal advice.*

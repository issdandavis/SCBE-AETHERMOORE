# Pre-Registration Protocol: Tesla-Valve / Asymmetric Pore Reynolds Validation

| Field | Value |
|-------|--------|
| **Title** | Directional Microchannel Diodicity — Reynolds-Matched Bench and Validated CFD |
| **Protocol ID** | `SCBE-TESLA-RE-v1` |
| **Status** | `DRAFT` → change to `FROZEN` only after all `[FREEZE: …]` fields are set |
| **Author** | Isaac D. Davis |
| **Date drafted** | 2026-06-01 |
| **Date frozen** | `[FREEZE: YYYY-MM-DD]` |
| **Background (non-binding)** | `docs/research/tesla_valve_reynolds_bench_cfd_test_plan_2026-06-01.md` |

---

## 0. Binding principle

**Geometry references, Reynolds targets, diodicity convention, control channels, success/pivot/kill thresholds, bench procedure, and CFD acceptance criteria are fixed in this document before any bench run or CFD job is launched.**

Positive or negative results **must not** retroactively change:

- the definition of \(D\),
- the target \(\mathrm{Re}\),
- which geometry “counts” as the invention,
- or the pivot narrative (§7).

A failed Tesla curve is a **registered outcome**, not a prompt to reinterpret the claim without a new protocol version.

---

## 1. Hypothesis and claim under test

**Physics hypothesis:**

> The frozen candidate microchannel geometry exhibits **useful forward/reverse asymmetry** (diodicity \(D > 1\)) at the **target transpiration-pore Reynolds number** derived from the actual coolant, pore size, and mass flux — not only at a convenient macro bench scale.

**Engineering claim (pre-registered):**

> At \(\mathrm{Re}_\text{target}\), the candidate’s diodicity **exceeds frozen thresholds** with uncertainty bounds that clear both straight and tapered controls, measured on a **Reynolds-matched bench** and reproduced by **validated CFD** within frozen tolerance.

**What this protocol is not:** flight certification, arc-jet proof, or manufacturing sign-off.

---

## 2. Frozen geometry and identifiers

| Item | Frozen value |
|------|----------------|
| **Candidate geometry ID** | `[FREEZE: e.g. tesla_pore_v3.stl]` |
| **Geometry SHA256** | `[FREEZE: hex]` |
| **Straight control ID** | `[FREEZE: straight_Dh_match.stl]` |
| **Tapered / labyrinth control ID** | `[FREEZE: tapered_Dh_match.stl]` |
| **Hydraulic diameter \(D_h\)** | `[FREEZE: value + unit]` |
| **Channel length \(L\)** | `[FREEZE: value + unit]` |
| **Wall roughness assumption** | `[FREEZE: e.g. smooth no-slip; or Ra]` |
| **CAD / revision tag** | `[FREEZE: git tag or drawing rev]` |

All three geometries share **matched** \(D_h\), \(L\), and inlet/outside area within `[FREEZE: tolerance %, e.g. 2%]` unless explicitly noted in an erratum.

---

## 3. Target Reynolds number (from application, not bench convenience)

### 3.1 Application-side freeze (micropore / TPS)

| Parameter | Symbol | Frozen value |
|-----------|--------|----------------|
| Coolant | — | `[FREEZE: e.g. water, RP-1, air]` |
| Temperature | \(T\) | `[FREEZE: K or °C]` |
| Density | \(\rho\) | `[FREEZE: kg/m³]` |
| Dynamic viscosity | \(\mu\) | `[FREEZE: Pa·s]` |
| Mean pore velocity | \(U\) | `[FREEZE: m/s from mass flux / porosity]` |
| Characteristic length | \(D_h\) or \(D_p\) | `[FREEZE: m]` |

```text
Re_target = rho * U * D_h / mu
```

| Derived | Value |
|---------|--------|
| **Re_target** | `[FREEZE: numeric]` |
| **Re bracket (sweep must include)** | `[FREEZE: Re_low, …, Re_high]` e.g. spanning 0.1× to 10× Re_target |

### 3.2 Secondary dimensionless groups (declare)

| Group | Match on bench? | Notes |
|-------|-----------------|-------|
| Mach | `[FREEZE: yes/no]` | If no, document incompressible assumption |
| Prandtl / heat transfer | `[FREEZE: N/A for cold isothermal gate]` | Hot-gas CFD is **out of scope** until §6 gate passes |
| Roughness | `[FREEZE:]` | LPBF vs ideal CAD |

---

## 4. Frozen metric definitions

### 4.1 Diodicity convention (pick one — freeze)

**Selected convention (check one):**

- [ ] **Pressure ratio (recommended):** \(D_P(Q) = \Delta P_\text{reverse}(|Q|) / \Delta P_\text{forward}(|Q|)\) at matched volumetric flow rate \(Q\)
- [ ] **Flow ratio:** \(D_Q(\Delta P) = Q_\text{forward}(|\Delta P|) / Q_\text{reverse}(|\Delta P|)\)

**Frozen choice:** `[FREEZE: D_P or D_Q]`

Report **both** in appendix only if `[FREEZE: yes/no]` — primary decision uses frozen choice only.

### 4.2 Primary curve

**Primary outcome:** \(D(\mathrm{Re})\) for candidate and both controls, not a single headline number.

| Requirement | Rule |
|-------------|------|
| Re points | Minimum `[FREEZE: e.g. 8]` points spanning §3.1 bracket |
| Must include | \(\mathrm{Re}_\text{target}\) ± `[FREEZE: e.g. 20%]` |
| Per point repeats | \(N \geq\) `[FREEZE: e.g. 5]` bench runs |
| Report | Mean \(D\), sample SD, 95% CI of mean (Student-t) or propagated instrument uncertainty — **freeze method:** `[FREEZE: t-interval / propagation]` |

### 4.3 Instrument uncertainty (freeze)

| Instrument | Model | Uncertainty |
|------------|-------|-------------|
| \(\Delta P\) sensor | `[FREEZE]` | `[FREEZE: ± value or % FS]` |
| Flow meter | `[FREEZE]` | `[FREEZE]` |
| Temperature | `[FREEZE]` | `[FREEZE]` |

Uncertainty propagation method: `[FREEZE: path to script + SHA]`

---

## 5. Dynamic-similarity bench (freeze matching, not channel size)

**Principle:** Bench may use **larger** \(D_h\) only if \(\mathrm{Re}_\text{bench} = \mathrm{Re}_\text{target}\) via adjusted \(U\), \(\rho\), or \(\mu\) (e.g. glycerin/water mix, regulated air, temperature control).

| Bench parameter | Frozen value |
|-----------------|--------------|
| Bench fluid | `[FREEZE]` |
| Bench \(D_h\) | `[FREEZE: m]` |
| Matching rule | \(\rho U D_h / \mu = \mathrm{Re}_\text{target}\) |
| Fixed \(Q\) or fixed \(\Delta P\) protocol | `[FREEZE: pick one primary; secondary in appendix]` |
| Leak test procedure | `[FREEZE: e.g. pressure hold 60 s < 1% drop]` |
| Block materials | `[FREEZE: resin / PLA / metal]` |

**Explicit limitation (pre-registered):** Macro bench success **does not** alone prove micro-TPS pore performance. It proves geometry **can** rectify at matched Re. **CFD at pore scale** (§6) is required for transpiration claims.

### 5.1 Run order (bench)

1. Straight control — forward/reverse at each Re point.
2. Tapered control — same.
3. Candidate — same.
4. No geometry edits between runs. If geometry changes, new protocol version.

---

## 6. CFD role and validation order (freeze)

**Order is mandatory:**

```text
Bench (Re-matched)  →  CFD at identical geometry + Re  →  CFD extrapolation (only if validated)
```

### 6.1 CFD frozen setup

| Item | Value |
|------|--------|
| Solver | `[FREEZE: OpenFOAM / SimScale / other]` |
| Physics (phase 1) | `[FREEZE: laminar, incompressible, isothermal]` |
| Turbulence model (if used) | `[FREEZE: none / SST / …]` — must be declared before runs |
| Mesh levels | coarse / medium / fine — `[FREEZE: cell counts or target y+]` |
| Convergence | Residuals `[FREEZE: e.g. 1e-5]`, mass imbalance `[FREEZE: e.g. <1%]` |

### 6.2 Mesh independence (pre-registered)

| Criterion | Threshold |
|-----------|-----------|
| Compare | \(\Delta P\) and \(D\) at \(\mathrm{Re}_\text{target}\) on coarse / medium / fine |
| Pass | Relative change in \(D\) between fine and medium `<` `[FREEZE: e.g. 5%]` |
| If fail | Do not extrapolate; refine or fix geometry — **no** threshold change |

### 6.3 Bench–CFD validation

CFD is **validated** for this geometry only if, at each Re point in `[FREEZE: validation Re list]`:

\[
|D_\text{CFD} - D_\text{bench}| / D_\text{bench} \leq \text{[FREEZE: e.g. 0.15]}
\]

**Extrapolation allowed only after validation:** Re points outside bench range but inside §3.1 bracket may be reported as **CFD-only** with label `EXTRAPOLATED`.

**CFD never overrides a failed bench** at \(\mathrm{Re}_\text{target}\) for PROCEED/KILL in §7.

---

## 7. Pre-registered success / pivot / kill thresholds

Use **lower uncertainty bound** for PROCEED and **upper bound** for KILL where applicable.

Let \(D_\text{cand}\) = candidate diodicity at \(\mathrm{Re}_\text{target}\) (bench-primary). Let \(D_0, D_t\) = straight and tapered controls.

| Outcome | Pre-registered rule |
|---------|---------------------|
| **PROCEED** | \(D_\text{cand} \geq\) `[FREEZE: e.g. 2.0]` **and** lower 95% bound `>` `[FREEZE: e.g. 1.5]` **and** \(D_\text{cand} - D_0 \geq\) `[FREEZE: e.g. 0.3]` with non-overlapping CIs vs straight **and** \(D_\text{cand} > D_t\) at same Re |
| **WEAK PROCEED** | `[FREEZE: e.g. 1.5 ≤ D < 2.0]` — keep as **dependent embodiment only**; no broad Tesla claim |
| **PIVOT** | \(D_\text{cand} <\) `[FREEZE: e.g. 1.2]` at Re_target **or** \(D_\text{cand} \approx D_t\) within frozen CI overlap **or** pressure penalty exceeds `[FREEZE: max ΔP % vs straight]` |
| **KILL (Tesla as load-bearing)** | \(D_\text{cand} < 1.2\) at Re_target (aligns with desk kill table) |

**Pre-committed pivot narrative (no motivated rewriting):**

On PIVOT/KILL, broad claim re-anchors to **non-Tesla** mechanisms frozen here:

1. Asymmetric compliant cell (Jansen / chevron / buckling — see mechanical coupon protocol).
2. Aperiodic / quasi-lattice pore field (layout optimization, not Tesla shape).
3. MEMS pressure telemetry + fail-closed FDIR (not geometry-only).

Tesla geometry may remain as **optional dependent** only if WEAK PROCEED.

---

## 8. Reporting (frozen deliverables)

### 8.1 Figures (required)

1. \(D(\mathrm{Re})\) — candidate vs straight vs tapered; error bars per §4.2.
2. Overlay: bench points + validated CFD at same Re.
3. \(\Delta P\) vs \(Q\) forward/reverse at \(\mathrm{Re}_\text{target}\) (raw triplicate spread).

### 8.2 Tables (required)

| Table | Content |
|-------|---------|
| T1 | Geometry IDs + SHA256 |
| T2 | Fluid properties and Re_target derivation |
| T3 | \(D\) at each Re — all three geometries |
| T4 | Bench vs CFD delta at validation Re |
| T5 | Decision outcome (PROCEED / WEAK / PIVOT / KILL) |

### 8.3 Raw data archive

| Artifact | Path |
|----------|------|
| Bench raw CSV | `[FREEZE: e.g. data/tesla_re_v1/bench/raw/]` |
| CFD case dirs | `[FREEZE:]` |
| Analysis notebook/script | `[FREEZE: path + SHA256]` |
| Photos / leak check log | `[FREEZE:]` |

### 8.4 Public language lock

Until PROCEED: use only:

> Directional microchannel geometry is a **candidate embodiment**. Diodicity at target transpiration Re is **not established** until protocol `SCBE-TESLA-RE-v1` completes.

---

## 9. Anti-gaming clauses

1. **No post-hoc Re definition** — Re_target computed from §3.1 before bench.
2. **No dropping outlier runs** — all \(N\) repeats count; equipment failures logged, not silently omitted.
3. **No CFD-before-bench** for decision §7.
4. **No geometry “tweak”** after seeing \(D(\mathrm{Re})\) — new STL → new protocol + new SHA.
5. **No switching D convention** after results.
6. **Agent constraint** — automation may run solvers and plot, not edit thresholds or Re_target.

---

## 10. Relationship to simulation artifacts in repo

Existing desk models (`scripts/research/tesla_valve_particle_sim.py`, `tesla_valve_3d_sim.py`) are **screening only**. They **cannot** satisfy this protocol.

Particle metrics may be cited as **hypothesis generation** only, with sentence:

> Particle/reduced model — not registered evidence under SCBE-TESLA-RE-v1.

---

## 11. Falsification

The directional-pore hypothesis for Tesla geometry is **falsified** under this protocol if:

- Bench \(D_\text{cand}(\mathrm{Re}_\text{target}) < 1.2\) (KILL), or
- Candidate does not beat straight control at \(\mathrm{Re}_\text{target}\) by frozen margin, or
- Validated CFD cannot match bench within §6.3 tolerance (invalidates extrapolation; bench outcome stands).

---

## 12. Freeze block (complete before bench or CFD)

```text
STATUS:                         FROZEN
DATE_FROZEN:                    ____________________
SIGNED:                         Isaac D. Davis
CANDIDATE_GEOMETRY_SHA256:      ________________________________________
STRAIGHT_CONTROL_SHA256:        ________________________________________
TAPERED_CONTROL_SHA256:         ________________________________________
Re_target:                      ________________________________________
D_METRIC_CONVENTION:            ________________________________________  (D_P or D_Q)
PROCEED_THRESHOLD_D:            ________________________________________
KILL_THRESHOLD_D:               ________________________________________
BENCH_ANALYSIS_SCRIPT_SHA256:   ________________________________________
CFD_ANALYSIS_SCRIPT_SHA256:     ________________________________________
PROTOCOL_SHA256:                ________________________________________  (sha256 of this file at freeze)
```

**After this block is signed:** bench and CFD execution may proceed. No edits to §1–§11 except errata with new SHA.

---

## Appendix A — Re_target worksheet (fill at freeze)

```text
rho   = __________ kg/m³
mu    = __________ Pa·s
U     = __________ m/s
D_h   = __________ m
Re    = rho * U * D_h / mu = __________
```

## Appendix B — Alignment with desk kill table

| Desk gate (`tesla_valve_reynolds_bench_cfd_test_plan`) | This protocol |
|--------------------------------------------------------|---------------|
| \(D < 1.2\) → pivot Tesla | KILL / PIVOT §7 |
| \(1.5 \leq D < 2.0\) → weak | WEAK PROCEED §7 |
| \(D \geq 2.0\) → serious embodiment | PROCEED §7 (with CI bars) |

Thresholds in §7 **must** be filled at freeze; defaults above are **suggestions**, not substitutes for signing §12.

## Appendix C — Bench Reynolds matching example (illustrative)

If \(\mathrm{Re}_\text{target} = 50\) at pore scale but bench \(D_h\) is 10× larger, hold \(\rho\) and \(\mu\) fixed and set \(U_\text{bench} = U_\text{target} / 10\). Verify with independent calculation before data collection.

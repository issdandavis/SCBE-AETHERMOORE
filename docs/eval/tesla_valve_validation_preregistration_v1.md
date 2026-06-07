# Tesla-Valve Pore Rectification — Reynolds-Matched Validation Pre-Registration Protocol

**Status:** PRE-REGISTRATION — frozen BEFORE any bench or CFD run is interpreted
**Protocol version:** v1.0
**Date frozen:** 2026-06-01
**Frozen by:** Issac D. Davis
**Binding rule:** Geometry, target Reynolds range, metric definition, and success/pivot thresholds are frozen below and may not change after the freeze date. A change requires a new version number.

---

## 0. Purpose and the open question

The disclosure's central novelty — directional (one-way) flow through Tesla-valve pores — rests on a diodicity that is **strongly Reynolds-number dependent and known to weaken at low Re**. Transpiration micropores operate at low Re. This protocol answers one question before anything more is built or claimed:

> **Does the frozen geometry rectify at the target operating Reynolds number?**

It pre-commits the pivot in case the answer is no. The prior `3.35×` figure is a kinematic-model result from `scripts/research/tesla_valve_particle_sim.py` and does **not** satisfy any tier of this protocol; it is screening, not evidence.

## 1. Frozen geometry — FREEZE

- Tesla-valve embodiment reference: `scripts/research/generate_invention_schematics.py` (Panel B), SHA-256 of that file frozen at commit `9dcec6af4e894473cc0e9f6ed01a3aa07f05579e`
- The geometry for bench fabrication is a 2D Tesla-valve cross-section scaled to macroscopic (mm-scale) dimensions for Re-matching per §4
- Characteristic length `L` (hydraulic diameter of main channel): **[FREEZE before fabrication — fill from CAD nominal]**
- Controls fabricated alongside, same `L` and nominal porosity:
  - **Straight channel** (reference for base Darcy resistance)
  - **Tapered channel** (geometric asymmetry without Tesla-valve topology)
  - Diodicity is only meaningful relative to these controls

## 2. Target Reynolds regime — FREEZE

`Re = ρVL/μ`. Fill from the real application, not from the bench convenience.

| Parameter | Value | Source |
|-----------|-------|--------|
| Coolant fluid | Water (initial bench) / candidate: SC-CO₂ (high-temp op) | TBD from UHTC stack thermal model |
| ρ (water, 20°C) | 998 kg/m³ | NIST |
| μ (water, 20°C) | 1.002 × 10⁻³ Pa·s | NIST |
| Pore characteristic length `L` | **[FREEZE: from SEM or CAD of micro-pore]** | |
| Through-pore velocity `V` | **[FREEZE: from mass flux ÷ porosity ÷ pore area]** | |
| **→ Target Re** | **[FREEZE: compute Re = ρVL/μ at operating conditions]** | |

**Engineering estimate (screening):** Transpiration micropores at ~1 mm diameter, coolant flow 1 g/s/cm²:
- V ~ 1 m/s (order of magnitude)
- Re ~ 998 × 1 × 0.001 / 0.001 ~ 1000

At Re ~ 1000, Tesla-valve diodicity is typically 1.5–2.5×. At Re < 100 (Darcy/creeping-flow regime), diodicity may collapse toward 1.0. The protocol freeze must confirm the actual operating Re before any positive claim is made.

**Critical gate:** If Re_target < 50 after filling in real application parameters, the Tesla-valve mechanism is likely insufficient in isolation. This triggers the §6 PIVOT immediately, before any bench fabrication.

## 3. Metric definition — FROZEN

- **Diodicity** `Di ≡ ΔP_reverse / ΔP_forward`, measured at matched volumetric flow rate `Q`, at a stated Re. (This convention: Di > 1 means higher resistance in reverse direction = preferential forward flow.)
- Report `Di` as a **curve over Re**, `Di(Re)`, spanning at least **Re = [Re_target/5] to [Re_target × 5]** and **including Re_target** — never a single number, because the entire question is how `Di` behaves as Re falls.
- Each `Di` point: mean ± 1σ over **N ≥ 5** repeated runs, with instrument uncertainty on each pressure gauge propagated.
- A result is only valid if: (a) flow is fully developed, (b) pressure taps are in the far-field of the valve, (c) temperature drift during the run is < 2°C.

## 4. Dynamic-similarity bench — FREEZE the matching, not the dimensions

A macro 3D-printed block on an air pump at ambient Re does **not** test the application physics. The bench must sit at `Re_target` by dynamic similarity:

- Choose bench fluid and flow rate so `ρVL/μ` on the bench equals `Re_target`
- Bench design parameters: **[FREEZE at design time]**
  - Bench fluid: (e.g., water with glycerol for lower Re, or scale up L to reduce needed V)
  - Bench `L` (scaled channel dimension): `[FREEZE]`
  - Bench `Q` (volumetric flow rate yielding Re_target): `[FREEZE]`
- Identical rig and measurement procedure for Tesla, straight, and tapered blocks
- For cold-bench pressure-drop test, Re is the governing dimensionless group (Mach number neglected at these velocities)

**Accessible local resource:** PNNL-Sequim is 25 min from Port Angeles and has materials characterization capability. Contact for CRADA on bench testing after provisional patent filing.

**Near-term fallback (no CRADA yet):** 3D-print a macro Tesla-valve block at 10× scale on water bench; sweep Re from 10 to 5000; extract Di(Re) curve; confirm Re_target falls on a di > 1.5 region.

## 5. CFD role — FREEZE the order

CFD is a model, not ground truth. Order is fixed:

1. **Run the bench first.** Results are primary evidence.
2. Run CFD at the same geometry and Re (laminar/k-ω SST depending on Re_target).
3. CFD is "validated" **only if** `Di(Re)` from CFD matches bench within **±20%** on the `Di` value.
4. Only a validated CFD may extrapolate to Re ranges or scales the bench cannot reach.

CFD must report:
- Mesh convergence study: ≥ 3 mesh densities; `Di` change between two finest < **5%**
- Turbulence/laminar model declaration and justification
- Reynolds number and boundary conditions matched to bench

**Bench anchors, sim extends — never the reverse.**

## 6. Pre-registered success / pivot thresholds — FROZEN

| Outcome | Condition |
|---------|-----------|
| **PROCEED** | `Di(Re_target) ≥ 1.8` with **lower error bar > 1.4**, on bench, beating both controls |
| **CONDITIONAL PROCEED** | `Di(Re_target) ≥ 1.4` with lower error bar > 1.2, AND validated CFD shows `Di ≥ 1.8` at a nearby Re within the operating envelope |
| **PIVOT** | `Di(Re_target) < 1.4`, OR `Di` is statistically indistinguishable from the tapered control within error |

**On PIVOT:** The invention re-anchors on the **Tesla-independent** mechanisms, which stand on their own evidence independent of Tesla-valve diodicity:
1. **Asymmetric compliant cell** — K_A/K_B = 2.744× stiffness ratio (PRB model validated to ±5.7% against theory; bench coupon ordered via DXF)
2. **Phi-graded aperiodic pore field** — spatial frequency distribution prevents resonant bypass
3. **MEMS field-control layer** — active pressure-biased micro-orifices as backup rectification mechanism

Thresholds are set now, before the curve exists, so an ugly curve cannot be reinterpreted into a pass.

## 7. Reporting format — FROZEN

For each block (Tesla, straight, tapered):
- `Di(Re)` curves on one axis with error bars (± 1σ)
- Bench vs. validated-CFD overlay (after CFD validation)
- Raw pressure/flow logs (CSV), instrument spec and uncertainty sheet, run count, rig photographs
- The decision-rule outcome (PROCEED / CONDITIONAL / PIVOT) stated against the frozen threshold
- Geometry hash and this protocol version

## 8. Freeze block

- Frozen by: Issac D. Davis  Date: 2026-06-01
- Geometry reference commit: `9dcec6af4e894473cc0e9f6ed01a3aa07f05579e`
- CAD geometry hash (fill before fabrication): `[FILL AT CAD FREEZE]`
- Re_target: `[FILL FROM APPLICATION MODEL]`
- Protocol version: v1.0

> No edits past this line. Any change requires a new version number.

---

## Appendix: Screening evidence (below threshold — does not satisfy this protocol)

| Evidence | Result | Status |
|----------|--------|--------|
| `tesla_valve_particle_sim.py` kinematic model | 3.35× rectification | Screening only — reduced particle model, not CFD/bench |
| `tesla_valve_3d_sim.py` Taichi 3D visualization | Qualitative trapping behavior | Interactive engineering visualization only |
| Bench coupon (DXF for spring strip stiffness test) | K_A/K_B = 2.744× (predicted) | SendCutSend order pending; tests compliant cell only, not Tesla valve |

None of the above satisfy §5 (CFD role) or §4 (dynamic-similarity bench). They are prior-art and design-iteration artifacts only.

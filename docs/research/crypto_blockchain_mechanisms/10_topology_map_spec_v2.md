# 10 — Topology Map Spec v2 (after the stress test)

Reconstructed from `SCBE_Topology_Map_Spec_v2.md` (423 lines). v1 changes are in
`CHANGELOG.md`, and the stress test that drove them is in 11.

**Purpose:** a map of venue state that tells the router (and the SCBE gate) where it
is safe to act and how sure the system should be about that.

## Layer (a) — Calculus trajectory plane
- Axes: **localization** (where the venue's state is: price, depth, latency) versus
  **confidence** (how fresh and well-reconciled that knowledge is).
- Each venue traces a **path** over time. Velocity and acceleration along the path
  are early warnings, for example confidence falling faster than usual.

## Layer (b) — Gradient stochastic arrays → contour lines with error bands
- Sampled venue metrics are interpolated into a surface and drawn as contours.
- **v2 change:** inverse distance weighting (IDW) is **replaced**:
  - **Radial basis functions (RBF)** give the surface itself better accuracy.
  - **Kriging** gives **per-cell error estimates** (kriging variance).
  - Reasons for dropping IDW: bull's-eye artifacts around sample points, no
    extrapolation beyond the data range, and sensitivity to outliers. This is a
    standard result in the geostatistics comparison literature (⚠ add specific
    comparison papers; the session said "every accuracy study").

## Layer (c) — Experiential signatures (not genetic)
- **v2 change:** v1 called venue clustering "genetic," as in shared founders or code
  lineage. That framing was dropped after the session discussed:
  > *"Group-level phenotypes are idiosyncratic yet unpredictable over development in a clonal fish,"* **Current Biology**, published 2026-09-18, [doi:10.1016/j.cub.2026.08.073](https://doi.org/10.1016/j.cub.2026.08.073).
  > Replicate groups of **genetically identical Amazon mollies** were tracked from birth for **55 days**. The groups' rank order **reshuffled around weeks 4–5** as social feedback grew. **Verified.** (Authors not recorded here — see DOI. Correction: the session called it "4 days old"; the actual publication date is Sept 18, 2026.)
- **Reframe:** venues "school" through **shared experience**: common incidents,
  shared liquidity providers, correlated outages. Shared DNA (same codebase or
  founders) is the weaker signal.
- `ExperientialSignature` weights **recent incident data above founder overlap**,
  with decay.

## Layer (d) — Projection field with cross-validated radius
Procedure:
1. Hold out **20%** of venue nodes.
2. Interpolate them from the remaining 80%. Record error as a function of distance to
   the nearest observed node.
3. Set the **projection radius** where error crosses tolerance.
4. Beyond that radius, mark the region **unknown**. Do not extrapolate.

Extrapolating into empty regions has no honest geostatistical solution. Kriging error
bars grow with distance, so the map should *show* that growth, not hide it.

## Layer (e) — Risk-path router
- Shortest path across a **dynamic graph**. Edge weights combine cost, latency, and
  (1 − confidence).
- **Baseline gate before routing:** if the 09 no-data check or an open break fails,
  routing never runs.

## Poincaré-ball option (hypothesis, gated by a falsification test)
- Idea: put venues in a Poincaré ball with **confidence as radial distance**. Decaying
  venues drift toward the boundary, pushed by SCBE's Harmonic Wall repulsion.
- **Falsification test:** embed the venue graph in the Poincaré ball **without**
  imposing radial confidence. Then check whether confidence **naturally correlates**
  with distance from the center.
  - If it does, the mapping is earned and we keep it.
  - If it doesn't, stay Euclidean.
- Caveat (session, from surveys of hyperbolic representation learning): radial
  organization is an **outcome of training, not a guarantee**.

## TDA backbone (regime-shift detection)
- Method: sliding-window point clouds → persistence diagrams/landscapes → norms that
  spike before regime shifts.
- Anchor references (well known, ⚠ verify details):
  - Gidea & Katz, "Topological data analysis of financial time series: Landscapes of crashes," *Physica A* 491 (2018).
  - Gidea, Goldsmith, Katz, Roldan, Shmalo, "Topological recognition of critical transitions in time series of cryptocurrencies," *Physica A* 548 (2020) — the Bitcoin-bubble work.
- Session claim: **6 independent papers (2017–2026)** report regime-shift signals
  **34–250 days** before crashes at **98% thresholds**. ⚠ **Session note — the paper
  list was lost with the artifacts. Rebuild it before citing these numbers.**

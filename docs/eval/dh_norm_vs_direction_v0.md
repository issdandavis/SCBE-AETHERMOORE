---
tags: [governance, d_H, runtime-gate, eval, null-discipline, petri]
updated_at: 2026-06-05
status: v0 finding (negative/methodological); harness ready for v1 + semantic path
---

# d_H norm-vs-direction honesty harness (v0)

Carries the prime-fog **null discipline** (every separation claim must beat its own
label-shuffle null) into the SCBE governance metric, to answer:

> Is the runtime text gate's "d_H" a genuine intent detector, or a magnitude /
> surface detector wearing geometric clothing?

Code: `scripts/eval/dh_norm_vs_direction.py` · Artifact: `artifacts/eval/dh_norm_vs_direction_v0.json`

## Decisive discovery (before any numbers)

The production text gate's operative cost is **not** the hyperbolic arcosh and **not**
origin-referenced. From `RuntimeGate._harmonic_cost`:

```text
weighted_dist = sqrt( sum_k phi^k * (coords_k - centroid_k)^2 )   # phi-weighted EUCLIDEAN
cost          = PI ** (PHI * min(weighted_dist, 5))               # R^(d^2)-style wall
reference     = a LEARNED running centroid (the gate's "normal"), not the origin
```

There are three different "d_H" surfaces in the repo (hyperbolic `PoincareLattice.distance`,
the pure-norm `hyperbolic_distance_from_origin`, and this phi-weighted-Euclidean-from-centroid).
**The text gate uses the last.** Verified (lines 1489–1544): its `cost` tier directly emits
`cost_deny` / `cost_quarantine` / `cost_elevated` signals, and any "deny" signal → DENY while
any "quarantine"/"elevated" → council review — so it is a *genuine co-equal decision input*,
**not** mere telemetry. But it is **one of several parallel signals** (classifier score,
trichromatic risk, spin magnitude, cumulative cost, regex reroute), several of which can
short-circuit the decision before the harmonic path — so it is not the *sole* gate. So
"norm vs direction" becomes:

> Does the gate separate adversarial/benign because adversarial coords are FARTHER from
> learned-normal (magnitude), or because they deviate in specific phi-weighted tongue
> DIRECTIONS (the geometry earns its keep)?

## Second decisive fact: the default coords are pure surface stats

`_text_to_coords_stats` is six surface features — `coord[1]` is literally
`word_count / 600`. So on the default path the gate **cannot** detect intent by
construction; it can only read a surface fingerprint. This is why the benign control
**must** be length-matched (it neutralizes `coord[1]`), and why the only intent-capable
path is the semantic (SentenceTransformer) one.

## Test design

- Adversarial: Petri 173 (all `training_blocked=True`; repo has **no** benign corpus).
- Benign: **synthetic, length-matched, v0** — explicitly an artifact-control, NOT a benign
  generalization benchmark (the agreed framing). Run in **two surface-texture variants**
  that share intent + length and differ only in lexical diversity / digit-presence.
- Metric mirrors the gate exactly (centroid = benign mean; `y = sqrt(phi) (x - c)`;
  magnitude `m = ||y||`; direction `u = y/||y||`).
- Three separations, each gated by a **label-shuffle null** (refit per shuffle to absorb
  fit-optimism): magnitude-only, direction-only (`|m` removed), full-6D.

## Why the benign contrast is load-bearing

The gate function is like a laser in empty space: the path exists, but without a
scattering medium you only see where it hits the detector. Here the detector is the
final runtime score. The contrast class is the medium.

```text
Petri adversarial beam
+ benign contrast field
+ shuffled-label null
+ length-matched controls
= visible separation geometry
```

Without benign examples, adversarial coordinates alone cannot prove whether a
trajectory is special. Distance and direction become underdetermined as evidence:
there is no background field to say what "normal" means. Synthetic benign is useful
in v0 only because it is controlled fog: it makes the path visible under known
conditions, then the two-variant instability check asks whether that visible path is
real geometry or merely the benign author's surface fingerprint.

## Result: the separation is a benign-author fingerprint, not a gate property

| axis | length_only AUC | surface_matched AUC | swing |
| --- | ---: | ---: | ---: |
| magnitude | 0.444 (null) | 0.819 (REAL) | **0.374 — verdict flip** |
| direction (\|m removed) | 0.872 (REAL) | 0.882 (REAL) | 0.010 |
| full_6d | 0.832 | 0.879 | 0.047 |

Read this honestly, axis by axis — both axes are surface artifacts, for two *different* reasons:

- **magnitude is texture-FRAGILE.** Changing only the benign generator's surface texture
  flips it from null (0.444) to strongly-REAL (0.819) — a verdict flip — and the carrier
  tongue **RU** (type-token ratio) sign-flips (`+0.107` low-diversity benign → `-0.082`
  high-diversity). A separation that flips when only the *control's* texture changes was
  never a property of the gate.
- **direction is texture-STABLE (0.872 → 0.882) — and that is *worse*, not better.** It
  separates *both* benign variants from Petri robustly because it is stably reading the
  **synthetic-vs-real authorship gap** (the carrier just relocates RU → DR punctuation).
  Two benign sets with *identical benign intent* both separate strongly from Petri, so the
  thing direction measures cannot be intent — it is authorship surface.

Length itself is neutralized throughout (`word_count_AUC ≈ 0.49`), so this is not the
length trap — it is the more general surface-fingerprint trap one level up.

**Conclusion (auto-emitted by the harness): SURFACE-ONLY by construction.** The stats coords
are pure surface statistics, so *no* axis on this path can encode intent regardless of the
AUCs — the experiment then corroborates it two ways (magnitude texture-fragility; direction
stably tracking authorship). The way to *strengthen* d_H is to feed it intent-bearing
(semantic) coordinates — not to tune the geometry.

## What is trustworthy vs not

- **Trustworthy:** the harness + null discipline (it correctly caught its own confound by
  the two-variant instability check — the same way the prime-fog circular-shift null killed
  `ratio_graph_resonance`). The structural facts (Euclidean-from-centroid, surface-only
  coords) are code-verified.
- **Not yet answerable here:** whether the gate carries real intent signal — that needs the
  **semantic path** and/or **real-harvested benign (v1)**. The semantic path is *deferred,
  not blocked*: it needs `sentence-transformers` (pulls torch), and this box has ~3.6 GB free
  — an OOM risk, not a missing capability. The harness runs the semantic path **automatically**
  wherever the dep exists, so the off-box route is one job away: HF Pro Jobs (l4x1/a10g) or
  Kaggle. That turns v0 from a negative result into "v1 is one `hf jobs run` away."

## Next (staged ladder)

1. **v0 (done):** synthetic length-matched artifact-control → surface-only, magnitude fragile.
2. **v1:** real-harvested benign traffic (removes the authoring artifact entirely).
3. **semantic path:** run off-box (HF Pro / Kaggle) — the only path that could show intent
   living in magnitude vs direction; harness already wired to run it where the dep is present.
4. **v2:** within-adversarial subtyping (Petri family structure) against a fixed safe anchor.

Optional, low-priority: re-run with the literal hyperbolic-arcosh-from-centroid (the L5 metric
the docs call "d_H") to match the user's literal wording — but since the *inputs* are surface-only,
the conclusion won't move.

Related: [[../../notes/prime-fog/solutions/prime spacetime atlas|prime atlas]] (same
truthful-by-construction + null discipline); governed-state map work.

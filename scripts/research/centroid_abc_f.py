"""Retrain centroid on A+B+C, test on F. Diagnose why model fails at F.

Questions answered:
  1. Does the A-only centroid produce any signal on F at all (pure centroid w=0)?
  2. At what blend weight does A-centroid maximize F hits?
  3. Does retraining on A+B+C improve F?
  4. What is the in-range F ceiling (dynamic blend search on F itself)?
  5. Feature drift: how much do the centroid feature weights shift A→ABC?

Training variants:
  cen_a   : fit on fit_a (60% of A=100M-150M)
  cen_abc : fit on all of A+B+C (no holdout — C is the last known range)

Validation proxy for weight search:
  Use D or E (neither is in ABC training set).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research.run_prime_search_engine_bench import (  # noqa: E402
    DEFAULT_ROW_CACHE_DIR,
    FEATURE_NAMES,
    apply_score_normalizer,
    build_or_load_rows,
    fit_centroid_ranker,
    fit_score_normalizer,
    fresh_rows,
    labels,
    linear_scores,
    matrix,
    metrics_for_scores,
    score_frozen,
    split_ordered_rows,
)
from scripts.research.run_field_branch_gate_search import (  # noqa: E402
    GateSpec,
    ensure_dynamic_profiles,
)

CACHE_DIR = DEFAULT_ROW_CACHE_DIR
OUT_DIR = REPO_ROOT / "artifacts" / "range_regime_classifier"

WINDOW, HISTORY, ANCHOR_THRESHOLD, TOP_N = 36, 12, 4.0, 20
FIT_FRACTION = 0.60


def _load_frozen_spec() -> GateSpec:
    p = REPO_ROOT / "artifacts" / "prime_search_engine_bench" / "latest_report.json"
    return GateSpec(**json.loads(p.read_text())["frozen_spec"])


def z(scores, mean, scale):
    return apply_score_normalizer(scores, mean, scale)


def sd(rows, scores):
    return {id(r): s for r, s in zip(rows, scores)}


def hits(rows, sc):
    return metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)["unique_anchor_hits"]


def hits_total(rows, sc):
    m = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
    return m["unique_anchor_hits"], m["unique_anchors_total"]


def anchor_set(rows, sc):
    m = metrics_for_scores(rows, sc, TOP_N, unique_anchors_only=True)
    return {h["anchor_prime"] for h in m["hidden_numbers"]}


def blend2(frz_z, fill_z, w):
    wb = 1.0 - w
    return [w * f + wb * c for f, c in zip(frz_z, fill_z)]


def dyn_blend(frz_z, cen_z, wf, wa, wc):
    return [wf * f + wa * abs(f) + wc * c for f, c in zip(frz_z, cen_z)]


def search_w(rows, frz_z, fill_z, grid=None):
    if grid is None:
        grid = [-1.5, -1.0, -0.5, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    best_h, best_w = -1, 0.5
    for w in grid:
        h = hits(rows, sd(rows, blend2(frz_z, fill_z, w)))
        if h > best_h:
            best_h, best_w = h, w
    return best_w, best_h


def search_dyn(rows, frz_z, cen_z):
    WF = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
    WA = [0.0, 0.5, 1.0, 1.5, 2.0]
    WC = [0.5, 1.0, 1.5, 2.0]
    best_h, best = -1, (0.0, 0.0, 1.0)
    for wf in WF:
        for wa in WA:
            for wc in WC:
                h = hits(rows, sd(rows, dyn_blend(frz_z, cen_z, wf, wa, wc)))
                if h > best_h:
                    best_h, best = h, (wf, wa, wc)
    return *best, best_h


def top_weights(model, k=12):
    return sorted(zip(FEATURE_NAMES, model.weights), key=lambda x: abs(x[1]), reverse=True)[:k]


def main():
    ensure_dynamic_profiles()
    frozen_spec = _load_frozen_spec()
    print(f"Frozen spec: {frozen_spec.spec_id}")

    print("\nLoading caches A-F...", flush=True)
    r100 = build_or_load_rows(100_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    r150 = build_or_load_rows(150_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    r200 = build_or_load_rows(200_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    r250 = build_or_load_rows(250_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    r300 = build_or_load_rows(300_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    r350 = build_or_load_rows(350_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)
    r400 = build_or_load_rows(400_000_000, WINDOW, HISTORY, ANCHOR_THRESHOLD, CACHE_DIR, True)

    rA = fresh_rows(r100, r150)
    rB = fresh_rows(r150, r200)
    rC = fresh_rows(r200, r250)
    rD = fresh_rows(r250, r300)
    rE = fresh_rows(r300, r350)
    rF = fresh_rows(r350, r400)

    # Frozen baseline
    frz_fit_a, _ = split_ordered_rows(rA, FIT_FRACTION)
    frz_fit_s = score_frozen(frz_fit_a, frozen_spec)
    frz_mn, frz_sc = fit_score_normalizer(frz_fit_s)

    def frz_z(rows):
        return z(score_frozen(rows, frozen_spec), frz_mn, frz_sc)

    fzA, fzB, fzC, fzD, fzE, fzF = frz_z(rA), frz_z(rB), frz_z(rC), frz_z(rD), frz_z(rE), frz_z(rF)

    frz_set = {}
    for label, rows, fz in [("A", rA, fzA), ("B", rB, fzB), ("C", rC, fzC),
                              ("D", rD, fzD), ("E", rE, fzE), ("F", rF, fzF)]:
        m = metrics_for_scores(rows, sd(rows, fz), TOP_N, unique_anchors_only=True)
        frz_set[label] = {h["anchor_prime"] for h in m["hidden_numbers"]}
        print(f"  frozen {label}: {m['unique_anchor_hits']}/{m['unique_anchors_total']}")

    # ── Model A: centroid trained on fit_a only ────────────────────────────
    print("\n[Model A] Centroid on fit_a (60% of A)...", flush=True)
    fit_a, _ = split_ordered_rows(rA, FIT_FRACTION)
    cen_a = fit_centroid_ranker(matrix(fit_a), labels(fit_a))
    cen_a_fit_s = linear_scores(cen_a, matrix(fit_a))
    ca_mn, ca_sc = fit_score_normalizer(cen_a_fit_s)

    def cen_a_z(rows):
        return z(linear_scores(cen_a, matrix(rows)), ca_mn, ca_sc)

    czA_a, czB_a, czC_a, czD_a, czE_a, czF_a = (
        cen_a_z(rA), cen_a_z(rB), cen_a_z(rC), cen_a_z(rD), cen_a_z(rE), cen_a_z(rF))

    # Pure centroid (w=0) on each range — no frozen involved
    print("  Pure centroid (w=0):")
    for label, rows, cz, fz_set in [("A_holdout", None, None, None),
                                     ("B", rB, czB_a, frz_set["B"]),
                                     ("C", rC, czC_a, frz_set["C"]),
                                     ("D", rD, czD_a, frz_set["D"]),
                                     ("E", rE, czE_a, frz_set["E"]),
                                     ("F", rF, czF_a, frz_set["F"])]:
        if rows is None:
            continue
        m = metrics_for_scores(rows, sd(rows, cz), TOP_N, unique_anchors_only=True)
        new = sorted({h["anchor_prime"] for h in m["hidden_numbers"]} - fz_set)
        h_, tot = m["unique_anchor_hits"], m["unique_anchors_total"]
        frz_h = len(fz_set)
        print(f"    {label}: hits={h_}/{tot}  delta_frozen={h_-frz_h:+d}  new_vs_frozen={new}")

    # Weight sweep on F with Model A
    print("\n  Model A weight sweep on F:")
    WS = [-1.5, -1.0, -0.5, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    f_frz_h = len(frz_set["F"])
    for w in WS:
        h_ = hits(rF, sd(rF, blend2(fzF, czF_a, w)))
        marker = " ←" if w == 0.5 else ("  " if w != 0.0 else "  [pure centroid]")
        print(f"    w={w:+.1f}: F={h_}/231  delta={h_-f_frz_h:+d}{marker}")

    # Dynamic blend on F (in-sample ceiling)
    wf_f, wa_f, wc_f, h_f_opt = search_dyn(rF, fzF, czF_a)
    print(f"\n  Model A dyn blend F in-sample ceiling: {h_f_opt}/231  wf={wf_f:+.1f} wa={wa_f:.1f} wc={wc_f:.1f}")

    # ── Model ABC: centroid trained on A+B+C ───────────────────────────────
    print("\n[Model ABC] Centroid on A+B+C (no holdout)...", flush=True)
    rABC = rA + rB + rC
    xABC = matrix(rABC)
    yABC = labels(rABC)
    print(f"  Training set: {len(rABC)} rows  positives={sum(yABC)}")
    cen_abc = fit_centroid_ranker(xABC, yABC)

    # Normalise using A scores (same fit reference for fair comparison)
    cen_abc_fit_s = linear_scores(cen_abc, matrix(rA))
    abc_mn, abc_sc = fit_score_normalizer(cen_abc_fit_s)

    def cen_abc_z(rows):
        return z(linear_scores(cen_abc, matrix(rows)), abc_mn, abc_sc)

    czD_abc, czE_abc, czF_abc = cen_abc_z(rD), cen_abc_z(rE), cen_abc_z(rF)

    # Validate on D and E (both held-out from ABC)
    w_d, h_d = search_w(rD, fzD, czD_abc)
    w_e, h_e = search_w(rE, fzE, czE_abc)
    print(f"  D validation: best_w={w_d:+.1f}  hits={h_d}/220  frozen={len(frz_set['D'])}")
    print(f"  E validation: best_w={w_e:+.1f}  hits={h_e}/224  frozen={len(frz_set['E'])}")

    # Weight sweep on F with Model ABC
    print("\n  Model ABC weight sweep on F:")
    for w in WS:
        h_ = hits(rF, sd(rF, blend2(fzF, czF_abc, w)))
        new = sorted(anchor_set(rF, sd(rF, blend2(fzF, czF_abc, w))) - frz_set["F"])
        marker = " ←" if w == 0.5 else ""
        print(f"    w={w:+.1f}: F={h_}/231  delta={h_-f_frz_h:+d}  new={new}{marker}")

    # Dynamic blend on F with Model ABC
    wf_f_abc, wa_f_abc, wc_f_abc, h_f_opt_abc = search_dyn(rF, fzF, czF_abc)
    print(f"\n  Model ABC dyn blend F in-sample: {h_f_opt_abc}/231  wf={wf_f_abc:+.1f} wa={wa_f_abc:.1f} wc={wc_f_abc:.1f}")

    # Best ABC result on F
    w_f_abc, h_f_abc = search_w(rF, fzF, czF_abc)
    new_f_abc = sorted(anchor_set(rF, sd(rF, blend2(fzF, czF_abc, w_f_abc))) - frz_set["F"])
    print(f"  Model ABC best linear blend on F: w={w_f_abc:+.1f}  hits={h_f_abc}/231  delta={h_f_abc-f_frz_h:+d}  new={new_f_abc}")

    # ── Feature weight drift: how much do the top weights shift? ─────────
    print("\n[Feature drift] Top weights: Model A vs Model ABC")
    wa_top = dict(top_weights(cen_a, 15))
    wabc_top = dict(top_weights(cen_abc, 15))
    all_feats = sorted(set(wa_top) | set(wabc_top), key=lambda f: abs(wa_top.get(f, 0)), reverse=True)
    print(f"  {'feature':40s}  {'cen_a':>8}  {'cen_abc':>8}  {'drift':>8}")
    for f in all_feats[:15]:
        va = wa_top.get(f, 0.0)
        vb = wabc_top.get(f, 0.0)
        print(f"  {f:40s}  {va:+8.4f}  {vb:+8.4f}  {vb-va:+8.4f}")

    # ── Why F is hard: froze gate already captures signal ─────────────────
    print("\n[F analysis] Overlap between centroid top-20 and frozen top-20:")
    sc_f_frz = sd(rF, fzF)
    sc_f_cen_a = sd(rF, czF_a)
    sc_f_cen_abc = sd(rF, czF_abc)
    m_frz = metrics_for_scores(rF, sc_f_frz, TOP_N, unique_anchors_only=True)
    m_cen_a = metrics_for_scores(rF, sc_f_cen_a, TOP_N, unique_anchors_only=True)
    m_cen_abc = metrics_for_scores(rF, sc_f_cen_abc, TOP_N, unique_anchors_only=True)

    set_frz = {h["anchor_prime"] for h in m_frz["hidden_numbers"]}
    set_cen_a = {h["anchor_prime"] for h in m_cen_a["hidden_numbers"]}
    set_cen_abc = {h["anchor_prime"] for h in m_cen_abc["hidden_numbers"]}

    frz_total = m_frz["unique_anchors_total"]
    print(f"  Frozen TOP-20 anchors:    {len(set_frz)}/{frz_total}")
    print(f"  Centroid-A TOP-20 anchors:{len(set_cen_a)}/{frz_total}")
    print(f"  Centroid-ABC TOP-20:      {len(set_cen_abc)}/{frz_total}")
    print(f"  Frozen ∩ Cen-A:           {len(set_frz & set_cen_a)}")
    print(f"  Frozen ∩ Cen-ABC:         {len(set_frz & set_cen_abc)}")
    print(f"  Cen-A unique (not in frz):{sorted(set_cen_a - set_frz)}")
    print(f"  Cen-ABC unique (not in frz):{sorted(set_cen_abc - set_frz)}")
    print(f"  Frozen unique (not in cen-a):{sorted(set_frz - set_cen_a)}")
    print(f"  Frozen unique (not in cen-abc):{sorted(set_frz - set_cen_abc)}")

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n[Summary]")
    print(f"  Frozen baseline F:         {f_frz_h}/231")
    print(f"  Cen-A best blend on F:     {search_w(rF, fzF, czF_a)[1]}/231  w={search_w(rF, fzF, czF_a)[0]:+.1f}")
    print(f"  Cen-A pure centroid F:     {hits(rF, sd(rF, czF_a))}/231")
    print(f"  Cen-ABC best blend on F:   {h_f_abc}/231  w={w_f_abc:+.1f}")
    print(f"  Cen-ABC pure centroid F:   {hits(rF, sd(rF, czF_abc))}/231")
    print(f"  Cen-A dyn in-sample F:     {h_f_opt}/231  (wf={wf_f:+.1f} wa={wa_f:.1f} wc={wc_f:.1f})")
    print(f"  Cen-ABC dyn in-sample F:   {h_f_opt_abc}/231  (wf={wf_f_abc:+.1f} wa={wa_f_abc:.1f} wc={wc_f_abc:.1f})")


if __name__ == "__main__":
    main()

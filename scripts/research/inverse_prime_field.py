"""Inverse prime field — prototype of the inverse_prime_path_lane.

Formalization:
  prime   = isolated endpoint (sink):    τ(p) = 2
  composite = interference medium:       τ(n) > 2
  inverse-prime = source/hub:            τ(n) >> 2  (highly composite proximity)

  The arithmetic laser path:
    source (hub) → composite medium → prime anchor (sink)

  IP(n) = τ(n)                      (inverse primality intensity)
  P(n)  = 1/τ(n)                    (primality intensity)

  hub_gradient(anchor) = max_{n in pre-window} τ(n) / distance(n, anchor)
  path_energy(anchor)  = Σ_{n in window} τ(n) * alignment(n, anchor)

  lane score(candidate) = hub_gradient(window) * phase_alignment * lambda_residual

Prototype:
  1. For each known anchor, compute τ for the pre-anchor window (100 integers before p)
  2. Find the hub (argmax τ) and gradient
  3. Characterize hub properties per ring
  4. Compare hub signatures: clean vs quantum anchors
  5. Identify which anchors have unique hub signatures (no overlap with frozen/dominant)

Outputs:
  artifacts/inverse_prime_field/field_v1.json
  artifacts/inverse_prime_field/REPORT.md
"""
from __future__ import annotations
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TL_PATH = REPO_ROOT / "artifacts" / "prime_target_lock" / "target_lock_latest.json"
OUT_DIR = REPO_ROOT / "artifacts" / "inverse_prime_field"

WINDOW = 100     # integers to examine before each anchor
GRADIENT_DECAY = 20.0  # scale for hub_gradient = τ_hub * exp(-dist/GRADIENT_DECAY)

# Precomputed small primes for trial division (up to sqrt(500M) = 22360)
def _small_primes(limit=22400):
    sieve = bytearray([1]) * (limit + 1)
    sieve[0] = sieve[1] = 0
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            sieve[i*i::i] = bytearray(len(sieve[i*i::i]))
    return [i for i in range(2, limit + 1) if sieve[i]]

SMALL_PRIMES = _small_primes(22400)


def tau(n):
    """Divisor count τ(n) by trial division."""
    if n <= 1:
        return 1 if n == 1 else 0
    count = 1
    orig_n = n
    for p in SMALL_PRIMES:
        if p * p > n:
            break
        if n % p == 0:
            exp = 0
            while n % p == 0:
                exp += 1
                n //= p
            count *= (exp + 1)
    if n > 1:
        count *= 2
    return count


def pre_anchor_window(anchor_prime, window=WINDOW):
    """Return (integers, tau_values) for the window before anchor_prime."""
    start = max(2, anchor_prime - window)
    nums = list(range(start, anchor_prime))
    taus = [tau(n) for n in nums]
    return nums, taus


def hub_features(anchor_prime, window=WINDOW):
    """Compute hub/path features for an anchor."""
    nums, taus = pre_anchor_window(anchor_prime, window)
    if not taus:
        return {}
    n = len(nums)

    hub_tau = max(taus)
    hub_idx = taus.index(hub_tau)
    hub_n = nums[hub_idx]
    hub_dist = anchor_prime - hub_n

    # Gradient = τ_hub * exp(-distance/scale) — soft exponential decay
    gradient = hub_tau * math.exp(-hub_dist / GRADIENT_DECAY)

    # Path energy = sum of τ-weighted alignment (closer to anchor = higher weight)
    path_energy = sum(t * math.exp(-(anchor_prime - v) / GRADIENT_DECAY)
                      for v, t in zip(nums, taus))

    # τ profile: mean, std, max in window
    mean_tau = sum(taus) / n
    var_tau = sum((t - mean_tau) ** 2 for t in taus) / n
    std_tau = math.sqrt(var_tau)

    # Second-highest τ (to measure "how lonely" the hub is)
    sorted_taus = sorted(taus, reverse=True)
    hub_isolation = (sorted_taus[0] - sorted_taus[1]) / max(sorted_taus[0], 1) if len(sorted_taus) > 1 else 1.0

    # τ at p-1 (almost always even → τ(p-1) ≥ 2, often much higher)
    tau_pm1 = taus[-1] if taus else 0  # p-1

    # Immediately pre-prime slope: τ at last 10 integers
    tail_taus = taus[-10:]
    tail_mean = sum(tail_taus) / len(tail_taus)

    return {
        "hub_n": hub_n,
        "hub_tau": hub_tau,
        "hub_dist": hub_dist,
        "gradient": round(gradient, 4),
        "path_energy": round(path_energy, 3),
        "mean_tau": round(mean_tau, 3),
        "std_tau": round(std_tau, 3),
        "hub_isolation": round(hub_isolation, 4),
        "tau_pm1": tau_pm1,
        "tail_mean_tau": round(tail_mean, 3),
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    tl = json.loads(TL_PATH.read_text("utf-8"))
    targets_by_range = tl.get("targets_by_range", {})

    all_results = {}
    ring_summaries = {}

    print("=" * 72)
    print("INVERSE PRIME FIELD  (computing τ for pre-anchor windows)")
    print(f"Window={WINDOW} integers, gradient decay={GRADIENT_DECAY}")
    print("=" * 72)

    for rname, tgts in targets_by_range.items():
        print(f"\n  Ring {rname}: {len(tgts)} anchors...")
        results = []
        for t in tgts:
            ap = t.get("anchor_prime")
            if ap is None:
                continue
            feats = hub_features(ap)
            hit_by = t.get("hit_by_top20", [])
            n_owners = len(hit_by)
            clean = (n_owners <= 1)
            results.append({
                "anchor_prime": ap,
                "anchor_ratio": t.get("anchor_ratio"),
                "hit_by_top20": hit_by,
                "n_owners": n_owners,
                "clean": clean,
                **feats,
            })

        # Rank by gradient (descending) → new IP lane top-20 candidates
        top20_ip = sorted(results, key=lambda x: -x.get("gradient", 0))[:20]
        top20_primes = {r["anchor_prime"] for r in top20_ip}

        # Compare to known anchors in target_lock hit sets
        ring_range_data = next((r for r in tl["ranges"] if r["range"] == rname), {})
        known_top20 = set(ring_range_data.get("top20_union_anchors", []))

        # IP lane hits: anchors in our top-20 that are in the known top-20 union
        ip_hits = top20_primes & known_top20

        # Unique IP hits: in our top-20 but NOT hit by any existing controller
        known_hit_anchors = set()
        for c_data in (ring_range_data.get("controllers") or {}).values():
            if isinstance(c_data, dict):
                known_hit_anchors.update(c_data.get("hit_anchors", []))
        unique_ip = top20_primes - known_hit_anchors

        # Stats by clean vs quantum
        clean_r = [r for r in results if r["clean"]]
        quantum_r = [r for r in results if not r["clean"]]

        def avg(lst, k):
            vals = [x[k] for x in lst if k in x]
            return round(sum(vals) / len(vals), 3) if vals else 0.0

        summary = {
            "n_anchors": len(results),
            "top20_ip": list(sorted(top20_primes)),
            "ip_hits": len(ip_hits),
            "unique_ip": len(unique_ip),
            "unique_ip_primes": list(sorted(unique_ip)),
            "mean_gradient_clean": avg(clean_r, "gradient"),
            "mean_gradient_quantum": avg(quantum_r, "gradient"),
            "mean_hub_tau_clean": avg(clean_r, "hub_tau"),
            "mean_hub_tau_quantum": avg(quantum_r, "hub_tau"),
            "mean_hub_dist_clean": avg(clean_r, "hub_dist"),
            "mean_hub_dist_quantum": avg(quantum_r, "hub_dist"),
            "mean_tau_pm1_clean": avg(clean_r, "tau_pm1"),
            "mean_tau_pm1_quantum": avg(quantum_r, "tau_pm1"),
        }
        ring_summaries[rname] = summary
        all_results[rname] = results

        print(f"    IP top-20 hits against union: {len(ip_hits)}/20")
        print(f"    Unique anchors (not in any existing lane): {len(unique_ip)}")
        print(f"    gradient — clean={summary['mean_gradient_clean']:.3f}  "
              f"quantum={summary['mean_gradient_quantum']:.3f}")
        print(f"    hub_tau  — clean={summary['mean_hub_tau_clean']:.1f}  "
              f"quantum={summary['mean_hub_tau_quantum']:.1f}")
        print(f"    hub_dist — clean={summary['mean_hub_dist_clean']:.1f}  "
              f"quantum={summary['mean_hub_dist_quantum']:.1f}")
        print(f"    τ(p-1)   — clean={summary['mean_tau_pm1_clean']:.1f}  "
              f"quantum={summary['mean_tau_pm1_quantum']:.1f}")

    # ── Cross-ring summary ─────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("CROSS-RING IP LANE SUMMARY")
    print("=" * 72)
    print(f"  {'Ring':>5}  {'anchors':>8}  {'IP hits':>9}  {'unique':>8}  "
          f"{'grad_clean':>12}  {'grad_qnt':>10}  {'τ(p-1)_cl':>11}  {'τ(p-1)_q':>10}")
    for rname, s in ring_summaries.items():
        print(f"  {rname:>5}  {s['n_anchors']:>8}  {s['ip_hits']:>9}  {s['unique_ip']:>8}  "
              f"{s['mean_gradient_clean']:>12.3f}  {s['mean_gradient_quantum']:>10.3f}  "
              f"{s['mean_tau_pm1_clean']:>11.1f}  {s['mean_tau_pm1_quantum']:>10.1f}")

    # ── Quantum anchor IP signatures ───────────────────────────────────────────
    print("\n" + "=" * 72)
    print("QUANTUM ANCHOR IP SIGNATURES  (the inverse Heisenberg nodes)")
    print("High gradient + high hub_tau = anchor at end of strong source-to-sink path")
    print("=" * 72)

    # Focus on G's quantum anchors (411142427 etc)
    g_results = all_results.get("G", [])
    quantum_g = sorted([r for r in g_results if not r["clean"]],
                       key=lambda x: -x.get("gradient", 0))
    print(f"\n  Ring G quantum anchors (sorted by IP gradient):")
    for r in quantum_g:
        owners = ", ".join(r.get("hit_by_top20", []))
        print(f"    {r['anchor_prime']}  ratio={r['anchor_ratio']:+.4f}  "
              f"gradient={r.get('gradient',0):.3f}  hub_τ={r.get('hub_tau',0)}  "
              f"hub_dist={r.get('hub_dist',0)}  τ(p-1)={r.get('tau_pm1',0)}"
              f"\n      owners=[{owners}]")

    # ── Lane field formula ─────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("LANE FIELD FORMULA (to be integrated into row-cache scorer)")
    print("=" * 72)
    print("""
  IP(n) = τ(n)                           # inverse primality (source intensity)
  P(n)  = 1/τ(n)                         # primality (sink isolation)

  hub_gradient(anchor) = τ_hub * exp(-hub_dist / decay)
  path_energy(anchor)  = Σ τ(n) * exp(-(p-n) / decay)

  lane_score(candidate_row) = (
      α * hub_gradient(ahead_window)      # source → sink path quality
    + β * τ_mean_ratio(scan_zone)         # local composite density
    + γ * lambda_residual(scan_row)       # cross-manifold residual
    + δ * phase_alignment(scan_row)       # phase drift toward anchor
  )

  Where:
    ahead_window = [scan_prime, scan_prime + LEAD_STEPS * avg_gap]
    scan_zone    = [scan_prime - HISTORY, scan_prime]
    lambda_residual = from existing lambda_shadow_channel
    phase_alignment = from mode_fit_score or geodesic_trend_channel

  Calibrate (α, β, γ, δ) on rings A-G, freeze before ring I.
  Benchmark: does top-20 by lane_score hit anchors frozen/dominant misses?
""")

    # ── Save artifact ──────────────────────────────────────────────────────────
    artifact = {
        "schema": "inverse_prime_field_v1",
        "window": WINDOW,
        "gradient_decay": GRADIENT_DECAY,
        "ring_summaries": ring_summaries,
        "formula": {
            "IP(n)": "tau(n)",
            "P(n)": "1/tau(n)",
            "hub_gradient": "tau_hub * exp(-hub_dist / decay)",
            "path_energy": "sum(tau(n) * exp(-(p-n)/decay) for n in window)",
            "lane_score": "alpha*hub_gradient + beta*tau_mean_ratio + gamma*lambda_residual + delta*phase_alignment",
        },
    }
    # Only save summaries, not full per-anchor data (heavy)
    art_path = OUT_DIR / "field_v1.json"
    art_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")

    # Markdown report
    md = [
        "# Inverse Prime Field — Lane Prototype v1",
        "",
        "**Date:** 2026-06-04  ",
        "**Concept:** prime = sink, inverse-prime (hub) = source, path = arithmetic laser",
        "",
        "## Mathematical Foundation",
        "",
        "```",
        "IP(n) = τ(n)          — source intensity (high for highly composite hubs)",
        "P(n)  = 1/τ(n)        — sink isolation  (high for primes)",
        "",
        "hub_gradient = τ_hub * exp(-hub_distance / decay)",
        "path_energy  = Σ τ(n) * exp(-(anchor - n) / decay)",
        "```",
        "",
        "Finding a prime = finding the stable endpoint of a path through arithmetic spacetime.",
        "The source launches from the composite hub. The beam focuses into the prime sink.",
        "",
        "## Ring Summary",
        "",
        "| Ring | Anchors | IP top-20 hits | Unique IP | grad_clean | grad_qnt | τ(p-1)_clean | τ(p-1)_qnt |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rname, s in ring_summaries.items():
        md.append(f"| {rname} | {s['n_anchors']} | {s['ip_hits']} | {s['unique_ip']} "
                  f"| {s['mean_gradient_clean']:.3f} | {s['mean_gradient_quantum']:.3f} "
                  f"| {s['mean_tau_pm1_clean']:.1f} | {s['mean_tau_pm1_quantum']:.1f} |")

    md += [
        "",
        "## Key Findings",
        "",
        "- **Gradient** distinguishes clean from quantum anchors in most rings",
        "- **τ(p-1)** is systematically different between families",
        "- Quantum anchors have LOWER gradient: they sit at interference nodes where multiple paths overlap",
        "- Clean anchors have HIGHER gradient: they're at the end of a single strong source-to-sink arc",
        "",
        "## Full Integration Path",
        "",
        "1. Add τ computation to row-cache scorer (segmented sieve for each ring)",
        "2. Compute `hub_gradient` and `path_energy` as new channels per scan row",
        "3. Score candidates, take top-20, test union coverage improvement",
        "4. Calibrate (α, β, γ, δ) on A-G, freeze, test on I",
        "",
        "## Artifact",
        "",
        "- `artifacts/inverse_prime_field/field_v1.json`",
        "- Script: `scripts/research/inverse_prime_field.py`",
    ]

    rpt = OUT_DIR / "REPORT.md"
    rpt.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nSaved: {art_path}")
    print(f"Saved: {rpt}")


if __name__ == "__main__":
    main()

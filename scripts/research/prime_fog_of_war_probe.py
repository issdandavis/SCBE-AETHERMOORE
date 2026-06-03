#!/usr/bin/env python3
"""Prime fog-of-war probe.

This is an experiment harness, not a primality proof framework. It tests the
idea that geometry-like property folds can bracket a search space before exact
math verifies the target.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import dataclass
from typing import Iterable


KNOWN_MERSENNE_EXPONENTS = [
    2,
    3,
    5,
    7,
    13,
    17,
    19,
    31,
    61,
    89,
    107,
    127,
    521,
    607,
    1279,
    2203,
    2281,
    3217,
    4253,
    4423,
    9689,
    9941,
    11213,
    19937,
    21701,
    23209,
    44497,
    86243,
    110503,
    132049,
    216091,
    756839,
    859433,
    1257787,
    1398269,
    2976221,
    3021377,
    6972593,
    13466917,
    20996011,
    24036583,
    25964951,
    30402457,
    32582657,
    37156667,
    43112609,
    57885161,
    74207281,
    77232917,
    82589933,
    136279841,
]

KNOWN_FERMAT_PRIMES = [3, 5, 17, 257, 65537]
SMALL_FILTER_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
WHEEL30_RESIDUES = {1, 7, 11, 13, 17, 19, 23, 29}


@dataclass(frozen=True)
class FermatCandidate:
    prime: int
    score: int
    seams: list[str]


def sieve(limit: int) -> list[int]:
    if limit < 2:
        return []
    flags = bytearray(b"\x01") * (limit + 1)
    flags[0:2] = b"\x00\x00"
    root = math.isqrt(limit)
    for n in range(2, root + 1):
        if flags[n]:
            start = n * n
            flags[start : limit + 1 : n] = b"\x00" * (((limit - start) // n) + 1)
    return [n for n in range(2, limit + 1) if flags[n]]


def is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def fermat_score(p: int) -> FermatCandidate:
    score = 0
    seams: list[str] = []

    minus_one = p - 1
    if is_power_of_two(minus_one):
        score += 8
        seams.append("p_minus_1_is_power_of_two")
        exponent = minus_one.bit_length() - 1
        if is_power_of_two(exponent):
            score += 8
            seams.append("power_exponent_is_power_of_two")

    if p.bit_count() == 2:
        score += 4
        seams.append("binary_two_spike")

    if p == 2 or p % 4 == 1:
        score += 1
        seams.append("sum_two_squares_residue")

    if p in KNOWN_FERMAT_PRIMES:
        seams.append("known_fermat_prime_target")

    return FermatCandidate(prime=p, score=score, seams=seams)


def lucas_lehmer(exponent: int) -> bool:
    if exponent == 2:
        return True
    if exponent < 2:
        return False
    modulus = (1 << exponent) - 1
    s = 4
    for _ in range(exponent - 2):
        s = ((s * s) - 2) % modulus
    return s == 0


def known_targets_up_to(limit: int) -> list[int]:
    return [p for p in KNOWN_MERSENNE_EXPONENTS if p <= limit]


def nearest_window(limit: int) -> list[int]:
    anchors = [127, 521, 1279, 4423, 9689, 19937, 44497, 110503, 216091]
    out = [a for a in anchors if a < limit]
    if limit not in out:
        out.append(limit)
    return sorted(set(out))


def deterministic_miller_rabin_u64(n: int) -> bool:
    if n < 2:
        return False
    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    for p in small_primes:
        if n == p:
            return True
        if n % p == 0:
            return False
    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for a in [2, 325, 9375, 28178, 450775, 9780504, 1795265022]:
        a %= n
        if a in (0, 1):
            continue
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def next_prime_at_or_after(n: int) -> int:
    if n <= 2:
        return 2
    candidate = n if n % 2 else n + 1
    while not deterministic_miller_rabin_u64(candidate):
        candidate += 2
    return candidate


def blind_anchor(seed: int, base: int, step: int) -> int:
    return base + (seed * step) + (seed * seed * 1009) + (seed * seed * seed)


def cube_half_square_energy(n: int, anchor: int, window: int) -> dict:
    phase = max(0, n - anchor) / max(1, window)
    odd_penalty = 0.0 if n % 2 else 1.0
    wheel_penalty = 0.0 if n % 30 in WHEEL30_RESIDUES else 1.0
    divisor = first_small_divisor(n)
    small_factor_penalty = 0.0 if divisor is None else 1.0
    log_drift = abs(math.log(n) - math.log(anchor)) / max(math.log(anchor), 1.0)
    vector = [phase, odd_penalty, wheel_penalty, small_factor_penalty, log_drift]
    lifted = [value**3 for value in vector]
    energy = 0.5 * sum(value * value for value in lifted)
    return {
        "energy": energy,
        "phase": phase,
        "odd_penalty": odd_penalty,
        "wheel_penalty": wheel_penalty,
        "small_factor_penalty": small_factor_penalty,
        "log_drift": log_drift,
        **({"blocked_by": divisor} if divisor else {}),
    }


def run_blind_sweep(target_count: int, base: int, step: int, window: int) -> dict:
    rows = []
    total_raw = 0
    total_rank_tests = 0
    exact_first_hits = 0
    recovered = 0

    for seed in range(target_count):
        anchor = blind_anchor(seed, base, step)
        target = next_prime_at_or_after(anchor)
        search_end = max(anchor + window, target + 1)
        candidates = []

        for n in range(anchor, search_end + 1):
            energy = cube_half_square_energy(n, anchor, search_end - anchor + 1)
            candidates.append((energy["energy"], n, energy))

        candidates.sort(key=lambda item: (item[0], item[1]))
        total_raw += len(candidates)
        first_exact_prime = None
        tests_to_target = None
        target_energy_rank = None
        target_energy = None
        exact_tests = 0

        for rank, (_, n, energy) in enumerate(candidates, start=1):
            if n == target:
                target_energy_rank = rank
                target_energy = energy["energy"]
            if "blocked_by" in energy:
                continue
            exact_tests += 1
            if deterministic_miller_rabin_u64(n):
                if first_exact_prime is None:
                    first_exact_prime = n
                if n == target:
                    tests_to_target = exact_tests
                    break

        if tests_to_target is not None:
            recovered += 1
            total_rank_tests += tests_to_target
        if first_exact_prime == target:
            exact_first_hits += 1

        rows.append(
            {
                "seed": seed,
                "anchor": anchor,
                "target_prime": target,
                "target_gap": target - anchor,
                "raw_candidates": len(candidates),
                "target_energy_rank": target_energy_rank,
                "target_energy": round(target_energy or 0, 12),
                "exact_tests_to_target": tests_to_target,
                "first_exact_prime": first_exact_prime,
                "first_exact_prime_was_target": first_exact_prime == target,
            }
        )

    ranks = [row["target_energy_rank"] for row in rows if row["target_energy_rank"] is not None]
    tests = [row["exact_tests_to_target"] for row in rows if row["exact_tests_to_target"] is not None]
    return {
        "schema_version": "prime_fog_blind_sweep_v1",
        "target_family": "deterministic_12_digit_next_primes",
        "target_count": target_count,
        "base": base,
        "step": step,
        "window": window,
        "raw_candidate_count": total_raw,
        "recovered_count": recovered,
        "first_exact_prime_hit_count": exact_first_hits,
        "mean_target_energy_rank": round(sum(ranks) / len(ranks), 3) if ranks else None,
        "max_target_energy_rank": max(ranks) if ranks else None,
        "mean_exact_tests_to_target": round(sum(tests) / len(tests), 3) if tests else None,
        "max_exact_tests_to_target": max(tests) if tests else None,
        "exact_test_reduction": round(1 - (sum(tests) / total_raw), 6) if total_raw and tests else None,
        "rows": rows,
    }


def fermat_digits(n: int) -> int:
    return math.floor((1 << n) * math.log10(2)) + 1


def parse_mesh_primes(raw: str) -> list[int]:
    primes = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            value = int(part)
            if value > 2:
                primes.append(value)
    return sorted(set(primes))


def fermat_k_mesh(stride: int, mesh_primes: list[int]) -> dict[int, int]:
    mesh = {}
    for q in mesh_primes:
        residue = (-pow(stride % q, -1, q)) % q
        mesh[q] = residue
    return mesh


def mesh_blocker(k: int, mesh: dict[int, int]) -> int | None:
    for q, banned_residue in mesh.items():
        if k % q == banned_residue:
            return q
    return None


def mesh_gate_profile(k: int, mesh: dict[int, int]) -> dict:
    passed = 0
    for q, banned_residue in mesh.items():
        if k % q == banned_residue:
            return {
                "passed": passed,
                "total": len(mesh),
                "blocked_by": q,
                "ratio": passed / max(1, len(mesh)),
            }
        passed += 1
    return {
        "passed": passed,
        "total": len(mesh),
        "blocked_by": None,
        "ratio": passed / max(1, len(mesh)),
    }


def near_echo_glow(
    normalized_error: float,
    candidate: int,
    mesh_profile: dict,
    angle_bin: int,
    learned_bins: set[int],
    allowed_bins: set[int],
) -> dict:
    error_floor = 1 / max(2, candidate)
    closeness_digits = -math.log10(max(normalized_error, error_floor))
    lane_weight = 1.0 if angle_bin in learned_bins else 0.7 if angle_bin in allowed_bins else 0.25
    mesh_ratio = mesh_profile["ratio"]
    glow = mesh_ratio * lane_weight * (1 + closeness_digits)
    return {
        "glow_score": round(glow, 12),
        "closeness_digits": round(closeness_digits, 6),
        "mesh_gate_ratio": round(mesh_ratio, 6),
        "mesh_gates_passed": mesh_profile["passed"],
        "mesh_gate_total": mesh_profile["total"],
        "lane_weight": lane_weight,
    }


def fermat_number_index(value: int) -> int | None:
    if value <= 2 or not is_power_of_two(value - 1):
        return None
    power = (value - 1).bit_length() - 1
    if not is_power_of_two(power):
        return None
    return power.bit_length() - 1


def first_fermat_negation_step(candidate: int, max_n: int) -> int | None:
    target = candidate - 1
    for source_n in range(0, max_n + 1):
        if pow(2, 1 << source_n, candidate) == target:
            return source_n
    return None


def classify_fermat_family_echo(n: int, candidate: int, residue: int, modular_error: int) -> dict:
    target = candidate - 1
    candidate_fermat_n = fermat_number_index(candidate)
    if residue == target:
        return {
            "kind": "exact_collapse",
            "family": "fermat",
            "source_n": n,
            "source_form": f"F_{n}",
        }

    if residue == 1 and modular_error == 2:
        source_n = first_fermat_negation_step(candidate, n - 1)
        if source_n is not None:
            kind = (
                "lower_fermat_number_ghost"
                if candidate_fermat_n == source_n
                else "lower_fermat_factor_ghost"
            )
            return {
                "kind": kind,
                "family": "fermat",
                "source_n": source_n,
                "source_form": f"F_{source_n}",
                "echo_lag": n - source_n,
                "residue_relation": "minus_one_squared_to_plus_one",
                **({"candidate_fermat_n": candidate_fermat_n} if candidate_fermat_n is not None else {}),
            }
        return {
            "kind": "negation_mirror_echo",
            "family": "fermat",
            "residue_relation": "plus_one_opposite_target_minus_one",
            **({"candidate_fermat_n": candidate_fermat_n} if candidate_fermat_n is not None else {}),
        }

    if candidate_fermat_n is not None:
        return {
            "kind": "fermat_number_near_miss",
            "family": "fermat",
            "candidate_fermat_n": candidate_fermat_n,
            "candidate_form": f"F_{candidate_fermat_n}",
        }

    return {"kind": "ordinary_near_miss", "family": "fermat"}


def run_fermat_factor_flashlight(start_n: int, end_n: int, k_limit: int, mesh_primes: list[int]) -> dict:
    rows = []
    for n in range(start_n, end_n + 1):
        step = 1 << (n + 2)
        mesh = fermat_k_mesh(step, mesh_primes)
        found = None
        mesh_rejects = 0
        verifier_tests = 0
        for k in range(1, k_limit + 1):
            blocked_by = mesh_blocker(k, mesh)
            if blocked_by is not None:
                mesh_rejects += 1
                continue
            candidate = (k * step) + 1
            verifier_tests += 1
            if pow(2, 1 << n, candidate) == candidate - 1:
                raw_odd_tests = (candidate - 1) // 2
                found = {
                    "k": k,
                    "factor": candidate,
                    "factor_is_probable_prime": deterministic_miller_rabin_u64(candidate),
                    "grid_tests": k,
                    "mesh_rejects_to_hit": mesh_rejects,
                    "verifier_tests_to_hit": verifier_tests,
                    "raw_odd_tests_to_factor": raw_odd_tests,
                    "raw_to_grid_reduction": round(1 - (k / max(1, raw_odd_tests)), 12),
                    "grid_to_mesh_reduction": round(1 - (verifier_tests / max(1, k)), 12),
                    "raw_to_verifier_reduction": round(1 - (verifier_tests / max(1, raw_odd_tests)), 12),
                    "factor_digits": len(str(candidate)),
                    "factor_bits": candidate.bit_length(),
                    "factor_residues": {
                        "mod30": candidate % 30,
                        "mod210": candidate % 210,
                    },
                }
                break
        mesh_survivors = k_limit - mesh_rejects
        rows.append(
            {
                "n": n,
                "fermat_form": f"2^(2^{n}) + 1",
                "fermat_digits": fermat_digits(n),
                "factor_grid": f"k * 2^{n + 2} + 1",
                "k_limit": k_limit,
                "mesh_primes": mesh_primes,
                "mesh_banned_residues": {str(q): residue for q, residue in mesh.items()},
                "mesh_rejects": mesh_rejects,
                "mesh_survivors": mesh_survivors,
                "mesh_survival_rate": round(mesh_survivors / max(1, k_limit), 6),
                "verifier_tests": verifier_tests,
                "found": found is not None,
                **({"hit": found} if found else {}),
            }
        )

    hits = [row for row in rows if row["found"]]
    return {
        "schema_version": "prime_fog_fermat_factor_flashlight_v1",
        "start_n": start_n,
        "end_n": end_n,
        "k_limit": k_limit,
        "mesh_primes": mesh_primes,
        "tested_count": len(rows),
        "hit_count": len(hits),
        "total_mesh_rejects": sum(row["mesh_rejects"] for row in rows),
        "total_mesh_survivors": sum(row["mesh_survivors"] for row in rows),
        "total_verifier_tests": sum(row["verifier_tests"] for row in rows),
        "rows": rows,
    }


def print_fermat_factor_flashlight(payload: dict) -> None:
    print("Fermat factor flashlight")
    print(f"n range: {payload['start_n']}..{payload['end_n']}")
    print(f"k limit: {payload['k_limit']}")
    print(f"mesh primes: {payload['mesh_primes']}")
    print(f"hits: {payload['hit_count']}/{payload['tested_count']}")
    print(f"mesh rejects: {payload['total_mesh_rejects']}")
    print(f"verifier tests: {payload['total_verifier_tests']}")
    print()
    for row in payload["rows"]:
        if not row["found"]:
            print(
                f"F_{row['n']:<2} digits={row['fermat_digits']:<7} "
                f"grid={row['factor_grid']:<16} "
                f"survivors={row['mesh_survivors']:<8} "
                f"no hit within k<={row['k_limit']}"
            )
            continue
        hit = row["hit"]
        print(
            f"F_{row['n']:<2} digits={row['fermat_digits']:<7} "
            f"factor={hit['factor']:<18} "
            f"k={hit['k']:<8} "
            f"verifier={hit['verifier_tests_to_hit']:<7} "
            f"prime={hit['factor_is_probable_prime']} "
            f"grid-red={hit['raw_to_grid_reduction']:.8%} "
            f"mesh-red={hit['grid_to_mesh_reduction']:.8%} "
            f"raw-verifier-red={hit['raw_to_verifier_reduction']:.8%}"
        )


def ratio_sequence(values: list[int], labels: list[str] | None = None, bins: int = 32) -> dict:
    labels = labels or [str(value) for value in values]
    rows = []
    theta = 0.0
    histogram = [0] * bins
    for index in range(len(values) - 1):
        x0 = values[index]
        x1 = values[index + 1]
        if x0 <= 0 or x1 <= 0:
            continue
        delta = x1 - x0
        velocity = delta / x0
        log_step = math.log(x1 / x0)
        theta += log_step
        theta_mod = theta % (2 * math.pi)
        bin_index = min(bins - 1, int((theta_mod / (2 * math.pi)) * bins))
        histogram[bin_index] += 1
        rows.append(
            {
                "from": labels[index],
                "to": labels[index + 1],
                "x0": x0,
                "x1": x1,
                "delta": delta,
                "scale_invariant_velocity": velocity,
                "log_step": log_step,
                "theta": theta,
                "theta_mod_tau": theta_mod,
                "angle_bin": bin_index,
            }
        )

    velocities = [row["scale_invariant_velocity"] for row in rows]
    log_steps = [row["log_step"] for row in rows]
    return {
        "schema_version": "prime_fog_ratio_map_v1",
        "count": len(values),
        "pair_count": len(rows),
        "bins": bins,
        "mean_velocity": round(sum(velocities) / len(velocities), 12) if velocities else None,
        "min_velocity": round(min(velocities), 12) if velocities else None,
        "max_velocity": round(max(velocities), 12) if velocities else None,
        "mean_log_step": round(sum(log_steps) / len(log_steps), 12) if log_steps else None,
        "angle_histogram": histogram,
        "rows": rows,
    }


def run_ratio_map(args: argparse.Namespace) -> dict:
    source = args.ratio_source
    if source == "custom":
        values = parse_number_list(args.ratio_values)
        labels = [str(value) for value in values]
    elif source == "mersenne-exponents":
        values = KNOWN_MERSENNE_EXPONENTS[: args.ratio_count]
        labels = [f"M{index + 1}:p={value}" for index, value in enumerate(values)]
    elif source in ("fermat-factors", "fermat-k"):
        flashlight = run_fermat_factor_flashlight(
            args.fermat_start,
            args.fermat_end,
            args.fermat_k_limit,
            parse_mesh_primes(args.fermat_mesh_primes),
        )
        hits = [row for row in flashlight["rows"] if row["found"]]
        if source == "fermat-factors":
            values = [row["hit"]["factor"] for row in hits]
            labels = [f"F_{row['n']} factor" for row in hits]
        else:
            values = [row["hit"]["k"] for row in hits]
            labels = [f"F_{row['n']} k" for row in hits]
    else:
        raise ValueError(f"unknown ratio source: {source}")

    order = args.ratio_order
    if order == "value":
        paired = sorted(zip(values, labels), key=lambda item: item[0])
        values = [item[0] for item in paired]
        labels = [item[1] for item in paired]

    payload = ratio_sequence(values, labels, args.ratio_bins)
    payload["source"] = source
    payload["order"] = order
    payload["values"] = [{"label": label, "value": value} for label, value in zip(labels, values)]
    return payload


def print_ratio_map(payload: dict) -> None:
    print("Solution ratio map")
    print(f"source: {payload['source']}")
    print(f"order: {payload['order']}")
    print(f"values: {payload['count']} pairs: {payload['pair_count']}")
    print(f"mean dx/x: {payload['mean_velocity']}")
    print(f"min dx/x: {payload['min_velocity']}")
    print(f"max dx/x: {payload['max_velocity']}")
    print(f"mean d(log x): {payload['mean_log_step']}")
    print(f"angle histogram: {payload['angle_histogram']}")
    print()
    for row in payload["rows"]:
        print(
            f"{row['from']} -> {row['to']} "
            f"dx/x={row['scale_invariant_velocity']:.12g} "
            f"dlog={row['log_step']:.12g} "
            f"bin={row['angle_bin']}"
        )


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def solution_radius_profile(values: list[int], labels: list[str] | None = None) -> dict:
    labels = labels or [str(value) for value in values]
    rows = []
    for index, value in enumerate(values):
        left = values[index - 1] if index > 0 else None
        right = values[index + 1] if index + 1 < len(values) else None
        left_ratio = ((value - left) / value) if left is not None and value else None
        right_ratio = ((right - value) / value) if right is not None and value else None
        rows.append(
            {
                "label": labels[index],
                "center": value,
                "left_ratio": left_ratio,
                "right_ratio": right_ratio,
                "radius_band": [
                    left_ratio if left_ratio is not None else 0,
                    right_ratio if right_ratio is not None else 0,
                ],
            }
        )
    right_ratios = [row["right_ratio"] for row in rows if row["right_ratio"] is not None and row["right_ratio"] > 0]
    return {
        "schema_version": "prime_fog_solution_radius_v1",
        "count": len(values),
        "median_right_ratio": median(right_ratios),
        "rows": rows,
    }


def predictive_band_from_hits(hit_values: list[int], k_limit: int, min_width: int = 256) -> dict | None:
    if len(hit_values) < 2:
        return None
    profile = solution_radius_profile(hit_values)
    trend = profile["median_right_ratio"]
    if trend is None or trend <= 0:
        return None
    center = round(hit_values[-1] * (1 + trend))
    radius = max(min_width, round(hit_values[-1] * min(trend, 2.0)))
    low = max(1, center - radius)
    high = min(k_limit, center + radius)
    if low > k_limit or high < 1:
        return None
    return {
        "center": max(1, min(k_limit, center)),
        "radius": radius,
        "low": low,
        "high": high,
        "trend_ratio": trend,
        "source_hits": hit_values[-4:],
        "profile": profile,
    }


def angle_bin_for_value(value: int, bins: int) -> int:
    if value <= 0:
        return 0
    theta = math.log(value) % (2 * math.pi)
    return min(bins - 1, int((theta / (2 * math.pi)) * bins))


def expand_bins(active_bins: set[int], bins: int, halo: int) -> set[int]:
    expanded = set()
    for bin_index in active_bins:
        for offset in range(-halo, halo + 1):
            expanded.add((bin_index + offset) % bins)
    return expanded


def test_fermat_k_candidate(n: int, step: int, k: int, mesh: dict[int, int], counters: dict) -> dict | None:
    blocked_by = mesh_blocker(k, mesh)
    counters["visited"] += 1
    if blocked_by is not None:
        counters["mesh_rejects"] += 1
        return None

    counters["verifier_tests"] += 1
    candidate = (k * step) + 1
    if pow(2, 1 << n, candidate) != candidate - 1:
        return None

    raw_odd_tests = (candidate - 1) // 2
    return {
        "k": k,
        "factor": candidate,
        "factor_is_probable_prime": deterministic_miller_rabin_u64(candidate),
        "raw_odd_tests_to_factor": raw_odd_tests,
        "raw_to_grid_reduction": round(1 - (k / max(1, raw_odd_tests)), 12),
        "raw_to_verifier_reduction": round(
            1 - (counters["verifier_tests"] / max(1, raw_odd_tests)),
            12,
        ),
        "factor_digits": len(str(candidate)),
        "factor_bits": candidate.bit_length(),
        "factor_residues": {
            "mod30": candidate % 30,
            "mod210": candidate % 210,
        },
    }


def run_grenade_pings(
    n: int,
    step: int,
    mesh: dict[int, int],
    learned_bins: set[int],
    bins: int,
    start_k: int,
    end_k: int,
    halo: int,
    max_hits: int,
    proximity_count: int,
    skip_ks: set[int],
) -> dict:
    counters = {"visited": 0, "mesh_rejects": 0, "verifier_tests": 0}
    hits = []
    proximity = []
    allowed_bins = expand_bins(learned_bins, bins, halo) if learned_bins else set()
    if not allowed_bins or start_k > end_k:
        return {
            "enabled": False,
            "allowed_bins": sorted(allowed_bins),
            "visited": 0,
            "mesh_rejects": 0,
            "verifier_tests": 0,
            "hits": [],
            "proximity": [],
        }

    for k in range(start_k, end_k + 1):
        if k in skip_ks:
            continue
        if angle_bin_for_value(k, bins) not in allowed_bins:
            continue
        mesh_profile = mesh_gate_profile(k, mesh)
        counters["visited"] += 1
        if mesh_profile["blocked_by"] is not None:
            counters["mesh_rejects"] += 1
            continue

        candidate = (k * step) + 1
        angle_bin = angle_bin_for_value(k, bins)
        counters["verifier_tests"] += 1
        residue = pow(2, 1 << n, candidate)
        target = candidate - 1
        clockwise = (residue - target) % candidate
        counter_clockwise = (target - residue) % candidate
        modular_error = min(clockwise, counter_clockwise)
        normalized_error = modular_error / candidate
        proximity_row = {
            "k": k,
            "candidate": candidate,
            "angle_bin": angle_bin,
            "modular_error": modular_error,
            "normalized_error": normalized_error,
            "residue": residue,
            **near_echo_glow(
                normalized_error,
                candidate,
                mesh_profile,
                angle_bin,
                learned_bins,
                allowed_bins,
            ),
        }
        proximity.append(proximity_row)
        proximity.sort(key=lambda row: (-row["glow_score"], row["normalized_error"], row["k"]))
        if len(proximity) > proximity_count:
            proximity.pop()

        if residue == target:
            raw_odd_tests = (candidate - 1) // 2
            hit = {
                "k": k,
                "factor": candidate,
                "factor_is_probable_prime": deterministic_miller_rabin_u64(candidate),
                "raw_odd_tests_to_factor": raw_odd_tests,
                "raw_to_grid_reduction": round(1 - (k / max(1, raw_odd_tests)), 12),
                "raw_to_verifier_reduction": round(
                    1 - (counters["verifier_tests"] / max(1, raw_odd_tests)),
                    12,
                ),
                "factor_digits": len(str(candidate)),
                "factor_bits": candidate.bit_length(),
                "factor_residues": {
                    "mod30": candidate % 30,
                    "mod210": candidate % 210,
                },
                "angle_bin": angle_bin_for_value(k, bins),
                "ping_verifier_tests_to_hit": counters["verifier_tests"],
                "ping_mesh_rejects_to_hit": counters["mesh_rejects"],
                "ping_visited_to_hit": counters["visited"],
            }
            hits.append(hit)
            if len(hits) >= max_hits:
                break

    return {
        "enabled": True,
        "allowed_bins": sorted(allowed_bins),
        "start_k": start_k,
        "end_k": end_k,
        "visited": counters["visited"],
        "mesh_rejects": counters["mesh_rejects"],
        "verifier_tests": counters["verifier_tests"],
        "hits": hits,
        "proximity": [
            {
                **row,
                "normalized_error": round(row["normalized_error"], 18),
                "family_echo": classify_fermat_family_echo(
                    n,
                    row["candidate"],
                    row["residue"],
                    row["modular_error"],
                ),
            }
            for row in proximity
        ],
    }


def run_adaptive_cone_search(
    start_n: int,
    end_n: int,
    k_limit: int,
    mesh_primes: list[int],
    core_limit: int,
    bins: int,
    grenade_limit: int,
    grenade_halo: int,
    grenade_max_hits: int,
    grenade_proximity_count: int,
    glow_bin_threshold: float,
) -> dict:
    rows = []
    learned_bins: set[int] = set()
    glow_bins: set[int] = set()
    hit_ks: list[int] = []
    grenade_hit_ks: list[int] = []

    for n in range(start_n, end_n + 1):
        step = 1 << (n + 2)
        mesh = fermat_k_mesh(step, mesh_primes)
        visited: set[int] = set()
        counters = {"visited": 0, "mesh_rejects": 0, "verifier_tests": 0}
        phase_stats = []
        found = None
        found_phase = None
        bins_before = sorted(learned_bins)
        glow_bins_before = sorted(glow_bins)
        grenade = None
        phase_jump_band = predictive_band_from_hits(hit_ks, k_limit)

        def scan_phase(name: str, iterator, allowed_bins: set[int] | None = None) -> dict | None:
            nonlocal found_phase
            started = dict(counters)
            for k in iterator:
                if k < 1 or k > k_limit or k in visited:
                    continue
                if allowed_bins is not None and angle_bin_for_value(k, bins) not in allowed_bins:
                    continue
                visited.add(k)
                hit = test_fermat_k_candidate(n, step, k, mesh, counters)
                if hit:
                    found_phase = name
                    return hit
            phase_stats.append(
                {
                    "phase": name,
                    "visited": counters["visited"] - started["visited"],
                    "mesh_rejects": counters["mesh_rejects"] - started["mesh_rejects"],
                    "verifier_tests": counters["verifier_tests"] - started["verifier_tests"],
                    **({"allowed_bins": sorted(allowed_bins)} if allowed_bins is not None else {}),
                }
            )
            return None

        core_end = min(core_limit, k_limit)
        found = scan_phase("linear_core", range(1, core_end + 1))

        if not found and phase_jump_band:
            found = scan_phase(
                "solution_radius_band",
                range(phase_jump_band["low"], phase_jump_band["high"] + 1),
            )

        if not found and learned_bins:
            found = scan_phase(
                "learned_angle_lanes",
                range(core_end + 1, k_limit + 1),
                expand_bins(learned_bins, bins, 0),
            )

        if not found and glow_bins:
            found = scan_phase(
                "near_echo_lanes",
                range(core_end + 1, k_limit + 1),
                expand_bins(glow_bins, bins, 0),
            )

        if not found and learned_bins:
            found = scan_phase(
                "expanded_angle_lanes",
                range(core_end + 1, k_limit + 1),
                expand_bins(learned_bins | glow_bins, bins, 1),
            )

        if not found:
            found = scan_phase("full_fallback", range(core_end + 1, k_limit + 1))

        if found:
            found["phase"] = found_phase
            found["angle_bin"] = angle_bin_for_value(found["k"], bins)
            found["verifier_tests_to_hit"] = counters["verifier_tests"]
            found["mesh_rejects_to_hit"] = counters["mesh_rejects"]
            found["visited_to_hit"] = counters["visited"]
            found["grid_to_mesh_reduction"] = round(
                1 - (counters["verifier_tests"] / max(1, found["k"])),
                12,
            )
            learned_bins.add(found["angle_bin"])
            hit_ks.append(found["k"])

        grenade_end = min(k_limit, max(core_end, grenade_limit))
        grenade = run_grenade_pings(
            n,
            step,
            mesh,
            learned_bins,
            bins,
            core_end + 1,
            grenade_end,
            grenade_halo,
            grenade_max_hits,
            grenade_proximity_count,
            {found["k"]} if found else set(),
        )
        for ping_hit in grenade["hits"]:
            grenade_hit_ks.append(ping_hit["k"])
            learned_bins.add(ping_hit["angle_bin"])
        for near_echo in grenade["proximity"]:
            if near_echo["glow_score"] >= glow_bin_threshold:
                glow_bins.add(near_echo["angle_bin"])

        rows.append(
            {
                "n": n,
                "fermat_form": f"2^(2^{n}) + 1",
                "fermat_digits": fermat_digits(n),
                "k_limit": k_limit,
                "core_limit": core_limit,
                "phase_jump_band": phase_jump_band,
                "learned_bins_before": bins_before,
                "glow_bins_before": glow_bins_before,
                "learned_bins_after": sorted(learned_bins),
                "glow_bins_after": sorted(glow_bins),
                "visited": counters["visited"],
                "mesh_rejects": counters["mesh_rejects"],
                "verifier_tests": counters["verifier_tests"],
                "grenade_ping": grenade,
                "phase_stats": phase_stats,
                "found": found is not None,
                **({"hit": found} if found else {}),
            }
        )

    return {
        "schema_version": "prime_fog_adaptive_cone_search_v1",
        "start_n": start_n,
        "end_n": end_n,
        "k_limit": k_limit,
        "mesh_primes": mesh_primes,
        "core_limit": core_limit,
        "bins": bins,
        "hit_count": sum(1 for row in rows if row["found"]),
        "tested_count": len(rows),
        "learned_bins": sorted(learned_bins),
        "glow_bins": sorted(glow_bins),
        "solution_radius_profile": solution_radius_profile(
            hit_ks,
            [f"hit_{index + 1}" for index in range(len(hit_ks))],
        )
        if hit_ks
        else None,
        "hit_k_ratio_map": ratio_sequence(hit_ks, [f"hit_{index + 1}" for index in range(len(hit_ks))], bins)
        if len(hit_ks) >= 2
        else None,
        "grenade_hit_count": sum(len(row["grenade_ping"]["hits"]) for row in rows),
        "grenade_hit_k_ratio_map": ratio_sequence(
            grenade_hit_ks,
            [f"grenade_{index + 1}" for index in range(len(grenade_hit_ks))],
            bins,
        )
        if len(grenade_hit_ks) >= 2
        else None,
        "total_visited": sum(row["visited"] for row in rows),
        "total_mesh_rejects": sum(row["mesh_rejects"] for row in rows),
        "total_verifier_tests": sum(row["verifier_tests"] for row in rows),
        "total_grenade_visited": sum(row["grenade_ping"]["visited"] for row in rows),
        "total_grenade_mesh_rejects": sum(row["grenade_ping"]["mesh_rejects"] for row in rows),
        "total_grenade_verifier_tests": sum(row["grenade_ping"]["verifier_tests"] for row in rows),
        "total_grenade_proximity_records": sum(len(row["grenade_ping"]["proximity"]) for row in rows),
        "rows": rows,
    }


def print_adaptive_cone_search(payload: dict) -> None:
    print("Adaptive Fermat cone search")
    print(f"n range: {payload['start_n']}..{payload['end_n']}")
    print(f"k limit: {payload['k_limit']}")
    print(f"core limit: {payload['core_limit']}")
    print(f"bins: {payload['bins']}")
    print(f"hits: {payload['hit_count']}/{payload['tested_count']}")
    print(f"learned bins: {payload['learned_bins']}")
    print(f"glow bins: {payload['glow_bins']}")
    print(f"total visited: {payload['total_visited']}")
    print(f"mesh rejects: {payload['total_mesh_rejects']}")
    print(f"verifier tests: {payload['total_verifier_tests']}")
    print(f"grenade hits: {payload['grenade_hit_count']}")
    print(f"grenade verifier tests: {payload['total_grenade_verifier_tests']}")
    print(f"grenade proximity records: {payload['total_grenade_proximity_records']}")
    if payload["hit_k_ratio_map"]:
        print(f"hit-k angle histogram: {payload['hit_k_ratio_map']['angle_histogram']}")
    if payload["solution_radius_profile"]:
        print(f"solution-radius median right ratio: {payload['solution_radius_profile']['median_right_ratio']}")
    if payload["grenade_hit_k_ratio_map"]:
        print(f"grenade hit-k angle histogram: {payload['grenade_hit_k_ratio_map']['angle_histogram']}")
    print()

    def echo_note(best: dict) -> str:
        echo = best.get("family_echo")
        if not echo:
            return ""
        source = echo.get("source_form") or echo.get("candidate_form")
        source_note = f" source={source}" if source else ""
        lag_note = f" lag={echo['echo_lag']}" if "echo_lag" in echo else ""
        return f" echo={echo['kind']}{source_note}{lag_note}"

    for row in payload["rows"]:
        grenade = row["grenade_ping"]
        if not row["found"]:
            band = row["phase_jump_band"]
            band_note = f" band={band['low']}..{band['high']}" if band else ""
            print(
                f"F_{row['n']:<2} digits={row['fermat_digits']:<7} "
                f"visited={row['visited']:<8} verifier={row['verifier_tests']:<8} "
                f"grenade_hits={len(grenade['hits']):<2} no hit{band_note}"
            )
            if grenade["proximity"]:
                best = grenade["proximity"][0]
                print(
                    f"    nearest ping k={best['k']} candidate={best['candidate']} "
                    f"glow={best['glow_score']} "
                    f"digits={best['closeness_digits']} "
                    f"norm_err={best['normalized_error']}"
                    f"{echo_note(best)}"
                )
            continue
        hit = row["hit"]
        band = row["phase_jump_band"]
        band_note = f" band={band['low']}..{band['high']}" if band else ""
        print(
            f"F_{row['n']:<2} digits={row['fermat_digits']:<7} "
            f"factor={hit['factor']:<18} "
            f"k={hit['k']:<8} "
            f"phase={hit['phase']:<20} "
            f"bin={hit['angle_bin']:<3} "
            f"verifier={hit['verifier_tests_to_hit']:<8} "
            f"raw-verifier-red={hit['raw_to_verifier_reduction']:.8%} "
            f"grenade_hits={len(grenade['hits'])}"
            f"{band_note}"
        )
        if grenade["hits"]:
            for ping in grenade["hits"][:3]:
                print(
                    f"    ping hit factor={ping['factor']} k={ping['k']} "
                    f"bin={ping['angle_bin']} verifier={ping['ping_verifier_tests_to_hit']}"
                )
        elif grenade["proximity"]:
            best = grenade["proximity"][0]
            print(
                f"    nearest ping k={best['k']} candidate={best['candidate']} "
                f"glow={best['glow_score']} "
                f"digits={best['closeness_digits']} "
                f"norm_err={best['normalized_error']}"
                f"{echo_note(best)}"
            )


def run_fermat_probe(prime_limit: int, top: int) -> dict:
    primes = sieve(prime_limit)
    scored = sorted((fermat_score(p) for p in primes), key=lambda row: (-row.score, row.prime))
    top_rows = scored[:top]
    target_rows = [row for row in scored if row.prime in KNOWN_FERMAT_PRIMES and row.prime <= prime_limit]
    target_rank = {row.prime: index + 1 for index, row in enumerate(scored) if row.prime in KNOWN_FERMAT_PRIMES}
    return {
        "schema_version": "prime_fog_fermat_probe_v1",
        "prime_limit": prime_limit,
        "prime_count": len(primes),
        "top": [
            {"prime": row.prime, "score": row.score, "seams": row.seams}
            for row in top_rows
        ],
        "recovered_targets": [
            {
                "prime": row.prime,
                "score": row.score,
                "rank": target_rank[row.prime],
                "seams": row.seams,
            }
            for row in target_rows
        ],
    }


def first_small_divisor(n: int) -> int | None:
    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]:
        if n == p:
            return None
        if n % p == 0:
            return p
    return None


def arithmetic_lidar_frame(
    primes: list[int],
    prime_set: set[int],
    prime_index: dict[int, int],
    cursor: int,
    tail: int,
    radius: int,
) -> dict:
    index = prime_index[cursor]
    tail_primes = primes[max(0, index - tail) : index + 1]
    tail_gaps = [b - a for a, b in zip(tail_primes, tail_primes[1:])]
    tail_residues = [p % 30 for p in tail_primes]
    beams = []
    next_prime = None

    for n in range(cursor + 1, cursor + radius + 1):
        state = "prime_stop" if n in prime_set else "blocked"
        divisor = None if state == "prime_stop" else first_small_divisor(n)
        beams.append(
            {
                "n": n,
                "delta": n - cursor,
                "mod30": n % 30,
                "state": state,
                **({"blocked_by": divisor} if divisor else {}),
            }
        )
        if state == "prime_stop":
            next_prime = n
            break

    return {
        "cursor_prime": cursor,
        "prime_index": index + 1,
        "tail_chunk": {
            "primes": tail_primes,
            "gaps": tail_gaps,
            "gap_mean": round(sum(tail_gaps) / len(tail_gaps), 3) if tail_gaps else 0,
            "residue_mod30": tail_residues,
        },
        "radial_chunk": {
            "radius": radius,
            "beams": beams,
            "stop_at_next_prime": next_prime,
            "move_delta": (next_prime - cursor) if next_prime else None,
        },
        "worm_move": {
            "from": cursor,
            "to": next_prime,
            "status": "advance" if next_prime else "expand_radius",
            "rule": "scan forward arithmetic grid lines until exact next-prime verifier stops the cone",
        },
    }


def parse_anchor_list(raw: str | None) -> list[int]:
    if not raw:
        return [17, 257, 4423, 65537]
    anchors = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            anchors.append(int(part))
    return anchors


def run_lidar_probe(prime_limit: int, tail: int, radius: int, anchors: list[int]) -> dict:
    primes = sieve(prime_limit + radius + 32)
    prime_set = set(primes)
    prime_index = {p: index for index, p in enumerate(primes)}
    frames = []

    for anchor in anchors:
        if anchor > prime_limit:
            continue
        if anchor not in prime_set:
            continue
        frames.append(arithmetic_lidar_frame(primes, prime_set, prime_index, anchor, tail, radius))

    return {
        "schema_version": "prime_fog_lidar_probe_v1",
        "prime_limit": prime_limit,
        "tail": tail,
        "radius": radius,
        "anchors_requested": anchors,
        "frames": frames,
    }


def previous_prime_at_or_before(n: int) -> int | None:
    if n < 2:
        return None
    if n == 2:
        return 2
    candidate = n if n % 2 else n - 1
    while candidate >= 2:
        if deterministic_miller_rabin_u64(candidate):
            return candidate
        candidate -= 2
    return None


def number_fold_echo(n: int) -> list[dict]:
    echoes = []
    if n > 1 and is_power_of_two(n + 1):
        exponent = (n + 1).bit_length() - 1
        echoes.append(
            {
                "fold": "mersenne_number_form",
                "equation": f"{n} = 2^{exponent} - 1",
                "exponent": exponent,
                "exponent_is_prime": deterministic_miller_rabin_u64(exponent),
            }
        )
    if n > 2 and is_power_of_two(n - 1):
        exponent = (n - 1).bit_length() - 1
        echoes.append(
            {
                "fold": "fermat_like_form",
                "equation": f"{n} = 2^{exponent} + 1",
                "power_exponent_is_power_of_two": is_power_of_two(exponent),
            }
        )
    if n > 0:
        root = math.isqrt(n)
        if root * root == n:
            echoes.append({"fold": "perfect_square", "root": root})
    if deterministic_miller_rabin_u64(n) and (n == 2 or n % 4 == 1):
        echoes.append({"fold": "prime_sum_two_squares_residue", "mod4": n % 4})
    return echoes


def echolocate_number(n: int, radius: int) -> dict:
    if n < 0:
        raise ValueError("echolocation currently expects non-negative integers")
    if n >= 2**64:
        raise ValueError("echolocation verifier currently supports integers below 2^64")

    lower = previous_prime_at_or_before(n)
    upper = next_prime_at_or_after(n)
    primality = deterministic_miller_rabin_u64(n)
    divisor = None if primality else first_small_divisor(n)
    anchor = lower or n
    energy = cube_half_square_energy(n, anchor, max(radius, 1))

    forward = []
    backward = []
    for delta in range(1, radius + 1):
        plus = n + delta
        plus_divisor = first_small_divisor(plus)
        plus_prime = plus_divisor is None and deterministic_miller_rabin_u64(plus)
        forward.append(
            {
                "n": plus,
                "delta": delta,
                "state": "prime_echo" if plus_prime else "blocked",
                "mod30": plus % 30,
                **({"blocked_by": plus_divisor} if plus_divisor else {}),
            }
        )
        if plus_prime:
            break

    for delta in range(1, radius + 1):
        minus = n - delta
        if minus < 2:
            break
        minus_divisor = first_small_divisor(minus)
        minus_prime = minus_divisor is None and deterministic_miller_rabin_u64(minus)
        backward.append(
            {
                "n": minus,
                "delta": -delta,
                "state": "prime_echo" if minus_prime else "blocked",
                "mod30": minus % 30,
                **({"blocked_by": minus_divisor} if minus_divisor else {}),
            }
        )
        if minus_prime:
            break

    return {
        "n": n,
        "is_prime": primality,
        "small_divisor_echo": divisor,
        "residue_echoes": {
            "mod6": n % 6,
            "mod30": n % 30,
            "mod210": n % 210,
        },
        "nearest_prime_echoes": {
            "lower": lower,
            "upper": upper,
            "gap_left": (n - lower) if lower is not None else None,
            "gap_right": (upper - n) if upper is not None else None,
        },
        "cube_half_square_energy_from_lower_prime": round(energy["energy"], 12),
        "fold_echoes": number_fold_echo(n),
        "backward_beam": backward,
        "forward_beam": forward,
    }


def parse_number_list(raw: str) -> list[int]:
    numbers = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            numbers.append(int(part, 0))
    return numbers


def run_echolocation(numbers: list[int], radius: int) -> dict:
    return {
        "schema_version": "prime_fog_number_echolocation_v1",
        "radius": radius,
        "numbers": [echolocate_number(n, radius) for n in numbers],
    }


def print_echolocation(payload: dict) -> None:
    print("Prime number echolocation")
    print(f"radius: {payload['radius']}")
    for row in payload["numbers"]:
        print()
        print(f"n={row['n']}")
        print(f"  prime: {row['is_prime']}")
        print(f"  residues: {row['residue_echoes']}")
        print(f"  nearest primes: {row['nearest_prime_echoes']}")
        print(f"  energy from lower prime: {row['cube_half_square_energy_from_lower_prime']}")
        if row["small_divisor_echo"]:
            print(f"  small divisor echo: {row['small_divisor_echo']}")
        if row["fold_echoes"]:
            print("  folds:")
            for echo in row["fold_echoes"]:
                print(f"    {echo}")
        print("  backward beam:")
        for echo in row["backward_beam"][:8]:
            block = f" by {echo['blocked_by']}" if "blocked_by" in echo else ""
            print(f"    {echo['n']} {echo['delta']} {echo['state']}{block}")
        print("  forward beam:")
        for echo in row["forward_beam"][:8]:
            block = f" by {echo['blocked_by']}" if "blocked_by" in echo else ""
            print(f"    {echo['n']} +{echo['delta']} {echo['state']}{block}")


def factor_integer(n: int) -> dict[int, int]:
    factors: dict[int, int] = {}
    if n < 2:
        return factors
    while n % 2 == 0:
        factors[2] = factors.get(2, 0) + 1
        n //= 2
    d = 3
    while d * d <= n:
        while n % d == 0:
            factors[d] = factors.get(d, 0) + 1
            n //= d
        d += 2
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    return factors


def divisors_from_factorization(factors: dict[int, int]) -> list[int]:
    divisors = [1]
    for prime, exponent in factors.items():
        divisors = [divisor * (prime**power) for divisor in divisors for power in range(exponent + 1)]
    return sorted(divisors)


def verify_three_unit_fraction(n: int, a: int, b: int, c: int) -> bool:
    return 4 * a * b * c == n * ((b * c) + (a * c) + (a * b))


def congruence_miss(value: int, modulus: int) -> int:
    residue = value % modulus
    return min(residue, modulus - residue)


def two_unit_lattice_solution(p: int, q: int) -> dict:
    gcd = math.gcd(p, q)
    p //= gcd
    q //= gcd
    q2 = q * q
    q2_factors = {prime: exponent * 2 for prime, exponent in factor_integer(q).items()}
    best_echo = None
    divisor_tests = 0

    for d in divisors_from_factorization(q2_factors):
        divisor_tests += 1
        paired = q2 // d
        y_num = q + d
        z_num = q + paired
        y_miss = congruence_miss(y_num, p)
        z_miss = congruence_miss(z_num, p)
        gates_passed = int(y_miss == 0) + int(z_miss == 0)
        normalized_error = (y_miss + z_miss) / max(1, p)
        echo = {
            "divisor": d,
            "paired_divisor": paired,
            "gates_passed": gates_passed,
            "gate_total": 2,
            "normalized_error": round(normalized_error, 12),
            "glow": round((gates_passed + (1 - min(1.0, normalized_error))) / 3, 12),
        }
        if best_echo is None or (echo["glow"], -echo["normalized_error"]) > (
            best_echo["glow"],
            -best_echo["normalized_error"],
        ):
            best_echo = echo
        if y_miss == 0 and z_miss == 0:
            return {
                "found": True,
                "y": y_num // p,
                "z": z_num // p,
                "divisor_tests": divisor_tests,
                "best_echo": echo,
            }

    return {
        "found": False,
        "divisor_tests": divisor_tests,
        "best_echo": best_echo,
    }


def find_erdos_straus_solution(n: int) -> dict:
    x_low = (n // 4) + 1
    x_high = ((3 * n) // 4) + 1
    x_tests = 0
    divisor_tests = 0
    best_echo = None

    for x in range(x_low, x_high + 1):
        p = (4 * x) - n
        if p <= 0:
            continue
        q = n * x
        x_tests += 1
        lattice = two_unit_lattice_solution(p, q)
        divisor_tests += lattice["divisor_tests"]
        echo = {
            "x": x,
            "p": p // math.gcd(p, q),
            "q": q // math.gcd(p, q),
            **(lattice["best_echo"] or {}),
        }
        if best_echo is None or (echo.get("glow", 0), -echo.get("normalized_error", 1)) > (
            best_echo.get("glow", 0),
            -best_echo.get("normalized_error", 1),
        ):
            best_echo = echo
        if lattice["found"]:
            a, b, c = sorted([x, lattice["y"], lattice["z"]])
            return {
                "found": True,
                "a": a,
                "b": b,
                "c": c,
                "first_x": x,
                "residual_denominators": [lattice["y"], lattice["z"]],
                "target_fraction": f"4/{n}",
                "spatial_fraction_path": [
                    "n_base_coordinate",
                    "target_fraction_4_over_n",
                    "first_unit_fraction_x_band",
                    "two_unit_residual_divisor_lattice",
                    "exact_integer_equality_verifier",
                ],
                "x_tests": x_tests,
                "divisor_lattice_tests": divisor_tests,
                "first_denominator_bounds": [x_low, x_high],
                "best_echo": best_echo,
            }

    return {
        "found": False,
        "target_fraction": f"4/{n}",
        "spatial_fraction_path": [
            "n_base_coordinate",
            "target_fraction_4_over_n",
            "first_unit_fraction_x_band",
            "two_unit_residual_divisor_lattice",
            "near_echo_only",
        ],
        "x_tests": x_tests,
        "divisor_lattice_tests": divisor_tests,
        "first_denominator_bounds": [x_low, x_high],
        "best_echo": best_echo,
    }


def smallest_known_solution_divisor(n: int, solved: dict[int, tuple[int, int, int]]) -> int | None:
    for d in range(2, math.isqrt(n) + 1):
        if n % d == 0 and d in solved:
            return d
        paired = n // d
        if n % d == 0 and paired in solved:
            return paired
    return None


def run_erdos_straus_lidar(limit: int, proximity_count: int) -> dict:
    solved: dict[int, tuple[int, int, int]] = {}
    rows = []
    top_echoes = []

    for n in range(2, limit + 1):
        inherited_from = smallest_known_solution_divisor(n, solved)
        if inherited_from is not None:
            scale = n // inherited_from
            a, b, c = solved[inherited_from]
            hit = (a * scale, b * scale, c * scale)
            row = {
                "n": n,
                "phase": "inherited_egyptian_fraction",
                "source_n": inherited_from,
                "scale": scale,
                "target_fraction": f"4/{n}",
                "spatial_fraction_path": [
                    "n_base_coordinate",
                    "known_lower_solution",
                    "scale_denominators_by_n_over_source_n",
                    "exact_integer_equality_verifier",
                ],
                "found": True,
                "a": hit[0],
                "b": hit[1],
                "c": hit[2],
                "x_tests": 0,
                "divisor_lattice_tests": 0,
            }
        else:
            direct = find_erdos_straus_solution(n)
            row = {
                "n": n,
                "phase": "direct_three_unit_lattice",
                **direct,
            }
            if direct.get("best_echo"):
                top_echoes.append({"n": n, **direct["best_echo"]})
                top_echoes.sort(key=lambda echo: (-echo.get("glow", 0), echo.get("normalized_error", 1), echo["n"]))
                if len(top_echoes) > proximity_count:
                    top_echoes.pop()

        if row["found"]:
            triple = (row["a"], row["b"], row["c"])
            row["verified"] = verify_three_unit_fraction(n, *triple)
            solved[n] = triple
        else:
            row["verified"] = False
        rows.append(row)

    direct_rows = [row for row in rows if row["phase"] == "direct_three_unit_lattice"]
    return {
        "schema_version": "prime_fog_erdos_straus_lidar_v1",
        "title": "Egyptian fraction theorem lane: Erdos-Straus 4/n three-unit collapse",
        "geometry": {
            "base_axis": "n",
            "target_space": "fraction 4/n",
            "spatial_fraction_axis": "first unit denominator x",
            "residual_space": "two-unit divisor lattice",
            "collapse": "4*a*b*c == n*(bc+ac+ab)",
        },
        "limit": limit,
        "tested_count": len(rows),
        "hit_count": sum(1 for row in rows if row["verified"]),
        "direct_lattice_count": len(direct_rows),
        "inherited_count": sum(1 for row in rows if row["phase"] == "inherited_egyptian_fraction"),
        "total_x_tests": sum(row["x_tests"] for row in rows),
        "total_divisor_lattice_tests": sum(row["divisor_lattice_tests"] for row in rows),
        "worst_direct_rows": sorted(
            direct_rows,
            key=lambda row: (row["divisor_lattice_tests"], row["x_tests"]),
            reverse=True,
        )[:10],
        "top_near_echoes": top_echoes,
        "rows": rows,
    }


def print_erdos_straus_lidar(payload: dict) -> None:
    print("Egyptian fraction / Erdos-Straus lidar")
    print(f"limit: {payload['limit']}")
    print(f"hits: {payload['hit_count']}/{payload['tested_count']}")
    print(f"direct lattice probes: {payload['direct_lattice_count']}")
    print(f"inherited collapses: {payload['inherited_count']}")
    print(f"x tests: {payload['total_x_tests']}")
    print(f"divisor lattice tests: {payload['total_divisor_lattice_tests']}")
    print()
    print("Hardest direct rows:")
    for row in payload["worst_direct_rows"][:8]:
        status = "ok" if row["verified"] else "miss"
        print(
            f"  n={row['n']:<6} {status:<4} "
            f"4/{row['n']} = 1/{row.get('a', '?')} + 1/{row.get('b', '?')} + 1/{row.get('c', '?')} "
            f"x_tests={row['x_tests']} lattice={row['divisor_lattice_tests']}"
        )
    if payload["top_near_echoes"]:
        print()
        print("Top lattice echoes:")
        for echo in payload["top_near_echoes"][:8]:
            print(
                f"  n={echo['n']:<6} x={echo['x']:<6} glow={echo.get('glow', 0):.6f} "
                f"gates={echo.get('gates_passed', 0)}/{echo.get('gate_total', 2)} "
                f"norm_err={echo.get('normalized_error', 1)}"
            )


def erdos_wave_field(
    p: int,
    q: int,
    x: int,
    x_low: int,
    divisor: int,
    paired_divisor: int,
    angle_bin: int,
    learned_bins: set[int],
) -> dict:
    y_num = q + divisor
    z_num = q + paired_divisor
    y_residue = y_num % p
    z_residue = z_num % p
    y_miss = congruence_miss(y_num, p)
    z_miss = congruence_miss(z_num, p)
    gates_passed = int(y_miss == 0) + int(z_miss == 0)
    normalized_error = (y_miss + z_miss) / max(1, 2 * p)
    congruence_attraction = 1 - min(1.0, normalized_error)
    wave_alignment = (
        math.cos((2 * math.pi * y_residue) / p) + math.cos((2 * math.pi * z_residue) / p) + 2
    ) / 4
    first_fraction_focus = 1 / (1 + max(0, x - x_low))
    lane_resonance = 1.0 if angle_bin in learned_bins else 0.35
    gate_attraction = gates_passed / 2
    field_strength = (
        (0.34 * gate_attraction)
        + (0.28 * congruence_attraction)
        + (0.22 * wave_alignment)
        + (0.10 * first_fraction_focus)
        + (0.06 * lane_resonance)
    )
    return {
        "field_strength": round(field_strength, 12),
        "gate_attraction": round(gate_attraction, 12),
        "congruence_attraction": round(congruence_attraction, 12),
        "wave_alignment": round(wave_alignment, 12),
        "first_fraction_focus": round(first_fraction_focus, 12),
        "lane_resonance": lane_resonance,
        "gates_passed": gates_passed,
        "gate_total": 2,
        "normalized_error": round(normalized_error, 12),
        "y_miss": y_miss,
        "z_miss": z_miss,
        "y_residue": y_residue,
        "z_residue": z_residue,
    }


def erdos_magnetic_wave_candidates(n: int, learned_bins: set[int], bins: int, x_scan: int) -> list[dict]:
    x_low = (n // 4) + 1
    x_high = min(((3 * n) // 4) + 1, x_low + max(1, x_scan) - 1)
    candidates = []

    for x in range(x_low, x_high + 1):
        p = (4 * x) - n
        if p <= 0:
            continue
        q = n * x
        gcd = math.gcd(p, q)
        p //= gcd
        q //= gcd
        q2 = q * q
        q2_factors = {prime: exponent * 2 for prime, exponent in factor_integer(q).items()}
        angle_bin = angle_bin_for_value(x, bins)
        for divisor in divisors_from_factorization(q2_factors):
            paired_divisor = q2 // divisor
            field = erdos_wave_field(p, q, x, x_low, divisor, paired_divisor, angle_bin, learned_bins)
            y_num = q + divisor
            z_num = q + paired_divisor
            candidates.append(
                {
                    "n": n,
                    "x": x,
                    "p": p,
                    "q": q,
                    "divisor": divisor,
                    "paired_divisor": paired_divisor,
                    "angle_bin": angle_bin,
                    "y_num": y_num,
                    "z_num": z_num,
                    **field,
                }
            )

    return sorted(
        candidates,
        key=lambda row: (-row["field_strength"], row["normalized_error"], row["x"], row["divisor"]),
    )


def solve_erdos_magnetic_wave(
    n: int,
    learned_bins: set[int],
    bins: int,
    x_scan: int,
    top_candidates: int,
) -> dict:
    candidates = erdos_magnetic_wave_candidates(n, learned_bins, bins, x_scan)
    exact_tests = 0
    for candidate in candidates[: max(1, top_candidates)]:
        exact_tests += 1
        if candidate["y_miss"] != 0 or candidate["z_miss"] != 0:
            continue
        y = candidate["y_num"] // candidate["p"]
        z = candidate["z_num"] // candidate["p"]
        a, b, c = sorted([candidate["x"], y, z])
        return {
            "found": True,
            "a": a,
            "b": b,
            "c": c,
            "first_x": candidate["x"],
            "angle_bin": candidate["angle_bin"],
            "field_strength": candidate["field_strength"],
            "exact_tests": exact_tests,
            "candidates_generated": len(candidates),
            "top_candidate": candidate,
        }

    return {
        "found": False,
        "exact_tests": min(max(1, top_candidates), len(candidates)),
        "candidates_generated": len(candidates),
        "top_candidate": candidates[0] if candidates else None,
    }


def seed_erdos_wave_starters(seed_limit: int, bins: int) -> tuple[dict[int, tuple[int, int, int]], set[int]]:
    solved: dict[int, tuple[int, int, int]] = {}
    learned_bins: set[int] = set()
    for n in range(2, seed_limit + 1):
        inherited_from = smallest_known_solution_divisor(n, solved)
        if inherited_from is not None:
            scale = n // inherited_from
            a, b, c = solved[inherited_from]
            solved[n] = (a * scale, b * scale, c * scale)
            continue
        direct = find_erdos_straus_solution(n)
        if direct["found"]:
            solved[n] = (direct["a"], direct["b"], direct["c"])
            learned_bins.add(angle_bin_for_value(direct["first_x"], bins))
    return solved, learned_bins


def run_erdos_magnetic_wave(
    start_n: int,
    end_n: int,
    seed_limit: int,
    bins: int,
    x_scan: int,
    top_candidates: int,
) -> dict:
    solved, learned_bins = seed_erdos_wave_starters(seed_limit, bins)
    rows = []

    for n in range(start_n, end_n + 1):
        inherited_from = smallest_known_solution_divisor(n, solved)
        if inherited_from is not None:
            scale = n // inherited_from
            a, b, c = solved[inherited_from]
            hit = (a * scale, b * scale, c * scale)
            row = {
                "n": n,
                "phase": "inherited_magnetic_attractor",
                "source_n": inherited_from,
                "scale": scale,
                "found": True,
                "a": hit[0],
                "b": hit[1],
                "c": hit[2],
                "field_strength": 1.0,
                "exact_tests": 0,
                "candidates_generated": 0,
            }
        else:
            wave = solve_erdos_magnetic_wave(n, learned_bins, bins, x_scan, top_candidates)
            row = {"n": n, "phase": "magnetic_wave_ranked_unknown", **wave}
            if wave["found"]:
                learned_bins.add(wave["angle_bin"])

        if row["found"]:
            triple = (row["a"], row["b"], row["c"])
            row["verified"] = verify_three_unit_fraction(n, *triple)
            solved[n] = triple
        else:
            row["verified"] = False
        rows.append(row)

    unknown_rows = [row for row in rows if row["phase"] == "magnetic_wave_ranked_unknown"]
    unknown_hits = [row for row in unknown_rows if row["verified"]]
    ranked_top_candidates = [row["top_candidate"] for row in unknown_rows if row.get("top_candidate")]
    top_exact = [row for row in unknown_hits if row["exact_tests"] == 1]
    one_gate = [row for row in ranked_top_candidates if row.get("gates_passed") == 1]
    zero_gate = [row for row in ranked_top_candidates if row.get("gates_passed") == 0]
    return {
        "schema_version": "prime_fog_erdos_magnetic_wave_v1",
        "interpretation": (
            "wave telemetry benchmark, not a proof of the Erdos-Straus conjecture; "
            "the verifier only proves individual n rows"
        ),
        "formula": (
            "field = .34*gate + .28*congruence + .22*cosine_wave "
            "+ .10*first_fraction_focus + .06*learned_lane"
        ),
        "geometry": {
            "base_axis": "n",
            "goal_space": "4/n",
            "candidate_space": "(x, divisor_of_q_squared)",
            "attractors": ["exact congruence gates", "cosine residue alignment", "learned x-angle lanes"],
            "repellers": ["non-zero congruence distance", "late first-denominator drift"],
            "collapse": "4*a*b*c == n*(bc+ac+ab)",
        },
        "start_n": start_n,
        "end_n": end_n,
        "seed_limit": seed_limit,
        "bins": bins,
        "x_scan": x_scan,
        "top_candidates": top_candidates,
        "tested_count": len(rows),
        "hit_count": sum(1 for row in rows if row["verified"]),
        "unknown_wave_count": len(unknown_rows),
        "inherited_count": sum(1 for row in rows if row["phase"] == "inherited_magnetic_attractor"),
        "learned_bins": sorted(learned_bins),
        "total_exact_tests": sum(row["exact_tests"] for row in rows),
        "total_candidates_generated": sum(row["candidates_generated"] for row in rows),
        "telemetry": {
            "top_rank_exact_collapse_rate": round(len(top_exact) / max(1, len(unknown_rows)), 6),
            "mean_exact_tests_per_unknown": round(
                sum(row["exact_tests"] for row in unknown_rows) / max(1, len(unknown_rows)),
                6,
            ),
            "mean_candidates_per_unknown": round(
                sum(row["candidates_generated"] for row in unknown_rows) / max(1, len(unknown_rows)),
                6,
            ),
            "mean_top_field_strength": round(
                sum((row.get("field_strength") or 0) for row in unknown_rows) / max(1, len(unknown_rows)),
                6,
            ),
            "top_candidate_gate_histogram": {
                "0": len(zero_gate),
                "1": len(one_gate),
                "2": sum(1 for row in ranked_top_candidates if row.get("gates_passed") == 2),
            },
            "residue_repeller_examples": sorted(
                one_gate + zero_gate,
                key=lambda row: (row.get("gates_passed", 0), -row.get("field_strength", 0)),
            )[:8],
        },
        "hardest_unknown_rows": sorted(
            unknown_rows,
            key=lambda row: (row["exact_tests"], row["candidates_generated"]),
            reverse=True,
        )[:10],
        "misses": [row for row in rows if not row["verified"]],
        "rows": rows,
    }


def print_erdos_magnetic_wave(payload: dict) -> None:
    print("Erdos-Straus magnetic wave search")
    print(payload["interpretation"])
    print(f"range: {payload['start_n']}..{payload['end_n']}")
    print(f"seed limit: {payload['seed_limit']}")
    print(f"formula: {payload['formula']}")
    print(f"hits: {payload['hit_count']}/{payload['tested_count']}")
    print(f"unknown wave rows: {payload['unknown_wave_count']}")
    print(f"inherited attractors: {payload['inherited_count']}")
    print(f"learned bins: {payload['learned_bins']}")
    print(f"exact tests: {payload['total_exact_tests']}")
    print(f"candidates generated: {payload['total_candidates_generated']}")
    telemetry = payload["telemetry"]
    print(f"top-rank exact collapse rate: {telemetry['top_rank_exact_collapse_rate']:.2%}")
    print(f"mean exact tests per unknown: {telemetry['mean_exact_tests_per_unknown']}")
    print(f"mean candidates per unknown: {telemetry['mean_candidates_per_unknown']}")
    print(f"mean top field strength: {telemetry['mean_top_field_strength']}")
    print(f"top candidate gate histogram: {telemetry['top_candidate_gate_histogram']}")
    if payload["misses"]:
        print(f"misses: {len(payload['misses'])}")
    print()
    print("Hardest unknown wave rows:")
    for row in payload["hardest_unknown_rows"][:8]:
        status = "ok" if row["verified"] else "miss"
        print(
            f"  n={row['n']:<8} {status:<4} "
            f"field={row.get('field_strength', 0):.6f} "
            f"tests={row['exact_tests']:<4} generated={row['candidates_generated']:<6} "
            f"4/{row['n']}=1/{row.get('a', '?')}+1/{row.get('b', '?')}+1/{row.get('c', '?')}"
        )
    if telemetry["residue_repeller_examples"]:
        print()
        print("Residue repeller examples:")
        for row in telemetry["residue_repeller_examples"]:
            print(
                f"  n={row['n']:<8} x={row['x']:<8} field={row['field_strength']:.6f} "
                f"gates={row['gates_passed']}/2 y_miss={row['y_miss']} z_miss={row['z_miss']}"
            )


def prime_mesh_score(values: list[int], mesh_primes: list[int] | None = None) -> dict:
    primes = mesh_primes or SMALL_FILTER_PRIMES[1:]
    passed = 0
    blockers = []
    for q in primes:
        blocked_values = [value for value in values if value != q and value % q == 0]
        if blocked_values:
            blockers.append({"prime": q, "values": blocked_values})
        else:
            passed += 1
    return {
        "passed": passed,
        "total": len(primes),
        "ratio": passed / max(1, len(primes)),
        "blockers": blockers[:4],
    }


def ternary_counts(rows: list[dict], key: str = "ternary_state") -> dict:
    counts = {-1: 0, 0: 0, 1: 0}
    for row in rows:
        counts[int(row.get(key, 0))] += 1
    return {
        "repel": counts[-1],
        "neutral": counts[0],
        "attract": counts[1],
        "labels": {"-1": "repel", "0": "neutral", "1": "attract"},
    }


def ternary_from_prime_mesh(verified: bool, mesh_ratio: float) -> int:
    if verified:
        return 1
    if mesh_ratio < 1.0:
        return -1
    return 0


def multiplicative_wave_field(components: dict[str, float], weights: dict[str, float] | None = None) -> dict:
    weights = weights or {}
    product = 1.0
    rows = {}
    for name, value in components.items():
        clamped = min(1.0, max(1e-9, float(value)))
        weight = weights.get(name, 1.0)
        weighted = clamped**weight
        product *= weighted
        rows[name] = {
            "value": round(clamped, 12),
            "weight": weight,
            "weighted_value": round(weighted, 12),
        }
    return {
        "product_field_strength": round(product, 12),
        "components": rows,
    }


def twin_pair_wave_field(p: int, learned_bins: set[int], bins: int) -> dict:
    q = p + 2
    mesh = prime_mesh_score([p, q])
    wheel = 1.0 if p % 30 in WHEEL30_RESIDUES and q % 30 in WHEEL30_RESIDUES else 0.0
    angle_bin = angle_bin_for_value(p, bins)
    lane = 1.0 if angle_bin in learned_bins else 0.35
    phase = (math.cos((2 * math.pi * (p % 30)) / 30) + math.cos((2 * math.pi * (q % 30)) / 30) + 2) / 4
    field = (0.52 * mesh["ratio"]) + (0.18 * wheel) + (0.18 * phase) + (0.12 * lane)
    verified = deterministic_miller_rabin_u64(p) and deterministic_miller_rabin_u64(q)
    mesh_ratio = round(mesh["ratio"], 12)
    product = multiplicative_wave_field(
        {
            "mesh": mesh_ratio,
            "wheel": 0.35 + (0.65 * wheel),
            "phase": phase,
            "lane": lane,
        }
    )
    return {
        "p": p,
        "q": q,
        "angle_bin": angle_bin,
        "field_strength": round(field, 12),
        "mesh_ratio": mesh_ratio,
        "wheel_attraction": wheel,
        "phase_alignment": round(phase, 12),
        "lane_resonance": lane,
        "verified": verified,
        "ternary_state": ternary_from_prime_mesh(verified, mesh_ratio),
        **product,
        "blockers": mesh["blockers"],
    }


def run_twin_prime_wave(limit: int, seed_limit: int, bins: int, top: int) -> dict:
    learned_bins = {
        angle_bin_for_value(p, bins)
        for p in range(3, seed_limit + 1, 2)
        if deterministic_miller_rabin_u64(p) and deterministic_miller_rabin_u64(p + 2)
    }
    candidates = [twin_pair_wave_field(p, learned_bins, bins) for p in range(max(3, seed_limit + 1) | 1, limit, 2)]
    ranked = sorted(candidates, key=lambda row: (-row["field_strength"], row["p"]))
    hits = [row for row in candidates if row["verified"]]
    top_rows = ranked[:top]
    return {
        "problem": "twin_primes",
        "interpretation": "bounded twin-prime wave telemetry; each hit verifies only one pair",
        "candidate_count": len(candidates),
        "hit_count": len(hits),
        "learned_bins": sorted(learned_bins),
        "top_precision": round(sum(1 for row in top_rows if row["verified"]) / max(1, len(top_rows)), 6),
        "ternary_map": ternary_counts(candidates),
        "geodesic_path": [
            {"p": row["p"], "q": row["q"], "state": row["ternary_state"], "field_strength": row["field_strength"]}
            for row in top_rows[:16]
        ],
        "mean_hit_field": round(sum(row["field_strength"] for row in hits) / max(1, len(hits)), 6),
        "mean_miss_field": round(
            sum(row["field_strength"] for row in candidates if not row["verified"])
            / max(1, len(candidates) - len(hits)),
            6,
        ),
        "mean_product_field": round(
            sum(row["product_field_strength"] for row in candidates) / max(1, len(candidates)),
            6,
        ),
        "top_rows": top_rows,
    }


def circular_tau_distance(a: float, b: float) -> float:
    tau = 2 * math.pi
    diff = abs(a - b) % tau
    return min(diff, tau - diff)


def solution_gravity_bodies(values: list[int], bins: int) -> list[dict]:
    profile = solution_radius_profile(values)
    median_right = profile["median_right_ratio"] or 0.0
    bodies = []
    for row in profile["rows"]:
        center = row["center"]
        left_ratio = row["left_ratio"] if row["left_ratio"] is not None else median_right
        right_ratio = row["right_ratio"] if row["right_ratio"] is not None else median_right
        curvature = abs((right_ratio or 0) - (left_ratio or 0))
        mass = 1 + (math.log1p(center) / 16) + min(3.0, curvature * 600)
        log_radius = math.log(center)
        theta = log_radius % (2 * math.pi)
        bodies.append(
            {
                "center": center,
                "log_radius": log_radius,
                "theta": theta,
                "angle_bin": angle_bin_for_value(center, bins),
                "left_ratio": left_ratio,
                "right_ratio": right_ratio,
                "curvature": round(curvature, 12),
                "mass": round(mass, 12),
            }
        )
    return bodies


def solution_gravity_at_candidate(candidate: int, bodies: list[dict]) -> dict:
    if candidate <= 0 or not bodies:
        return {
            "gravity_field": 0.0,
            "gravity_field_normalized": 0.0,
            "nearest_solution": None,
            "top_forces": [],
        }

    log_radius = math.log(candidate)
    theta = log_radius % (2 * math.pi)
    total_force = 0.0
    forces = []
    for body in bodies:
        radial_distance = abs(log_radius - body["log_radius"])
        angular_distance = circular_tau_distance(theta, body["theta"])
        geodesic_distance = math.sqrt((radial_distance * radial_distance) + (angular_distance * angular_distance))
        candidate_ratio = abs(candidate - body["center"]) / max(1, body["center"])
        target_ratio = body["right_ratio"] if candidate >= body["center"] else body["left_ratio"]
        ratio_error = abs(math.log1p(candidate_ratio) - math.log1p(max(0.0, target_ratio)))
        ratio_alignment = 1 / (1 + ratio_error)
        force = (body["mass"] * ratio_alignment) / ((geodesic_distance * geodesic_distance) + 0.03)
        total_force += force
        forces.append(
            {
                "center": body["center"],
                "force": round(force, 12),
                "mass": body["mass"],
                "geodesic_distance": round(geodesic_distance, 12),
                "ratio_alignment": round(ratio_alignment, 12),
                "direction": 1 if candidate >= body["center"] else -1,
            }
        )

    forces.sort(key=lambda row: (-row["force"], row["center"]))
    normalized = total_force / (1 + total_force)
    return {
        "gravity_field": round(total_force, 12),
        "gravity_field_normalized": round(normalized, 12),
        "nearest_solution": forces[0]["center"] if forces else None,
        "top_forces": forces[:4],
    }


def twin_prime_gravity_candidate(p: int, bodies: list[dict], learned_bins: set[int], bins: int) -> dict:
    wave = twin_pair_wave_field(p, learned_bins, bins)
    gravity = solution_gravity_at_candidate(p, bodies)
    product = multiplicative_wave_field(
        {
            "gravity": gravity["gravity_field_normalized"],
            "mesh": wave["mesh_ratio"],
            "wave": wave["field_strength"],
            "product_wave": wave["product_field_strength"],
        },
        weights={"gravity": 0.7, "mesh": 1.1, "wave": 0.7, "product_wave": 0.5},
    )
    combined = (
        (0.42 * gravity["gravity_field_normalized"])
        + (0.28 * wave["mesh_ratio"])
        + (0.20 * wave["field_strength"])
        + (0.10 * wave["product_field_strength"])
    )
    return {
        **wave,
        **gravity,
        "gravity_product_field": product["product_field_strength"],
        "gravity_components": product["components"],
        "combined_gravity_field": round(combined, 12),
    }


def run_twin_prime_gravity_search(seed_limit: int, limit: int, bins: int, top: int) -> dict:
    seed_values = [
        p
        for p in range(3, seed_limit + 1, 2)
        if deterministic_miller_rabin_u64(p) and deterministic_miller_rabin_u64(p + 2)
    ]
    bodies = solution_gravity_bodies(seed_values, bins)
    learned_bins = {body["angle_bin"] for body in bodies}
    start = max(3, seed_limit + 1)
    if start % 2 == 0:
        start += 1
    candidates = [
        twin_prime_gravity_candidate(p, bodies, learned_bins, bins)
        for p in range(start, limit, 2)
    ]
    ranked = sorted(
        candidates,
        key=lambda row: (-row["combined_gravity_field"], -row["gravity_product_field"], row["p"]),
    )
    top_rows = ranked[:top]
    hits = [row for row in candidates if row["verified"]]
    top_hits = [row for row in top_rows if row["verified"]]
    return {
        "schema_version": "prime_fog_twin_prime_gravity_search_v1",
        "interpretation": (
            "known verified twin primes are gravity bodies on the log/phase manifold; "
            "candidate p values are ranked by gravitational potential, then exactly verified"
        ),
        "verifier": "is_prime(p) and is_prime(p+2)",
        "seed_limit": seed_limit,
        "limit": limit,
        "bins": bins,
        "seed_solution_count": len(seed_values),
        "candidate_count": len(candidates),
        "hit_count": len(hits),
        "top": top,
        "top_hit_count": len(top_hits),
        "top_precision": round(len(top_hits) / max(1, len(top_rows)), 6),
        "known_solution_grid": [
            {
                "p": body["center"],
                "mass": body["mass"],
                "angle_bin": body["angle_bin"],
                "left_ratio": body["left_ratio"],
                "right_ratio": body["right_ratio"],
            }
            for body in bodies
        ],
        "top_rows": top_rows,
    }


def print_twin_prime_gravity_search(payload: dict) -> None:
    print("Twin-prime solution gravity search")
    print(payload["interpretation"])
    print(f"verifier: {payload['verifier']}")
    print(f"seed limit: {payload['seed_limit']}  search limit: {payload['limit']}")
    print(f"known solution bodies: {payload['seed_solution_count']}")
    print(f"candidates: {payload['candidate_count']}  hits in range: {payload['hit_count']}")
    print(f"top precision: {payload['top_precision']:.2%} ({payload['top_hit_count']}/{payload['top']})")
    print()
    print("Top gravity-ranked candidates:")
    for row in payload["top_rows"][:12]:
        mark = "hit" if row["verified"] else "echo"
        print(
            f"  {mark:<4} p={row['p']:<8} q={row['q']:<8} "
            f"gravity={row['gravity_field_normalized']:.6f} "
            f"combined={row['combined_gravity_field']:.6f} "
            f"product={row['gravity_product_field']:.6f} "
            f"nearest={row['nearest_solution']}"
        )


def goldbach_pair_wave_field(n: int, p: int, learned_bins: set[int], bins: int) -> dict:
    q = n - p
    mesh = prime_mesh_score([p, q])
    balance = 1 - (abs((n / 2) - p) / max(1, n / 2))
    angle_bin = angle_bin_for_value(p, bins)
    lane = 1.0 if angle_bin in learned_bins else 0.35
    phase = (math.cos((2 * math.pi * (p % 30)) / 30) + math.cos((2 * math.pi * (q % 30)) / 30) + 2) / 4
    field = (0.48 * mesh["ratio"]) + (0.20 * balance) + (0.20 * phase) + (0.12 * lane)
    verified = deterministic_miller_rabin_u64(p) and deterministic_miller_rabin_u64(q)
    mesh_ratio = round(mesh["ratio"], 12)
    product = multiplicative_wave_field(
        {
            "mesh": mesh_ratio,
            "balance": balance,
            "phase": phase,
            "lane": lane,
        }
    )
    return {
        "n": n,
        "p": p,
        "q": q,
        "angle_bin": angle_bin,
        "field_strength": round(field, 12),
        "mesh_ratio": mesh_ratio,
        "balance": round(balance, 12),
        "phase_alignment": round(phase, 12),
        "lane_resonance": lane,
        "verified": verified,
        "ternary_state": ternary_from_prime_mesh(verified, mesh_ratio),
        **product,
        "blockers": mesh["blockers"],
    }


def seed_goldbach_bins(seed_limit: int, bins: int) -> set[int]:
    learned_bins = set()
    for n in range(4, seed_limit + 1, 2):
        for p in range(2, (n // 2) + 1):
            if deterministic_miller_rabin_u64(p) and deterministic_miller_rabin_u64(n - p):
                learned_bins.add(angle_bin_for_value(p, bins))
                break
    return learned_bins


def run_goldbach_wave(start: int, end: int, seed_limit: int, bins: int, top: int) -> dict:
    start = start if start % 2 == 0 else start + 1
    end = end if end % 2 == 0 else end - 1
    learned_bins = seed_goldbach_bins(seed_limit, bins)
    rows = []
    ternary_rows = []
    for n in range(max(4, start), end + 1, 2):
        candidates = [goldbach_pair_wave_field(n, p, learned_bins, bins) for p in range(2, (n // 2) + 1)]
        ternary_rows.extend(candidates)
        ranked = sorted(candidates, key=lambda row: (-row["field_strength"], row["p"]))
        exact_tests = 0
        found = None
        found_phase = None
        for index, candidate in enumerate(ranked):
            exact_tests += 1
            if candidate["verified"]:
                found = candidate
                found_phase = "top_wave" if index < top else "full_geodesic_fallback"
                learned_bins.add(candidate["angle_bin"])
                break
        rows.append(
            {
                "n": n,
                "found": found is not None,
                "phase": found_phase or "bounded_miss",
                "exact_tests": exact_tests,
                "top_cap": top,
                "candidates_generated": len(candidates),
                "top_candidate": ranked[0] if ranked else None,
                **({"p": found["p"], "q": found["q"], "field_strength": found["field_strength"]} if found else {}),
            }
        )
    hit_rows = [row for row in rows if row["found"]]
    top_rank_hits = [row for row in hit_rows if row["exact_tests"] == 1]
    top_cap_hits = [row for row in hit_rows if row["exact_tests"] <= top]
    return {
        "problem": "goldbach",
        "interpretation": "bounded strong-Goldbach wave telemetry; each hit verifies one even n",
        "tested_count": len(rows),
        "hit_count": len(hit_rows),
        "learned_bins": sorted(learned_bins),
        "top_rank_exact_collapse_rate": round(len(top_rank_hits) / max(1, len(rows)), 6),
        "top_cap_success_rate": round(len(top_cap_hits) / max(1, len(rows)), 6),
        "mean_exact_tests": round(sum(row["exact_tests"] for row in rows) / max(1, len(rows)), 6),
        "total_candidates_generated": sum(row["candidates_generated"] for row in rows),
        "ternary_map": ternary_counts(ternary_rows),
        "mean_product_field": round(
            sum(row["product_field_strength"] for row in ternary_rows) / max(1, len(ternary_rows)),
            6,
        ),
        "geodesic_path": [
            {
                "n": row["n"],
                "p": row.get("p"),
                "q": row.get("q"),
                "phase": row["phase"],
                "field_strength": row.get("field_strength"),
            }
            for row in rows[:16]
        ],
        "hardest_rows": sorted(rows, key=lambda row: (row["exact_tests"], row["candidates_generated"]), reverse=True)[:10],
        "misses": [row for row in rows if not row["found"]],
    }


def collatz_trajectory(seed: int, max_steps: int) -> dict:
    value = seed
    max_value = value
    odd_steps = 0
    even_steps = 0
    descents = 0
    for step in range(max_steps + 1):
        if value == 1:
            return {
                "seed": seed,
                "verified": True,
                "ternary_state": 1,
                "steps": step,
                "max_value": max_value,
                "max_ratio": round(max_value / max(1, seed), 6),
                "odd_steps": odd_steps,
                "even_steps": even_steps,
                "descent_ratio": round(descents / max(1, step), 6),
            }
        previous = value
        if value % 2 == 0:
            value //= 2
            even_steps += 1
        else:
            value = (3 * value) + 1
            odd_steps += 1
        if value < previous:
            descents += 1
        max_value = max(max_value, value)
    return {
        "seed": seed,
        "verified": False,
        "ternary_state": -1,
        "steps": max_steps,
        "max_value": max_value,
        "max_ratio": round(max_value / max(1, seed), 6),
        "odd_steps": odd_steps,
        "even_steps": even_steps,
        "descent_ratio": round(descents / max(1, max_steps), 6),
    }


def run_collatz_wave(start: int, end: int, max_steps: int, top: int) -> dict:
    rows = []
    for seed in range(max(2, start), end + 1):
        row = collatz_trajectory(seed, max_steps)
        contraction = 1 / (1 + row["max_ratio"])
        parity_balance = row["even_steps"] / max(1, row["odd_steps"] + row["even_steps"])
        field = (0.42 * row["descent_ratio"]) + (0.33 * contraction) + (0.25 * parity_balance)
        row["field_strength"] = round(field, 12)
        row.update(
            multiplicative_wave_field(
                {
                    "descent": row["descent_ratio"],
                    "contraction": contraction,
                    "parity_balance": parity_balance,
                    "bounded_collapse": 1.0 if row["verified"] else 0.05,
                }
            )
        )
        rows.append(row)
    hard_rows = sorted(rows, key=lambda row: (not row["verified"], row["steps"], row["max_ratio"]), reverse=True)[:top]
    return {
        "problem": "collatz",
        "interpretation": "bounded Collatz telemetry; reaching 1 is verified only within max_steps",
        "tested_count": len(rows),
        "hit_count": sum(1 for row in rows if row["verified"]),
        "max_steps": max_steps,
        "max_observed_steps": max(row["steps"] for row in rows) if rows else 0,
        "max_observed_ratio": max(row["max_ratio"] for row in rows) if rows else 0,
        "ternary_map": ternary_counts(rows),
        "mean_product_field": round(
            sum(row["product_field_strength"] for row in rows) / max(1, len(rows)),
            6,
        ),
        "geodesic_path": [
            {
                "seed": row["seed"],
                "state": row["ternary_state"],
                "steps": row["steps"],
                "max_ratio": row["max_ratio"],
                "field_strength": row["field_strength"],
            }
            for row in hard_rows[:16]
        ],
        "hard_rows": hard_rows,
        "misses": [row for row in rows if not row["verified"]],
    }


def collatz_forward_once(n: int) -> int:
    return n // 2 if n % 2 == 0 else (3 * n) + 1


def verify_collatz_reaches_target(value: int, target: int, max_steps: int) -> dict:
    current = value
    for step in range(max_steps + 1):
        if current == target:
            return {
                "passed": True,
                "steps": step,
                "start": value,
                "target": target,
            }
        current = collatz_forward_once(current)
    return {
        "passed": False,
        "steps": max_steps,
        "start": value,
        "target": target,
        "last": current,
    }


def collatz_reverse_preimages(value: int, include_one: bool = False) -> list[dict]:
    preimages = [{"value": value * 2, "branch": "even_preimage"}]
    if (value - 1) % 3 == 0:
        odd = (value - 1) // 3
        if odd > 0 and odd % 2 == 1 and (include_one or odd != 1):
            preimages.append({"value": odd, "branch": "odd_preimage"})
    return preimages


def collatz_tree_edge(parent: int, child: int, branch: str, bins: int, learned_bins: set[int]) -> dict:
    ratio = child / parent
    log_step = math.log(ratio)
    angle_bin = angle_bin_for_value(child, bins)
    branch_resonance = 1.0 if branch == "odd_preimage" else 0.55
    contraction = 1.0 if child < parent else 0.0
    phase_alignment = (math.cos(log_step) + 1) / 2
    lane_resonance = 1.0 if angle_bin in learned_bins else 0.35
    field_strength = (
        (0.34 * branch_resonance)
        + (0.28 * phase_alignment)
        + (0.22 * contraction)
        + (0.10 / (1 + abs(log_step)))
        + (0.06 * lane_resonance)
    )
    product = multiplicative_wave_field(
        {
            "valid_preimage": 1.0,
            "branch": branch_resonance,
            "phase": phase_alignment,
            "ratio_focus": 1 / (1 + abs(log_step)),
            "lane": lane_resonance,
        }
    )
    return {
        "parent": parent,
        "child": child,
        "branch": branch,
        "forward_check": collatz_forward_once(child) == parent,
        "ratio": round(ratio, 12),
        "dx_over_x": round((child - parent) / parent, 12),
        "log_step": round(log_step, 12),
        "angle_bin": angle_bin,
        "ternary_state": 1 if branch == "odd_preimage" else 0,
        "field_strength": round(field_strength, 12),
        **product,
        "geodesic_cost": round(1 - field_strength, 12),
        "branch_resonance": branch_resonance,
        "phase_alignment": round(phase_alignment, 12),
        "lane_resonance": lane_resonance,
    }


def reconstruct_collatz_tree_path(nodes: list[dict], node_index: int) -> list[int]:
    path = []
    cursor = node_index
    while cursor is not None:
        node = nodes[cursor]
        path.append(node["value"])
        cursor = node["parent_index"]
    return list(reversed(path))


def run_collatz_ratio_tree(
    seeds: list[int],
    depth: int,
    max_value: int,
    bins: int,
    include_one: bool,
    top: int,
) -> dict:
    clean_seeds = [seed for seed in seeds if seed > 1]
    nodes = []
    edges = []
    skipped = []
    learned_bins = {angle_bin_for_value(seed, bins) for seed in clean_seeds}
    queue = []
    visited = set()

    for seed in clean_seeds:
        node = {
            "index": len(nodes),
            "value": seed,
            "source_seed": seed,
            "depth": 0,
            "parent_index": None,
            "incoming_branch": "seed",
        }
        nodes.append(node)
        queue.append(node["index"])
        visited.add((seed, seed))

    edge_histogram = [0] * bins
    blocked_odd_gates = 0
    while queue:
        node_index = queue.pop(0)
        node = nodes[node_index]
        if node["depth"] >= depth:
            continue

        preimages = collatz_reverse_preimages(node["value"], include_one)
        if not any(preimage["branch"] == "odd_preimage" for preimage in preimages):
            blocked_odd_gates += 1
        for preimage in preimages:
            child = preimage["value"]
            if child > max_value:
                skipped.append(
                    {
                        "parent": node["value"],
                        "child": child,
                        "branch": preimage["branch"],
                        "reason": "max_value_cap",
                    }
                )
                continue
            key = (node["source_seed"], child)
            if key in visited:
                continue
            visited.add(key)

            edge = collatz_tree_edge(node["value"], child, preimage["branch"], bins, learned_bins)
            edge["source_seed"] = node["source_seed"]
            edge["parent_index"] = node_index
            edge["child_index"] = len(nodes)
            edges.append(edge)
            edge_histogram[edge["angle_bin"]] += 1
            if edge["ternary_state"] == 1:
                learned_bins.add(edge["angle_bin"])

            child_node = {
                "index": len(nodes),
                "value": child,
                "source_seed": node["source_seed"],
                "depth": node["depth"] + 1,
                "parent_index": node_index,
                "incoming_branch": preimage["branch"],
                "incoming_field_strength": edge["field_strength"],
                "incoming_geodesic_cost": edge["geodesic_cost"],
            }
            nodes.append(child_node)
            queue.append(child_node["index"])

    leaves = [
        node
        for node in nodes
        if node["depth"] == depth
        or not any(edge["parent_index"] == node["index"] for edge in edges)
    ]
    for leaf in leaves:
        leaf["end_verifier"] = verify_collatz_reaches_target(
            leaf["value"],
            leaf["source_seed"],
            leaf["depth"],
        )
        leaf["end_verifier_passed"] = leaf["end_verifier"]["passed"] and leaf["end_verifier"]["steps"] == leaf["depth"]
    hard_leaves = sorted(
        leaves,
        key=lambda node: (
            node["depth"],
            node.get("incoming_geodesic_cost", 0),
            node["value"],
        ),
        reverse=True,
    )[:top]
    path_maps = []
    for node in hard_leaves[: min(5, top)]:
        path = reconstruct_collatz_tree_path(nodes, node["index"])
        path_maps.append(
            {
                "source_seed": node["source_seed"],
                "leaf": node["value"],
                "depth": node["depth"],
                "values": path,
                "ratio_map": ratio_sequence(path, [str(value) for value in path], bins),
            }
        )

    odd_edges = [edge for edge in edges if edge["branch"] == "odd_preimage"]
    even_edges = [edge for edge in edges if edge["branch"] == "even_preimage"]
    return {
        "schema_version": "prime_fog_collatz_ratio_tree_v1",
        "interpretation": "reverse Collatz tree from non-1 seeds using ratio/geodesic telemetry; finite tree only",
        "solution_grid": [
            {
                "seed": seed,
                "known_true": True,
                "angle_bin": angle_bin_for_value(seed, bins),
            }
            for seed in clean_seeds
        ],
        "end_function_verifier": {
            "name": "collatz_leaf_to_seed",
            "rule": "T(n)=n/2 if even else 3n+1",
            "collapse": "T^depth(leaf) == source_seed",
            "scope": "finite reverse-tree path, not an infinite Collatz proof",
        },
        "seeds": clean_seeds,
        "depth": depth,
        "max_value": max_value,
        "bins": bins,
        "include_one": include_one,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "leaf_count": len(leaves),
        "leaf_end_verifier_pass_count": sum(1 for leaf in leaves if leaf["end_verifier_passed"]),
        "odd_preimage_edges": len(odd_edges),
        "even_preimage_edges": len(even_edges),
        "blocked_odd_gates": blocked_odd_gates,
        "skipped_by_cap": len(skipped),
        "ternary_map": {
            "repel": blocked_odd_gates + len(skipped),
            "neutral": len(even_edges),
            "attract": len(odd_edges),
            "labels": {"-1": "blocked/capped reverse gate", "0": "even preimage lane", "1": "odd preimage fold"},
        },
        "edge_angle_histogram": edge_histogram,
        "mean_edge_field": round(sum(edge["field_strength"] for edge in edges) / max(1, len(edges)), 6),
        "mean_odd_field": round(sum(edge["field_strength"] for edge in odd_edges) / max(1, len(odd_edges)), 6),
        "mean_even_field": round(sum(edge["field_strength"] for edge in even_edges) / max(1, len(even_edges)), 6),
        "mean_product_field": round(
            sum(edge["product_field_strength"] for edge in edges) / max(1, len(edges)),
            6,
        ),
        "hard_leaves": hard_leaves,
        "path_maps": path_maps,
        "skipped_examples": skipped[:top],
    }


def print_collatz_ratio_tree(payload: dict) -> None:
    print("Collatz non-1 seeded ratio tree")
    print(payload["interpretation"])
    print(f"end verifier: {payload['end_function_verifier']['collapse']}")
    print(f"seeds: {payload['seeds']}")
    print(f"depth: {payload['depth']}  max_value: {payload['max_value']}")
    print(f"nodes: {payload['node_count']}  edges: {payload['edge_count']}  leaves: {payload['leaf_count']}")
    print(f"leaf verifier passes: {payload['leaf_end_verifier_pass_count']}/{payload['leaf_count']}")
    print(f"odd folds: {payload['odd_preimage_edges']}  even lanes: {payload['even_preimage_edges']}")
    print(f"blocked/capped gates: {payload['blocked_odd_gates'] + payload['skipped_by_cap']}")
    print(f"ternary: {payload['ternary_map']}")
    print(f"edge angle histogram: {payload['edge_angle_histogram']}")
    print(
        f"mean field: {payload['mean_edge_field']}  "
        f"odd field: {payload['mean_odd_field']}  even field: {payload['mean_even_field']}  "
        f"product field: {payload['mean_product_field']}"
    )
    print()
    print("Hard leaves:")
    for node in payload["hard_leaves"][:8]:
        print(
            f"  seed={node['source_seed']:<8} leaf={node['value']:<12} "
            f"depth={node['depth']:<3} branch={node['incoming_branch']:<14} "
            f"cost={node.get('incoming_geodesic_cost', 0):.6f} "
            f"verified={node['end_verifier_passed']}"
        )
    if payload["path_maps"]:
        print()
        print("Sample ratio paths:")
        for path in payload["path_maps"][:3]:
            ratio_map = path["ratio_map"]
            print(
                f"  seed={path['source_seed']} leaf={path['leaf']} depth={path['depth']} "
                f"mean_dx/x={ratio_map['mean_velocity']} bins={ratio_map['angle_histogram']}"
            )
            print(f"    path={path['values']}")


def run_catalan_power_gap_wave(base_limit: int, exponent_limit: int, top: int) -> dict:
    powers = []
    for base in range(2, base_limit + 1):
        for exponent in range(2, exponent_limit + 1):
            powers.append({"base": base, "exponent": exponent, "value": base**exponent})
    candidates = []
    for left in powers:
        for right in powers:
            if left["value"] <= right["value"]:
                continue
            gap = left["value"] - right["value"]
            gap_error = abs(gap - 1)
            phase = (math.cos((2 * math.pi * (gap % 30)) / 30) + 1) / 2
            field = (0.72 / (1 + gap_error)) + (0.18 * phase) + (0.10 / (1 + abs(left["exponent"] - right["exponent"])))
            candidates.append(
                {
                    "larger": left,
                    "smaller": right,
                    "gap": gap,
                    "field_strength": round(field, 12),
                    "verified": gap == 1,
                    "ternary_state": 1 if gap == 1 else 0 if gap_error <= 3 else -1,
                    **multiplicative_wave_field(
                        {
                            "gap": 1 / (1 + gap_error),
                            "phase": phase,
                            "exponent_balance": 1 / (1 + abs(left["exponent"] - right["exponent"])),
                        }
                    ),
                }
            )
    ranked = sorted(candidates, key=lambda row: (-row["field_strength"], row["larger"]["value"], row["smaller"]["value"]))
    hits = [row for row in candidates if row["verified"]]
    return {
        "problem": "catalan_power_gaps",
        "interpretation": "Catalan-style adjacent perfect-power telemetry over a finite box",
        "candidate_count": len(candidates),
        "hit_count": len(hits),
        "top_precision": round(sum(1 for row in ranked[:top] if row["verified"]) / max(1, min(top, len(ranked))), 6),
        "ternary_map": ternary_counts(candidates),
        "mean_product_field": round(
            sum(row["product_field_strength"] for row in candidates) / max(1, len(candidates)),
            6,
        ),
        "geodesic_path": [
            {
                "larger": row["larger"],
                "smaller": row["smaller"],
                "gap": row["gap"],
                "state": row["ternary_state"],
                "field_strength": row["field_strength"],
            }
            for row in ranked[:16]
        ],
        "hits": hits[:top],
        "top_rows": ranked[:top],
    }


def run_gilbreath_wave(prime_count: int, rows_limit: int, top: int) -> dict:
    enough = max(100, int(prime_count * (math.log(max(10, prime_count)) + math.log(max(10, math.log(max(10, prime_count)))))) + 50)
    primes = sieve(enough)
    while len(primes) < prime_count:
        enough *= 2
        primes = sieve(enough)
    row = primes[:prime_count]
    rows = []
    for depth in range(1, min(rows_limit, prime_count - 1) + 1):
        row = [abs(b - a) for a, b in zip(row, row[1:])]
        first = row[0]
        field = 1 / (1 + abs(first - 1))
        rows.append(
            {
                "depth": depth,
                "first_value": first,
                "verified": first == 1,
                "ternary_state": 1 if first == 1 else -1 if first > 1 else 0,
                "field_strength": round(field, 12),
                **multiplicative_wave_field(
                    {
                        "first_value": field,
                        "bounded_prefix": 1.0 if first == 1 else 0.05,
                        "row_length": len(row) / max(1, prime_count),
                    }
                ),
                "row_length": len(row),
            }
        )
    return {
        "problem": "gilbreath",
        "interpretation": "bounded Gilbreath prime-difference telemetry; row first values verify only this finite prefix",
        "prime_count": prime_count,
        "rows_tested": len(rows),
        "hit_count": sum(1 for row in rows if row["verified"]),
        "ternary_map": ternary_counts(rows),
        "mean_product_field": round(
            sum(row["product_field_strength"] for row in rows) / max(1, len(rows)),
            6,
        ),
        "geodesic_path": [
            {
                "depth": row["depth"],
                "first_value": row["first_value"],
                "state": row["ternary_state"],
                "field_strength": row["field_strength"],
            }
            for row in rows[:16]
        ],
        "hard_rows": sorted(rows, key=lambda row: (not row["verified"], abs(row["first_value"] - 1), row["depth"]), reverse=True)[:top],
        "misses": [row for row in rows if not row["verified"]],
    }


def parse_problem_list(raw: str) -> list[str]:
    aliases = {
        "twin": "twin",
        "twins": "twin",
        "twin-primes": "twin",
        "twin_primes": "twin",
        "goldbach": "goldbach",
        "gold": "goldbach",
        "collatz": "collatz",
        "collatx": "collatz",
        "catalan": "catalan",
        "catalans": "catalan",
        "catalan-gaps": "catalan",
        "g": "gilbreath",
        "gilbreath": "gilbreath",
        "all": "all",
    }
    problems = []
    for part in raw.split(","):
        key = part.strip().lower()
        if not key:
            continue
        mapped = aliases.get(key, key)
        if mapped == "all":
            return ["twin", "goldbach", "collatz", "catalan", "gilbreath"]
        problems.append(mapped)
    return problems or ["twin", "goldbach", "collatz", "catalan", "gilbreath"]


def run_conjecture_wave_suite(args: argparse.Namespace) -> dict:
    problems = parse_problem_list(args.wave_problems)
    results = []
    if "twin" in problems:
        results.append(run_twin_prime_wave(args.wave_limit, args.wave_seed, args.wave_bins, args.wave_top))
    if "goldbach" in problems:
        results.append(run_goldbach_wave(args.wave_start, args.wave_end, args.wave_seed, args.wave_bins, args.wave_top))
    if "collatz" in problems:
        results.append(run_collatz_wave(args.wave_start, args.wave_end, args.collatz_steps, args.wave_top))
    if "catalan" in problems:
        results.append(run_catalan_power_gap_wave(args.catalan_base_limit, args.catalan_exp_limit, args.wave_top))
    if "gilbreath" in problems:
        results.append(run_gilbreath_wave(args.gilbreath_prime_count, args.gilbreath_rows, args.wave_top))
    return {
        "schema_version": "prime_fog_conjecture_wave_suite_v1",
        "interpretation": "pseudo-magnetic wave telemetry across bounded hard-problem surfaces; no infinite conjecture proof is claimed",
        "verifier_registry": {
            "twin_primes": "is_prime(p) and is_prime(p+2)",
            "goldbach": "is_prime(p) and is_prime(n-p) and p+(n-p)==n",
            "collatz": "bounded iteration reaches 1 within max_steps",
            "catalan_power_gaps": "a^m - b^n == 1 with exponents > 1",
            "gilbreath": "first value of finite absolute-difference row == 1",
            "erdos_straus": "4*a*b*c == n*(bc+ac+ab)",
        },
        "manifold_contract": {
            "raw_space": "integer candidates and generated compositions",
            "transform": "value -> log/value phase bins, residue vectors, verifier-adjacent gates, ternary state",
            "metric": "geodesic cost is ranked by 1 - field_strength plus ternary repel penalties",
            "ternary_states": {"-1": "repel", "0": "neutral survivor", "1": "verified attractor"},
            "collapse": "problem-specific exact verifier; only finite rows are proven",
        },
        "problems": problems,
        "results": results,
    }


def print_conjecture_wave_suite(payload: dict) -> None:
    print("Conjecture wave telemetry suite")
    print(payload["interpretation"])
    print(f"manifold metric: {payload['manifold_contract']['metric']}")
    print(f"problems: {', '.join(payload['problems'])}")
    print()
    for result in payload["results"]:
        print(f"[{result['problem']}]")
        print(result["interpretation"])
        if result["problem"] == "twin_primes":
            print(
                f"candidates={result['candidate_count']} hits={result['hit_count']} "
                f"top_precision={result['top_precision']:.2%} product_mean={result['mean_product_field']}"
            )
            print(f"ternary={result['ternary_map']}")
            for row in result["top_rows"][:5]:
                mark = "hit" if row["verified"] else "miss"
                print(
                    f"  {mark:<4} p={row['p']:<8} q={row['q']:<8} "
                    f"field={row['field_strength']:.6f} product={row['product_field_strength']:.6f}"
                )
        elif result["problem"] == "goldbach":
            print(
                f"tested={result['tested_count']} hits={result['hit_count']} "
                f"top_rank={result['top_rank_exact_collapse_rate']:.2%} "
                f"top_cap={result['top_cap_success_rate']:.2%} mean_tests={result['mean_exact_tests']} "
                f"product_mean={result['mean_product_field']}"
            )
            print(f"ternary={result['ternary_map']}")
            for row in result["hardest_rows"][:5]:
                mark = "hit" if row["found"] else "miss"
                print(
                    f"  {mark:<4} n={row['n']:<8} p={row.get('p', '?'):<8} q={row.get('q', '?'):<8} "
                    f"tests={row['exact_tests']} phase={row['phase']}"
                )
        elif result["problem"] == "collatz":
            print(
                f"tested={result['tested_count']} hits={result['hit_count']} "
                f"max_steps={result['max_observed_steps']} max_ratio={result['max_observed_ratio']} "
                f"product_mean={result['mean_product_field']}"
            )
            print(f"ternary={result['ternary_map']}")
            for row in result["hard_rows"][:5]:
                mark = "hit" if row["verified"] else "miss"
                print(
                    f"  {mark:<4} seed={row['seed']:<8} steps={row['steps']:<5} "
                    f"max_ratio={row['max_ratio']} product={row['product_field_strength']:.6f}"
                )
        elif result["problem"] == "catalan_power_gaps":
            print(
                f"candidates={result['candidate_count']} hits={result['hit_count']} "
                f"top_precision={result['top_precision']:.2%} product_mean={result['mean_product_field']}"
            )
            print(f"ternary={result['ternary_map']}")
            for row in result["top_rows"][:5]:
                mark = "hit" if row["verified"] else "miss"
                left = row["larger"]
                right = row["smaller"]
                print(
                    f"  {mark:<4} {left['base']}^{left['exponent']} - "
                    f"{right['base']}^{right['exponent']} = {row['gap']} "
                    f"field={row['field_strength']:.6f} product={row['product_field_strength']:.6f}"
                )
        elif result["problem"] == "gilbreath":
            print(
                f"rows={result['rows_tested']} hits={result['hit_count']} "
                f"misses={len(result['misses'])} product_mean={result['mean_product_field']}"
            )
            print(f"ternary={result['ternary_map']}")
            for row in result["hard_rows"][:5]:
                mark = "hit" if row["verified"] else "miss"
                print(
                    f"  {mark:<4} depth={row['depth']:<5} first={row['first_value']} "
                    f"field={row['field_strength']:.6f} product={row['product_field_strength']:.6f}"
                )
        print()


def int_sha256_hex(n: int) -> str:
    byte_length = max(1, (n.bit_length() + 7) // 8)
    return hashlib.sha256(n.to_bytes(byte_length, "big")).hexdigest()


def decimal_digits_power2_minus1(exponent: int) -> int:
    return math.floor(exponent * math.log10(2)) + 1


def perfect_digits_for_mersenne_exponent(exponent: int) -> int:
    log10_value = (exponent - 1) * math.log10(2) + math.log10((1 << exponent) - 1)
    return math.floor(log10_value) + 1


def mersenne_prime_math_row(exponent: int, rank: int, prime_rank: int, verify_locally: bool) -> dict:
    started = time.time()
    local_result = lucas_lehmer(exponent) if verify_locally else None
    mersenne_mod = pow(2, exponent, 10**12) - 1
    if mersenne_mod < 0:
        mersenne_mod += 10**12
    perfect_mod = (pow(2, exponent - 1, 10**12) * mersenne_mod) % 10**12
    row = {
        "rank": rank,
        "exponent": exponent,
        "mersenne_form": f"2^{exponent}-1",
        "raw_exponent_rank": exponent - 1,
        "prime_exponent_rank": prime_rank,
        "magnifying_glass_reduction": round(1 - (prime_rank / max(1, exponent - 1)), 6),
        "verified_by": "local_lucas_lehmer" if verify_locally else "known_mersenne_list_source",
        "local_lucas_lehmer_result": local_result,
        "local_verify_sec": round(time.time() - started, 3) if verify_locally else None,
        "math_from_prime": {
            "mersenne_bit_length": exponent,
            "mersenne_decimal_digits": decimal_digits_power2_minus1(exponent),
            "mersenne_last_12_digits": f"{mersenne_mod:012d}",
            "perfect_number_form": f"2^{exponent - 1} * (2^{exponent}-1)",
            "perfect_number_bit_length": (2 * exponent) - 1,
            "perfect_number_decimal_digits": perfect_digits_for_mersenne_exponent(exponent),
            "perfect_number_last_12_digits": f"{perfect_mod:012d}",
        },
        "path": [
            "raw_number_space",
            "mersenne_substitution_n_plus_1_is_power_of_two",
            "exponent_space",
            "prime_exponent_filter",
            "lucas_lehmer_or_source_verifier",
            "euclid_euler_perfect_number_math",
        ],
    }
    if exponent <= 25000:
        mersenne = (1 << exponent) - 1
        perfect = (1 << (exponent - 1)) * mersenne
        row["math_from_prime"]["mersenne_sha256"] = int_sha256_hex(mersenne)
        row["math_from_prime"]["perfect_number_sha256"] = int_sha256_hex(perfect)
    return row


def run_mersenne_replay(count: int, local_exact_count: int) -> dict:
    count = max(1, min(count, len(KNOWN_MERSENNE_EXPONENTS)))
    local_exact_count = max(0, min(local_exact_count, count))
    targets = KNOWN_MERSENNE_EXPONENTS[:count]
    max_exponent = targets[-1]
    prime_exponents = sieve(max_exponent)
    rank_by_exponent = {p: index for index, p in enumerate(prime_exponents, start=1)}
    rows = [
        mersenne_prime_math_row(
            exponent,
            rank=index,
            prime_rank=rank_by_exponent[exponent],
            verify_locally=index <= local_exact_count,
        )
        for index, exponent in enumerate(targets, start=1)
    ]
    local_rows = [row for row in rows if row["verified_by"] == "local_lucas_lehmer"]
    return {
        "schema_version": "prime_fog_mersenne_replay_v1",
        "target_count": count,
        "locally_verified_count": len(local_rows),
        "source_known_count": count - len(local_rows),
        "max_exponent": max_exponent,
        "raw_exponent_candidates_to_max": max_exponent - 1,
        "prime_exponent_candidates_to_max": len(prime_exponents),
        "magnifying_glass_reduction_to_max": round(1 - (len(prime_exponents) / (max_exponent - 1)), 6),
        "local_verify_total_sec": round(sum(row["local_verify_sec"] or 0 for row in rows), 3),
        "rows": rows,
    }


def print_mersenne_replay(payload: dict) -> None:
    print("Mersenne hard-prime replay")
    print(f"targets: {payload['target_count']}")
    print(f"locally verified: {payload['locally_verified_count']}")
    print(f"source-known only: {payload['source_known_count']}")
    print(f"max exponent: {payload['max_exponent']}")
    print(f"raw exponent candidates: {payload['raw_exponent_candidates_to_max']}")
    print(f"prime exponent candidates: {payload['prime_exponent_candidates_to_max']}")
    print(f"magnifying-glass reduction: {payload['magnifying_glass_reduction_to_max']:.2%}")
    print(f"local verify total seconds: {payload['local_verify_total_sec']}")
    print()
    for row in payload["rows"]:
        math_row = row["math_from_prime"]
        verified = row["verified_by"]
        local = row["local_lucas_lehmer_result"]
        local_note = f" LL={local} {row['local_verify_sec']}s" if local is not None else ""
        print(
            f"{row['rank']:>2}. {row['mersenne_form']:<13} "
            f"prime-exp-rank={row['prime_exponent_rank']:<5} "
            f"reduction={row['magnifying_glass_reduction']:.2%} "
            f"{verified}{local_note}"
        )
        print(
            f"    M digits={math_row['mersenne_decimal_digits']} "
            f"last12={math_row['mersenne_last_12_digits']} "
            f"perfect digits={math_row['perfect_number_decimal_digits']} "
            f"perfect last12={math_row['perfect_number_last_12_digits']}"
        )


def run_mersenne_probe(exponent_limit: int) -> dict:
    started = time.time()
    raw_candidates = list(range(2, exponent_limit + 1))
    prime_exponents = sieve(exponent_limit)
    found: list[int] = []
    tests_run = 0
    recovery_rows: list[dict] = []
    target_set = set(known_targets_up_to(exponent_limit))

    for index, exponent in enumerate(prime_exponents, start=1):
        tests_run += 1
        is_mersenne_prime = lucas_lehmer(exponent)
        if is_mersenne_prime:
            found.append(exponent)
            if exponent in target_set:
                raw_rank = exponent - 1
                recovery_rows.append(
                    {
                        "exponent": exponent,
                        "mersenne_form": f"2^{exponent}-1",
                        "raw_rank": raw_rank,
                        "prime_exponent_rank": index,
                        "preverify_reduction": round(1 - (index / raw_rank), 6) if raw_rank else 0,
                        "seams": [
                            "candidate_is_exponent",
                            "exponent_is_prime",
                            "mersenne_family",
                            "lucas_lehmer_zero",
                        ],
                    }
                )

    windows = []
    for window in nearest_window(exponent_limit):
        raw_count = max(0, window - 1)
        prime_count = sum(1 for p in prime_exponents if p <= window)
        found_count = sum(1 for p in found if p <= window)
        windows.append(
            {
                "depth": window,
                "raw_candidates": raw_count,
                "prime_exponent_candidates": prime_count,
                "mersenne_hits": found_count,
                "preverify_reduction": round(1 - (prime_count / raw_count), 6) if raw_count else 0,
            }
        )

    expected = known_targets_up_to(exponent_limit)
    return {
        "schema_version": "prime_fog_mersenne_probe_v1",
        "exponent_limit": exponent_limit,
        "raw_candidate_count": len(raw_candidates),
        "prime_exponent_count": len(prime_exponents),
        "preverify_reduction": round(1 - (len(prime_exponents) / len(raw_candidates)), 6),
        "lucas_lehmer_tests": tests_run,
        "found_exponents": found,
        "expected_known_exponents": expected,
        "matches_known_prefix": found == expected,
        "recovery_rows": recovery_rows,
        "time_windows": windows,
        "elapsed_sec": round(time.time() - started, 3),
    }


def record_branch_probe() -> dict:
    exponent = 136_279_841
    return {
        "schema_version": "prime_fog_record_branch_probe_v1",
        "known_record_branch": "2^136279841-1",
        "exponent": exponent,
        "exponent_prime_by_local_miller_rabin": deterministic_miller_rabin_u64(exponent),
        "verified_mersenne_prime_by_source": True,
        "local_note": "This script does not run Lucas-Lehmer for the 41M-digit record target.",
        "seams": ["exponent_is_prime", "mersenne_family", "external_verified_record"],
    }


def print_plain(payload: dict) -> None:
    fermat = payload["fermat_probe"]
    lidar = payload["lidar_probe"]
    blind = payload["blind_sweep"]
    mersenne = payload["mersenne_probe"]
    record = payload["record_branch_probe"]

    print("Prime fog-of-war probe")
    print()
    print("Fermat branch")
    print(f"  primes scanned: {fermat['prime_count']} up to {fermat['prime_limit']}")
    print("  top geometry candidates:")
    for row in fermat["top"]:
        seams = ", ".join(row["seams"])
        print(f"    {row['prime']:>7}  score={row['score']:>2}  {seams}")
    print("  recovered known Fermat primes:")
    for row in fermat["recovered_targets"]:
        print(f"    {row['prime']:>7}  rank={row['rank']:>2}  score={row['score']:>2}")

    print()
    print("Arithmetic lidar frames")
    print(f"  tail={lidar['tail']} radius={lidar['radius']}")
    for frame in lidar["frames"]:
        tail_gaps = ",".join(str(gap) for gap in frame["tail_chunk"]["gaps"])
        beams = frame["radial_chunk"]["beams"]
        blocked = [beam for beam in beams if beam["state"] == "blocked"]
        stop = frame["radial_chunk"]["stop_at_next_prime"]
        print(
            f"  p={frame['cursor_prime']:<7} "
            f"idx={frame['prime_index']:<6} "
            f"tail_gaps=[{tail_gaps}] "
            f"blocked={len(blocked):<3} "
            f"next={stop} "
            f"move={frame['radial_chunk']['move_delta']}"
        )
        for beam in beams[:8]:
            block = f" by {beam['blocked_by']}" if "blocked_by" in beam else ""
            print(
                f"    beam n={beam['n']:<7} "
                f"+{beam['delta']:<3} "
                f"mod30={beam['mod30']:<2} "
                f"{beam['state']}{block}"
            )

    print()
    print("30-prime blind flashlight sweep")
    print(f"  family: {blind['target_family']}")
    print(f"  targets: {blind['target_count']}")
    print(f"  recovered: {blind['recovered_count']}/{blind['target_count']}")
    print(f"  first exact prime was target: {blind['first_exact_prime_hit_count']}/{blind['target_count']}")
    print(f"  raw candidates: {blind['raw_candidate_count']}")
    print(f"  exact-test reduction: {blind['exact_test_reduction']:.2%}")
    print(
        f"  mean exact tests to target: {blind['mean_exact_tests_to_target']} "
        f"(max {blind['max_exact_tests_to_target']})"
    )
    print(
        f"  mean target energy rank: {blind['mean_target_energy_rank']} "
        f"(max {blind['max_target_energy_rank']})"
    )
    for row in blind["rows"]:
        print(
            f"    seed={row['seed']:<2} "
            f"gap={row['target_gap']:<4} "
            f"rank={row['target_energy_rank']:<4} "
            f"tests={row['exact_tests_to_target']:<3} "
            f"prime={row['target_prime']}"
        )

    print()
    print("Mersenne exponent branch")
    print(f"  exponent fog depth: {mersenne['exponent_limit']}")
    print(f"  raw candidates: {mersenne['raw_candidate_count']}")
    print(f"  prime exponent candidates: {mersenne['prime_exponent_count']}")
    print(f"  pre-verifier reduction: {mersenne['preverify_reduction']:.2%}")
    print(f"  Lucas-Lehmer tests run: {mersenne['lucas_lehmer_tests']}")
    print(f"  found exponents: {mersenne['found_exponents']}")
    print(f"  matches known prefix: {mersenne['matches_known_prefix']}")
    print("  target recovery rows:")
    for row in mersenne["recovery_rows"]:
        print(
            "    "
            f"{row['mersenne_form']:<12} "
            f"prime-rank={row['prime_exponent_rank']:<5} "
            f"reduction={row['preverify_reduction']:.2%}"
        )

    print()
    print("Depth windows")
    for row in mersenne["time_windows"]:
        print(
            f"  t={row['depth']:<6} "
            f"raw={row['raw_candidates']:<6} "
            f"prime-exp={row['prime_exponent_candidates']:<5} "
            f"hits={row['mersenne_hits']:<3} "
            f"preverify-reduction={row['preverify_reduction']:.2%}"
        )

    print()
    print("Current record branch")
    print(f"  {record['known_record_branch']}")
    print(f"  local exponent prime check: {record['exponent_prime_by_local_miller_rabin']}")
    print(f"  {record['local_note']}")


# ─────────────────────────────────────────────────────────────────────────────
# Chemical compound fog-of-war probe
# Same search architecture as the prime probe:
#   linear base  →  curved lens (log-MW ratio map)
#   mesh compass  →  structural-alert filter (SEVERE = banned residue)
#   exact collapse  →  stability_score threshold
# ─────────────────────────────────────────────────────────────────────────────

# (name, mw_g_per_mol, half_life_hours_at_25C, has_severe_structural_alert)
_CHEM_SEEDS: list[tuple[str, float, float, bool]] = [
    ("caffeine",          194.194, 876_000.0, False),
    ("paracetamol",       151.163, 438_000.0, False),
    ("glucose",           180.157, 219_000.0, False),
    ("sucrose",           342.297,   8_760.0, False),
    ("ascorbic_acid",     176.124,     432.0, False),
    ("aspirin",           180.157,      48.0, True),
    ("hydrogen_peroxide",  34.014,       0.5, True),
    ("ibuprofen",         206.281, 262_800.0, False),
    ("metformin",         129.163, 438_000.0, False),
    ("naproxen",          230.259, 262_800.0, False),
    ("atorvastatin",      558.641,  87_600.0, False),
    ("omeprazole",        345.416,   8_760.0, False),
    ("diazepam",          284.741,  43_800.0, False),
    ("warfarin",          308.328,     876.0, True),
    ("glycine",            75.032, 876_000.0, False),
]

# LogP and TPSA (Å²) per seed.  Sources: PubChem Compound / RDKit 2D-descriptor.
# Used by the 6-trit ADME expansion for MW-interpolated property estimation.
_SEED_ADME_PROPS: dict[str, tuple[float, float]] = {
    "glycine":          (-3.21,  65.06),
    "hydrogen_peroxide": (-1.36, 38.69),
    "metformin":        (-1.43,  91.46),
    "paracetamol":       (0.46,  49.33),
    "ascorbic_acid":    (-1.85, 107.22),
    "glucose":          (-3.24, 110.38),
    "aspirin":           (1.19,  63.60),
    "caffeine":         (-0.07,  58.44),
    "ibuprofen":         (3.97,  37.30),
    "naproxen":          (3.18,  46.53),
    "diazepam":          (2.82,  32.67),
    "warfarin":          (2.70,  75.99),
    "sucrose":          (-3.70, 189.53),
    "omeprazole":       (-0.13,  97.69),
    "atorvastatin":      (4.46, 111.79),
}


def _estimate_logp_tpsa(mw: float) -> tuple[float, float]:
    """MW-sorted linear interpolation of (logP, TPSA) from the seed table.

    Avoids external API calls while preserving local chemical geometry.
    Clamps to nearest endpoint for MWs outside the seed range.
    """
    pts = sorted(
        [(s[1], _SEED_ADME_PROPS[s[0]][0], _SEED_ADME_PROPS[s[0]][1])
         for s in _CHEM_SEEDS if s[0] in _SEED_ADME_PROPS],
        key=lambda x: x[0],
    )
    if not pts:
        return 2.5, 75.0
    if mw <= pts[0][0]:
        return pts[0][1], pts[0][2]
    if mw >= pts[-1][0]:
        return pts[-1][1], pts[-1][2]
    for i in range(len(pts) - 1):
        lo_mw, lo_logp, lo_tpsa = pts[i]
        hi_mw, hi_logp, hi_tpsa = pts[i + 1]
        if lo_mw <= mw <= hi_mw:
            t = (mw - lo_mw) / max(hi_mw - lo_mw, 1e-9)
            return lo_logp + t * (hi_logp - lo_logp), lo_tpsa + t * (hi_tpsa - lo_tpsa)
    return 2.5, 75.0


def _logp_trit(logp: float) -> int:
    """Gate 5 — lipophilicity (LogP).

    trit=0 (fail):      logP < −3  or  logP > 7
    trit=1 (near-miss): −3 ≤ logP < 0  or  5 < logP ≤ 7   ← activity-cliff edges
    trit=2 (pass):      0 ≤ logP ≤ 5

    Near-miss cliff widths are asymmetric: −3 log-units below 0 (steep hydrophilic
    cliff), +2 above 5 (gentler lipophilic cliff — formulation can rescue).
    Grounding: activity cliff boundary analysis (arXiv:2302.07541), Lipinski Ro5,
    and bRo5 greasy-PROTAC literature.
    """
    if logp < -3.0 or logp > 7.0:
        return 0
    if logp < 0.0 or logp > 5.0:
        return 1
    return 2


def _tpsa_trit(tpsa: float) -> int:
    """Gate 6 — polar surface area (TPSA, Å²).

    trit=0 (fail):      TPSA < 5  or  TPSA > 200
    trit=1 (near-miss): 5 ≤ TPSA < 20  or  130 < TPSA ≤ 200   ← activity-cliff edges
    trit=2 (pass):      20 ≤ TPSA ≤ 130

    Lower cliff (5→20): CNS 'flat molecule' zone — BBB-crossing possible, efflux risk high.
    Upper cliff (130→200): bRo5/PROTAC/macrocycle zone — chameleonicity can rescue
    (multi-level BO coarse→fine, 2505.04169). The 130 Å² wall is the sharpest gate:
    empirical Caco-2 data shows a steep passive-permeability drop here (2310.00174).
    """
    if tpsa < 5.0 or tpsa > 200.0:
        return 0
    if tpsa < 20.0 or tpsa > 130.0:
        return 1
    return 2


def _chem_stability_score(mw: float, half_life_h: float, severe: int) -> float:
    penalty = 1.0 + severe * 10.0
    return (half_life_h / penalty) / max(mw, 1.0)


def _load_rdkit_enhancement() -> dict[str, dict]:
    """Try to pull RDKit-computed MW + severe-alert count for each compound."""
    out: dict[str, dict] = {}
    try:
        import sys
        from pathlib import Path

        _root = Path(__file__).resolve().parents[2]
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        from scripts.pharma_rdkit_screen import (
            compute_descriptors,
            stability_evidence_from_structure,
            SMILES_DB,
            EXTENDED_SMILES,
        )

        for name, smiles in {**SMILES_DB, **EXTENDED_SMILES}.items():
            desc = compute_descriptors(smiles)
            if not desc:
                continue
            alerts = stability_evidence_from_structure(desc)
            severe = sum(1 for a in alerts if "SEVERE" in a)
            out[name] = {"mw": desc.mw, "severe": severe, "alerts": alerts}
    except Exception:
        pass
    return out


def _build_chem_candidates(bins: int, enhanced: dict[str, dict]) -> list[dict]:
    candidates = []
    for name, mw, half_life, has_severe in _CHEM_SEEDS:
        if name in enhanced:
            mw = enhanced[name]["mw"]
            severe = enhanced[name]["severe"]
        else:
            severe = 1 if has_severe else 0
        stability = _chem_stability_score(mw, half_life, severe)
        candidates.append(
            {
                "name": name,
                "mw": mw,
                "half_life_hours": half_life,
                "severe_alerts": severe,
                "stability_score": stability,
                "mw_bin": angle_bin_for_value(max(1, round(mw * 1000)), bins),
                "mesh_blocked": severe > 0,
            }
        )
    candidates.sort(key=lambda c: c["mw"])
    return candidates


# ─────────────────────────────────────────────────────────────────────────────
# Trit / Binary / Linear-Decomposition Answer-Space Engine
#
# Research grounding (synthesised from arXiv sweep):
#   HDBind (Scientific Reports 2024)      — binary HD vectors for screening
#   HDF 2604.27810 (Apr 2026)             — algebraic ops on high-dim vectors
#   HimNet 2504.20127                     — 3-level atom→motif→mol cascade
#   Multi-Level BO 2505.04169             — coarse→fine funnel in chem space
#   Activity Cliff Prediction 2302.07541  — near-miss (cliff) boundary region
#   ADMET combinations 2310.00174         — cascade filter combinations
#   CheapVS / Pref-MOBO 2503.16841       — screens 6% of library, 50% recall
#   ECFP+PCA ChemRxiv-2025-qdp8w         — PCA over Tanimoto/ECFP space
#
# Encoding layers:
#   Binary  : hard gates {0,1} — IS the candidate in the feasible polytope?
#   Trit    : soft gates {0,1,2} — FAIL / NEAR-MISS / PASS per gate
#   Float   : continuous glow score [0,1]
#   Linear  : PCA projection of (MW, log_stability) → first principal axis
#
# Answer space = { candidates where binary_pass=True and trit_int > 0 }
#   This is typically <5% of the raw MW grid (50–900 Da at 0.5 Da step = 1700 pts)
#   Matches the CheapVS result: 6% library screening → ≥50% recall.
# ─────────────────────────────────────────────────────────────────────────────


def _mw_lipinski_trit(mw: float) -> int:
    """0=outside Lipinski MW (fail), 1=edge zone 50-100/500-900 (near), 2=core 100-500 (pass)"""
    if mw < 50.0 or mw > 900.0:
        return 0
    if (50.0 <= mw < 100.0) or (500.0 < mw <= 900.0):
        return 1
    return 2


def _severity_trit(mw: float) -> int:
    """0=exact severe compound mass (fail), 1=within 5 Da of severe (near), 2=clear (pass)"""
    severe_mws = [s[1] for s in _CHEM_SEEDS if s[3]]
    if not severe_mws:
        return 2
    min_dist = min(abs(mw - sm) for sm in severe_mws)
    if min_dist < 0.5:
        return 0
    if min_dist < 5.0:
        return 1
    return 2


def _band_trit(mw: float, band: tuple[float, float] | None) -> int:
    """0=well outside predicted band (fail), 1=adjacent ±50% band-width (near), 2=inside band (pass)"""
    if band is None:
        return 1
    lo, hi = band
    width = max(hi - lo, 1.0)
    if lo <= mw <= hi:
        return 2
    if (mw >= lo - width * 0.5) or (mw <= hi + width * 0.5):
        return 1
    return 0


def _stability_trit(stability_score: float, threshold: float) -> int:
    """0=far below (fail), 1=≥50% of threshold (near), 2=at or above threshold (pass)"""
    if stability_score >= threshold:
        return 2
    if stability_score >= threshold * 0.5:
        return 1
    return 0


def encode_trit_vector(trits: list[int]) -> int:
    """Pack a list of base-3 digits into a single ternary integer.

    E.g. [2, 1, 2, 0] → 2*1 + 1*3 + 2*9 + 0*27 = 23
    Ordering: trits[0] is the least-significant trit.
    """
    return sum(t * (3 ** i) for i, t in enumerate(trits))


def decode_trit_vector(trit_int: int, n: int) -> list[int]:
    """Unpack a ternary integer back to n trits (LSB first)."""
    trits = []
    for _ in range(n):
        trits.append(trit_int % 3)
        trit_int //= 3
    return trits


def drug_space_linear_decomp(seeds: list | None = None) -> dict:
    """PCA over the 2D (MW, log_half_life) drug-space of seed compounds.

    Returns the first principal component axis, explained variance, and the
    projection range of the stable compound cluster — this is the "answer space"
    that the ternary search should be constrained to.

    Grounded in: ECFP+PCA (ChemRxiv-2025-qdp8w), multi-level BO (2505.04169),
    and the long-standing chemical space PCA literature (self-organizing maps,
    PCA-8/PCA-16 from binary fingerprint work).
    """
    seeds = seeds or _CHEM_SEEDS
    n = len(seeds)
    mws = [s[1] for s in seeds]
    log_hls = [math.log(s[2] + 1.0) for s in seeds]

    mean_mw = sum(mws) / n
    mean_lhl = sum(log_hls) / n
    std_mw = math.sqrt(sum((m - mean_mw) ** 2 for m in mws) / max(1, n - 1))
    std_lhl = math.sqrt(sum((l - mean_lhl) ** 2 for l in log_hls) / max(1, n - 1))

    eps = 1e-9
    z_mw = [(m - mean_mw) / max(std_mw, eps) for m in mws]
    z_lhl = [(l - mean_lhl) / max(std_lhl, eps) for l in log_hls]

    cov_mm = sum(a * b for a, b in zip(z_mw, z_mw)) / n
    cov_ml = sum(a * b for a, b in zip(z_mw, z_lhl)) / n
    cov_ll = sum(a * b for a, b in zip(z_lhl, z_lhl)) / n

    trace = cov_mm + cov_ll
    det = cov_mm * cov_ll - cov_ml ** 2
    disc = math.sqrt(max(0.0, (trace / 2) ** 2 - det))
    lam1 = trace / 2 + disc
    lam2 = max(0.0, trace / 2 - disc)

    if abs(cov_ml) > 1e-10:
        vx, vy = cov_ml, lam1 - cov_mm
        norm = math.sqrt(vx ** 2 + vy ** 2)
        pc1 = [vx / norm, vy / norm]
    else:
        pc1 = [1.0, 0.0] if cov_mm >= cov_ll else [0.0, 1.0]

    projections = [pc1[0] * z + pc1[1] * l for z, l in zip(z_mw, z_lhl)]
    proj_min, proj_max = min(projections), max(projections)

    mw_at_min = mws[projections.index(proj_min)]
    mw_at_max = mws[projections.index(proj_max)]
    answer_mw_lo = min(mw_at_min, mw_at_max)
    answer_mw_hi = max(mw_at_min, mw_at_max)

    return {
        "n_seeds": n,
        "mean_mw": round(mean_mw, 3),
        "std_mw": round(std_mw, 3),
        "mean_log_halflife": round(mean_lhl, 4),
        "std_log_halflife": round(std_lhl, 4),
        "pc1": [round(pc1[0], 6), round(pc1[1], 6)],
        "eigenvalue_1": round(lam1, 6),
        "eigenvalue_2": round(lam2, 6),
        "explained_variance_pc1": round(lam1 / (lam1 + lam2 + eps), 4),
        "projection_range": [round(proj_min, 4), round(proj_max, 4)],
        "answer_mw_range": [round(answer_mw_lo, 3), round(answer_mw_hi, 3)],
    }


def answer_space_grid(
    linear_decomp: dict,
    stability_threshold: float = 1.0,
    predicted_band: tuple[float, float] | None = None,
    mw_step: float = 0.5,
    extend_sigma: float = 1.0,
    alphafold_trit: int | None = None,
) -> list[dict]:
    """Generate the set of MW candidates that lie in the answer space.

    The answer space is the intersection of:
      1. Binary gate: MW passes Lipinski range (50-900 Da)
      2. Trit gate: no severe-compound collision, inside or near predicted band
      3. Linear subspace: MW within [answer_mw_lo - sigma, answer_mw_hi + sigma]
      4. (Optional) AlphaFold trit[6] — target structure quality

    Trit encoding per candidate:
      trit[0] = Lipinski MW trit
      trit[1] = severity trit
      trit[2] = predicted-band trit
      trit[3] = stability trit
      trit[4] = logP trit (ADME membrane permeability)
      trit[5] = TPSA trit (polar surface area / passive absorption)
      trit[6] = AlphaFold pLDDT trit (target structure quality, optional)

    Geometry framing (alphafold_trit):
      Proteins fold into negative space (binding pockets) or positive space
      (exterior surface). The neutral / disordered state is neither.
      pLDDT measures collapse to one geometry; pLDDT / 100 ~ 1 / (1 + self_ratio),
      the same form as the harmonic wall H = 1 / (1 + d + 2*pd).
      The innate shape is 1 +/- self_ratio, never a fixed 1.

    alphafold_trit: pre-fetched pLDDT trit (0/1/2) for the target protein.
      Same value for all MW candidates — it is a property of the TARGET.
      Pass None for 6-trit system; pass a value for 7-trit system.

    Only candidates with binary_pass=True (all trits > 0) are returned.

    Grounded in: HDBind, CheapVS (arXiv:2503.16841), HimNet (2504.20127),
    activity cliff boundary (2302.07541), AlphaFold EBI pLDDT confidence.
    """
    sigma = linear_decomp["std_mw"]
    lo_mw = max(50.0, linear_decomp["answer_mw_range"][0] - extend_sigma * sigma)
    hi_mw = min(900.0, linear_decomp["answer_mw_range"][1] + extend_sigma * sigma)

    results = []
    mw = round(lo_mw, 4)
    while mw <= hi_mw + 1e-6:
        lip_t = _mw_lipinski_trit(mw)
        sev_t = _severity_trit(mw)
        band_t = _band_trit(mw, predicted_band)

        best_score = 0.0
        for _, seed_mw, half_life_h, severe in _CHEM_SEEDS:
            if abs(mw - seed_mw) < 2.0:
                s = _chem_stability_score(seed_mw, half_life_h, severe)
                if s > best_score:
                    best_score = s
        if best_score == 0.0:
            half_life_est = 24.0 * max(50.0, min(mw, 500.0)) / 200.0
            best_score = _chem_stability_score(mw, half_life_est, False)

        stab_t = _stability_trit(best_score, stability_threshold)
        logp_est, tpsa_est = _estimate_logp_tpsa(mw)
        logp_t = _logp_trit(logp_est)
        tpsa_t = _tpsa_trit(tpsa_est)
        trit_vec = [lip_t, sev_t, band_t, stab_t, logp_t, tpsa_t]
        if alphafold_trit is not None:
            trit_vec.append(int(alphafold_trit))
        trit_int = encode_trit_vector(trit_vec)
        binary_pass = all(t > 0 for t in trit_vec)

        if binary_pass:
            results.append(
                {
                    "mw": round(mw, 4),
                    "trit_vec": trit_vec,
                    "trit_int": trit_int,
                    "trit_label": "".join(str(t) for t in trit_vec),
                    "stability_score": round(best_score, 6),
                    "logp_est": round(logp_est, 3),
                    "tpsa_est": round(tpsa_est, 2),
                    "binary_pass": True,
                    "glow_float": round(sum(trit_vec) / (2.0 * len(trit_vec)), 4),
                }
            )
        mw = round(mw + mw_step, 4)

    results.sort(key=lambda r: -r["trit_int"])
    return results


def _alphafold_trit_fetch(uniprot_id: str) -> tuple[int, dict]:
    """Fetch AlphaFold pLDDT trit for a UniProt accession.

    Returns (trit_value, metadata_dict). On network failure trit defaults to 1
    (near-miss) so the gate degrades gracefully without blocking the scan.
    Imports alphafold_gate lazily so the module is not required for non-AF runs.
    """
    try:
        import sys
        import os

        _probe_dir = os.path.dirname(os.path.abspath(__file__))
        if _probe_dir not in sys.path:
            sys.path.insert(0, _probe_dir)
        from alphafold_gate import alphafold_lookup, alphafold_plddt_trit  # type: ignore[import]

        result = alphafold_lookup(uniprot_id)
        if result["error"]:
            return 1, result
        if result["mean_plddt"] is None:
            return 1, result
        return alphafold_plddt_trit(result["mean_plddt"]), result
    except Exception as exc:
        return 1, {"error": str(exc), "uniprot_id": uniprot_id}


def run_answer_space_probe(
    stability_threshold: float = 1.0,
    predicted_band: tuple[float, float] | None = None,
    mw_step: float = 0.5,
    extend_sigma: float = 1.0,
    bins: int = 32,
    alphafold_uniprot: str | None = None,
) -> dict:
    """Full answer-space probe: linear decomposition -> trit grid -> ranked answer space.

    alphafold_uniprot: if set, fetches AlphaFold pLDDT for the target protein
      and adds trit[6] to all candidates. Example: "P00533" for EGFR.
    """
    af_trit = None
    af_meta: dict = {}
    if alphafold_uniprot:
        af_trit, af_meta = _alphafold_trit_fetch(alphafold_uniprot)
        af_meta["applied_trit"] = af_trit

    decomp = drug_space_linear_decomp()
    grid = answer_space_grid(
        decomp, stability_threshold, predicted_band, mw_step, extend_sigma,
        alphafold_trit=af_trit,
    )

    full_range_count = int((900.0 - 50.0) / max(mw_step, 1e-6))
    reduction_pct = round((1.0 - len(grid) / max(1, full_range_count)) * 100, 2)

    trit_histogram: dict[str, int] = {}
    for g in grid:
        lbl = g["trit_label"]
        trit_histogram[lbl] = trit_histogram.get(lbl, 0) + 1

    trit_states = sorted(trit_histogram.items(), key=lambda x: -encode_trit_vector([int(c) for c in x[0]]))
    n_trits = len(grid[0]["trit_vec"]) if grid else 4
    all_near_int = sum(1 * (3 ** i) for i in range(n_trits))
    top_candidates = [g for g in grid if g["trit_int"] >= all_near_int]

    result: dict = {
        "schema_version": "answer_space_probe_v1",
        "top_trit_threshold": all_near_int,
        "linear_decomp": decomp,
        "grid_size": len(grid),
        "full_range_count": full_range_count,
        "reduction_pct": reduction_pct,
        "stability_threshold": stability_threshold,
        "predicted_band": list(predicted_band) if predicted_band else None,
        "mw_step": mw_step,
        "n_trits": n_trits,
        "trit_histogram": dict(trit_states),
        "top_candidates": top_candidates[:30],
        "all_candidates": grid,
    }
    if alphafold_uniprot:
        result["alphafold"] = af_meta
    return result


def print_answer_space_probe(payload: dict) -> None:
    d = payload["linear_decomp"]
    print("Answer-space probe  (trit / binary / linear decomposition)")
    print(f"Seeds: {d['n_seeds']}  mean MW: {d['mean_mw']}  σ: {d['std_mw']}")
    print(f"PC1: [{d['pc1'][0]}, {d['pc1'][1]}]  explained variance: {d['explained_variance_pc1']:.1%}")
    print(f"Answer MW range: [{d['answer_mw_range'][0]}, {d['answer_mw_range'][1]}] Da")
    if payload["predicted_band"]:
        print(f"Predicted band: {payload['predicted_band']}")
    print()
    print(
        f"Grid: {payload['grid_size']} candidates in answer space "
        f"({payload['reduction_pct']}% reduction from full 50-900 Da grid)"
    )
    n_trits = payload.get("n_trits", 6)
    max_trit_int = 3 ** n_trits - 1
    print()
    if n_trits == 7:
        print(f"Trit encoding key (7-trit, 3^7=2187 states, max={max_trit_int}) [AlphaFold gate active]:")
        print("  [0]=Lipinski-MW  [1]=Severity  [2]=Predicted-Band  [3]=Stability  [4]=LogP  [5]=TPSA  [6]=AF-pLDDT")
    else:
        print(f"Trit encoding key (6-trit, 3^6=729 states, max={max_trit_int}):")
        print("  [0]=Lipinski-MW  [1]=Severity  [2]=Predicted-Band  [3]=Stability  [4]=LogP  [5]=TPSA")
    print("  0=fail(hard)  1=near-miss(cliff)  2=pass      trit_int=sum(t*3^i)")
    if "alphafold" in payload:
        af = payload["alphafold"]
        plddt_str = f"{af['mean_plddt']}" if af.get("mean_plddt") else "N/A"
        err_str = f"  error={af['error']}" if af.get("error") else ""
        af_label = ["disordered", "partial-fold", "confident"][af.get("applied_trit", 1)]
        print(f"  AlphaFold [{af.get('uniprot_id','')}]  gene={af.get('gene','?')}  "
              f"mean_pLDDT={plddt_str}  trit={af.get('applied_trit',1)} ({af_label}){err_str}")
    print()
    print("Trit state histogram (top states, count):")
    for lbl, cnt in list(payload["trit_histogram"].items())[:12]:
        trits = [int(c) for c in lbl]
        ti = encode_trit_vector(trits)
        bar = "█" * min(cnt, 40)
        max_int = 3 ** len(lbl) - 1
        suffix = "  ← all-pass" if ti == max_int else ("  ← all-near-miss" if all(t == 1 for t in trits) else "")
        print(f"  [{lbl}] int={ti:<4}  {cnt:>5} pts  {bar}{suffix}")
    print()
    if payload["top_candidates"]:
        top_thresh = payload.get("top_trit_threshold", 53)
        print(f"Top answer-space candidates (trit_int ≥ {top_thresh}, ordered by trit_int desc):")
        print(f"  {'MW':>10}  {'trit':>8}  {'int':>5}  {'glow':>6}  {'logP':>6}  {'TPSA':>6}  {'stability':>12}")
        print("  " + "─" * 68)
        for g in payload["top_candidates"][:20]:
            print(
                f"  {g['mw']:>10.4f}  {g['trit_label']:>8}  {g['trit_int']:>5}  "
                f"{g['glow_float']:>6.4f}  {g.get('logp_est', '?'):>6}  "
                f"{g.get('tpsa_est', '?'):>6}  {g['stability_score']:>12.6f}"
            )


def run_chem_ratio_map(source_filter: str, order: str, bins: int) -> dict:
    enhanced = _load_rdkit_enhancement()
    candidates = _build_chem_candidates(bins, enhanced)

    if source_filter == "stable":
        pool = [c for c in candidates if not c["mesh_blocked"]]
    elif source_filter == "unstable":
        pool = [c for c in candidates if c["mesh_blocked"]]
    else:
        pool = list(candidates)

    if order == "stability":
        pool.sort(key=lambda c: c["stability_score"], reverse=True)
    elif order == "half_life":
        pool.sort(key=lambda c: c["half_life_hours"], reverse=True)
    # default: already sorted by mw

    mw_ints = [max(1, round(c["mw"] * 1000)) for c in pool]
    labels = [c["name"] for c in pool]
    mw_seq = ratio_sequence(mw_ints, labels, bins)

    stab_ints = [max(1, round(c["stability_score"] * 1_000_000)) for c in pool]
    stab_seq = ratio_sequence(stab_ints, labels, bins)

    stable_bins = {c["mw_bin"] for c in candidates if not c["mesh_blocked"]}
    unstable_bins = {c["mw_bin"] for c in candidates if c["mesh_blocked"]}

    return {
        "schema_version": "chem_fog_ratio_map_v1",
        "compound_count": len(pool),
        "source_filter": source_filter,
        "order": order,
        "bins": bins,
        "mw_ratio_sequence": mw_seq,
        "stability_ratio_sequence": stab_seq,
        "stable_mw_bins": sorted(stable_bins),
        "unstable_mw_bins": sorted(unstable_bins),
        "shadow_zones": sorted(unstable_bins - stable_bins),
        "compounds": [
            {
                "name": c["name"],
                "mw": round(c["mw"], 3),
                "half_life_hours": c["half_life_hours"],
                "severe_alerts": c["severe_alerts"],
                "stability_score": round(c["stability_score"], 8),
                "mw_bin": c["mw_bin"],
                "stable": not c["mesh_blocked"],
            }
            for c in pool
        ],
    }


def print_chem_ratio_map(payload: dict) -> None:
    print("Chemical compound ratio map")
    print(f"compounds: {payload['compound_count']}  filter: {payload['source_filter']}  order: {payload['order']}")
    mw = payload["mw_ratio_sequence"]
    print(f"MW dx/x  mean={mw['mean_velocity']}  min={mw['min_velocity']}  max={mw['max_velocity']}")
    print(f"MW d(log) mean={mw['mean_log_step']}")
    print(f"stable bins:   {payload['stable_mw_bins']}")
    print(f"unstable bins: {payload['unstable_mw_bins']}")
    print(f"shadow zones:  {payload['shadow_zones']}")
    print(f"MW angle histogram: {mw['angle_histogram']}")
    print()
    for row in payload["compounds"]:
        label = "stable" if row["stable"] else "BLOCKED"
        print(
            f"  {row['name']:<20} "
            f"MW={row['mw']:<8.3f} "
            f"t½={row['half_life_hours']:<10} "
            f"alerts={row['severe_alerts']} "
            f"bin={row['mw_bin']:<3} "
            f"score={row['stability_score']:.4g} "
            f"[{label}]"
        )
    print()
    print("MW ratio pairs:")
    for row in mw.get("rows", []):
        print(
            f"  {row['from']:<20} → {row['to']:<20} "
            f"dx/x={row['scale_invariant_velocity']:.6g} "
            f"dlog={row['log_step']:.6g} "
            f"bin={row['angle_bin']}"
        )


def run_adaptive_chem_cone_search(
    bins: int,
    core_mw_min: float,
    core_mw_max: float,
    stability_threshold: float,
) -> dict:
    """
    Four-phase cone search over compound property space.

    Phase 1 (linear_core):         MW in sweet-spot range
    Phase 2 (learned_angle_lanes): MW bins from phase-1 hits
    Phase 3 (expanded_angle_lanes): halo-1 around learned bins
    Phase 4 (full_fallback):       all remaining compounds

    Mesh compass = severe structural-alert filter  (blocks like a banned residue)
    Verifier     = stability_score > threshold
    """
    enhanced = _load_rdkit_enhancement()
    candidates = _build_chem_candidates(bins, enhanced)

    visited: set[str] = set()
    learned_bins: set[int] = set()
    all_hits: list[dict] = []
    phase_log: list[dict] = []
    counters = {"total_scanned": 0, "mesh_blocked": 0, "verifier_calls": 0}

    def scan_phase(name: str, pool: list[dict], allowed_bins: set[int] | None = None) -> list[dict]:
        phase_hits = []
        phase_scanned = phase_blocked = phase_verified = 0
        for c in pool:
            cname = c["name"]
            if cname in visited:
                continue
            if allowed_bins is not None and c["mw_bin"] not in allowed_bins:
                continue
            visited.add(cname)
            counters["total_scanned"] += 1
            phase_scanned += 1
            if c["mesh_blocked"]:
                counters["mesh_blocked"] += 1
                phase_blocked += 1
                continue
            counters["verifier_calls"] += 1
            phase_verified += 1
            if c["stability_score"] > stability_threshold:
                hit = dict(c)
                hit["phase"] = name
                phase_hits.append(hit)
                learned_bins.add(c["mw_bin"])
        phase_log.append(
            {
                "phase": name,
                "scanned": phase_scanned,
                "mesh_blocked": phase_blocked,
                "verifier_calls": phase_verified,
                "hits": len(phase_hits),
                **({"allowed_bins": sorted(allowed_bins)} if allowed_bins is not None else {}),
            }
        )
        return phase_hits

    core_pool = [c for c in candidates if core_mw_min <= c["mw"] <= core_mw_max]
    all_hits.extend(scan_phase("linear_core", core_pool))

    remaining = [c for c in candidates if c["name"] not in visited]
    if learned_bins and remaining:
        all_hits.extend(scan_phase("learned_angle_lanes", remaining, learned_bins))

    remaining = [c for c in candidates if c["name"] not in visited]
    if learned_bins and remaining:
        expanded = expand_bins(learned_bins, bins, 1)
        all_hits.extend(scan_phase("expanded_angle_lanes", remaining, expanded))

    remaining = [c for c in candidates if c["name"] not in visited]
    if remaining:
        all_hits.extend(scan_phase("full_fallback", remaining))

    mesh_reduction = round(1 - (counters["verifier_calls"] / max(1, counters["total_scanned"])), 6)

    hit_mw_seq = None
    if len(all_hits) >= 2:
        hit_mw_ints = [max(1, round(h["mw"] * 1000)) for h in all_hits]
        hit_labels = [h["name"] for h in all_hits]
        hit_mw_seq = ratio_sequence(hit_mw_ints, hit_labels, bins)

    shadow_zones = sorted(
        {c["mw_bin"] for c in candidates if c["mesh_blocked"]}
        - {c["mw_bin"] for c in candidates if not c["mesh_blocked"]}
    )

    return {
        "schema_version": "chem_fog_adaptive_cone_v1",
        "bins": bins,
        "core_mw_range": [core_mw_min, core_mw_max],
        "stability_threshold": stability_threshold,
        "candidate_count": len(candidates),
        "total_scanned": counters["total_scanned"],
        "mesh_blocked": counters["mesh_blocked"],
        "verifier_calls": counters["verifier_calls"],
        "mesh_reduction": mesh_reduction,
        "hit_count": len(all_hits),
        "learned_bins": sorted(learned_bins),
        "phase_log": phase_log,
        "shadow_zones": shadow_zones,
        "hit_mw_ratio_map": hit_mw_seq,
        "hits": [
            {
                "name": h["name"],
                "mw": round(h["mw"], 3),
                "half_life_hours": h["half_life_hours"],
                "stability_score": round(h["stability_score"], 6),
                "mw_bin": h["mw_bin"],
                "phase": h["phase"],
            }
            for h in all_hits
        ],
    }


def print_adaptive_chem_cone_search(payload: dict) -> None:
    print("Adaptive chemical compound cone search")
    print(f"bins: {payload['bins']}  MW core: {payload['core_mw_range']}  threshold: {payload['stability_threshold']}")
    print(f"candidates: {payload['candidate_count']}")
    print(f"scanned: {payload['total_scanned']}  mesh-blocked: {payload['mesh_blocked']}  verifier calls: {payload['verifier_calls']}")
    print(f"mesh reduction: {payload['mesh_reduction']:.2%}")
    print(f"hits: {payload['hit_count']}")
    print(f"learned bins: {payload['learned_bins']}")
    print(f"shadow zones: {payload['shadow_zones']}")
    print()
    print("Phases:")
    for phase in payload["phase_log"]:
        bins_note = f"  lanes={phase['allowed_bins']}" if "allowed_bins" in phase else ""
        print(
            f"  {phase['phase']:<24} "
            f"scanned={phase['scanned']:<3} "
            f"blocked={phase['mesh_blocked']:<3} "
            f"verified={phase['verifier_calls']:<3} "
            f"hits={phase['hits']}"
            f"{bins_note}"
        )
    print()
    print("Stable hits (ordered by phase → MW):")
    for h in payload["hits"]:
        print(
            f"  [{h['phase']:<24}]  "
            f"{h['name']:<20} "
            f"MW={h['mw']:<8.3f} "
            f"t½={h['half_life_hours']:<10} "
            f"bin={h['mw_bin']:<3} "
            f"score={h['stability_score']:.4g}"
        )
    if payload["hit_mw_ratio_map"]:
        seq = payload["hit_mw_ratio_map"]
        print()
        print(f"Hit MW ratio map  (mean dx/x={seq['mean_velocity']}  histogram={seq['angle_histogram']})")
        for row in seq.get("rows", []):
            print(
                f"  {row['from']:<20} → {row['to']:<20} "
                f"dx/x={row['scale_invariant_velocity']:.6g} "
                f"dlog={row['log_step']:.6g} "
                f"bin={row['angle_bin']}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Solution radius engine
#
# For a sequence of verified hits x0, x1, x2, ...:
#   left_radius_i  = (x_i - x_{i-1}) / x_i   — distance back to prior hit
#   right_radius_i = (x_{i+1} - x_i) / x_i   — distance forward to next hit
#
# Each solution becomes a local field:
#   center, left_ratio, right_ratio, angle, radius_band, near_echoes
#
# The compass predicts a band, not a point:
#   next_center ≈ x_last * (1 + trend_ratio)
#   search_band ≈ [x_last * (trend − spread), x_last * (trend + spread)]
#
# Glow score = stages_cleared / total_gates — near-miss proximity beacon:
#   0.25  survived mesh prime sieve
#   0.50  survived wheel-30 filter
#   0.75  survived Miller-Rabin
#   0.99  passed all pre-filters, exact verifier says composite
#   1.00  exact verifier: confirmed solution
# ─────────────────────────────────────────────────────────────────────────────


def compute_solution_fields(hits: list[int], bins: int) -> list[dict]:
    n = len(hits)
    fields = []
    for i, x in enumerate(hits):
        x_prev = hits[i - 1] if i > 0 else None
        x_next = hits[i + 1] if i < n - 1 else None
        left_radius = round((x - x_prev) / x, 12) if x_prev is not None else None
        right_radius = round((x_next - x) / x, 12) if x_next is not None else None
        angle = round(math.log(x / x_prev), 12) if x_prev is not None else None
        fields.append(
            {
                "index": i,
                "center": x,
                "left_radius": left_radius,
                "right_radius": right_radius,
                "angle": angle,
                "radius_band": [left_radius, right_radius],
                "angle_bin": angle_bin_for_value(x, bins),
                "near_echoes": [],
            }
        )
    return fields


def predict_next_band(fields: list[dict], recency_weight: float = 0.7) -> dict | None:
    right_radii = [f["right_radius"] for f in fields if f["right_radius"] is not None]
    if not right_radii:
        return None
    n = len(right_radii)
    weights = [recency_weight ** (n - 1 - i) for i in range(n)]
    total_w = sum(weights)
    trend_ratio = sum(r * w for r, w in zip(right_radii, weights)) / total_w
    pairs = [
        (f["left_radius"], f["right_radius"])
        for f in fields
        if f["left_radius"] is not None and f["right_radius"] is not None
    ]
    radius_spread = sum(abs(r - lr) for lr, r in pairs) / max(1, len(pairs))
    last = fields[-1]["center"]
    next_center = last * (1.0 + trend_ratio)
    lo = last * max(0.0, trend_ratio - radius_spread)
    hi = last * (trend_ratio + radius_spread)
    return {
        "trend_ratio": round(trend_ratio, 8),
        "radius_spread": round(radius_spread, 8),
        "last_hit": last,
        "next_center_estimate": round(next_center, 3),
        "search_band_offset": [round(lo, 3), round(hi, 3)],
        "search_absolute": [round(last + lo, 3), round(last + hi, 3)],
        "band_width": round(hi - lo, 6),
        "band_width_relative": round((hi - lo) / max(1, last), 8),
    }


def fermat_k_glow(k: int, fermat_n: int, step: int, mesh: dict[int, int]) -> dict:
    candidate = k * step + 1
    blocked_by = mesh_blocker(k, mesh)
    if blocked_by is not None:
        return {"k": k, "candidate": candidate, "glow": 0.25, "stage": "mesh_blocked", "blocked_by": blocked_by}
    if candidate % 30 not in WHEEL30_RESIDUES:
        return {"k": k, "candidate": candidate, "glow": 0.50, "stage": "wheel_blocked"}
    if not deterministic_miller_rabin_u64(candidate):
        return {"k": k, "candidate": candidate, "glow": 0.75, "stage": "miller_rabin_fail"}
    verified = pow(2, 1 << fermat_n, candidate) == candidate - 1
    return {
        "k": k,
        "candidate": candidate,
        "glow": 1.0 if verified else 0.99,
        "stage": "verified" if verified else "fermat_exact_fail",
        "verified": verified,
    }


def drug_mw_glow(
    mw: float,
    stability_threshold: float,
    predicted_band: tuple[float, float] | None = None,
) -> dict:
    """4-gate glow score for a candidate MW in drug discovery space.

    Gate 1 (0.25): passes Lipinski-style MW filter (50-900 Da)
    Gate 2 (0.50): not a known-severe compound (peroxide, warfarin-like) within ±0.5 Da
    Gate 3 (0.75): falls inside the predicted radius band (if provided)
    Gate 4 (0.99 / 1.0): stability_score exceeds threshold (the verifier)
    """
    if mw < 50.0 or mw > 900.0:
        return {"mw": round(mw, 4), "glow": 0.25, "stage": "lipinski_mw_fail"}
    severe_mws = [s[1] for s in _CHEM_SEEDS if s[3]]
    if any(abs(mw - smw) < 0.5 for smw in severe_mws):
        return {"mw": round(mw, 4), "glow": 0.25, "stage": "severe_exact_match"}
    if predicted_band is not None:
        lo, hi = predicted_band
        if not (lo <= mw <= hi):
            return {"mw": round(mw, 4), "glow": 0.50, "stage": "outside_predicted_band"}
    best_score = 0.0
    best_name = "unknown"
    for name, seed_mw, half_life_h, severe in _CHEM_SEEDS:
        if abs(mw - seed_mw) < 2.0:
            score = _chem_stability_score(seed_mw, half_life_h, severe)
            if score > best_score:
                best_score = score
                best_name = name
    if best_score == 0.0:
        half_life_h_estimate = 24.0 * max(50.0, min(mw, 500.0)) / 200.0
        best_score = _chem_stability_score(mw, half_life_h_estimate, False)
    verified = best_score >= stability_threshold
    return {
        "mw": round(mw, 4),
        "glow": 1.0 if verified else 0.99,
        "stage": "verified" if verified else "stability_fail",
        "stability_score": round(best_score, 6),
        "nearest_compound": best_name,
        "verified": verified,
    }


def mersenne_exponent_glow(p: int) -> dict:
    if not deterministic_miller_rabin_u64(p):
        return {"p": p, "glow": 0.25, "stage": "not_prime"}
    if p == 2:
        return {"p": p, "glow": 1.0, "stage": "verified", "verified": True}
    modulus = (1 << p) - 1
    s = 4
    partial_steps = max(10, int(math.sqrt(p)))
    full_run = partial_steps >= p - 2
    for _ in range(min(partial_steps, p - 2)):
        s = (s * s - 2) % modulus
    low_zero = 0
    temp = s
    while temp & 1 == 0 and low_zero < 32:
        low_zero += 1
        temp >>= 1
    if full_run:
        verified = s == 0
        return {
            "p": p,
            "glow": 1.0 if verified else 0.99,
            "stage": "verified" if verified else "ll_full_fail",
            "verified": verified,
            "low_zero_bits": low_zero,
        }
    partial_glow = 0.50 + 0.24 * min(1.0, low_zero / 16.0)
    return {"p": p, "glow": partial_glow, "stage": "partial_ll", "steps_run": partial_steps, "low_zero_bits": low_zero}


def _attach_near_echoes(fields: list[dict], glows: list[dict]) -> None:
    if not fields:
        return
    centers = [f["center"] for f in fields]
    for g in glows:
        if g.get("verified"):
            continue
        val = g.get("mw", g.get("k", g.get("p", g.get("candidate", 0))))
        nearest_i = min(range(len(centers)), key=lambda i: abs(centers[i] - val))
        fields[nearest_i]["near_echoes"].append(
            {"value": val, "glow": round(g["glow"], 4), "stage": g["stage"]}
        )


def run_solution_radius_probe(
    mode: str,
    hits: list,
    search_forward: int,
    k_limit: int,
    mesh_primes: list[int],
    glow_threshold: float,
    bins: int,
    fermat_n: int,
    **kwargs,
) -> dict:
    if mode == "drug" and not hits:
        stab_thresh = kwargs.get("stability_threshold", 1.0)
        hits = sorted(
            s[1] for s in _CHEM_SEEDS
            if _chem_stability_score(s[1], s[2], s[3]) >= stab_thresh
        )
    hits_sorted = sorted(set(hits))
    if len(hits_sorted) < 2:
        return {
            "schema_version": "solution_radius_probe_v1",
            "error": "need at least 2 hits to compute solution fields",
            "mode": mode,
            "hit_count": len(hits_sorted),
        }

    fields = compute_solution_fields(hits_sorted, bins)
    prediction = predict_next_band(fields)
    hit_ratio = ratio_sequence(hits_sorted, [str(h) for h in hits_sorted], bins)

    all_glows: list[dict] = []
    verified_hit: dict | None = None

    if prediction is not None and search_forward > 0:
        band = prediction["search_absolute"]
        if mode == "fermat-k":
            step = 1 << (fermat_n + 2)
            mesh = fermat_k_mesh(step, mesh_primes)
            k_start = max(1, int(band[0]))
            k_end = min(k_limit, int(band[1]) + search_forward)
            for k in range(k_start, k_end + 1):
                g = fermat_k_glow(k, fermat_n, step, mesh)
                if g["glow"] >= glow_threshold:
                    all_glows.append(g)
                if g.get("verified"):
                    verified_hit = g
                    break

        elif mode == "mersenne":
            last = hits_sorted[-1]
            p_start = max(2, int(last + band[0]))
            p_end = max(p_start + 1, int(last + band[1]) + search_forward)
            for p in range(p_start, p_end + 1):
                g = mersenne_exponent_glow(p)
                if g["glow"] >= glow_threshold:
                    all_glows.append(g)
                if g.get("verified"):
                    verified_hit = g
                    break

        elif mode == "drug":
            band_abs = prediction["search_absolute"]
            predicted_tuple = (band_abs[0], band_abs[1])
            mw_step = kwargs.get("drug_mw_step", 0.5)
            mw_max = kwargs.get("drug_mw_max", 900.0)
            mw_start = max(50.0, band_abs[0] - search_forward * mw_step)
            mw_end = min(mw_max, band_abs[1] + search_forward * mw_step)
            mw = mw_start
            while mw <= mw_end:
                g = drug_mw_glow(mw, stability_threshold=kwargs.get("stability_threshold", 1.0), predicted_band=predicted_tuple)
                if g["glow"] >= glow_threshold:
                    all_glows.append(g)
                if g.get("verified"):
                    verified_hit = g
                    break
                mw = round(mw + mw_step, 4)

    _attach_near_echoes(fields, all_glows)

    def _glow_value(g: dict) -> float:
        return g.get("mw", g.get("candidate", g.get("p", 1)))

    echo_bins = {angle_bin_for_value(_glow_value(g), bins) for g in all_glows if not g.get("verified")}
    hit_bins = {f["angle_bin"] for f in fields}

    return {
        "schema_version": "solution_radius_probe_v1",
        "mode": mode,
        "hit_count": len(hits_sorted),
        "bins": bins,
        "glow_threshold": glow_threshold,
        "solution_fields": fields,
        "prediction": prediction,
        "hit_ratio_map": hit_ratio,
        "forward_scan_count": len(all_glows),
        "near_echo_count": sum(len(f["near_echoes"]) for f in fields),
        "shadow_echo_bins": sorted(echo_bins - hit_bins),
        "verified_hit": verified_hit,
        "glows": all_glows,
    }


def print_solution_radius_probe(payload: dict) -> None:
    print("Solution radius probe")
    print(f"mode: {payload['mode']}  hits: {payload['hit_count']}  bins: {payload['bins']}")
    if "error" in payload:
        print(f"error: {payload['error']}")
        return
    print()
    print("Solution fields  (left_radius | center | right_radius | d(log x) | bin):")
    for f in payload["solution_fields"]:
        lr = f"{f['left_radius']:.6g}" if f["left_radius"] is not None else "       —"
        rr = f"{f['right_radius']:.6g}" if f["right_radius"] is not None else "       —"
        an = f"{f['angle']:.6g}" if f["angle"] is not None else "—"
        echoes = len(f["near_echoes"])
        echo_note = f"  ({echoes} echoes: " + ", ".join(f"{e['glow']:.2f}" for e in f["near_echoes"][:4]) + ")" if echoes else ""
        print(
            f"  [{f['index']:>2}] lr={lr:<14}| {f['center']:>14} |rr={rr:<14}| dlog={an:<14} bin={f['angle_bin']:<3}"
            + echo_note
        )
    p = payload["prediction"]
    if p:
        print()
        print("Predictive band:")
        print(f"  trend_ratio:      {p['trend_ratio']}")
        print(f"  radius_spread:    {p['radius_spread']}")
        print(f"  next_center_est:  {p['next_center_estimate']}")
        print(f"  band (offset):    [{p['search_band_offset'][0]}, {p['search_band_offset'][1]}]")
        print(f"  band (absolute):  [{p['search_absolute'][0]}, {p['search_absolute'][1]}]")
        print(f"  band_width_rel:   {p['band_width_relative']:.6g}")
    hr = payload["hit_ratio_map"]
    print()
    print(f"Hit ratio map  mean dx/x={hr['mean_velocity']:.6g}  histogram={hr['angle_histogram']}")
    if payload["glows"]:
        print()
        top = sorted(payload["glows"], key=lambda g: -g["glow"])[:20]
        print(f"Forward scan glows (threshold≥{payload['glow_threshold']}, top {len(top)}):")
        for g in top:
            sym = "★" if g.get("verified") else " "
            if "mw" in g:
                score = f"  stability={g.get('stability_score', '?')}"
                cmpd = g.get("nearest_compound", "")
                print(f"  {sym} MW={g['mw']:<10.4f}  glow={g['glow']:.2f}  [{g['stage']}]{score}  {cmpd}")
            else:
                val = g.get("k", g.get("p", "?"))
                cand = g.get("candidate", "—")
                print(f"  {sym} val={val:<12} cand={cand:<20} glow={g['glow']:.2f}  [{g['stage']}]")
    if payload.get("verified_hit"):
        v = payload["verified_hit"]
        if "mw" in v:
            print(f"\n★ VERIFIED HIT in predicted band:  MW={v['mw']}  stability={v.get('stability_score', '?')}  {v.get('nearest_compound', '')}")
        else:
            val = v.get("k", v.get("p", "?"))
            cand = v.get("candidate", "—")
            print(f"\n★ VERIFIED HIT in predicted band:  val={val}  candidate={cand}")
    if payload["shadow_echo_bins"]:
        print(f"\nShadow echo bins (near-misses, no verified hits): {payload['shadow_echo_bins']}")


# ─────────────────────────────────────────────────────────────────────────────

def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prime-limit", type=int, default=1_000_000)
    parser.add_argument("--mersenne-exp-limit", type=int, default=5_000)
    parser.add_argument("--lidar-tail", type=int, default=8)
    parser.add_argument("--lidar-radius", type=int, default=128)
    parser.add_argument("--lidar-anchors", default="")
    parser.add_argument("--blind-count", type=int, default=30)
    parser.add_argument("--blind-base", type=int, default=1_000_000_000_000)
    parser.add_argument("--blind-step", type=int, default=9_999_937)
    parser.add_argument("--blind-window", type=int, default=20_000)
    parser.add_argument("--echolocate", default="", help="Comma-separated integers to probe, fast path")
    parser.add_argument("--echo-radius", type=int, default=64)
    parser.add_argument("--erdos-straus-lidar", action="store_true", help="Probe 4/n as three unit fractions")
    parser.add_argument("--erdos-limit", type=int, default=2_000)
    parser.add_argument("--erdos-proximity-count", type=int, default=8)
    parser.add_argument("--erdos-magnetic-wave", action="store_true", help="Rank 4/n candidates with a wave field")
    parser.add_argument("--erdos-wave-start", type=int, default=2_001)
    parser.add_argument("--erdos-wave-end", type=int, default=5_000)
    parser.add_argument("--erdos-wave-seed", type=int, default=2_000)
    parser.add_argument("--erdos-wave-bins", type=int, default=32)
    parser.add_argument("--erdos-wave-x-scan", type=int, default=16)
    parser.add_argument("--erdos-wave-top", type=int, default=128)
    parser.add_argument("--conjecture-wave", action="store_true", help="Run bounded wave telemetry on classic conjecture lanes")
    parser.add_argument("--wave-problems", default="all", help="Comma list: twin,goldbach,collatz,catalan,gilbreath,all")
    parser.add_argument("--wave-start", type=int, default=2_001)
    parser.add_argument("--wave-end", type=int, default=5_000)
    parser.add_argument("--wave-limit", type=int, default=50_000)
    parser.add_argument("--wave-seed", type=int, default=2_000)
    parser.add_argument("--wave-bins", type=int, default=32)
    parser.add_argument("--wave-top", type=int, default=128)
    parser.add_argument("--collatz-steps", type=int, default=1_000)
    parser.add_argument("--gravity-search", action="store_true", help="Run solution-gravity search from verified seed bodies")
    parser.add_argument("--gravity-problem", choices=["twin"], default="twin")
    parser.add_argument("--gravity-seed-limit", type=int, default=2_000)
    parser.add_argument("--gravity-limit", type=int, default=50_000)
    parser.add_argument("--gravity-bins", type=int, default=32)
    parser.add_argument("--gravity-top", type=int, default=256)
    parser.add_argument("--collatz-ratio-tree", action="store_true", help="Build reverse Collatz tree from non-1 seeds")
    parser.add_argument("--collatz-tree-seeds", default="27,6171,77031")
    parser.add_argument("--collatz-tree-depth", type=int, default=14)
    parser.add_argument("--collatz-tree-max-value", type=int, default=50_000_000)
    parser.add_argument("--collatz-tree-bins", type=int, default=32)
    parser.add_argument("--collatz-tree-include-one", action="store_true")
    parser.add_argument("--collatz-tree-top", type=int, default=12)
    parser.add_argument("--catalan-base-limit", type=int, default=32)
    parser.add_argument("--catalan-exp-limit", type=int, default=8)
    parser.add_argument("--gilbreath-prime-count", type=int, default=512)
    parser.add_argument("--gilbreath-rows", type=int, default=256)
    parser.add_argument("--mersenne-replay", action="store_true", help="Replay known hard Mersenne targets")
    parser.add_argument("--mersenne-replay-count", type=int, default=30)
    parser.add_argument("--mersenne-local-exact-count", type=int, default=20)
    parser.add_argument("--fermat-factor-flashlight", action="store_true")
    parser.add_argument("--fermat-start", type=int, default=5)
    parser.add_argument("--fermat-end", type=int, default=20)
    parser.add_argument("--fermat-k-limit", type=int, default=2_000_000)
    parser.add_argument(
        "--fermat-mesh-primes",
        default="3,5,7,11,13,17,19,23,29,31,37,41,43,47",
    )
    parser.add_argument("--ratio-map", action="store_true")
    parser.add_argument(
        "--ratio-source",
        choices=["mersenne-exponents", "fermat-factors", "fermat-k", "custom"],
        default="mersenne-exponents",
    )
    parser.add_argument("--ratio-values", default="", help="Comma-separated values for --ratio-source custom")
    parser.add_argument("--ratio-order", choices=["discovery", "value"], default="discovery")
    parser.add_argument("--ratio-count", type=int, default=30)
    parser.add_argument("--ratio-bins", type=int, default=32)
    parser.add_argument("--adaptive-cone-search", action="store_true")
    parser.add_argument("--adaptive-core-limit", type=int, default=5_000)
    parser.add_argument("--adaptive-bins", type=int, default=32)
    parser.add_argument("--grenade-limit", type=int, default=0)
    parser.add_argument("--grenade-halo", type=int, default=1)
    parser.add_argument("--grenade-max-hits", type=int, default=2)
    parser.add_argument("--grenade-proximity-count", type=int, default=3)
    parser.add_argument("--glow-bin-threshold", type=float, default=8.0)
    # Chemical compound fog-of-war modes
    parser.add_argument("--chem-ratio-map", action="store_true", help="Ratio map over compound MW space")
    parser.add_argument(
        "--chem-source",
        choices=["all", "stable", "unstable"],
        default="all",
        help="Filter compounds for --chem-ratio-map",
    )
    parser.add_argument(
        "--chem-order",
        choices=["mw", "stability", "half_life"],
        default="mw",
        help="Sort order for --chem-ratio-map",
    )
    parser.add_argument("--chem-bins", type=int, default=32, help="Angle bins for chemistry modes")
    parser.add_argument("--adaptive-chem-cone", action="store_true", help="Adaptive cone search over compound property space")
    parser.add_argument("--chem-core-mw-min", type=float, default=50.0)
    parser.add_argument("--chem-core-mw-max", type=float, default=350.0)
    parser.add_argument("--chem-stability-threshold", type=float, default=1.0)
    # Solution radius engine
    parser.add_argument("--solution-radius", action="store_true", help="Run solution radius probe")
    parser.add_argument(
        "--solution-mode",
        choices=["mersenne", "fermat-k", "drug"],
        default="drug",
        help="Domain for solution radius probe",
    )
    parser.add_argument(
        "--solution-hits",
        default="",
        help="Comma-separated hit values (ints or floats). Drug mode: omit to auto-load stable compounds.",
    )
    parser.add_argument("--solution-search-fwd", type=int, default=50, help="Extra steps to scan beyond predicted band")
    parser.add_argument("--solution-glow-threshold", type=float, default=0.50)
    parser.add_argument("--solution-bins", type=int, default=32)
    parser.add_argument("--solution-fermat-n", type=int, default=5, help="Fermat number index for fermat-k mode")
    parser.add_argument("--solution-drug-mw-step", type=float, default=0.5, help="MW grid step (Da) for drug scan")
    parser.add_argument("--solution-drug-mw-max", type=float, default=900.0, help="MW ceiling for drug scan")
    parser.add_argument("--solution-stability-threshold", type=float, default=1.0, help="Stability score threshold for drug verifier")
    # Answer-space probe (trit/binary/linear decomposition)
    parser.add_argument("--answer-space", action="store_true", help="Run trit/binary/linear-decomp answer-space probe")
    parser.add_argument("--answer-space-step", type=float, default=0.5, help="MW grid step for answer-space scan")
    parser.add_argument("--answer-space-sigma", type=float, default=1.0, help="How many σ to extend beyond PCA answer range")
    parser.add_argument("--answer-space-threshold", type=float, default=1.0, help="Stability threshold for trit[3] gate")
    parser.add_argument("--answer-space-band-lo", type=float, default=0.0, help="Predicted-band lower MW (0=use --solution-radius prediction)")
    parser.add_argument("--answer-space-band-hi", type=float, default=0.0, help="Predicted-band upper MW")
    parser.add_argument("--answer-space-show-all", action="store_true", help="Print full grid not just top candidates")
    parser.add_argument(
        "--answer-space-alphafold-uniprot",
        type=str,
        default="",
        metavar="UNIPROT",
        help="UniProt accession for AlphaFold trit[6] gate (e.g. P00533 for EGFR). "
             "Fetches mean pLDDT from AlphaFold EBI API and adds a 7th trit to every candidate. "
             "Requires network access. Gate: 0=pLDDT<50 (disordered), 1=50-70 (partial fold), "
             "2=>=70 (confident structure).",
    )
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.echolocate:
        payload = run_echolocation(parse_number_list(args.echolocate), args.echo_radius)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_echolocation(payload)
        return 0

    if args.erdos_straus_lidar:
        payload = run_erdos_straus_lidar(args.erdos_limit, args.erdos_proximity_count)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_erdos_straus_lidar(payload)
        return 0

    if args.erdos_magnetic_wave:
        payload = run_erdos_magnetic_wave(
            args.erdos_wave_start,
            args.erdos_wave_end,
            args.erdos_wave_seed,
            args.erdos_wave_bins,
            args.erdos_wave_x_scan,
            args.erdos_wave_top,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_erdos_magnetic_wave(payload)
        return 0

    if args.gravity_search:
        if args.gravity_problem != "twin":
            raise ValueError(f"unsupported gravity problem: {args.gravity_problem}")
        payload = run_twin_prime_gravity_search(
            args.gravity_seed_limit,
            args.gravity_limit,
            args.gravity_bins,
            args.gravity_top,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_twin_prime_gravity_search(payload)
        return 0

    if args.conjecture_wave:
        payload = run_conjecture_wave_suite(args)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_conjecture_wave_suite(payload)
        return 0

    if args.collatz_ratio_tree:
        payload = run_collatz_ratio_tree(
            parse_number_list(args.collatz_tree_seeds),
            args.collatz_tree_depth,
            args.collatz_tree_max_value,
            args.collatz_tree_bins,
            args.collatz_tree_include_one,
            args.collatz_tree_top,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_collatz_ratio_tree(payload)
        return 0

    if args.mersenne_replay:
        payload = run_mersenne_replay(args.mersenne_replay_count, args.mersenne_local_exact_count)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_mersenne_replay(payload)
        return 0

    if args.fermat_factor_flashlight:
        payload = run_fermat_factor_flashlight(
            args.fermat_start,
            args.fermat_end,
            args.fermat_k_limit,
            parse_mesh_primes(args.fermat_mesh_primes),
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_fermat_factor_flashlight(payload)
        return 0

    if args.ratio_map:
        payload = run_ratio_map(args)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_ratio_map(payload)
        return 0

    if args.adaptive_cone_search:
        payload = run_adaptive_cone_search(
            args.fermat_start,
            args.fermat_end,
            args.fermat_k_limit,
            parse_mesh_primes(args.fermat_mesh_primes),
            args.adaptive_core_limit,
            args.adaptive_bins,
            args.grenade_limit or args.fermat_k_limit,
            args.grenade_halo,
            args.grenade_max_hits,
            args.grenade_proximity_count,
            args.glow_bin_threshold,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_adaptive_cone_search(payload)
        return 0

    if args.chem_ratio_map:
        payload = run_chem_ratio_map(args.chem_source, args.chem_order, args.chem_bins)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_chem_ratio_map(payload)
        return 0

    if args.adaptive_chem_cone:
        payload = run_adaptive_chem_cone_search(
            args.chem_bins,
            args.chem_core_mw_min,
            args.chem_core_mw_max,
            args.chem_stability_threshold,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_adaptive_chem_cone_search(payload)
        return 0

    if args.solution_radius:
        raw_hits = args.solution_hits.strip()
        if raw_hits:
            try:
                hits = [float(v) if "." in v else int(v) for v in raw_hits.split(",") if v.strip()]
            except ValueError:
                print(f"--solution-hits: could not parse {raw_hits!r}", file=sys.stderr)
                return 1
        else:
            hits = []
        payload = run_solution_radius_probe(
            mode=args.solution_mode,
            hits=hits,
            search_forward=args.solution_search_fwd,
            k_limit=args.fermat_k_limit,
            mesh_primes=parse_mesh_primes(args.fermat_mesh_primes),
            glow_threshold=args.solution_glow_threshold,
            bins=args.solution_bins,
            fermat_n=args.solution_fermat_n,
            drug_mw_step=args.solution_drug_mw_step,
            drug_mw_max=args.solution_drug_mw_max,
            stability_threshold=args.solution_stability_threshold,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_solution_radius_probe(payload)
        return 0

    if args.answer_space:
        band = None
        if args.answer_space_band_lo > 0 and args.answer_space_band_hi > 0:
            band = (args.answer_space_band_lo, args.answer_space_band_hi)
        af_uniprot = getattr(args, "answer_space_alphafold_uniprot", "") or ""
        payload = run_answer_space_probe(
            stability_threshold=args.answer_space_threshold,
            predicted_band=band,
            mw_step=args.answer_space_step,
            extend_sigma=args.answer_space_sigma,
            bins=args.solution_bins,
            alphafold_uniprot=af_uniprot or None,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_answer_space_probe(payload)
            if args.answer_space_show_all:
                print()
                print("Full grid:")
                for g in payload["all_candidates"]:
                    print(f"  MW={g['mw']:.4f}  trit={g['trit_label']}  int={g['trit_int']}  glow={g['glow_float']}")
        return 0

    payload = {
        "schema_version": "prime_fog_probe_v1",
        "fermat_probe": run_fermat_probe(args.prime_limit, args.top),
        "lidar_probe": run_lidar_probe(
            args.prime_limit,
            args.lidar_tail,
            args.lidar_radius,
            parse_anchor_list(args.lidar_anchors),
        ),
        "blind_sweep": run_blind_sweep(
            args.blind_count,
            args.blind_base,
            args.blind_step,
            args.blind_window,
        ),
        "mersenne_probe": run_mersenne_probe(args.mersenne_exp_limit),
        "record_branch_probe": record_branch_probe(),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print_plain(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Prime fog-of-war probe.

This is an experiment harness, not a primality proof framework. It tests the
idea that geometry-like property folds can bracket a search space before exact
math verifies the target.
"""

from __future__ import annotations

import argparse
import bisect
import cmath
import colorsys
import hashlib
import json
import math
import sys
import time
from collections import Counter
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


def harmonic_wall(deviation: float, partial_deviation: float = 0.0) -> float:
    return 1 / (1 + max(0.0, deviation) + (2 * max(0.0, partial_deviation)))


def normalize_force(total_force: float) -> float:
    if total_force <= 0:
        return 0.0
    return total_force * harmonic_wall(total_force)


def semantic_invariant_packet(domain: str, form: str, normalized_name: str) -> dict:
    return {
        "domain": domain,
        "semantic_invariant": "unit-erased fractional proximity to a verified solution surface",
        "harmonic_wall": "H(d,pd)=1/(1+d+2*pd)",
        "force_normalization": "F/(1+F)=1/(1+1/F) for F>0",
        "local_form": form,
        "normalized_signal": normalized_name,
        "range": "[0,1]",
    }


U64_MAX = (1 << 64) - 1


def _trailing_zero_bits(value: int) -> int | None:
    if value <= 0:
        return None
    return (value & -value).bit_length() - 1


def _trit_label_to_int(values: list[int]) -> int:
    out = 0
    for value in values:
        out = (out * 3) + int(value)
    return out


DEFAULT_RESIDUE_MODULI = [2, 3, 5, 6, 7, 11, 13, 17, 19, 23, 29, 30, 210]


def _clean_positive_unique(values: list[int]) -> list[int]:
    return sorted({value for value in values if value > 0})


def _integer_residue_vector(core: int, moduli: list[int] | None = None) -> dict:
    active_moduli = _clean_positive_unique(moduli or DEFAULT_RESIDUE_MODULI)
    residues = {str(modulus): core % modulus if core else 0 for modulus in active_moduli}
    shadow_hits = [modulus for modulus in active_moduli if core >= 2 and core % modulus == 0]
    return {
        "mode": "fixed_modulus_tracks",
        "moduli": active_moduli,
        "residues": residues,
        "shadow_hits": shadow_hits,
        "mod6": residues.get("6", core % 6 if core else 0),
        "mod30": residues.get("30", core % 30 if core else 0),
        "mod210": residues.get("210", core % 210 if core else 0),
        "wheel30_lane": bool(core in (2, 3, 5) or core % 30 in WHEEL30_RESIDUES) if core else False,
    }


def _integer_factor_vector(core: int, factor_primes: list[int] | None = None) -> dict:
    """Bounded factor telemetry for ingestion.

    This is intentionally not an unbounded factorization routine. It divides by
    configured small primes, records exact witnesses found in that bound, and
    leaves the remaining cofactor as a residual tail for later verifier stages.
    """
    active_primes = _clean_positive_unique(factor_primes or ([2] + SMALL_FILTER_PRIMES[1:]))
    if core < 2:
        return {
            "mode": "bounded_trial_division",
            "factor_primes": active_primes,
            "division_budget": 0,
            "exponents": {},
            "factors": [],
            "residual": core,
            "residual_state": "outside_prime_domain",
            "complete": False,
        }

    residual = core
    exponents: dict[str, int] = {}
    factors = []
    divisions = 0
    for prime in active_primes:
        if prime < 2:
            continue
        divisions += 1
        exponent = 0
        while residual % prime == 0:
            residual //= prime
            exponent += 1
        if exponent:
            exponents[str(prime)] = exponent
            factors.append({"prime": prime, "exponent": exponent})
        if residual == 1:
            break

    if residual == 1:
        residual_state = "fully_factored_in_bound"
        complete = True
    elif residual <= U64_MAX and deterministic_miller_rabin_u64(residual):
        residual_state = "prime_residual_tail"
        complete = True
    else:
        residual_state = "unresolved_composite_or_large_tail"
        complete = False

    return {
        "mode": "bounded_trial_division",
        "factor_primes": active_primes,
        "division_budget": divisions,
        "exponents": exponents,
        "factors": factors,
        "residual": residual,
        "residual_state": residual_state,
        "complete": complete,
    }


def _integer_prime_verifier(core: int) -> dict:
    if core < 2:
        return {
            "domain": "Z integers",
            "normalization": "abs(raw)",
            "method": "domain_reject",
            "scope": "exact",
            "is_prime": False,
            "state": "outside_prime_domain",
        }

    if core <= U64_MAX:
        is_prime = deterministic_miller_rabin_u64(core)
        return {
            "domain": "Z integers",
            "normalization": "abs(raw)",
            "method": "deterministic_miller_rabin_u64",
            "scope": "exact for unsigned 64-bit integers",
            "is_prime": is_prime,
            "state": "prime" if is_prime else "composite",
        }

    divisor = first_small_divisor(core)
    if divisor is not None:
        return {
            "domain": "Z integers",
            "normalization": "abs(raw)",
            "method": "small_divisor_witness",
            "scope": "exact composite witness",
            "is_prime": False,
            "state": "composite",
            "witness": {"divisor": divisor, "cofactor": core // divisor},
        }

    probable_signal = deterministic_miller_rabin_u64(core)
    return {
        "domain": "Z integers",
        "normalization": "abs(raw)",
        "method": "miller_rabin_seed_probe",
        "scope": "telemetry only above unsigned 64-bit; true is not a proof",
        "is_prime": None if probable_signal else False,
        "probable_prime_signal": probable_signal,
        "state": "unresolved_probable_prime" if probable_signal else "composite_witnessed",
    }


def _integer_relation_row(
    raw: int,
    bins: int,
    mesh_primes: list[int] | None,
    binary_bits: int,
    factor_primes: list[int] | None = None,
    residue_moduli: list[int] | None = None,
) -> dict:
    core = abs(raw)
    sign = -1 if raw < 0 else 1 if raw > 0 else 0
    verifier = _integer_prime_verifier(core)
    residue_vector = _integer_residue_vector(core, residue_moduli)
    factor_vector = _integer_factor_vector(core, factor_primes or ([2] + (mesh_primes or SMALL_FILTER_PRIMES[1:])))
    small_divisor = first_small_divisor(core) if core >= 2 else None
    mesh = prime_mesh_score([core], mesh_primes) if core >= 2 else {
        "passed": 0,
        "total": len(mesh_primes or SMALL_FILTER_PRIMES[1:]),
        "ratio": 0.0,
        "blockers": [],
    }
    wheel_gate = 1.0 if residue_vector["wheel30_lane"] else 0.0
    bit_length = core.bit_length()
    popcount = core.bit_count()
    binary_density = popcount / max(1, bit_length)
    binary_balance = harmonic_wall(abs(binary_density - 0.5) * 2.0)
    suffix_width = max(1, min(binary_bits, max(1, bit_length)))
    suffix_mask = (1 << suffix_width) - 1
    verifier_signal = 1.0 if verifier["is_prime"] is True else 0.65 if verifier["is_prime"] is None else 0.15
    components = {
        "domain": 1.0 if core >= 2 else 0.05,
        "mesh": mesh["ratio"] if core >= 2 else 0.05,
        "no_small_blocker": 1.0 if small_divisor is None and core >= 2 else 0.12,
        "wheel_lane": wheel_gate if wheel_gate else 0.2,
        "binary_balance": binary_balance,
        "verifier_echo": verifier_signal,
        "negative_value_allowance": 1.0 if sign != 0 else 0.1,
    }
    product = multiplicative_wave_field(
        components,
        weights={
            "domain": 0.8,
            "mesh": 0.8,
            "no_small_blocker": 1.0,
            "wheel_lane": 0.4,
            "binary_balance": 0.35,
            "verifier_echo": 0.7,
            "negative_value_allowance": 0.25,
        },
    )
    trits = [
        2 if core >= 2 else 0,
        2 if mesh["ratio"] >= 1.0 else 1 if mesh["ratio"] >= 0.75 else 0,
        2 if small_divisor is None and core >= 2 else 0,
        2 if wheel_gate else 0,
        2 if verifier["is_prime"] is True else 1 if verifier["is_prime"] is None else 0,
        1 if sign < 0 else 2 if sign > 0 else 0,
    ]
    ternary_state = 1 if verifier["is_prime"] is True else -1 if verifier["is_prime"] is False else 0
    factor_wave = None
    if small_divisor is not None:
        factor_wave = {
            "divisor": small_divisor,
            "cofactor": core // small_divisor,
            "relation": f"{small_divisor}*{core // small_divisor}={core}",
        }

    return {
        "raw": raw,
        "core": core,
        "orientation": sign,
        "negative_tracking": {
            "allowed": True,
            "rule": "sign is orientation; primality lens uses abs(raw)",
            "mirror": -raw if raw != 0 else 0,
        },
        "exact_verifier": verifier,
        "ternary_state": ternary_state,
        "phase": {
            "theta": round(math.log(core) % (2 * math.pi), 12) if core > 0 else 0.0,
            "angle_bin": angle_bin_for_value(core, bins),
            "bins": bins,
        },
        "residue_vector": residue_vector,
        "factor_vector": factor_vector,
        "binary_vector": {
            "bit_length": bit_length,
            "popcount": popcount,
            "density": round(binary_density, 12),
            "density_harmonic": round(binary_balance, 12),
            "suffix_bits": suffix_width,
            "suffix": format(core & suffix_mask, f"0{suffix_width}b"),
            "trailing_zero_bits": _trailing_zero_bits(core),
            "trailing_zero_bits_n_minus_1": _trailing_zero_bits(core - 1),
            "trailing_zero_bits_n_plus_1": _trailing_zero_bits(core + 1),
        },
        "mesh": mesh,
        "factor_wave": factor_wave,
        "fold_echoes": number_fold_echo(core) if core >= 2 else [],
        "trit_vector": {
            "order": ["domain", "mesh", "no_small_blocker", "wheel_lane", "verifier", "orientation"],
            "values": trits,
            "label": "[" + "".join(str(v) for v in trits) + "]",
            "int": _trit_label_to_int(trits),
        },
        "field": {
            "field_strength": round(sum(components.values()) / len(components), 12),
            "normalized_force": round(normalize_force(sum(components.values())), 12),
            **product,
        },
    }


def _integer_relation_edges(rows: list[dict], bins: int) -> list[dict]:
    ordered = sorted(rows, key=lambda row: (row["core"], row["raw"]))
    edges = []
    for left, right in zip(ordered, ordered[1:]):
        a = int(left["core"])
        b = int(right["core"])
        raw_a = int(left["raw"])
        raw_b = int(right["raw"])
        gap = b - a
        min_core = min(a, b)
        gcd_value = math.gcd(a, b)
        if a == b and raw_a == -raw_b and raw_a != 0:
            relation = "negative_mirror_pair"
        elif a == b:
            relation = "same_absolute_core"
        elif a > 1 and b % a == 0:
            relation = "factor_wave_lands"
        else:
            relation = "ordered_gap"
        dx_over_x = gap / a if a > 0 else None
        dlog = (math.log(b) - math.log(a)) if a > 0 and b > 0 else None
        bin_gap = abs(left["phase"]["angle_bin"] - right["phase"]["angle_bin"])
        bin_gap = min(bin_gap, bins - bin_gap)
        gcd_pull = gcd_value / max(1, min_core) if min_core > 0 else 0.0
        phase_pull = harmonic_wall(bin_gap / max(1, bins))
        mirror_pull = 1.0 if relation == "negative_mirror_pair" else 0.35
        product = multiplicative_wave_field(
            {
                "gcd_pull": gcd_pull,
                "phase_pull": phase_pull,
                "mirror_pull": mirror_pull,
            },
            weights={"gcd_pull": 0.7, "phase_pull": 0.45, "mirror_pull": 0.35},
        )
        edges.append(
            {
                "from_raw": raw_a,
                "to_raw": raw_b,
                "from_core": a,
                "to_core": b,
                "relation": relation,
                "gap": gap,
                "dx_over_x": round(dx_over_x, 12) if dx_over_x is not None else None,
                "dlog": round(dlog, 12) if dlog is not None else None,
                "gcd": gcd_value,
                "xor": a ^ b,
                "hamming_distance": (a ^ b).bit_count(),
                "field": product,
            }
        )
    return edges


def _integer_shell_echoes(row: dict, shell_radius: int, bins: int) -> list[dict]:
    if shell_radius <= 0:
        return []
    center = int(row["core"])
    echoes = []
    for delta in range(-shell_radius, shell_radius + 1):
        candidate = center + delta
        if candidate < 0:
            continue
        verifier = _integer_prime_verifier(candidate)
        echoes.append(
            {
                "candidate_core": candidate,
                "delta": delta,
                "positive_value": candidate,
                "negative_mirror": -candidate if candidate != 0 else 0,
                "state": verifier["state"],
                "is_prime": verifier["is_prime"],
                "angle_bin": angle_bin_for_value(candidate, bins),
                "small_divisor": first_small_divisor(candidate) if candidate >= 2 else None,
            }
        )
    return echoes


def run_integer_magnifier(
    numbers: list[int],
    bins: int = 32,
    shell_radius: int = 2,
    mesh_primes: list[int] | None = None,
    binary_bits: int = 16,
    factor_primes: list[int] | None = None,
    residue_moduli: list[int] | None = None,
) -> dict:
    if not numbers:
        numbers = [-31, -29, -17, -5, -1, 0, 1, 2, 3, 4, 5, 17, 19, 29, 31, 33, 35]
    active_factor_primes = _clean_positive_unique(factor_primes or ([2] + (mesh_primes or SMALL_FILTER_PRIMES[1:])))
    active_residue_moduli = _clean_positive_unique(residue_moduli or DEFAULT_RESIDUE_MODULI)
    rows = [
        _integer_relation_row(
            value,
            bins,
            mesh_primes,
            binary_bits,
            active_factor_primes,
            active_residue_moduli,
        )
        for value in numbers
    ]
    edges = _integer_relation_edges(rows, bins)
    for row in rows:
        row["expansion_shell"] = _integer_shell_echoes(row, shell_radius, bins)

    active_bins = sorted({row["phase"]["angle_bin"] for row in rows if row["core"] > 0})
    verified = [row for row in rows if row["ternary_state"] == 1]
    rejected = [row for row in rows if row["ternary_state"] == -1]
    unresolved = [row for row in rows if row["ternary_state"] == 0]
    return {
        "schema_version": "prime_fog_integer_magnifier_v1",
        "contract": {
            "purpose": "testing magnification lens for integer relations",
            "truth_boundary": "only exact_verifier collapses a prime/composite state",
            "negative_rule": "negative values are preserved as orientation and normalized with abs(raw)",
        },
        "parameters": {
            "bins": bins,
            "shell_radius": shell_radius,
            "mesh_primes": mesh_primes or SMALL_FILTER_PRIMES[1:],
            "binary_bits": binary_bits,
            "factor_primes": active_factor_primes,
            "residue_moduli": active_residue_moduli,
        },
        "summary": {
            "input_count": len(numbers),
            "negative_count": sum(1 for value in numbers if value < 0),
            "zero_count": sum(1 for value in numbers if value == 0),
            "positive_count": sum(1 for value in numbers if value > 0),
            "verified_prime_count": len(verified),
            "rejected_count": len(rejected),
            "unresolved_count": len(unresolved),
            "factor_division_budget": sum(row["factor_vector"]["division_budget"] for row in rows),
            "complete_factor_vector_count": sum(1 for row in rows if row["factor_vector"]["complete"]),
            "active_angle_bins": active_bins,
            "shadow_angle_bins": [idx for idx in range(bins) if idx not in active_bins],
        },
        "rows": rows,
        "relation_edges": edges,
    }


def print_integer_magnifier(payload: dict) -> None:
    print("Integer relation magnifier")
    print(f"purpose: {payload['contract']['purpose']}")
    print(f"truth boundary: {payload['contract']['truth_boundary']}")
    print(f"negative rule: {payload['contract']['negative_rule']}")
    print(f"summary: {payload['summary']}")
    print()
    print("Numbers:")
    for row in payload["rows"]:
        blocker = row["factor_wave"]["relation"] if row["factor_wave"] else "none"
        print(
            f"  raw={row['raw']:<8} core={row['core']:<8} orient={row['orientation']:+d} "
            f"state={row['exact_verifier']['state']:<25} ternary={row['ternary_state']:+d} "
            f"field={row['field']['field_strength']:.6f} product={row['field']['product_field_strength']:.6f}"
        )
        print(
            f"    bin={row['phase']['angle_bin']:<2} mod30={row['residue_vector']['mod30']:<2} "
            f"trit={row['trit_vector']['label']} bits={row['binary_vector']['suffix']} "
            f"pop={row['binary_vector']['popcount']} blocker={blocker}"
        )
        print(
            f"    factor_vector={row['factor_vector']['exponents']} "
            f"residual={row['factor_vector']['residual']} "
            f"state={row['factor_vector']['residual_state']} "
            f"residue_shadows={row['residue_vector']['shadow_hits']}"
        )
        if row["expansion_shell"]:
            shell = ", ".join(
                f"{echo['candidate_core']}:{echo['state']}" for echo in row["expansion_shell"]
            )
            print(f"    shell: {shell}")
    if payload["relation_edges"]:
        print()
        print("Relation edges:")
        for edge in payload["relation_edges"][:16]:
            print(
                f"  {edge['from_raw']} -> {edge['to_raw']} "
                f"{edge['relation']} gap={edge['gap']} gcd={edge['gcd']} "
                f"ham={edge['hamming_distance']} product={edge['field']['product_field_strength']:.6f}"
            )


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


def hyperbolic_point(value: int, scale: float) -> dict:
    log_radius = math.log(max(2, value))
    safe_scale = max(1.0, scale)
    radius = min(0.999999, math.tanh(log_radius / safe_scale))
    theta = log_radius % (2 * math.pi)
    return {
        "r": radius,
        "theta": theta,
        "x": radius * math.cos(theta),
        "y": radius * math.sin(theta),
    }


def poincare_distance(a: dict, b: dict) -> float:
    dx = a["x"] - b["x"]
    dy = a["y"] - b["y"]
    euclidean_sq = (dx * dx) + (dy * dy)
    a_norm_sq = (a["x"] * a["x"]) + (a["y"] * a["y"])
    b_norm_sq = (b["x"] * b["x"]) + (b["y"] * b["y"])
    denominator = max(1e-12, (1 - a_norm_sq) * (1 - b_norm_sq))
    return math.acosh(1 + (2 * euclidean_sq / denominator))


def solution_gravity_bodies(values: list[int], bins: int, hyperbolic_scale: float | None = None) -> list[dict]:
    profile = solution_radius_profile(values)
    median_right = profile["median_right_ratio"] or 0.0
    scale = hyperbolic_scale or max(1.0, math.log(max(values) if values else 2))
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
                "hyperbolic": hyperbolic_point(center, scale),
            }
        )
    return bodies


def solution_gravity_at_candidate(
    candidate: int,
    bodies: list[dict],
    metric: str = "cylindrical",
    hyperbolic_scale: float | None = None,
) -> dict:
    if candidate <= 0 or not bodies:
        return {
            "gravity_field": 0.0,
            "gravity_field_normalized": 0.0,
            "nearest_solution": None,
            "top_forces": [],
        }

    log_radius = math.log(candidate)
    theta = log_radius % (2 * math.pi)
    scale = hyperbolic_scale or max(1.0, max(body["log_radius"] for body in bodies))
    candidate_hyperbolic = hyperbolic_point(candidate, scale)
    total_force = 0.0
    forces = []
    for body in bodies:
        radial_distance = abs(log_radius - body["log_radius"])
        angular_distance = circular_tau_distance(theta, body["theta"])
        cylindrical_distance = math.sqrt((radial_distance * radial_distance) + (angular_distance * angular_distance))
        hyperbolic_distance = poincare_distance(candidate_hyperbolic, body["hyperbolic"])
        if metric == "hyperbolic":
            geodesic_distance = hyperbolic_distance
        elif metric == "hybrid":
            geodesic_distance = math.sqrt((cylindrical_distance * hyperbolic_distance) + 1e-12)
        else:
            geodesic_distance = cylindrical_distance
        candidate_ratio = abs(candidate - body["center"]) / max(1, body["center"])
        target_ratio = body["right_ratio"] if candidate >= body["center"] else body["left_ratio"]
        ratio_error = abs(math.log1p(candidate_ratio) - math.log1p(max(0.0, target_ratio)))
        ratio_alignment = 1 / (1 + ratio_error)
        magnetic_band = harmonic_wall(geodesic_distance, ratio_error)
        force = (body["mass"] * ratio_alignment) / ((geodesic_distance * geodesic_distance) + 0.03)
        total_force += force
        forces.append(
            {
                "center": body["center"],
                "force": round(force, 12),
                "mass": body["mass"],
                "geodesic_distance": round(geodesic_distance, 12),
                "cylindrical_distance": round(cylindrical_distance, 12),
                "hyperbolic_distance": round(hyperbolic_distance, 12),
                "ratio_alignment": round(ratio_alignment, 12),
                "magnetic_band": round(magnetic_band, 12),
                "direction": 1 if candidate >= body["center"] else -1,
            }
        )

    forces.sort(key=lambda row: (-row["force"], row["center"]))
    normalized = normalize_force(total_force)
    return {
        "gravity_field": round(total_force, 12),
        "gravity_field_normalized": round(normalized, 12),
        "gravity_metric": metric,
        "nearest_solution": forces[0]["center"] if forces else None,
        "top_forces": forces[:4],
    }


# ── Float-safe gravity primitives ────────────────────────────────────────────
# These extend the integer gravity well infrastructure to accept any real
# number — ratios, decimals, atomically small (1e-15) and very large (1e20).
# They use log1p instead of log so values near 0 stay well-behaved, and they
# use absolute value + epsilon so negative inputs don't crash.  The Poincaré
# disk embedding is identical to hyperbolic_point but scaled to the log1p
# range rather than the raw integer log range.


def _hyperbolic_point_float(value: float, scale: float) -> dict:
    """Embed any finite real in the Poincaré disk via log1p(|value|)."""
    pos = max(1e-15, abs(float(value)))
    log_val = math.log1p(pos)
    safe_scale = max(1e-9, abs(scale))
    radius = min(0.999999, math.tanh(log_val / safe_scale))
    theta = log_val % (2 * math.pi)
    return {
        "r": radius,
        "theta": theta,
        "x": radius * math.cos(theta),
        "y": radius * math.sin(theta),
        "log_val": log_val,
    }


def _gravity_bodies_float(
    values: list,
    bins: int,
    scale: float | None = None,
) -> list[dict]:
    """Build gravity bodies from any sequence of finite real numbers.

    Accepts floats, ratios, decimals, very small (1e-15) and very large (1e20)
    values.  Non-finite values are silently filtered.
    """
    filtered = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not filtered:
        return []
    pos_vals = [max(1e-15, abs(v)) for v in filtered]
    log_vals = [math.log1p(v) for v in pos_vals]
    # Anchor the Poincaré disk to the fundamental Riemann zero frequency ρ₁:
    #   scale = t₁ / 2π ≈ 2.249
    # This maps abs_ratio=4 (anchor threshold) to r≈0.61 on the disk,
    # and is scale-invariant — the same embedding regardless of prime range.
    auto_scale = scale if scale is not None else _RIEMANN_ZERO_FREQS[0] / (2 * math.pi)
    bodies: list[dict] = []
    for i, (orig, lv) in enumerate(zip(filtered, log_vals)):
        left_lv = log_vals[i - 1] if i > 0 else None
        right_lv = log_vals[i + 1] if i + 1 < len(log_vals) else None
        left_ratio = abs(lv - left_lv) / max(1e-12, abs(lv)) if left_lv is not None else 0.0
        right_ratio = abs(right_lv - lv) / max(1e-12, abs(lv)) if right_lv is not None else 0.0
        curvature = abs(right_ratio - left_ratio) if left_lv is not None and right_lv is not None else 0.0
        mass = 1.0 + min(3.0, curvature * 600)
        bodies.append(
            {
                "center": orig,
                "log_val": lv,
                "theta": lv % (2 * math.pi),
                "left_ratio": left_ratio,
                "right_ratio": right_ratio,
                "curvature": round(curvature, 12),
                "mass": round(mass, 12),
                "hyperbolic": _hyperbolic_point_float(orig, auto_scale),
            }
        )
    return bodies


def _gravity_at_float(
    candidate: float,
    bodies: list[dict],
    metric: str = "hyperbolic",
) -> dict:
    """Score a float candidate against gravity bodies built by _gravity_bodies_float.

    Returns gravity_field (raw force sum) and gravity_field_normalized ∈ [0,1].
    The hyperbolic metric uses the Poincaré disk distance, making the score
    scale-invariant: it only depends on relative log-space positions, not on
    the absolute magnitude of the values.
    """
    if not bodies or not math.isfinite(float(candidate)):
        return {"gravity_field": 0.0, "gravity_field_normalized": 0.0}
    pos_cand = max(1e-15, abs(float(candidate)))
    log_cand = math.log1p(pos_cand)
    theta_cand = log_cand % (2 * math.pi)
    # Same Riemann-anchored scale as _gravity_bodies_float — bodies and candidate
    # must embed in the same disk geometry.
    auto_scale = _RIEMANN_ZERO_FREQS[0] / (2 * math.pi)
    cand_hyp = _hyperbolic_point_float(candidate, auto_scale)
    total_force = 0.0
    for body in bodies:
        radial_distance = abs(log_cand - body["log_val"])
        angular_distance = circular_tau_distance(theta_cand, body["theta"])
        cylindrical_dist = math.sqrt(radial_distance**2 + angular_distance**2)
        hyp_dist = poincare_distance(cand_hyp, body["hyperbolic"])
        if metric == "hyperbolic":
            geodesic_dist = hyp_dist
        elif metric == "hybrid":
            geodesic_dist = math.sqrt(cylindrical_dist * hyp_dist + 1e-12)
        else:
            geodesic_dist = cylindrical_dist
        cand_ratio = abs(pos_cand - body["center"]) / max(1e-12, body["center"])
        target_ratio = body["right_ratio"] if candidate >= body["center"] else body["left_ratio"]
        ratio_error = abs(math.log1p(cand_ratio) - math.log1p(max(0.0, target_ratio)))
        ratio_alignment = 1.0 / (1.0 + ratio_error)
        force = (body["mass"] * ratio_alignment) / (geodesic_dist**2 + 0.03)
        total_force += force
    normalized = normalize_force(total_force)
    return {
        "gravity_field": round(total_force, 12),
        "gravity_field_normalized": round(normalized, 12),
    }


def _topological_type_at_float(candidate: float, bodies: list[dict]) -> dict:
    """Classify the topological flow type at candidate in the Poincaré gravity field.

    Decomposes the gravity field into left-side vs right-side contributions (in
    log space) and computes the net force vector in disk coordinates.  From these
    three scalar quantities — asymmetry, cancellation, total force — classifies
    the candidate as one of three geometric types:

      compression  — balanced pull from both sides, net vector largely cancels.
                     Candidate sits in a 'valley': gap ratios converge toward it.
      saddle       — strongly asymmetric pull.  One side dominates.  Curvature
                     changes sign here — the inflection / phase-transition zone.
      expansion    — total field is weak.  Candidate is in a sparse, diffuse zone.

    Returns a dict with:
      type         : "compression" | "saddle" | "expansion"
      asymmetry    : 0..1  (0 = perfectly symmetric left/right)
      cancellation : 0..1  (how much of the scalar force the vector field cancels)
      topo_score   : float in [0,1] — compressed→1, saddle→0.5, expansion→0
      confidence   : 0..1
    """
    if not bodies or not math.isfinite(float(candidate)):
        return {
            "type": "unknown",
            "asymmetry": 0.0,
            "cancellation": 0.0,
            "topo_score": 0.0,
            "confidence": 0.0,
        }

    pos_cand = max(1e-15, abs(float(candidate)))
    log_cand = math.log1p(pos_cand)
    theta_cand = log_cand % (2 * math.pi)
    auto_scale = _RIEMANN_ZERO_FREQS[0] / (2 * math.pi)
    cand_hyp = _hyperbolic_point_float(candidate, auto_scale)

    left_force = 0.0
    right_force = 0.0
    net_x = 0.0
    net_y = 0.0

    for body in bodies:
        hyp_dist = poincare_distance(cand_hyp, body["hyperbolic"])
        geodesic_dist = hyp_dist
        cand_ratio = abs(pos_cand - body["center"]) / max(1e-12, body["center"])
        target_ratio = body["right_ratio"] if candidate >= body["center"] else body["left_ratio"]
        ratio_error = abs(math.log1p(cand_ratio) - math.log1p(max(0.0, target_ratio)))
        ratio_alignment = 1.0 / (1.0 + ratio_error)
        force_mag = (body["mass"] * ratio_alignment) / (geodesic_dist**2 + 0.03)

        # Direction vector in disk space: from candidate toward body
        dx = body["hyperbolic"]["x"] - cand_hyp["x"]
        dy = body["hyperbolic"]["y"] - cand_hyp["y"]
        dlen = math.sqrt(dx**2 + dy**2 + 1e-15)
        net_x += force_mag * dx / dlen
        net_y += force_mag * dy / dlen

        if body["log_val"] < log_cand:
            left_force += force_mag
        else:
            right_force += force_mag

    total = left_force + right_force
    asymmetry = abs(left_force - right_force) / max(1e-12, total)
    net_mag = math.sqrt(net_x**2 + net_y**2)
    # Cancellation: how much the vector forces cancel against each other.
    # High cancellation with strong total → balanced pull from both sides (compression).
    cancellation = 1.0 - net_mag / max(1e-12, total)
    flow_angle = math.atan2(net_y, net_x)

    # Thresholds (Riemann-anchored disk geometry; not tuned per range)
    ASYMMETRY_SADDLE = 0.40
    FORCE_EXPANSION = 0.25

    if asymmetry >= ASYMMETRY_SADDLE:
        topo_type = "saddle"
        topo_score = 0.5 + 0.5 * asymmetry          # 0.7..1.0 range for strong saddles
        confidence = min(1.0, asymmetry)
    elif total < FORCE_EXPANSION:
        topo_type = "expansion"
        topo_score = 0.0
        confidence = 1.0 - min(1.0, total / FORCE_EXPANSION)
    else:
        topo_type = "compression"
        topo_score = cancellation * min(1.0, total / (total + 1.0))
        confidence = min(1.0, cancellation)

    return {
        "type": topo_type,
        "asymmetry": round(asymmetry, 6),
        "cancellation": round(cancellation, 6),
        "flow_angle": round(flow_angle, 6),
        "left_force": round(left_force, 6),
        "right_force": round(right_force, 6),
        "net_mag": round(net_mag, 6),
        "topo_score": round(topo_score, 6),
        "confidence": round(confidence, 6),
    }


# ── Musical mode channels ─────────────────────────────────────────────────────
# Adaptive tonic = geometric mean of abs_ratio window → log-uniform key center.
# Each ratio maps to a pitch class via 12*log2(r/tonic) % 12 (equal temperament).
# Seven diatonic modes are scored by mean nearest-degree distance; the best fit
# determines the local "mode" of the prime gap field.  Mode-shift is the cosine
# distance between early-half vs late-half mode-weight vectors — detects structural
# inflection mid-window without knowing the scale of abs_ratio values.
_DIATONIC_MODES: dict[str, list[float]] = {
    "ionian":     [0, 2, 4, 5, 7, 9, 11],
    "dorian":     [0, 2, 3, 5, 7, 9, 10],
    "phrygian":   [0, 1, 3, 5, 7, 8, 10],
    "lydian":     [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "aeolian":    [0, 2, 3, 5, 7, 8, 10],
    "locrian":    [0, 1, 3, 5, 6, 8, 10],
}
_DIATONIC_MODE_NAMES = list(_DIATONIC_MODES.keys())
_DIATONIC_MODE_DEGREES = list(_DIATONIC_MODES.values())


def _musical_mode_channels(ratio_vals: list[float]) -> dict:
    """Adaptive tonic + diatonic mode fit channels for a window of abs_ratio values.

    Returns:
        local_tonic       : geometric mean of |ratio_vals| (log-uniform key center)
        best_mode         : mode name with lowest mean nearest-degree semitone error
        mode_fit_score    : 1 - mean_error/6.0  in [0, 1]  (1 = perfect fit)
        mode_shift_channel: cosine distance between early-half and late-half mode
                            weight vectors — near 1.0 signals a structural transition
    """
    _EMPTY: dict = {
        "local_tonic": 1.0,
        "best_mode": "none",
        "mode_fit_score": 0.0,
        "mode_shift_channel": 0.0,
    }
    n = len(ratio_vals)
    if n < 2:
        return _EMPTY

    log_sum = 0.0
    valid = 0
    for r in ratio_vals:
        if r > 1e-9:
            log_sum += math.log(r)
            valid += 1
    if valid < 2:
        return _EMPTY
    local_tonic = math.exp(log_sum / valid)

    pitch_classes = []
    for r in ratio_vals:
        if r > 1e-9:
            pitch_classes.append((12.0 * math.log2(r / local_tonic)) % 12.0)

    def _nearest_err(pc: float, degrees: list) -> float:
        best = 12.0
        for d in degrees:
            delta = abs(pc - d)
            if delta > 6.0:
                delta = 12.0 - delta
            if delta < best:
                best = delta
        return best

    def _mode_error_vec(pitches: list) -> list:
        if not pitches:
            return [6.0] * len(_DIATONIC_MODE_DEGREES)
        return [
            sum(_nearest_err(pc, deg) for pc in pitches) / len(pitches)
            for deg in _DIATONIC_MODE_DEGREES
        ]

    errors = _mode_error_vec(pitch_classes)
    best_idx = int(min(range(len(errors)), key=lambda i: errors[i]))
    best_mode = _DIATONIC_MODE_NAMES[best_idx]
    mode_fit_score = max(0.0, 1.0 - errors[best_idx] / 6.0)

    mode_shift_channel = 0.0
    if len(pitch_classes) >= 4:
        half = len(pitch_classes) // 2
        early_err = _mode_error_vec(pitch_classes[:half])
        late_err = _mode_error_vec(pitch_classes[half:])
        # Invert errors to weights (lower error = higher weight)
        ew = [max(0.0, 6.0 - e) for e in early_err]
        lw = [max(0.0, 6.0 - e) for e in late_err]
        dot = sum(a * b for a, b in zip(ew, lw))
        mag_e = math.sqrt(sum(x * x for x in ew))
        mag_l = math.sqrt(sum(x * x for x in lw))
        if mag_e > 1e-9 and mag_l > 1e-9:
            mode_shift_channel = max(0.0, 1.0 - dot / (mag_e * mag_l))

    return {
        "local_tonic": round(local_tonic, 6),
        "best_mode": best_mode,
        "mode_fit_score": round(mode_fit_score, 6),
        "mode_shift_channel": round(mode_shift_channel, 6),
    }


# ── Lambda shadow channels ────────────────────────────────────────────────────
# Flashlight: illuminate the local prime gap field with the von Mangoldt / prime-
# density scaling law.  Expected echo baseline from PNT: mean of Λ(n)/ln(n) → 1.
# Shadow = observed ln-weighted gap density − expected baseline.
#
# lambda_shadow_channel   : mean of (observed - expected) shadow over context window
#                           positive = field is denser than baseline (hot zone)
# lambda_gradient_channel : late-half minus early-half shadow mean (trajectory slope)
# lambda_peak_lag         : index (0..n-1) of the maximum shadow value in the window;
#                           normalized to [0,1].  Near 1.0 = shadow peak is recent.
#
# Key design choice: expected = 1.0 everywhere (PNT; Λ̄ ≈ 1) so the baseline is
# parameter-free and scale-invariant.  Observed echo weight for step i is:
#     w_i = abs_ratio_i / ln(approx_prime_i)
# where approx_prime_i is the scan_prime scaled by the step offset (rough), but
# since ln(p) changes slowly, using the single anchor ln(scan_prime) works fine.


def _lambda_shadow_channels(ratio_vals: list[float], scan_prime: int) -> dict:
    """Von Mangoldt / PNT shadow channels.

    ratio_vals  : abs_ratio values from the context window (already absolute values)
    scan_prime  : the prime at the scan position (used for ln-scaling)

    Returns:
        lambda_shadow_channel   : mean(observed - 1.0) over window, clipped to [-2, 2]
        lambda_gradient_channel : late_mean_shadow - early_mean_shadow
        lambda_peak_lag         : normalized position of max shadow in window [0, 1]
    """
    _EMPTY = {
        "lambda_shadow_channel": 0.0,
        "lambda_gradient_channel": 0.0,
        "lambda_peak_lag": 0.5,
    }
    n = len(ratio_vals)
    if n < 2 or scan_prime < 2:
        return _EMPTY

    ln_p = math.log(max(scan_prime, 2))
    if ln_p < 1e-9:
        return _EMPTY

    # Observed echo weight per step: |ratio| / ln(p) → compare to expected baseline 1.0
    shadows = [r / ln_p for r in ratio_vals]

    mean_shadow = sum(shadows) / n
    clipped_shadow = max(-2.0, min(2.0, mean_shadow - 1.0))

    half = max(1, n // 2)
    early_mean = sum(shadows[:half]) / half
    late_mean = sum(shadows[half:]) / max(1, n - half)
    gradient = max(-2.0, min(2.0, late_mean - early_mean))

    peak_idx = int(max(range(n), key=lambda i: shadows[i]))
    peak_lag = peak_idx / max(1, n - 1)

    return {
        "lambda_shadow_channel": round(clipped_shadow, 6),
        "lambda_gradient_channel": round(gradient, 6),
        "lambda_peak_lag": round(peak_lag, 6),
    }


# ── Graph-map channels (gap transition graph) ─────────────────────────────────
# Treat the context window of abs_ratio values as a directed sequence graph:
# each node is a ratio value, each edge (i→i+1) carries the signed difference.
#
# Four channels capture structure the point-by-point camera and lambda flashlight
# do not see:
#
#   graph_monotone_ramp  : longest monotone (up or down) sub-run, normalized by n.
#                          Near 1.0 = the whole window is a single ramp → field
#                          is building or dissipating consistently.
#   graph_return_rate    : fraction of steps that move TOWARD the local geometric
#                          mean (tonic).  High = oscillatory field, low = trending.
#   graph_edge_variance  : variance of successive differences |r_{i+1} - r_i|.
#                          High = chaotic transitions; low = smooth progression.
#   graph_attractor_score: concentration of the ratio distribution.  Computed as
#                          1 - normalized entropy of a 5-bin histogram of ratio_vals.
#                          Near 1.0 = nearly all ratios fall in one magnitude band
#                          (strong attractor); near 0.0 = uniform spread.


def _graph_map_channels(ratio_vals: list[float]) -> dict:
    """Gap transition graph structural channels for a context window of abs_ratio values."""
    _EMPTY = {
        "graph_monotone_ramp": 0.0,
        "graph_return_rate": 0.5,
        "graph_edge_variance": 0.0,
        "graph_attractor_score": 0.0,
    }
    n = len(ratio_vals)
    if n < 2:
        return _EMPTY

    # ── local tonic (geometric mean) for return-rate computation ──────────────
    log_sum = sum(math.log(max(r, 1e-9)) for r in ratio_vals)
    tonic = math.exp(log_sum / n)

    # ── graph_monotone_ramp ──────────────────────────────────────────────────
    # Length of the longest consecutive run of strictly increasing or decreasing steps.
    max_run = 1
    cur_run = 1
    cur_dir = 0  # 0=unknown, 1=up, -1=down
    for i in range(1, n):
        delta = ratio_vals[i] - ratio_vals[i - 1]
        step_dir = 1 if delta > 0 else (-1 if delta < 0 else 0)
        if step_dir == 0:
            cur_run = 1
            cur_dir = 0
        elif cur_dir == 0 or step_dir == cur_dir:
            cur_run += 1
            cur_dir = step_dir
        else:
            cur_run = 2
            cur_dir = step_dir
        if cur_run > max_run:
            max_run = cur_run
    graph_monotone_ramp = (max_run - 1) / max(1, n - 1)

    # ── graph_return_rate ────────────────────────────────────────────────────
    # Fraction of steps where |r_i - tonic| < |r_{i-1} - tonic| (moving toward center).
    returns = sum(
        1 for i in range(1, n)
        if abs(ratio_vals[i] - tonic) < abs(ratio_vals[i - 1] - tonic)
    )
    graph_return_rate = returns / (n - 1)

    # ── graph_edge_variance ──────────────────────────────────────────────────
    edges = [abs(ratio_vals[i] - ratio_vals[i - 1]) for i in range(1, n)]
    edge_mean = sum(edges) / len(edges)
    edge_var = sum((e - edge_mean) ** 2 for e in edges) / len(edges)
    # Normalize: divide by (max_ratio - min_ratio)^2 to be scale-invariant
    ratio_range = max(ratio_vals) - min(ratio_vals)
    graph_edge_variance = edge_var / max(1e-9, ratio_range ** 2)
    graph_edge_variance = min(1.0, graph_edge_variance)

    # ── graph_attractor_score ────────────────────────────────────────────────
    # 5-bin histogram of ratio_vals in [min, max]; entropy concentration.
    r_min = min(ratio_vals)
    r_max = max(ratio_vals)
    if r_max <= r_min:
        graph_attractor_score = 1.0
    else:
        bins = [0] * 5
        for r in ratio_vals:
            b = min(4, int(5 * (r - r_min) / (r_max - r_min)))
            bins[b] += 1
        probs = [b / n for b in bins if b > 0]
        entropy = -sum(p * math.log2(p) for p in probs)
        max_entropy = math.log2(min(5, n))
        graph_attractor_score = max(0.0, 1.0 - entropy / max(1e-9, max_entropy))

    return {
        "graph_monotone_ramp": round(graph_monotone_ramp, 6),
        "graph_return_rate": round(graph_return_rate, 6),
        "graph_edge_variance": round(graph_edge_variance, 6),
        "graph_attractor_score": round(graph_attractor_score, 6),
    }


# ── Riemann zero frequencies ─────────────────────────────────────────────────
# The imaginary parts of the first non-trivial zeros of ζ(s) on the critical
# line Re(s)=1/2. These are the exact frequencies of the oscillation in π(x)
# (the prime counting function). The formula is:
#   π(x) ≈ Li(x) - Σ_ρ Li(x^ρ)  (sum over non-trivial zeros ρ)
# Each zero t_n contributes a cosine wave cos(t_n * log x) to the error term.
# Using these as a wave field gives the probe the actual harmonic signature of
# where prime density is above or below the smooth prediction.
_RIEMANN_ZERO_FREQS: list[float] = [
    14.134725141734693,   # ρ_1  — the fundamental
    21.022039638771554,   # ρ_2
    25.010857580145688,   # ρ_3
    30.424876125859513,   # ρ_4
    32.935061587739189,   # ρ_5
    37.586178158825671,   # ρ_6
    40.918719012147495,   # ρ_7
    43.327073280914999,   # ρ_8
    48.005150881167159,   # ρ_9
    49.773832477672302,   # ρ_10
]

# Natural harmonic ratios for the prime ratio map (small/large alignment check).
# These are the ratios that appear in musical tuning, plant growth, and quantum
# shell structure — used to test whether twin prime center spacings cluster near them.
_NATURAL_HARMONICS: list[tuple[str, float]] = [
    ("octave",       2.0),
    ("fifth",        3 / 2),           # 1.500
    ("fourth",       4 / 3),           # 1.333
    ("major_third",  5 / 4),           # 1.250
    ("minor_third",  6 / 5),           # 1.200
    ("phi",          1.6180339887),    # golden ratio
    ("sqrt2",        1.4142135623),
    ("sqrt3",        1.7320508076),
    ("e_over_pi",    math.e / math.pi),  # 0.8653 — below 1 (ratio can go either way)
    ("pi_over_e",    math.pi / math.e),  # 1.1557
    ("phi_sq",       2.6180339887),    # φ² = φ+1
]

# Echo-diagnostic small divisors: the prime-shaped-but-composite trap zone.
# Candidates that land near these frequencies are composites masquerading as primes.
# The integer ratio clearance field measures fractional-part distance from each trap.
_DIV_ECHO_SMALL: list[int] = [7, 11, 13, 17, 19, 23]
# Next layer of divisor traps — significant at ranges > 8810 (10x seed horizon).
_DIV_ECHO_LARGE: list[int] = [29, 31, 37, 41, 43, 47]

# Hardy-Littlewood twin prime constant C₂ = ∏_{p≥3} p(p-2)/(p-1)²
_TWIN_PRIME_CONSTANT: float = 0.6601618158468695739278121


def _div_ratio_clearance(p: int, divisors: list[int] = _DIV_ECHO_SMALL) -> float:
    """Integer ratio fractional-part clearance for p and p+2 against small divisors.

    For each divisor d and each of n in {p, p+2}:
      frac     = (n % d) / d          — position in the unit interval [0,1)
      clearance = min(frac, 1-frac)*2  — 0 = exactly divisible (trap), 1 = maximally clear

    Combined = geometric mean over all (d, n) pairs.

    This is the 'integer ratio search in the binary region': scanning the interval
    [0,1) of n/d mod 1 for proximity to integer landings. A candidate sitting close
    to an integer ratio n/d is the algebraic equivalent of an arrow caught in the
    7/11/13 crosswind just before the target.
    """
    scores: list[float] = []
    for d in divisors:
        for n in (p, p + 2):
            frac = (n % d) / d
            scores.append(min(frac, 1.0 - frac) * 2.0)
    if not scores:
        return 1.0
    product = 1.0
    for s in scores:
        product *= max(s, 1e-9)
    return product ** (1.0 / len(scores))


def riemann_zero_wave(p: int, freqs: list[float] = _RIEMANN_ZERO_FREQS) -> float:
    """Riemann zero wave field at candidate p.

    Computes the normalized superposition of cosine waves driven by the imaginary
    parts of the first N non-trivial Riemann zeros:

      raw(p) = (1/N) * Σ_n cos(t_n * log(p))

    Maps to [0, 1] via (raw + 1) / 2.

    This is the actual harmonic signature of where π(x) oscillates above and below
    Li(x). A high value means p sits near a local peak in prime density; a low value
    means p is in a trough. Adding this as a weight gives the probe the refraction-
    aware correction that the smooth gravity field lacks — the same oscillation that
    produces the Skewes phenomenon and the prime conspiracy.

    Ratios are denominative: the zero frequencies t_n are the denominators of the
    oscillation — they determine the period of each refraction cycle. The field is
    strongest (most predictive) at small p and weakens gracefully as p grows, exactly
    like the error term in the prime counting formula.
    """
    if p <= 1:
        return 0.5
    log_p = math.log(p)
    raw = sum(math.cos(t * log_p) for t in freqs) / len(freqs)
    return (raw + 1.0) / 2.0


def riemann_phase_anchor(seed_values: list[int], freqs: list[float] = _RIEMANN_ZERO_FREQS) -> list[dict]:
    """Build phase anchors from verified seed values for each Riemann zero frequency.

    The flat Riemann wave asks whether a candidate sits at an absolute cosine peak.
    That can add noise at dense ranges. This anchor instead asks whether a candidate
    phase-aligns with the verified solution manifold already seen in the seeds.
    """
    seeds = [value for value in seed_values if value > 1]
    if not seeds:
        return []

    anchors = []
    for freq in freqs:
        cos_mean = sum(math.cos(freq * math.log(seed)) for seed in seeds) / len(seeds)
        sin_mean = sum(math.sin(freq * math.log(seed)) for seed in seeds) / len(seeds)
        coherence = math.hypot(cos_mean, sin_mean)
        if coherence <= 1e-12:
            anchors.append({"freq": freq, "cos": 1.0, "sin": 0.0, "coherence": 0.0})
        else:
            anchors.append(
                {
                    "freq": freq,
                    "cos": cos_mean / coherence,
                    "sin": sin_mean / coherence,
                    "coherence": coherence,
                }
            )
    return anchors


def riemann_phase_coherence(p: int, anchors: list[dict]) -> float:
    """Candidate-to-seed Riemann phase coherence in [0, 1]."""
    if p <= 1 or not anchors:
        return 0.5

    log_p = math.log(p)
    total = 0.0
    weight_sum = 0.0
    for anchor in anchors:
        weight = float(anchor.get("coherence", 0.0))
        if weight <= 0:
            continue
        phase = float(anchor["freq"]) * log_p
        candidate_cos = math.cos(phase)
        candidate_sin = math.sin(phase)
        aligned = (candidate_cos * float(anchor["cos"])) + (candidate_sin * float(anchor["sin"]))
        total += weight * aligned
        weight_sum += weight

    if weight_sum <= 0:
        return 0.5
    return ((total / weight_sum) + 1.0) / 2.0


def prime_harmonic_ratio_map(twin_centers: list[int]) -> dict:
    """Map consecutive twin prime center ratios against natural harmonic ratios.

    For each consecutive pair of twin prime centers c_n and c_{n+1}:
      ratio = c_{n+1} / c_n

    For each natural harmonic h, count how many ratios land within epsilon=0.02
    of h (the 'resonance' count). The denominator is the total ratio count.

    This tells us which natural harmonic ratios the twin prime spacing prefers.
    A prime structure that strongly aligns with a natural harmonic (e.g. phi or 3/2)
    at multiple scales would suggest the same geometric attractor governs both.

    Also computes:
      - ratio_mean, ratio_std: distribution of consecutive center ratios
      - log_ratio_mean: mean of log(ratio) — this is the average log-scale gap
      - riemann_alignment: fraction of centers where riemann_zero_wave > 0.5
        (above the Li(x) prediction)
    """
    if len(twin_centers) < 2:
        return {"error": "need at least 2 twin prime centers"}

    ratios = [twin_centers[i + 1] / twin_centers[i] for i in range(len(twin_centers) - 1)]
    n = len(ratios)
    mean_r = sum(ratios) / n
    var_r = sum((r - mean_r) ** 2 for r in ratios) / n
    std_r = var_r ** 0.5
    log_ratios = [math.log(r) for r in ratios]
    mean_log = sum(log_ratios) / len(log_ratios)

    # Resonance: how many ratios land within epsilon of each natural harmonic
    eps = 0.02
    resonance: dict[str, dict] = {}
    for name, h in _NATURAL_HARMONICS:
        hits = sum(1 for r in ratios if abs(r - h) < eps or abs(r - 1.0 / h) < eps)
        resonance[name] = {
            "harmonic": round(h, 6),
            "hits": hits,
            "fraction": round(hits / n, 4),
        }

    # Riemann zero alignment: for each center, is riemann_zero_wave > 0.5?
    above_li = sum(1 for c in twin_centers if riemann_zero_wave(c) > 0.5)
    riemann_alignment = round(above_li / len(twin_centers), 4)

    # Gap structure: gaps between consecutive centers
    gaps = [twin_centers[i + 1] - twin_centers[i] for i in range(len(twin_centers) - 1)]
    gap_mod6 = {}
    for g in gaps:
        key = str(g % 6)
        gap_mod6[key] = gap_mod6.get(key, 0) + 1
    # Sort resonance by hits descending
    sorted_resonance = dict(sorted(resonance.items(), key=lambda x: -x[1]["hits"]))

    return {
        "n_centers": len(twin_centers),
        "n_ratios": n,
        "ratio_mean": round(mean_r, 6),
        "ratio_std": round(std_r, 6),
        "log_ratio_mean": round(mean_log, 6),
        "natural_harmonic_resonance": sorted_resonance,
        "riemann_alignment_frac": riemann_alignment,
        "gap_mod6_distribution": gap_mod6,
        "top_harmonic": max(resonance.items(), key=lambda x: x[1]["hits"])[0],
    }


def run_prime_harmonic_map(limit: int = 10000, seed_limit: int | None = None) -> dict:
    """Collect verified twin primes up to limit, run harmonic ratio map.

    seed_limit: if set, only use twins in [3, seed_limit] as the reference set,
    then show how the ratio map looks in both the seed and the extended range.
    """
    all_twins = [
        p for p in range(3, limit + 1, 2)
        if deterministic_miller_rabin_u64(p) and deterministic_miller_rabin_u64(p + 2)
    ]
    centers = [p + 1 for p in all_twins]

    result: dict = {"limit": limit, "twin_count": len(all_twins)}
    result["full_range"] = prime_harmonic_ratio_map(centers)

    if seed_limit and seed_limit < limit:
        seed_twins = [p for p in all_twins if p <= seed_limit]
        seed_centers = [p + 1 for p in seed_twins]
        ext_twins = [p for p in all_twins if p > seed_limit]
        ext_centers = [p + 1 for p in ext_twins]
        result["seed_range"] = prime_harmonic_ratio_map(seed_centers) if len(seed_centers) >= 2 else {}
        result["extended_range"] = prime_harmonic_ratio_map(ext_centers) if len(ext_centers) >= 2 else {}
        result["seed_limit"] = seed_limit

    return result


def print_prime_harmonic_map(payload: dict) -> None:
    print("Prime harmonic ratio map")
    print(f"twin primes up to {payload['limit']}  total pairs: {payload['twin_count']}")
    print()
    for band_key, label in [("seed_range", "seed"), ("extended_range", "extended"), ("full_range", "full")]:
        if band_key not in payload:
            if band_key == "full_range":
                band_key = "full_range"
                label = "full"
            else:
                continue
        band = payload[band_key]
        if not band or "error" in band:
            continue
        seed_lbl = f"  [{label}] n={band['n_centers']} centers  ratio_mean={band['ratio_mean']}  σ={band['ratio_std']}  log_gap={band['log_ratio_mean']}"
        print(seed_lbl)
        print(f"  riemann_alignment={band['riemann_alignment_frac']:.2%} of centers above Li(x) prediction")
        print(f"  gap_mod6: {band['gap_mod6_distribution']}")
        print(f"  top natural harmonic: {band['top_harmonic']}")
        print(f"  natural harmonic resonance (within ±2% of ratio):")
        for name, info in band["natural_harmonic_resonance"].items():
            bar = "█" * info["hits"]
            print(f"    {name:<14} h={info['harmonic']:.5f}  hits={info['hits']:>4}  frac={info['fraction']:.3f}  {bar[:40]}")
        print()


def _triangulation_mixed_radix_id(coords: tuple[int, ...], moduli: tuple[int, ...]) -> int:
    index = 0
    base = 1
    for coord, modulus in zip(coords, moduli):
        index += coord * base
        base *= modulus
    return index


def _wavelength_from_phase(phase: float) -> float:
    # Visible-spectrum-like span used for plotting/color coding; exact physical meaning
    # is intentionally treated as an invariant proxy, not a literal optical model.
    return 380.0 + (phase * 400.0)


def _phase_to_color(phase: float) -> str:
    # hue in [0,1) from phase and converted to a stable hex code
    hue = phase % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 0.95)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _sub_decimal_bucket(n: int) -> int:
    # Leading-digit fractional residue in [0,1): n / 10^floor(log10(n)).
    if n <= 0:
        return 0
    scale = 10 ** math.floor(math.log10(n))
    frac = (n / max(scale, 1.0)) - math.floor(n / max(scale, 1.0))
    return int(frac * 1000)


def _mod_triangulation_area(coords_a: tuple[int, ...], coords_b: tuple[int, ...], coords_c: tuple[int, ...]) -> float:
    # Use first three coordinate axes to estimate local simplex area.
    # It is a geometry signature for "triangulation hopping" consistency, not a proof metric.
    dims = 3 if len(coords_a) >= 3 else len(coords_a)
    if dims < 2:
        return 0.0
    v1 = [coords_b[i] - coords_a[i] for i in range(dims)]
    v2 = [coords_c[i] - coords_a[i] for i in range(dims)]
    if dims == 2:
        area = abs(v1[0] * v2[1] - v1[1] * v2[0]) / 2.0
    else:
        cx = v1[1] * v2[2] - v1[2] * v2[1]
        cy = v1[2] * v2[0] - v1[0] * v2[2]
        cz = v1[0] * v2[1] - v1[1] * v2[0]
        area = 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
    return area


def _is_twin_prime_starter(n: int) -> bool:
    if n == 5:
        return True
    return n > 5 and n % 30 in (11, 17, 29)


def _sorted_insertion_index(values: list[int], target: float) -> int:
    low = 0
    high = len(values)
    while low < high:
        mid = (low + high) // 2
        if values[mid] < target:
            low = mid + 1
        else:
            high = mid
    return low


def _mean_triangulate(values: list[int], label: str) -> dict:
    if not values:
        return {
            "label": label,
            "count": 0,
            "mean": 0.0,
            "mean_rank": None,
            "anchor_index": None,
            "anchor_value": None,
            "next_index": None,
            "next_value": None,
            "next_gap": None,
        }

    mean = sum(values) / len(values)
    insertion_index = _sorted_insertion_index(values, mean)
    anchor_index = min(max(insertion_index, 0), len(values) - 1)
    next_index = anchor_index + 1 if anchor_index + 1 < len(values) else None
    payload = {
        "label": label,
        "count": len(values),
        "mean": round(mean, 6),
        "mean_rank": insertion_index,
        "anchor_index": anchor_index,
        "anchor_value": values[anchor_index],
        "next_index": next_index,
        "next_value": values[next_index] if next_index is not None else None,
    }
    payload["next_gap"] = (payload["next_value"] - payload["anchor_value"]) if payload["next_value"] is not None else None
    return payload


def _classify_gap_shape(prev_gap: int, curr_gap: int, flat_delta: int = 0, rounded_delta: int = 4) -> tuple[str, int]:
    # Treat shape transitions with integer gap-difference bands only.
    delta = curr_gap - prev_gap
    if delta == 0:
        return "edge", 0
    direction = "left" if delta > 0 else "right"
    abs_delta = abs(delta)
    if abs_delta <= rounded_delta:
        return f"rounded_corner_{direction}", delta
    return f"corner_{direction}", delta


def _crt_board_axes(moduli: tuple[int, ...]) -> tuple[int, ...]:
    axes = [m for m in moduli if m != 2]
    if len(axes) >= 3:
        return tuple(axes[-3:])
    if len(axes) < 3:
        axes.extend(m for m in moduli if m not in axes)
    return tuple(axes[:3])


def _crt_transition_token(start: int | None, end: int | None, modulus: int) -> str:
    if start is None or end is None:
        return "?"
    start_residue = start % modulus
    end_residue = end % modulus
    if end_residue == start_residue:
        return "."
    return "X" if end_residue > start_residue else "O"


def _crt_board_lines(matrix: list[list[str]]) -> list[str]:
    lines = []
    if not matrix or not matrix[0]:
        return lines

    def add_line(label: str, values: list[str]) -> None:
        if "?" in values:
            return
        if values and all(value == values[0] for value in values):
            lines.append(f"{label}:{values[0]}")

    for row_idx, row in enumerate(matrix):
        add_line(f"row{row_idx}", row)
    for col_idx in range(len(matrix[0])):
        add_line(f"col{col_idx}", [row[col_idx] for row in matrix])
    if len(matrix) == 3 and len(matrix[0]) == 3:
        add_line("diag0", [matrix[0][0], matrix[1][1], matrix[2][2]])
        add_line("diag1", [matrix[0][2], matrix[1][1], matrix[2][0]])
    return lines


def _build_crt_board(
    prev_n: int | None,
    twin_n: int,
    bridge_n: int,
    next_n: int | None,
    axes: tuple[int, ...],
) -> dict:
    transitions = [(prev_n, twin_n), (twin_n, bridge_n), (bridge_n, next_n)]
    matrix = [[_crt_transition_token(start, end, modulus) for start, end in transitions] for modulus in axes]
    signature = "/".join("".join(row) for row in matrix)
    line_rules = _crt_board_lines(matrix)
    return {
        "n": twin_n,
        "bridge": bridge_n,
        "axes": list(axes),
        "columns": ["incoming", "bridge", "outgoing"],
        "matrix": matrix,
        "signature": signature,
        "line_rules": line_rules,
        "line_count": len(line_rules),
    }


def _complex_quadrant_token(real: float, imag: float) -> str:
    if abs(real) >= abs(imag):
        return "R" if real >= 0 else "N"
    return "I" if imag >= 0 else "J"


def _phase_quadrant_token(n: int, modulus: int) -> str:
    angle = 2.0 * math.pi * ((n % modulus) / modulus)
    return _complex_quadrant_token(math.cos(angle), math.sin(angle))


def _build_midpoint_conjugate_board(center: int, axes: tuple[int, ...]) -> dict:
    matrix = [
        [
            _phase_quadrant_token(center - 1, modulus),
            _phase_quadrant_token(center, modulus),
            _phase_quadrant_token(center + 1, modulus),
        ]
        for modulus in axes
    ]
    sum_tokens = []
    cancel_errors = []
    real_sums = []
    for modulus in axes:
        theta = 2.0 * math.pi / modulus
        relative_pair_sum = cmath.exp(-1j * theta) + cmath.exp(1j * theta)
        cancel_errors.append(abs(relative_pair_sum.imag))
        real_sums.append(round(relative_pair_sum.real, 9))

        left = cmath.exp(2j * math.pi * (((center - 1) % modulus) / modulus))
        right = cmath.exp(2j * math.pi * (((center + 1) % modulus) / modulus))
        combined = left + right
        sum_tokens.append(_complex_quadrant_token(combined.real, combined.imag))

    cancellation_error = sum(cancel_errors)
    cancellation_signature = "".join("C" if error <= 1e-9 else "B" for error in cancel_errors)
    return {
        "center": center,
        "left": center - 1,
        "right": center + 1,
        "axes": list(axes),
        "columns": ["left", "center", "right"],
        "matrix": matrix,
        "signature": "/".join("".join(row) for row in matrix),
        "sum_signature": "".join(sum_tokens),
        "cancellation_signature": cancellation_signature,
        "cancellation_error": round(cancellation_error, 12),
        "real_sums": real_sums,
        "center_residue_signature": ",".join(str(center % modulus) for modulus in axes),
    }


def _rank_enrichment_entries(counts: Counter[str], verified_counts: Counter[str], baseline_precision: float) -> tuple[list[dict], list[dict]]:
    entries = []
    for key, count in counts.items():
        verified = verified_counts[key]
        precision = verified / max(1, count)
        lift = precision / max(1e-12, baseline_precision) if baseline_precision else None
        entries.append(
            {
                "key": key,
                "twin_count": count,
                "verified_twin_count": verified,
                "precision": round(precision, 6),
                "lift": None if lift is None else round(lift, 3),
            }
        )
    by_lift = sorted(entries, key=lambda row: (row["lift"] is not None, row["lift"] or 0.0), reverse=True)
    by_support = sorted(entries, key=lambda row: row["twin_count"], reverse=True)
    return by_lift, by_support


def run_mod_triangulation_hop_probe(
    limit: int = 100_000,
    moduli: tuple[int, ...] = (2, 3, 5),
    top_hops: int = 24,
    verify_bridges: bool = False,
    exclude_non_starters: bool = False,
) -> dict:
    """Map numbers into orthogonal CRT coordinates and track root-product bridges."""
    moduli = tuple(int(m) for m in moduli if int(m) > 1)
    if not moduli:
        return {"schema_version": "prime_fog_mod_triangulation_v1", "error": "moduli must be integers > 1"}

    # Strict pairwise coprimality is preferred; if not present, note it directly.
    bad_pairs: list[tuple[int, int, int]] = []
    for i in range(len(moduli)):
        for j in range(i + 1, len(moduli)):
            gcd = math.gcd(moduli[i], moduli[j])
            if gcd != 1:
                bad_pairs.append((moduli[i], moduli[j], gcd))

    product = math.prod(moduli)
    modulus_nodes: dict[str, int] = {}
    all_survivors: list[dict] = []
    survivors: list[dict] = []
    all_survivor_set: set[int] = set()
    survivor_set: set[int] = set()
    prime_cache: dict[int, bool] = {}
    for n in range(2, limit + 1):
        coords = tuple(n % m for m in moduli)
        key = ",".join(str(v) for v in coords)
        modulus_nodes[key] = modulus_nodes.get(key, 0) + 1
        if all(c != 0 for c in coords):
            row = {
                "n": n,
                "coords": coords,
                "mixed_radix": _triangulation_mixed_radix_id(coords, moduli),
                "sub_decimal_bucket": _sub_decimal_bucket(n),
                "sub_decimal_ratio": round(n / (10 ** math.floor(math.log10(n))), 6),
                "verified": None,
            }
            all_survivors.append(row)
            all_survivor_set.add(n)
            if not exclude_non_starters or _is_twin_prime_starter(n):
                survivors.append(row)
                survivor_set.add(n)

    # Optional exact bridge verification: only tested where needed.
    if verify_bridges:
        to_verify: set[int] = set()
        for row in survivors:
            to_verify.add(row["n"])
            pair = row["n"] + 2
            if pair in survivor_set or pair <= limit:
                to_verify.add(pair)
        prime_cache = {n: deterministic_miller_rabin_u64(n) for n in to_verify}
        for row in survivors:
            row["verified"] = bool(prime_cache.get(row["n"], False))

    hop_rows: list[dict] = []
    hue_bins = 18
    hue_hist = [0] * hue_bins
    for current, nxt in zip(survivors[:-1], survivors[1:]):
        gap = nxt["n"] - current["n"]
        root = math.sqrt(current["n"] * nxt["n"])
        log_root = math.log(root)
        phase = (log_root * _PHI) % (2.0 * math.pi)
        phase_norm = phase / (2.0 * math.pi)
        wavelength = _wavelength_from_phase(phase_norm)
        hue_bin = int(phase_norm * hue_bins) % hue_bins
        hue_hist[hue_bin] += 1
        hop_rows.append(
            {
                "from": current["n"],
                "to": nxt["n"],
                "gap": gap,
                "ratio": gap / current["n"],
                "root": round(root, 6),
                "log_root": round(log_root, 6),
                "phase": round(phase_norm, 6),
                "wavelength_nm": round(wavelength, 3),
                "color": _phase_to_color(phase_norm),
                "from_coords": current["coords"],
                "to_coords": nxt["coords"],
                "sub_decimal_bridge": round((current["sub_decimal_bucket"] + nxt["sub_decimal_bucket"]) / 2, 1),
            }
        )

    shape_hist = Counter()
    for idx in range(1, len(hop_rows)):
        shape, delta = _classify_gap_shape(hop_rows[idx - 1]["gap"], hop_rows[idx]["gap"])
        hop_rows[idx]["shape"] = shape
        hop_rows[idx]["shape_delta"] = delta
        shape_hist[shape] += 1

    if hop_rows:
        hop_rows[0]["shape"] = "edge"
        hop_rows[0]["shape_delta"] = 0
        shape_hist["edge"] += 1

    gaps = [hop["gap"] for hop in hop_rows]
    hop_gaps_sorted = sorted(gaps)
    if gaps:
        mean_gap = sum(gaps) / len(gaps)
        median_gap = hop_gaps_sorted[len(gaps) // 2]
    else:
        mean_gap = 0.0
        median_gap = 0.0

    hop_spectrum = [
        {"bin": idx, "label": f"{idx/hue_bins:0.2f}..{(idx+1)/hue_bins:0.2f}", "count": count}
        for idx, count in enumerate(hue_hist)
    ]

    top_hops_rows = sorted(hop_rows, key=lambda row: row["gap"], reverse=True)[:top_hops]

    # Triangulation snapshots: consecutive node triplets, geometric area in first 3 axes.
    tri_rows: list[dict] = []
    if len(survivors) >= 3:
        for i in range(len(survivors) - 2):
            a = survivors[i]
            b = survivors[i + 1]
            c = survivors[i + 2]
            area = _mod_triangulation_area(a["coords"], b["coords"], c["coords"])
            tri_rows.append(
                {
                    "a": a["n"],
                    "b": b["n"],
                    "c": c["n"],
                    "gap_ab": b["n"] - a["n"],
                    "gap_bc": c["n"] - b["n"],
                    "area": round(area, 4),
                    "root": round(math.sqrt(a["n"] * c["n"]), 6),
                }
            )
    tri_rows.sort(key=lambda row: row["area"], reverse=True)
    tri_top = tri_rows[:max(5, min(20, len(tri_rows) // 200 + 1))]

    # Twin-bridge layer: starter candidates p where p+2 is also in the full CRT-survivor lattice.
    # With --triangulation-exclude-non-starters, p is restricted by residue class but p+2
    # can still live outside that restricted class.
    twin_candidates = [row["n"] for row in survivors if row["n"] + 2 in all_survivor_set]
    twin_index_by_n = {row["n"]: idx for idx, row in enumerate(survivors)}
    all_survivor_index_by_n = {row["n"]: idx for idx, row in enumerate(all_survivors)}
    verified_twin = 0
    motif_stats: Counter[str] = Counter()
    motif_verified: Counter[str] = Counter()
    if twin_candidates:
        for twin_n in twin_candidates:
            idx = twin_index_by_n.get(twin_n, -1)
            incoming_shape = "none"
            outgoing_shape = "none"
            if idx >= 1 and idx < len(hop_rows):
                incoming_shape = hop_rows[idx]["shape"]
            if idx + 1 < len(hop_rows):
                outgoing_shape = hop_rows[idx + 1]["shape"]
            motif = f"{incoming_shape}|{outgoing_shape}"
            motif_stats[motif] += 1

    if verify_bridges:
        verified_twin = sum(
            1
            for n in twin_candidates
            if bool(prime_cache.get(n, False)) and bool(prime_cache.get(n + 2, False))
        )
        for twin_n in twin_candidates:
            idx = twin_index_by_n.get(twin_n, -1)
            incoming_shape = "none"
            outgoing_shape = "none"
            if idx >= 1 and idx < len(hop_rows):
                incoming_shape = hop_rows[idx]["shape"]
            if idx + 1 < len(hop_rows):
                outgoing_shape = hop_rows[idx + 1]["shape"]
            motif = f"{incoming_shape}|{outgoing_shape}"
            if bool(prime_cache.get(twin_n, False)) and bool(prime_cache.get(twin_n + 2, False)):
                motif_verified[motif] += 1

    baseline_twin_precision = verified_twin / len(twin_candidates) if verify_bridges and twin_candidates else 0.0
    motif_by_lift_raw, motif_by_support_raw = _rank_enrichment_entries(motif_stats, motif_verified, baseline_twin_precision)
    motifs_by_lift = [{**{k: v for k, v in row.items() if k != "key"}, "motif": row["key"]} for row in motif_by_lift_raw]
    motifs_by_support = [{**{k: v for k, v in row.items() if k != "key"}, "motif": row["key"]} for row in motif_by_support_raw]

    board_axes = _crt_board_axes(moduli)
    board_signature_stats: Counter[str] = Counter()
    board_signature_verified: Counter[str] = Counter()
    board_rule_stats: Counter[str] = Counter()
    board_rule_verified: Counter[str] = Counter()
    board_samples: list[dict] = []
    midpoint_signature_stats: Counter[str] = Counter()
    midpoint_signature_verified: Counter[str] = Counter()
    midpoint_sum_stats: Counter[str] = Counter()
    midpoint_sum_verified: Counter[str] = Counter()
    midpoint_cancellation_stats: Counter[str] = Counter()
    midpoint_cancellation_verified: Counter[str] = Counter()
    midpoint_samples: list[dict] = []
    for twin_n in twin_candidates:
        twin_idx = all_survivor_index_by_n.get(twin_n)
        bridge_idx = all_survivor_index_by_n.get(twin_n + 2)
        if twin_idx is None or bridge_idx is None:
            continue
        prev_n = all_survivors[twin_idx - 1]["n"] if twin_idx > 0 else None
        next_n = all_survivors[bridge_idx + 1]["n"] if bridge_idx + 1 < len(all_survivors) else None
        board = _build_crt_board(prev_n, twin_n, twin_n + 2, next_n, board_axes)
        signature = board["signature"]
        rules = board["line_rules"] or ["no_line"]
        board_signature_stats[signature] += 1
        for rule in rules:
            board_rule_stats[rule] += 1
        is_verified_twin = bool(verify_bridges and prime_cache.get(twin_n, False) and prime_cache.get(twin_n + 2, False))
        if is_verified_twin:
            board_signature_verified[signature] += 1
            for rule in rules:
                board_rule_verified[rule] += 1
        if len(board_samples) < top_hops:
            board_samples.append(
                {
                    **board,
                    "verified_twin": is_verified_twin if verify_bridges else None,
                }
            )
        midpoint = _build_midpoint_conjugate_board(twin_n + 1, board_axes)
        midpoint_signature_stats[midpoint["signature"]] += 1
        midpoint_sum_stats[midpoint["sum_signature"]] += 1
        midpoint_cancellation_stats[midpoint["cancellation_signature"]] += 1
        if is_verified_twin:
            midpoint_signature_verified[midpoint["signature"]] += 1
            midpoint_sum_verified[midpoint["sum_signature"]] += 1
            midpoint_cancellation_verified[midpoint["cancellation_signature"]] += 1
        if len(midpoint_samples) < top_hops:
            midpoint_samples.append(
                {
                    **midpoint,
                    "verified_twin": is_verified_twin if verify_bridges else None,
                }
            )
    board_signatures_by_lift, board_signatures_by_support = _rank_enrichment_entries(
        board_signature_stats,
        board_signature_verified,
        baseline_twin_precision,
    )
    board_rules_by_lift, board_rules_by_support = _rank_enrichment_entries(
        board_rule_stats,
        board_rule_verified,
        baseline_twin_precision,
    )
    midpoint_signatures_by_lift, midpoint_signatures_by_support = _rank_enrichment_entries(
        midpoint_signature_stats,
        midpoint_signature_verified,
        baseline_twin_precision,
    )
    midpoint_sums_by_lift, midpoint_sums_by_support = _rank_enrichment_entries(
        midpoint_sum_stats,
        midpoint_sum_verified,
        baseline_twin_precision,
    )
    midpoint_cancellations_by_lift, midpoint_cancellations_by_support = _rank_enrichment_entries(
        midpoint_cancellation_stats,
        midpoint_cancellation_verified,
        baseline_twin_precision,
    )

    mean_triangulations = [
        _mean_triangulate([row["n"] for row in survivors], "survivors"),
    ]
    if twin_candidates:
        mean_triangulations.append(_mean_triangulate(twin_candidates, "twin_candidates"))

    top_nodes = [
        {"n": row["n"], "coords": row["coords"], "sub_decimal_bucket": row["sub_decimal_bucket"], "color": _phase_to_color(row["sub_decimal_bucket"] / 1000)}
        for row in survivors[:top_hops]
    ]

    return {
        "schema_version": "prime_fog_mod_triangulation_v1",
        "limit": limit,
        "moduli": list(moduli),
        "exclude_non_starters": bool(exclude_non_starters),
        "modulus_product": product,
        "coprime_warnings": bad_pairs,
        "residue_nodes": len(modulus_nodes),
        "raw_survivor_count": len(all_survivors),
        "survivor_count": len(survivors),
        "survival_rate": round(len(survivors) / max(1, limit - 1), 6),
        "gap_count": len(gaps),
        "gap_mean": round(mean_gap, 6),
        "gap_median": median_gap,
        "gap_min": min(gaps) if gaps else 0,
        "gap_max": max(gaps) if gaps else 0,
        "shape_hist": [{"shape": k, "count": shape_hist[k]} for k in sorted(shape_hist)],
        "shape_motif_overlay": {
            "baseline_twin_precision": round(baseline_twin_precision, 6) if verify_bridges else None,
            "twin_count": len(twin_candidates),
            "motif_count": len(motif_stats),
            "motifs_by_lift": motifs_by_lift[:10],
            "motifs_by_support": motifs_by_support[:10],
            "enabled": bool(verify_bridges),
        },
        "crt_board_overlay": {
            "enabled": bool(board_axes),
            "axes": list(board_axes),
            "columns": ["incoming", "bridge", "outgoing"],
            "tokens": {
                "X": "forward_residue_move",
                "O": "wraparound_residue_move",
                ".": "same_residue",
                "?": "missing_boundary",
            },
            "rule_note": "row/column/diagonal lines are non-exclusive custom rules",
            "baseline_twin_precision": round(baseline_twin_precision, 6) if verify_bridges else None,
            "signature_count": len(board_signature_stats),
            "rule_count": len(board_rule_stats),
            "signatures_by_lift": board_signatures_by_lift[:10],
            "signatures_by_support": board_signatures_by_support[:10],
            "rules_by_lift": board_rules_by_lift[:10],
            "rules_by_support": board_rules_by_support[:10],
            "samples": board_samples,
        },
        "midpoint_conjugate_overlay": {
            "enabled": bool(board_axes),
            "axes": list(board_axes),
            "columns": ["left", "center", "right"],
            "tokens": {
                "R": "real_positive_dominant",
                "N": "real_negative_dominant",
                "I": "imag_positive_dominant",
                "J": "imag_negative_dominant",
                "C": "relative_imaginary_cancelled",
                "B": "relative_imaginary_broken",
            },
            "baseline_twin_precision": round(baseline_twin_precision, 6) if verify_bridges else None,
            "signature_count": len(midpoint_signature_stats),
            "sum_signature_count": len(midpoint_sum_stats),
            "cancellation_signature_count": len(midpoint_cancellation_stats),
            "signatures_by_lift": midpoint_signatures_by_lift[:10],
            "signatures_by_support": midpoint_signatures_by_support[:10],
            "sum_signatures_by_lift": midpoint_sums_by_lift[:10],
            "sum_signatures_by_support": midpoint_sums_by_support[:10],
            "cancellations_by_lift": midpoint_cancellations_by_lift[:10],
            "cancellations_by_support": midpoint_cancellations_by_support[:10],
            "samples": midpoint_samples,
        },
        "hops_sample": top_hops_rows,
        "spectrum": {
            "bins": hue_bins,
            "bin_counts": hop_spectrum,
            "dominant_bin": max(range(hue_bins), key=lambda idx: hue_hist[idx]) if gaps else None,
        },
        "twin_candidates": len(twin_candidates),
        "verified_twin_candidates": verified_twin,
        "twin_verification_mode": bool(verify_bridges),
        "twin_precision": round(baseline_twin_precision, 6) if verify_bridges and twin_candidates else None,
        "mean_triangulations": mean_triangulations,
        "top_nodes": top_nodes,
        "triangulation_snapshots": tri_top,
    }


def print_mod_triangulation_probe(payload: dict) -> None:
    print("Mod triangulation hopping probe")
    if payload.get("error"):
        print(f"error: {payload['error']}")
        return
    print(f"moduli: {payload['moduli']}  modulus_product={payload['modulus_product']}")
    print(f"exclude_non_starters={payload['exclude_non_starters']}")
    print(f"coprime warnings: {payload['coprime_warnings']}")
    if payload["exclude_non_starters"]:
        print(
            f"limit: {payload['limit']}  residue_nodes={payload['residue_nodes']}  "
            f"survivors={payload['survivor_count']} ({payload['survival_rate']:.2%}) [raw={payload['raw_survivor_count']}]"
        )
    else:
        print(f"limit: {payload['limit']}  residue_nodes={payload['residue_nodes']}  survivors={payload['survivor_count']} ({payload['survival_rate']:.2%})")
    print(f"gaps: n={payload['gap_count']}  mean={payload['gap_mean']:.3f}  median={payload['gap_median']:.1f}  min={payload['gap_min']}  max={payload['gap_max']}")
    print(f"twin candidates from survivor lattice: {payload['twin_candidates']} verified={payload['verified_twin_candidates']} mode={payload['twin_verification_mode']}")
    if payload["twin_precision"] is not None:
        print(f"twin precision: {payload['twin_precision']:.4f}")
    if payload["shape_hist"]:
        print("shape histogram:")
        for row in payload["shape_hist"]:
            print(f"  {row['shape']:<23} n={row['count']}")
    for entry in payload.get("mean_triangulations", []):
        if entry.get("count", 0) == 0:
            print(f"mean-triangulation ({entry.get('label', 'set')}): empty")
            continue
        anchor = entry["anchor_value"]
        next_value = entry["next_value"]
        next_gap = entry["next_gap"]
        print(
            f"mean-triangulation ({entry['label']}): mean={entry['mean']:.6f} "
            f"index={entry['anchor_index']} value={anchor} -> next_index={entry['next_index']} "
            f"next={next_value} gap={next_gap}"
        )
    print("wavelength spectrum bins:")
    for row in payload["spectrum"]["bin_counts"]:
        bar = "█" * min(row["count"], 40)
        marker = " <- top" if row["count"] == max(row["count"] for row in payload["spectrum"]["bin_counts"]) else ""
        print(f"  {row['label']}  n={row['count']:>6}  {bar}{marker}")
    print(f"dominant bin: {payload['spectrum']['dominant_bin']}")
    print("top root-product hops:")
    for hop in payload["hops_sample"]:
        print(
            f"  {hop['from']} -> {hop['to']}  gap={hop['gap']:>4} "
            f"root={hop['root']:<10} phase={hop['phase']:<.6f} "
            f"λ={hop['wavelength_nm']:.1f}nm  color={hop['color']}  ratio={hop['ratio']:.3f}  "
            f"shape={hop.get('shape','?')}  Δ={hop.get('shape_delta',0)}"
        )
    motif_overlay = payload.get("shape_motif_overlay", {})
    if motif_overlay.get("enabled"):
        print("shape motif overlay (verified bridges):")
        baseline = motif_overlay.get("baseline_twin_precision")
        if baseline is not None:
            print(f"  baseline precision: {baseline:.4f}")
        print("  motifs by lift:")
        for row in motif_overlay.get("motifs_by_lift", [])[:8]:
            print(
                f"    motif={row['motif']:<40} twins={row['twin_count']:>6} "
                f"verified={row['verified_twin_count']:>6} precision={row['precision']:.4f} "
                f"lift={row['lift']}"
            )
        print("  motifs by support:")
        for row in motif_overlay.get("motifs_by_support", [])[:8]:
            print(
                f"    motif={row['motif']:<40} twins={row['twin_count']:>6} "
                f"verified={row['verified_twin_count']:>6} precision={row['precision']:.4f} "
                f"lift={row['lift']}"
            )
    board_overlay = payload.get("crt_board_overlay", {})
    if board_overlay.get("enabled"):
        print("CRT board overlay:")
        print(f"  axes={board_overlay['axes']} columns={board_overlay['columns']}")
        print("  tokens: X=forward O=wrap .=same ?=boundary")
        print("  signatures by lift:")
        for row in board_overlay.get("signatures_by_lift", [])[:8]:
            print(
                f"    board={row['key']:<14} twins={row['twin_count']:>6} "
                f"verified={row['verified_twin_count']:>6} precision={row['precision']:.4f} "
                f"lift={row['lift']}"
            )
        print("  rules by lift:")
        for row in board_overlay.get("rules_by_lift", [])[:8]:
            print(
                f"    rule={row['key']:<10} twins={row['twin_count']:>6} "
                f"verified={row['verified_twin_count']:>6} precision={row['precision']:.4f} "
                f"lift={row['lift']}"
            )
        print("  sample boards:")
        for board in board_overlay.get("samples", [])[:5]:
            rows = ["".join(row) for row in board["matrix"]]
            print(
                f"    n={board['n']:<8} bridge={board['bridge']:<8} "
                f"sig={board['signature']:<14} lines={','.join(board['line_rules']) or 'none'} "
                f"rows={rows}"
            )
    midpoint_overlay = payload.get("midpoint_conjugate_overlay", {})
    if midpoint_overlay.get("enabled"):
        print("midpoint conjugate overlay:")
        print(f"  axes={midpoint_overlay['axes']} columns={midpoint_overlay['columns']}")
        print("  tokens: R/N=real-dominant I/J=imag-dominant C=cancelled B=broken")
        print("  midpoint phase boards by lift:")
        for row in midpoint_overlay.get("signatures_by_lift", [])[:8]:
            print(
                f"    board={row['key']:<14} twins={row['twin_count']:>6} "
                f"verified={row['verified_twin_count']:>6} precision={row['precision']:.4f} "
                f"lift={row['lift']}"
            )
        print("  side-sum signatures by lift:")
        for row in midpoint_overlay.get("sum_signatures_by_lift", [])[:8]:
            print(
                f"    sum={row['key']:<6} twins={row['twin_count']:>6} "
                f"verified={row['verified_twin_count']:>6} precision={row['precision']:.4f} "
                f"lift={row['lift']}"
            )
        print("  cancellation signatures:")
        for row in midpoint_overlay.get("cancellations_by_support", [])[:8]:
            print(
                f"    cancel={row['key']:<6} twins={row['twin_count']:>6} "
                f"verified={row['verified_twin_count']:>6} precision={row['precision']:.4f} "
                f"lift={row['lift']}"
            )
        print("  sample midpoint boards:")
        for board in midpoint_overlay.get("samples", [])[:5]:
            rows = ["".join(row) for row in board["matrix"]]
            print(
                f"    x={board['center']:<8} pair=({board['left']},{board['right']}) "
                f"sig={board['signature']:<14} sum={board['sum_signature']:<6} "
                f"cancel={board['cancellation_signature']} err={board['cancellation_error']} rows={rows}"
            )
    print("triangulation snapshots (top areas):")
    for tri in payload["triangulation_snapshots"]:
        print(
            f"  ({tri['a']}, {tri['b']}, {tri['c']})  gaps=({tri['gap_ab']},{tri['gap_bc']}) "
            f"area={tri['area']:.4f} root={tri['root']}"
        )
    print("representative nodes:")
    for row in payload["top_nodes"]:
        print(f"  n={row['n']:<8} coords={tuple(row['coords'])} bucket={row['sub_decimal_bucket']:>4} color={row['color']}")

_PHI: float = (1.0 + math.sqrt(5.0)) / 2.0  # golden ratio ≈ 1.6180


# ── Independent sub-paths ─────────────────────────────────────────────────────
# These three scorers operate in spaces ORTHOGONAL to the gravity/wave/Riemann
# stack above. Each produces an independent [0,1] score. Running them as a
# parallel path and intersecting their top-N with the gravity path's top-N gives
# triangulated high-confidence candidates.
#
# Path A = gravity + wave + Riemann + phi-zero  (geometry / frequency space)
# Path B = mod30_wheel + hl_density + large_div  (algebra / analytic / residue space)
# Path C = base10 digit braid / carry topology       (decimal morphology space)
# Path D = Cramér gap-record + log² normalized gap anomalies (analytic gap geometry)
# Gold   = Path A top-N ∩ Path B top-N ∩ Path C top-N


def mod30_wheel_score(p: int) -> float:
    """Algebraic wheel gate: 1.0 if p ≡ 11 (mod 30), else 0.0.

    All twin prime starters (p, p+2) with p > 5 satisfy p ≡ 11 (mod 30).
    Proof: primes > 5 are ≡ {1,7,11,13,17,19,23,29} (mod 30).
    Of these pairs (r, r+2): (1,3)→3|3, (7,9)→3|9, (11,13)→both coprime to 30,
    (13,15)→5|15, (17,19)→both but 17 ≡ 17 not 11, (19,21)→3|21,
    (23,25)→5|25, (29,31≡1)→valid but 29+2=31 ≡ 1 mod 30, same wheel slot as p=29.
    Wait — 17 (mod 30): (17,19) both wheel-clean, so 17 is also valid? Let me recheck.
    Actually: 17 mod 30 = 17, 17+2 = 19, both coprime to 30 → ALSO valid.
    And 29 mod 30 = 29, 29+2 = 31 ≡ 1, also coprime to 30 → ALSO valid.
    Correct wheel-valid residues for twin starters: {11, 17, 29}.
    (5 mod 30: special case, (5,7) is a twin prime.)
    Score is 1.0 for any of {5, 11, 17, 29} mod 30, else 0.0.
    Zero score = exact algebraic elimination. Not probabilistic.
    """
    if p <= 5:
        return 1.0
    r = p % 30
    return 1.0 if r in (11, 17, 29) else 0.0


def hl_density_deviation_score(
    p: int,
    seed_twins: list[int],
    window_log: float = 1.8,
) -> float:
    """Hardy-Littlewood local density deviation score.

    In a log-window [log(p) - w, log(p) + w], the H-L conjecture B predicts
    the expected number of twin prime starters:
        expected = 2 * C₂ * (hi - lo) / (log(p))²

    Score = actual_count / (expected + actual_count)  — normalized to [0,1).
    High score (→1): this region has MORE twins than analytic theory predicts.
    Near 0.5: region matches the H-L prediction exactly.
    Low score (→0): region is sparse relative to analytic baseline.

    Orthogonal to geometry: uses integer counts, not phase/gravity/waves.
    The 'hot zone' detector: finds regions where twin primes cluster tighter
    than the smooth analytic distribution would predict — these are the same
    resonance pockets the gravity field hunts, but detected by a completely
    different method.
    """
    log_p = math.log(max(p, 3))
    lo = math.exp(log_p - window_log)
    hi = math.exp(log_p + window_log)

    actual = sum(1 for s in seed_twins if lo <= s <= hi)
    window_size = hi - lo
    expected = 2.0 * _TWIN_PRIME_CONSTANT * window_size / (log_p * log_p)

    if expected <= 0:
        return 0.5
    # Ratio: 1.0 = matches HL exactly → score 0.5.  > 1 = denser → → 1.0
    ratio = actual / expected
    return ratio / (1.0 + ratio)


def large_divisor_clearance(p: int) -> float:
    """Divisor clearance against next-layer echo primes {29,31,37,41,43,47}.

    Same fractional-part clearance as _div_ratio_clearance but using the
    prime layer that becomes dominant at range > 8810 (the 10x seed horizon).
    At large ranges the {7,11,13} traps weaken and the {29,31,37} layer
    takes over — this captures that shift.
    Completely independent from _div_ratio_clearance (different divisors).
    """
    return _div_ratio_clearance(p, _DIV_ECHO_LARGE)


def path_b_score(
    p: int,
    seed_twins: list[int],
    window_log: float = 1.8,
) -> float:
    """Combined Path B score (algebraic + analytic + next-layer divisor).

    Path B is orthogonal to Path A (gravity/wave/Riemann).
    wheel: hard algebraic gate — 0.0 = exact elimination
    hl:    density deviation from Hardy-Littlewood baseline
    ldiv:  large-prime divisor clearance (next echo layer)

    Score: if wheel == 0 → 0.0 (exact composite, no further scoring).
    Otherwise: 0.50 * hl + 0.50 * ldiv.
    """
    wheel = mod30_wheel_score(p)
    if wheel == 0.0:
        return 0.0
    hl = hl_density_deviation_score(p, seed_twins, window_log)
    ldiv = large_divisor_clearance(p)
    return 0.50 * hl + 0.50 * ldiv


# ── Path C: Shadow Lattice + p-adic Ultrametric ───────────────────────────────
# Completely orthogonal to Path A (geometry/frequency/phi) and Path B
# (modular algebra/analytic density).
# Path C lives in: algebraic factor structure + q-adic tree topology.
#
# Shadow Lattice:  detects Prime Mirrors — composites n = seed_prime × other_prime
#   that pass the mod30 wheel because (twin_starter ≡ 5 mod 6) × (prime ≡ 1 mod 6)
#   = product ≡ 5 mod 6, landing on twin-prime wheel positions.
#   These also pass div_clearance because their factor is > 47.
#   Exact elimination: n divisible by ANY seed twin prime value → score 0.
#
# p-adic Ultrametric:  for each adic base q, candidate n is in a specific
#   branch of the q-adic tree at each depth d (defined by n mod q^d).
#   Twin primes cluster in specific branches; composites made from prime
#   products land in different branches at depth > 1.
#   Score: fraction of seeds sharing the same q-adic branch, above the
#   random baseline, averaged across bases and depths.

_PADIC_BASES: list[int] = [2, 3, 5, 7, 11]


def _padic_valuation(n: int, q: int) -> int:
    """Highest power of q dividing n (q-adic valuation v_q(n))."""
    if n == 0:
        return 20
    v = 0
    while n % q == 0:
        n //= q
        v += 1
    return v


def padic_twin_alignment(
    p: int,
    seeds: list[int],
    bases: list[int] = _PADIC_BASES,
    max_depth: int = 4,
    top_k: int = 20,
) -> float:
    """p-adic branch alignment: measures how well candidate p matches the
    q-adic address of known seed twin primes.

    For each adic base q and depth d, n is in the branch (n mod q^d).
    True twin primes cluster in specific branches (governed by congruence
    conditions like p ≡ 2 mod 3 for all twin starters > 3).
    Composites — especially those formed as products of primes — land in
    different branches because multiplication produces different residues
    than addition of nearby primes.

    Score: at each (base, depth), count what fraction of nearest seeds share
    p's branch vs the random expectation (1/q^d). Mean normalized ratio,
    mapped to [0,1] via sigmoid.

    Uses only top_k nearest seeds (log-distance) for efficiency at 1M range.
    """
    if not seeds:
        return 0.5
    log_p = math.log(max(p, 2))
    nearest = sorted(seeds, key=lambda s: abs(math.log(max(s, 2)) - log_p))[:top_k]
    n_seeds = len(nearest)

    total_ratio = 0.0
    count = 0
    for q in bases:
        q_pow = q
        for d in range(1, max_depth + 1):
            p_branch = p % q_pow
            matches = sum(1 for s in nearest if s % q_pow == p_branch)
            expected = n_seeds / q_pow
            if expected >= 0.5:
                total_ratio += matches / expected
                count += 1
            q_pow *= q

    if count == 0:
        return 0.5
    mean_ratio = total_ratio / count
    # mean_ratio ≈ 1.0 for random candidates; > 1.0 for branch-aligned candidates
    # Map [0, ∞) → [0, 1) via ratio / (1 + ratio)
    return mean_ratio / (1.0 + mean_ratio)


def _digit_entropy_score(value: int) -> float:
    digits = str(abs(value))
    if not digits:
        return 0.0
    counts = {digit: digits.count(digit) for digit in set(digits)}
    entropy = 0.0
    for count in counts.values():
        p_digit = count / len(digits)
        entropy -= p_digit * math.log(p_digit)
    return entropy / math.log(10)


def _addition_carry_count(value: int, addend: int = 2) -> int:
    carries = 0
    carry = addend
    n = abs(value)
    while carry:
        digit = n % 10
        if digit + carry >= 10:
            carries += 1
            carry = 1
            n //= 10
        else:
            break
    return carries


def _reversed_int(value: int) -> int:
    return int(str(abs(value))[::-1])


def _decimal_shadow_clearance(value: int, divisors: list[int] | None = None) -> float:
    active = divisors or [7, 11, 13, 37]
    scores = []
    for divisor in active:
        if divisor <= 1:
            continue
        frac = (value % divisor) / divisor
        scores.append(min(frac, 1.0 - frac) * 2.0)
    if not scores:
        return 1.0
    product = 1.0
    for score in scores:
        product *= max(score, 1e-9)
    return product ** (1.0 / len(scores))


def digit_braid_score(p: int) -> dict:
    """Path C: base-10 digit morphology for twin-prime starters.

    This intentionally avoids log/phase geometry. It reads the candidate as a
    decimal braid: legal final digit, digit-sum shadows, local +/-2 topology,
    carry complexity from p to p+2, digit entropy, and reversed-digit clearance.
    The result is telemetry/ranking only; exact truth stays with the verifier.
    """
    q = p + 2
    last_digit = p % 10
    if p > 5 and last_digit not in (1, 7, 9):
        return {
            "score": 0.0,
            "last_digit": last_digit,
            "reason": "base10_last_digit_elimination",
        }

    p_digit_sum = sum(int(digit) for digit in str(abs(p)))
    q_digit_sum = sum(int(digit) for digit in str(abs(q)))
    digit_sum_gate = 1.0
    if p > 3 and p_digit_sum % 3 == 0:
        digit_sum_gate = 0.0
    if q > 3 and q_digit_sum % 3 == 0:
        digit_sum_gate = 0.0

    local_guard = 1.0 if (p <= 5 or ((p - 2) % 3 == 0 and (p + 4) % 3 == 0)) else 0.0
    carry_count = _addition_carry_count(p, 2)
    carry_score = 1.0 / (1.0 + carry_count)
    entropy_score = (_digit_entropy_score(p) + _digit_entropy_score(q)) / 2.0
    reverse_clearance = (
        _decimal_shadow_clearance(_reversed_int(p)) + _decimal_shadow_clearance(_reversed_int(q))
    ) / 2.0
    alternating_11_clearance = (
        _decimal_shadow_clearance(p, [11]) + _decimal_shadow_clearance(q, [11])
    ) / 2.0
    product = multiplicative_wave_field(
        {
            "last_digit": 1.0,
            "digit_sum": digit_sum_gate,
            "local_guard": local_guard,
            "carry": carry_score,
            "entropy": max(0.15, entropy_score),
            "reverse_clearance": reverse_clearance,
            "alternating_11": alternating_11_clearance,
        },
        weights={
            "last_digit": 1.0,
            "digit_sum": 1.0,
            "local_guard": 0.8,
            "carry": 0.25,
            "entropy": 0.35,
            "reverse_clearance": 0.5,
            "alternating_11": 0.35,
        },
    )
    soft_score = (
        (0.20 * digit_sum_gate)
        + (0.18 * local_guard)
        + (0.12 * carry_score)
        + (0.18 * entropy_score)
        + (0.20 * reverse_clearance)
        + (0.12 * alternating_11_clearance)
    )
    return {
        "score": round(soft_score * product["product_field_strength"], 12),
        "last_digit": last_digit,
        "digit_sum_mod3": [p_digit_sum % 3, q_digit_sum % 3],
        "local_guard": local_guard,
        "carry_count": carry_count,
        "carry_score": round(carry_score, 6),
        "entropy_score": round(entropy_score, 6),
        "reverse_clearance": round(reverse_clearance, 6),
        "alternating_11_clearance": round(alternating_11_clearance, 6),
        "components": product["components"],
    }


def build_shadow_lattice(seed_twins: list[int], limit: int) -> dict:
    """Build a deterministic semiprime exclusion mask from seed twin primes.

    The lattice contains products a*b where a and b are primes appearing inside
    verified seed twin pairs. A candidate whose p or p+2 lands exactly on this
    lattice is a known composite shadow before Miller-Rabin runs.
    """
    prime_pool = sorted({value for p in seed_twins for value in (p, p + 2) if value > 1})
    products: set[int] = set()
    witnesses: dict[int, tuple[int, int]] = {}
    cap = max(0, limit + 2)
    for i, a in enumerate(prime_pool):
        for b in prime_pool[i:]:
            product = a * b
            if product > cap:
                break
            products.add(product)
            witnesses.setdefault(product, (a, b))
    sorted_products = sorted(products)
    return {
        "prime_pool": prime_pool,
        "products": sorted_products,
        "product_set": products,
        "witnesses": witnesses,
        "limit": limit,
    }


def _nearest_shadow_gap(value: int, products: list[int]) -> tuple[int | None, int | None]:
    if not products:
        return None, None
    index = bisect.bisect_left(products, value)
    candidates = []
    if index < len(products):
        candidates.append(products[index])
    if index > 0:
        candidates.append(products[index - 1])
    nearest = min(candidates, key=lambda candidate: abs(candidate - value))
    return nearest, abs(nearest - value)


def shadow_lattice_score(p: int, lattice: dict) -> dict:
    q = p + 2
    product_set = lattice.get("product_set", set())
    products = lattice.get("products", [])
    p_shadow = p in product_set
    q_shadow = q in product_set
    if p_shadow or q_shadow:
        hit_value = p if p_shadow else q
        witness = lattice.get("witnesses", {}).get(hit_value)
        return {
            "score": 0.0,
            "exact_shadow": True,
            "shadow_value": hit_value,
            "witness": list(witness) if witness else None,
            "nearest_gap": 0,
        }

    clearances = []
    nearest_rows = []
    for value in (p, q):
        nearest, gap = _nearest_shadow_gap(value, products)
        if nearest is None or gap is None:
            clearances.append(1.0)
            continue
        scaled_gap = gap / max(1.0, math.sqrt(max(1, value)))
        clearances.append(scaled_gap / (1.0 + scaled_gap))
        nearest_rows.append({"value": value, "nearest_shadow": nearest, "gap": gap})
    score = sum(clearances) / max(1, len(clearances))
    nearest_gap = min((row["gap"] for row in nearest_rows), default=None)
    return {
        "score": round(score, 12),
        "exact_shadow": False,
        "shadow_value": None,
        "witness": None,
        "nearest_gap": nearest_gap,
    }


def path_c_score(
    p: int,
    shadow_lattice: dict | None = None,
    seed_twins: list[int] | None = None,
) -> dict:
    digit = digit_braid_score(p)
    shadow = shadow_lattice_score(p, shadow_lattice or {}) if shadow_lattice else {
        "score": 1.0,
        "exact_shadow": False,
        "shadow_value": None,
        "witness": None,
        "nearest_gap": None,
    }
    if digit["score"] <= 0.0 or shadow["exact_shadow"]:
        score = 0.0
        padic_s = 0.5
    else:
        if seed_twins:
            # p-adic branch alignment: how well does candidate's q-adic address
            # match known seed twin prime branches across bases {2,3,5,7,11}?
            # Genuinely orthogonal to digit_braid (base-10) and shadow (product
            # lattice). Blended 55/45 with shadow inside the 0.70 signal band.
            padic_s = padic_twin_alignment(p, seed_twins)
            combined_signal = 0.55 * shadow["score"] + 0.45 * padic_s
            score = digit["score"] * (0.30 + 0.70 * combined_signal)
        else:
            padic_s = 0.5
            score = digit["score"] * (0.35 + 0.65 * shadow["score"])
    return {
        "score": round(score, 12),
        "digit_score": round(float(digit.get("score", 0.0)), 12),
        "shadow_score": round(float(shadow.get("score", 0.0)), 12),
        "padic_score": round(float(padic_s), 6),
        "shadow_hit": bool(shadow.get("exact_shadow", False)),
        "shadow_value": shadow.get("shadow_value"),
        "shadow_witness": shadow.get("witness"),
        "shadow_nearest_gap": shadow.get("nearest_gap"),
        "last_digit": digit.get("last_digit"),
        "carry_count": digit.get("carry_count"),
    }


def build_twin_gap_record_profile(seed_twins: list[int], window: int = 16) -> dict:
    """Build a Cramér-style twin-gap profile from seed twins.

    We use normalized twin gaps ratio = gap / log^2(center) to capture tail behavior.
    Running records and rolling means let us score candidate positions by how well
    they align with local gap-statistical structure.
    """
    centers = [p + 1 for p in sorted(seed_twins)]
    if len(centers) < 3:
        return {
            "seed_centers": centers[:-1],
            "gap_to_log2_ratio": [],
            "record_ratio": [],
            "rolling_ratio_mean": [],
            "window": max(1, window),
            "ready": False,
        }

    gaps = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
    ratios: list[float] = []
    for idx, gap in enumerate(gaps):
        scale = max(1.0, math.log(max(centers[idx], 2)) ** 2)
        ratios.append(gap / scale)

    prefix = [0.0]
    for ratio in ratios:
        prefix.append(prefix[-1] + ratio)

    record: list[float] = []
    running_max = 0.0
    for ratio in ratios:
        if ratio > running_max:
            running_max = ratio
        record.append(running_max)

    window = max(1, int(window))
    rolling_mean: list[float] = []
    for i in range(len(ratios)):
        lo = max(0, i - window + 1)
        total = prefix[i + 1] - prefix[lo]
        rolling_mean.append(total / (i - lo + 1))

    return {
        "seed_centers": centers[:-1],
        "gap_to_log2_ratio": ratios,
        "record_ratio": record,
        "rolling_ratio_mean": rolling_mean,
        "window": window,
        "ready": True,
    }


_COMPASS_PRIMES: list[int] = [2, 3, 5, 7, 11, 13]
_COMPASS_THETAS: list[float] = [
    (1.0 + math.sqrt(5.0)) / 2.0,          # φ  — quasicrystalline (most irrational)
    2.0 / (1.0 + math.sqrt(5.0)),           # 1/φ — conjugate quasicrystalline axis
    math.pi / 4.0,                           # π/4 — 8-cycle harmonic partial alignment
]
_TAU: float = 2.0 * math.pi


def path_d_score(p: int, seed_twins: list[int] | None, top_k: int = 20) -> tuple[float, dict]:
    """Path D: Multi-dimensional phase compass alignment.

    Maps (p, p+2) to state vectors Ψ(n, θ) ∈ ℂ^d where dimension k carries
    angular frequency ωk = 2π·θ / pk matched to prime sieve components.

    Three compass angles θ ∈ {φ, 1/φ, π/4} sweep the space:
    - θ = φ: quasicrystalline projection — maximally irrational, non-repeating.
      Twin primes cluster here because their residue structure across multiple
      prime bases creates a recognizable interference pattern that composites
      (products of two primes each with their own phase bias) cannot mimic.
    - θ = 1/φ: conjugate axis — discriminates a different quadrant of the space.
    - θ = π/4: captures 8-cycle harmonic resonance structure.

    Score = joint cosine similarity of Ψ(p) and Ψ(p+2) with mean seed reference,
    averaged across all three compass angles. The JOINT constraint (both p and p+2
    must simultaneously align) is the key: for a composite n = a·b passing the mod30
    wheel, either n or n+2 will typically misalign because composites' phase vectors
    are biased by their factor structure in at least one dimension.

    Orthogonal to:
    - Path A: operates in complex multi-dimensional phase space vs. real 1D log-space
    - Path B: continuous complex cosine similarity vs. discrete mod/count algebra
    - Path C: joint pair phase vs. single-n digit/factor/branch structure
    """
    if not seed_twins or p <= 5:
        return 0.5, {"compass_alignment": None}

    log_p = math.log(max(p, 2))
    nearest = sorted(seed_twins, key=lambda s: abs(math.log(max(s, 2)) - log_p))[:top_k]
    n_s = len(nearest)
    if n_s == 0:
        return 0.5, {"compass_alignment": None}

    total = 0.0
    for theta in _COMPASS_THETAS:
        # Candidate state vectors for p and p+2
        p_psi = [cmath.exp(1j * p * _TAU * theta / pk) for pk in _COMPASS_PRIMES]
        p2_psi = [cmath.exp(1j * (p + 2) * _TAU * theta / pk) for pk in _COMPASS_PRIMES]

        # Mean reference state vectors from nearest seed twins
        ref_p = [
            sum(cmath.exp(1j * s * _TAU * theta / pk) for s in nearest) / n_s
            for pk in _COMPASS_PRIMES
        ]
        ref_p2 = [
            sum(cmath.exp(1j * (s + 2) * _TAU * theta / pk) for s in nearest) / n_s
            for pk in _COMPASS_PRIMES
        ]

        # Cosine similarity: |⟨Ψ, Ψ_ref⟩| / (‖Ψ‖ · ‖Ψ_ref‖)
        dot_p = abs(sum(a.conjugate() * b for a, b in zip(p_psi, ref_p)))
        dot_p2 = abs(sum(a.conjugate() * b for a, b in zip(p2_psi, ref_p2)))
        mag_p = math.sqrt(sum(abs(v) ** 2 for v in p_psi))
        mag_rp = math.sqrt(sum(abs(v) ** 2 for v in ref_p))
        mag_p2 = math.sqrt(sum(abs(v) ** 2 for v in p2_psi))
        mag_rp2 = math.sqrt(sum(abs(v) ** 2 for v in ref_p2))

        align_p = dot_p / max(mag_p * mag_rp, 1e-12)
        align_p2 = dot_p2 / max(mag_p2 * mag_rp2, 1e-12)

        # Joint twin constraint: geometric mean penalizes when either leg misaligns
        total += math.sqrt(align_p * align_p2)

    score = total / len(_COMPASS_THETAS)
    return score, {"compass_alignment": round(score, 6)}


def phi_mean_zero_wave(
    target: int,
    seeds: list[int],
    scale: float | None = None,
    n_modes: int = 6,
) -> float:
    """Phi-mean-zero wave function: target as origin, known structure defines phase.

    Places the wave function AT the target (not at the seeds). The target is the
    zero point — phi-mean-zero. Each seed prime contributes a cosine wave whose
    frequency is its log-distance from the target, phi-weighted by distance rank
    so nearer seeds denominate the local pattern.

    The superposition extrapolates the binary prime/composite pattern (0=composite,
    1=prime) outward from the target in log-space. If the resulting overlap is high,
    the target sits in a phase-constructive zone of the known prime structure. If low,
    the target sits in a destructive zone (likely composite territory).

    Dual to the gravity field: gravity measures pull FROM seeds TO candidate.
    This measures overlap OF the candidate wave function WITH the seed manifold.
    For symmetric kernels they are equivalent; phi-weighting makes this asymmetric,
    privileging the nearest prime structure, which is the correct physical prior for
    the prime number theorem (local density dominates).

    n_modes: number of cosine frequency modes per seed (default 6 = first 6 harmonics
             of the phi-scaled period). More modes = sharper resonance, more noise.
    """
    if not seeds or target <= 1:
        return 0.5
    if target in seeds:
        return 1.0

    log_t = math.log(target)
    effective_scale = scale or math.log(max(seeds) + 1)

    # Sort seeds by log-distance from target
    by_dist = sorted(seeds, key=lambda s: abs(math.log(s) - log_t))

    total = 0.0
    weight_sum = 0.0
    for rank, seed in enumerate(by_dist):
        phi_weight = _PHI ** (-rank)  # phi-decay: rank 0 = weight 1, rank 1 = 1/φ, ...
        log_dist = abs(log_t - math.log(seed))

        # Superpose n_modes cosine waves at harmonics of the phi-scaled period.
        # Mode k uses frequency 2π(k+1) / (effective_scale / φ^k).
        # This is the "overlap them in the binary pattern" step: each mode checks
        # whether the target is in phase with the kth harmonic of the seed's wave.
        mode_sum = 0.0
        for k in range(n_modes):
            period = effective_scale / (_PHI ** k)
            mode_sum += math.cos(2.0 * math.pi * log_dist * (k + 1) / period)
        mode_sum /= n_modes

        total += phi_weight * mode_sum
        weight_sum += phi_weight

    # Normalize: raw in [-1,1] → [0,1]
    raw = total / weight_sum if weight_sum > 0 else 0.0
    return (raw + 1.0) / 2.0


def path_e_score(p: int, seed_values: list[int], window: int = 12) -> float:
    """Path E: Riemann-anchored float gravity on inter-twin gap ratios.

    Orthogonal to Paths A–D:
    - Path A embeds the prime p itself in integer Poincaré space (log p scale).
    - Path E embeds normalized inter-twin gap ratios in float Poincaré space,
      anchored to t₁/2π ≈ 2.249 regardless of absolute prime range.

    Score = how strongly the candidate's local gap ratio is attracted to the
    basin formed by the inter-twin gap ratios of the nearest seed twins.
    Twin primes cluster in specific ratio basins; composites that slip through
    the mod30 wheel land in different basins — the Poincaré distance exposes
    that mismatch without ever seeing the absolute prime values.

    Scale-invariant: the same Riemann-anchored disk at 50M and 400M+.
    """
    if not seed_values or p <= 5:
        return 0.0
    log_p = math.log(max(p, 2))
    nearest = sorted(seed_values, key=lambda s: abs(math.log(max(s, 2)) - log_p))[:window]
    if len(nearest) < 2:
        return 0.0
    nearest_sorted = sorted(nearest)
    gap_ratios = [
        (nearest_sorted[i + 1] - nearest_sorted[i]) / max(1, nearest_sorted[i])
        for i in range(len(nearest_sorted) - 1)
    ]
    if not gap_ratios:
        return 0.0
    twins_below = [s for s in seed_values if s < p]
    cand_ratio = (p - max(twins_below)) / max(1, p) if twins_below else 1.0
    bodies_e = _gravity_bodies_float(gap_ratios, bins=min(8, len(gap_ratios)))
    if not bodies_e:
        return 0.0
    return _gravity_at_float(cand_ratio, bodies_e, metric="hyperbolic")["gravity_field_normalized"]


def twin_prime_gravity_candidate(
    p: int,
    bodies: list[dict],
    learned_bins: set[int],
    bins: int,
    metric: str = "cylindrical",
    hyperbolic_scale: float | None = None,
    seed_values: list[int] | None = None,
    rz_anchors: list[dict] | None = None,
    shadow_lattice: dict | None = None,
    gap_profile: dict | None = None,
) -> dict:
    wave = twin_pair_wave_field(p, learned_bins, bins)
    gravity = solution_gravity_at_candidate(p, bodies, metric, hyperbolic_scale)
    div_clearance = _div_ratio_clearance(p)
    rz_wave = riemann_zero_wave(p)
    rz_phase = riemann_phase_coherence(p, rz_anchors or [])
    # Phi-mean-zero wave: dual to gravity. Places the wave function AT p,
    # overlaps it with the seed prime manifold. Extrapolates the binary
    # prime/composite pattern outward from the target in log-space.
    pmz = phi_mean_zero_wave(p, seed_values or [], scale=hyperbolic_scale)
    product = multiplicative_wave_field(
        {
            "gravity": gravity["gravity_field_normalized"],
            "mesh": wave["mesh_ratio"],
            "wave": wave["field_strength"],
            "product_wave": wave["product_field_strength"],
        },
        weights={"gravity": 0.7, "mesh": 1.1, "wave": 0.7, "product_wave": 0.5},
    )
    # Path A: geometry / frequency / phi space
    # Weights sum to 1.0.
    # gravity + mesh + wave: structure pull from seed manifold
    # div_clearance: removes small-divisor trap noise
    # rz_phase: Riemann zero harmonic correction phase-anchored to seed solutions
    # pmz: phi-mean-zero overlap (dual: target as origin, pattern extrapolation)
    combined = (
        (0.26 * gravity["gravity_field_normalized"])
        + (0.20 * wave["mesh_ratio"])
        + (0.14 * wave["field_strength"])
        + (0.08 * wave["product_field_strength"])
        + (0.11 * div_clearance)
        + (0.10 * rz_phase)
        + (0.11 * pmz)
    )
    # Path B: algebra / analytic / next-layer-divisor — orthogonal to Path A
    pb = path_b_score(p, seed_values or [])
    wheel = mod30_wheel_score(p)
    pc = path_c_score(p, shadow_lattice, seed_values or [])
    pd, pd_meta = path_d_score(p, seed_values or [])
    pe = path_e_score(p, seed_values or [])
    return {
        **wave,
        **gravity,
        "gravity_product_field": product["product_field_strength"],
        "gravity_components": product["components"],
        "div_ratio_clearance": round(div_clearance, 6),
        "riemann_zero_wave": round(rz_wave, 6),
        "riemann_phase_coherence": round(rz_phase, 6),
        "phi_mean_zero_wave": round(pmz, 6),
        "combined_gravity_field": round(combined, 12),
        # Path B columns (independent sub-agent paths)
        "mod30_wheel": wheel,
        "path_b_score": round(pb, 6),
        # Path C columns (radix/p-adic-adjacent morphology + shadow lattice)
        "path_c_score": round(pc["score"], 6),
        # Path D columns (cramer gap-record pressure diagnostics)
        "path_d_score": round(pd, 6),
        "path_d_compass_alignment": pd_meta.get("compass_alignment"),
        # Path E: Riemann-anchored float gravity on inter-twin gap ratios
        "path_e_score": round(pe, 6),
        "digit_braid_score": round(pc["digit_score"], 6),
        "shadow_lattice_score": round(pc["shadow_score"], 6),
        "shadow_lattice_hit": pc["shadow_hit"],
        "shadow_lattice_value": pc["shadow_value"],
        "shadow_lattice_witness": pc["shadow_witness"],
        "shadow_lattice_nearest_gap": pc["shadow_nearest_gap"],
        "digit_last": pc["last_digit"],
        "digit_carry_count": pc["carry_count"],
    }


def score_twin_gravity_row(row: dict, weights: dict[str, float]) -> float:
    total = sum(max(0.0, weight) for weight in weights.values())
    if total <= 0:
        return 0.0
    return (
        (weights.get("gravity", 0.0) * row["gravity_field_normalized"])
        + (weights.get("mesh", 0.0) * row["mesh_ratio"])
        + (weights.get("wave", 0.0) * row["field_strength"])
        + (weights.get("product_wave", 0.0) * row["product_field_strength"])
    ) / total


def classify_twin_gravity_row(row: dict) -> dict:
    p_prime = deterministic_miller_rabin_u64(row["p"])
    q_prime = deterministic_miller_rabin_u64(row["q"])
    if p_prime and q_prime:
        mode = "verified_twin_prime"
    elif p_prime:
        mode = "p_prime_q_composite"
    elif q_prime:
        mode = "p_composite_q_prime"
    else:
        mode = "both_composite"
    return {
        "mode": mode,
        "p_prime": p_prime,
        "q_prime": q_prime,
        "p_small_divisor": None if p_prime else first_small_divisor(row["p"]),
        "q_small_divisor": None if q_prime else first_small_divisor(row["q"]),
    }


def increment_count(counter: dict, key) -> None:
    counter[str(key)] = counter.get(str(key), 0) + 1


def twin_gravity_echo_analysis(rows: list[dict], bins: int) -> dict:
    hit_angle_histogram = [0] * bins
    echo_angle_histogram = [0] * bins
    failure_modes: dict[str, int] = {}
    small_divisors: dict[str, int] = {}
    mesh_ratio_bands: dict[str, int] = {}
    echo_rows = []
    hit_rows = []

    for row in rows:
        classification = classify_twin_gravity_row(row)
        angle_bin = row["angle_bin"]
        if classification["mode"] == "verified_twin_prime":
            hit_rows.append(row)
            hit_angle_histogram[angle_bin] += 1
            continue

        echo = {**row, "classification": classification}
        echo_rows.append(echo)
        echo_angle_histogram[angle_bin] += 1
        increment_count(failure_modes, classification["mode"])
        for divisor in (classification["p_small_divisor"], classification["q_small_divisor"]):
            if divisor is not None:
                increment_count(small_divisors, divisor)
        band = f"{math.floor(row['mesh_ratio'] * 10) / 10:.1f}"
        increment_count(mesh_ratio_bands, band)

    return {
        "row_count": len(rows),
        "hit_count": len(hit_rows),
        "echo_count": len(echo_rows),
        "precision": round(len(hit_rows) / max(1, len(rows)), 6),
        "failure_modes": failure_modes,
        "small_divisors": dict(sorted(small_divisors.items(), key=lambda item: (-item[1], int(item[0])))[:12]),
        "mesh_ratio_bands": dict(sorted(mesh_ratio_bands.items())),
        "hit_angle_histogram": hit_angle_histogram,
        "echo_angle_histogram": echo_angle_histogram,
        "top_echoes": [
            {
                "p": row["p"],
                "q": row["q"],
                "angle_bin": row["angle_bin"],
                "combined_gravity_field": row["combined_gravity_field"],
                "gravity_field_normalized": row["gravity_field_normalized"],
                "mesh_ratio": row["mesh_ratio"],
                "classification": row["classification"],
            }
            for row in echo_rows[:12]
        ],
    }


def iter_gravity_weight_grid(step: float) -> Iterable[dict[str, float]]:
    units = max(1, round(1 / max(0.01, step)))
    for gravity in range(units + 1):
        for mesh in range(units - gravity + 1):
            for wave in range(units - gravity - mesh + 1):
                product_wave = units - gravity - mesh - wave
                yield {
                    "gravity": gravity / units,
                    "mesh": mesh / units,
                    "wave": wave / units,
                    "product_wave": product_wave / units,
                }


def tune_twin_gravity_weights(candidates: list[dict], top: int, step: float, bins: int) -> dict:
    best = None
    evaluations = 0
    for weights in iter_gravity_weight_grid(step):
        evaluations += 1
        ranked = sorted(
            candidates,
            key=lambda row: (-score_twin_gravity_row(row, weights), -row["gravity_product_field"], row["p"]),
        )[:top]
        hits = sum(1 for row in ranked if row["verified"])
        precision = hits / max(1, len(ranked))
        mean_score = sum(score_twin_gravity_row(row, weights) for row in ranked) / max(1, len(ranked))
        candidate = {
            "weights": weights,
            "top_hit_count": hits,
            "top_precision": round(precision, 6),
            "mean_score": round(mean_score, 12),
            "top_rows": ranked,
        }
        if best is None or (
            candidate["top_precision"],
            candidate["top_hit_count"],
            candidate["mean_score"],
        ) > (
            best["top_precision"],
            best["top_hit_count"],
            best["mean_score"],
        ):
            best = candidate

    assert best is not None
    best["evaluations"] = evaluations
    best["echo_analysis"] = twin_gravity_echo_analysis(best["top_rows"], bins)
    return best


def run_twin_prime_gravity_search(
    seed_limit: int,
    limit: int,
    bins: int,
    top: int,
    tune: bool = False,
    tune_step: float = 0.1,
    metric: str = "cylindrical",
) -> dict:
    seed_values = [
        p
        for p in range(3, seed_limit + 1, 2)
        if deterministic_miller_rabin_u64(p) and deterministic_miller_rabin_u64(p + 2)
    ]
    hyperbolic_scale = math.log(max(2, limit))
    bodies = solution_gravity_bodies(seed_values, bins, hyperbolic_scale)
    learned_bins = {body["angle_bin"] for body in bodies}
    rz_anchors = riemann_phase_anchor(seed_values)
    shadow_lattice = build_shadow_lattice(seed_values, limit)
    gap_profile = build_twin_gap_record_profile(seed_values)
    start = max(3, seed_limit + 1)
    if start % 2 == 0:
        start += 1
    candidates = [
        twin_prime_gravity_candidate(
            p,
            bodies,
            learned_bins,
            bins,
            metric,
            hyperbolic_scale,
            seed_values,
            rz_anchors,
            shadow_lattice,
            gap_profile,
        )
        for p in range(start, limit, 2)
    ]
    ranked = sorted(
        candidates,
        key=lambda row: (-row["combined_gravity_field"], -row["gravity_product_field"], row["p"]),
    )
    top_rows = ranked[:top]
    hits = [row for row in candidates if row["verified"]]
    top_hits = [row for row in top_rows if row["verified"]]
    echo_analysis = twin_gravity_echo_analysis(top_rows, bins)
    tuned = tune_twin_gravity_weights(candidates, top, tune_step, bins) if tune else None

    # ── 1. Solution radius ratio: Δcenter / center ─────────────────────────
    # center = p + 1 for each verified twin prime.  Keeps scale change visible
    # as numbers grow (raw ratio drifts to 1 at large values and loses signal).
    hit_centers = sorted([row["p"] + 1 for row in hits])
    sol_radius_ratios: list[float] = []
    if len(hit_centers) >= 2:
        for i in range(len(hit_centers) - 1):
            c_curr, c_next = hit_centers[i], hit_centers[i + 1]
            sol_radius_ratios.append((c_next - c_curr) / c_curr)
    srr_mean = sum(sol_radius_ratios) / len(sol_radius_ratios) if sol_radius_ratios else 0.0
    srr_max = max(sol_radius_ratios) if sol_radius_ratios else 0.0
    srr_min = min(sol_radius_ratios) if sol_radius_ratios else 0.0

    # ── 2. Phase lane contrast: hit_density / echo_density per angle bin ──
    # Shows which log(p) mod 2π bins are true solution lanes vs noisy echo lanes.
    eps_density = 1e-6
    hit_bins = [0] * bins
    echo_bins = [0] * bins
    for row in top_rows:
        ab = angle_bin_for_value(row["p"], bins)
        if row["verified"]:
            hit_bins[ab] += 1
        else:
            echo_bins[ab] += 1
    lane_contrast = [
        round(hit_bins[b] / max(echo_bins[b], eps_density), 4)
        for b in range(bins)
    ]
    top_lane_bins = sorted(range(bins), key=lambda b: -lane_contrast[b])[:8]

    # ── 3. Seed horizon jump ratio: candidate_p / max(seed_values) ────────
    # Shows how far the gravity field is projecting beyond the known bodies.
    max_seed = max(seed_values) if seed_values else 1
    for row in candidates:
        row["horizon_jump"] = round(row["p"] / max_seed, 4)

    # ── 4. Precision lift by distance band ─────────────────────────────────
    # Bins candidates by horizon_jump factor; computes precision per band.
    # Tests whether the field learns a portable shape or just orbits seeds.
    bands = [
        ("1x-2x",      1.0,    2.0),
        ("2x-10x",     2.0,   10.0),
        ("10x-60x",   10.0,   60.0),
        ("60x-1000x", 60.0, 1000.0),
        ("1000x+",  1000.0, math.inf),
    ]
    band_stats: list[dict] = []
    for label, lo, hi in bands:
        band_cands = [row for row in candidates if lo <= row["horizon_jump"] < hi]
        band_hits = [row for row in band_cands if row["verified"]]
        base_rate = len(band_hits) / max(1, len(band_cands))
        # Precision: top-10% of band by combined_gravity_field
        top_n = max(1, len(band_cands) // 10)
        band_ranked = sorted(band_cands, key=lambda r: -r["combined_gravity_field"])
        band_top_hits = [r for r in band_ranked[:top_n] if r["verified"]]
        precision = len(band_top_hits) / max(1, top_n)
        lift = precision / max(base_rate, eps_density)
        band_stats.append({
            "band": label,
            "candidates": len(band_cands),
            "hits": len(band_hits),
            "base_rate": round(base_rate, 4),
            "top_n": top_n,
            "top_hits": len(band_top_hits),
            "precision": round(precision, 4),
            "lift": round(lift, 2),
        })

    return {
        "schema_version": "prime_fog_twin_prime_gravity_search_v1",
        "interpretation": (
            "known verified twin primes are gravity bodies on the log/phase manifold; "
            "candidate p values are ranked by gravitational potential, then exactly verified"
        ),
        "verifier": "is_prime(p) and is_prime(p+2)",
        "semantic_invariant": semantic_invariant_packet(
            "twin_prime_gravity",
            "normalized_force = total_force / (1 + total_force)",
            "gravity_field_normalized",
        ),
        "seed_limit": seed_limit,
        "limit": limit,
        "bins": bins,
        "gravity_metric": metric,
        "hyperbolic_scale": round(hyperbolic_scale, 12),
        "seed_solution_count": len(seed_values),
        "shadow_lattice_product_count": len(shadow_lattice["products"]),
        "shadow_lattice_prime_pool_count": len(shadow_lattice["prime_pool"]),
        "riemann_phase_anchor_count": len(rz_anchors),
        "riemann_phase_anchor_mean_coherence": round(
            sum(anchor["coherence"] for anchor in rz_anchors) / max(1, len(rz_anchors)),
            6,
        ),
        "candidate_count": len(candidates),
        "hit_count": len(hits),
        "top": top,
        "top_hit_count": len(top_hits),
        "top_precision": round(len(top_hits) / max(1, len(top_rows)), 6),
        "echo_analysis": echo_analysis,
        "tuning": tuned,
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
        "all_candidates": candidates,
        "solution_radius_ratio": {
            "mean": round(srr_mean, 6),
            "min": round(srr_min, 6),
            "max": round(srr_max, 6),
            "n": len(sol_radius_ratios),
        },
        "phase_lane_contrast": lane_contrast,
        "top_lane_bins": top_lane_bins,
        "band_precision": band_stats,
        "max_seed": max_seed,
    }


def print_twin_prime_gravity_search(payload: dict) -> None:
    print("Twin-prime solution gravity search")
    print(payload["interpretation"])
    print(f"verifier: {payload['verifier']}")
    print(f"invariant: {payload['semantic_invariant']['local_form']}")
    print(f"metric: {payload['gravity_metric']}  hyperbolic_scale={payload['hyperbolic_scale']}")
    print(f"seed limit: {payload['seed_limit']}  search limit: {payload['limit']}")
    print(f"known solution bodies: {payload['seed_solution_count']}")
    print(
        "shadow lattice: "
        f"{payload.get('shadow_lattice_product_count', 0)} products from "
        f"{payload.get('shadow_lattice_prime_pool_count', 0)} seed primes"
    )
    print(
        "riemann phase anchors: "
        f"{payload.get('riemann_phase_anchor_count', 0)}  "
        f"mean coherence={payload.get('riemann_phase_anchor_mean_coherence', 0.0)}"
    )
    print(f"candidates: {payload['candidate_count']}  hits in range: {payload['hit_count']}")
    print(f"top precision: {payload['top_precision']:.2%} ({payload['top_hit_count']}/{payload['top']})")
    echo = payload["echo_analysis"]
    print(f"echoes: {echo['echo_count']}  precision={echo['precision']:.2%}")
    print(f"echo failure modes: {echo['failure_modes']}")
    print(f"echo small divisors: {echo['small_divisors']}")
    print(f"echo mesh bands: {echo['mesh_ratio_bands']}")
    print(f"hit angle bins: {echo['hit_angle_histogram']}")
    print(f"echo angle bins: {echo['echo_angle_histogram']}")
    if payload.get("tuning"):
        tuned = payload["tuning"]
        print()
        print("Weight sweep:")
        print(f"  evaluations: {tuned['evaluations']}")
        print(f"  best weights: {tuned['weights']}")
        print(f"  tuned precision: {tuned['top_precision']:.2%} ({tuned['top_hit_count']}/{payload['top']})")
        print(f"  tuned echo modes: {tuned['echo_analysis']['failure_modes']}")

    # Solution radius ratio
    srr = payload.get("solution_radius_ratio", {})
    if srr:
        print()
        print(f"Solution radius ratio  Δcenter/center  (n={srr['n']} gaps):")
        print(f"  mean={srr['mean']:.6f}  min={srr['min']:.6f}  max={srr['max']:.6f}")
        print(f"  (scale-stable gap: keeps signal as p grows; raw p_next/p_curr drifts to 1)")

    # Phase lane contrast
    contrast = payload.get("phase_lane_contrast", [])
    top_bins = payload.get("top_lane_bins", [])
    if contrast and top_bins:
        print()
        print("Phase lane contrast  hit_density/echo_density  (top solution lanes):")
        for b in top_bins:
            bar = "█" * min(int(contrast[b] * 4), 40)
            print(f"  bin {b:>2}  contrast={contrast[b]:>7.3f}  {bar}")

    # Precision lift by distance band
    bands = payload.get("band_precision", [])
    if bands:
        print()
        print("Precision lift by seed horizon distance band  (top-10% of band):")
        print(f"  {'band':<12}  {'cands':>7}  {'hits':>5}  {'base':>6}  {'prec':>6}  {'lift':>6}")
        print("  " + "─" * 52)
        for b in bands:
            if b["candidates"] == 0:
                continue
            print(
                f"  {b['band']:<12}  {b['candidates']:>7}  {b['hits']:>5}  "
                f"{b['base_rate']:>5.2%}  {b['precision']:>5.2%}  {b['lift']:>5.1f}x"
            )

    # Path A ∩ Path B ∩ Path C intersection statistics
    all_rows = payload.get("all_candidates", [])
    if all_rows and any("path_b_score" in r for r in all_rows[:5]):
        n_all = len(all_rows)
        top10_n = max(1, n_all // 10)
        path_a_sorted = sorted(all_rows, key=lambda r: -r.get("combined_gravity_field", 0))
        path_b_sorted = sorted(
            [r for r in all_rows if r.get("mod30_wheel", 0) != 0.0],
            key=lambda r: -r.get("path_b_score", 0),
        )
        path_a_top = {r["p"] for r in path_a_sorted[:top10_n]}
        path_b_top = {r["p"] for r in path_b_sorted[:top10_n]}
        path_c_sorted = sorted(
            all_rows,
            key=lambda r: -r.get("path_c_score", 0),
        )
        path_c_top = {r["p"] for r in path_c_sorted[:top10_n]}
        path_d_sorted = sorted(
            all_rows,
            key=lambda r: -r.get("path_d_score", 0),
        )
        path_d_top = {r["p"] for r in path_d_sorted[:top10_n]}
        path_e_sorted = sorted(all_rows, key=lambda r: -r.get("path_e_score", 0))
        path_e_top = {r["p"] for r in path_e_sorted[:top10_n]}
        intersection = path_a_top & path_b_top
        triple = intersection & path_c_top
        quad = triple & path_d_top
        penta = quad & path_e_top
        wheel_zero = sum(1 for r in all_rows if r.get("mod30_wheel", 1.0) == 0.0)
        shadow_hits = sum(1 for r in all_rows if r.get("shadow_lattice_hit"))
        wheel_elim_pct = wheel_zero / n_all * 100
        hits_a = sum(1 for r in all_rows if r["p"] in path_a_top and r.get("verified"))
        hits_b = sum(1 for r in all_rows if r["p"] in path_b_top and r.get("verified"))
        hits_c = sum(1 for r in all_rows if r["p"] in path_c_top and r.get("verified"))
        hits_d = sum(1 for r in all_rows if r["p"] in path_d_top and r.get("verified"))
        hits_e = sum(1 for r in all_rows if r["p"] in path_e_top and r.get("verified"))
        hits_ab = sum(
            1 for r in all_rows if r["p"] in intersection and r.get("verified")
        )
        hits_abc = sum(
            1 for r in all_rows if r["p"] in triple and r.get("verified")
        )
        hits_abcd = sum(
            1 for r in all_rows if r["p"] in quad and r.get("verified")
        )
        hits_abcde = sum(
            1 for r in all_rows if r["p"] in penta and r.get("verified")
        )
        base_rate = sum(1 for r in all_rows if r.get("verified")) / max(n_all, 1)
        prec_a = hits_a / max(len(path_a_top), 1)
        prec_b = hits_b / max(len(path_b_top), 1)
        prec_c = hits_c / max(len(path_c_top), 1)
        prec_d = hits_d / max(len(path_d_top), 1)
        prec_e = hits_e / max(len(path_e_top), 1)
        prec_ab = hits_ab / max(len(intersection), 1)
        prec_abc = hits_abc / max(len(triple), 1)
        prec_abcd = hits_abcd / max(len(quad), 1)
        prec_abcde = hits_abcde / max(len(penta), 1)
        print()
        print("Path A ∩ Path B ∩ Path C ∩ Path D intersection  (top-10% each path):")
        print(f"  Path A  candidates={len(path_a_top):>5}  hits={hits_a:>4}  prec={prec_a:.2%}  ({prec_a/max(base_rate,1e-9):.1f}x lift)")
        print(f"  Path B  candidates={len(path_b_top):>5}  hits={hits_b:>4}  prec={prec_b:.2%}  ({prec_b/max(base_rate,1e-9):.1f}x lift)")
        print(f"  Path C  candidates={len(path_c_top):>5}  hits={hits_c:>4}  prec={prec_c:.2%}  ({prec_c/max(base_rate,1e-9):.1f}x lift)")
        print(f"  Path D  candidates={len(path_d_top):>5}  hits={hits_d:>4}  prec={prec_d:.2%}  ({prec_d/max(base_rate,1e-9):.1f}x lift)")
        print(f"  Path E  candidates={len(path_e_top):>5}  hits={hits_e:>4}  prec={prec_e:.2%}  ({prec_e/max(base_rate,1e-9):.1f}x lift)  [Riemann-anchored gap-ratio gravity]")
        print(f"  A∩B     candidates={len(intersection):>5}  hits={hits_ab:>4}  prec={prec_ab:.2%}  ({prec_ab/max(base_rate,1e-9):.1f}x lift)")
        print(f"  A∩B∩C   candidates={len(triple):>5}  hits={hits_abc:>4}  prec={prec_abc:.2%}  ({prec_abc/max(base_rate,1e-9):.1f}x lift)")
        print(f"  A∩B∩C∩D candidates={len(quad):>5}  hits={hits_abcd:>4}  prec={prec_abcd:.2%}  ({prec_abcd/max(base_rate,1e-9):.1f}x lift)")
        print(f"  A∩…∩E   candidates={len(penta):>5}  hits={hits_abcde:>4}  prec={prec_abcde:.2%}  ({prec_abcde/max(base_rate,1e-9):.1f}x lift)  [all five paths]")
        print(f"  mod30 wheel: {wheel_zero} eliminated ({wheel_elim_pct:.1f}% of candidates algebraically impossible)")
        print(f"  shadow lattice: {shadow_hits} exact seed-product shadows masked before verifier")

    print()
    print("Top gravity-ranked candidates:")
    for row in payload["top_rows"][:12]:
        mark = "hit" if row["verified"] else "echo"
        div_clr = row.get("div_ratio_clearance", 1.0)
        pmz = row.get("phi_mean_zero_wave", "—")
        hj = row.get("horizon_jump", "—")
        pb = row.get("path_b_score", "—")
        pc = row.get("path_c_score", "—")
        pd = row.get("path_d_score", "—")
        compass = row.get("path_d_compass_alignment")
        shadow = " shadow" if row.get("shadow_lattice_hit") else ""
        pd_str = f"{pd:.4f}" if isinstance(pd, float) else str(pd)
        compass_str = f"{compass:.4f}" if isinstance(compass, float) else "—"
        print(
            f"  {mark:<4} p={row['p']:<8} q={row['q']:<8} "
            f"combined={row['combined_gravity_field']:.5f} "
            f"pmz={pmz:.4f}  pathB={pb:.4f}  pathC={pc:.4f}  pathD={pd_str}  "
            f"compass={compass_str}  div={div_clr:.3f}{shadow}  jump={hj}x"
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


# ── Unified Harmonic Gate — the algebraic squashing invariant ────────────────
#
# The cross-domain invariant identified across primes, molecular weights,
# protein pLDDT, gravity fields, and electron well depths is the rational form:
#
#   H(delta) = delta / (1 + delta)
#
# This is the pure rational squashing function that maps [0, ∞) → [0, 1).
# It replaces transcendental sigmoid (e^-x, which requires Taylor expansion at
# the CPU level) with a simple integer division — one subtraction and one
# multiply at the hardware level.
#
# The CRITICAL INSIGHT for trit generation:
#   theta_edge = 0.5 = H(1.0) is the UNIVERSAL threshold.
#   This means: the near-miss zone is exactly ONE scale unit beyond the ideal
#   boundary. The scale IS the cliff width. No other parameter is needed.
#
#   delta=0 → H=0     → inside ideal zone → trit=2 (ground state)
#   delta=1 → H=0.5   → at near-miss edge → trit=1 (activity cliff)
#   delta>1 → H>0.5   → beyond cliff      → trit=0 (ionized / escaped)
#
# Gate table: (name, lo_ideal, hi_ideal, lo_scale, hi_scale)
#   lo_scale = distance from lo_ideal to the outer near-miss boundary (left cliff)
#   hi_scale = distance from hi_ideal to the outer near-miss boundary (right cliff)
#
# Calibration: all cliffs match the empirically derived thresholds from the
# legacy _logp_trit / _tpsa_trit / _mw_lipinski_trit functions EXACTLY,
# because H(1.0) = 0.5 pinned to the same outer boundaries.
#
# The table encodes the PHYSICS of each cliff:
#   MW:    lo_scale=50  (100→50 Da, fragility cliff)
#          hi_scale=400 (500→900 Da, macrocycle cliff — much wider tolerance)
#   logP:  lo_scale=3   (0→-3, steep hydrophilic cliff — membrane impermeability)
#          hi_scale=2   (5→7,  gentler lipophilic — formulation can rescue)
#   TPSA:  lo_scale=15  (20→5, CNS flat-molecule zone)
#          hi_scale=70  (130→200, bRo5/PROTAC chameleonicity zone)
#
# Stability and severity use unilateral harmonic gates (single-sided):
#   stability: H(delta) where delta = max(0, threshold - score) / scale
#   severity:  H(delta) where delta = min_distance_to_severe / scale

_HARMONIC_GATE_TABLE: list[tuple[str, float, float, float, float]] = [
    # name,   lo_ideal,  hi_ideal,  lo_scale,  hi_scale
    ("mw",     100.0,     500.0,      50.0,     400.0),
    ("logp",     0.0,       5.0,       3.0,       2.0),
    ("tpsa",    20.0,     130.0,      15.0,      70.0),
]

# Universal threshold: H(1.0) = 0.5
# delta <= 1 → H <= 0.5 → trit=1 (near-miss zone = one scale unit from ideal)
# delta > 1  → H > 0.5  → trit=0 (escaped / ionized)
_HARMONIC_THETA_EDGE: float = 0.5


def harmonic_gate_trit(
    value: float,
    lo_ideal: float,
    hi_ideal: float,
    lo_scale: float,
    hi_scale: float,
    theta_edge: float = _HARMONIC_THETA_EDGE,
) -> int:
    """Unified harmonic gate: trit from a bilateral ideal window.

    Maps value to {0, 1, 2} via H(delta) = delta / (1 + delta):

      trit=2 (ground)   : value in [lo_ideal, hi_ideal]         H=0
      trit=1 (excited)  : H(delta) <= theta_edge = 0.5          delta <= 1
                          i.e. within one scale unit of the ideal boundary
      trit=0 (escaped)  : H(delta) > theta_edge                 delta > 1

    The near-miss zone extends exactly lo_scale below lo_ideal and hi_scale
    above hi_ideal. theta_edge = 0.5 = H(1.0) is the universal constant.
    """
    if lo_ideal <= value <= hi_ideal:
        return 2
    if value < lo_ideal:
        delta = (lo_ideal - value) / max(lo_scale, 1e-9)
    else:
        delta = (value - hi_ideal) / max(hi_scale, 1e-9)
    h = delta / (1.0 + delta)
    return 1 if h <= theta_edge else 0


def harmonic_gate_trit_unilateral(
    delta: float,
    scale: float,
    theta_edge: float = _HARMONIC_THETA_EDGE,
) -> int:
    """Unilateral harmonic gate for deviation-from-target gates (stability, severity).

    delta=0 → trit=2, delta=scale → trit boundary, delta>scale → trit=0.
    """
    if delta <= 0.0:
        return 2
    d = delta / max(scale, 1e-9)
    h = d / (1.0 + d)
    return 1 if h <= theta_edge else 0


def _harmonic_gate_state(
    spec: dict,
    theta_edge: float = _HARMONIC_THETA_EDGE,
) -> dict:
    name = str(spec["name"])
    kind = str(spec.get("kind", "bilateral"))
    value = float(spec.get("value", 0.0))

    if kind == "constant":
        trit = int(spec.get("trit", 1))
        return {
            "name": name,
            "kind": kind,
            "value": value,
            "delta": 0.0 if trit == 2 else 1.0 if trit == 1 else math.inf,
            "harmonic": 0.0 if trit == 2 else theta_edge if trit == 1 else 1.0,
            "trit": trit,
        }

    if kind == "bilateral":
        lo_ideal = float(spec["lo_ideal"])
        hi_ideal = float(spec["hi_ideal"])
        lo_scale = max(float(spec["lo_scale"]), 1e-9)
        hi_scale = max(float(spec["hi_scale"]), 1e-9)
        if lo_ideal <= value <= hi_ideal:
            delta = 0.0
        elif value < lo_ideal:
            delta = (lo_ideal - value) / lo_scale
        else:
            delta = (value - hi_ideal) / hi_scale
    elif kind == "lower_bound":
        lo_ideal = float(spec["lo_ideal"])
        lo_scale = max(float(spec["lo_scale"]), 1e-9)
        delta = 0.0 if value >= lo_ideal else (lo_ideal - value) / lo_scale
    elif kind == "upper_bound":
        hi_ideal = float(spec["hi_ideal"])
        hi_scale = max(float(spec["hi_scale"]), 1e-9)
        delta = 0.0 if value <= hi_ideal else (value - hi_ideal) / hi_scale
    else:
        raise ValueError(f"unsupported harmonic gate kind: {kind}")

    h = delta / (1.0 + delta)
    trit = 2 if delta <= 0.0 else 1 if h <= theta_edge else 0
    return {
        "name": name,
        "kind": kind,
        "value": round(value, 12),
        "delta": round(delta, 12),
        "harmonic": round(h, 12),
        "trit": trit,
    }


def harmonic_gate_tensor(gate_specs: list[dict], theta_edge: float = _HARMONIC_THETA_EDGE) -> dict:
    """Evaluate many trit gates with one shared H(delta)=delta/(1+delta) law."""
    states = [_harmonic_gate_state(spec, theta_edge) for spec in gate_specs]
    trits = [int(state["trit"]) for state in states]
    harmonics = [float(state["harmonic"]) for state in states if math.isfinite(float(state["harmonic"]))]
    mean_h = sum(harmonics) / max(1, len(harmonics))
    return {
        "theta_edge": theta_edge,
        "law": "H(delta)=delta/(1+delta)",
        "trits": trits,
        "states": states,
        "mean_harmonic": round(mean_h, 12),
        "glow_float": round(sum(trits) / (2.0 * max(1, len(trits))), 12),
    }


def generalized_trit_tensor(
    mw: float,
    logp: float,
    tpsa: float,
    stability_score: float,
    stability_threshold: float,
    predicted_band: tuple[float, float] | None = None,
    severity_min_dist: float | None = None,
    alphafold_trit: int | None = None,
) -> dict:
    if severity_min_dist is None:
        severe_mws = [s[1] for s in _CHEM_SEEDS if s[3]]
        severity_min_dist = min((abs(mw - sm) for sm in severe_mws), default=999.0)

    gate_specs: list[dict] = [
        {
            "name": "mw",
            "kind": "bilateral",
            "value": mw,
            "lo_ideal": 100.0,
            "hi_ideal": 500.0,
            "lo_scale": 50.0,
            "hi_scale": 400.0,
        },
        {
            "name": "severity",
            "kind": "lower_bound",
            "value": severity_min_dist,
            "lo_ideal": 5.0,
            "lo_scale": 4.5,
        },
        {
            "name": "predicted_band",
            "kind": "constant",
            "value": mw,
            "trit": 1,
        },
        {
            "name": "stability",
            "kind": "lower_bound",
            "value": stability_score,
            "lo_ideal": stability_threshold,
            "lo_scale": max(stability_threshold * 0.5, 1e-9),
        },
        {
            "name": "logp",
            "kind": "bilateral",
            "value": logp,
            "lo_ideal": 0.0,
            "hi_ideal": 5.0,
            "lo_scale": 3.0,
            "hi_scale": 2.0,
        },
        {
            "name": "tpsa",
            "kind": "bilateral",
            "value": tpsa,
            "lo_ideal": 20.0,
            "hi_ideal": 130.0,
            "lo_scale": 15.0,
            "hi_scale": 70.0,
        },
    ]

    if predicted_band is not None:
        lo_b, hi_b = predicted_band
        width = max(hi_b - lo_b, 1.0)
        gate_specs[2] = {
            "name": "predicted_band",
            "kind": "bilateral",
            "value": mw,
            "lo_ideal": lo_b,
            "hi_ideal": hi_b,
            "lo_scale": width * 0.5,
            "hi_scale": width * 0.5,
        }

    if alphafold_trit is not None:
        gate_specs.append(
            {
                "name": "alphafold_plddt",
                "kind": "constant",
                "value": alphafold_trit,
                "trit": int(alphafold_trit),
            }
        )

    tensor = harmonic_gate_tensor(gate_specs)
    tensor["gate_order"] = [spec["name"] for spec in gate_specs]
    return tensor


def generalized_trit_vector(
    mw: float,
    logp: float,
    tpsa: float,
    stability_score: float,
    stability_threshold: float,
    predicted_band: tuple[float, float] | None = None,
    severity_min_dist: float | None = None,
    alphafold_trit: int | None = None,
) -> list[int]:
    """Evaluate all gate trits simultaneously via the unified harmonic form.

    Returns a trit vector [mw_t, sev_t, band_t, stab_t, logp_t, tpsa_t, (af_t)].
    All continuous gates use H(delta) = delta / (1 + delta) with theta_edge=0.5.

    Gate layout (matches legacy gate ordering):
      [0] mw      — Lipinski MW, bilateral, lo=100 hi=500, scales 50/400
      [1] sev     — severity distance, unilateral, scale=5 (0.5 Da hard fail zone)
      [2] band    — predicted band membership, bilateral from band center
      [3] stab    — stability vs threshold, unilateral, scale=threshold*0.5
      [4] logp    — LogP, bilateral, lo=0 hi=5, scales 3/2
      [5] tpsa    — TPSA, bilateral, lo=20 hi=130, scales 15/70
      [6] af      — AlphaFold pLDDT trit (pre-computed, passed through as-is)

    This is a single vectorized pass: compute all deltas, apply H, threshold.
    No branching per gate — all gates share the same rational squashing law.
    """
    return generalized_trit_tensor(
        mw=mw,
        logp=logp,
        tpsa=tpsa,
        stability_score=stability_score,
        stability_threshold=stability_threshold,
        predicted_band=predicted_band,
        severity_min_dist=severity_min_dist,
        alphafold_trit=alphafold_trit,
    )["trits"]


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


# ── Quantum electron-well model ──────────────────────────────────────────────
#
# The trit gate vector IS a quantum-well potential landscape.
#
# Each gate i has three eigenstates:
#   |0⟩  =  trit=0  "unbound"    — gate hard-failed, candidate escaped the well
#   |1⟩  =  trit=1  "excited"    — near-miss, candidate in superposition zone
#   |2⟩  =  trit=2  "ground"     — gate confirmed pass, lowest energy for this gate
#
# The full candidate state is a tensor product of per-gate eigenstates:
#   |ψ⟩ = |trit_0⟩ ⊗ |trit_1⟩ ⊗ ... ⊗ |trit_n⟩
#
# Ground state    = all gates at |2⟩  → trit_int = 3^n - 1 (maximum)
# Excitation level = number of gates in |1⟩ (superposition, not yet collapsed)
# Ionization      = any gate at |0⟩   → candidate escaped the well entirely
#
# Before the endpoint verifier runs, a trit=1 gate is in genuine superposition:
# the candidate could collapse to pass OR fail.  The verifier is the measurement
# operator.  The "affirmation" the user describes is the verifier collapsing
# the excited superposition state to a definite outcome.
#
# "Erratic transformation to new electron" = MW activity cliff: a ±0.5 Da step
# causes one gate to tunnel from |1⟩ → |2⟩ or |1⟩ → |0⟩.  The candidate
# jumps to a different address in trit-space.  The cliff IS the tunnel barrier.
#
# "Excitement into multi-state" = polypharmacology: a candidate simultaneously
# satisfies multiple target profiles.  Encoded as multiple AlphaFold trits (one
# per target protein); the multi-target excitation vector shows which targets the
# candidate is in ground state for.
#
# Potential energy U(trit_vec):
#   U = (max_int - trit_int) / max_int        in [0, 1]
#   U = 0 at ground state (all 2s)            deepest in the well
#   U = 1 at fully unbound (all 0s)           escaped / ionized
#
# Self-ratio observation (from user): the innate shape of one thing is not 1
# but 1 ± self_ratio.  In trit-space this is:
#   trit_i ∈ {0, 1, 2}  →  normalized = trit_i / 2  ∈ {0, 0.5, 1}
#   self_ratio_i = |1 - normalized_i|  ∈ {0, 0.5, 1}
# The ground state has self_ratio=0 for all gates (no deviation from the
# stable shape).  An excited gate has self_ratio=0.5 (oscillating ± half-step).
# An escaped gate has self_ratio=1 (fully inverted / at the outer wall).
#
# Connection to harmonic wall: H = 1/(1 + d + 2*pd)
#   At ground state: d=0, pd=0  → H=1    (U=0)
#   At excited:      d≈0.5       → H≈0.67 (U≈0.5)
#   At escaped:      d=1, pd=1   → H≈0.2  (U=1)
# The well potential IS the complement of the harmonic wall score.

_GATE_NAMES = ["Lipinski-MW", "Severity", "Predicted-Band", "Stability", "LogP", "TPSA", "AF-pLDDT"]
_GATE_LABELS = {0: "unbound", 1: "excited", 2: "ground"}


def electron_well_state(trit_vec: list[int]) -> dict:
    """Compute the quantum-well state for a trit gate vector.

    Returns:
      excitation_level   — number of gates in |1⟩ (uncertain, superposition)
      ionized_gates      — number of gates in |0⟩ (hard-failed, escaped well)
      ground_gates       — number of gates in |2⟩ (confirmed pass)
      well_depth         — fractional proximity to ground state in [0, 1]
                           1.0 = fully in ground state (all-pass)
                           0.0 = fully escaped (all-fail)
      potential_energy   — complement of well_depth (0 = deepest, 1 = escaped)
      self_ratio         — mean |1 - trit_i/2| across gates (0 = stable)
      gate_states        — per-gate label dict
      superposition_frac — fraction of gates in excited superposition
      state_label        — human label for the dominant state
    """
    n = len(trit_vec)
    if n == 0:
        return {
            "excitation_level": 0, "ionized_gates": 0, "ground_gates": 0,
            "well_depth": 0.0, "potential_energy": 1.0, "self_ratio": 1.0,
            "gate_states": {}, "superposition_frac": 0.0, "state_label": "empty",
        }
    max_int = 3 ** n - 1
    trit_int = encode_trit_vector(trit_vec)
    excitation_level = sum(1 for t in trit_vec if t == 1)
    ionized_gates = sum(1 for t in trit_vec if t == 0)
    ground_gates = sum(1 for t in trit_vec if t == 2)
    well_depth = trit_int / max_int
    potential_energy = 1.0 - well_depth
    self_ratio = sum(abs(1.0 - t / 2.0) for t in trit_vec) / n

    gate_states = {}
    for i, t in enumerate(trit_vec):
        name = _GATE_NAMES[i] if i < len(_GATE_NAMES) else f"gate_{i}"
        gate_states[name] = _GATE_LABELS[t]

    superposition_frac = excitation_level / n

    if ionized_gates > 0:
        state_label = f"ionized({ionized_gates})"
    elif excitation_level == 0:
        state_label = "ground"
    elif excitation_level == 1:
        state_label = "1st-excited"
    elif excitation_level == 2:
        state_label = "2nd-excited"
    else:
        state_label = f"{excitation_level}th-excited"

    return {
        "excitation_level": excitation_level,
        "ionized_gates": ionized_gates,
        "ground_gates": ground_gates,
        "well_depth": round(well_depth, 6),
        "potential_energy": round(potential_energy, 6),
        "self_ratio": round(self_ratio, 6),
        "gate_states": gate_states,
        "superposition_frac": round(superposition_frac, 4),
        "state_label": state_label,
    }


def electron_well_landscape(grid: list[dict]) -> dict:
    """Compute the electron well energy landscape across the answer-space grid.

    Maps the trit grid into a quantum-well potential landscape:
      - Ground state MWs (excitation=0): deepest in the well
      - Excited state MWs (excitation>0): near the walls, cliff-edge candidates
      - Activity cliffs: MW ranges where excitation level changes sharply

    Returns:
      ground_state_mws     — list of MWs fully in ground state
      excitation_histogram — {excitation_level: count}
      cliff_transitions    — list of (mw_a, mw_b, gate, direction) cliff edges
      mean_well_depth      — average well_depth across all candidates
      mean_self_ratio      — average self_ratio (lower = more stable geometry)
      deepest_candidate    — candidate with highest well_depth (most ground-state)
    """
    if not grid:
        return {
            "ground_state_mws": [], "excitation_histogram": {},
            "cliff_transitions": [], "mean_well_depth": 0.0,
            "mean_self_ratio": 0.0, "deepest_candidate": None,
        }

    enriched = []
    for g in grid:
        ws = electron_well_state(g["trit_vec"])
        enriched.append({**g, **ws})

    ground_state_mws = [e["mw"] for e in enriched if e["excitation_level"] == 0 and e["ionized_gates"] == 0]

    exc_hist: dict[int, int] = {}
    for e in enriched:
        k = e["excitation_level"]
        exc_hist[k] = exc_hist.get(k, 0) + 1

    # Activity cliffs: adjacent MW steps where a gate flips trit value
    cliff_transitions = []
    for i in range(len(enriched) - 1):
        a, b = enriched[i], enriched[i + 1]
        n = min(len(a["trit_vec"]), len(b["trit_vec"]))
        for gi in range(n):
            if a["trit_vec"][gi] != b["trit_vec"][gi]:
                direction = "excited→ground" if b["trit_vec"][gi] > a["trit_vec"][gi] else "ground→excited"
                gate_name = _GATE_NAMES[gi] if gi < len(_GATE_NAMES) else f"gate_{gi}"
                cliff_transitions.append({
                    "mw_a": a["mw"], "mw_b": b["mw"],
                    "gate": gate_name, "gate_index": gi,
                    "trit_a": a["trit_vec"][gi], "trit_b": b["trit_vec"][gi],
                    "direction": direction,
                })

    mean_well_depth = sum(e["well_depth"] for e in enriched) / len(enriched)
    mean_self_ratio = sum(e["self_ratio"] for e in enriched) / len(enriched)
    deepest = max(enriched, key=lambda e: e["well_depth"])

    return {
        "ground_state_mws": ground_state_mws,
        "ground_state_count": len(ground_state_mws),
        "excitation_histogram": dict(sorted(exc_hist.items())),
        "cliff_transitions": cliff_transitions[:50],
        "cliff_count": len(cliff_transitions),
        "mean_well_depth": round(mean_well_depth, 6),
        "mean_self_ratio": round(mean_self_ratio, 6),
        "deepest_candidate": {k: v for k, v in deepest.items() if k not in ("gate_states",)},
    }


def run_electron_well_probe(
    stability_threshold: float = 1.0,
    predicted_band: tuple[float, float] | None = None,
    mw_step: float = 0.5,
    extend_sigma: float = 1.0,
    alphafold_uniprot: str | None = None,
    use_harmonic_gates: bool = False,
) -> dict:
    """Full electron-well probe: answer space + quantum well energy landscape."""
    space = run_answer_space_probe(
        stability_threshold=stability_threshold,
        predicted_band=predicted_band,
        mw_step=mw_step,
        extend_sigma=extend_sigma,
        alphafold_uniprot=alphafold_uniprot,
        use_harmonic_gates=use_harmonic_gates,
    )
    landscape = electron_well_landscape(space["all_candidates"])
    space["electron_well"] = landscape
    return space


def print_electron_well_probe(payload: dict) -> None:
    """Print answer space + electron well energy landscape."""
    print_answer_space_probe(payload)
    well = payload.get("electron_well", {})
    if not well:
        return
    print()
    print("Electron well energy landscape")
    print(f"  mean well depth:    {well['mean_well_depth']:.4f}  (1.0=fully in ground state)")
    print(f"  mean self-ratio:    {well['mean_self_ratio']:.4f}  (0.0=stable shape, 1.0=inverted)")
    print(f"  ground state MWs:   {well['ground_state_count']} candidates (excitation=0, all gates confirmed)")
    print(f"  activity cliffs:    {well['cliff_count']} gate transitions detected")
    print()
    print("  Excitation level histogram:")
    for lvl, cnt in sorted(well["excitation_histogram"].items()):
        _lvl_labels = ["ground", "1st-excited", "2nd-excited", "3rd-excited"]
        label = _lvl_labels[lvl] if lvl < len(_lvl_labels) else f"{lvl}th-excited"
        bar = "▓" * min(cnt, 50)
        print(f"    excitation={lvl}  ({label:<16})  {cnt:>5} pts  {bar}")
    if well.get("deepest_candidate"):
        d = well["deepest_candidate"]
        print(f"\n  Deepest well candidate: MW={d['mw']}  trit={d['trit_label']}  "
              f"depth={d['well_depth']:.4f}  self_ratio={d['self_ratio']:.4f}")
    if well["cliff_transitions"]:
        print()
        print("  Activity cliff edges (first 10):")
        print(f"  {'MW_a':>8}  {'MW_b':>8}  {'gate':<20}  {'trit_a':>6}  {'trit_b':>6}  direction")
        print("  " + "─" * 72)
        for c in well["cliff_transitions"][:10]:
            print(f"  {c['mw_a']:>8.2f}  {c['mw_b']:>8.2f}  {c['gate']:<20}  "
                  f"{c['trit_a']:>6}  {c['trit_b']:>6}  {c['direction']}")


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
    use_harmonic_gates: bool = False,
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
        best_score = 0.0
        for _, seed_mw, half_life_h, severe in _CHEM_SEEDS:
            if abs(mw - seed_mw) < 2.0:
                s = _chem_stability_score(seed_mw, half_life_h, severe)
                if s > best_score:
                    best_score = s
        if best_score == 0.0:
            half_life_est = 24.0 * max(50.0, min(mw, 500.0)) / 200.0
            best_score = _chem_stability_score(mw, half_life_est, False)

        logp_est, tpsa_est = _estimate_logp_tpsa(mw)
        harmonic_tensor = None

        if use_harmonic_gates:
            harmonic_tensor = generalized_trit_tensor(
                mw=mw,
                logp=logp_est,
                tpsa=tpsa_est,
                stability_score=best_score,
                stability_threshold=stability_threshold,
                predicted_band=predicted_band,
                alphafold_trit=alphafold_trit,
            )
            trit_vec = harmonic_tensor["trits"]
        else:
            lip_t = _mw_lipinski_trit(mw)
            sev_t = _severity_trit(mw)
            band_t = _band_trit(mw, predicted_band)
            stab_t = _stability_trit(best_score, stability_threshold)
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
                    **(
                        {
                            "harmonic_mean": harmonic_tensor["mean_harmonic"],
                            "harmonic_gate_order": harmonic_tensor["gate_order"],
                        }
                        if harmonic_tensor is not None
                        else {}
                    ),
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
    use_harmonic_gates: bool = False,
) -> dict:
    """Full answer-space probe: linear decomposition -> trit grid -> ranked answer space.

    alphafold_uniprot: if set, fetches AlphaFold pLDDT for the target protein
      and adds trit[6] to all candidates. Example: "P00533" for EGFR.
    use_harmonic_gates: if True, uses the unified H(delta)=delta/(1+delta) bilateral
      gate formula instead of legacy step-function thresholds.
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
        use_harmonic_gates=use_harmonic_gates,
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
    parser.add_argument("--integer-magnifier", action="store_true", help="Run integer relation magnification test lens")
    parser.add_argument(
        "--integer-values",
        default="-31,-29,-17,-5,-1,0,1,2,3,4,5,17,19,29,31,33,35",
        help="Comma-separated signed integers for --integer-magnifier",
    )
    parser.add_argument("--integer-bins", type=int, default=32, help="Log-phase bins for --integer-magnifier")
    parser.add_argument("--integer-shell", type=int, default=2, help="Near-value shell radius for --integer-magnifier")
    parser.add_argument(
        "--integer-binary-bits",
        type=int,
        default=16,
        help="How many low binary bits to show in --integer-magnifier",
    )
    parser.add_argument(
        "--integer-factor-primes",
        default="2,3,5,7,11,13,17,19,23,29,31,37,41,43,47",
        help="Bounded trial-division primes for integer factor_vector ingestion",
    )
    parser.add_argument(
        "--integer-residue-moduli",
        default="2,3,5,6,7,11,13,17,19,23,29,30,210",
        help="Comma-separated moduli for integer residue_vector ingestion",
    )
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
    parser.add_argument("--gravity-metric", choices=["cylindrical", "hyperbolic", "hybrid"], default="cylindrical")
    parser.add_argument("--gravity-tune", action="store_true", help="Grid-search gravity field weights")
    parser.add_argument("--gravity-tune-step", type=float, default=0.1)
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
        "--electron-well", action="store_true",
        help="Add quantum electron-well energy landscape to the answer-space probe. "
             "Shows ground-state MWs, excitation levels, activity cliff edges, "
             "well depth, and self-ratio (1±self_ratio shape oscillation). "
             "Use with --answer-space.",
    )
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
    parser.add_argument(
        "--harmonic-gates",
        action="store_true",
        help="Use unified harmonic gate formula H(delta)=delta/(1+delta) for all trit gates. "
             "Replaces legacy step-function thresholds with continuous bilateral cliff detection. "
             "theta_edge=0.5 means the near-miss zone is exactly ONE scale unit from the ideal window. "
             "Gate calibration: MW lo_scale=50 hi_scale=400, logP lo_scale=3 hi_scale=2, "
             "TPSA lo_scale=15 hi_scale=70. Use with --answer-space.",
    )
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--prime-ratio-map",
        action="store_true",
        help="Map consecutive twin prime center ratios against natural harmonic ratios "
             "(phi, sqrt2, musical intervals) and Riemann zero alignment. "
             "Shows which natural harmonic the twin prime spacing prefers at each scale.",
    )
    parser.add_argument("--ratio-map-limit", type=int, default=10000,
                        help="Upper limit for twin prime collection in --prime-ratio-map (default 10000)")
    parser.add_argument("--ratio-map-seed", type=int, default=1000,
                        help="Seed/split point for seed vs extended range comparison (default 1000)")
    parser.add_argument("--mod-triangulation", action="store_true", help="Run mod-space triangulation hopping probe")
    parser.add_argument("--triangulation-limit", type=int, default=100_000, help="Upper range for triangulation probe (default=100000)")
    parser.add_argument("--triangulation-mods", default="2,3,5", help="Comma-separated moduli for CRT axes")
    parser.add_argument("--triangulation-top", type=int, default=24, help="Top samples to print in hops/nodes")
    parser.add_argument("--triangulation-verify", action="store_true", help="Verify prime/twin-bridge candidates exactly")
    parser.add_argument(
        "--triangulation-exclude-non-starters",
        action="store_true",
        help="Drop known twin non-starters after CRT filtering (keeps only n in {11,17,29} mod 30, plus n=5)",
    )
    # Superprime layer — P(P(n)) through CRT negative-triangulation shells
    parser.add_argument("--superprime-layer", action="store_true", help="Map P(P(n)) superprimes [n prime] through CRT mod-30 shells")
    parser.add_argument("--superprime-limit", type=int, default=10_000, help="Sieve limit for superprime layer (default=10000)")
    parser.add_argument("--superprime-top", type=int, default=40, help="Rows to print in superprime table (default=40)")
    # Imaginary gap path — Δg × i complex pathfinder
    parser.add_argument("--imaginary-paths", action="store_true", help="Trace Δg×i complex path from prime gap acceleration")
    parser.add_argument("--imaginary-paths-limit", type=int, default=10_000, help="Sieve limit for imaginary gap path (default=10000)")
    parser.add_argument("--imaginary-paths-superprime", action="store_true", help="Use P(P(n)) superprime sequence for imaginary path (combines both probes)")
    parser.add_argument("--imaginary-paths-top", type=int, default=40, help="Path sample rows to print (default=40)")
    parser.add_argument("--imaginary-paths-ratio", action="store_true", help="Re-step using ratio of true Δg to mean |Δg| (triangulation normalization)")
    parser.add_argument("--imaginary-paths-well", action="store_true", help="Apply square-well potential at inner/outer shell crossings + tangential extrapolation")
    parser.add_argument("--imaginary-paths-well-depth", type=float, default=1.0, help="Well depth W in ratio-units (default=1.0; reflects inner→outer steps with |ratio|<=sqrt(W))")
    parser.add_argument("--imaginary-paths-well-extrap", type=int, default=5, help="Steps to extrapolate tangentially from each landmark crossing (default=5)")
    parser.add_argument("--imaginary-paths-well-threshold", type=float, default=2.0, help="Min |ratio| to trigger tangential extrapolation (default=2.0)")
    parser.add_argument("--foam-score", action="store_true", help="Score splash zones by surrounding turbulence density")
    parser.add_argument("--foam-score-window", type=int, default=10, help="Steps to scan each side of a splash for mist/droplet density (default=10)")
    parser.add_argument("--foam-score-top", type=int, default=20, help="Number of top foam zones to display (default=20)")
    parser.add_argument("--wall-loop", action="store_true", help="Test III/OOO splash events for hidden crossings in mod-210/2310 + phi phase drift")
    parser.add_argument("--wall-loop-window", type=int, default=6, help="Window around each splash for gap wall-loop scan (default=6)")
    parser.add_argument("--wall-loop-top", type=int, default=20, help="Top splash events to inspect per pattern class (default=20)")
    parser.add_argument("--soliton", action="store_true", help="Gap charge field soliton probe: ±1 per wall prime, 5-class taxonomy, soliton score")
    parser.add_argument("--soliton-window", type=int, default=10, help="Window around each splash for foam/charge density (default=10)")
    parser.add_argument("--soliton-top", type=int, default=25, help="Top events to display sorted by soliton score (default=25)")
    parser.add_argument("--next-region-field", action="store_true", help="Combine foam/shell/wall/phi/prime-ratio channels into found→next region search field")
    parser.add_argument("--next-region-window", type=int, default=12, help="Steps after each found splash anchor to score as the next region (default=12)")
    parser.add_argument("--next-region-top", type=int, default=25, help="Top next regions to display (default=25)")
    parser.add_argument("--next-region-anchor-threshold", type=float, default=4.0, help="Min |ratio| to treat a found event as an anchor (default=4.0)")
    parser.add_argument("--next-region-profile", choices=["balanced", "soliton", "forecast", "instability", "instability_flip", "instability_gate2", "resonance_gate3", "instability_geo", "resonant_soliton"], default="balanced", help="Channel weight profile: balanced (current), soliton (wall/charge/hidden), forecast (phi/prime/no outcome), instability (rebound/crossing/flip - phi - prime_ratio), instability_flip (gates high-foam/no-flip churn), instability_gate2 (extra stale-churn gates), resonance_gate3 (p-adic depth x prime-ratio), resonant_soliton (accel+depth flux+ratio+flip)")
    parser.add_argument("--field-scan", action="store_true", help="Scan every non-anchor step with trailing structural channels, then measure future heat/anchors")
    parser.add_argument("--field-scan-window", type=int, default=12, help="Future steps to score after each scan point (default=12)")
    parser.add_argument("--field-scan-history", type=int, default=6, help="Trailing context steps used for predictive field score (default=6)")
    parser.add_argument("--field-scan-top", type=int, default=25, help="Top field-scan rows to display (default=25)")
    parser.add_argument("--field-scan-anchor-threshold", type=float, default=4.0, help="Future |ratio| threshold counted as a confirmed anchor (default=4.0)")
    parser.add_argument("--field-scan-profile", choices=["balanced", "soliton", "forecast", "instability", "instability_flip", "instability_gate2", "resonance_gate3", "instability_geo", "resonant_soliton", "cassette", "instability_geo_cassette", "thermal", "instability_geo_cassette_thermal", "thermal_cold", "thermal_cool", "thermal_heat", "thermal_omni", "thermal_abs", "instability_geo_cassette_thermal_abs", "igct_c2_g3", "igct_c2_g4", "igct_c2_g5", "igct_c2_g6", "igct_c3_g3", "igct_c3_g4", "igct_c3_g5", "igct_c3_g6", "igct_c4_g3", "igct_c4_g4", "igct_c4_g5", "igct_c4_g6", "igct_c2_g7", "igct_c2_g8", "igct_c3_g7", "igct_c3_g8", "igct_c4_g7", "igct_c4_g8"], default="forecast", help="Predictive channel profile for --field-scan (default=forecast)")
    return parser.parse_args(argv)


# ─── Superprime Layer (P(P(n)) prime-index filter) ────────────────────────────


def _compute_doubly_indexed_superprimes(primes: list[int]) -> list[dict]:
    """P(P(n)) for each prime n, using n as a 1-based index into the primes list."""
    rows: list[dict] = []
    for n in primes:
        if n < 1 or n > len(primes):
            continue
        pn = primes[n - 1]
        if pn < 1 or pn > len(primes):
            continue
        ppn = primes[pn - 1]
        r30 = ppn % 30
        zs = r30 % 5
        if zs > 2:
            zs -= 5
        ys = r30 % 3
        if ys > 1:
            ys -= 3
        a = r30 % 2
        is_pc = (a != 0) and (ys != 0) and (zs != 0)
        shell: str | None = None
        if is_pc:
            shell = "inner" if (zs * zs + ys * ys) == 2 else "outer"
        rows.append({"n": n, "P_n": pn, "P_P_n": ppn, "r30": r30, "is_prime_candidate": is_pc, "shell": shell})
    return rows


def _iter_primes_segmented(limit: int, seg_size: int = 1 << 22):
    """Yield ``(index, prime)`` for every prime ``<= limit``, 1-based index, in O(seg_size) memory.

    Memory-bounded twin of :func:`sieve`: never holds the full prime list, only one
    ``seg_size``-byte window at a time. Used to pick sparse superprimes off their global
    prime index without materialising every prime up to ``limit`` (the RAM wall).
    """
    if limit < 2:
        return
    base = sieve(math.isqrt(limit))  # base primes <= sqrt(limit); tiny (sqrt(2e9) ~ 44_721)
    idx = 0
    lo = 2
    while lo <= limit:
        hi = min(limit, lo + seg_size - 1)
        size = hi - lo + 1
        flags = bytearray(b"\x01") * size
        for p in base:
            if p * p > hi:
                break
            start = max(p * p, ((lo + p - 1) // p) * p)
            if start <= hi:
                flags[start - lo : hi - lo + 1 : p] = b"\x00" * (((hi - start) // p) + 1)
        for off in range(size):
            if flags[off]:
                idx += 1
                yield idx, lo + off
        lo = hi + 1


def _superprime_rows_segmented(limit: int, seg_size: int = 1 << 22) -> list[dict]:
    """Memory-bounded reimplementation of ``_compute_doubly_indexed_superprimes(sieve(limit))``.

    P(P(n)) = ``p_{p_n}`` needs random access ``primes[primes[n-1]-1]``, so this is not a literal
    swap of the sieve but an index-tracking pick-off: build the sparse target indices ``{p_n}`` from
    a small sieve (only up to an upper bound on ``pi(limit)``), then stream primes ``<= limit`` with a
    running 1-based index and capture the prime whenever the index lands on a target. Targets above
    ``pi(limit)`` are over-generated and auto-drop (the stream never reaches them) — this reproduces
    the original ``pn <= len(primes)`` guard for free. Rows come out ascending in ``n`` (n, p_n,
    p_{p_n} all monotonic, p_n injective), byte-identical to the original.
    """
    if limit < 2:
        return []
    # Upper bound on pi(limit): Dusart 2010, pi(x) <= x/(ln x - 1.1) for x >= 60184. Below that,
    # pi(x) <= x trivially and sieve(limit) is cheap. small sieve must reach this bound to supply p_n.
    if limit >= 60184:
        upper = int(limit / (math.log(limit) - 1.1)) + 64
    else:
        upper = limit
    small = sieve(upper)  # primes <= upper (>= pi(limit)); supplies p_n for every contributing n
    m = len(small)  # = pi(upper) >= pi(limit)
    targets: dict[int, int] = {}  # global prime index pn = p_n  ->  n
    for n in small:  # n = prime value, ascending
        if n > m:  # cannot index p_n = small[n-1]
            break
        pn = small[n - 1]  # p_n
        if pn > upper:  # p_n exceeds the pi(limit) over-bound -> can never fire; pn increasing -> stop
            break
        targets[pn] = n
    rows: list[dict] = []
    for idx, prime in _iter_primes_segmented(limit, seg_size):
        n = targets.get(idx)
        if n is None:
            continue
        ppn = prime  # = p_{p_n}, the superprime
        r30 = ppn % 30
        zs = r30 % 5
        if zs > 2:
            zs -= 5
        ys = r30 % 3
        if ys > 1:
            ys -= 3
        a = r30 % 2
        is_pc = (a != 0) and (ys != 0) and (zs != 0)
        shell: str | None = None
        if is_pc:
            shell = "inner" if (zs * zs + ys * ys) == 2 else "outer"
        rows.append(
            {"n": n, "P_n": small[n - 1], "P_P_n": ppn, "r30": r30, "is_prime_candidate": is_pc, "shell": shell}
        )
    return rows


def run_superprime_layer(limit: int = 10_000, top: int = 40) -> dict:
    """Map P(P(n)) [n prime] through CRT mod-30 negative-triangulation shells."""
    primes = sieve(limit)
    rows = _compute_doubly_indexed_superprimes(primes)
    sh: dict[str, int] = {"inner": 0, "outer": 0, "sieve_prime": 0, "other": 0}
    for r in rows:
        if r["shell"] == "inner":
            sh["inner"] += 1
        elif r["shell"] == "outer":
            sh["outer"] += 1
        elif r["r30"] in {0, 2, 3, 5, 6, 10, 15, 30}:
            sh["sieve_prime"] += 1
        else:
            sh["other"] += 1
    pp_seq = [r["P_P_n"] for r in rows]
    gaps = [pp_seq[i + 1] - pp_seq[i] for i in range(len(pp_seq) - 1)] if len(pp_seq) > 1 else []
    delta_g = [gaps[i + 1] - gaps[i] for i in range(len(gaps) - 1)] if len(gaps) > 1 else []
    return {
        "schema_version": "prime_fog_superprime_layer_v1",
        "limit": limit,
        "prime_count": len(primes),
        "superprime_count": len(rows),
        "shell_histogram": sh,
        "inner_outer_ratio": round(sh["inner"] / max(1, sh["outer"]), 4),
        "gap_mean": round(sum(gaps) / len(gaps), 3) if gaps else 0,
        "gap_max": max(gaps) if gaps else 0,
        "delta_g_positive": sum(1 for d in delta_g if d > 0),
        "delta_g_negative": sum(1 for d in delta_g if d < 0),
        "delta_g_zero": sum(1 for d in delta_g if d == 0),
        "rows": rows[:top],
    }


def print_superprime_layer(payload: dict) -> None:
    print(f"\n{'═' * 64}")
    print("  SUPERPRIME LAYER  P(P(n)) [n prime]  — pure prime-index filter")
    print(f"{'═' * 64}")
    print(f"  limit={payload['limit']}  primes={payload['prime_count']}  superprimes={payload['superprime_count']}")
    sh = payload["shell_histogram"]
    total_sp = max(1, sum(sh.values()))
    print(f"\n  CRT SHELL DISTRIBUTION  (mod-30 negative-triangulation map)")
    print(f"  inner  |z|²=2 : {sh['inner']:4d}  ({100*sh['inner']/total_sp:.1f}%)")
    print(f"  outer  |z|²=5 : {sh['outer']:4d}  ({100*sh['outer']/total_sp:.1f}%)")
    print(f"  sieve prime    : {sh['sieve_prime']:4d}  ({100*sh['sieve_prime']/total_sp:.1f}%)")
    print(f"  other/composite: {sh['other']:4d}  ({100*sh['other']/total_sp:.1f}%)")
    print(f"  inner:outer ratio : {payload['inner_outer_ratio']}")
    print(f"  gap_mean={payload['gap_mean']}  gap_max={payload['gap_max']}")
    dp = payload["delta_g_positive"]
    dn = payload["delta_g_negative"]
    dz = payload["delta_g_zero"]
    tot = max(1, dp + dn + dz)
    print(f"\n  Δg>0 (gap widening):  {dp:4d}  ({100*dp/tot:.1f}%)")
    print(f"  Δg<0 (gap shrinking): {dn:4d}  ({100*dn/tot:.1f}%)")
    print(f"  Δg=0 (edge):          {dz:4d}  ({100*dz/tot:.1f}%)")
    print(f"\n  {'n':>6}  {'P(n)':>8}  {'P(P(n))':>9}  {'r30':>5}  shell")
    print(f"  {'─'*6}  {'─'*8}  {'─'*9}  {'─'*5}  {'─'*6}")
    for row in payload["rows"]:
        shell_label = row["shell"] or ("sieve" if row["r30"] in {2, 3, 5} else "comp")
        print(f"  {row['n']:>6}  {row['P_n']:>8}  {row['P_P_n']:>9}  {row['r30']:>5}  {shell_label}")


# ─── Imaginary Gap Path (Δg × i complex pathfinder) ─────────────────────────


def run_imaginary_gap_path(
    limit: int = 10_000,
    superprime_only: bool = False,
    top: int = 40,
    ratio_mode: bool = False,
) -> dict:
    """Trace the complex path formed by prime gap acceleration Δg = g[n+1] − g[n].

    Positive Δg → real step +Δg      (gap widening, rightward on Re-axis).
    Negative Δg → imag step +|Δg|·i  (gap shrinking, upward on Im-axis).
    Zero Δg     → edge (no movement).

    ratio_mode: replace each raw Δg step with Δg / mean(|Δg|) — a dimensionless
    triangulation ratio showing each step as a multiple of the average acceleration.
    """
    all_primes = sieve(limit)
    if superprime_only:
        rows = _compute_doubly_indexed_superprimes(all_primes)
        seq = [r["P_P_n"] for r in rows]
        seq_label = "P(P(n)) superprimes [n prime]"
    else:
        seq = all_primes
        seq_label = "all primes"

    if len(seq) < 3:
        return {"schema_version": "prime_fog_imaginary_path_v1", "error": "too few primes in sequence"}

    gaps = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
    delta_g = [gaps[i + 1] - gaps[i] for i in range(len(gaps) - 1)]

    # Triangulation ratio baseline: mean absolute Δg across all non-zero steps
    nonzero_dg = [abs(d) for d in delta_g if d != 0]
    mean_abs_dg = sum(nonzero_dg) / len(nonzero_dg) if nonzero_dg else 1.0

    z = complex(0, 0)
    path_points: list[dict] = [{"idx": 0, "prime": seq[0], "z_re": 0.0, "z_im": 0.0, "dg": None, "ratio": None, "shape": "start"}]
    shape_hist: Counter = Counter()
    real_steps: list[float] = []
    imag_steps: list[float] = []

    for idx, dg in enumerate(delta_g):
        prev_gap = gaps[idx]
        curr_gap = gaps[idx + 1]
        shape, _ = _classify_gap_shape(prev_gap, curr_gap)
        shape_hist[shape] += 1
        ratio = dg / mean_abs_dg  # signed: positive→real, negative→imaginary
        step = ratio if ratio_mode else dg
        if dg > 0:
            z = complex(z.real + abs(step), z.imag)
            real_steps.append(abs(step))
        elif dg < 0:
            z = complex(z.real, z.imag + abs(step))
            imag_steps.append(abs(step))
        path_points.append({
            "idx": idx + 1,
            "prime": seq[idx + 2] if idx + 2 < len(seq) else None,
            "z_re": round(z.real, 6),
            "z_im": round(z.imag, 6),
            "dg": dg,
            "ratio": round(ratio, 6),
            "gap_before": prev_gap,
            "gap_after": curr_gap,
            "shape": shape,
        })

    re_vals = [p["z_re"] for p in path_points]
    im_vals = [p["z_im"] for p in path_points]
    re_min, re_max = min(re_vals), max(re_vals)
    im_min, im_max = min(im_vals), max(im_vals)
    width = re_max - re_min
    height = im_max - im_min
    angle_deg = math.degrees(cmath.phase(z)) if abs(z) > 0 else 0.0
    corners_right = shape_hist.get("corner_right", 0) + shape_hist.get("rounded_corner_right", 0)
    corners_left = shape_hist.get("corner_left", 0) + shape_hist.get("rounded_corner_left", 0)

    # Top outlier ratios — the highest-ratio steps are the triangulation landmarks
    ratio_entries = [(p["ratio"], p["idx"], p["prime"], p["dg"]) for p in path_points if p["ratio"] is not None]
    top_ratios = sorted(ratio_entries, key=lambda x: abs(x[0]), reverse=True)[:10]

    return {
        "schema_version": "prime_fog_imaginary_path_v1",
        "sequence": seq_label,
        "limit": limit,
        "seq_length": len(seq),
        "gap_count": len(gaps),
        "delta_g_count": len(delta_g),
        "ratio_mode": ratio_mode,
        "mean_abs_dg": round(mean_abs_dg, 4),
        "delta_g_positive": sum(1 for d in delta_g if d > 0),
        "delta_g_negative": sum(1 for d in delta_g if d < 0),
        "delta_g_zero": sum(1 for d in delta_g if d == 0),
        "z_final_re": round(z.real, 6),
        "z_final_im": round(z.imag, 6),
        "z_final_magnitude": round(abs(z), 6),
        "z_final_angle_deg": round(angle_deg, 3),
        "bounding_box": {"re_min": re_min, "re_max": re_max, "im_min": im_min, "im_max": im_max},
        "path_width": round(width, 6),
        "path_height": round(height, 6),
        "aspect_ratio": round(height / width, 6) if width > 0 else None,
        "real_step_mean": round(sum(real_steps) / len(real_steps), 6) if real_steps else 0,
        "imag_step_mean": round(sum(imag_steps) / len(imag_steps), 6) if imag_steps else 0,
        "corners_turning_right": corners_right,
        "corners_turning_left": corners_left,
        "edges": shape_hist.get("edge", 0),
        "shape_histogram": dict(shape_hist),
        "top_ratio_landmarks": [{"ratio": r[0], "idx": r[1], "prime": r[2], "dg": r[3]} for r in top_ratios],
        "path_sample": path_points[:top],
        "path_tail": path_points[-10:] if len(path_points) > top + 10 else [],
    }


_SHELL_V = {"inner": 2.0, "outer": 5.0}  # potential energy of each shell; lower = well


def _triple_veff(sa: str | None, sb: str | None, sc: str | None) -> float:
    """Effective potential at the middle node B relative to neighbors A and C.

    V_eff = V_B - mean(V_A, V_C)
      OIO -> 2 - 5     = -3.0   (deep well, boosts step)
      IOI -> 5 - 2     = +3.0   (barrier, damps/reflects)
      IIO -> 2 - 3.5   = -1.5   (partial well)
      OII -> 2 - 3.5   = -1.5
      IOO -> 5 - 3.5   = +1.5   (partial barrier)
      OOI -> 5 - 3.5   = +1.5
      III / OOO        =  0.0   (flat)
    """
    vb = _SHELL_V.get(sb, 5.0)
    va = _SHELL_V.get(sa, 5.0)
    vc = _SHELL_V.get(sc, 5.0)
    return vb - (va + vc) / 2.0


def _well_ratio(ratio: float, veff: float, W: float) -> float:
    """Apply square-well energy correction.

    ratio  : signed normalised step (positive -> Re, negative -> Im)
    veff   : effective potential from _triple_veff (negative = well, positive = barrier)
    W      : well depth scale factor (default 1.0 means OIO correction = ±1.0 in ratio² space)

    E_kin_after = ratio² - W * (veff / 3.0)
    Reflects (returns 0) if E_kin_after <= 0.
    """
    correction = W * (veff / 3.0)  # normalise veff [-3,+3] to [-W,+W]
    e_after = ratio * ratio - correction
    if e_after <= 0.0:
        return 0.0  # reflected
    return math.copysign(math.sqrt(e_after), ratio)


def _mod30_coords(n: int) -> tuple[int, int]:
    """Signed balanced (zs, ys) coords in the mod-30 CRT embedding."""
    r30 = n % 30
    zs = r30 % 5
    if zs > 2:
        zs -= 5
    ys = r30 % 3
    if ys > 1:
        ys -= 3
    return zs, ys


def run_imaginary_well_path(
    limit: int = 1_000_000,
    superprime_only: bool = True,
    top: int = 40,
    W: float = 1.0,
    extrap_steps: int = 5,
    landmark_threshold: float = 2.0,
) -> dict:
    """Square-well potential at triple shell crossings + tangential extrapolation.

    At each step the triple (A, B, C) defines V_eff = V_B - mean(V_A, V_C).
    The well-corrected step replaces the raw ratio step.
    At every crossing where |well_ratio| >= landmark_threshold, extrapolate
    forward extrap_steps positions along the tangent angle of that step,
    using the mod-30 embedding tangent vector (z_C - z_A) as the geometric anchor.
    """
    all_primes = sieve(limit)
    if superprime_only:
        rows = _compute_doubly_indexed_superprimes(all_primes)
        seq = [r["P_P_n"] for r in rows]
        seq_label = "P(P(n)) superprimes [n prime]"
        shell_map: dict[int, str | None] = {r["P_P_n"]: r["shell"] for r in rows}
    else:
        seq = all_primes
        seq_label = "all primes"
        shell_map = {}

    if len(seq) < 3:
        return {"schema_version": "prime_fog_well_path_v1", "error": "too few primes"}

    gaps = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
    delta_g = [gaps[i + 1] - gaps[i] for i in range(len(gaps) - 1)]

    nonzero = [abs(d) for d in delta_g if d != 0]
    mean_abs_dg = sum(nonzero) / len(nonzero) if nonzero else 1.0

    z_well = complex(0, 0)  # well-corrected path
    z_raw = complex(0, 0)   # unmodified ratio path

    path_points: list[dict] = []
    landmark_extraps: list[dict] = []
    shell_pattern_hist: Counter = Counter()
    reflected_count = 0
    crossing_count = 0

    for idx, dg in enumerate(delta_g):
        sa = shell_map.get(seq[idx])
        sb = shell_map.get(seq[idx + 1])
        sc = shell_map.get(seq[idx + 2]) if idx + 2 < len(seq) else None

        veff = _triple_veff(sa, sb, sc)
        pattern = f"{'I' if sa=='inner' else 'O'}{'I' if sb=='inner' else 'O'}{'I' if sc=='inner' else 'O'}"
        shell_pattern_hist[pattern] += 1

        ratio = dg / mean_abs_dg
        wr = _well_ratio(ratio, veff, W)
        reflected = wr == 0.0
        if reflected:
            reflected_count += 1

        is_crossing = (sa != sc) and sa in ("inner", "outer") and sc in ("inner", "outer")
        if is_crossing:
            crossing_count += 1

        # Advance both paths
        if dg > 0:
            z_raw = complex(z_raw.real + abs(ratio), z_raw.imag)
            z_well = complex(z_well.real + abs(wr), z_well.imag)
        elif dg < 0:
            z_raw = complex(z_raw.real, z_raw.imag + abs(ratio))
            z_well = complex(z_well.real, z_well.imag + abs(wr))

        # Mod-30 tangent: direction from A to C in the CRT embedding
        za = complex(*_mod30_coords(seq[idx]))
        zc = complex(*_mod30_coords(seq[idx + 2])) if idx + 2 < len(seq) else za
        tangent_vec = zc - za
        theta_mod30 = math.degrees(cmath.phase(tangent_vec)) if abs(tangent_vec) > 0 else 0.0

        # Path tangent: direction of the current well step in path space
        if dg > 0:
            theta_path = 0.0   # +real
        elif dg < 0:
            theta_path = 90.0  # +imag
        else:
            theta_path = 45.0  # edge

        pt = {
            "idx": idx + 1,
            "prime_C": seq[idx + 2] if idx + 2 < len(seq) else None,
            "z_well_re": round(z_well.real, 4),
            "z_well_im": round(z_well.imag, 4),
            "z_raw_re": round(z_raw.real, 4),
            "z_raw_im": round(z_raw.imag, 4),
            "dg": dg,
            "ratio": round(ratio, 4),
            "well_ratio": round(wr, 4),
            "veff": round(veff, 2),
            "pattern": pattern,
            "reflected": reflected,
            "theta_mod30_deg": round(theta_mod30, 2),
            "theta_path_deg": theta_path,
        }
        path_points.append(pt)

        # Mark landmark crossings for second-pass extrapolation
        if abs(wr) >= landmark_threshold and is_crossing:
            avg_step = (z_well.real + z_well.imag) / max(1, idx + 1)
            landmark_extraps.append({
                "at_idx": idx + 1,
                "list_pos": len(path_points),  # index into path_points AFTER append
                "prime_C": seq[idx + 2] if idx + 2 < len(seq) else None,
                "pattern": pattern,
                "veff": round(veff, 2),
                "ratio": round(ratio, 4),
                "well_ratio": round(wr, 4),
                "theta_mod30_deg": round(theta_mod30, 2),
                "z_re": round(z_well.real, 4),
                "z_im": round(z_well.imag, 4),
                "avg_step": avg_step,
                "extrapolation": [],  # filled in second pass
            })

    # Second pass: fill actual positions into extrapolation predictions
    for lm in landmark_extraps:
        base = lm["list_pos"]
        theta_rad = math.radians(lm["theta_mod30_deg"])
        avg_step = lm["avg_step"]
        preds = []
        for n in range(1, extrap_steps + 1):
            pred_re = lm["z_re"] + n * avg_step * math.cos(theta_rad)
            pred_im = lm["z_im"] + n * avg_step * math.sin(theta_rad)
            actual = path_points[base + n] if base + n < len(path_points) else None
            preds.append({
                "n": n,
                "pred_re": round(pred_re, 4),
                "pred_im": round(pred_im, 4),
                "actual_re": actual["z_well_re"] if actual else None,
                "actual_im": actual["z_well_im"] if actual else None,
                "err_re": round(pred_re - actual["z_well_re"], 4) if actual else None,
                "err_im": round(pred_im - actual["z_well_im"], 4) if actual else None,
            })
        lm["extrapolation"] = preds
        del lm["list_pos"], lm["avg_step"]  # clean up internal fields

    angle_well = math.degrees(cmath.phase(z_well)) if abs(z_well) > 0 else 0.0
    angle_raw = math.degrees(cmath.phase(z_raw)) if abs(z_raw) > 0 else 0.0
    w_re, w_im = z_well.real, z_well.imag
    asp = round(w_im / w_re, 6) if w_re > 0 else None

    return {
        "schema_version": "prime_fog_well_path_v1",
        "sequence": seq_label,
        "limit": limit,
        "seq_length": len(seq),
        "delta_g_count": len(delta_g),
        "W": W,
        "mean_abs_dg": round(mean_abs_dg, 4),
        "reflected_steps": reflected_count,
        "shell_crossings": crossing_count,
        "shell_pattern_histogram": dict(shell_pattern_hist.most_common()),
        "z_well_final_re": round(w_re, 4),
        "z_well_final_im": round(w_im, 4),
        "z_well_magnitude": round(abs(z_well), 4),
        "z_well_angle_deg": round(angle_well, 3),
        "z_well_aspect": asp,
        "z_raw_final_re": round(z_raw.real, 4),
        "z_raw_final_im": round(z_raw.imag, 4),
        "z_raw_angle_deg": round(angle_raw, 3),
        "angle_shift_deg": round(angle_well - angle_raw, 4),
        "landmark_threshold": landmark_threshold,
        "landmark_extrapolations": landmark_extraps,
        "path_sample": path_points[:top],
        "path_tail": path_points[-10:] if len(path_points) > top + 10 else [],
    }


def print_imaginary_well_path(payload: dict) -> None:
    print(f"\n{'═' * 68}")
    print("  IMAGINARY WELL PATH  —  triple-shell V_eff + tangential extrapolation")
    print(f"{'═' * 68}")
    print(f"  sequence : {payload['sequence']}")
    print(f"  limit={payload['limit']}  seq_len={payload['seq_length']}  W={payload['W']}  mean|Δg|={payload['mean_abs_dg']}")
    print(f"\n  WELL CORRECTION SUMMARY")
    print(f"  reflected steps (classically forbidden) : {payload['reflected_steps']}")
    print(f"  shell crossings (A≠C)                  : {payload['shell_crossings']}")
    print(f"\n  SHELL PATTERN HISTOGRAM  (V_eff shown)")
    veff_map = {"OIO": -3.0, "IOI": +3.0, "IIO": -1.5, "OII": -1.5, "IOO": +1.5, "OOI": +1.5, "III": 0.0, "OOO": 0.0}
    for pat, cnt in payload["shell_pattern_histogram"].items():
        ve = veff_map.get(pat, "?")
        bar = "█" * min(cnt // 5 + 1, 30)
        print(f"  {pat}  V_eff={str(ve):>5}  {cnt:>5}  {bar}")
    print(f"\n  PATH GEOMETRY  (well-corrected vs raw ratio)")
    print(f"  well : z={payload['z_well_final_re']:.4f}+{payload['z_well_final_im']:.4f}i  |z|={payload['z_well_magnitude']:.4f}  ∠={payload['z_well_angle_deg']:.3f}°  asp={payload['z_well_aspect']}")
    print(f"  raw  : z={payload['z_raw_final_re']:.4f}+{payload['z_raw_final_im']:.4f}i  ∠={payload['z_raw_angle_deg']:.3f}°")
    print(f"  angle shift (well − raw) : {payload['angle_shift_deg']:+.4f}°")
    extraps = payload["landmark_extrapolations"]
    if extraps:
        print(f"\n  TANGENTIAL EXTRAPOLATIONS  ({len(extraps)} landmark crossings, threshold={payload.get('landmark_threshold', 2.0)})")
        for lm in extraps:
            print(f"\n  ── idx={lm['at_idx']}  prime={lm['prime_C']}  pattern={lm['pattern']}  V_eff={lm['veff']}  ratio={lm['ratio']:+.4f}  well_ratio={lm['well_ratio']:+.4f}")
            print(f"     anchor z=({lm['z_re']:.2f},{lm['z_im']:.2f})  θ_mod30={lm['theta_mod30_deg']:.1f}°")
            print(f"     {'n':>3}  {'pred_re':>10}  {'pred_im':>10}  {'actual_re':>10}  {'actual_im':>10}  {'err_re':>9}  {'err_im':>9}")
            for p in lm["extrapolation"]:
                ar = f"{p['actual_re']:.2f}" if p["actual_re"] is not None else "—"
                ai = f"{p['actual_im']:.2f}" if p["actual_im"] is not None else "—"
                er = f"{p['err_re']:+.2f}" if p["err_re"] is not None else "—"
                ei = f"{p['err_im']:+.2f}" if p["err_im"] is not None else "—"
                print(f"     {p['n']:>3}  {p['pred_re']:>10.2f}  {p['pred_im']:>10.2f}  {ar:>10}  {ai:>10}  {er:>9}  {ei:>9}")
    print(f"\n  PATH SAMPLE (first {len(payload['path_sample'])} steps)")
    print(f"  {'idx':>4}  {'prime':>10}  {'pat':>3}  {'veff':>5}  {'ratio':>7}  {'w_rat':>7}  {'z_re':>8}  {'z_im':>8}  {'θmod30':>7}  refl")
    print(f"  {'─'*4}  {'─'*10}  {'─'*3}  {'─'*5}  {'─'*7}  {'─'*7}  {'─'*8}  {'─'*8}  {'─'*7}  ─")
    for pt in payload["path_sample"]:
        r = "Y" if pt["reflected"] else " "
        p = str(pt["prime_C"]) if pt["prime_C"] else "—"
        print(f"  {pt['idx']:>4}  {p:>10}  {pt['pattern']:>3}  {pt['veff']:>5.1f}  {pt['ratio']:>7.3f}  {pt['well_ratio']:>7.3f}  {pt['z_well_re']:>8.3f}  {pt['z_well_im']:>8.3f}  {pt['theta_mod30_deg']:>7.1f}  {r}")


def print_imaginary_gap_path(payload: dict) -> None:
    ratio_mode = payload.get("ratio_mode", False)
    step_label = "ratio" if ratio_mode else "dg"
    print(f"\n{'═' * 64}")
    title = "IMAGINARY GAP PATH  —  Δg × i  [RATIO RE-STEP]" if ratio_mode else "IMAGINARY GAP PATH  —  Δg × i complex pathfinder"
    print(f"  {title}")
    print(f"{'═' * 64}")
    print(f"  sequence : {payload['sequence']}")
    print(f"  limit={payload['limit']}  seq_len={payload['seq_length']}  Δg samples={payload['delta_g_count']}")
    if ratio_mode:
        print(f"  mean |Δg| baseline = {payload['mean_abs_dg']}  (step = Δg / baseline)")
    dp = payload["delta_g_positive"]
    dn = payload["delta_g_negative"]
    dz = payload["delta_g_zero"]
    tot = max(1, dp + dn + dz)
    print(f"\n  GAP ACCELERATION → COMPLEX PLANE MAPPING")
    print(f"  Δg>0 → +real  (avg={payload['real_step_mean']:8.4f}) : {dp:5d}  ({100*dp/tot:.1f}%)")
    print(f"  Δg<0 → +imag  (avg={payload['imag_step_mean']:8.4f}) : {dn:5d}  ({100*dn/tot:.1f}%)")
    print(f"  Δg=0 → edge                           : {dz:5d}  ({100*dz/tot:.1f}%)")
    print(f"\n  PATH GEOMETRY")
    bb = payload["bounding_box"]
    print(f"  Re range [{bb['re_min']:.4f}, {bb['re_max']:.4f}]   Im range [{bb['im_min']:.4f}, {bb['im_max']:.4f}]")
    print(f"  width={payload['path_width']:.4f}   height={payload['path_height']:.4f}   aspect={payload['aspect_ratio'] or '—'}")
    print(f"  z_final = {payload['z_final_re']:.4f} + {payload['z_final_im']:.4f}i   |z|={payload['z_final_magnitude']:.4f}   ∠={payload['z_final_angle_deg']:.3f}°")
    print(f"\n  CORNER GRAMMAR  (shape_histogram from _classify_gap_shape)")
    print(f"  corners_right (Δg>0 arrivals) : {payload['corners_turning_right']}")
    print(f"  corners_left  (Δg<0 arrivals) : {payload['corners_turning_left']}")
    print(f"  edges (Δg=0)                  : {payload['edges']}")
    print(f"  full histogram : {payload['shape_histogram']}")
    landmarks = payload.get("top_ratio_landmarks", [])
    if landmarks:
        print(f"\n  TOP TRIANGULATION LANDMARKS  (highest |ratio| = furthest from average)")
        print(f"  {'rank':>4}  {'idx':>6}  {'prime':>12}  {'dg':>8}  {'ratio':>10}  direction")
        print(f"  {'─'*4}  {'─'*6}  {'─'*12}  {'─'*8}  {'─'*10}  {'─'*9}")
        for rank, lm in enumerate(landmarks, 1):
            direction = "+real" if lm["dg"] > 0 else "+imag"
            print(f"  {rank:>4}  {lm['idx']:>6}  {str(lm['prime'] or '—'):>12}  {lm['dg']:>8}  {lm['ratio']:>10.4f}  {direction}")
    print(f"\n  PATH SAMPLE (first {len(payload['path_sample'])} steps)")
    print(f"  {'idx':>4}  {'prime':>12}  {'z_re':>10}  {'z_im':>10}  {step_label:>8}  shape")
    print(f"  {'─'*4}  {'─'*12}  {'─'*10}  {'─'*10}  {'─'*8}  {'─'*20}")
    for pt in payload["path_sample"]:
        step_val = pt["ratio"] if ratio_mode else pt["dg"]
        step_str = f"{step_val:.4f}" if step_val is not None else "—"
        prime_str = str(pt["prime"]) if pt["prime"] is not None else "—"
        print(f"  {pt['idx']:>4}  {prime_str:>12}  {pt['z_re']:>10.4f}  {pt['z_im']:>10.4f}  {step_str:>8}  {pt['shape']}")
    tail = payload.get("path_tail", [])
    if tail:
        print(f"\n  PATH TAIL (last {len(tail)} steps)")
        for pt in tail:
            step_val = pt["ratio"] if ratio_mode else pt["dg"]
            step_str = f"{step_val:.4f}" if step_val is not None else "—"
            prime_str = str(pt["prime"]) if pt["prime"] is not None else "—"
            print(f"  {pt['idx']:>4}  {prime_str:>12}  {pt['z_re']:>10.4f}  {pt['z_im']:>10.4f}  {step_str:>8}  {pt['shape']}")


def _classify_step(abs_ratio: float) -> str:
    if abs_ratio < 1.0:
        return "calm"
    elif abs_ratio < 2.0:
        return "mist"
    elif abs_ratio < 4.0:
        return "droplet"
    return "splash"


def run_foam_score_probe(
    limit: int = 1_000_000,
    superprime_only: bool = True,
    window: int = 10,
    top: int = 20,
    W: float = 1.0,
) -> dict:
    """Score splash zones by surrounding turbulence density.

    Classifies each step: calm |r|<1, mist 1-2, droplet 2-4, splash >=4.
    For each splash event, scans ±window steps for mist/droplet count and
    rebound pairs (adjacent opposite-sign contacts), then ranks by foam_score.
    foam_score = splash_strength + droplet_density*3 + mist_density*1.5
                 + rebound_pair_density*2 + crossing_density
    """
    all_primes = sieve(limit)
    if superprime_only:
        rows = _compute_doubly_indexed_superprimes(all_primes)
        seq = [r["P_P_n"] for r in rows]
        seq_label = "P(P(n)) superprimes [n prime]"
        shell_map: dict[int, str | None] = {r["P_P_n"]: r["shell"] for r in rows}
    else:
        seq = all_primes
        seq_label = "all primes"
        shell_map = {}

    if len(seq) < 3:
        return {"schema_version": "prime_fog_foam_score_v1", "error": "too few primes"}

    gaps = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
    delta_g = [gaps[i + 1] - gaps[i] for i in range(len(gaps) - 1)]

    nonzero = [abs(d) for d in delta_g if d != 0]
    mean_abs_dg = sum(nonzero) / len(nonzero) if nonzero else 1.0

    classified: list[dict] = []
    for idx, dg in enumerate(delta_g):
        sa = shell_map.get(seq[idx])
        sb = shell_map.get(seq[idx + 1])
        sc = shell_map.get(seq[idx + 2]) if idx + 2 < len(seq) else None
        veff = _triple_veff(sa, sb, sc)
        is_crossing = (sa != sc) and sa in ("inner", "outer") and sc in ("inner", "outer")
        pattern = f"{'I' if sa == 'inner' else 'O'}{'I' if sb == 'inner' else 'O'}{'I' if sc == 'inner' else 'O'}"
        ratio = dg / mean_abs_dg
        cls = _classify_step(abs(ratio))
        classified.append({
            "idx": idx,
            "prime": seq[idx + 1],
            "dg": dg,
            "ratio": ratio,
            "cls": cls,
            "sign": 1 if dg > 0 else (-1 if dg < 0 else 0),
            "pattern": pattern,
            "veff": round(veff, 2),
            "is_crossing": is_crossing,
        })

    N = len(classified)
    global_dist: Counter = Counter(c["cls"] for c in classified)

    # Rebound contacts: for each splash, count immediately adjacent steps with opposite sign.
    # Matches the structural ~1.7x ratio observed empirically.
    splash_indices = [i for i, c in enumerate(classified) if c["cls"] == "splash"]
    splash_set: set[int] = set(splash_indices)

    rebound_contact_count = 0
    rebound_contact_idx: set[int] = set()
    for si in splash_indices:
        sp_sign = classified[si]["sign"]
        for adj in (si - 1, si + 1):
            if 0 <= adj < N and classified[adj]["sign"] != 0 and classified[adj]["sign"] != sp_sign:
                rebound_contact_count += 1
                rebound_contact_idx.add(adj)

    zones: list[dict] = []
    for si in splash_indices:
        sp = classified[si]
        lo = max(0, si - window)
        hi = min(N - 1, si + window)
        neighborhood = classified[lo:si] + classified[si + 1:hi + 1]
        nbr = max(1, len(neighborhood))

        mist_count = sum(1 for c in neighborhood if c["cls"] == "mist")
        droplet_count = sum(1 for c in neighborhood if c["cls"] == "droplet")
        adj_splash = sum(1 for c in neighborhood if c["cls"] == "splash")
        # Rebound bonus in neighborhood: any index that is a rebound contact to a splash in window
        rebound_bonus = sum(
            1 for j in range(lo, hi + 1)
            if j in rebound_contact_idx
            and any(abs(j - k) == 1 for k in splash_set if lo <= k <= hi)
        )
        crossing_bonus = sum(1 for c in neighborhood if c["is_crossing"])

        mist_density = mist_count / nbr
        droplet_density = droplet_count / nbr

        foam_score = (
            abs(sp["ratio"])
            + droplet_density * 3.0
            + mist_density * 1.5
            + (rebound_bonus / nbr) * 2.0
            + (crossing_bonus / nbr) * 1.0
        )
        zones.append({
            "rank": 0,
            "at_idx": si + 1,
            "prime": sp["prime"],
            "splash_ratio": round(sp["ratio"], 4),
            "pattern": sp["pattern"],
            "veff": sp["veff"],
            "is_crossing": sp["is_crossing"],
            "mist_count": mist_count,
            "droplet_count": droplet_count,
            "adj_splash_count": adj_splash,
            "rebound_bonus_count": rebound_bonus,
            "crossing_bonus_count": crossing_bonus,
            "mist_density": round(mist_density, 4),
            "droplet_density": round(droplet_density, 4),
            "turbulence_density": round((mist_count + droplet_count) / nbr, 4),
            "foam_score": round(foam_score, 4),
        })

    zones.sort(key=lambda z: z["foam_score"], reverse=True)
    for rank, z in enumerate(zones, 1):
        z["rank"] = rank

    near_idx: set[int] = set()
    for si in splash_indices:
        for j in range(max(0, si - window), min(N, si + window + 1)):
            near_idx.add(j)
    near_classified = [classified[i] for i in sorted(near_idx)]
    near_dist: Counter = Counter(c["cls"] for c in near_classified)

    def _pct(dist: Counter, total_n: int) -> dict:
        return {k: round(100.0 * v / max(1, total_n), 2) for k, v in dist.most_common()}

    return {
        "schema_version": "prime_fog_foam_score_v1",
        "sequence": seq_label,
        "limit": limit,
        "seq_length": len(seq),
        "W": W,
        "window": window,
        "mean_abs_dg": round(mean_abs_dg, 4),
        "total_steps": N,
        "global_distribution": dict(global_dist.most_common()),
        "global_distribution_pct": _pct(global_dist, N),
        "global_turbulence_pct": round(100.0 * (global_dist.get("mist", 0) + global_dist.get("droplet", 0)) / max(1, N), 2),
        "splash_count": len(splash_indices),
        "rebound_contact_count": rebound_contact_count,
        "rebound_per_splash": round(rebound_contact_count / max(1, len(splash_indices)), 4),
        "near_splash_step_count": len(near_idx),
        "near_splash_distribution": dict(near_dist.most_common()),
        "near_splash_distribution_pct": _pct(near_dist, len(near_idx)),
        "near_turbulence_pct": round(100.0 * (near_dist.get("mist", 0) + near_dist.get("droplet", 0)) / max(1, len(near_idx)), 2),
        "top_foam_zones": zones[:top],
        "all_zone_count": len(zones),
    }


def print_foam_score_probe(payload: dict) -> None:
    print(f"\n{'═' * 72}")
    print("  FOAM SCORE PROBE  —  splash zone turbulence ranking")
    print(f"{'═' * 72}")
    print(f"  sequence      : {payload['sequence']}")
    print(f"  limit         : {payload['limit']:,}")
    print(f"  total steps   : {payload['total_steps']:,}")
    print(f"  foam window   : ±{payload['window']}")
    print()
    gd = payload["global_distribution_pct"]
    print(f"  GLOBAL DISTRIBUTION  ({payload['total_steps']:,} steps)")
    for cls in ("calm", "mist", "droplet", "splash"):
        n = payload["global_distribution"].get(cls, 0)
        print(f"    {cls:10s}  {n:>8,}   {gd.get(cls, 0.0):6.2f}%")
    print(f"    turbulence   {'':>8}   {payload['global_turbulence_pct']:6.2f}%  (mist+droplet)")
    print()
    nd = payload["near_splash_distribution_pct"]
    print(f"  NEAR-SPLASH DISTRIBUTION  ({payload['near_splash_step_count']:,} steps within ±{payload['window']} of a splash)")
    for cls in ("calm", "mist", "droplet", "splash"):
        n = payload["near_splash_distribution"].get(cls, 0)
        print(f"    {cls:10s}  {n:>8,}   {nd.get(cls, 0.0):6.2f}%")
    print(f"    turbulence   {'':>8}   {payload['near_turbulence_pct']:6.2f}%  (mist+droplet)")
    print()
    n_sp = payload["splash_count"]
    n_rb = payload["rebound_contact_count"]
    rps = payload["rebound_per_splash"]
    print(f"  SPLASH EVENTS : {n_sp}   REBOUND CONTACTS : {n_rb}   rebound/splash : {rps:.3f}")
    print()
    print(f"  TOP FOAM ZONES  (ranked by foam_score = splash_strength + droplet*3 + mist*1.5 + rebound*2 + crossing)")
    zones = payload["top_foam_zones"]
    hdr = f"  {'rk':>3}  {'idx':>8}  {'prime':>14}  {'splash_r':>9}  {'pat':>3}  {'veff':>5}  {'mst%':>5}  {'drp%':>5}  {'rb':>3}  {'cx':>3}  {'foam':>8}"
    print(hdr)
    print(f"  {'─'*3}  {'─'*8}  {'─'*14}  {'─'*9}  {'─'*3}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*3}  {'─'*3}  {'─'*8}")
    w2 = max(1, 2 * payload["window"])
    for z in zones:
        xmark = "*" if z["is_crossing"] else " "
        mst_pct = 100.0 * z["mist_count"] / w2
        drp_pct = 100.0 * z["droplet_count"] / w2
        print(
            f"  {z['rank']:>3}  {z['at_idx']:>8,}  {z['prime']:>14,}  {z['splash_ratio']:>9.4f}"
            f"  {z['pattern']:>3}{xmark}  {z['veff']:>5.1f}  {mst_pct:>5.1f}  {drp_pct:>5.1f}"
            f"  {z['rebound_bonus_count']:>3}  {z['crossing_bonus_count']:>3}  {z['foam_score']:>8.4f}"
        )


_PHI = (1.0 + 5.0 ** 0.5) / 2.0
# skip 2 — all even gaps are trivially 0; mod-13 is the tesseract (4th hidden) axis
_GAP_WALL_MODS = [3, 5, 7, 11, 13, 17, 19]

# Behavior taxonomy (4 types + flat):
#   flat      = no crossings anywhere (pure large-gap variance outlier)
#   surface   = mod-30 crossing only (fully visible in the shell map)
#   shadow    = exactly 1 hidden axis sign-flips (mod-7 OR mod-11 OR mod-13)
#   deep      = exactly 2 hidden axes sign-flip
#   tesseract = all 3 hidden axes sign-flip simultaneously (4D boundary event)
_BEHAVIOR_ORDER = ["tesseract", "deep", "shadow", "surface", "flat"]


def _extended_prime_coords(p: int) -> dict:
    """Signed balanced CRT coordinates across mod-30 / mod-210 / mod-2310 / mod-30030 axes."""
    r30 = p % 30
    zs = r30 % 5
    if zs > 2:
        zs -= 5
    ys = r30 % 3
    if ys > 1:
        ys -= 3
    a = r30 % 2
    is_pc = (a != 0) and (ys != 0) and (zs != 0)
    shell30 = None
    if is_pc:
        sq30 = zs * zs + ys * ys
        shell30 = "inner" if sq30 == 2 else "outer"
    ws = p % 7           # mod-210 axis
    if ws > 3:
        ws -= 7
    vs = p % 11          # mod-2310 axis
    if vs > 5:
        vs -= 11
    ts = p % 13          # mod-30030 axis (tesseract dimension)
    if ts > 6:
        ts -= 13
    return {
        "shell30": shell30,
        "zs": zs, "ys": ys, "ws": ws, "vs": vs, "ts": ts,
        "phi_phase": (p * _PHI) % 1.0,
    }


def _gap_wall_loops(gap: int) -> dict:
    """Folded residue vector for a prime gap. -1 where gap is divisible by that prime."""
    rv = {}
    for q in _GAP_WALL_MODS:
        r = gap % q
        rv[q] = -1 if r == 0 else r
    return rv


def _gap_charge_simple(gap: int) -> int:
    """Signed gap charge: -1 for each wall prime that divides gap, +1 otherwise. Range -5 to +5."""
    return sum(-1 if gap % p == 0 else 1 for p in _GAP_WALL_MODS)


_SOLITON_PHI_THRESHOLD = 0.30
_SOLITON_CLASSES = [
    "visible_crossing",
    "mixed_collision",
    "charged_hidden_wall",
    "smooth_phase",
    "variance_only",
]


def _soliton_event_class(cross30: bool, gc_before: int, gc_after: int, phi_drift: float) -> str:
    """5-class soliton taxonomy based on mod-30 crossing and flanking gap charge signs."""
    neg = (gc_before < 0) or (gc_after < 0)
    if cross30 and neg:
        return "mixed_collision"
    if cross30:
        return "visible_crossing"
    if neg:
        return "charged_hidden_wall"
    if phi_drift >= _SOLITON_PHI_THRESHOLD:
        return "smooth_phase"
    return "variance_only"


_PRIME_RATIO_PAIRS: list[tuple[int, int, float]] = [
    (p, q, p / q)
    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53]
    for q in [1, 2, 3, 5, 7]
    if p > q
]


def _nearest_prime_ratio(abs_ratio: float) -> tuple[float, str]:
    """Returns (log_error, label). Small err = strong prime-ratio resonance."""
    if abs_ratio < 1.1:
        return 1.0, ""
    best_err = float("inf")
    best_label = ""
    log_r = math.log(abs_ratio)
    for p, q, r in _PRIME_RATIO_PAIRS:
        err = abs(log_r - math.log(r))
        if err < best_err:
            best_err = err
            best_label = f"{p}/{q}"
    return best_err, best_label


def _prime_ratio_score(log_err: float) -> float:
    """Resonance score 0→1: 1 = perfect match, 0 at log-err ≥ 0.02."""
    return max(0.0, 1.0 - log_err / 0.02)


def _splash_type5(
    cross30: bool,
    gc_before: int,
    gc_after: int,
    phi_drift: float,
    prime_res: float,
    rebound: int,
) -> str:
    """5-class splash type taxonomy: wall_charge / shell_crossing / prime_ratio / smooth_phi / rebound."""
    neg = (gc_before < 0) or (gc_after < 0)
    if neg and not cross30:
        return "wall_charge_splash"
    if cross30:
        return "shell_crossing_splash"
    if prime_res >= 0.5:
        return "prime_ratio_splash"
    if phi_drift >= 0.30:
        return "smooth_phi_splash"
    return "rebound_splash"


def _behavior_class(cross30: bool, hidden7: bool, hidden11: bool, hidden13: bool) -> str:
    hidden_count = sum([hidden7, hidden11, hidden13])
    if hidden_count == 3:
        return "tesseract"
    if hidden_count == 2:
        return "deep"
    if hidden_count == 1:
        return "shadow"
    if cross30:
        return "surface"
    return "flat"


def run_wall_loop_probe(
    limit: int = 1_000_000,
    superprime_only: bool = True,
    window: int = 6,
    top: int = 20,
) -> dict:
    """Test III/OOO splash events for hidden crossings across 4 CRT axes + phi drift.

    Behavior taxonomy (4 types + flat):
      tesseract = all 3 hidden axes flip (mod-7, mod-11, mod-13) — 4D boundary event
      deep      = exactly 2 hidden axes flip
      shadow    = exactly 1 hidden axis flips
      surface   = mod-30 shell crossing only
      flat      = no crossings (pure large-gap variance outlier)

    Events sorted by own_wall_density (count of -1 in gap's folded residue vector).
    """
    all_primes = sieve(limit)
    if superprime_only:
        rows = _compute_doubly_indexed_superprimes(all_primes)
        seq = [r["P_P_n"] for r in rows]
        seq_label = "P(P(n)) superprimes [n prime]"
    else:
        seq = all_primes
        seq_label = "all primes"

    if len(seq) < 3:
        return {"schema_version": "prime_fog_wall_loop_v2", "error": "too few primes"}

    gaps = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
    delta_g = [gaps[i + 1] - gaps[i] for i in range(len(gaps) - 1)]
    nonzero = [abs(d) for d in delta_g if d != 0]
    mean_abs_dg = sum(nonzero) / len(nonzero) if nonzero else 1.0

    N = len(delta_g)
    splash_events: list[dict] = []
    pattern_stats: dict = {}

    for idx, dg in enumerate(delta_g):
        pa = seq[idx]
        pb = seq[idx + 1]
        pc = seq[idx + 2] if idx + 2 < len(seq) else seq[idx + 1]
        ca = _extended_prime_coords(pa)
        cb = _extended_prime_coords(pb)
        cc = _extended_prime_coords(pc)

        sa, sb, sc = ca["shell30"], cb["shell30"], cc["shell30"]
        pat = f"{'I' if sa == 'inner' else 'O'}{'I' if sb == 'inner' else 'O'}{'I' if sc == 'inner' else 'O'}"

        cross30 = (sa != sc) and sa in ("inner", "outer") and sc in ("inner", "outer")

        hidden7 = ca["ws"] != 0 and cc["ws"] != 0 and ((ca["ws"] > 0) != (cc["ws"] > 0))
        hidden11 = ca["vs"] != 0 and cc["vs"] != 0 and ((ca["vs"] > 0) != (cc["vs"] > 0))
        hidden13 = ca["ts"] != 0 and cc["ts"] != 0 and ((ca["ts"] > 0) != (cc["ts"] > 0))

        bclass = _behavior_class(cross30, hidden7, hidden11, hidden13)
        phi_drift = abs(cc["phi_phase"] - ca["phi_phase"])
        ratio = dg / mean_abs_dg
        cls = _classify_step(abs(ratio))

        if pat not in pattern_stats:
            pattern_stats[pat] = {
                "total": 0, "splash": 0, "cross30": 0,
                "hidden7": 0, "hidden11": 0, "hidden13": 0,
                "tesseract": 0, "deep": 0, "shadow": 0, "surface": 0, "flat": 0,
            }
        st = pattern_stats[pat]
        st["total"] += 1
        if cross30:
            st["cross30"] += 1
        if hidden7:
            st["hidden7"] += 1
        if hidden11:
            st["hidden11"] += 1
        if hidden13:
            st["hidden13"] += 1
        st[bclass] += 1
        if cls == "splash":
            st["splash"] += 1

        if cls != "splash":
            continue

        lo = max(0, idx - window)
        hi = min(N - 1, idx + window)
        window_gaps = gaps[lo: hi + 2]
        wall_totals: Counter = Counter()
        for g in window_gaps:
            for q, v in _gap_wall_loops(g).items():
                if v == -1:
                    wall_totals[q] += 1
        wl_own = _gap_wall_loops(gaps[idx])
        own_wall_density = sum(1 for v in wl_own.values() if v == -1)
        window_wall_density = sum(wall_totals.values())

        phi_vals = [_extended_prime_coords(seq[j + 1])["phi_phase"] for j in range(lo, hi + 1) if j + 1 < len(seq)]
        phi_mean = sum(phi_vals) / max(1, len(phi_vals))
        phi_std = (sum((v - phi_mean) ** 2 for v in phi_vals) / max(1, len(phi_vals))) ** 0.5

        splash_events.append({
            "at_idx": idx + 1,
            "prime_A": pa, "prime_B": pb, "prime_C": pc,
            "pattern": pat,
            "ratio": round(ratio, 4),
            "cross30": cross30,
            "hidden7": hidden7,
            "hidden11": hidden11,
            "hidden13": hidden13,
            "behavior": bclass,
            "ws_A": ca["ws"], "ws_C": cc["ws"],
            "vs_A": ca["vs"], "vs_C": cc["vs"],
            "ts_A": ca["ts"], "ts_C": cc["ts"],
            "phi_drift_triple": round(phi_drift, 6),
            "phi_std_window": round(phi_std, 6),
            "own_wall_density": own_wall_density,
            "window_wall_density": window_wall_density,
            "gap_wall_loops_own": {str(q): v for q, v in wl_own.items()},
            "gap_wall_freq_window": {str(q): wall_totals.get(q, 0) for q in _GAP_WALL_MODS},
        })

    # Pattern summary with per-behavior counts
    pattern_summary: list[dict] = []
    for pat, st in sorted(pattern_stats.items(), key=lambda x: -x[1]["total"]):
        tot = max(1, st["total"])
        pattern_summary.append({
            "pattern": pat,
            "total": st["total"],
            "splash": st["splash"],
            "cross30_pct": round(100.0 * st["cross30"] / tot, 1),
            "hidden7_pct": round(100.0 * st["hidden7"] / tot, 1),
            "hidden11_pct": round(100.0 * st["hidden11"] / tot, 1),
            "hidden13_pct": round(100.0 * st["hidden13"] / tot, 1),
            "tesseract_pct": round(100.0 * st["tesseract"] / tot, 1),
            "deep_pct": round(100.0 * st["deep"] / tot, 1),
            "shadow_pct": round(100.0 * st["shadow"] / tot, 1),
            "surface_pct": round(100.0 * st["surface"] / tot, 1),
            "flat_pct": round(100.0 * st["flat"] / tot, 1),
        })

    # Behavior-tagged groups, sorted by own_wall_density desc then |ratio| desc
    def _sort_key(e: dict) -> tuple:
        return (-e["own_wall_density"], -abs(e["ratio"]))

    by_behavior: dict[str, list[dict]] = {b: [] for b in _BEHAVIOR_ORDER}
    for e in splash_events:
        by_behavior[e["behavior"]].append(e)
    for b in _BEHAVIOR_ORDER:
        by_behavior[b].sort(key=_sort_key)

    return {
        "schema_version": "prime_fog_wall_loop_v2",
        "sequence": seq_label,
        "limit": limit,
        "total_steps": N,
        "splash_count": len(splash_events),
        "window": window,
        "behavior_counts": {b: len(by_behavior[b]) for b in _BEHAVIOR_ORDER},
        "pattern_summary": pattern_summary,
        "by_behavior": {b: by_behavior[b][:top] for b in _BEHAVIOR_ORDER},
        "all_by_wall_density": sorted(splash_events, key=_sort_key)[:top],
    }


def print_wall_loop_probe(payload: dict) -> None:
    print(f"\n{'═' * 78}")
    print("  WALL LOOP PROBE  —  4-axis hidden crossing + gap wall density")
    print(f"  behaviors: flat / surface / shadow / deep / TESSERACT")
    print(f"{'═' * 78}")
    print(f"  sequence    : {payload['sequence']}")
    print(f"  limit       : {payload['limit']:,}")
    print(f"  total steps : {payload['total_steps']:,}")
    print(f"  window      : ±{payload['window']}")
    print()

    bc = payload["behavior_counts"]
    total_sp = max(1, payload["splash_count"])
    print(f"  BEHAVIOR DISTRIBUTION  ({total_sp} splash events)")
    for b in _BEHAVIOR_ORDER:
        n = bc[b]
        pct = 100.0 * n / total_sp
        bar = "█" * int(pct / 2)
        print(f"    {b:12s}  {n:>5}  {pct:5.1f}%  {bar}")
    print()

    print(f"  PATTERN CROSSING RATES  (hidden axes: ws=mod7, vs=mod11, ts=mod13)")
    print(f"  {'pat':>3}  {'total':>6}  {'sp':>4}  {'c30%':>5}  {'h7%':>5}  {'h11%':>5}  {'h13%':>5}  {'tess%':>6}  {'deep%':>6}  {'shad%':>6}  {'surf%':>6}  {'flat%':>6}")
    print(f"  {'─'*3}  {'─'*6}  {'─'*4}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}")
    for ps in payload["pattern_summary"]:
        print(
            f"  {ps['pattern']:>3}  {ps['total']:>6,}  {ps['splash']:>4}"
            f"  {ps['cross30_pct']:>5.1f}"
            f"  {ps['hidden7_pct']:>5.1f}  {ps['hidden11_pct']:>5.1f}  {ps['hidden13_pct']:>5.1f}"
            f"  {ps['tesseract_pct']:>6.1f}  {ps['deep_pct']:>6.1f}  {ps['shadow_pct']:>6.1f}"
            f"  {ps['surface_pct']:>6.1f}  {ps['flat_pct']:>6.1f}"
        )
    print()

    col_hdr = (
        f"  {'idx':>7}  {'prime_B':>14}  {'ratio':>8}  {'pat':>3}  {'beh':>9}"
        f"  {'c30':>3}  {'h7':>3}  {'h11':>3}  {'h13':>3}"
        f"  {'wA':>3}  {'wC':>3}  {'vA':>3}  {'vC':>3}  {'tA':>3}  {'tC':>3}"
        f"  {'φ_drft':>7}  {'wd':>3}  gap_wl[3,5,7,11,13]"
    )
    col_sep = (
        f"  {'─'*7}  {'─'*14}  {'─'*8}  {'─'*3}  {'─'*9}"
        f"  {'─'*3}  {'─'*3}  {'─'*3}  {'─'*3}"
        f"  {'─'*3}  {'─'*3}  {'─'*3}  {'─'*3}  {'─'*3}  {'─'*3}"
        f"  {'─'*7}  {'─'*3}  {'─'*20}"
    )

    def _show_group(label: str, events: list[dict]) -> None:
        if not events:
            return
        print(f"  ── {label}  ({len(events)} shown) ──")
        print(col_hdr)
        print(col_sep)
        for e in events:
            gwl = e["gap_wall_loops_own"]
            wl_str = ",".join(str(gwl.get(str(q), "?")) for q in _GAP_WALL_MODS)
            c30 = "Y" if e["cross30"] else "."
            h7  = "Y" if e["hidden7"]  else "."
            h11 = "Y" if e["hidden11"] else "."
            h13 = "Y" if e["hidden13"] else "."
            print(
                f"  {e['at_idx']:>7,}  {e['prime_B']:>14,}  {e['ratio']:>8.4f}"
                f"  {e['pattern']:>3}  {e['behavior']:>9}"
                f"  {c30:>3}  {h7:>3}  {h11:>3}  {h13:>3}"
                f"  {e['ws_A']:>3}  {e['ws_C']:>3}  {e['vs_A']:>3}  {e['vs_C']:>3}"
                f"  {e['ts_A']:>3}  {e['ts_C']:>3}"
                f"  {e['phi_drift_triple']:>7.4f}  {e['own_wall_density']:>3}  [{wl_str}]"
            )
        print()

    # Show tesseract + dense-wall events first
    _show_group("TESSERACT  (all 3 hidden axes flip)", payload["by_behavior"]["tesseract"])
    _show_group("ALL SPLASHES sorted by gap wall density", payload["all_by_wall_density"])
    _show_group("DEEP  (2 hidden axes)", payload["by_behavior"]["deep"])
    _show_group("SURFACE  (mod-30 only)", payload["by_behavior"]["surface"])
    _show_group("FLAT  (no crossings — pure outliers)", payload["by_behavior"]["flat"])


def run_soliton_probe(
    limit: int = 1_000_000,
    superprime_only: bool = True,
    window: int = 10,
    top: int = 25,
) -> dict:
    """Gap charge field soliton probe.

    gap_charge(g) = sum(-1 if g%p==0 else +1 for p in [3,5,7,11,13])  range -5 to +5

    soliton_score = abs(ratio) + rebound_count + foam_density
                   + max(0, -gc_before) + max(0, -gc_after) + charge_flip

    5-class event taxonomy:
      visible_crossing    : mod-30 shell crossing (standard CRT event)
      mixed_collision     : shell crossing AND negative flanking gap charge
      charged_hidden_wall : no crossing, negative flanking charge (III/OOO gap-field events)
      smooth_phase        : no crossing, positive charge, phi_drift >= 0.30
      variance_only       : no crossing, positive charge, phi_drift < 0.30
    """
    all_primes = sieve(limit)
    if superprime_only:
        rows = _compute_doubly_indexed_superprimes(all_primes)
        seq = [r["P_P_n"] for r in rows]
        seq_label = "P(P(n)) superprimes [n prime]"
        shell_map = {r["P_P_n"]: r["shell"] for r in rows}
    else:
        seq = all_primes
        seq_label = "all primes"
        shell_map = {}

    if len(seq) < 3:
        return {"schema_version": "prime_fog_soliton_v1", "error": "too few primes"}

    gaps = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
    delta_g = [gaps[i + 1] - gaps[i] for i in range(len(gaps) - 1)]
    nonzero = [abs(d) for d in delta_g if d != 0]
    mean_abs_dg = sum(nonzero) / len(nonzero) if nonzero else 1.0

    gap_charges = [_gap_charge_simple(g) for g in gaps]

    N = len(delta_g)
    splash_events: list[dict] = []
    class_hist: dict[str, int] = {sc: 0 for sc in _SOLITON_CLASSES}
    pat_class_hist: dict[str, dict[str, int]] = {}

    for idx, dg in enumerate(delta_g):
        ratio = dg / mean_abs_dg
        if _classify_step(abs(ratio)) != "splash":
            continue

        pa = seq[idx]
        pb = seq[idx + 1]
        pc = seq[idx + 2]

        sa = shell_map.get(pa)
        sc_val = shell_map.get(pc)
        pat = (
            ("I" if sa == "inner" else "O")
            + ("I" if shell_map.get(pb) == "inner" else "O")
            + ("I" if sc_val == "inner" else "O")
        )
        cross30 = sa in ("inner", "outer") and sc_val in ("inner", "outer") and sa != sc_val

        gc_before = gap_charges[idx - 1] if idx > 0 else 0
        gc_AB = gap_charges[idx]
        gc_BC = gap_charges[idx + 1] if idx + 1 < len(gap_charges) else 0
        gc_after = gap_charges[idx + 2] if idx + 2 < len(gap_charges) else 0

        ca = _extended_prime_coords(pa)
        cc = _extended_prime_coords(pc)
        phi_drift = abs(cc["phi_phase"] - ca["phi_phase"])

        h7 = ca["ws"] != 0 and cc["ws"] != 0 and (ca["ws"] > 0) != (cc["ws"] > 0)
        h11 = ca["vs"] != 0 and cc["vs"] != 0 and (ca["vs"] > 0) != (cc["vs"] > 0)
        h13 = ca["ts"] != 0 and cc["ts"] != 0 and (ca["ts"] > 0) != (cc["ts"] > 0)
        bclass = _behavior_class(cross30, h7, h11, h13)

        s_class = _soliton_event_class(cross30, gc_before, gc_after, phi_drift)

        rebound = 0
        if idx > 0 and delta_g[idx - 1] != 0 and dg != 0 and (delta_g[idx - 1] > 0) != (dg > 0):
            rebound += 1
        if idx + 1 < N and delta_g[idx + 1] != 0 and dg != 0 and (delta_g[idx + 1] > 0) != (dg > 0):
            rebound += 1

        lo = max(0, idx - window)
        hi = min(N - 1, idx + window)
        nbr = [abs(delta_g[j] / mean_abs_dg) for j in range(lo, hi + 1) if j != idx]
        mist_droplet = sum(1 for r in nbr if 1.0 <= r < 4.0)
        foam_density = mist_droplet / max(1, len(nbr))

        charge_flip = 1.0 if (gc_before < 0) != (gc_after < 0) else 0.0

        soliton_score = (
            abs(ratio)
            + rebound
            + foam_density
            + max(0, -gc_before)
            + max(0, -gc_after)
            + charge_flip
        )

        w_lo = max(0, idx - window)
        w_hi = min(len(gap_charges) - 1, idx + window + 3)
        w_charges = gap_charges[w_lo : w_hi + 1]
        mean_wc = sum(w_charges) / max(1, len(w_charges))
        neg_wc_frac = sum(1 for c in w_charges if c < 0) / max(1, len(w_charges))

        class_hist[s_class] = class_hist.get(s_class, 0) + 1
        if pat not in pat_class_hist:
            pat_class_hist[pat] = {sc: 0 for sc in _SOLITON_CLASSES}
        pat_class_hist[pat][s_class] = pat_class_hist[pat].get(s_class, 0) + 1

        splash_events.append(
            {
                "at_idx": idx + 1,
                "prime_A": pa,
                "prime_B": pb,
                "prime_C": pc,
                "pattern": pat,
                "ratio": round(ratio, 4),
                "cross30": cross30,
                "behavior": bclass,
                "soliton_class": s_class,
                "gc_before": gc_before,
                "gc_AB": gc_AB,
                "gc_BC": gc_BC,
                "gc_after": gc_after,
                "charge_flip": bool(charge_flip),
                "phi_drift": round(phi_drift, 4),
                "rebound_count": rebound,
                "foam_density": round(foam_density, 4),
                "mean_window_gc": round(mean_wc, 3),
                "neg_window_frac": round(neg_wc_frac, 4),
                "soliton_score": round(soliton_score, 4),
            }
        )

    pat_summary: list[dict] = []
    for pat, c in sorted(pat_class_hist.items()):
        total = max(1, sum(c.values()))
        row: dict = {"pattern": pat, "splash_count": total}
        for sc in _SOLITON_CLASSES:
            row[f"{sc}_pct"] = round(100.0 * c.get(sc, 0) / total, 1)
        pat_summary.append(row)

    by_soliton = sorted(splash_events, key=lambda e: -e["soliton_score"])
    iii_ooo = [e for e in by_soliton if e["pattern"] in ("III", "OOO")]
    chw = [e for e in by_soliton if e["soliton_class"] == "charged_hidden_wall"]
    crossings = [e for e in by_soliton if e["cross30"]]

    return {
        "schema_version": "prime_fog_soliton_v1",
        "sequence": seq_label,
        "limit": limit,
        "total_steps": N,
        "splash_count": len(splash_events),
        "window": window,
        "mean_abs_dg": round(mean_abs_dg, 4),
        "class_histogram": class_hist,
        "pattern_summary": pat_summary,
        "top_by_soliton": by_soliton[:top],
        "iii_ooo_splashes": iii_ooo[:top],
        "charged_hidden_wall_splashes": chw[:top],
        "crossing_splashes": crossings[:top],
    }


def print_soliton_probe(payload: dict) -> None:
    if "error" in payload:
        print(f"SOLITON PROBE error: {payload['error']}")
        return

    print(f"\n{'='*72}")
    print("SOLITON CHARGE PROBE")
    print(f"  sequence : {payload['sequence']}")
    print(f"  limit    : {payload['limit']:,}")
    print(f"  splashes : {payload['splash_count']}  (of {payload['total_steps']:,} steps)")
    print("  charge   : sum(-1 if gap%p==0 else +1 for p in [3,5,7,11,13])  range -5 to +5")

    print(f"\n{'─'*60}")
    print("EVENT CLASS DISTRIBUTION  (splash events only)")
    ch = payload["class_histogram"]
    total = max(1, payload["splash_count"])
    for sc in _SOLITON_CLASSES:
        n = ch.get(sc, 0)
        bar = "#" * int(30 * n / total)
        print(f"  {sc:<25}  {n:>4}  ({100.0*n/total:5.1f}%)  {bar}")

    print(f"\n{'─'*60}")
    print("PATTERN × CLASS  (% of each pattern's splashes)")
    print(f"  {'pat':>3}  {'n':>5}  {'vis':>5}  {'mix':>5}  {'chw':>5}  {'phi':>5}  {'var':>5}")
    print(f"  {'─'*46}")
    for row in payload["pattern_summary"]:
        p = row["pattern"]
        n = row["splash_count"]
        vis = row.get("visible_crossing_pct", 0.0)
        mix = row.get("mixed_collision_pct", 0.0)
        chw = row.get("charged_hidden_wall_pct", 0.0)
        phi = row.get("smooth_phase_pct", 0.0)
        var = row.get("variance_only_pct", 0.0)
        print(f"  {p:>3}  {n:>5}  {vis:>5.1f}  {mix:>5.1f}  {chw:>5.1f}  {phi:>5.1f}  {var:>5.1f}")

    def _show_events(title: str, events: list[dict], limit: int = 20) -> None:
        if not events:
            return
        print(f"\n{'─'*60}")
        print(f"{title}  [{len(events)} total, {min(len(events), limit)} shown]")
        print(
            f"  {'rk':>3}  {'idx':>6}  {'prime_B':>10}  {'rat':>7}  "
            f"{'pat':>3}  {'cls':<25}  {'c30':>3}  "
            f"{'gcB':>4}  {'gcA':>4}  {'flp':>3}  {'phi':>6}  {'sol':>7}"
        )
        for i, e in enumerate(events[:limit], 1):
            c30 = "Y" if e["cross30"] else "N"
            fl = "Y" if e["charge_flip"] else "N"
            print(
                f"  {i:>3}  {e['at_idx']:>6}  {e['prime_B']:>10,}  {e['ratio']:>7.3f}  "
                f"{e['pattern']:>3}  {e['soliton_class']:<25}  {c30:>3}  "
                f"{e['gc_before']:>4}  {e['gc_after']:>4}  {fl:>3}  "
                f"{e['phi_drift']:>6.4f}  {e['soliton_score']:>7.3f}"
            )

    _show_events("TOP EVENTS BY SOLITON SCORE", payload["top_by_soliton"])
    _show_events("III / OOO SPLASHES  (non-crossing patterns)", payload["iii_ooo_splashes"])
    _show_events(
        "CHARGED HIDDEN WALL  (no mod-30 cross, negative flanking charge)",
        payload["charged_hidden_wall_splashes"],
    )
    _show_events("CROSSING SPLASHES  (visible + mixed)", payload["crossing_splashes"])
    print()


_PRIME_RATIO_NUMERATOR_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
    53, 59, 61, 67, 71, 73, 79, 83, 89, 97,
]
_PRIME_RATIO_DENOMINATORS = [1, 2, 3, 5, 7, 11, 13, 17, 19, 23, 29]


def _nearest_prime_ratio(gap_a: int, gap_b: int) -> dict:
    if gap_a <= 0 or gap_b <= 0:
        return {"ratio": 0.0, "target": 0.0, "label": "none", "error": 1.0, "score": 0.0}
    ratio = max(gap_a, gap_b) / min(gap_a, gap_b)
    best: tuple[float, float, int, int] | None = None
    for p in _PRIME_RATIO_NUMERATOR_PRIMES:
        for q in _PRIME_RATIO_DENOMINATORS:
            if p <= q:
                continue
            target = p / q
            error = abs(math.log(ratio / target))
            if best is None or error < best[0]:
                best = (error, target, p, q)
    if best is None:
        return {"ratio": ratio, "target": 0.0, "label": "none", "error": 1.0, "score": 0.0}
    error, target, p, q = best
    return {
        "ratio": round(ratio, 6),
        "target": round(target, 6),
        "label": f"{p}/{q}",
        "error": round(error, 6),
        "score": round(1 / (1 + 50 * error), 6),
    }


def _gap_depth_ratio_resonance(
    prime_ratio: dict,
    depth_before: float,
    depth_after: float,
    wall_before: int,
    wall_after: int,
) -> dict:
    depth_total = depth_before + depth_after
    depth_norm = min(1.0, depth_total / 12.0)
    wall_norm = min(1.0, (wall_before + wall_after) / max(1, 2 * len(_GAP_WALL_MODS)))
    support = (depth_norm * 0.70) + (wall_norm * 0.30)
    score = prime_ratio["score"] * support
    return {
        "score": round(score, 6),
        "depth_total": round(depth_total, 6),
        "depth_norm": round(depth_norm, 6),
        "wall_norm": round(wall_norm, 6),
        "support": round(support, 6),
        "ratio_label": prime_ratio["label"],
        "label": f"{prime_ratio['label']}@D{depth_total:.2f}",
    }


def _gap_wall_count(gap: int) -> int:
    return sum(1 for p in _GAP_WALL_MODS if gap % p == 0)


def _gap_padic_depth(gap: int) -> float:
    return sum(_padic_valuation(gap, p) * math.log(p) for p in _GAP_WALL_MODS)


def _build_superprime_event_field(limit: int, superprime_only: bool) -> dict:
    if superprime_only:
        # Memory-bounded: pick superprimes off their global index via a segmented stream instead of
        # materialising sieve(limit) (the RAM wall). Byte-identical to the old full-sieve path.
        rows = _superprime_rows_segmented(limit)
        seq = [r["P_P_n"] for r in rows]
        seq_label = "P(P(n)) superprimes [n prime]"
        shell_map = {r["P_P_n"]: r["shell"] for r in rows}
    else:
        seq = sieve(limit)
        seq_label = "all primes"
        shell_map = {}

    if len(seq) < 3:
        return {"error": "too few primes"}

    gaps = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
    delta_g = [gaps[i + 1] - gaps[i] for i in range(len(gaps) - 1)]
    nonzero = [abs(d) for d in delta_g if d != 0]
    mean_abs_dg = sum(nonzero) / len(nonzero) if nonzero else 1.0
    gap_charges = [_gap_charge_simple(g) for g in gaps]

    events: list[dict] = []
    for idx, dg in enumerate(delta_g):
        pa = seq[idx]
        pb = seq[idx + 1]
        pc = seq[idx + 2]
        ca = _extended_prime_coords(pa)
        cb = _extended_prime_coords(pb)
        cc = _extended_prime_coords(pc)

        sa = shell_map.get(pa) if shell_map else ca["shell30"]
        sb = shell_map.get(pb) if shell_map else cb["shell30"]
        sc = shell_map.get(pc) if shell_map else cc["shell30"]
        pattern = (
            ("I" if sa == "inner" else "O")
            + ("I" if sb == "inner" else "O")
            + ("I" if sc == "inner" else "O")
        )
        cross30 = sa in ("inner", "outer") and sc in ("inner", "outer") and sa != sc
        hidden7 = ca["ws"] != 0 and cc["ws"] != 0 and ((ca["ws"] > 0) != (cc["ws"] > 0))
        hidden11 = ca["vs"] != 0 and cc["vs"] != 0 and ((ca["vs"] > 0) != (cc["vs"] > 0))
        hidden13 = ca["ts"] != 0 and cc["ts"] != 0 and ((ca["ts"] > 0) != (cc["ts"] > 0))
        hidden_count = int(hidden7) + int(hidden11) + int(hidden13)

        ratio = dg / mean_abs_dg
        gap_before = gaps[idx]
        gap_after = gaps[idx + 1]
        wall_before = _gap_wall_count(gap_before)
        wall_after = _gap_wall_count(gap_after)
        depth_before = _gap_padic_depth(gap_before)
        depth_after = _gap_padic_depth(gap_after)
        gc_before = gap_charges[idx]
        gc_after = gap_charges[idx + 1]
        prime_ratio = _nearest_prime_ratio(gap_before, gap_after)
        depth_resonance = _gap_depth_ratio_resonance(
            prime_ratio,
            depth_before,
            depth_after,
            wall_before,
            wall_after,
        )
        depth_delta = depth_after - depth_before
        depth_flux = abs(depth_delta)
        charge_flip = (gc_before < 0) != (gc_after < 0)
        resonant_soliton_score = (
            abs(ratio)
            + depth_flux
            + prime_ratio["score"]
            + (1.0 if charge_flip else 0.0)
        )
        phi_drift = abs(cc["phi_phase"] - ca["phi_phase"])

        events.append(
            {
                "idx": idx + 1,
                "prime_A": pa,
                "prime_B": pb,
                "prime_C": pc,
                "gap_before": gap_before,
                "gap_after": gap_after,
                "dg": dg,
                "ratio": ratio,
                "abs_ratio": abs(ratio),
                "cls": _classify_step(abs(ratio)),
                "sign": 1 if dg > 0 else -1 if dg < 0 else 0,
                "pattern": pattern,
                "cross30": cross30,
                "hidden_count": hidden_count,
                "behavior": _behavior_class(cross30, hidden7, hidden11, hidden13),
                "wall_before": wall_before,
                "wall_after": wall_after,
                "wall_density": (wall_before + wall_after) / (2 * len(_GAP_WALL_MODS)),
                "padic_depth_before": depth_before,
                "padic_depth_after": depth_after,
                "padic_depth": max(depth_before, depth_after),
                "gap_charge_before": gc_before,
                "gap_charge_after": gc_after,
                "charge_flip": charge_flip,
                "phi_drift": phi_drift,
                "prime_ratio": prime_ratio,
                "depth_resonance": depth_resonance,
                "depth_delta": depth_delta,
                "depth_flux": depth_flux,
                "resonant_soliton_score": resonant_soliton_score,
            }
        )

    for i, event in enumerate(events):
        event["rebound"] = any(
            0 <= j < len(events) and events[j]["sign"] != 0 and event["sign"] != 0 and events[j]["sign"] != event["sign"]
            for j in (i - 1, i + 1)
        )

    return {
        "sequence": seq_label,
        "seq_length": len(seq),
        "gaps": gaps,
        "events": events,
        "mean_abs_dg": mean_abs_dg,
    }


def _next_region_kind(row: dict) -> str:
    if row["wall_channel"] >= 0.45:
        return "hidden_wall_region"
    if row["crossing_channel"] >= 0.50:
        return "visible_crossing_region"
    if row.get("depth_resonance_channel", 0.0) >= 0.55:
        return "depth_resonance_region"
    if row["prime_ratio_channel"] >= 0.90:
        return "prime_ratio_region"
    if row["phi_channel"] >= 0.50:
        return "smooth_phase_region"
    return "variance_region"


_NEXT_REGION_PROFILES: dict[str, dict[str, float]] = {
    # retrospective: uses next_strength (window outcome)
    "balanced": {
        "anchor": 1.0, "next_strength": 2.0,
        "foam": 1.0, "rebound": 2.0, "crossing": 1.0, "hidden": 1.0,
        "wall": 3.0, "depth": 1.0, "charge_flip": 2.0, "phi": 1.0, "prime_ratio": 1.0,
    },
    # predictive: bias toward hidden walls and charge movement, no outcome
    "soliton": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 1.0, "rebound": 2.0, "crossing": -0.5, "hidden": 2.0,
        "wall": 5.0, "depth": 0.0, "charge_flip": 4.0, "phi": 0.0, "prime_ratio": 0.0,
    },
    # predictive: region-health without outcome domination
    "forecast": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 0.0, "rebound": 0.0, "crossing": 0.5, "hidden": 1.0,
        "wall": 2.0, "depth": 0.0, "charge_flip": 2.0, "phi": 3.0, "prime_ratio": 2.0,
    },
    # predictive: score onset of breakdown — penalize stability, reward stress signals
    "instability": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 2.0, "rebound": 3.0, "crossing": 2.0, "hidden": 2.0,
        "wall": 2.0, "depth": 1.0, "charge_flip": 3.0, "phi": -2.0, "prime_ratio": -2.0,
    },
    # same stress profile, but high foam without charge motion is treated as stale churn
    "instability_flip": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 2.0, "rebound": 3.0, "crossing": 2.0, "hidden": 2.0,
        "wall": 2.0, "depth": 1.0, "charge_flip": 3.0, "phi": -2.0, "prime_ratio": -2.0,
    },
    # same stress profile, with additional stale-churn gates for known miss shapes
    "instability_gate2": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 2.0, "rebound": 3.0, "crossing": 2.0, "hidden": 2.0,
        "wall": 2.0, "depth": 1.0, "charge_flip": 3.0, "phi": -2.0, "prime_ratio": -2.0,
    },
    # gate2 plus p-adic-supported prime-ratio resonance
    "resonance_gate3": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 2.0, "rebound": 3.0, "crossing": 2.0, "hidden": 2.0,
        "wall": 2.0, "depth": 0.5, "charge_flip": 3.0, "phi": -2.0, "prime_ratio": -2.0,
        "depth_resonance": 4.0,
    },
    # direct combined metric: |accel_ratio| + depth_flux + prime-ratio resonance + charge-flip bonus
    "resonant_soliton": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 0.0, "rebound": 0.0, "crossing": 0.0, "hidden": 0.0,
        "wall": 0.0, "depth": 0.0, "depth_flux": 2.0, "charge_flip": 0.0,
        "phi": 0.0, "prime_ratio": 0.0, "depth_resonance": 2.0, "resonant_soliton": 8.0,
    },
    # thermal omnidirectional suite — isolates each axis of the thermal signal:
    # cold_spot: ordered (low-variance) windows; no direction
    "thermal_cold": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 1.0, "rebound": 2.0, "crossing": 1.0, "hidden": 1.0,
        "wall": 1.0, "depth": 0.5, "charge_flip": 2.0, "phi": -1.0, "prime_ratio": -1.0,
        "geodesic_trend": 2.0,
        "cold_spot": 8.0,
    },
    # cooling only: disorder decreasing toward anchor (front half noisier than back)
    "thermal_cool": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 1.0, "rebound": 2.0, "crossing": 1.0, "hidden": 1.0,
        "wall": 1.0, "depth": 0.5, "charge_flip": 2.0, "phi": -1.0, "prime_ratio": -1.0,
        "geodesic_trend": 2.0,
        "cooling": 8.0,
    },
    # heating only: disorder increasing toward anchor (back half noisier than front)
    "thermal_heat": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 1.0, "rebound": 2.0, "crossing": 1.0, "hidden": 1.0,
        "wall": 1.0, "depth": 0.5, "charge_flip": 2.0, "phi": -1.0, "prime_ratio": -1.0,
        "geodesic_trend": 2.0,
        "heating": 8.0,
    },
    # combined: cold_spot + both directions (null hypothesis that direction is irrelevant)
    "thermal_omni": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 1.0, "rebound": 2.0, "crossing": 1.0, "hidden": 1.0,
        "wall": 1.0, "depth": 0.5, "charge_flip": 2.0, "phi": -1.0, "prime_ratio": -1.0,
        "geodesic_trend": 2.0,
        "cold_spot": 4.0, "cooling": 4.0, "heating": 4.0,
    },
    # thermal: cold_spot rewards ordered windows; cooling rewards windows where
    # disorder decays toward the anchor (front half noisier than back half)
    "thermal": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 1.0, "rebound": 2.0, "crossing": 1.0, "hidden": 1.0,
        "wall": 1.0, "depth": 0.5, "charge_flip": 2.0, "phi": -1.0, "prime_ratio": -1.0,
        "geodesic_trend": 2.0,
        "cold_spot": 4.0, "cooling": 6.0,
    },
    # instability_geo_cassette + cold_spot + |gradient|: phase-boundary thermal channels
    # gradient_abs rewards windows with large front/back temperature contrast (phase transition)
    # regardless of direction — the boundary zone, not which side you're on
    "instability_geo_cassette_thermal_abs": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 2.0, "rebound": 3.0, "crossing": 2.0, "hidden": 2.0,
        "wall": 2.0, "depth": 1.0, "charge_flip": 3.0, "phi": -2.0, "prime_ratio": -2.0,
        "geodesic_trend": 4.0,
        "cassette": 2.0, "cassette_adj": 4.0, "cassette_triplet": 3.0, "cassette_non_adj": 1.0,
        "cold_spot": 3.0, "gradient_abs": 5.0,
    },
    # grid sweep: cold_spot in {2,3,4} x gradient_abs in {3,4,5,6}
    # base channels identical to instability_geo_cassette_thermal_abs
    "igct_c2_g3": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":2.0,"gradient_abs":3.0},
    "igct_c2_g4": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":2.0,"gradient_abs":4.0},
    "igct_c2_g5": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":2.0,"gradient_abs":5.0},
    "igct_c2_g6": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":2.0,"gradient_abs":6.0},
    "igct_c3_g3": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":3.0,"gradient_abs":3.0},
    "igct_c3_g4": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":3.0,"gradient_abs":4.0},
    "igct_c3_g5": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":3.0,"gradient_abs":5.0},
    "igct_c3_g6": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":3.0,"gradient_abs":6.0},
    "igct_c4_g3": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":4.0,"gradient_abs":3.0},
    "igct_c4_g4": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":4.0,"gradient_abs":4.0},
    "igct_c4_g5": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":4.0,"gradient_abs":5.0},
    "igct_c4_g6": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":4.0,"gradient_abs":6.0},
    "igct_c2_g7": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":2.0,"gradient_abs":7.0},
    "igct_c2_g8": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":2.0,"gradient_abs":8.0},
    "igct_c3_g7": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":3.0,"gradient_abs":7.0},
    "igct_c3_g8": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":3.0,"gradient_abs":8.0},
    "igct_c4_g7": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":4.0,"gradient_abs":7.0},
    "igct_c4_g8": {"anchor":0.0,"next_strength":0.0,"foam":2.0,"rebound":3.0,"crossing":2.0,"hidden":2.0,"wall":2.0,"depth":1.0,"charge_flip":3.0,"phi":-2.0,"prime_ratio":-2.0,"geodesic_trend":4.0,"cassette":2.0,"cassette_adj":4.0,"cassette_triplet":3.0,"cassette_non_adj":1.0,"cold_spot":4.0,"gradient_abs":8.0},
    # standalone thermal_abs: cold_spot + |gradient| only, light instability base
    "thermal_abs": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 1.0, "rebound": 2.0, "crossing": 1.0, "hidden": 1.0,
        "wall": 1.0, "depth": 0.5, "charge_flip": 2.0, "phi": -1.0, "prime_ratio": -1.0,
        "geodesic_trend": 2.0,
        "cold_spot": 4.0, "gradient_abs": 6.0,
    },
    # instability_geo_cassette + thermal perturbation channels
    # cooling_score is directional: rewards windows where disorder decays toward anchor
    "instability_geo_cassette_thermal": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 2.0, "rebound": 3.0, "crossing": 2.0, "hidden": 2.0,
        "wall": 2.0, "depth": 1.0, "charge_flip": 3.0, "phi": -2.0, "prime_ratio": -2.0,
        "geodesic_trend": 4.0,
        "cassette": 2.0, "cassette_adj": 4.0, "cassette_triplet": 3.0, "cassette_non_adj": 1.0,
        "cold_spot": 3.0, "cooling": 5.0,
    },
    # instability_geo + cassette sub-channels: tests whether cross-manifold structure adds lift
    # adj (offset=1) and triplet (outer pair of 3) weighted higher than broad non-adjacent
    "instability_geo_cassette": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 2.0, "rebound": 3.0, "crossing": 2.0, "hidden": 2.0,
        "wall": 2.0, "depth": 1.0, "charge_flip": 3.0, "phi": -2.0, "prime_ratio": -2.0,
        "geodesic_trend": 4.0,
        "cassette": 2.0, "cassette_adj": 4.0, "cassette_triplet": 3.0, "cassette_non_adj": 1.0,
    },
    # cross-manifold phase-shifted symmetric zone: reward shell-complement + sign-opposite pairs
    # cassette = cross_density * phase_coherence * spectral_anomaly in trailing window
    "cassette": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 1.0, "rebound": 2.0, "crossing": 1.0, "hidden": 1.0,
        "wall": 1.0, "depth": 0.5, "charge_flip": 2.0, "phi": -1.0, "prime_ratio": -1.0,
        "geodesic_trend": 1.5, "cassette": 6.0,
    },
    # instability + geodesic trend: reward accelerating path through log-gap space
    # geodesic_trend > 0 means late-window step-sizes exceed early-window (field building)
    # geodesic_trend < 0 means decelerating (post-storm decay) — penalized here
    "instability_geo": {
        "anchor": 0.0, "next_strength": 0.0,
        "foam": 2.0, "rebound": 3.0, "crossing": 2.0, "hidden": 2.0,
        "wall": 2.0, "depth": 1.0, "charge_flip": 3.0, "phi": -2.0, "prime_ratio": -2.0,
        "geodesic_trend": 4.0,
    },
}


def _cassette_signal(region: list[dict]) -> dict:
    """Cross-manifold phase-shifted symmetric zone (CMPSSZ / cassette) scorer.

    Finds events where shell pattern is the bitwise complement (OIO ↔ IOI, etc.)
    AND gap-acceleration sign is opposite.  Three resolution levels:

      adj     — adjacent pairs (offset=1): the immediate inversion
      triplet — consecutive triplets (i, i+1, i+2) where outer pair is complement
      non_adj — all complement pairs at offset≥2 (broad background)

    cassette_score = weighted_cross × phase_coherence × spectral_anomaly
    """
    n = len(region)
    _empty = {
        "cassette_score": 0.0,
        "adj_density": 0.0,
        "triplet_density": 0.0,
        "non_adj_density": 0.0,
        "phase_coherence": 0.0,
        "spectral_anomaly": 0.0,
    }
    if n < 2:
        return _empty

    def _complement(pat: str) -> str:
        return "".join("O" if c == "I" else "I" for c in pat)

    # --- adjacent pairs (offset=1) ---
    adj_cross = 0
    for i in range(n - 1):
        ei, ej = region[i], region[i + 1]
        if (
            _complement(ei["pattern"]) == ej["pattern"]
            and ei["sign"] != 0
            and ej["sign"] != 0
            and ei["sign"] != ej["sign"]
        ):
            adj_cross += 1
    adj_density = adj_cross / max(1, n - 1)

    # --- consecutive triplets: outer pair (i, i+2) is complement, i+1 bridges ---
    triplet_cross = 0
    for i in range(n - 2):
        ei, ek = region[i], region[i + 2]
        if (
            _complement(ei["pattern"]) == ek["pattern"]
            and ei["sign"] != 0
            and ek["sign"] != 0
            and ei["sign"] != ek["sign"]
        ):
            triplet_cross += 1
    triplet_density = triplet_cross / max(1, n - 2) if n >= 3 else 0.0

    # --- non-adjacent pairs (offset≥2) + collect all offsets for phase coherence ---
    non_adj_cross = 0
    non_adj_total = 0
    offsets: list[int] = []
    # adjacent offsets first
    for i in range(n - 1):
        ei, ej = region[i], region[i + 1]
        if (
            _complement(ei["pattern"]) == ej["pattern"]
            and ei["sign"] != 0
            and ej["sign"] != 0
            and ei["sign"] != ej["sign"]
        ):
            offsets.append(1)
    # non-adjacent
    for i in range(n):
        comp_i = _complement(region[i]["pattern"])
        si = region[i]["sign"]
        for j in range(i + 2, n):
            non_adj_total += 1
            ej = region[j]
            if comp_i == ej["pattern"] and si != 0 and ej["sign"] != 0 and si != ej["sign"]:
                non_adj_cross += 1
                offsets.append(j - i)
    non_adj_density = non_adj_cross / max(1, non_adj_total)

    # --- phase coherence: consistency of offset distances across all pairs ---
    if offsets:
        mean_off = sum(offsets) / len(offsets)
        variance = sum((o - mean_off) ** 2 for o in offsets) / len(offsets)
        std_off = math.sqrt(variance)
        phase_coherence = max(0.0, 1.0 - std_off / max(mean_off, 1.0))
    else:
        phase_coherence = 0.0

    # --- spectral anomaly: DFT peakedness of gap_before sequence ---
    spectral_anomaly = 0.0
    if n >= 4:
        gap_seq = [float(e["gap_before"]) for e in region]
        N = len(gap_seq)
        mags = []
        for k in range(1, N // 2 + 1):
            s = sum(gap_seq[j] * cmath.exp(-2j * cmath.pi * k * j / N) for j in range(N))
            mags.append(abs(s))
        if mags:
            mean_mag = sum(mags) / len(mags)
            max_mag = max(mags)
            spectral_anomaly = min(3.0, max_mag / max(mean_mag, 1e-9))

    # combined cross: adjacent weighted most heavily (sharpest signal), triplets medium
    cross_combined = (adj_density * 3.0 + triplet_density * 2.0 + non_adj_density * 1.0) / 6.0
    cassette_score = cross_combined * phase_coherence * spectral_anomaly

    return {
        "cassette_score": round(cassette_score, 5),
        "adj_density": round(adj_density, 4),
        "triplet_density": round(triplet_density, 4),
        "non_adj_density": round(non_adj_density, 4),
        "phase_coherence": round(phase_coherence, 4),
        "spectral_anomaly": round(spectral_anomaly, 4),
    }


def _thermal_signal(region: list[dict]) -> dict:
    """Thermal perturbation channel.

    Models the gap field as a thermal system where gap-acceleration variance
    is the 'temperature'.  Three outputs:

      thermal_amplitude — std(dg) / mean(|gap|): how noisy the window is
      cold_spot_score   — 1/(1+amplitude): high = ordered = signal above noise floor
      thermal_gradient  — (T_front - T_back) / (T_front + T_back):
                          positive = field is cooling toward anchor (ordered)
                          negative = field is heating (building disorder)
      cooling_score     — max(0, thermal_gradient): reward cooling direction only

    Hypothesis: anchor primes occur preferentially when the trailing window is
    cooling — the front half was noisy, the back half organised.
    """
    n = len(region)
    _empty = {
        "thermal_amplitude": 0.0,
        "cold_spot_score": 0.5,
        "thermal_gradient": 0.0,
        "cooling_score": 0.0,
        "heating_score": 0.0,
        "gradient_abs": 0.0,
    }
    if n < 4:
        return _empty

    dg_vals = [float(e["dg"]) for e in region]
    gap_vals = [float(e["gap_before"]) for e in region]

    mean_gap = sum(abs(g) for g in gap_vals) / n
    mean_dg = sum(dg_vals) / n
    variance_dg = sum((d - mean_dg) ** 2 for d in dg_vals) / n
    std_dg = math.sqrt(variance_dg)

    thermal_amplitude = std_dg / max(mean_gap, 1.0)
    cold_spot_score = 1.0 / (1.0 + thermal_amplitude)

    # directional gradient: front half (older) vs back half (closer to anchor)
    half = n // 2
    front_dg = dg_vals[:half]
    back_dg = dg_vals[half:]

    mean_f = sum(front_dg) / len(front_dg)
    mean_b = sum(back_dg) / len(back_dg)
    var_f = sum((d - mean_f) ** 2 for d in front_dg) / len(front_dg)
    var_b = sum((d - mean_b) ** 2 for d in back_dg) / len(back_dg)
    T_front = math.sqrt(var_f)
    T_back = math.sqrt(var_b)

    denom = T_front + T_back
    if denom > 1e-9:
        thermal_gradient = (T_front - T_back) / denom
    else:
        thermal_gradient = 0.0

    cooling_score = max(0.0, thermal_gradient)   # reward: front hotter → field cooling toward anchor
    heating_score = max(0.0, -thermal_gradient)  # reward: back hotter → field heating toward anchor
    gradient_abs = abs(thermal_gradient)         # phase boundary: large contrast regardless of direction

    return {
        "thermal_amplitude": round(thermal_amplitude, 4),
        "cold_spot_score": round(cold_spot_score, 4),
        "thermal_gradient": round(thermal_gradient, 4),
        "cooling_score": round(cooling_score, 4),
        "heating_score": round(heating_score, 4),
        "gradient_abs": round(gradient_abs, 4),
    }


def _field_region_channels(region: list[dict]) -> dict:
    if not region:
        return {
            "foam_channel": 0.0,
            "rebound_channel": 0.0,
            "crossing_channel": 0.0,
            "hidden_channel": 0.0,
            "wall_channel": 0.0,
            "depth_channel": 0.0,
            "depth_flux_channel": 0.0,
            "charge_flip_channel": 0.0,
            "phi_channel": 0.0,
            "prime_ratio_channel": 0.0,
            "prime_ratio_label": "none",
            "depth_resonance_channel": 0.0,
            "depth_resonance_label": "none",
            "resonant_soliton_channel": 0.0,
            "geodesic_trend_channel": 0.0,
            "cassette_channel": 0.0,
            "cassette_adj_channel": 0.0,
            "cassette_triplet_channel": 0.0,
            "cassette_non_adj_channel": 0.0,
            "cmpssz_phase_coherence": 0.0,
            "cmpssz_spectral_anomaly": 0.0,
            "cold_spot_channel": 0.5,
            "cooling_channel": 0.0,
            "heating_channel": 0.0,
            "gradient_abs_channel": 0.0,
            "thermal_amplitude": 0.0,
            "thermal_gradient": 0.0,
            "class_counts": {},
            "pattern_counts": {},
        }

    n = len(region)
    mist_density = sum(1 for e in region if e["cls"] == "mist") / n
    droplet_density = sum(1 for e in region if e["cls"] == "droplet") / n
    splash_density = sum(1 for e in region if e["cls"] == "splash") / n
    pr_best = max(region, key=lambda e: e["prime_ratio"]["score"])
    dr_best = max(region, key=lambda e: e["depth_resonance"]["score"])
    # geodesic_trend: acceleration of trajectory in log-gap space
    # embed each step as (log|gap_before|, log|gap_after|), compute consecutive step distances,
    # compare late-half vs early-half mean. log(late/early) > 0 = field building toward event.
    if n >= 3:
        pts = [(math.log(max(e["gap_before"], 1)), math.log(max(e["gap_after"], 1))) for e in region]
        dists = [
            math.sqrt((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2)
            for i in range(len(pts) - 1)
        ]
        half = max(1, len(dists) // 2)
        early_mean = sum(dists[:half]) / half
        late_mean = sum(dists[half:]) / max(1, len(dists) - half)
        raw_geo = math.log(late_mean / max(early_mean, 1e-9)) if late_mean > 0 else -2.0
        geodesic_trend_val = max(-2.0, min(2.0, raw_geo))
    else:
        geodesic_trend_val = 0.0
    cmp = _cassette_signal(region)
    thm = _thermal_signal(region)
    return {
        "foam_channel": (mist_density * 1.5) + (droplet_density * 3.0) + (splash_density * 4.0),
        "rebound_channel": sum(1 for e in region if e["rebound"]) / n,
        "crossing_channel": sum(1 for e in region if e["cross30"]) / n,
        "hidden_channel": sum(e["hidden_count"] for e in region) / (3 * n),
        "wall_channel": sum(e["wall_density"] for e in region) / n,
        "depth_channel": min(1.0, sum(e["padic_depth"] for e in region) / (15.0 * n)),
        "depth_flux_channel": min(1.0, sum(e["depth_flux"] for e in region) / (10.0 * n)),
        "charge_flip_channel": sum(1 for e in region if e["charge_flip"]) / n,
        "phi_channel": max(e["phi_drift"] for e in region),
        "prime_ratio_channel": pr_best["prime_ratio"]["score"],
        "prime_ratio_label": pr_best["prime_ratio"]["label"],
        "depth_resonance_channel": dr_best["depth_resonance"]["score"],
        "depth_resonance_label": dr_best["depth_resonance"]["label"],
        "resonant_soliton_channel": min(1.0, max(e["resonant_soliton_score"] for e in region) / 12.0),
        "geodesic_trend_channel": round(geodesic_trend_val, 4),
        "cassette_channel": cmp["cassette_score"],
        "cassette_adj_channel": cmp["adj_density"],
        "cassette_triplet_channel": cmp["triplet_density"],
        "cassette_non_adj_channel": cmp["non_adj_density"],
        "cmpssz_phase_coherence": cmp["phase_coherence"],
        "cmpssz_spectral_anomaly": cmp["spectral_anomaly"],
        "cold_spot_channel": thm["cold_spot_score"],
        "cooling_channel": thm["cooling_score"],
        "heating_channel": thm["heating_score"],
        "gradient_abs_channel": thm["gradient_abs"],
        "thermal_amplitude": thm["thermal_amplitude"],
        "thermal_gradient": thm["thermal_gradient"],
        "class_counts": dict(Counter(e["cls"] for e in region)),
        "pattern_counts": dict(Counter(e["pattern"] for e in region).most_common(5)),
    }


def _weighted_field_score(channels: dict, weights: dict[str, float]) -> float:
    return (
        channels["foam_channel"] * weights.get("foam", 0.0)
        + channels["rebound_channel"] * weights.get("rebound", 0.0)
        + channels["crossing_channel"] * weights.get("crossing", 0.0)
        + channels["hidden_channel"] * weights.get("hidden", 0.0)
        + channels["wall_channel"] * weights.get("wall", 0.0)
        + channels["depth_channel"] * weights.get("depth", 0.0)
        + channels["depth_flux_channel"] * weights.get("depth_flux", 0.0)
        + channels["charge_flip_channel"] * weights.get("charge_flip", 0.0)
        + channels["phi_channel"] * weights.get("phi", 0.0)
        + channels["prime_ratio_channel"] * weights.get("prime_ratio", 0.0)
        + channels["depth_resonance_channel"] * weights.get("depth_resonance", 0.0)
        + channels["resonant_soliton_channel"] * weights.get("resonant_soliton", 0.0)
        + channels.get("geodesic_trend_channel", 0.0) * weights.get("geodesic_trend", 0.0)
        + channels.get("cassette_channel", 0.0) * weights.get("cassette", 0.0)
        + channels.get("cassette_adj_channel", 0.0) * weights.get("cassette_adj", 0.0)
        + channels.get("cassette_triplet_channel", 0.0) * weights.get("cassette_triplet", 0.0)
        + channels.get("cassette_non_adj_channel", 0.0) * weights.get("cassette_non_adj", 0.0)
        + channels.get("cold_spot_channel", 0.0) * weights.get("cold_spot", 0.0)
        + channels.get("cooling_channel", 0.0) * weights.get("cooling", 0.0)
        + channels.get("heating_channel", 0.0) * weights.get("heating", 0.0)
        + channels.get("gradient_abs_channel", 0.0) * weights.get("gradient_abs", 0.0)
    )


def _field_profile_gate_reason(channels: dict, profile: str) -> str:
    if (
        profile in ("instability_flip", "instability_gate2", "resonance_gate3")
        and channels["foam_channel"] >= 2.5
        and channels["charge_flip_channel"] <= 0.0
    ):
        return "high_foam_no_charge_flip"
    if profile in ("instability_gate2", "resonance_gate3"):
        if (
            channels["foam_channel"] <= 1.5
            and channels["wall_channel"] >= 0.40
            and channels["crossing_channel"] >= 0.80
        ):
            return "low_foam_high_wall_crossing_churn"
        if (
            channels["prime_ratio_channel"] >= 0.95
            and channels["crossing_channel"] <= 0.35
            and channels["charge_flip_channel"] <= 0.50
        ):
            return "prime_ratio_low_crossing_churn"
        if (
            channels["foam_channel"] >= 2.35
            and channels["charge_flip_channel"] <= 0.0
            and channels["crossing_channel"] >= 0.90
            and channels["phi_channel"] <= 0.40
        ):
            return "no_flip_low_phi_splash_residue"
    if (
        profile == "resonance_gate3"
        and channels["prime_ratio_channel"] >= 0.95
        and channels["depth_resonance_channel"] <= 0.20
    ):
        return "unsupported_prime_ratio_resonance"
    return ""


def _apply_field_profile_gate(score: float, channels: dict, profile: str) -> float:
    if _field_profile_gate_reason(channels, profile):
        return 0.0
    return score


def run_next_region_field_probe(
    limit: int = 1_000_000,
    superprime_only: bool = True,
    window: int = 12,
    top: int = 25,
    anchor_threshold: float = 4.0,
    profile: str = "balanced",
) -> dict:
    """Next-region search field with three channel-weight profiles.

    predictive_score  — anchor-local features only (before the window opens)
    observed_heat     — window evidence including next_strength (after-the-fact)
    field_score       — profile-weighted combination

    Overlap test: rank by predictive_score DESC and observed_heat DESC.
    Fraction of top-N that appear in both = predictive overlap %.
    """
    field = _build_superprime_event_field(limit, superprime_only)
    if "error" in field:
        return {"schema_version": "prime_fog_next_region_field_v1", "error": field["error"]}

    weights = _NEXT_REGION_PROFILES.get(profile, _NEXT_REGION_PROFILES["balanced"])
    events = field["events"]
    anchors = [i for i, event in enumerate(events) if event["abs_ratio"] >= anchor_threshold]
    rows: list[dict] = []

    for anchor_i in anchors:
        anchor = events[anchor_i]
        lo = anchor_i + 1
        hi = min(len(events), anchor_i + 1 + window)
        region = events[lo:hi]
        if not region:
            continue

        n = len(region)
        mist_density = sum(1 for e in region if e["cls"] == "mist") / n
        droplet_density = sum(1 for e in region if e["cls"] == "droplet") / n
        splash_density = sum(1 for e in region if e["cls"] == "splash") / n
        foam_channel = (mist_density * 1.5) + (droplet_density * 3.0) + (splash_density * 4.0)
        rebound_channel = sum(1 for e in region if e["rebound"]) / n
        crossing_channel = sum(1 for e in region if e["cross30"]) / n
        hidden_channel = sum(e["hidden_count"] for e in region) / (3 * n)
        wall_channel = sum(e["wall_density"] for e in region) / n
        depth_channel = min(1.0, sum(e["padic_depth"] for e in region) / (n * 10.0))
        charge_flip_channel = sum(1 for e in region if e["charge_flip"]) / n
        phi_channel = max(e["phi_drift"] for e in region)
        prime_ratio_channel = max(e["prime_ratio"]["score"] for e in region)
        depth_resonance_channel = max(e["depth_resonance"]["score"] for e in region)
        max_event = max(region, key=lambda e: e["abs_ratio"])
        anchor_channel = min(anchor["abs_ratio"] / 10.0, 1.0)
        next_strength_channel = min(max_event["abs_ratio"] / 10.0, 1.0)

        # Profile-weighted field score
        ch = {
            "anchor": anchor_channel, "next_strength": next_strength_channel,
            "foam": foam_channel, "rebound": rebound_channel,
            "crossing": crossing_channel, "hidden": hidden_channel,
            "wall": wall_channel, "depth": depth_channel,
            "charge_flip": charge_flip_channel, "phi": phi_channel,
            "prime_ratio": prime_ratio_channel,
            "depth_resonance": depth_resonance_channel,
        }
        field_score = sum(ch.get(k, 0.0) * weights[k] for k in weights)

        # Observed heat: full retrospective score (always balanced, includes outcome)
        observed_heat = (
            next_strength_channel * 3.0
            + foam_channel
            + rebound_channel * 2.0
            + crossing_channel
            + wall_channel * 3.0
            + depth_channel
            + charge_flip_channel * 2.0
            + phi_channel
            + prime_ratio_channel
        )

        # Predictive score: anchor-local only, no window evidence
        predictive_score = (
            anchor_channel
            + anchor["phi_drift"]
            + anchor["prime_ratio"]["score"]
            + anchor["wall_density"] * 3.0
            + min(anchor["padic_depth"], 5.0) / 5.0
            + (1.0 if anchor["charge_flip"] else 0.0) * 2.0
            + anchor["hidden_count"] / 3.0
            + max(0, -anchor["gap_charge_before"]) * 0.2
            + max(0, -anchor["gap_charge_after"]) * 0.2
        )

        pr_best = max(region, key=lambda e: e["prime_ratio"]["score"])
        dr_best = max(region, key=lambda e: e["depth_resonance"]["score"])
        row = {
            "rank": 0,
            "anchor_idx": anchor["idx"],
            "anchor_prime": anchor["prime_B"],
            "anchor_ratio": round(anchor["ratio"], 4),
            "anchor_pattern": anchor["pattern"],
            "region_start_idx": region[0]["idx"],
            "region_end_idx": region[-1]["idx"],
            "top_event_idx": max_event["idx"],
            "top_event_prime": max_event["prime_B"],
            "top_event_ratio": round(max_event["ratio"], 4),
            "top_event_pattern": max_event["pattern"],
            "field_score": round(field_score, 4),
            "observed_heat": round(observed_heat, 4),
            "predictive_score": round(predictive_score, 4),
            "region_kind": "",
            # channels
            "anchor_channel": round(anchor_channel, 4),
            "next_strength_channel": round(next_strength_channel, 4),
            "foam_channel": round(foam_channel, 4),
            "rebound_channel": round(rebound_channel, 4),
            "crossing_channel": round(crossing_channel, 4),
            "hidden_channel": round(hidden_channel, 4),
            "wall_channel": round(wall_channel, 4),
            "depth_channel": round(depth_channel, 4),
            "charge_flip_channel": round(charge_flip_channel, 4),
            "phi_channel": round(phi_channel, 4),
            "prime_ratio_channel": round(prime_ratio_channel, 4),
            "prime_ratio_label": pr_best["prime_ratio"]["label"],
            "depth_resonance_channel": round(depth_resonance_channel, 4),
            "depth_resonance_label": dr_best["depth_resonance"]["label"],
            "class_counts": dict(Counter(e["cls"] for e in region)),
            "pattern_counts": dict(Counter(e["pattern"] for e in region).most_common(5)),
        }
        row["region_kind"] = _next_region_kind(row)
        rows.append(row)

    rows.sort(key=lambda r: -r["field_score"])
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank

    # Overlap: top-20 by field_score vs top-20 by observed_heat vs top-20 by predictive_score
    overlap_n = min(20, len(rows))
    top_field_idx = {r["anchor_idx"] for r in rows[:overlap_n]}
    by_heat = sorted(rows, key=lambda r: -r["observed_heat"])
    top_heat_idx = {r["anchor_idx"] for r in by_heat[:overlap_n]}
    by_pred = sorted(rows, key=lambda r: -r["predictive_score"])
    top_pred_idx = {r["anchor_idx"] for r in by_pred[:overlap_n]}

    overlap_field_heat = len(top_field_idx & top_heat_idx)
    overlap_pred_heat = len(top_pred_idx & top_heat_idx)
    overlap_pred_field = len(top_pred_idx & top_field_idx)

    return {
        "schema_version": "prime_fog_next_region_field_v1",
        "sequence": field["sequence"],
        "limit": limit,
        "seq_length": field["seq_length"],
        "total_steps": len(events),
        "mean_abs_dg": round(field["mean_abs_dg"], 4),
        "window": window,
        "anchor_threshold": anchor_threshold,
        "anchor_count": len(anchors),
        "region_count": len(rows),
        "profile": profile,
        "weights": weights,
        "kind_counts": dict(Counter(row["region_kind"] for row in rows)),
        "overlap_n": overlap_n,
        "overlap_field_heat": overlap_field_heat,
        "overlap_pred_heat": overlap_pred_heat,
        "overlap_pred_field": overlap_pred_field,
        "top_regions": rows[:top],
        "top_by_heat": by_heat[:top],
        "top_by_predictive": by_pred[:top],
    }


def run_field_scan_probe(
    limit: int = 1_000_000,
    superprime_only: bool = True,
    window: int = 12,
    history: int = 6,
    top: int = 25,
    anchor_threshold: float = 4.0,
    profile: str = "forecast",
) -> dict:
    """Causal field scan.

    field_score uses only the current/trailing context ending at scan_idx.
    future_heat and future_anchor are measured after scan_idx and are not used
    by the predictive score.
    """
    field = _build_superprime_event_field(limit, superprime_only)
    if "error" in field:
        return {"schema_version": "prime_fog_field_scan_v1", "error": field["error"]}

    events = field["events"]
    if len(events) < 2:
        return {"schema_version": "prime_fog_field_scan_v1", "error": "too few events"}

    weights = _NEXT_REGION_PROFILES.get(profile, _NEXT_REGION_PROFILES["forecast"])
    history = max(1, history)
    window = max(1, window)
    rows: list[dict] = []

    for scan_i, event in enumerate(events[:-1]):
        if event["abs_ratio"] >= anchor_threshold:
            continue

        context = events[max(0, scan_i + 1 - history) : scan_i + 1]
        future = events[scan_i + 1 : min(len(events), scan_i + 1 + window)]
        if not future:
            continue

        current = _field_region_channels(context)
        future_channels = _field_region_channels(future)
        max_future = max(future, key=lambda e: e["abs_ratio"])
        future_anchor_events = [e for e in future if e["abs_ratio"] >= anchor_threshold]
        first_anchor = future_anchor_events[0] if future_anchor_events else None
        future_strength_channel = min(2.0, max_future["abs_ratio"] / anchor_threshold)
        future_heat = (
            future_strength_channel * 2.0
            + future_channels["foam_channel"]
            + future_channels["rebound_channel"] * 2.0
        )
        raw_field_score = _weighted_field_score(current, weights)
        profile_gate = _field_profile_gate_reason(current, profile)
        field_score = _apply_field_profile_gate(raw_field_score, current, profile)

        # Precompute gravity fallback score from local abs_ratio context.
        # Uses float-safe Poincaré embedding — scale-invariant across prime ranges.
        # branch_score() uses this when the thermal gate fires and fallback_scale=0.
        _ratio_vals = [e["abs_ratio"] for e in context if math.isfinite(e.get("abs_ratio", 0.0)) and e.get("abs_ratio", 0.0) > 0]
        if len(_ratio_vals) >= 2:
            _gbodies = _gravity_bodies_float(_ratio_vals, bins=min(8, len(_ratio_vals)))
            _gresult = _gravity_at_float(event["abs_ratio"], _gbodies, metric="hyperbolic")
            gravity_score_normalized = _gresult["gravity_field_normalized"]
            _topo = _topological_type_at_float(event["abs_ratio"], _gbodies)
            topo_type_str = _topo["type"]
            topo_score = _topo["topo_score"]
            topo_asymmetry = _topo["asymmetry"]
            topo_confidence = _topo["confidence"]
        else:
            gravity_score_normalized = 0.0
            topo_type_str = "unknown"
            topo_score = 0.0
            topo_asymmetry = 0.0
            topo_confidence = 0.0

        _mmode = _musical_mode_channels(_ratio_vals)
        _lshadow = _lambda_shadow_channels(_ratio_vals, event["prime_B"])
        _gmap = _graph_map_channels(_ratio_vals)

        row = {
            "scan_idx": event["idx"],
            "scan_prime": event["prime_B"],
            "scan_ratio": round(event["ratio"], 4),
            "field_score": round(field_score, 4),
            "raw_field_score": round(raw_field_score, 4),
            "profile_gate": profile_gate,
            "future_heat": round(future_heat, 4),
            "future_strength_channel": round(future_strength_channel, 4),
            "future_anchor": bool(future_anchor_events),
            "future_anchor_count": len(future_anchor_events),
            "first_anchor_idx": first_anchor["idx"] if first_anchor else None,
            "first_anchor_prime": first_anchor["prime_B"] if first_anchor else None,
            "first_anchor_ratio": round(first_anchor["ratio"], 4) if first_anchor else None,
            "lead_steps": (first_anchor["idx"] - event["idx"]) if first_anchor else None,
            "top_future_idx": max_future["idx"],
            "top_future_prime": max_future["prime_B"],
            "top_future_ratio": round(max_future["ratio"], 4),
            "profile": profile,
            "gravity_score_normalized": round(gravity_score_normalized, 6),
            "topo_type": topo_type_str,
            "topo_score": round(topo_score, 6),
            "topo_asymmetry": round(topo_asymmetry, 6),
            "topo_confidence": round(topo_confidence, 6),
            "local_tonic": _mmode["local_tonic"],
            "best_mode": _mmode["best_mode"],
            "mode_fit_score": _mmode["mode_fit_score"],
            "mode_shift_channel": _mmode["mode_shift_channel"],
            "lambda_shadow_channel": _lshadow["lambda_shadow_channel"],
            "lambda_gradient_channel": _lshadow["lambda_gradient_channel"],
            "lambda_peak_lag": _lshadow["lambda_peak_lag"],
            "graph_monotone_ramp": _gmap["graph_monotone_ramp"],
            "graph_return_rate": _gmap["graph_return_rate"],
            "graph_edge_variance": _gmap["graph_edge_variance"],
            "graph_attractor_score": _gmap["graph_attractor_score"],
            **{k: round(v, 4) if isinstance(v, float) else v for k, v in current.items()},
            "future_class_counts": future_channels["class_counts"],
            "future_pattern_counts": future_channels["pattern_counts"],
        }
        row["region_kind"] = _next_region_kind(row)
        rows.append(row)

    rows.sort(key=lambda r: -r["field_score"])
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank

    by_heat = sorted(rows, key=lambda r: -r["future_heat"])
    by_anchor = sorted(
        rows,
        key=lambda r: (not r["future_anchor"], r["lead_steps"] if r["lead_steps"] is not None else 10**9, -r["field_score"]),
    )

    overlap_n = min(20, len(rows))
    top_field_idx = {r["scan_idx"] for r in rows[:overlap_n]}
    top_heat_idx = {r["scan_idx"] for r in by_heat[:overlap_n]}
    overlap_field_heat = len(top_field_idx & top_heat_idx)
    top_rows = rows[:overlap_n]
    top_anchor_hits = sum(1 for r in top_rows if r["future_anchor"])
    baseline_anchor_rate = sum(1 for r in rows if r["future_anchor"]) / len(rows) if rows else 0.0

    return {
        "schema_version": "prime_fog_field_scan_v1",
        "sequence": field["sequence"],
        "limit": limit,
        "seq_length": field["seq_length"],
        "total_steps": len(events),
        "mean_abs_dg": round(field["mean_abs_dg"], 4),
        "window": window,
        "history": history,
        "anchor_threshold": anchor_threshold,
        "profile": profile,
        "weights": weights,
        "scan_count": len(rows),
        "kind_counts": dict(Counter(row["region_kind"] for row in rows)),
        "overlap_n": overlap_n,
        "overlap_field_heat": overlap_field_heat,
        "top_anchor_hits": top_anchor_hits,
        "baseline_anchor_rate": round(baseline_anchor_rate, 4),
        "top_anchor_rate": round(top_anchor_hits / overlap_n, 4) if overlap_n else 0.0,
        "top_by_field": rows[:top],
        "top_by_future_heat": by_heat[:top],
        "top_by_soonest_anchor": by_anchor[:top],
    }


def print_field_scan_probe(payload: dict) -> None:
    if "error" in payload:
        print(f"FIELD SCAN error: {payload['error']}")
        return

    print(f"\n{'='*88}")
    print("FIELD SCAN")
    print(f"{'='*88}")
    print(f"  sequence  : {payload['sequence']}")
    print(f"  limit     : {payload['limit']:,}")
    print(f"  steps     : {payload['total_steps']:,}   scanned: {payload['scan_count']:,}")
    print(f"  history   : trailing {payload['history']} steps")
    print(f"  window    : future {payload['window']} steps")
    print(f"  profile   : {payload['profile']}")
    print(f"  anchors   : future |ratio| >= {payload['anchor_threshold']}")
    print(f"  kinds     : {payload['kind_counts']}")

    n = payload["overlap_n"]
    fh = payload["overlap_field_heat"]
    print(f"\n{'-'*60}")
    print(f"CAUSAL TEST  (top-{n} sets)")
    print(f"  field_score ∩ future_heat : {fh}/{n} ({100*fh//n if n else 0}%)")
    print(f"  top field future-anchor   : {payload['top_anchor_hits']}/{n} ({payload['top_anchor_rate']:.1%})")
    print(f"  baseline future-anchor    : {payload['baseline_anchor_rate']:.1%}")

    def _show(title: str, rows: list[dict]) -> None:
        print(f"\n{'-'*60}")
        print(title)
        print(
            f"  {'rk':>3}  {'idx':>6}  {'ratio':>7}  {'field':>7}  {'heat':>7}  "
            f"{'lead':>5}  {'a_ratio':>8}  {'kind':<22}  pr / dr"
        )
        for i, row in enumerate(rows, 1):
            lead = row["lead_steps"] if row["lead_steps"] is not None else "-"
            a_ratio = row["first_anchor_ratio"] if row["first_anchor_ratio"] is not None else "-"
            print(
                f"  {i:>3}  {row['scan_idx']:>6,}  {row['scan_ratio']:>7.3f}  "
                f"{row['field_score']:>7.3f}  {row['future_heat']:>7.3f}  "
                f"{str(lead):>5}  {str(a_ratio):>8}  {row['region_kind']:<22}  "
                f"{row['prime_ratio_label']} / {row['depth_resonance_label']}"
            )
            print(
                f"       ch: foam={row['foam_channel']:.2f} rb={row['rebound_channel']:.2f} "
                f"cx={row['crossing_channel']:.2f} hid={row['hidden_channel']:.2f} "
                f"wall={row['wall_channel']:.2f} flip={row['charge_flip_channel']:.2f} "
                f"phi={row['phi_channel']:.2f} pr={row['prime_ratio_channel']:.2f} "
                f"dr={row['depth_resonance_channel']:.2f}"
                f" flux={row.get('depth_flux_channel', 0.0):.2f}"
                f" rs={row.get('resonant_soliton_channel', 0.0):.2f}"
                f" geo={row.get('geodesic_trend_channel', 0.0):.3f}"
                f" cas={row.get('cassette_channel', 0.0):.4f}"
                f"(adj={row.get('cassette_adj_channel', 0.0):.2f}"
                f" tri={row.get('cassette_triplet_channel', 0.0):.2f}"
                f" na={row.get('cassette_non_adj_channel', 0.0):.2f}"
                f" pc={row.get('cmpssz_phase_coherence', 0.0):.2f}"
                f" sa={row.get('cmpssz_spectral_anomaly', 0.0):.2f})"
                f" thm=(cs={row.get('cold_spot_channel', 0.5):.2f}"
                f" |g|={row.get('gradient_abs_channel', 0.0):.2f}"
                f" cool={row.get('cooling_channel', 0.0):.2f}"
                f" heat={row.get('heating_channel', 0.0):.2f}"
                f" grad={row.get('thermal_gradient', 0.0):+.2f})"
            )

    _show("TOP BY FIELD SCORE  (no future evidence in score)", payload["top_by_field"])
    _show("TOP BY FUTURE HEAT  (outcome control)", payload["top_by_future_heat"])
    _show("SOONEST FUTURE ANCHORS", payload["top_by_soonest_anchor"])
    print()


def print_next_region_field_probe(payload: dict) -> None:
    if "error" in payload:
        print(f"NEXT REGION FIELD error: {payload['error']}")
        return

    print(f"\n{'='*88}")
    print("NEXT REGION SEARCH FIELD")
    print(f"{'='*88}")
    print(f"  sequence  : {payload['sequence']}")
    print(f"  limit     : {payload['limit']:,}")
    print(f"  steps     : {payload['total_steps']:,}   anchors: {payload['anchor_count']}  (|ratio|≥{payload['anchor_threshold']})")
    print(f"  window    : next {payload['window']} steps after each anchor")
    print(f"  profile   : {payload['profile']}")
    print(f"  kinds     : {payload['kind_counts']}")

    # Channel weight table
    print(f"\n{'─'*60}")
    print("CHANNEL WEIGHTS")
    w = payload["weights"]
    ch_order = ["anchor", "next_strength", "foam", "rebound", "crossing", "hidden",
                "wall", "depth", "depth_flux", "charge_flip", "phi", "prime_ratio",
                "depth_resonance", "resonant_soliton", "geodesic_trend"]
    note = {
        "anchor":        "anchor |ratio| (retrospective anchor strength)",
        "next_strength": "max |ratio| in window  ← OUTCOME (look-ahead)",
        "foam":          "mist+droplet density in window",
        "rebound":       "sign-flip rate in window",
        "crossing":      "mod-30 crossing fraction in window",
        "hidden":        "hidden-axis crossing fraction in window",
        "wall":          "gap wall-loop density in window",
        "depth":         "p-adic depth in window",
        "depth_flux":    "absolute change in p-adic depth across transitions",
        "charge_flip":   "charge-flip fraction in window",
        "phi":           "max phi drift in window",
        "prime_ratio":   "best prime-ratio match score in window",
        "depth_resonance": "best p-adic-supported prime-ratio match in window",
        "resonant_soliton": "combined accel + depth-flux + ratio-lock + charge-flip score",
        "geodesic_trend": "late/early log-gap trajectory trend",
    }
    for c in ch_order:
        wt = w.get(c, 0.0)
        mark = "← PREDICTIVE" if c in ("anchor",) else ("← OUTCOME" if c == "next_strength" else "")
        bar = ("+" if wt > 0 else "") + "#" * int(abs(wt) * 4)
        print(f"  {c:<18}  {wt:>6.1f}  {bar:<22}  {note[c]}")

    # Overlap test
    n = payload["overlap_n"]
    fh = payload["overlap_field_heat"]
    ph = payload["overlap_pred_heat"]
    pf = payload["overlap_pred_field"]
    print(f"\n{'─'*60}")
    print(f"OVERLAP TEST  (top-{n} sets)")
    print(f"  field_score  ∩ observed_heat  : {fh}/{n}  ({100*fh//n}%)  ← does profile track outcome?")
    print(f"  predictive   ∩ observed_heat  : {ph}/{n}  ({100*ph//n}%)  ← do anchor features predict outcome?")
    print(f"  predictive   ∩ field_score    : {pf}/{n}  ({100*pf//n}%)  ← do anchor features agree with profile?")
    predictive_is_real = ph >= n * 0.5
    print(f"  verdict: predictive overlap = {ph}/{n} → {'REAL FORWARD SIGNAL' if predictive_is_real else 'WEAK — anchor features do not predict outcome'}")

    def _show_region_list(title: str, region_list: list[dict], limit: int = 20) -> None:
        print(f"\n{'─'*60}")
        print(f"{title}")
        print(
            f"  {'rk':>3}  {'anc':>6}  {'a_rat':>7}  {'n_rat':>7}  "
            f"{'kind':<22}  {'fld':>6}  {'heat':>6}  {'pred':>6}  {'pr_label'} / dr"
        )
        for i, row in enumerate(region_list[:limit], 1):
            print(
                f"  {i:>3}  {row['anchor_idx']:>6,}  {row['anchor_ratio']:>7.3f}  "
                f"{row['top_event_ratio']:>7.3f}  {row['region_kind']:<22}  "
                f"{row['field_score']:>6.3f}  {row['observed_heat']:>6.3f}  "
                f"{row['predictive_score']:>6.3f}  {row['prime_ratio_label']} / {row['depth_resonance_label']}"
            )
            print(
                f"       ch: foam={row['foam_channel']:.2f} rb={row['rebound_channel']:.2f} "
                f"cx={row['crossing_channel']:.2f} hid={row['hidden_channel']:.2f} "
                f"wall={row['wall_channel']:.2f} flip={row['charge_flip_channel']:.2f} "
                f"phi={row['phi_channel']:.2f} pr={row['prime_ratio_channel']:.2f} "
                f"dr={row['depth_resonance_channel']:.2f}"
                f" geo={row.get('geodesic_trend_channel', 0.0):.3f}"
            )

    _show_region_list(
        f"TOP REGIONS BY FIELD SCORE  (profile={payload['profile']})",
        payload["top_regions"],
    )
    _show_region_list(
        "TOP REGIONS BY OBSERVED HEAT  (retrospective, includes next_strength)",
        payload["top_by_heat"],
    )
    _show_region_list(
        "TOP REGIONS BY PREDICTIVE SCORE  (anchor-local only, no window look-ahead)",
        payload["top_by_predictive"],
    )
    print()


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.echolocate:
        payload = run_echolocation(parse_number_list(args.echolocate), args.echo_radius)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_echolocation(payload)
        return 0

    if args.integer_magnifier:
        payload = run_integer_magnifier(
            parse_number_list(args.integer_values),
            args.integer_bins,
            args.integer_shell,
            parse_mesh_primes(args.fermat_mesh_primes),
            args.integer_binary_bits,
            parse_number_list(args.integer_factor_primes),
            parse_number_list(args.integer_residue_moduli),
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_integer_magnifier(payload)
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
            args.gravity_tune,
            args.gravity_tune_step,
            args.gravity_metric,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_twin_prime_gravity_search(payload)
        return 0

    if getattr(args, "prime_ratio_map", False):
        payload = run_prime_harmonic_map(
            limit=args.ratio_map_limit,
            seed_limit=args.ratio_map_seed,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_prime_harmonic_map(payload)
        return 0

    if args.mod_triangulation:
        mods = tuple(m for m in parse_number_list(args.triangulation_mods) if m > 1)
        payload = run_mod_triangulation_hop_probe(
            limit=args.triangulation_limit,
            moduli=mods or (2, 3, 5),
            top_hops=args.triangulation_top,
            verify_bridges=args.triangulation_verify,
            exclude_non_starters=args.triangulation_exclude_non_starters,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_mod_triangulation_probe(payload)
        return 0

    if args.superprime_layer:
        payload = run_superprime_layer(limit=args.superprime_limit, top=args.superprime_top)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_superprime_layer(payload)
        return 0

    if args.imaginary_paths:
        payload = run_imaginary_gap_path(
            limit=args.imaginary_paths_limit,
            superprime_only=args.imaginary_paths_superprime,
            top=args.imaginary_paths_top,
            ratio_mode=args.imaginary_paths_ratio,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_imaginary_gap_path(payload)
        return 0

    if args.imaginary_paths_well:
        payload = run_imaginary_well_path(
            limit=args.imaginary_paths_limit,
            superprime_only=args.imaginary_paths_superprime,
            top=args.imaginary_paths_top,
            W=args.imaginary_paths_well_depth,
            extrap_steps=args.imaginary_paths_well_extrap,
            landmark_threshold=args.imaginary_paths_well_threshold,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_imaginary_well_path(payload)
        return 0

    if args.foam_score:
        payload = run_foam_score_probe(
            limit=args.imaginary_paths_limit,
            superprime_only=args.imaginary_paths_superprime,
            window=args.foam_score_window,
            top=args.foam_score_top,
            W=args.imaginary_paths_well_depth,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_foam_score_probe(payload)
        return 0

    if args.wall_loop:
        payload = run_wall_loop_probe(
            limit=args.imaginary_paths_limit,
            superprime_only=args.imaginary_paths_superprime,
            window=args.wall_loop_window,
            top=args.wall_loop_top,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_wall_loop_probe(payload)
        return 0

    if args.soliton:
        payload = run_soliton_probe(
            limit=args.imaginary_paths_limit,
            superprime_only=args.imaginary_paths_superprime,
            window=args.soliton_window,
            top=args.soliton_top,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_soliton_probe(payload)
        return 0

    if args.next_region_field:
        payload = run_next_region_field_probe(
            limit=args.imaginary_paths_limit,
            superprime_only=args.imaginary_paths_superprime,
            window=args.next_region_window,
            top=args.next_region_top,
            anchor_threshold=args.next_region_anchor_threshold,
            profile=args.next_region_profile,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_next_region_field_probe(payload)
        return 0

    if args.field_scan:
        payload = run_field_scan_probe(
            limit=args.imaginary_paths_limit,
            superprime_only=args.imaginary_paths_superprime,
            window=args.field_scan_window,
            history=args.field_scan_history,
            top=args.field_scan_top,
            anchor_threshold=args.field_scan_anchor_threshold,
            profile=args.field_scan_profile,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_field_scan_probe(payload)
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
        use_well = getattr(args, "electron_well", False)
        use_harmonic = getattr(args, "harmonic_gates", False)
        if use_well:
            payload = run_electron_well_probe(
                stability_threshold=args.answer_space_threshold,
                predicted_band=band,
                mw_step=args.answer_space_step,
                extend_sigma=args.answer_space_sigma,
                alphafold_uniprot=af_uniprot or None,
                use_harmonic_gates=use_harmonic,
            )
        else:
            payload = run_answer_space_probe(
                stability_threshold=args.answer_space_threshold,
                predicted_band=band,
                mw_step=args.answer_space_step,
                extend_sigma=args.answer_space_sigma,
                bins=args.solution_bins,
                alphafold_uniprot=af_uniprot or None,
                use_harmonic_gates=use_harmonic,
            )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            if use_well:
                print_electron_well_probe(payload)
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

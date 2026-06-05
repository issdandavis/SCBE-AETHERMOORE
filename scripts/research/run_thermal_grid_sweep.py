"""Cached thermal grid sweep runner for the prime fog field scan.

Builds the expensive superprime event field once, then evaluates the 12 IGCT
thermal profiles against that same field. This avoids rerunning the 50M sieve
for every weight profile.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from itertools import product
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.research import prime_fog_of_war_probe as probe


DEFAULT_COLD_SPOTS = [2, 3, 4]
DEFAULT_GRADIENT_ABS = [3, 4, 5, 6, 7, 8]
DEFAULT_OUT_DIR = Path("artifacts/prime_fog_sweep")


def load_done(results_file: Path) -> set[str]:
    done: set[str] = set()
    if results_file.exists():
        for line in results_file.read_text(encoding="utf-8").splitlines()[1:]:
            parts = line.split("\t")
            if parts:
                done.add(parts[0])
    return done


def append_result(results_file: Path, row: dict[str, Any]) -> None:
    header = (
        "profile\tcold_spot\tgradient_abs\ttop_anchor_hits\ttop_anchor_rate\t"
        "baseline_anchor_rate\tlift\toverlap_field_heat\tscan_count\telapsed_s\tstatus\n"
    )
    if not results_file.exists():
        results_file.write_text(header, encoding="utf-8")
    with results_file.open("a", encoding="utf-8") as handle:
        handle.write(
            "{profile}\t{cold_spot}\t{gradient_abs}\t{top_anchor_hits}\t"
            "{top_anchor_rate}\t{baseline_anchor_rate}\t{lift}\t{overlap_field_heat}\t"
            "{scan_count}\t{elapsed_s:.2f}\t{status}\n".format(**row)
        )


def parse_int_list(raw: str) -> list[int]:
    values = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        values.append(int(part))
    if not values:
        raise ValueError("integer list cannot be empty")
    return values


def grid_from_args(args: argparse.Namespace) -> list[tuple[int, int]]:
    return list(product(parse_int_list(args.cold_spots), parse_int_list(args.gradient_abs)))


def ensure_igct_profiles(grid: list[tuple[int, int]]) -> None:
    template = probe._NEXT_REGION_PROFILES["igct_c2_g3"].copy()  # noqa: SLF001
    for cold_spot, gradient_abs in grid:
        profile = f"igct_c{cold_spot}_g{gradient_abs}"
        weights = template.copy()
        weights["cold_spot"] = float(cold_spot)
        weights["gradient_abs"] = float(gradient_abs)
        probe._NEXT_REGION_PROFILES[profile] = weights  # type: ignore[attr-defined]  # noqa: SLF001


def build_field_once(limit: int, superprime_only: bool, out_dir: Path) -> dict[str, Any]:
    summary_path = out_dir / "field_summary.json"
    started = time.time()
    print(
        f"Building event field once: limit={limit:,} superprime_only={superprime_only}",
        flush=True,
    )
    field = probe._build_superprime_event_field(limit, superprime_only)  # noqa: SLF001
    elapsed = time.time() - started
    summary = {
        "schema_version": "prime_fog_sweep_field_summary_v1",
        "limit": limit,
        "superprime_only": superprime_only,
        "elapsed_s": round(elapsed, 3),
        "error": field.get("error"),
        "sequence": field.get("sequence"),
        "seq_length": field.get("seq_length"),
        "event_count": len(field.get("events", [])),
        "mean_abs_dg": field.get("mean_abs_dg"),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        "Field ready: events={event_count:,} seq_length={seq_length} elapsed={elapsed_s:.1f}s".format(
            event_count=summary["event_count"],
            seq_length=summary["seq_length"],
            elapsed_s=summary["elapsed_s"],
        ),
        flush=True,
    )
    return field


def install_cached_field(field: dict[str, Any], limit: int, superprime_only: bool) -> None:
    original_builder = probe._build_superprime_event_field  # noqa: SLF001

    def cached_builder(requested_limit: int, requested_superprime_only: bool) -> dict[str, Any]:
        if requested_limit == limit and requested_superprime_only == superprime_only:
            return field
        return original_builder(requested_limit, requested_superprime_only)

    probe._build_superprime_event_field = cached_builder  # type: ignore[attr-defined]  # noqa: SLF001


def profile_payload(
    profile: str,
    limit: int,
    superprime_only: bool,
    window: int,
    history: int,
    top: int,
    anchor_threshold: float,
) -> dict[str, Any]:
    return probe.run_field_scan_probe(
        limit=limit,
        superprime_only=superprime_only,
        window=window,
        history=history,
        top=top,
        anchor_threshold=anchor_threshold,
        profile=profile,
    )


def write_profile_log(log_file: Path, payload: dict[str, Any], elapsed: float) -> None:
    if "error" in payload:
        log_file.write_text(
            f"profile={payload.get('profile', '?')}\nerror={payload['error']}\nelapsed_s={elapsed:.2f}\n",
            encoding="utf-8",
        )
        return

    lines = [
        f"profile={payload['profile']}",
        f"limit={payload['limit']}",
        f"scan_count={payload['scan_count']}",
        f"top_anchor_hits={payload['top_anchor_hits']}/{payload['overlap_n']}",
        f"top_anchor_rate={payload['top_anchor_rate']}",
        f"baseline_anchor_rate={payload['baseline_anchor_rate']}",
        f"overlap_field_heat={payload['overlap_field_heat']}/{payload['overlap_n']}",
        f"elapsed_s={elapsed:.2f}",
        "",
        "top_by_field:",
    ]
    for row in payload.get("top_by_field", [])[:20]:
        lines.append(
            "rank={rank} idx={idx} ratio={ratio} field={field} anchor={anchor} lead={lead} kind={kind}".format(
                rank=row.get("rank"),
                idx=row.get("scan_idx"),
                ratio=row.get("scan_ratio"),
                field=row.get("field_score"),
                anchor=row.get("future_anchor"),
                lead=row.get("lead_steps"),
                kind=row.get("region_kind"),
            )
        )
    log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_sweep(args: argparse.Namespace) -> None:
    grid = grid_from_args(args)
    ensure_igct_profiles(grid)
    out_dir = Path(args.out_dir)
    log_dir = out_dir / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    results_file = out_dir / "results.tsv"

    done = set() if args.reset else load_done(results_file)
    if args.reset and results_file.exists():
        results_file.unlink()
    remaining = [(c, g) for c, g in grid if f"igct_c{c}_g{g}" not in done]

    print(f"Thermal grid sweep: {len(done)}/{len(grid)} done, {len(remaining)} to run")
    print(f"Results: {results_file}", flush=True)
    if not remaining:
        print(results_file.read_text(encoding="utf-8") if results_file.exists() else "")
        return

    field = build_field_once(args.limit, not args.all_primes, out_dir)
    if "error" in field:
        raise RuntimeError(f"field build failed: {field['error']}")
    install_cached_field(field, args.limit, not args.all_primes)

    for index, (cold, gabs) in enumerate(remaining, start=1):
        profile = f"igct_c{cold}_g{gabs}"
        log_file = log_dir / f"{profile}.log"
        json_file = log_dir / f"{profile}.json"
        print(f"[{index}/{len(remaining)}] Evaluating {profile} ...", flush=True)
        started = time.time()
        payload = profile_payload(
            profile=profile,
            limit=args.limit,
            superprime_only=not args.all_primes,
            window=args.window,
            history=args.history,
            top=args.top,
            anchor_threshold=args.anchor_threshold,
        )
        elapsed = time.time() - started
        payload["sweep_elapsed_s"] = round(elapsed, 3)
        json_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        write_profile_log(log_file, payload, elapsed)

        if "error" in payload:
            row = {
                "profile": profile,
                "cold_spot": cold,
                "gradient_abs": gabs,
                "top_anchor_hits": "ERROR",
                "top_anchor_rate": "ERROR",
                "baseline_anchor_rate": "ERROR",
                "lift": "ERROR",
                "overlap_field_heat": "ERROR",
                "scan_count": 0,
                "elapsed_s": elapsed,
                "status": payload["error"],
            }
        else:
            lift = (
                round(payload["top_anchor_rate"] / payload["baseline_anchor_rate"], 4)
                if payload["baseline_anchor_rate"]
                else 0.0
            )
            row = {
                "profile": profile,
                "cold_spot": cold,
                "gradient_abs": gabs,
                "top_anchor_hits": payload["top_anchor_hits"],
                "top_anchor_rate": payload["top_anchor_rate"],
                "baseline_anchor_rate": payload["baseline_anchor_rate"],
                "lift": lift,
                "overlap_field_heat": payload["overlap_field_heat"],
                "scan_count": payload["scan_count"],
                "elapsed_s": elapsed,
                "status": "ok",
            }
        append_result(results_file, row)
        print(
            "  {profile}: top_anchor_rate={rate} hits={hits}/20 baseline={base} elapsed={elapsed:.2f}s".format(
                profile=profile,
                rate=row["top_anchor_rate"],
                hits=row["top_anchor_hits"],
                base=row["baseline_anchor_rate"],
                elapsed=elapsed,
            ),
            flush=True,
        )
        if args.sleep and index < len(remaining):
            time.sleep(args.sleep)

    print("\nSweep complete.")
    print(results_file.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50_000_000)
    parser.add_argument("--window", type=int, default=36)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--anchor-threshold", type=float, default=4.0)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--all-primes", action="store_true")
    parser.add_argument("--cold-spots", default=",".join(str(value) for value in DEFAULT_COLD_SPOTS))
    parser.add_argument("--gradient-abs", default=",".join(str(value) for value in DEFAULT_GRADIENT_ABS))
    run_sweep(parser.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

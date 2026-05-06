"""Multi-seed gate evaluation harness for SCBE training contracts.

Runs an existing eval contract against a pluggable model callable
across multiple decode seeds and temperatures, then reports recall
distribution rather than a single point estimate. Catches seed-lucky
gate claims the same way `mahss_dual_state_sweep.py` catches
landscape-lucky search-method claims.

The lesson from MAHSS: a single-pass evaluation can be a lucky draw.
Existing SCBE training gates use 12 prompts at one decode pass with
one seed -- a "2/12 raw" or "5/5 scaffolded" report has no error bar
on it. This harness adds the audit:
  - per-prompt pass rate
  - per-seed pass rate (the seed-lucky check)
  - per-temperature pass rate
  - 95% Wilson confidence interval on overall pass rate
  - seed-lucky risk (max single-seed rate - min single-seed rate)
  - must_pass coverage (prompts that the contract says must pass)

The harness is contract-aware: it understands the existing
`schema_version: scbe_stage_eval_contract_v1` format with required and
forbidden substring lists. It is model-agnostic: the model callable
receives (prompt_dict, seed, temperature) and returns a string. Bring
your own adapter, HF Inference Endpoint, vLLM, constrained-decoding
shim, or local transformers run.

Output schema (`scbe_multi_seed_gate_eval_v1`):
    {
      "schema_version": "scbe_multi_seed_gate_eval_v1",
      "contract_id": str,
      "n_prompts": int,
      "seeds": [int, ...],
      "temperatures": [float, ...],
      "trials": [
        {
          "prompt_id": str,
          "seed": int,
          "temperature": float,
          "passed": bool,
          "score": float,
          "checker_meta": {...},
          "must_pass": bool
        }
      ],
      "aggregate": {
        "overall": {
          "n_trials": int,
          "passed_count": int,
          "pass_rate": float,
          "wilson_95ci_low": float,
          "wilson_95ci_high": float
        },
        "per_seed": {seed: {pass_rate, n}},
        "per_temperature": {temp: {pass_rate, n}},
        "per_prompt": {prompt_id: {pass_rate, n, must_pass}},
        "seed_lucky_risk": {
          "min_seed_pass_rate": float,
          "max_seed_pass_rate": float,
          "spread": float,
          "single_seed_distribution": [float, ...]
        },
        "must_pass_coverage": {
          "n_must_pass_prompts": int,
          "all_must_pass_pass_in_all_trials": bool,
          "any_must_pass_failures_per_trial": [...]
        }
      }
    }
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA_VERSION = "scbe_multi_seed_gate_eval_v1"

ModelCallable = Callable[[dict, int, float], str]
CheckerCallable = Callable[[dict, str], dict]


@dataclass(frozen=True)
class Trial:
    prompt_id: str
    seed: int
    temperature: float
    passed: bool
    score: float
    checker_meta: dict
    must_pass: bool


def required_forbidden_checker(prompt: dict, completion: str) -> dict:
    """Default checker for `scbe_stage_eval_contract_v1` prompts.

    Matches the existing scoring: case-insensitive substring presence
    for `required`, case-insensitive substring absence for `forbidden`.
    Score is the fraction of required tokens found, minus a penalty
    for any forbidden token. `passed` requires all required present
    and zero forbidden.
    """

    text = (completion or "").lower()
    required: list[str] = [str(s).lower() for s in prompt.get("required", [])]
    forbidden: list[str] = [str(s).lower() for s in prompt.get("forbidden", [])]
    missing = [r for r in required if r not in text]
    triggered = [f for f in forbidden if f in text]
    n_required = max(1, len(required))
    found = len(required) - len(missing)
    score = found / n_required - 0.25 * len(triggered)
    passed = (len(missing) == 0) and (len(triggered) == 0)
    return {
        "passed": bool(passed),
        "score": float(round(score, 4)),
        "meta": {
            "missing_required": missing,
            "triggered_forbidden": triggered,
            "n_required": int(len(required)),
            "n_forbidden": int(len(forbidden)),
        },
    }


def wilson_interval(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Two-sided Wilson score interval at the given z (default 95%)."""

    if total <= 0:
        return (0.0, 0.0)
    p = passed / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (p + z2 / (2 * total)) / denom
    half = (z * math.sqrt(p * (1 - p) / total + z2 / (4 * total * total))) / denom
    low = max(0.0, center - half)
    high = min(1.0, center + half)
    return (round(low, 4), round(high, 4))


def _aggregate(trials: list[Trial], must_pass_ids: set[str]) -> dict[str, Any]:
    n = len(trials)
    passed_count = sum(1 for t in trials if t.passed)
    pass_rate = passed_count / n if n else 0.0
    ci_low, ci_high = wilson_interval(passed_count, n)

    per_seed: dict[int, list[Trial]] = defaultdict(list)
    per_temp: dict[float, list[Trial]] = defaultdict(list)
    per_prompt: dict[str, list[Trial]] = defaultdict(list)
    for t in trials:
        per_seed[t.seed].append(t)
        per_temp[t.temperature].append(t)
        per_prompt[t.prompt_id].append(t)

    def _rate(rows: list[Trial]) -> dict[str, Any]:
        if not rows:
            return {"pass_rate": 0.0, "n": 0, "passed": 0}
        rate = sum(1 for r in rows if r.passed) / len(rows)
        return {
            "pass_rate": round(rate, 4),
            "n": len(rows),
            "passed": sum(1 for r in rows if r.passed),
        }

    seed_distribution = sorted(
        round(_rate(rows)["pass_rate"], 4) for rows in per_seed.values()
    )
    spread = (max(seed_distribution) - min(seed_distribution)) if seed_distribution else 0.0

    must_pass_failures_per_trial_index: list[list[str]] = []
    if must_pass_ids:
        # Group trials by (seed, temperature) so we can ask per-trial-context
        # whether all must_pass prompts passed at that decode setting.
        by_context: dict[tuple[int, float], list[Trial]] = defaultdict(list)
        for t in trials:
            by_context[(t.seed, t.temperature)].append(t)
        for (seed, temp), ctx in sorted(by_context.items()):
            failed_must = [
                t.prompt_id for t in ctx
                if t.must_pass and not t.passed
            ]
            if failed_must:
                must_pass_failures_per_trial_index.append(
                    [str(seed), str(temp), *failed_must]
                )

    all_must_pass = (
        bool(must_pass_ids)
        and all(
            all(
                (not t.must_pass) or t.passed
                for t in trials
                if t.seed == s and t.temperature == temp
            )
            for s in {t.seed for t in trials}
            for temp in {t.temperature for t in trials}
        )
    )

    return {
        "overall": {
            "n_trials": n,
            "passed_count": passed_count,
            "pass_rate": round(pass_rate, 4),
            "wilson_95ci_low": ci_low,
            "wilson_95ci_high": ci_high,
        },
        "per_seed": {str(s): _rate(rows) for s, rows in sorted(per_seed.items())},
        "per_temperature": {
            f"{t:.2f}": _rate(rows) for t, rows in sorted(per_temp.items())
        },
        "per_prompt": {
            pid: {
                **_rate(rows),
                "must_pass": pid in must_pass_ids,
            }
            for pid, rows in sorted(per_prompt.items())
        },
        "seed_lucky_risk": {
            "min_seed_pass_rate": min(seed_distribution) if seed_distribution else 0.0,
            "max_seed_pass_rate": max(seed_distribution) if seed_distribution else 0.0,
            "spread": round(spread, 4),
            "single_seed_distribution": seed_distribution,
        },
        "must_pass_coverage": {
            "n_must_pass_prompts": len(must_pass_ids),
            "all_must_pass_pass_in_all_trials": bool(all_must_pass),
            "must_pass_failures_per_context": must_pass_failures_per_trial_index,
        },
    }


def run_sweep(
    contract: dict,
    model: ModelCallable,
    *,
    seeds: Sequence[int],
    temperatures: Sequence[float],
    checker: CheckerCallable | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run the contract across (prompt, seed, temperature) and aggregate.

    `model` receives (prompt_dict, seed, temperature) and returns a
    completion string. `checker` defaults to the contract-aware
    required/forbidden matcher. `progress` is an optional callback for
    logging.
    """

    if checker is None:
        checker = required_forbidden_checker

    prompts = contract.get("prompts") or []
    must_pass_ids: set[str] = set(contract.get("thresholds", {}).get("must_pass") or [])
    contract_id = contract.get("contract_id", "<unknown>")

    if progress:
        progress(
            f"contract={contract_id} prompts={len(prompts)} "
            f"seeds={list(seeds)} temps={list(temperatures)}"
        )

    trials: list[Trial] = []
    for seed in seeds:
        for temperature in temperatures:
            for prompt in prompts:
                pid = str(prompt.get("id", ""))
                completion = model(prompt, int(seed), float(temperature))
                result = checker(prompt, completion)
                trials.append(
                    Trial(
                        prompt_id=pid,
                        seed=int(seed),
                        temperature=float(temperature),
                        passed=bool(result["passed"]),
                        score=float(result.get("score", 0.0)),
                        checker_meta=dict(result.get("meta", {})),
                        must_pass=pid in must_pass_ids,
                    )
                )

    aggregate = _aggregate(trials, must_pass_ids)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": contract_id,
        "n_prompts": len(prompts),
        "seeds": list(int(s) for s in seeds),
        "temperatures": list(float(t) for t in temperatures),
        "trials": [
            {
                "prompt_id": t.prompt_id,
                "seed": t.seed,
                "temperature": t.temperature,
                "passed": t.passed,
                "score": t.score,
                "checker_meta": t.checker_meta,
                "must_pass": t.must_pass,
            }
            for t in trials
        ],
        "aggregate": aggregate,
    }


def synthetic_oracle_model(success_rate: float = 1.0, *, jitter_seed: int = 0) -> ModelCallable:
    """Return a deterministic oracle model that emits the joined required tokens.

    Useful for harness self-tests: when `success_rate=1.0` every trial
    passes; lower values randomly omit required tokens to drive partial
    failures conditional on (prompt_id, seed, temperature). The output
    is reproducible: same (prompt, seed, temperature) -> same string.
    """

    def model(prompt: dict, seed: int, temperature: float) -> str:
        required = list(prompt.get("required", []))
        if success_rate >= 1.0 or not required:
            return " ".join(required)
        # Deterministic per-trial drop of required tokens
        h = (
            hash((str(prompt.get("id", "")), int(seed), int(round(float(temperature) * 100)), jitter_seed))
            & 0xFFFF_FFFF
        )
        rng = h / 0xFFFF_FFFF
        if rng > success_rate:
            kept = required[: max(0, len(required) - 1)]
            return " ".join(kept)
        return " ".join(required)

    return model


def _import_dotted(spec: str) -> Any:
    """Resolve `module.path:attribute` to the named attribute."""

    if ":" not in spec:
        raise ValueError(f"expected 'module:attribute' got {spec!r}")
    module_path, attr = spec.split(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr)


def _load_contract(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _summarize_console(report: dict[str, Any]) -> None:
    agg = report["aggregate"]
    overall = agg["overall"]
    risk = agg["seed_lucky_risk"]
    must_pass = agg["must_pass_coverage"]
    print(
        f"\ncontract={report['contract_id']} "
        f"prompts={report['n_prompts']} seeds={report['seeds']} "
        f"temperatures={report['temperatures']}"
    )
    print(
        f"overall pass_rate={overall['pass_rate']:.3f}  "
        f"95% CI [{overall['wilson_95ci_low']:.3f}, {overall['wilson_95ci_high']:.3f}]  "
        f"({overall['passed_count']}/{overall['n_trials']})"
    )
    print(
        f"seed-lucky risk: spread={risk['spread']:.3f}  "
        f"min={risk['min_seed_pass_rate']:.3f}  max={risk['max_seed_pass_rate']:.3f}  "
        f"single-seed-distribution={risk['single_seed_distribution']}"
    )
    print(
        f"must_pass coverage: "
        f"{must_pass['n_must_pass_prompts']} must-pass prompts; "
        f"all-pass-everywhere={must_pass['all_must_pass_pass_in_all_trials']}"
    )
    if must_pass["must_pass_failures_per_context"]:
        print("  must_pass failures by (seed, temp):")
        for row in must_pass["must_pass_failures_per_context"][:10]:
            print(f"    {row}")
    print("\nper-prompt pass rates:")
    for pid, row in agg["per_prompt"].items():
        marker = "*" if row["must_pass"] else " "
        print(f"  {marker} {pid:<48} {row['pass_rate']:.2f}  ({row['passed']}/{row['n']})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        required=True,
        help="Path to a scbe_stage_eval_contract_v1 JSON.",
    )
    parser.add_argument(
        "--model-spec",
        type=str,
        default="scripts.eval.multi_seed_gate_eval:synthetic_oracle_model",
        help="`module:callable` resolvable to either a ModelCallable or a "
        "factory returning one. Default is the built-in synthetic oracle.",
    )
    parser.add_argument(
        "--checker-spec",
        type=str,
        default="scripts.eval.multi_seed_gate_eval:required_forbidden_checker",
        help="`module:callable` resolving to a CheckerCallable.",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="0,1,2,3,4",
        help="Comma-separated decode seeds (default: 0..4).",
    )
    parser.add_argument(
        "--temperatures",
        type=str,
        default="0.0,0.5,1.0",
        help="Comma-separated decode temperatures (default: 0.0,0.5,1.0).",
    )
    parser.add_argument(
        "--success-rate",
        type=float,
        default=1.0,
        help="Synthetic-oracle pass rate (only used when model-spec is the default oracle).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/eval/multi_seed_gate_eval.json"),
    )
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    contract = _load_contract(args.contract)
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    temperatures = [float(t) for t in args.temperatures.split(",") if t.strip()]

    model_obj = _import_dotted(args.model_spec)
    if callable(model_obj) and not _is_model_callable_signature(model_obj):
        # Likely a factory; call it to get the actual model.
        try:
            model: ModelCallable = model_obj(success_rate=args.success_rate)
        except TypeError:
            model = model_obj()  # type: ignore[assignment]
    else:
        model = model_obj  # type: ignore[assignment]

    checker = _import_dotted(args.checker_spec)

    progress = (lambda msg: None) if args.quiet else (lambda msg: print(msg))
    t0 = time.time()
    report = run_sweep(
        contract,
        model,
        seeds=seeds,
        temperatures=temperatures,
        checker=checker,
        progress=progress,
    )
    report["elapsed_s"] = round(time.time() - t0, 3)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not args.quiet:
        _summarize_console(report)
        print(f"\nwrote {args.output}")
    return 0


def _is_model_callable_signature(fn: Callable) -> bool:
    """Heuristic: a ModelCallable accepts (prompt, seed, temperature)."""

    import inspect

    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return True
    params = [p for p in sig.parameters.values() if p.kind not in (
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.VAR_KEYWORD,
    )]
    return len(params) >= 3


if __name__ == "__main__":
    raise SystemExit(main())

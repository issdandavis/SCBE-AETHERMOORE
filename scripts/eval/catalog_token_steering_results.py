"""Catalog token-steering evidence and recommended next actions.

This is a no-GPU training ops helper. It reads existing constrained-decoding
and bijective gate artifacts, classifies the observed failure shape, and writes
a concise operator report. The goal is to prevent solution shopping: use
prompting, constrained decoding, verifier repair, activation steering, or SFT
only when the recorded failures actually call for that tool.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_JSON_OUT = REPO / "artifacts/eval/token_steering_decision_matrix_2026-05-07.json"
DEFAULT_MD_OUT = REPO / "docs/ops/TOKEN_STEERING_FAILURE_CATALOG_2026-05-07.md"


@dataclass(frozen=True)
class ArtifactSummary:
    path: str
    schema: str
    n: int
    passed: int
    pass_rate: float
    missing_required: int
    forbidden_triggered: int
    syntax_or_exec_failures: int
    assertion_failures: int
    note: str


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _summarize_multi_seed(path: Path, data: dict[str, Any]) -> ArtifactSummary:
    trials = list(data.get("trials") or [])
    passed = sum(1 for t in trials if bool(t.get("passed")))
    missing_required = 0
    forbidden_triggered = 0
    for trial in trials:
        meta = trial.get("checker_meta") or {}
        missing_required += len(meta.get("missing_required") or [])
        forbidden_triggered += len(meta.get("triggered_forbidden") or [])
    n = len(trials)
    return ArtifactSummary(
        path=str(path.relative_to(REPO)),
        schema=str(data.get("schema_version") or data.get("schema") or "unknown"),
        n=n,
        passed=passed,
        pass_rate=round(passed / n, 4) if n else 0.0,
        missing_required=missing_required,
        forbidden_triggered=forbidden_triggered,
        syntax_or_exec_failures=0,
        assertion_failures=0,
        note="multi-seed required/forbidden contract audit",
    )


def _summarize_bijective(path: Path, data: dict[str, Any]) -> ArtifactSummary:
    results = list(data.get("results") or [])
    passed = sum(1 for r in results if bool(r.get("repaired_tests_passed") or r.get("tests_passed")))
    syntax_or_exec = 0
    assertions = 0
    for result in results:
        if not bool(result.get("syntax_ok", True)) or not bool(result.get("exec_ok", True)):
            syntax_or_exec += 1
        error = str(result.get("error") or result.get("repaired_error") or "")
        if "AssertionError" in error:
            assertions += 1
    n = len(results)
    return ArtifactSummary(
        path=str(path.relative_to(REPO)),
        schema=str(data.get("schema") or data.get("schema_version") or "unknown"),
        n=n,
        passed=passed,
        pass_rate=round(passed / n, 4) if n else float(data.get("repaired_pass_rate") or 0.0),
        missing_required=0,
        forbidden_triggered=0,
        syntax_or_exec_failures=syntax_or_exec,
        assertion_failures=assertions,
        note="bijective round-trip code execution audit",
    )


def discover_artifacts(root: Path = REPO) -> list[Path]:
    candidates: list[Path] = []
    for folder in (
        root / "artifacts/eval",
        root / "artifacts/hf_eval_results",
        root / "artifacts/bijective_tongue",
    ):
        if not folder.exists():
            continue
        for path in folder.glob("*.json"):
            name = path.name.lower()
            if "constrained" in name or "multi_seed" in name or "local_constrained" in name:
                candidates.append(path)
    return sorted(candidates)


def summarize_artifacts(paths: list[Path]) -> list[ArtifactSummary]:
    summaries: list[ArtifactSummary] = []
    for path in paths:
        data = _load_json(path)
        if not data:
            continue
        schema = str(data.get("schema_version") or data.get("schema") or "")
        if "bijective_tongue_gate" in schema or "local_constrained" in path.name:
            summaries.append(_summarize_bijective(path, data))
        elif "multi_seed" in schema or "constrained" in path.name:
            summaries.append(_summarize_multi_seed(path, data))
    return summaries


def build_decision_matrix(summaries: list[ArtifactSummary]) -> dict[str, Any]:
    totals = {
        "n": sum(s.n for s in summaries),
        "passed": sum(s.passed for s in summaries),
        "missing_required": sum(s.missing_required for s in summaries),
        "forbidden_triggered": sum(s.forbidden_triggered for s in summaries),
        "syntax_or_exec_failures": sum(s.syntax_or_exec_failures for s in summaries),
        "assertion_failures": sum(s.assertion_failures for s in summaries),
    }
    totals["pass_rate"] = round(totals["passed"] / totals["n"], 4) if totals["n"] else 0.0

    if totals["missing_required"]:
        primary = "constrained_decoding_or_contract_prefix"
        reason = "required tokens are missing; force the contract before spending on SFT"
    elif totals["forbidden_triggered"]:
        primary = "logit_mask_or_verifier_rejection"
        reason = "structure is present but continuation drifts into forbidden tokens"
    elif totals["syntax_or_exec_failures"]:
        primary = "verifier_repair_loop"
        reason = "output shape reaches code but fails parser/runtime"
    elif totals["assertion_failures"]:
        primary = "targeted_training_or_activation_vector"
        reason = "syntax is fine but behavior is semantically wrong"
    else:
        primary = "harden_ci_and_expand_coverage"
        reason = "current checked artifacts are green; broaden coverage before more training"

    return {
        "schema_version": "scbe_token_steering_decision_matrix_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "totals": totals,
        "recommendation": {
            "primary_next_action": primary,
            "reason": reason,
            "do_not_do_next": (
                "Do not launch a new fine-tune solely to solve schema or required-token "
                "failures; those are steering/gating problems first."
            ),
        },
        "routing_rules": [
            {
                "failure_shape": "missing required markers or fixed schema fields",
                "use": "constrained decoding / forced prefix",
            },
            {
                "failure_shape": "forbidden token appears after a valid prefix",
                "use": "logit mask, rejection sampling, or verifier retry",
            },
            {
                "failure_shape": "syntax error or runtime/import error",
                "use": "compiler/interpreter verifier repair loop",
            },
            {
                "failure_shape": "code runs but assertions fail consistently",
                "use": "targeted SFT, DPO, or activation control vector",
            },
            {
                "failure_shape": "large seed-to-seed variance",
                "use": "best-of-N verifier search before changing weights",
            },
        ],
        "artifacts": [s.__dict__ for s in summaries],
    }


def render_markdown(matrix: dict[str, Any]) -> str:
    totals = matrix["totals"]
    rec = matrix["recommendation"]
    lines = [
        "# Token Steering Failure Catalog",
        "",
        f"Generated: {matrix['generated_at_utc']}",
        "",
        "## Bottom Line",
        "",
        f"Primary next action: `{rec['primary_next_action']}`.",
        "",
        rec["reason"],
        "",
        rec["do_not_do_next"],
        "",
        "## Current Evidence Summary",
        "",
        f"- Checked trials/results: {totals['passed']}/{totals['n']} passed "
        f"({totals['pass_rate']:.4f}).",
        f"- Missing-required incidents: {totals['missing_required']}",
        f"- Forbidden-token incidents: {totals['forbidden_triggered']}",
        f"- Syntax/runtime incidents: {totals['syntax_or_exec_failures']}",
        f"- Semantic assertion incidents: {totals['assertion_failures']}",
        "",
        "## Steering Routing Rules",
        "",
    ]
    for row in matrix["routing_rules"]:
        lines.append(f"- If `{row['failure_shape']}` -> use `{row['use']}`.")
    lines.extend(["", "## Artifact Table", ""])
    lines.append("| Artifact | Schema | Passed | Missing | Forbidden | Syntax/Exec | Assertions | Note |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|")
    for row in matrix["artifacts"]:
        lines.append(
            f"| `{row['path']}` | `{row['schema']}` | {row['passed']}/{row['n']} "
            f"({row['pass_rate']:.4f}) | {row['missing_required']} | "
            f"{row['forbidden_triggered']} | {row['syntax_or_exec_failures']} | "
            f"{row['assertion_failures']} | {row['note']} |"
        )
    lines.extend(
        [
            "",
            "## Production Hooks Already Available",
            "",
            "- `src/governance/coding_eval_constrained_decoding.py::build_bad_words_ids` converts forbidden strings into decode-time masks.",
            "- `coding_eval_constrained_response(..., suppress_forbidden=True)` applies those masks during generation.",
            "- `coding_eval_best_of_n_response(...)` retries deterministic decode contexts and returns the first verified pass.",
            "- Focused guard test: `python -m pytest tests/governance/test_coding_eval_constrained_decoding.py -q`.",
            "",
            "## Operational Decision",
            "",
            "The checked constrained-decoding and bijective artifacts do not justify a new training run by themselves.",
            "The next zero-cost work is to wire this catalog into CI, keep forbidden-token suppression enabled for drift-prone gates, and expand the contract coverage until a real semantic failure shape appears.",
            "Activation vectors are worth scoping only for repeated semantic assertion failures, not for schema compliance.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    args = parser.parse_args(argv)

    summaries = summarize_artifacts(discover_artifacts())
    matrix = build_decision_matrix(summaries)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.md_out.write_text(render_markdown(matrix), encoding="utf-8")
    print(json.dumps({"json": str(args.json_out), "md": str(args.md_out), "summary": matrix["totals"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

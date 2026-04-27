#!/usr/bin/env python3
"""Build a useful promotion/evaluation matrix for SCBE training runs.

The point is not another metric dump. This script consolidates scattered
training, frozen-eval, DSL executable, Stage 6, and functional benchmark
signals into a single decision board:

- what improved;
- what broke;
- what is still unevaluated;
- whether the adapter is routable, merge-blocked, or quarantined.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINING_REPORTS = REPO_ROOT / "artifacts" / "training_reports"
FROZEN_EVALS = REPO_ROOT / "artifacts" / "model_evals" / "frozen"
DSL_EVALS = REPO_ROOT / "artifacts" / "dsl_eval_reports"
FUNCTIONAL_LATEST = REPO_ROOT / "artifacts" / "coding_agent_benchmarks" / "latest" / "report.json"
OUT_DIR = REPO_ROOT / "artifacts" / "training_evaluation_matrix"


LANE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("dsl_synthesis", ("dsl", "synthesis", "well", "executable")),
    ("bijective_tongue", ("bijective", "tongue", "cross_tongue", "langues")),
    ("binary_hex", ("binary", "hex", "byte", "ieee")),
    ("coding_approval", ("approval", "metric", "governance", "review")),
    ("regularized_coding", ("regularized", "coding-v8", "coding_model")),
    ("stage6_repair", ("stage6", "repair", "atomic_workflow")),
    ("operator_bus", ("operator", "agent_bus", "bus")),
)
GENERIC_MATCH_TOKENS = {
    "adapter",
    "agent",
    "artifacts",
    "auto",
    "coding",
    "hfjobs",
    "issdandavis",
    "kaggle",
    "model",
    "output",
    "polly",
    "qwen",
    "scbe",
    "the",
    "v1",
    "v2",
    "v3",
    "v4",
    "v5",
    "v6",
    "v7",
    "v8",
}


@dataclass
class Gate:
    name: str
    status: str = "unknown"
    value: str = "-"
    evidence: str = "-"
    note: str = "-"


@dataclass
class EvalRow:
    name: str
    lane: str
    adapter: str = "-"
    source_report: str = "-"
    gates: list[Gate] = field(default_factory=list)
    decision: str = "EVAL_REQUIRED"
    next_action: str = "Run missing gates."
    risk_notes: list[str] = field(default_factory=list)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_rel(path: Path | str | None) -> str:
    if not path:
        return "-"
    p = Path(path)
    try:
        return str(p.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def safe_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def classify_lane(text: str) -> str:
    lowered = text.lower()
    for lane, hints in LANE_HINTS:
        if any(hint in lowered for hint in hints):
            return lane
    return "general_coding"


def comparable_key(value: str) -> str:
    text = str(value or "").lower().replace("\\", "/")
    text = text.removeprefix("artifacts/kaggle_output/")
    text = text.removeprefix("issdandavis/")
    text = text.removeprefix("issacizrealdavis/")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def loose_adapter_match(left: str, right: str) -> bool:
    a = comparable_key(left)
    b = comparable_key(right)
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    a_parts = {part for part in a.split("-") if len(part) > 2 and part not in GENERIC_MATCH_TOKENS}
    b_parts = {part for part in b.split("-") if len(part) > 2 and part not in GENERIC_MATCH_TOKENS}
    overlap = a_parts & b_parts
    if len(overlap) < 3:
        return False
    # Avoid matching two unrelated adapters just because they share broad
    # project/model words. At least one distinctive token must be lane-specific.
    distinctive = {"approval", "bijective", "dsl", "geoseal", "regularized", "repair", "stage6", "synthesis", "tongue"}
    return bool(overlap & distinctive)


def status_from_bool(value: Any) -> str:
    if value is True:
        return "pass"
    if value is False:
        return "fail"
    return "unknown"


def status_icon(status: str) -> str:
    return {
        "pass": "PASS",
        "warn": "WARN",
        "fail": "FAIL",
        "unknown": "UNKNOWN",
        "missing": "MISSING",
    }.get(status, status.upper())


def gate_lookup(gates: list[Gate], name: str) -> Gate | None:
    return next((gate for gate in gates if gate.name == name), None)


def summarize_training_health(payload: dict[str, Any]) -> Gate:
    results = payload.get("results") if isinstance(payload.get("results"), dict) else {}
    train_acc = safe_float(results.get("train_token_accuracy_final"))
    eval_acc = safe_float(results.get("eval_token_accuracy_final"))
    train_loss = safe_float(results.get("train_loss_final"))
    eval_loss = safe_float(results.get("eval_loss_final"))
    gap = safe_float(results.get("train_eval_loss_gap_final"))
    epochs = safe_float(results.get("epochs_reached"))

    notes: list[str] = []
    status = "unknown"
    if train_acc is not None or eval_acc is not None or train_loss is not None:
        status = "pass"
    if gap is not None and gap > 1.0:
        status = "warn"
        notes.append(f"loss_gap={gap:.3g}")
    if epochs is not None and epochs > 3:
        status = "warn"
        notes.append(f"effective_epochs={epochs:.3g}")
    if train_acc is not None and train_acc > 0.95:
        status = "warn"
        notes.append(f"train_acc={train_acc:.1%} overfit-risk")

    value_parts = []
    if train_loss is not None:
        value_parts.append(f"train_loss={train_loss:.3g}")
    if eval_loss is not None:
        value_parts.append(f"eval_loss={eval_loss:.3g}")
    if eval_acc is not None:
        value_parts.append(f"eval_acc={eval_acc:.1%}")
    return Gate(
        "token_training",
        status,
        ", ".join(value_parts) or "-",
        "-",
        "; ".join(notes) or payload.get("convergence", "-"),
    )


def summarize_frozen_from_training(payload: dict[str, Any]) -> Gate:
    frozen = (((payload.get("frozen_eval") or {}).get("frozen_perplexity")) or {})
    if not frozen:
        return Gate("frozen_perplexity", "missing", "-", "-", "No frozen perplexity report attached.")
    ppl = safe_float(frozen.get("perplexity"))
    status = str(frozen.get("status") or "unknown").lower()
    if frozen.get("ood_regression_vs_base") is True:
        status = "fail"
    return Gate(
        "frozen_perplexity",
        status,
        f"ppl={ppl:.4g}" if ppl is not None else "-",
        repo_rel(frozen.get("report_path")),
        "OOD regression" if frozen.get("ood_regression_vs_base") else "No OOD regression flag",
    )


def summarize_dsl_from_training(payload: dict[str, Any]) -> Gate:
    dsl = (((payload.get("frozen_eval") or {}).get("dsl_executable_accuracy")) or {})
    if not dsl:
        return Gate("dsl_executable", "missing", "-", "-", "No executable DSL report attached.")
    acc = safe_float(dsl.get("executable_accuracy"))
    gate = safe_float(dsl.get("gate"))
    status = status_from_bool(dsl.get("overall_pass"))
    value = f"acc={acc:.1%}" if acc is not None else "-"
    if gate is not None:
        value += f" / gate={gate:.1%}"
    note = f"floor_violations={dsl.get('floor_violations', '-')}"
    failure_modes = dsl.get("failure_modes")
    if isinstance(failure_modes, dict) and failure_modes:
        note += "; " + ", ".join(f"{k}={v}" for k, v in sorted(failure_modes.items()))
    return Gate("dsl_executable", status, value, repo_rel(dsl.get("report_path")), note)


def summarize_stage6_from_training(payload: dict[str, Any]) -> Gate:
    stage6 = (((payload.get("frozen_eval") or {}).get("stage6_regression")) or {})
    if not stage6:
        return Gate("stage6_regression", "missing", "-", "-", "No Stage 6 regression report attached.")
    rate = safe_float(stage6.get("pass_rate"))
    minimum = safe_float(stage6.get("minimum_pass_rate"))
    status = status_from_bool(stage6.get("overall_pass"))
    value = f"pass_rate={rate:.1%}" if rate is not None else "-"
    if minimum is not None:
        value += f" / min={minimum:.1%}"
    return Gate("stage6_regression", status, value, repo_rel(stage6.get("report_path")), "must-pass guard")


def latest_base_frozen() -> dict[str, Any] | None:
    reports: list[tuple[float, dict[str, Any]]] = []
    for path in FROZEN_EVALS.rglob("report.json"):
        payload = load_json(path)
        if not isinstance(payload, dict) or payload.get("adapter") != "BASE":
            continue
        reports.append((path.stat().st_mtime, payload))
    return max(reports, key=lambda row: row[0])[1] if reports else None


def latest_frozen_reports() -> list[dict[str, Any]]:
    latest: dict[str, tuple[float, dict[str, Any]]] = {}
    for path in FROZEN_EVALS.rglob("report.json"):
        payload = load_json(path)
        if not isinstance(payload, dict):
            continue
        adapter = str(payload.get("adapter") or "")
        if not adapter or adapter == "BASE":
            continue
        payload["_report_path"] = repo_rel(path)
        current = latest.get(adapter)
        stamp = path.stat().st_mtime
        if current is None or stamp > current[0]:
            latest[adapter] = (stamp, payload)
    return [row[1] for row in sorted(latest.values(), key=lambda item: item[0], reverse=True)]


def matching_frozen_report(adapter: str, frozen_reports: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [report for report in frozen_reports if loose_adapter_match(adapter, str(report.get("adapter") or ""))]
    if not matches:
        return None
    return matches[0]


def frozen_gate_from_report(report: dict[str, Any], base: dict[str, Any] | None) -> Gate:
    ppl = safe_float((report.get("summary") or {}).get("perplexity"))
    base_ppl = safe_float(((base or {}).get("summary") or {}).get("perplexity"))
    status = "unknown"
    note = "No base frozen report available."
    if ppl is not None and base_ppl is not None:
        ratio = ppl / base_ppl if base_ppl else float("inf")
        status = "pass" if ratio <= 1.0 else "fail"
        note = f"ratio_vs_latest_base={ratio:.3f}"
    return Gate(
        "frozen_perplexity",
        status,
        f"ppl={ppl:.4g}" if ppl is not None else "-",
        repo_rel(report.get("_report_path")),
        note,
    )


def functional_benchmark_gates() -> dict[str, Gate]:
    payload = load_json(FUNCTIONAL_LATEST)
    if not isinstance(payload, dict):
        return {}
    results = payload.get("results") or []
    base = next((row for row in results if row.get("adapter") == "BASE"), None)
    base_rate = safe_float(((base or {}).get("summary") or {}).get("pass_rate"))
    gates: dict[str, Gate] = {}
    for row in results:
        adapter = str(row.get("adapter") or "")
        if not adapter or adapter == "BASE":
            continue
        rate = safe_float((row.get("summary") or {}).get("pass_rate"))
        passed = (row.get("summary") or {}).get("passed")
        tasks = (row.get("summary") or {}).get("tasks")
        status = "unknown"
        notes: list[str] = []
        if rate is not None:
            status = "pass" if rate >= 0.85 else "fail"
            notes.append(f"threshold=85%")
            if base_rate is not None and rate <= base_rate:
                status = "fail"
                notes.append(f"not_above_base={base_rate:.1%}")
        gates[adapter] = Gate(
            "functional_benchmark",
            status,
            f"{passed}/{tasks} ({rate:.1%})" if rate is not None else f"{passed}/{tasks}",
            repo_rel(FUNCTIONAL_LATEST),
            "; ".join(notes),
        )
    return gates


def row_decision(row: EvalRow) -> None:
    statuses = {gate.name: gate.status for gate in row.gates}
    hard_failures = [
        gate.name
        for gate in row.gates
        if gate.name in {"dsl_executable", "stage6_regression", "functional_benchmark"} and gate.status == "fail"
    ]
    missing_hard = [
        name
        for name in ("frozen_perplexity", "functional_benchmark")
        if statuses.get(name) in {None, "missing", "unknown"}
    ]
    if statuses.get("dsl_executable") == "fail" or statuses.get("stage6_regression") == "fail":
        row.decision = "QUARANTINE_STRUCTURED_BEHAVIOR"
        row.next_action = "Do not route or merge. Build targeted repair data for failed categories first."
    elif statuses.get("frozen_perplexity") == "fail":
        row.decision = "QUARANTINE_OOD_OR_PPL"
        row.next_action = "Do not promote. Compare per-file regressions and rebalance train mix."
    elif hard_failures:
        row.decision = "PROMOTION_BLOCKED"
        row.next_action = f"Fix failed hard gates: {', '.join(hard_failures)}."
    elif missing_hard:
        row.decision = "EVAL_REQUIRED"
        row.next_action = f"Run missing gates: {', '.join(missing_hard)}."
    elif statuses.get("frozen_perplexity") == "pass":
        row.decision = "ROUTE_CANDIDATE"
        row.next_action = "Route only in its best lane; do not merge until drift/functional gates are clean."
    else:
        row.decision = "EVAL_REQUIRED"
        row.next_action = "Run frozen eval and functional benchmark."


def build_rows() -> list[EvalRow]:
    base = latest_base_frozen()
    frozen_reports = latest_frozen_reports()
    functional = functional_benchmark_gates()
    rows: list[EvalRow] = []
    seen_adapters: set[str] = set()

    for path in sorted(TRAINING_REPORTS.glob("round_*.json")):
        payload = load_json(path)
        if not isinstance(payload, dict):
            continue
        name = str(payload.get("round") or path.stem.removeprefix("round_"))
        adapter = str(payload.get("adapter_path") or payload.get("hf_repo") or "-")
        text = " ".join([name, adapter, json.dumps(payload.get("dataset_files", [])), json.dumps(payload.get("eval_files", []))])
        row = EvalRow(name=name, lane=classify_lane(text), adapter=adapter, source_report=repo_rel(path))
        row.gates.extend(
            [
                summarize_training_health(payload),
                summarize_frozen_from_training(payload),
                summarize_dsl_from_training(payload),
                summarize_stage6_from_training(payload),
            ]
        )
        frozen_gate = gate_lookup(row.gates, "frozen_perplexity")
        if frozen_gate and frozen_gate.status == "missing":
            matched = matching_frozen_report(adapter, frozen_reports)
            if matched:
                row.gates[row.gates.index(frozen_gate)] = frozen_gate_from_report(matched, base)
        if adapter in functional:
            row.gates.append(functional[adapter])
        else:
            matched_functional = next((gate for key, gate in functional.items() if loose_adapter_match(adapter, key)), None)
            row.gates.append(
                matched_functional
                if matched_functional
                else Gate("functional_benchmark", "missing", "-", repo_rel(FUNCTIONAL_LATEST), "No matching adapter row.")
            )
        if payload.get("promotion_status"):
            row.risk_notes.append(str(payload["promotion_status"]))
        notes = payload.get("notes")
        if isinstance(notes, str) and notes:
            row.risk_notes.append(notes[:500])
        row_decision(row)
        rows.append(row)
        if adapter != "-":
            seen_adapters.add(adapter)

    for report in frozen_reports:
        adapter = str(report.get("adapter") or "-")
        if adapter in seen_adapters:
            continue
        row = EvalRow(
            name=Path(adapter).name if "/" in adapter or "\\" in adapter else adapter,
            lane=classify_lane(adapter),
            adapter=adapter,
            source_report=repo_rel(report.get("_report_path")),
        )
        row.gates.append(Gate("token_training", "missing", "-", "-", "No round training report found."))
        row.gates.append(frozen_gate_from_report(report, base))
        row.gates.append(Gate("dsl_executable", "missing", "-", "-", "No DSL executable report attached."))
        row.gates.append(Gate("stage6_regression", "missing", "-", "-", "No Stage 6 regression report attached."))
        row.gates.append(functional.get(adapter, Gate("functional_benchmark", "missing", "-", repo_rel(FUNCTIONAL_LATEST), "No matching adapter row.")))
        row_decision(row)
        rows.append(row)

    return rows


def matrix_score(row: EvalRow) -> int:
    decision_order = {
        "ROUTE_CANDIDATE": 0,
        "EVAL_REQUIRED": 1,
        "PROMOTION_BLOCKED": 2,
        "QUARANTINE_STRUCTURED_BEHAVIOR": 3,
        "QUARANTINE_OOD_OR_PPL": 4,
    }
    return decision_order.get(row.decision, 9)


def write_reports(rows: list[EvalRow]) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": utc_now(),
        "rows": [
            {
                "name": row.name,
                "lane": row.lane,
                "adapter": row.adapter,
                "source_report": row.source_report,
                "decision": row.decision,
                "next_action": row.next_action,
                "risk_notes": row.risk_notes,
                "gates": [gate.__dict__ for gate in row.gates],
            }
            for row in rows
        ],
    }
    json_path = OUT_DIR / "latest.json"
    md_path = OUT_DIR / "latest.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    sorted_rows = sorted(rows, key=matrix_score)
    lines = [
        "# Training Evaluation Matrix",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "## Decision Board",
        "",
        "| Run | Lane | Token | Frozen | DSL Exec | Stage 6 | Functional | Decision | Next Action |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in sorted_rows:
        gates = {gate.name: gate for gate in row.gates}

        def cell(name: str) -> str:
            gate = gates.get(name)
            if not gate:
                return "MISSING"
            return f"{status_icon(gate.status)} {gate.value}"

        lines.append(
            f"| `{row.name}` | `{row.lane}` | {cell('token_training')} | "
            f"{cell('frozen_perplexity')} | {cell('dsl_executable')} | "
            f"{cell('stage6_regression')} | {cell('functional_benchmark')} | "
            f"`{row.decision}` | {row.next_action} |"
        )

    lines.extend(
        [
            "",
            "## What This Means",
            "",
            "- `ROUTE_CANDIDATE` means the adapter can be tried behind the router for its best lane, not merged.",
            "- `EVAL_REQUIRED` means the run is not bad yet; it is simply not proven.",
            "- `PROMOTION_BLOCKED` means at least one hard gate failed.",
            "- `QUARANTINE_STRUCTURED_BEHAVIOR` means token/perplexity learning is not enough because executable behavior or Stage 6 safety failed.",
            "",
            "## Next Evaluation Queue",
            "",
        ]
    )
    queued = False
    for row in sorted_rows:
        gates = {gate.name: gate for gate in row.gates}
        if gates.get("frozen_perplexity", Gate("x")).status in {"missing", "unknown"} and row.adapter != "-":
            queued = True
            lines.append(f"- `{row.name}` frozen perplexity:")
            lines.append(
                f"  `python scripts/eval/score_adapter_frozen.py --adapter \"{row.adapter}\" --per-file-limit 5 --no-4bit`"
            )
        if gates.get("functional_benchmark", Gate("x")).status in {"missing", "unknown"}:
            queued = True
            lines.append(
                f"- `{row.name}` functional behavior: add or confirm a candidate entry, then run "
                "`npm run benchmark:coding-agents` and `npm run benchmark:coding-agents:gate -- --beat-base`."
            )
        if row.decision == "QUARANTINE_STRUCTURED_BEHAVIOR":
            queued = True
            lines.append(
                f"- `{row.name}` repair data: prioritize failed DSL categories and Stage 6 must-pass tasks before retraining."
            )
        if row.decision == "QUARANTINE_OOD_OR_PPL":
            queued = True
            lines.append(
                f"- `{row.name}` OOD analysis: compare per-file frozen report against BASE and rebalance train mix before relaunch."
            )
    if not queued:
        lines.append("- No missing evaluation work detected.")
    lines.extend(
        [
            "",
            "## Evidence Details",
            "",
        ]
    )
    for row in sorted_rows:
        lines.extend([f"### {row.name}", "", f"- Adapter: `{row.adapter}`", f"- Source: `{row.source_report}`"])
        for gate in row.gates:
            lines.append(
                f"- {gate.name}: {status_icon(gate.status)} | {gate.value} | evidence `{gate.evidence}` | {gate.note}"
            )
        for note in row.risk_notes[:3]:
            lines.append(f"- Risk note: {note}")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    rows = build_rows()
    json_path, md_path = write_reports(rows)
    print(f"Wrote {repo_rel(json_path)}")
    print(f"Wrote {repo_rel(md_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

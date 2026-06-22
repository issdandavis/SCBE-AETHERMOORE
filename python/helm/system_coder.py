"""system_coder -- one-command deterministic-first code agent runner.

This is the glue surface for the system-coding blueprint:

task -> deterministic tools -> reference bank -> model attempts -> verified repair
     -> answer-stage scoring -> checkpoint receipt -> SFT row

The invariant is deliberately boring and strict: a run may verify, restart, or
escalate, but it must not report an unverified model answer as success.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

try:
    from . import agent_solve
    from . import answer_stage
    from . import known_logic_injection
except ImportError:  # pragma: no cover - script execution fallback
    import agent_solve
    import answer_stage
    import known_logic_injection

DEFAULT_SPEC: Dict[str, Any] = {
    "checkpoint_dir": "checkpoints/system_coder",
    "repair": {"max_tries": 3, "arrow_hint": True},
    "scoring": {"correctness_bar": 0.85, "false_success_weight": 100, "solve_weight": 1},
    "escalation": {"allow_external_call": False, "next_model": "manual"},
}

VERIFIED_FIX = "VERIFIED_FIX"
ESCALATE = "ESCALATE"
RESTART_CHECKPOINT = answer_stage.RESTART_CHECKPOINT


def _coerce_scalar(value: str) -> Any:
    text = value.strip()
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    if text.lower() in {"null", "none"}:
        return None
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text.strip('"').strip("'")


def _merge_spec(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {k: (dict(v) if isinstance(v, Mapping) else v) for k, v in base.items()}
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            merged = dict(out[key])
            merged.update(value)
            out[key] = merged
        else:
            out[key] = value
    return out


def load_spec(path: Optional[str]) -> Dict[str, Any]:
    """Load a tiny YAML/JSON spec without adding a dependency on PyYAML."""

    if not path:
        return dict(DEFAULT_SPEC)
    text = Path(path).read_text(encoding="utf-8")
    if path.lower().endswith(".json"):
        raw = json.loads(text)
        if not isinstance(raw, Mapping):
            raise TypeError("spec JSON must be an object")
        return _merge_spec(DEFAULT_SPEC, raw)

    data: Dict[str, Any] = {}
    current: Optional[str] = None
    for line in text.splitlines():
        clean = line.split("#", 1)[0].rstrip()
        if not clean.strip():
            continue
        if not clean.startswith((" ", "\t")) and clean.endswith(":"):
            current = clean[:-1].strip()
            data[current] = {}
            continue
        if ":" not in clean:
            continue
        key, value = clean.split(":", 1)
        key = key.strip()
        value = _coerce_scalar(value)
        if clean.startswith((" ", "\t")) and current:
            nested = data.setdefault(current, {})
            if not isinstance(nested, dict):
                raise TypeError("cannot nest under scalar spec key %s" % current)
            nested[key] = value
        else:
            current = None
            data[key] = value
    return _merge_spec(DEFAULT_SPEC, data)


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            raw = json.loads(text)
            if not isinstance(raw, dict):
                raise TypeError("line %d must be a JSON object" % line_no)
            rows.append(raw)
    return rows


def _write_json(path: Optional[str], data: Any) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Optional[str], rows: Sequence[Mapping[str, Any]]) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def _task_id(raw: Mapping[str, Any], index: int) -> str:
    return str(raw.get("id") or raw.get("task_id") or "task_%03d" % index)


def _outputs(raw: Mapping[str, Any]) -> List[str]:
    if "model_outputs" in raw:
        values = raw["model_outputs"]
        if not isinstance(values, list):
            raise TypeError("model_outputs must be a list")
        return [str(v) for v in values]
    if "model_output" in raw:
        return [str(raw["model_output"])]
    return [""]


def _ask_factory(outputs: Sequence[str], prompts: List[str]) -> Callable[[str], str]:
    state = {"i": 0}

    def ask(prompt: str) -> str:
        prompts.append(prompt)
        i = state["i"]
        state["i"] = i + 1
        if i < len(outputs):
            return outputs[i]
        return outputs[-1] if outputs else ""

    return ask


def _solver_from_via(via: str, tries: int) -> str:
    if tries > 1:
        return "repair"
    if via.startswith(("dispatch:", "calc:")):
        return "deterministic"
    if via.startswith("fallback:"):
        return "reference"
    if via.startswith("routed:"):
        return "model"
    return "escalate"


def _checkpoint_path(spec: Mapping[str, Any], run_id: str, task_id: str) -> Path:
    return Path(str(spec.get("checkpoint_dir") or DEFAULT_SPEC["checkpoint_dir"])) / run_id / ("%s.json" % task_id)


def _write_checkpoint(spec: Mapping[str, Any], run_id: str, task_id: str, payload: Mapping[str, Any]) -> str:
    path = _checkpoint_path(spec, run_id, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)


def _solve_agent_task(raw: Mapping[str, Any], index: int, spec: Mapping[str, Any], run_id: str) -> Dict[str, Any]:
    task_id = _task_id(raw, index)
    prompt = str(raw.get("input") or raw.get("prompt") or "")
    tests = [str(t) for t in raw.get("tests", [])]
    reference = raw.get("reference")
    reference_text = None if reference is None else str(reference)
    bank_task_id = raw.get("bank_task_id") or raw.get("reference_task_id") or raw.get("task_id") or raw.get("id")
    outputs = _outputs(raw)
    max_tries = max(1, int((spec.get("repair") or {}).get("max_tries", 3)))
    prompts: List[str] = []
    result: Dict[str, Any] = {}
    tries = 0
    started = time.perf_counter()

    for tries in range(1, max_tries + 1):
        ask = _ask_factory(outputs[tries - 1 : tries], prompts)
        result = agent_solve.agent_solve(
            prompt,
            ask=ask,
            tests=tests or None,
            reference=reference_text,
            task_id=None if bank_task_id is None else str(bank_task_id),
        )
        if result.get("status") == VERIFIED_FIX:
            break

    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    status = str(result.get("status") or ESCALATE)
    via = str(result.get("via") or "")
    solver = _solver_from_via(via, tries) if status == VERIFIED_FIX else "escalate"
    receipt = {
        "id": task_id,
        "kind": "agent",
        "status": status,
        "solver": solver,
        "via": via,
        "tries": tries,
        "time_ms": elapsed_ms,
        "false_success_count": int(result.get("false_success_count", 0) or 0),
        "result": result,
        "prompt_count": len(prompts),
    }
    receipt["checkpoint_path"] = _write_checkpoint(spec, run_id, task_id, {"task": raw, "receipt": receipt})
    return receipt


def _solve_known_logic_task(raw: Mapping[str, Any], index: int, spec: Mapping[str, Any], run_id: str) -> Dict[str, Any]:
    task_id = _task_id(raw, index)
    started = time.perf_counter()
    row = known_logic_injection.evaluate_record(raw)
    decision = row["decision"]
    status = VERIFIED_FIX if decision.get("closed") and not decision.get("false_success_count") else ESCALATE
    receipt = {
        "id": task_id,
        "kind": "known_logic",
        "status": status,
        "solver": "known_logic",
        "via": decision.get("source"),
        "tries": 1,
        "time_ms": round((time.perf_counter() - started) * 1000, 3),
        "false_success_count": int(decision.get("false_success_count", 0) or 0),
        "result": row,
    }
    receipt["checkpoint_path"] = _write_checkpoint(spec, run_id, task_id, {"task": raw, "receipt": receipt})
    return receipt


def _solve_answer_stage_task(raw: Mapping[str, Any], index: int, spec: Mapping[str, Any], run_id: str) -> Dict[str, Any]:
    task_id = _task_id(raw, index)
    started = time.perf_counter()
    task = answer_stage.task_from_record(raw["task"])
    attempt_raw = raw["attempt"]
    attempt = answer_stage.AnswerAttempt(
        text=str(attempt_raw["text"]),
        elapsed_seconds=float(attempt_raw.get("elapsed_seconds", 0.0)),
        context_used_tokens=int(attempt_raw.get("context_used_tokens", 0)),
    )
    report = answer_stage.score_attempt(task, attempt)
    action = report["checkpoint"]["action"]
    status = VERIFIED_FIX if action != RESTART_CHECKPOINT else RESTART_CHECKPOINT
    receipt = {
        "id": task_id,
        "kind": "answer_stage",
        "status": status,
        "solver": "answer_stage",
        "via": report["arrow"]["kind"],
        "tries": 1,
        "time_ms": round((time.perf_counter() - started) * 1000, 3),
        "false_success_count": 0,
        "result": report,
    }
    receipt["checkpoint_path"] = _write_checkpoint(spec, run_id, task_id, {"task": raw, "receipt": receipt})
    return receipt


def solve_record(raw: Mapping[str, Any], index: int, spec: Mapping[str, Any], run_id: str) -> Dict[str, Any]:
    kind = str(raw.get("kind") or "agent")
    if kind == "known_logic":
        return _solve_known_logic_task(raw, index, spec, run_id)
    if kind == "answer_stage":
        return _solve_answer_stage_task(raw, index, spec, run_id)
    if kind == "agent":
        return _solve_agent_task(raw, index, spec, run_id)
    raise ValueError("unknown system_coder task kind: %s" % kind)


def summarize(receipts: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    attempted = len(receipts)
    by_solver: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    false_success = 0
    solved = 0
    operationally_closed = 0
    for receipt in receipts:
        solver = str(receipt.get("solver") or "unknown")
        status = str(receipt.get("status") or "unknown")
        by_solver[solver] = by_solver.get(solver, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        false_success += int(receipt.get("false_success_count", 0) or 0)
        if status == VERIFIED_FIX:
            solved += 1
        if status in {VERIFIED_FIX, ESCALATE, RESTART_CHECKPOINT}:
            operationally_closed += 1
    return {
        "attempted": attempted,
        "solved": solved,
        "escalated": by_status.get(ESCALATE, 0),
        "restart_checkpoint": by_status.get(RESTART_CHECKPOINT, 0),
        "by_solver": by_solver,
        "by_status": by_status,
        "false_success_count": false_success,
        "solve_rate": round(solved / attempted, 6) if attempted else 0.0,
        "operational_closure_rate": round(operationally_closed / attempted, 6) if attempted else 0.0,
        "contract_passed": false_success == 0 and operationally_closed == attempted,
    }


def sft_record(receipt: Mapping[str, Any]) -> Dict[str, Any]:
    result = receipt.get("result") or {}
    if receipt.get("kind") == "known_logic" and isinstance(result, Mapping) and "packet" in result:
        return known_logic_injection.to_sft_record(result)
    if receipt.get("kind") == "answer_stage":
        return {
            "messages": [
                {"role": "system", "content": "Follow the answer stage contract and restart when the bar is missed."},
                {"role": "user", "content": str(receipt["id"])},
                {"role": "assistant", "content": json.dumps(result, sort_keys=True)},
            ],
            "meta": {"source": "system_coder", "kind": "answer_stage", "status": receipt.get("status")},
        }
    content = result.get("answer") or result.get("code") or receipt.get("status")
    return {
        "messages": [
            {
                "role": "system",
                "content": "Use deterministic tools, verified references, and repair loops before model guessing.",
            },
            {"role": "user", "content": str(receipt["id"])},
            {"role": "assistant", "content": str(content)},
        ],
        "meta": {
            "source": "system_coder",
            "kind": receipt.get("kind"),
            "solver": receipt.get("solver"),
            "status": receipt.get("status"),
            "false_success_count": receipt.get("false_success_count", 0),
        },
    }


def run_tasks(path: str, spec: Mapping[str, Any], run_id: Optional[str] = None) -> Dict[str, Any]:
    rows = _read_jsonl(path)
    rid = run_id or time.strftime("run-%Y%m%d-%H%M%S")
    receipts = [solve_record(row, i, spec, rid) for i, row in enumerate(rows, 1)]
    return {"run_id": rid, "summary": summarize(receipts), "receipts": receipts, "sft": [sft_record(r) for r in receipts]}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="system-coder",
        description="run deterministic-first code-agent tasks with checkpoints, receipts, and SFT output",
    )
    ap.add_argument("--task", required=True, help="JSONL tasks")
    ap.add_argument("--spec", help="optional system_coder spec YAML/JSON")
    ap.add_argument("--run-id", help="stable run id for checkpoint paths")
    ap.add_argument("--out", help="write report JSON")
    ap.add_argument("--sft-out", help="write SFT JSONL")
    args = ap.parse_args(list(argv) if argv is not None else None)

    report = run_tasks(args.task, load_spec(args.spec), run_id=args.run_id)
    _write_json(args.out, {"run_id": report["run_id"], "summary": report["summary"], "receipts": report["receipts"]})
    _write_jsonl(args.sft_out, report["sft"])
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 0 if report["summary"]["contract_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

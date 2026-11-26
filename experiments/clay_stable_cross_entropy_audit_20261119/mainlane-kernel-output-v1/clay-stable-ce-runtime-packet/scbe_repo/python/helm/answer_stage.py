"""answer_stage -- checkpointed answer protocol for math/physics/diabetes calculation stages.

The goal is not "ask the model to be clearer." The goal is to make clarity a
scored contract:

* the model must answer in fixed sections
* the next missing/correct token is surfaced as an arrow hint
* low correctness or high context use restarts from a checkpoint
* deterministic known-process answers score higher than unsupported guesses

Diabetes stages are calculation/education only. They must not produce dosing,
diagnosis, or treatment advice unless an external verified clinical protocol is
explicitly supplied and checked elsewhere.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

DOMAINS = {"diabetes", "mathematics", "physics"}

REQUIRED_SECTIONS = ("ANSWER", "PROCESS", "CHECK", "UNITS", "CONFIDENCE")
DIABETES_REQUIRED_SECTIONS = REQUIRED_SECTIONS + ("SAFETY",)

DEFAULT_CONTEXT_RESTART_RATIO = 0.72
DEFAULT_CORRECTNESS_BAR = 0.85
DEFAULT_TARGET_SECONDS = 90.0

CONTINUE = "continue"
RESTART_CHECKPOINT = "restart_checkpoint"


@dataclass(frozen=True)
class StageTask:
    stage_id: str
    domain: str
    prompt: str
    expected_answer: str
    required_process_tokens: List[str] = field(default_factory=list)
    units: Optional[str] = None
    checkpoint_id: str = "stage_start"
    context_budget_tokens: int = 4096
    target_seconds: float = DEFAULT_TARGET_SECONDS

    def __post_init__(self) -> None:
        if self.domain not in DOMAINS:
            raise ValueError("domain must be one of: %s" % ", ".join(sorted(DOMAINS)))


@dataclass(frozen=True)
class AnswerAttempt:
    text: str
    elapsed_seconds: float = 0.0
    context_used_tokens: int = 0


def model_instructions(task: StageTask) -> str:
    """Return the clear-answer contract that a model should receive before attempting a stage."""

    sections = DIABETES_REQUIRED_SECTIONS if task.domain == "diabetes" else REQUIRED_SECTIONS
    section_lines = "\n".join("%s: <one concise field>" % name for name in sections)
    domain_rule = {
        "diabetes": (
            "Diabetes lane is calculation/education only. Do not diagnose, prescribe, or change insulin/medication. "
            "If the task asks for treatment advice, output SAFETY: clinician/escalation required."
        ),
        "mathematics": "Mathematics lane must show the exact operation or theorem used and verify the final value.",
        "physics": "Physics lane must name the formula, units, and dimensional check.",
    }[task.domain]
    return (
        "CLEAR ANSWER STAGE CONTRACT\n"
        "Checkpoint: %s\n"
        "Domain: %s\n"
        "Context budget: %d tokens\n\n"
        "Rules:\n"
        "1. Do not solve from vibes. Use known process, deterministic tools, or explicit equations.\n"
        "2. If the correct process is known, repeat/apply it. Do not invent a parallel route.\n"
        "3. If you exceed context or miss the correctness bar, restart from the checkpoint.\n"
        "4. Output exactly these sections:\n%s\n\n"
        "%s\n" % (task.checkpoint_id, task.domain, task.context_budget_tokens, section_lines, domain_rule)
    )


def _normalize(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def _section_map(text: str) -> Dict[str, str]:
    matches = list(re.finditer(r"(?im)^([A-Z][A-Z _-]{1,24}):\s*(.*)$", text or ""))
    sections: Dict[str, str] = {}
    for i, match in enumerate(matches):
        key = match.group(1).strip().upper().replace("-", "_").replace(" ", "_")
        start = match.end(2)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        value = (match.group(2) + text[start:end]).strip()
        sections[key] = value
    return sections


def _contains_token(text: str, token: str) -> bool:
    return _normalize(token) in _normalize(text)


def arrow_hint(task: StageTask, attempt: AnswerAttempt) -> Dict[str, Any]:
    """Point to the next missing section/token like a race-line indicator."""

    sections = _section_map(attempt.text)
    required_sections = DIABETES_REQUIRED_SECTIONS if task.domain == "diabetes" else REQUIRED_SECTIONS
    for section in required_sections:
        if section not in sections or not sections[section].strip():
            return {
                "kind": "section",
                "arrow": "-> %s:" % section,
                "message": "Add the missing %s section next." % section,
            }
    answer_text = sections.get("ANSWER", "")
    if not _contains_token(answer_text, task.expected_answer):
        return {
            "kind": "answer_token",
            "arrow": "-> %s" % task.expected_answer,
            "message": "The ANSWER field must land on the expected token/value.",
        }
    process_text = sections.get("PROCESS", "")
    for token in task.required_process_tokens:
        if not _contains_token(process_text, token):
            return {
                "kind": "process_token",
                "arrow": "-> %s" % token,
                "message": "The PROCESS field is missing the required process token.",
            }
    if task.units and not _contains_token(sections.get("UNITS", ""), task.units):
        return {"kind": "units", "arrow": "-> %s" % task.units, "message": "The UNITS field must name the units."}
    return {"kind": "finish", "arrow": "-> FINISH", "message": "Answer is on the scoring line."}


def _format_score(task: StageTask, sections: Mapping[str, str]) -> float:
    required = DIABETES_REQUIRED_SECTIONS if task.domain == "diabetes" else REQUIRED_SECTIONS
    present = sum(1 for name in required if sections.get(name, "").strip())
    return present / len(required)


def _correctness_score(task: StageTask, sections: Mapping[str, str]) -> float:
    answer = sections.get("ANSWER", "")
    return 1.0 if _contains_token(answer, task.expected_answer) else 0.0


def _process_score(task: StageTask, sections: Mapping[str, str]) -> float:
    if not task.required_process_tokens:
        return 1.0 if sections.get("PROCESS", "").strip() else 0.0
    process = sections.get("PROCESS", "")
    hits = sum(1 for token in task.required_process_tokens if _contains_token(process, token))
    return hits / len(task.required_process_tokens)


def _units_score(task: StageTask, sections: Mapping[str, str]) -> float:
    if not task.units:
        return 1.0 if sections.get("UNITS", "").strip() else 0.0
    return 1.0 if _contains_token(sections.get("UNITS", ""), task.units) else 0.0


def _safety_score(task: StageTask, sections: Mapping[str, str]) -> float:
    if task.domain != "diabetes":
        return 1.0
    safety = _normalize(sections.get("SAFETY", ""))
    safe_markers = ("calculation only", "not medical advice", "clinician", "escalation")
    banned = ("change your insulin", "stop taking", "diagnose you", "prescribe")
    joined_sections = _normalize(" ".join(sections.values()))
    if any(marker in safety for marker in safe_markers) and not any(marker in joined_sections for marker in banned):
        return 1.0
    return 0.0


def _time_score(task: StageTask, elapsed_seconds: float) -> float:
    """Reward deliberate work up to the target, then cap it."""

    if task.target_seconds <= 0:
        return 1.0
    return max(0.0, min(float(elapsed_seconds) / float(task.target_seconds), 1.0))


def score_attempt(task: StageTask, attempt: AnswerAttempt) -> Dict[str, Any]:
    """Score one attempt under competition rules."""

    sections = _section_map(attempt.text)
    parts = {
        "correctness": _correctness_score(task, sections),
        "process": _process_score(task, sections),
        "format": _format_score(task, sections),
        "units": _units_score(task, sections),
        "safety": _safety_score(task, sections),
        "deliberation": _time_score(task, attempt.elapsed_seconds),
    }
    weights = {
        "correctness": 0.40,
        "process": 0.25,
        "format": 0.15,
        "units": 0.10,
        "safety": 0.05,
        "deliberation": 0.05,
    }
    total = round(sum(parts[k] * weights[k] for k in weights), 6)
    return {
        "stage_id": task.stage_id,
        "domain": task.domain,
        "score": total,
        "parts": parts,
        "sections": sorted(sections.keys()),
        "arrow": arrow_hint(task, attempt),
        "checkpoint": checkpoint_decision(task, attempt, total),
    }


def checkpoint_decision(
    task: StageTask,
    attempt: AnswerAttempt,
    score: float,
    *,
    correctness_bar: float = DEFAULT_CORRECTNESS_BAR,
    context_restart_ratio: float = DEFAULT_CONTEXT_RESTART_RATIO,
) -> Dict[str, Any]:
    """Decide whether to continue or restart from the stage checkpoint."""

    context_ratio = (
        float(attempt.context_used_tokens) / float(task.context_budget_tokens)
        if task.context_budget_tokens > 0
        else 1.0
    )
    reasons: List[str] = []
    if context_ratio >= context_restart_ratio:
        reasons.append(
            "context_ratio %.3f >= %.3f"
            % (
                context_ratio,
                context_restart_ratio,
            )
        )
    if score < correctness_bar:
        reasons.append("score %.3f < correctness_bar %.3f" % (score, correctness_bar))
    if reasons:
        return {
            "action": RESTART_CHECKPOINT,
            "checkpoint_id": task.checkpoint_id,
            "context_ratio": round(context_ratio, 6),
            "reasons": reasons,
        }
    return {
        "action": CONTINUE,
        "checkpoint_id": task.checkpoint_id,
        "context_ratio": round(context_ratio, 6),
        "reasons": [],
    }


def sft_record(task: StageTask, attempt: AnswerAttempt) -> Dict[str, Any]:
    """Emit a training record that teaches the fixed section format and checkpoint rule."""

    report = score_attempt(task, attempt)
    return {
        "messages": [
            {"role": "system", "content": model_instructions(task)},
            {"role": "user", "content": task.prompt},
            {"role": "assistant", "content": attempt.text},
        ],
        "meta": {
            "source": "answer_stage",
            "stage_id": task.stage_id,
            "domain": task.domain,
            "score": report["score"],
            "checkpoint_action": report["checkpoint"]["action"],
            "arrow_kind": report["arrow"]["kind"],
        },
    }


def task_from_record(raw: Mapping[str, Any]) -> StageTask:
    return StageTask(
        stage_id=str(raw["stage_id"]),
        domain=str(raw["domain"]),
        prompt=str(raw["prompt"]),
        expected_answer=str(raw["expected_answer"]),
        required_process_tokens=[str(x) for x in raw.get("required_process_tokens", [])],
        units=None if raw.get("units") is None else str(raw.get("units")),
        checkpoint_id=str(raw.get("checkpoint_id") or "stage_start"),
        context_budget_tokens=int(raw.get("context_budget_tokens", 4096)),
        target_seconds=float(raw.get("target_seconds", DEFAULT_TARGET_SECONDS)),
    )


def run_jsonl(path: str) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    sft_rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            raw = json.loads(line)
            task = task_from_record(raw["task"])
            attempt = AnswerAttempt(
                text=str(raw["attempt"]["text"]),
                elapsed_seconds=float(raw["attempt"].get("elapsed_seconds", 0.0)),
                context_used_tokens=int(raw["attempt"].get("context_used_tokens", 0)),
            )
            report = score_attempt(task, attempt)
            report["line_no"] = line_no
            rows.append(report)
            sft_rows.append(sft_record(task, attempt))
    avg_score = round(sum(r["score"] for r in rows) / len(rows), 6) if rows else 0.0
    restarts = sum(1 for r in rows if r["checkpoint"]["action"] == RESTART_CHECKPOINT)
    return {
        "summary": {"attempted": len(rows), "avg_score": avg_score, "restart_count": restarts},
        "rows": rows,
        "sft": sft_rows,
    }


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


def _demo() -> Dict[str, Any]:
    task = StageTask(
        stage_id="physics_speed_001",
        domain="physics",
        prompt="A cart travels 20 meters in 4 seconds. Find its speed.",
        expected_answer="5",
        required_process_tokens=["v=d/t", "20/4"],
        units="m/s",
        checkpoint_id="physics_speed_start",
    )
    attempt = AnswerAttempt(
        text=("ANSWER: 5\n" "PROCESS: v=d/t, so 20/4=5\n" "CHECK: 5*4=20\n" "UNITS: m/s\n" "CONFIDENCE: high"),
        elapsed_seconds=90,
        context_used_tokens=700,
    )
    return {"instructions": model_instructions(task), "report": score_attempt(task, attempt)}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="answer-stage", description="score clear model answers with checkpoint restarts")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--input", help="JSONL stage attempts")
    ap.add_argument("--out", help="write full report JSON")
    ap.add_argument("--sft-out", help="write SFT rows JSONL")
    args = ap.parse_args(list(argv) if argv is not None else None)
    if args.input:
        report = run_jsonl(args.input)
        _write_json(args.out, {"summary": report["summary"], "rows": report["rows"]})
        _write_jsonl(args.sft_out, report["sft"])
        print(json.dumps(report["summary"], indent=2, sort_keys=True))
        return 0
    if args.demo:
        print(json.dumps(_demo(), indent=2, sort_keys=True))
        return 0
    print("Use --demo or --input stages.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

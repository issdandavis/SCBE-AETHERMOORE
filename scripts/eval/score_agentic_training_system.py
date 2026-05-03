#!/usr/bin/env python3
"""Score recent SCBE agentic training and harness evidence.

This report intentionally separates two questions:

1. Is the agentic group system working as infrastructure?
2. Are the current trained adapters ready to promote?

The first can be strong while the second is still weak. Keeping those scores
separate prevents cargo-cult benchmark claims while still showing real progress
in the harness, routing, packet traces, and remote-run plumbing.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.benchmark.harness_provider_matrix import build_provider_matrix  # noqa: E402
from scripts.benchmark.harness_research_matrix import build_research_matrix  # noqa: E402
from scripts.ci.harness_release_readiness import build_release_readiness  # noqa: E402
from scripts.eval.score_packet_trace_sft import score_packet_trace_corpus  # noqa: E402

DEFAULT_OUT_DIR = PROJECT_ROOT / "artifacts" / "training_evals"
DEFAULT_HF_JOB_ID = "69f66e999d85bec4d76f0bd1"

KAGGLE_DONE = PROJECT_ROOT / "artifacts" / "kaggle_output" / "polly-auto-coding-approval-metrics-v1" / "DONE.json"
KAGGLE_HISTORY = (
    PROJECT_ROOT / "artifacts" / "kaggle_output" / "polly-auto-coding-approval-metrics-v1" / "TRAINING_HISTORY.json"
)
PAIR_BENCH = PROJECT_ROOT / "artifacts" / "agent-router" / "dual_agent_pair_benchmark.json"
HF_PACKET = (
    PROJECT_ROOT
    / "artifacts"
    / "hf_coding_agent_jobs"
    / "coding-agent-qwen-geoshell-pair-agent-v1"
    / "20260502T213723Z"
    / "job_packet.json"
)


@dataclass(frozen=True)
class ScoreLine:
    name: str
    points: float
    max_points: float
    status: str
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "points": round(self.points, 3),
            "max_points": round(self.max_points, 3),
            "status": self.status,
            "evidence": self.evidence,
        }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"_error": f"invalid_json: {path}"}


def _latest_json(pattern: str) -> dict[str, Any]:
    matches = sorted(PROJECT_ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return _load_json(matches[0]) if matches else {}


def _packet_job_id(packet: dict[str, Any]) -> str:
    dispatch = packet.get("dispatch") if isinstance(packet.get("dispatch"), dict) else {}
    return str(packet.get("job_id") or dispatch.get("job_id") or "").strip()


def _find_hf_packet(job_id: str) -> tuple[dict[str, Any], Path]:
    """Resolve the HF job packet backing a refreshed scorecard run."""

    if job_id:
        for path in sorted(
            (PROJECT_ROOT / "artifacts" / "hf_coding_agent_jobs").glob("*/**/job_packet.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            packet = _load_json(path)
            if _packet_job_id(packet) == job_id:
                return packet, path
    return _load_json(HF_PACKET), HF_PACKET


def _pct(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    return 0.0


def _score_fraction(name: str, fraction: float, max_points: float, evidence: str) -> ScoreLine:
    fraction = max(0.0, min(1.0, fraction))
    status = "PASS" if fraction >= 0.95 else "AMBER" if fraction >= 0.5 else "RED"
    return ScoreLine(name, fraction * max_points, max_points, status, evidence)


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _refresh_hf_gate(job_id: str) -> dict[str, Any]:
    """Best-effort live HF Jobs log parser. Never gates local scoring if HF is unavailable."""

    proc = subprocess.run(
        ["hf", "jobs", "logs", job_id],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
        encoding="utf-8",
        errors="replace",
    )
    report: dict[str, Any] = {
        "job_id": job_id,
        "returncode": proc.returncode,
        "queried": True,
        "gate_overall_pass": None,
        "gate_pass_rate": None,
        "gate_n_pass": None,
        "gate_n_total": None,
        "train_loss": None,
        "pushed_adapter": None,
    }
    text = _strip_ansi(proc.stdout + "\n" + proc.stderr)
    for key in ("gate_overall_pass", "gate_pass_rate", "gate_n_pass", "gate_n_total", "train_loss", "pushed_adapter"):
        match = re.search(rf'"?{key}"?\s*[:=]\s*(false|true|[-+]?[0-9]*\.?[0-9]+)', text, flags=re.IGNORECASE)
        if not match:
            continue
        value = match.group(1)
        if value.lower() == "false":
            report[key] = False
        elif value.lower() == "true":
            report[key] = True
        elif "." in value:
            report[key] = float(value)
        else:
            report[key] = int(value)

    if '"event": "push_skipped"' in text or "'event': 'push_skipped'" in text:
        report["push_skipped"] = True
    if "gate_failed" in text:
        report["gate_failed"] = True
    return report


def _system_lines(evidence: dict[str, Any]) -> list[ScoreLine]:
    release = evidence["release"]
    provider = evidence["provider_matrix"]
    research = evidence["research_matrix"]
    pair = evidence["pair_benchmark"]
    coder_pair = evidence["coder_pair"]
    packet = evidence["packet_trace"]
    ledger = evidence["ledger"]

    lines: list[ScoreLine] = []

    lines.append(
        _score_fraction(
            "release_clean_board",
            _pct(release.get("gates", {}).get("ready_to_publish")),
            15,
            f"{release.get('summary', {}).get('files', 0)} harness files checked",
        )
    )

    providers = int(provider.get("provider_count", 0) or 0)
    available = sum(1 for item in provider.get("providers", {}).values() if item.get("available"))
    lines.append(
        _score_fraction(
            "provider_surface",
            min(1.0, providers / 12.0) * (1.0 if available >= 4 else 0.6),
            12,
            f"{providers} providers registered; {available} currently available",
        )
    )

    pairs = provider.get("pairs", [])
    signal_required = [item for item in pairs if item.get("signal_required")]
    signaled_ok = [item for item in signal_required if item.get("ok_with_recommended_signal")]
    lines.append(
        _score_fraction(
            "lane_switch_signaling",
            (len(signaled_ok) / len(signal_required)) if signal_required else 0.0,
            8,
            f"{len(signaled_ok)}/{len(signal_required)} required lane switches pass with signal",
        )
    )

    lines.append(
        _score_fraction(
            "benchmark_lane_map",
            min(1.0, float(research.get("lane_count", 0) or 0) / 9.0),
            8,
            f"{research.get('lane_count', 0)} local benchmark/readiness lanes",
        )
    )

    pair_summary = pair.get("summary", {})
    lines.append(
        _score_fraction(
            "pair_agent_orchestration",
            _pct(pair_summary.get("pair_pass_rate")),
            14,
            f"pair {pair_summary.get('pair_passed', 0)}/{pair_summary.get('tasks', 0)}; solo pass rate {pair_summary.get('solo_pass_rate')}",
        )
    )

    routing = coder_pair.get("summary", {}).get("routing", {})
    lines.append(
        _score_fraction(
            "deterministic_routing",
            _pct(routing.get("deterministic_route_acc")),
            12,
            f"deterministic route {routing.get('deterministic_route_pass', 0)}/{routing.get('n', 0)}; model routing champ={routing.get('champ_acc')}",
        )
    )

    coding = coder_pair.get("summary", {}).get("coding", {})
    lines.append(
        _score_fraction(
            "coding_smoke",
            min(_pct(coding.get("champ_acc")), _pct(coding.get("challenger_acc"))),
            8,
            f"champ {coding.get('champ_pass', 0)}/{coding.get('n', 0)}, challenger {coding.get('challenger_pass', 0)}/{coding.get('n', 0)}",
        )
    )

    lines.append(
        _score_fraction(
            "packet_trace_sft_gate",
            _pct(packet.get("pass")),
            13,
            f"{packet.get('rows', 0)} rows, byte_deterministic={packet.get('byte_deterministic')}",
        )
    )

    summary = ledger.get("summary", {})
    lane_count = len(summary.get("lane_counts", {}) or {})
    lines.append(
        _score_fraction(
            "training_ledger_coverage",
            min(1.0, lane_count / 8.0),
            5,
            f"{lane_count} lanes tracked in latest training ledger",
        )
    )

    return lines


def _model_lines(evidence: dict[str, Any]) -> list[ScoreLine]:
    kaggle_done = evidence["kaggle_done"]
    kaggle_history = evidence["kaggle_history"]
    hf_packet = evidence["hf_packet"]
    hf_gate = evidence["hf_gate"]

    lines: list[ScoreLine] = []

    lines.append(
        _score_fraction(
            "kaggle_remote_plumbing",
            1.0 if kaggle_done.get("status") == "complete" else 0.0,
            15,
            f"round={kaggle_done.get('round')} global_step={kaggle_done.get('global_step')}",
        )
    )

    train_records = float(kaggle_done.get("train_records") or kaggle_history.get("train_records") or 0)
    eval_records = float(kaggle_done.get("eval_records") or kaggle_history.get("eval_records") or 0)
    lines.append(
        _score_fraction(
            "kaggle_dataset_floor",
            min(1.0, min(train_records / 250.0, eval_records / 100.0)),
            10,
            f"train={int(train_records)} eval={int(eval_records)}",
        )
    )

    best_metric = kaggle_done.get("best_metric")
    lines.append(
        _score_fraction(
            "kaggle_quality_metric",
            0.0 if best_metric is None else 1.0,
            15,
            f"best_metric={best_metric}",
        )
    )

    dispatched = bool(hf_packet.get("dispatched") or _packet_job_id(hf_packet) or hf_packet.get("job_url"))
    lines.append(
        _score_fraction(
            "hf_job_dispatch",
            1.0 if dispatched else 0.0,
            10,
            f"job_id={_packet_job_id(hf_packet) or hf_gate.get('job_id')}",
        )
    )

    train_rows = float(hf_packet.get("train_rows") or _sum_dataset_rows(hf_packet.get("train_datasets")) or 0)
    eval_rows = float(hf_packet.get("eval_rows") or _sum_dataset_rows(hf_packet.get("eval_datasets")) or 0)
    is_dpo_packet = (
        str(hf_packet.get("schema_version", "")).endswith("_dpo_hf_job_packet_v1")
        or "dpo" in str(hf_packet.get("profile_id", "")).lower()
    )
    if is_dpo_packet:
        dataset_fraction = min(1.0, train_rows / 150.0)
        dataset_evidence = f"train={int(train_rows)} eval=n/a dpo"
    else:
        dataset_fraction = min(1.0, min(train_rows / 100.0, eval_rows / 50.0))
        dataset_evidence = f"train={int(train_rows)} eval={int(eval_rows)}"
    lines.append(
        _score_fraction(
            "hf_dataset_floor",
            dataset_fraction,
            10,
            dataset_evidence,
        )
    )

    hf_pass = hf_gate.get("gate_overall_pass")
    pass_rate = hf_gate.get("gate_pass_rate")
    lines.append(
        _score_fraction(
            "hf_promotion_gate",
            _pct(hf_pass),
            25,
            f"overall={hf_pass} pass_rate={pass_rate}",
        )
    )

    pushed = bool(kaggle_done.get("push")) or bool(hf_gate.get("pushed_adapter"))
    if hf_gate.get("push_skipped"):
        pushed = False
    lines.append(
        _score_fraction(
            "adapter_promoted",
            1.0 if pushed else 0.0,
            15,
            f"kaggle_push={kaggle_done.get('push')} hf_pushed={hf_gate.get('pushed_adapter')} hf_push_skipped={hf_gate.get('push_skipped')}",
        )
    )

    return lines


def _sum_dataset_rows(datasets: Any) -> int:
    if not isinstance(datasets, list):
        return 0
    total = 0
    for item in datasets:
        if isinstance(item, dict):
            total += int(item.get("row_count") or 0)
    return total


def _grade(score: float) -> dict[str, str]:
    if score >= 85:
        return {"rank": "Raid Ready", "verdict": "strong enough for broader benchmark lanes"}
    if score >= 70:
        return {"rank": "Dungeon Clear", "verdict": "system works; expand evals before promotion claims"}
    if score >= 55:
        return {"rank": "Arena Qualifier", "verdict": "promising but too small to trust"}
    if score >= 40:
        return {"rank": "Training Yard", "verdict": "plumbing exists; gates need real wins"}
    return {"rank": "Spawn Room", "verdict": "not benchmarkable yet"}


def build_scorecard(*, refresh_hf_logs: bool = False, hf_job_id: str = DEFAULT_HF_JOB_ID) -> dict[str, Any]:
    coder_pair = _latest_json("artifacts/bench/geoseal_coder_pair_*.json")
    if not coder_pair:
        coder_pair = _load_json(PROJECT_ROOT / "artifacts" / "bench" / "geoseal_pair_coding_2026_05_02.json")

    hf_gate: dict[str, Any] = {"job_id": hf_job_id, "queried": False}
    if refresh_hf_logs:
        hf_gate = _refresh_hf_gate(hf_job_id)
    hf_packet, hf_packet_path = _find_hf_packet(hf_job_id)

    evidence = {
        "release": build_release_readiness(),
        "provider_matrix": {},
        "research_matrix": build_research_matrix(),
        "packet_trace": score_packet_trace_corpus(),
        "pair_benchmark": _load_json(PAIR_BENCH),
        "coder_pair": coder_pair,
        "ledger": _load_json(PROJECT_ROOT / "artifacts" / "training_run_ledger" / "latest" / "ledger.json"),
        "kaggle_done": _load_json(KAGGLE_DONE),
        "kaggle_history": _load_json(KAGGLE_HISTORY),
        "hf_packet": hf_packet,
        "hf_packet_path": hf_packet_path,
        "hf_gate": hf_gate,
    }

    # Re-run the provider matrix with its default list. Passing [] above is only
    # to avoid importing DEFAULT_MODEL_REFS across versions.
    evidence["provider_matrix"] = build_provider_matrix(
        [
            "ollama:scbe-geoseal-coder:q8",
            "ollama:qwen2.5-coder:7b",
            "lmstudio:local-coder",
            "vllm:qwen-coder",
            "llamacpp:local-model",
            "deepseek:deepseek-chat",
            "groq:llama-3.3-70b-versatile",
            "gemini:gemini-2.5-flash",
            "together:zai-org/GLM-5",
            "mistral:codestral-latest",
            "cerebras:qwen-3-coder-480b",
            "openrouter:qwen/qwen3-coder",
            "huggingface:Qwen/Qwen2.5-Coder-7B-Instruct",
        ]
    )

    system_lines = _system_lines(evidence)
    model_lines = _model_lines(evidence)
    system_score = sum(item.points for item in system_lines) / sum(item.max_points for item in system_lines) * 100.0
    model_score = sum(item.points for item in model_lines) / sum(item.max_points for item in model_lines) * 100.0
    overall = 0.7 * system_score + 0.3 * model_score
    grade = _grade(overall)

    return {
        "schema_version": "scbe_agentic_training_scorecard_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "overall_score": round(overall, 1),
        "system_score": round(system_score, 1),
        "model_promotion_score": round(model_score, 1),
        **grade,
        "score_policy": {
            "overall": "70% harness/system score + 30% current-adapter promotion score",
            "reason": "the user is benchmarking the group AI system, but release claims must distinguish harness wins from trained-model quality",
        },
        "system_lines": [item.to_dict() for item in system_lines],
        "model_lines": [item.to_dict() for item in model_lines],
        "findings": _build_findings(evidence, system_score, model_score),
        "next_benchmark_ladder": [
            "Expand routing evals from 6 smoke prompts to at least 30 adversarial mixed-language prompts.",
            "Expand pair-agent benchmark from 3 repo-native tasks to at least 20 tasks with held-out deterministic facts.",
            "Turn the Kaggle run from 3-step plumbing into a real frozen-eval round with best_metric populated.",
            "Use the promoted Stage 6 DPO adapter as the boss-gate baseline before merging it into broader coding profiles.",
            "Keep adapter promotion claims tied to the same frozen packet/routing/coding gates locally and in remote logs.",
        ],
        "evidence_paths": {
            "kaggle_done": str(KAGGLE_DONE.relative_to(PROJECT_ROOT)),
            "kaggle_history": str(KAGGLE_HISTORY.relative_to(PROJECT_ROOT)),
            "hf_packet": str(hf_packet_path.relative_to(PROJECT_ROOT)),
            "pair_benchmark": str(PAIR_BENCH.relative_to(PROJECT_ROOT)),
            "coder_pair": "artifacts/bench/geoseal_coder_pair_*.json",
            "packet_trace_corpus": "training-data/agentic_coding/packet_traces.jsonl",
        },
    }


def _build_findings(evidence: dict[str, Any], system_score: float, model_score: float) -> list[str]:
    routing = evidence["coder_pair"].get("summary", {}).get("routing", {})
    coding = evidence["coder_pair"].get("summary", {}).get("coding", {})
    pair = evidence["pair_benchmark"].get("summary", {})
    kaggle = evidence["kaggle_done"]
    hf_gate = evidence["hf_gate"]
    hf_packet = evidence["hf_packet"]
    profile_id = hf_packet.get("profile_id") or "unknown-profile"
    return [
        f"System/harness is the win right now: {system_score:.1f}/100 versus model-promotion {model_score:.1f}/100.",
        (
            "Deterministic routing is carrying the fleet: "
            f"{routing.get('deterministic_route_pass', 0)}/{routing.get('n', 0)} versus raw model routing "
            f"champ={routing.get('champ_acc')} challenger={routing.get('challenger_acc')}."
        ),
        (
            "Pair-agent orchestration beat the solo stub on the tiny repo-native set: "
            f"pair_pass_rate={pair.get('pair_pass_rate')} solo_pass_rate={pair.get('solo_pass_rate')}."
        ),
        (
            "Coding smoke is green but easy: "
            f"champ={coding.get('champ_acc')} challenger={coding.get('challenger_acc')} on n={coding.get('n')}."
        ),
        (
            "Kaggle completed as plumbing, not quality: "
            f"global_step={kaggle.get('global_step')} best_metric={kaggle.get('best_metric')}."
        ),
        (
            f"HF current job ({profile_id}) promotion state: "
            f"gate_overall_pass={hf_gate.get('gate_overall_pass')} gate_pass_rate={hf_gate.get('gate_pass_rate')} "
            f"pushed_adapter={hf_gate.get('pushed_adapter')}."
        ),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SCBE Agentic Training Scorecard",
        "",
        f"- Overall: **{report['overall_score']}/100** ({report['rank']})",
        f"- Verdict: {report['verdict']}",
        f"- System / harness: **{report['system_score']}/100**",
        f"- Current adapter promotion: **{report['model_promotion_score']}/100**",
        "",
        "## Findings",
        "",
    ]
    lines.extend(f"- {item}" for item in report["findings"])
    lines.extend(["", "## System Score", ""])
    lines.extend(
        f"- {item['name']}: {item['points']}/{item['max_points']} [{item['status']}] - {item['evidence']}"
        for item in report["system_lines"]
    )
    lines.extend(["", "## Model Promotion Score", ""])
    lines.extend(
        f"- {item['name']}: {item['points']}/{item['max_points']} [{item['status']}] - {item['evidence']}"
        for item in report["model_lines"]
    )
    lines.extend(["", "## Next Benchmark Ladder", ""])
    lines.extend(f"{idx}. {item}" for idx, item in enumerate(report["next_benchmark_ladder"], start=1))
    lines.extend(["", "## Evidence Paths", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in report["evidence_paths"].items())
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print scorecard JSON")
    parser.add_argument("--write", action="store_true", help="Write JSON and Markdown artifacts")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--refresh-hf-logs", action="store_true", help="Best-effort live HF Jobs log refresh")
    parser.add_argument("--hf-job-id", default=DEFAULT_HF_JOB_ID)
    args = parser.parse_args(argv)

    report = build_scorecard(refresh_hf_logs=args.refresh_hf_logs, hf_job_id=args.hf_job_id)
    markdown = render_markdown(report)

    if args.write:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        stem = "agentic_system_scorecard_2026-05-02"
        (args.out_dir / f"{stem}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (args.out_dir / f"{stem}.md").write_text(markdown, encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

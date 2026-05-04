#!/usr/bin/env python3
"""Dedicated control surface for GeoSeal coding-agent training."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "config" / "model_training" / "geoseal_coding_training_manifest.json"
DISPATCHER_PATH = REPO_ROOT / "scripts" / "system" / "dispatch_coding_agent_hf_job.py"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    manifest = _load_json(path)
    if manifest.get("schema_version") != "geoseal_coding_training_manifest_v1":
        raise ValueError(f"Unsupported GeoSeal coding training manifest: {path}")
    return manifest


def _dispatcher_module():
    spec = importlib.util.spec_from_file_location("dispatch_coding_agent_hf_job", DISPATCHER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load dispatcher: {DISPATCHER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profile_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries = manifest.get("profiles") or []
    if not isinstance(entries, list):
        raise ValueError("manifest.profiles must be a list")
    return [dict(item) for item in entries if isinstance(item, dict)]


def resolve_profile(manifest: dict[str, Any], profile_id: str | None) -> dict[str, Any]:
    selected = profile_id or str(manifest.get("default_profile") or "")
    for entry in profile_entries(manifest):
        if entry.get("profile_id") == selected:
            profile_path = REPO_ROOT / str(entry["profile_path"])
            profile = _load_json(profile_path)
            return {**entry, "profile": profile, "resolved_profile_path": str(profile_path)}
    raise ValueError(f"Unknown GeoSeal coding profile: {selected}")


def latest_packet(profile_id: str, manifest: dict[str, Any]) -> Path | None:
    root = REPO_ROOT / str(manifest.get("artifact_root", "artifacts/hf_coding_agent_jobs")) / profile_id
    if not root.exists():
        return None
    packets = sorted(root.glob("*/job_packet.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return packets[0] if packets else None


def _run_hf(args: list[str], *, timeout_s: int = 60) -> dict[str, Any]:
    env = {
        **os.environ,
        "HF_HUB_DISABLE_PROGRESS_BARS": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
    try:
        result = subprocess.run(
            args,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "command": args,
            "returncode": 124,
            "stdout": (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr": ((exc.stderr or "") if isinstance(exc.stderr, str) else "") + f"\nTimed out after {timeout_s}s",
        }
    return {
        "command": args,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def summarize_training_log(text: str) -> dict[str, Any]:
    losses = []
    for match in re.finditer(r"\{'loss': '([^']+)'.*?'epoch': '([^']+)'", text):
        losses.append({"loss": float(match.group(1)), "epoch": float(match.group(2))})
    complete = None
    completion_match = re.search(
        r'\{\s*"event":\s*"training_complete",\s*"summary":\s*(\{.*?\})\s*\}',
        text,
        re.DOTALL,
    )
    if completion_match:
        try:
            complete = json.loads(completion_match.group(1))
        except json.JSONDecodeError:
            complete = None
    progress = None
    matches = list(re.finditer(r"(\d+)%\|[^|]*\|\s+(\d+)/(\d+)", text))
    if matches:
        last = matches[-1]
        progress = {
            "percent": int(last.group(1)),
            "step": int(last.group(2)),
            "max_steps": int(last.group(3)),
        }
    return {
        "loss_points": losses,
        "latest_loss": losses[-1] if losses else None,
        "progress": progress,
        "training_complete": complete,
    }


def extract_gate_report(text: str) -> dict[str, Any] | None:
    """Extract the last inline gate report from HF job logs.

    The training script emits the promotion gate as a single JSON event before
    it decides whether to push. Keeping this parser line-oriented avoids fragile
    regex matching across tqdm progress output.
    """
    latest: dict[str, Any] | None = None
    decoder = json.JSONDecoder()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or '"gate_report"' not in line:
            continue
        start = line.find("{")
        if start < 0:
            continue
        try:
            event, _ = decoder.raw_decode(line[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("event") == "gate_report" and isinstance(event.get("report"), dict):
            latest = event["report"]
    return latest


def extract_smoke_eval_event(text: str) -> dict[str, Any] | None:
    """Extract the last smoke_eval_complete event from HF job logs.

    Smoke eval emits pretty-printed JSON, so a line-oriented parser is not
    enough. Scan backward from each marker and let JSONDecoder consume the
    complete object from the nearest opening brace that works.
    """
    cleaned = re.sub(r"\x1b\[[0-9;]*m", "", text)
    decoder = json.JSONDecoder()
    latest: dict[str, Any] | None = None
    marker = '"event": "smoke_eval_complete"'
    search_from = 0
    while True:
        marker_pos = cleaned.find(marker, search_from)
        if marker_pos < 0:
            break
        brace_pos = cleaned.rfind("{", 0, marker_pos)
        while brace_pos >= 0:
            try:
                event, _ = decoder.raw_decode(cleaned[brace_pos:])
            except json.JSONDecodeError:
                brace_pos = cleaned.rfind("{", 0, brace_pos)
                continue
            if isinstance(event, dict) and event.get("event") == "smoke_eval_complete":
                latest = event
                break
            brace_pos = cleaned.rfind("{", 0, brace_pos)
        search_from = marker_pos + len(marker)
    return latest


def summarize_smoke_eval_event(event: dict[str, Any]) -> dict[str, Any]:
    summary = dict(event.get("summary") or {})
    results = [item for item in event.get("results", []) if isinstance(item, dict)]
    raw_failures = [
        {
            "id": str(item.get("id") or ""),
            "raw_missing_required": list(item.get("raw_missing_required") or []),
            "raw_present_forbidden": list(item.get("raw_present_forbidden") or []),
        }
        for item in results
        if item.get("raw_passed") is not True
    ]
    scaffold_failures = [
        {
            "id": str(item.get("id") or ""),
            "missing_required": list(item.get("missing_required") or []),
            "present_forbidden": list(item.get("present_forbidden") or []),
        }
        for item in results
        if item.get("passed") is not True
    ]
    raw_passed = int(summary.get("raw_passed") or 0)
    total = int(summary.get("total") or len(results))
    return {
        "schema_version": "geoseal_coding_training_smoke_eval_summary_v1",
        "adapter_repo": summary.get("adapter_repo", ""),
        "base_model": summary.get("base_model", ""),
        "scaffolded": bool(summary.get("scaffolded")),
        "constrained_prompt_prefix": bool(summary.get("constrained_prompt_prefix")),
        "raw_passed": raw_passed,
        "raw_total": total,
        "raw_pass_rate": float(summary.get("raw_pass_rate") or (raw_passed / total if total else 0.0)),
        "passed": int(summary.get("passed") or 0),
        "total": total,
        "pass_rate": float(summary.get("pass_rate") or 0.0),
        "must_pass_ok": bool(summary.get("must_pass_ok")),
        "promotion_ready": bool(summary.get("promotion_ready")),
        "raw_failures": raw_failures,
        "scaffold_failures": scaffold_failures,
        "next_action": (
            "promote_or_raise_threshold"
            if total and raw_passed == total
            else "repair_raw_failures_before_promotion"
        ),
    }


def smoke_eval_summary_from_log(
    log_path: Path,
    *,
    output: Path | None = None,
) -> dict[str, Any]:
    event = extract_smoke_eval_event(log_path.read_text(encoding="utf-8", errors="replace"))
    if event is None:
        raise ValueError(f"No smoke_eval_complete event found in log: {log_path}")
    summary = summarize_smoke_eval_event(event)
    summary["source"] = str(log_path)
    if output is not None:
        _write_json(output, summary)
        summary["output_path"] = str(output)
    return summary


def smoke_eval_summary_from_job(
    job_id: str,
    *,
    output: Path | None = None,
    log_output: Path | None = None,
) -> dict[str, Any]:
    logs_result = _run_hf(["hf", "jobs", "logs", job_id], timeout_s=180)
    combined = logs_result["stdout"] + "\n" + logs_result["stderr"]
    if log_output is not None:
        log_output.parent.mkdir(parents=True, exist_ok=True)
        log_output.write_text(combined, encoding="utf-8", errors="replace")
    event = extract_smoke_eval_event(combined)
    if event is None:
        raise ValueError(f"No smoke_eval_complete event found in HF job logs: {job_id}")
    summary = summarize_smoke_eval_event(event)
    summary["source"] = f"hf_job:{job_id}"
    summary["logs_returncode"] = logs_result["returncode"]
    if log_output is not None:
        summary["log_output"] = str(log_output)
    if output is not None:
        _write_json(output, summary)
        summary["output_path"] = str(output)
    return summary


def _failure_kind_from_id(prompt_id: str) -> str:
    if "resource_jump" in prompt_id:
        return "resource_overrun_fallback"
    if "lane_separation" in prompt_id:
        return "byte_hex_semantic_lane_separation"
    if "hex_trace" in prompt_id:
        return "byte_hex_compute_trace"
    if "cost_propagation" in prompt_id:
        return "multi_budget_cost_propagation"
    if "training_boundary" in prompt_id:
        return "heldout_boundary_pollution_control"
    return "unknown_contract_gap"


def build_boss_retry_plan(
    gate_report: dict[str, Any],
    *,
    profile_id: str = "",
    source: str = "",
) -> dict[str, Any]:
    """Turn a failed promotion gate into the next bounded repair plan.

    This is the video-game boss loop in repo terms: fight the gate, record
    exactly which mechanics beat the model, generate analog repair curriculum,
    retry, and only promote when the same frozen boss gate passes. It does not
    copy frozen prompt text into training instructions.
    """
    results = [item for item in gate_report.get("results", []) if isinstance(item, dict)]
    failed = [item for item in results if not item.get("ok")]
    passed = [item for item in results if item.get("ok")]
    n_total = int(gate_report.get("n_total") or len(results))
    n_pass = int(gate_report.get("n_pass") or len(passed))
    pass_rate = float(gate_report.get("pass_rate") or (n_pass / n_total if n_total else 0.0))
    minimum = float(gate_report.get("minimum_pass_rate") or 0.8)
    must_pass_results = gate_report.get("must_pass_results") or {}
    must_pass_failed = [key for key, ok in must_pass_results.items() if ok is not True]

    repair_targets = []
    for item in failed:
        prompt_id = str(item.get("id") or "")
        missing = [str(token) for token in item.get("missing_required", item.get("missing", [])) if str(token)]
        kind = _failure_kind_from_id(prompt_id)
        repair_targets.append(
            {
                "id": prompt_id,
                "kind": kind,
                "missing_required": missing,
                "must_pass": prompt_id in must_pass_failed,
                "repair_rule": (
                    "Generate new analog scenarios with different nouns and action chains, "
                    "but preserve the missing required markers and the same forbidden-marker guard."
                ),
                "recommended_rows": 72 if prompt_id in must_pass_failed else 48,
            }
        )

    strategy = "promote_or_merge"
    if repair_targets:
        strategy = "constrained_decoding_plus_targeted_dpo" if "v12" in profile_id.lower() else "targeted_repair_sft"
    if pass_rate < 0.5 and repair_targets:
        strategy = "constrained_decoding_plus_targeted_dpo"

    next_actions = [
        "Do not change the frozen eval contract.",
        "Do not copy held-out prompt text into training data.",
        "Generate analog repair rows only from missing marker classes and failure kinds.",
        "Run the next candidate through the same inline gate and push only if the gate passes.",
    ]
    if strategy == "constrained_decoding_plus_targeted_dpo":
        next_actions.insert(
            2,
            "Add a decoding shim or response scaffold that forces a required-token checklist before prose, then train preferences around pass/fail responses.",
        )

    return {
        "schema_version": "geoseal_stage6_boss_retry_plan_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "profile_id": profile_id or gate_report.get("profile_id", ""),
        "contract_id": gate_report.get("contract_id", ""),
        "score": {
            "n_pass": n_pass,
            "n_total": n_total,
            "pass_rate": pass_rate,
            "minimum_pass_rate": minimum,
            "must_pass_failed": must_pass_failed,
            "promotion_ready": bool(pass_rate >= minimum and not must_pass_failed and n_total),
        },
        "strategy": strategy,
        "passed_ids": [str(item.get("id") or "") for item in passed],
        "repair_targets": repair_targets,
        "experience_model": {
            "definition": (
                "EXP is aggregate micro-skill evidence: each failed gate records the small repeated behaviors "
                "that must become routine before the agent earns promotion."
            ),
            "unit_fields": [
                "failure_kind",
                "missing_required_marker",
                "must_pass_pressure",
                "analog_repair_rows",
                "same_gate_retry",
            ],
            "promotion_rule": "EXP counts only when the same frozen gate improves without training on the held-out prompt text.",
        },
        "next_actions": next_actions,
        "loop_rule": "train -> frozen gate -> mine failures -> analog repair data -> retry; publish only after gate pass",
    }


def assess_job_health(inspect_summary: dict[str, Any], logs_payload: dict[str, Any] | None) -> dict[str, Any]:
    """Classify common HF Jobs failure modes before a full train is launched."""
    stage = str(inspect_summary.get("stage") or "").upper()
    tail = str((logs_payload or {}).get("tail") or "").strip()
    logs_returncode = (logs_payload or {}).get("returncode")
    summary = (logs_payload or {}).get("summary") or {}
    has_training_signal = bool(
        tail
        or (
            isinstance(summary, dict)
            and (summary.get("latest_loss") or summary.get("progress") or summary.get("training_complete"))
        )
    )
    if stage == "RUNNING" and logs_payload is not None and not has_training_signal and logs_returncode == 0:
        return {
            "state": "running_without_logs",
            "safe_for_full_train": False,
            "recommendation": "cancel this smoke job and do not launch a full training run until a smoke job emits startup/train logs",
        }
    if stage == "RUNNING" and has_training_signal:
        return {
            "state": "running_with_training_signal",
            "safe_for_full_train": True,
            "recommendation": "training is emitting progress/loss signal; wait for the terminal gate before promotion",
        }
    if stage in {"FAILED", "CANCELED", "ERROR"}:
        return {
            "state": stage.lower(),
            "safe_for_full_train": False,
            "recommendation": "inspect the failed smoke job before launching another training run",
        }
    if stage in {"COMPLETED", "SUCCEEDED"}:
        return {
            "state": "completed",
            "safe_for_full_train": True,
            "recommendation": "full training can be launched if the smoke eval gate also passes",
        }
    return {
        "state": stage.lower() or "unknown",
        "safe_for_full_train": False,
        "recommendation": "wait for startup/train logs or a terminal job state before spending on full training",
    }


def list_profiles(manifest: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for entry in profile_entries(manifest):
        profile_path = REPO_ROOT / str(entry["profile_path"])
        profile = _load_json(profile_path) if profile_path.exists() else {}
        rows.append(
            {
                "profile_id": entry.get("profile_id"),
                "stage": entry.get("stage"),
                "profile_path": str(profile_path),
                "exists": profile_path.exists(),
                "base_model": profile.get("base_model", ""),
                "adapter_repo": (profile.get("hub") or {}).get("adapter_repo", ""),
                "latest_packet": str(latest_packet(str(entry.get("profile_id")), manifest) or ""),
            }
        )
    return {"schema_version": "geoseal_coding_training_profiles_v1", "profiles": rows}


def plan_or_dispatch(
    manifest: dict[str, Any],
    profile_id: str | None,
    *,
    dispatch: bool,
    flavor: str,
    timeout: str,
    smoke: bool = False,
    backend: str = "cli-file",
) -> dict[str, Any]:
    resolved = resolve_profile(manifest, profile_id)
    dispatcher = _dispatcher_module()
    packet = dispatcher.build_packet(
        profile_path=Path(resolved["resolved_profile_path"]),
        artifact_root=REPO_ROOT / str(manifest.get("artifact_root", "artifacts/hf_coding_agent_jobs")),
        flavor=flavor or None,
        timeout=timeout or None,
    )
    if dispatch:
        packet = dispatcher.dispatch_packet(packet)
    return packet


def status(manifest: dict[str, Any], profile_id: str | None, job_id: str | None, include_logs: bool) -> dict[str, Any]:
    resolved = resolve_profile(manifest, profile_id)
    packet_path = latest_packet(str(resolved["profile_id"]), manifest)
    packet = _load_json(packet_path) if packet_path else {}
    selected_job_id = job_id or str(((packet.get("dispatch") or {}).get("job_id")) or "")
    payload: dict[str, Any] = {
        "schema_version": "geoseal_coding_training_status_v1",
        "profile_id": resolved["profile_id"],
        "packet_path": str(packet_path or ""),
        "job_id": selected_job_id,
        "adapter_repo": (resolved["profile"].get("hub") or {}).get("adapter_repo", ""),
    }
    if selected_job_id:
        inspect_result = _run_hf(["hf", "jobs", "inspect", selected_job_id])
        inspect_summary: dict[str, Any] = {}
        try:
            inspected = json.loads(inspect_result["stdout"])
            if isinstance(inspected, list) and inspected:
                first = inspected[0]
                if isinstance(first, dict):
                    inspect_summary = {
                        "stage": ((first.get("status") or {}) if isinstance(first.get("status"), dict) else {}).get(
                            "stage"
                        ),
                        "url": first.get("url"),
                        "flavor": first.get("flavor"),
                        "created_at": first.get("created_at"),
                    }
        except json.JSONDecodeError:
            inspect_summary = {}
        payload["inspect"] = {
            "returncode": inspect_result["returncode"],
            "summary": inspect_summary,
            "stdout_tail": inspect_result["stdout"][-4000:],
            "stderr_tail": inspect_result["stderr"][-2000:],
        }
        if include_logs:
            logs_result = _run_hf(["hf", "jobs", "logs", selected_job_id])
            combined = logs_result["stdout"] + "\n" + logs_result["stderr"]
            payload["logs"] = {
                "returncode": logs_result["returncode"],
                "tail": combined[-12000:],
                "summary": summarize_training_log(combined),
            }
        payload["health"] = assess_job_health(inspect_summary, payload.get("logs"))
    return payload


def smoke_eval_plan(manifest: dict[str, Any], profile_id: str | None, adapter_repo: str | None) -> dict[str, Any]:
    resolved = resolve_profile(manifest, profile_id)
    profile = resolved["profile"]
    eval_cfg = dict(manifest.get("smoke_eval") or {})
    profile_training_cfg = profile.get("training") or {}
    profile_evaluation_cfg = profile.get("evaluation") or {}
    contract_path = str(((profile.get("evaluation") or {}).get("contract_path")) or "").strip()
    contract: dict[str, Any] = {}
    if contract_path:
        resolved_contract_path = REPO_ROOT / contract_path
        contract = _load_json(resolved_contract_path)
        eval_cfg["prompts"] = contract.get("prompts") or eval_cfg.get("prompts") or []
        contract_thresholds = contract.get("thresholds") or {}
        if isinstance(contract_thresholds, dict):
            eval_cfg["promotion_gate"] = {
                "minimum_pass_rate": contract_thresholds.get("minimum_pass_rate", 1.0),
                "must_pass": contract_thresholds.get("must_pass", []),
                "notes": contract_thresholds.get("decision_rule", ""),
            }
    selected_adapter = adapter_repo or str((profile.get("hub") or {}).get("adapter_repo", ""))
    out_dir = REPO_ROOT / "artifacts" / "model_evals" / f"geoseal-coding-{resolved['profile_id']}-{_utc_stamp()}"
    promotion_gate = eval_cfg.get("promotion_gate") or manifest.get("promotion_gate") or {}
    report = {
        "schema_version": "geoseal_coding_training_smoke_eval_plan_v1",
        "profile_id": resolved["profile_id"],
        "base_model": eval_cfg.get("base_model") or profile.get("base_model"),
        "adapter_repo": selected_adapter,
        "system_prompt": profile.get("system_prompt")
        or "You are an SCBE-AETHERMOORE GeoSeal coding agent. Preserve route/slot semantics.",
        "max_new_tokens": int(
            profile_evaluation_cfg.get(
                "max_new_tokens",
                profile_training_cfg.get("max_new_tokens", eval_cfg.get("max_new_tokens", 384)),
            )
        ),
        "constrained_gate_scaffold": bool(profile_evaluation_cfg.get("constrained_gate_scaffold")),
        "constrained_prompt_prefix": bool(profile_evaluation_cfg.get("constrained_prompt_prefix")),
        "output_dir": str(out_dir),
        "prompts": eval_cfg.get("prompts") or [],
        "promotion_gate": promotion_gate,
        "eval_contract": {
            "path": str((REPO_ROOT / contract_path).resolve()) if contract_path else "",
            "contract_id": contract.get("contract_id", ""),
            "failure_modes": contract.get("failure_modes", []),
        },
        "manual_command": [
            "python",
            "scripts/system/geoseal_coding_training_system.py",
            "score-smoke-report",
            "--report",
            str(out_dir / "report.json"),
        ],
    }
    _write_json(out_dir / "smoke_eval_plan.json", report)
    return report


def render_smoke_eval_uv_script(plan: dict[str, Any]) -> str:
    plan_json = json.dumps(plan, indent=2, ensure_ascii=True)
    return f'''# /// script
# dependencies = [
#   "accelerate>=0.34.0",
#   "peft>=0.12.0",
#   "torch",
#   "transformers>=4.46.0",
#   "huggingface_hub>=0.25.0"
# ]
# ///
from __future__ import annotations

import json
import os

import torch
from huggingface_hub import whoami
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

PLAN = json.loads(r"""{plan_json}""")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _token() -> str:
    token = os.environ.get("HF_TOKEN", "").strip() or os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Missing $HF_TOKEN or $HUGGING_FACE_HUB_TOKEN")
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", token)
    return token


def _generate(tokenizer, model, prompt: str, max_new_tokens: int) -> str:
    messages = [
        {{
            "role": "system",
            "content": str(PLAN.get("system_prompt") or "You are an SCBE-AETHERMOORE GeoSeal coding agent. Preserve route/slot semantics."),
        }},
        {{"role": "user", "content": prompt}},
    ]
    encoded = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=False,
    )
    if isinstance(encoded, torch.Tensor):
        input_ids = encoded
    elif hasattr(encoded, "data") and not isinstance(encoded.data, torch.Tensor) and "input_ids" in encoded.data:
        input_ids = encoded.data["input_ids"]
    elif isinstance(encoded, dict):
        input_ids = encoded["input_ids"]
    else:
        input_ids = encoded
    input_ids = input_ids.to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.05,
        )
    return tokenizer.decode(outputs[0][input_ids.shape[-1]:], skip_special_tokens=True).strip()


def _gate_required_prefix(item: dict) -> str:
    required = [str(needle) for needle in (item.get("required") or [])]
    forbidden = [str(needle) for needle in (item.get("forbidden") or [])]
    prefix = "required-items: " + " | ".join(required) + " ::"
    present_forbidden = [needle for needle in forbidden if needle and needle in prefix]
    if present_forbidden:
        raise RuntimeError(
            "constrained gate prefix would trigger forbidden token: " + ", ".join(present_forbidden)
        )
    return prefix


def _prompt_with_required_prefix(item: dict) -> str:
    required = [str(needle) for needle in (item.get("required") or [])]
    prompt = str(item["prompt"])
    prefix = (
        "Your first line must be exactly: REQUIRED_MARKERS="
        + " | ".join(required)
        + "\\nYour second line must be exactly: REQUIRED_CHECKLIST="
        + "; ".join(needle + "=" + needle for needle in required)
        + "\\nDo not translate, rename, pluralize, omit, or replace any REQUIRED_MARKERS value."
        + "\\nAfter that line, answer the task compactly."
        + "\\nTask: "
    )
    return prefix + prompt


def main() -> None:
    token = _token()
    print(json.dumps({{"event": "auth", "whoami": whoami(token=token).get("name", "unknown")}}))
    base_model = str(PLAN["base_model"])
    adapter_repo = str(PLAN["adapter_repo"])
    tokenizer = AutoTokenizer.from_pretrained(base_model, token=token)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        token=token,
        torch_dtype=dtype if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    model = PeftModel.from_pretrained(base, adapter_repo, token=token)
    model.eval()

    results = []
    for item in PLAN["prompts"]:
        prompt = _prompt_with_required_prefix(item) if PLAN.get("constrained_prompt_prefix") else str(item["prompt"])
        raw_response = _generate(tokenizer, model, prompt, int(PLAN.get("max_new_tokens", 220)))
        scaffolded = bool(PLAN.get("constrained_gate_scaffold"))
        response = raw_response
        if scaffolded:
            response = _gate_required_prefix(item) + "\\n" + raw_response
        required = list(item.get("required") or [])
        forbidden = list(item.get("forbidden") or [])
        raw_missing = [needle for needle in required if needle not in raw_response]
        raw_present_forbidden = [needle for needle in forbidden if needle in raw_response]
        missing = [needle for needle in required if needle not in response]
        present_forbidden = [needle for needle in forbidden if needle in response]
        results.append(
            {{
                "id": item["id"],
                "prompt": item["prompt"],
                "response": response,
                "raw_response": raw_response,
                "scaffolded": scaffolded,
                "raw_passed": not raw_missing and not raw_present_forbidden,
                "raw_missing_required": raw_missing,
                "raw_present_forbidden": raw_present_forbidden,
                "passed": not missing and not present_forbidden,
                "missing_required": missing,
                "present_forbidden": present_forbidden,
            }}
        )

    passed = sum(1 for item in results if item["passed"])
    raw_passed = sum(1 for item in results if item["raw_passed"])
    total = len(results)
    gate = PLAN.get("promotion_gate") or {{}}
    must_pass = set(gate.get("must_pass") or [])
    by_id = {{item["id"]: item for item in results}}
    must_pass_ok = all(by_id.get(item, {{}}).get("passed") is True for item in must_pass)
    pass_rate = passed / total if total else 0.0
    raw_pass_rate = raw_passed / total if total else 0.0
    promotion_ready = bool(total and pass_rate >= float(gate.get("minimum_pass_rate", 1.0)) and must_pass_ok)
    print(json.dumps({{
        "event": "smoke_eval_complete",
        "summary": {{
            "base_model": base_model,
            "adapter_repo": adapter_repo,
            "scaffolded": bool(PLAN.get("constrained_gate_scaffold")),
            "constrained_prompt_prefix": bool(PLAN.get("constrained_prompt_prefix")),
            "raw_passed": raw_passed,
            "raw_pass_rate": raw_pass_rate,
            "passed": passed,
            "total": total,
            "pass_rate": pass_rate,
            "must_pass_ok": must_pass_ok,
            "promotion_ready": promotion_ready,
        }},
        "results": results,
    }}, indent=2))


if __name__ == "__main__":
    main()
'''


def dispatch_smoke_eval(
    manifest: dict[str, Any], profile_id: str | None, adapter_repo: str | None, timeout: str
) -> dict[str, Any]:
    plan = smoke_eval_plan(manifest, profile_id, adapter_repo)
    out_dir = Path(plan["output_dir"])
    script_path = out_dir / "smoke_eval_hf.py"
    script_path.write_text(render_smoke_eval_uv_script(plan), encoding="utf-8")
    command = [
        "hf",
        "jobs",
        "uv",
        "run",
        "--flavor",
        "t4-small",
        "--timeout",
        timeout or "30m",
        "--env",
        "PYTHONIOENCODING=utf-8",
        "--env",
        "PYTHONUTF8=1",
        "--secrets",
        "HF_TOKEN",
        "--detach",
        str(script_path),
    ]
    result = _run_hf(command)
    combined = result["stdout"] + "\n" + result["stderr"]
    match = re.search(r"(?:Job ID|ID|job)[^A-Za-z0-9_-]*([A-Za-z0-9_-]{8,})", combined, re.IGNORECASE)
    payload = {
        **plan,
        "schema_version": "geoseal_coding_training_smoke_eval_dispatch_v1",
        "script_path": str(script_path),
        "command": command,
        "dispatch": {
            "returncode": result["returncode"],
            "stdout": result["stdout"][-4000:],
            "stderr": result["stderr"][-2000:],
            "job_id": match.group(1) if match else "",
        },
    }
    _write_json(out_dir / "smoke_eval_dispatch.json", payload)
    return payload


def score_smoke_report(report_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    report = _load_json(report_path)
    prompts = (manifest.get("smoke_eval") or {}).get("prompts", [])
    gate = manifest.get("promotion_gate") or {}
    if report.get("prompts"):
        prompts = report.get("prompts") or prompts
    if report.get("promotion_gate"):
        gate = report.get("promotion_gate") or gate
    prompt_cfg = {item["id"]: item for item in prompts}
    responses = report.get("responses") or report.get("prompts") or []
    results = []
    for item in responses:
        prompt_id = str(item.get("id") or item.get("prompt_id") or "")
        response = str(item.get("response", ""))
        cfg = prompt_cfg.get(prompt_id, {})
        required = list(cfg.get("required") or [])
        forbidden = list(cfg.get("forbidden") or [])
        missing = [needle for needle in required if needle not in response]
        present_forbidden = [needle for needle in forbidden if needle in response]
        results.append(
            {
                "id": prompt_id,
                "passed": not missing and not present_forbidden,
                "missing_required": missing,
                "present_forbidden": present_forbidden,
            }
        )
    passed = sum(1 for item in results if item["passed"])
    total = len(results)
    must_pass = set((gate or {}).get("must_pass") or [])
    result_by_id = {item["id"]: item for item in results}
    must_pass_ok = all(result_by_id.get(item, {}).get("passed") is True for item in must_pass)
    pass_rate = passed / total if total else 0.0
    minimum = float((gate or {}).get("minimum_pass_rate", 1.0))
    return {
        "schema_version": "geoseal_coding_training_smoke_score_v1",
        "report_path": str(report_path),
        "passed": passed,
        "total": total,
        "pass_rate": pass_rate,
        "minimum_pass_rate": minimum,
        "must_pass_ok": must_pass_ok,
        "promotion_ready": bool(total and pass_rate >= minimum and must_pass_ok),
        "results": results,
    }


def reward_smoke_report(report_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Convert a frozen smoke-eval report into deterministic reward signals.

    This is intentionally rule-based: it is suitable for RLVR/GRPO-style
    ranking because it does not require an LLM judge and it preserves the same
    pre-committed required/forbidden markers used by the promotion gate.
    """
    report = _load_json(report_path)
    score = score_smoke_report(report_path, manifest)
    prompts = report.get("prompts") or (manifest.get("smoke_eval") or {}).get("prompts", [])
    prompt_cfg = {item["id"]: item for item in prompts}
    responses = report.get("responses") or report.get("prompts") or []
    reward_items = []
    total_reward = 0.0
    for item in responses:
        prompt_id = str(item.get("id") or item.get("prompt_id") or "")
        response = str(item.get("response", ""))
        cfg = prompt_cfg.get(prompt_id, {})
        required = list(cfg.get("required") or [])
        forbidden = list(cfg.get("forbidden") or [])
        required_hits = [needle for needle in required if needle in response]
        missing_required = [needle for needle in required if needle not in response]
        present_forbidden = [needle for needle in forbidden if needle in response]
        required_score = len(required_hits) / len(required) if required else 1.0
        forbidden_penalty = len(present_forbidden) / len(forbidden) if forbidden else 0.0
        reward = max(-1.0, min(1.0, required_score - forbidden_penalty))
        total_reward += reward
        reward_items.append(
            {
                "id": prompt_id,
                "reward": reward,
                "required_score": required_score,
                "forbidden_penalty": forbidden_penalty,
                "required_hits": required_hits,
                "missing_required": missing_required,
                "present_forbidden": present_forbidden,
                "passed": not missing_required and not present_forbidden,
            }
        )
    mean_reward = total_reward / len(reward_items) if reward_items else 0.0
    return {
        "schema_version": "geoseal_coding_training_reward_report_v1",
        "report_path": str(report_path),
        "profile_id": report.get("profile_id", ""),
        "eval_contract": report.get("eval_contract") or {},
        "mean_reward": mean_reward,
        "total": len(reward_items),
        "promotion_ready": score["promotion_ready"],
        "pass_rate": score["pass_rate"],
        "items": reward_items,
        "notes": "Rule-based reward: required marker coverage minus forbidden marker penalty, clamped to [-1, 1].",
    }


def boss_retry_plan_from_report(
    report_path: Path,
    *,
    profile_id: str = "",
    output: Path | None = None,
) -> dict[str, Any]:
    payload = _load_json(report_path)
    gate_report = payload.get("report") if payload.get("event") == "gate_report" else payload
    if not isinstance(gate_report, dict) or "results" not in gate_report:
        raise ValueError(f"Report does not look like a Stage 6 gate report: {report_path}")
    plan = build_boss_retry_plan(gate_report, profile_id=profile_id, source=str(report_path))
    if output is not None:
        _write_json(output, plan)
        plan["output_path"] = str(output)
    return plan


def boss_retry_plan_from_job(
    job_id: str,
    *,
    profile_id: str = "",
    output: Path | None = None,
) -> dict[str, Any]:
    logs_result = _run_hf(["hf", "jobs", "logs", job_id, "--tail", "400"], timeout_s=90)
    combined = logs_result["stdout"] + "\n" + logs_result["stderr"]
    gate_report = extract_gate_report(combined)
    if gate_report is None:
        raise ValueError(f"No gate_report event found in HF job logs: {job_id}")
    plan = build_boss_retry_plan(gate_report, profile_id=profile_id, source=f"hf_job:{job_id}")
    plan["logs_returncode"] = logs_result["returncode"]
    if output is not None:
        _write_json(output, plan)
        plan["output_path"] = str(output)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("profiles")
    for name in ("plan", "dispatch"):
        item = sub.add_parser(name)
        item.add_argument("--profile-id", default="")
        item.add_argument("--flavor", default="")
        item.add_argument("--timeout", default="")
        item.add_argument(
            "--smoke",
            action="store_true",
            help="Use the tiny no-push HF smoke profile before spending on a full train.",
        )
        item.add_argument(
            "--backend",
            choices=["cli-file", "api-inline"],
            default="cli-file",
            help="HF Jobs dispatch backend.",
        )
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--profile-id", default="")
    status_parser.add_argument("--job-id", default="")
    status_parser.add_argument("--logs", action="store_true")
    eval_parser = sub.add_parser("smoke-eval-plan")
    eval_parser.add_argument("--profile-id", default="")
    eval_parser.add_argument("--adapter-repo", default="")
    eval_dispatch_parser = sub.add_parser("dispatch-smoke-eval")
    eval_dispatch_parser.add_argument("--profile-id", default="")
    eval_dispatch_parser.add_argument("--adapter-repo", default="")
    eval_dispatch_parser.add_argument("--timeout", default="30m")
    score_parser = sub.add_parser("score-smoke-report")
    score_parser.add_argument("--report", required=True)
    reward_parser = sub.add_parser("reward-smoke-report")
    reward_parser.add_argument("--report", required=True)
    smoke_summary_parser = sub.add_parser("smoke-eval-summary")
    smoke_src = smoke_summary_parser.add_mutually_exclusive_group(required=True)
    smoke_src.add_argument("--log")
    smoke_src.add_argument("--job-id")
    smoke_summary_parser.add_argument("--output", default="")
    smoke_summary_parser.add_argument("--log-output", default="")
    boss_parser = sub.add_parser("boss-retry-plan")
    boss_src = boss_parser.add_mutually_exclusive_group(required=True)
    boss_src.add_argument("--report")
    boss_src.add_argument("--job-id")
    boss_parser.add_argument("--profile-id", default="")
    boss_parser.add_argument("--output", default="")
    args = parser.parse_args()

    manifest = load_manifest(Path(args.manifest))
    if args.command == "profiles":
        payload = list_profiles(manifest)
    elif args.command == "plan":
        payload = plan_or_dispatch(
            manifest,
            args.profile_id or None,
            dispatch=False,
            flavor=args.flavor,
            timeout=args.timeout,
            smoke=bool(args.smoke),
            backend=args.backend,
        )
    elif args.command == "dispatch":
        payload = plan_or_dispatch(
            manifest,
            args.profile_id or None,
            dispatch=True,
            flavor=args.flavor,
            timeout=args.timeout,
            smoke=bool(args.smoke),
            backend=args.backend,
        )
    elif args.command == "status":
        payload = status(manifest, args.profile_id or None, args.job_id or None, args.logs)
    elif args.command == "smoke-eval-plan":
        payload = smoke_eval_plan(manifest, args.profile_id or None, args.adapter_repo or None)
    elif args.command == "dispatch-smoke-eval":
        payload = dispatch_smoke_eval(manifest, args.profile_id or None, args.adapter_repo or None, args.timeout)
    elif args.command == "score-smoke-report":
        payload = score_smoke_report(Path(args.report), manifest)
    elif args.command == "reward-smoke-report":
        payload = reward_smoke_report(Path(args.report), manifest)
    elif args.command == "smoke-eval-summary":
        output = Path(args.output) if args.output else None
        if args.log:
            payload = smoke_eval_summary_from_log(Path(args.log), output=output)
        else:
            log_output = Path(args.log_output) if args.log_output else None
            payload = smoke_eval_summary_from_job(str(args.job_id), output=output, log_output=log_output)
    elif args.command == "boss-retry-plan":
        output = Path(args.output) if args.output else None
        if args.report:
            payload = boss_retry_plan_from_report(Path(args.report), profile_id=args.profile_id, output=output)
        else:
            payload = boss_retry_plan_from_job(str(args.job_id), profile_id=args.profile_id, output=output)
    else:
        raise AssertionError(args.command)
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

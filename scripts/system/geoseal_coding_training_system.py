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


def _run_hf(args: list[str]) -> dict[str, Any]:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    result = subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
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


def plan_or_dispatch(manifest: dict[str, Any], profile_id: str | None, *, dispatch: bool, flavor: str, timeout: str) -> dict[str, Any]:
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
                        "stage": ((first.get("status") or {}) if isinstance(first.get("status"), dict) else {}).get("stage"),
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
    return payload


def smoke_eval_plan(manifest: dict[str, Any], profile_id: str | None, adapter_repo: str | None) -> dict[str, Any]:
    resolved = resolve_profile(manifest, profile_id)
    profile = resolved["profile"]
    eval_cfg = dict(manifest.get("smoke_eval") or {})
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
            "content": "You are an SCBE-AETHERMOORE GeoSeal coding agent. Obey the requested target language and preserve route/slot semantics.",
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
            max_new_tokens=int(PLAN.get("max_new_tokens", 220)),
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.05,
        )
    return tokenizer.decode(outputs[0][input_ids.shape[-1]:], skip_special_tokens=True).strip()


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
        response = _generate(tokenizer, model, str(item["prompt"]), int(PLAN.get("max_new_tokens", 220)))
        required = list(item.get("required") or [])
        forbidden = list(item.get("forbidden") or [])
        missing = [needle for needle in required if needle not in response]
        present_forbidden = [needle for needle in forbidden if needle in response]
        results.append(
            {{
                "id": item["id"],
                "prompt": item["prompt"],
                "response": response,
                "passed": not missing and not present_forbidden,
                "missing_required": missing,
                "present_forbidden": present_forbidden,
            }}
        )

    passed = sum(1 for item in results if item["passed"])
    total = len(results)
    gate = PLAN.get("promotion_gate") or {{}}
    must_pass = set(gate.get("must_pass") or [])
    by_id = {{item["id"]: item for item in results}}
    must_pass_ok = all(by_id.get(item, {{}}).get("passed") is True for item in must_pass)
    pass_rate = passed / total if total else 0.0
    promotion_ready = bool(total and pass_rate >= float(gate.get("minimum_pass_rate", 1.0)) and must_pass_ok)
    print(json.dumps({{
        "event": "smoke_eval_complete",
        "summary": {{
            "base_model": base_model,
            "adapter_repo": adapter_repo,
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


def dispatch_smoke_eval(manifest: dict[str, Any], profile_id: str | None, adapter_repo: str | None, timeout: str) -> dict[str, Any]:
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
    args = parser.parse_args()

    manifest = load_manifest(Path(args.manifest))
    if args.command == "profiles":
        payload = list_profiles(manifest)
    elif args.command == "plan":
        payload = plan_or_dispatch(manifest, args.profile_id or None, dispatch=False, flavor=args.flavor, timeout=args.timeout)
    elif args.command == "dispatch":
        payload = plan_or_dispatch(manifest, args.profile_id or None, dispatch=True, flavor=args.flavor, timeout=args.timeout)
    elif args.command == "status":
        payload = status(manifest, args.profile_id or None, args.job_id or None, args.logs)
    elif args.command == "smoke-eval-plan":
        payload = smoke_eval_plan(manifest, args.profile_id or None, args.adapter_repo or None)
    elif args.command == "dispatch-smoke-eval":
        payload = dispatch_smoke_eval(manifest, args.profile_id or None, args.adapter_repo or None, args.timeout)
    elif args.command == "score-smoke-report":
        payload = score_smoke_report(Path(args.report), manifest)
    else:
        raise AssertionError(args.command)
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

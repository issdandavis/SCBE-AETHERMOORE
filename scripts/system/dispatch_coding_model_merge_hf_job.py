#!/usr/bin/env python3
"""Plan and dispatch a Hugging Face job that merges coding-agent LoRA adapters."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = REPO_ROOT / "config" / "model_training" / "coding-agent-qwen-merged-coding-model.json"
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "hf_coding_model_merges"


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


def normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    if profile.get("schema_version") != "scbe_coding_model_merge_profile_v1":
        raise ValueError("Unsupported coding model merge profile.")
    adapters = [dict(item) for item in profile.get("adapters") or [] if isinstance(item, dict)]
    if not adapters:
        raise ValueError("Merge profile must include at least one adapter.")
    weights = [float(item.get("weight", 0.0)) for item in adapters]
    total = sum(weights)
    if total <= 0:
        raise ValueError("Adapter weights must sum to a positive value.")
    for item, weight in zip(adapters, weights):
        item["weight"] = weight / total
        if not item.get("adapter_repo"):
            raise ValueError(f"Adapter is missing adapter_repo: {item}")
    profile = dict(profile)
    profile["adapters"] = adapters
    return profile


def build_packet(profile_path: Path, artifact_root: Path, flavor: str | None = None, timeout: str | None = None) -> dict[str, Any]:
    profile_path = profile_path.resolve()
    profile = normalize_profile(_load_json(profile_path))
    run_dir = artifact_root / str(profile["merge_id"]) / _utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    packet = {
        "schema_version": "scbe_coding_model_merge_job_packet_v1",
        "prepared_at_utc": _utc_stamp(),
        "profile_path": str(profile_path),
        "run_dir": str(run_dir),
        "script_path": str(run_dir / "merge_coding_model_hf.py"),
        "merge_id": profile["merge_id"],
        "base_model": profile["base_model"],
        "output_model_repo": profile["output_model_repo"],
        "merge_mode": profile.get("merge_mode", "weighted"),
        "adapters": profile["adapters"],
        "blocked_adapters": profile.get("blocked_adapters", []),
        "pre_merge_gates": profile.get("pre_merge_gates", {}),
        "execution": {
            "flavor": flavor or (profile.get("execution") or {}).get("hf_flavor", "t4-small"),
            "timeout": timeout or (profile.get("execution") or {}).get("timeout", "1h"),
        },
    }
    _write_json(run_dir / "merge_packet.json", packet)
    script = render_merge_script(packet)
    Path(packet["script_path"]).write_text(script, encoding="utf-8")
    (run_dir / "RUN.md").write_text(
        "\n".join(
            [
                "# Coding Model Merge Job",
                "",
                f"- Merge ID: `{packet['merge_id']}`",
                f"- Base model: `{packet['base_model']}`",
                f"- Output model repo: `{packet['output_model_repo']}`",
                f"- Mode: `{packet['merge_mode']}`",
                "",
                "## Dispatch",
                "",
                "```powershell",
                f"python scripts\\system\\dispatch_coding_model_merge_hf_job.py dispatch --profile {profile_path}",
                "```",
                "",
                "## Boundary",
                "",
                "This performs a full-model merge on Hugging Face Jobs. Do not dispatch until the frozen Stage 6 smoke eval is scored.",
            ]
        ),
        encoding="utf-8",
    )
    return packet


def render_merge_script(packet: dict[str, Any]) -> str:
    packet_json = json.dumps(packet, indent=2, ensure_ascii=True)
    return f'''# /// script
# dependencies = [
#   "accelerate>=0.34.0",
#   "peft>=0.12.0",
#   "torch",
#   "transformers>=4.46.0",
#   "huggingface_hub>=0.25.0",
#   "safetensors"
# ]
# ///
from __future__ import annotations

import json
import os
from io import BytesIO

import torch
from huggingface_hub import HfApi, whoami
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

PACKET = json.loads(r"""{packet_json}""")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _token() -> str:
    token = os.environ.get("HF_TOKEN", "").strip() or os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Missing $HF_TOKEN or $HUGGING_FACE_HUB_TOKEN")
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", token)
    return token


def _load_base(token: str):
    base_model = str(PACKET["base_model"])
    tokenizer = AutoTokenizer.from_pretrained(base_model, token=token, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        token=token,
        torch_dtype=dtype if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    return tokenizer, model


def _weighted_merge(base, token: str):
    adapters = PACKET["adapters"]
    names = [f"a{{idx}}" for idx in range(len(adapters))]
    model = PeftModel.from_pretrained(base, adapters[0]["adapter_repo"], adapter_name=names[0], token=token)
    for name, adapter in zip(names[1:], adapters[1:]):
        model.load_adapter(adapter["adapter_repo"], adapter_name=name, token=token)
    if not hasattr(model, "add_weighted_adapter"):
        raise RuntimeError("Installed PEFT does not support add_weighted_adapter.")
    weights = [float(item["weight"]) for item in adapters]
    model.add_weighted_adapter(names, weights, adapter_name="scbe_coding_merged", combination_type="linear")
    model.set_adapter("scbe_coding_merged")
    return model.merge_and_unload()


def _stack_merge(base, token: str):
    model = base
    for adapter in PACKET["adapters"]:
        model = PeftModel.from_pretrained(model, adapter["adapter_repo"], token=token)
        model = model.merge_and_unload()
    return model


def main() -> None:
    token = _token()
    api = HfApi(token=token)
    print(json.dumps({{"event": "auth", "whoami": whoami(token=token).get("name", "unknown")}}))
    tokenizer, base = _load_base(token)
    mode = str(PACKET.get("merge_mode", "weighted"))
    if mode == "weighted":
        merged = _weighted_merge(base, token)
    elif mode == "stack":
        merged = _stack_merge(base, token)
    else:
        raise RuntimeError(f"Unsupported merge mode: {{mode}}")

    output_repo = str(PACKET["output_model_repo"])
    api.create_repo(output_repo, repo_type="model", exist_ok=True, private=False)
    merged.push_to_hub(output_repo, token=token, safe_serialization=True)
    tokenizer.push_to_hub(output_repo, token=token)
    summary = {{
        "schema_version": "scbe_coding_model_merge_result_v1",
        "merge_id": PACKET["merge_id"],
        "base_model": PACKET["base_model"],
        "output_model_repo": output_repo,
        "merge_mode": mode,
        "adapters": PACKET["adapters"],
        "blocked_adapters": PACKET.get("blocked_adapters", []),
    }}
    api.upload_file(
        path_or_fileobj=BytesIO(json.dumps(summary, indent=2).encode("utf-8")),
        path_in_repo="scbe_merge_summary.json",
        repo_id=output_repo,
        repo_type="model",
    )
    print(json.dumps({{"event": "merge_complete", "summary": summary}}, indent=2))


if __name__ == "__main__":
    main()
'''


def dispatch_packet(packet: dict[str, Any]) -> dict[str, Any]:
    command = [
        "hf",
        "jobs",
        "uv",
        "run",
        "--flavor",
        str(packet["execution"]["flavor"]),
        "--timeout",
        str(packet["execution"]["timeout"]),
        "--env",
        "PYTHONIOENCODING=utf-8",
        "--env",
        "PYTHONUTF8=1",
        "--secrets",
        "HF_TOKEN",
        "--detach",
        str(packet["script_path"]),
    ]
    result = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    combined = result.stdout + "\n" + result.stderr
    match = re.search(r"(?:Job ID|ID|job)[^A-Za-z0-9_-]*([A-Za-z0-9_-]{8,})", combined, re.IGNORECASE)
    packet = dict(packet)
    packet["dispatch"] = {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-2000:],
        "job_id": match.group(1) if match else "",
    }
    _write_json(Path(packet["run_dir"]) / "merge_packet.json", packet)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "dispatch"):
        item = sub.add_parser(name)
        item.add_argument("--profile", default=str(DEFAULT_PROFILE))
        item.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
        item.add_argument("--flavor", default="")
        item.add_argument("--timeout", default="")
    args = parser.parse_args()
    packet = build_packet(Path(args.profile), Path(args.artifact_root), flavor=args.flavor or None, timeout=args.timeout or None)
    if args.command == "dispatch":
        packet = dispatch_packet(packet)
    print(json.dumps(packet, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Dispatch the SCBE-Gemma4 governance demo as an HF Job (~$0.50 on l4x1).

Use when local GPU is too small (Gemma 4 E2B-it = 5.1B params, doesn't fit
in 6GB VRAM at fp16). Generates a self-contained training-style script that
loads Gemma 4, runs both eval surfaces (executable + governance), uploads a
JSON report to a HF dataset repo.

Usage:
    python demos/gemma4_scbe_governance/dispatch_hf_job.py \\
      --base-model google/gemma-4-E2B-it
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "training_data"))
from build_executable_coding_v1_sft import PROBLEMS  # noqa: E402

DEFAULT_BASE = "google/gemma-4-E2B-it"
DEFAULT_OUT = REPO_ROOT / "artifacts" / "demo_gemma4"
DEFAULT_HOLDOUT = REPO_ROOT / "training-data" / "sft" / "executable_coding_v1_holdout.sft.jsonl"
DEFAULT_GOV_CONTRACT = REPO_ROOT / "config" / "model_training" / "coding_verification_eval_contract_v2.json"
DEFAULT_RESULT_DATASET = "issdandavis/scbe-eval-results"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_holdout(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        msgs = row["messages"]
        rows.append({
            "problem_id": row["metadata"]["problem_id"],
            "system": next(m["content"] for m in msgs if m["role"] == "system"),
            "user": next(m["content"] for m in msgs if m["role"] == "user"),
        })
    return rows


def build_packet(args) -> dict[str, Any]:
    holdout_rows = _load_holdout(args.holdout)
    contract = json.loads(args.gov_contract.read_text(encoding="utf-8"))
    run_dir = args.artifact_root / args.eval_id / _utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    packet = {
        "schema_version": "scbe_gemma4_demo_packet_v1",
        "prepared_at_utc": _utc_stamp(),
        "eval_id": args.eval_id,
        "run_dir": str(run_dir),
        "script_path": str(run_dir / "run_demo_hf.py"),
        "base_model": args.base_model,
        "result_dataset": args.result_dataset,
        "max_new_tokens": int(args.max_new_tokens),
        "execution": {"flavor": args.flavor, "timeout": args.timeout},
        "holdout": holdout_rows,
        "problems": PROBLEMS,
        "contract": contract,
    }
    (run_dir / "demo_packet.json").write_text(
        json.dumps(packet, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    Path(packet["script_path"]).write_text(_render_script(packet), encoding="utf-8")
    return packet


def _render_script(packet: dict[str, Any]) -> str:
    packet_json = json.dumps(packet, indent=2, ensure_ascii=True)
    return f'''# /// script
# dependencies = [
#   "accelerate>=0.34.0",
#   "torch",
#   "transformers>=4.50.0",
#   "huggingface_hub>=0.25.0",
#   "safetensors",
#   "pillow"
# ]
# ///
"""HF Job: SCBE-Gemma4 governance demo runner."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import torch
from huggingface_hub import HfApi, whoami
from transformers import AutoProcessor, AutoModelForImageTextToText

PACKET = json.loads(r"""{packet_json}""")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

CODE_BLOCK_RE = re.compile(r"```(?:python)?\\s*\\n?(.*?)```", re.DOTALL)


def _token() -> str:
    token = os.environ.get("HF_TOKEN", "").strip() or os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Missing $HF_TOKEN or $HUGGING_FACE_HUB_TOKEN")
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", token)
    return token


def extract_code(response):
    if not response:
        return ""
    m = CODE_BLOCK_RE.search(response)
    if m:
        return m.group(1).strip()
    return response.strip()


def score_executable_problem(problem, code):
    if not code:
        return {{"problem_id": problem["id"], "all_pass": False, "n_tests_pass": 0, "n_tests_total": len(problem["tests"])}}
    n_pass = 0
    for call_str, expected_repr in problem["tests"]:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "candidate.py"
            script.write_text(code + f"\\n_result = {{call_str}}\\nprint(repr(_result))\\n", encoding="utf-8")
            try:
                result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip() == expected_repr:
                    n_pass += 1
            except subprocess.TimeoutExpired:
                pass
    return {{
        "problem_id": problem["id"],
        "all_pass": n_pass == len(problem["tests"]),
        "n_tests_pass": n_pass,
        "n_tests_total": len(problem["tests"]),
    }}


def entry_present(entry, body_lower):
    if isinstance(entry, list):
        return any(str(alt).lower() in body_lower for alt in entry)
    return str(entry).lower() in body_lower


def score_governance_prompt(prompt, response):
    body_lower = (response or "").lower()
    missing = [
        e if isinstance(e, str) else " | ".join(e)
        for e in (prompt.get("required") or [])
        if not entry_present(e, body_lower)
    ]
    triggered = [str(t) for t in (prompt.get("forbidden") or []) if str(t).lower() in body_lower]
    return {{
        "prompt_id": prompt.get("id"),
        "ok": (not missing) and (not triggered),
        "missing_required": missing,
        "triggered_forbidden": triggered,
    }}


def scbe_shim_wrap(messages, required):
    if not required:
        return messages
    flat = [r if isinstance(r, str) else " | ".join(r) for r in required]
    suffix = "\\n\\n[SCBE shim] Your response must include the following anchors verbatim where natural in your answer: " + " | ".join(flat) + "."
    msgs = list(messages)
    if msgs and msgs[-1]["role"] == "user":
        msgs[-1] = {{"role": "user", "content": msgs[-1]["content"] + suffix}}
    else:
        msgs.append({{"role": "user", "content": suffix.strip()}})
    return msgs


def main():
    token = _token()
    print(json.dumps({{"event": "auth", "whoami": whoami(token=token).get("name", "unknown")}}))
    base_model_id = str(PACKET["base_model"])
    processor = AutoProcessor.from_pretrained(base_model_id, token=token, trust_remote_code=True)
    if processor.tokenizer.pad_token_id is None:
        processor.tokenizer.pad_token_id = processor.tokenizer.eos_token_id
    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    model = AutoModelForImageTextToText.from_pretrained(
        base_model_id,
        token=token,
        dtype=dtype if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    model.eval()
    print(json.dumps({{"event": "model_loaded", "base_model": base_model_id}}))

    def generate(messages):
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=int(PACKET["max_new_tokens"]),
                do_sample=False,
                pad_token_id=processor.tokenizer.pad_token_id or processor.tokenizer.eos_token_id,
            )
        gen_ids = out[0][inputs.input_ids.shape[1]:]
        return processor.decode(gen_ids, skip_special_tokens=True)

    problems_by_id = {{p["id"]: p for p in PACKET["problems"]}}
    exec_bare = []
    for row in PACKET["holdout"]:
        pid = row["problem_id"]
        problem = problems_by_id[pid]
        msgs = [
            {{"role": "system", "content": row["system"]}},
            {{"role": "user", "content": row["user"]}},
        ]
        response = generate(msgs)
        result = score_executable_problem(problem, extract_code(response))
        result["response"] = response
        exec_bare.append(result)
        print(json.dumps({{"event": "exec_done", "problem_id": pid,
                           "n_tests_pass": result["n_tests_pass"],
                           "n_tests_total": result["n_tests_total"]}}))

    gov_bare = []
    gov_shim = []
    for prompt_def in PACKET["contract"]["prompts"]:
        bare_msgs = [{{"role": "user", "content": prompt_def["prompt"]}}]
        bare_resp = generate(bare_msgs)
        bare_score = score_governance_prompt(prompt_def, bare_resp)
        bare_score["response"] = bare_resp
        gov_bare.append(bare_score)
        shim_msgs = scbe_shim_wrap(bare_msgs, prompt_def.get("required") or [])
        shim_resp = generate(shim_msgs)
        shim_score = score_governance_prompt(prompt_def, shim_resp)
        shim_score["response"] = shim_resp
        gov_shim.append(shim_score)
        print(json.dumps({{"event": "gov_done", "prompt_id": prompt_def["id"],
                           "bare_ok": bare_score["ok"], "shim_ok": shim_score["ok"]}}))

    summary = {{
        "schema_version": "scbe_gemma4_demo_report_v1",
        "base_model": base_model_id,
        "eval_id": str(PACKET["eval_id"]),
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "executable_holdout": {{
            "n_total": len(exec_bare),
            "bare_n_pass": sum(1 for r in exec_bare if r["all_pass"]),
            "bare_pass_rate": (sum(1 for r in exec_bare if r["all_pass"]) / len(exec_bare)) if exec_bare else 0.0,
        }},
        "governance_gate": {{
            "n_total": len(gov_bare),
            "bare_n_pass": sum(1 for r in gov_bare if r["ok"]),
            "shim_n_pass": sum(1 for r in gov_shim if r["ok"]),
            "bare_pass_rate": (sum(1 for r in gov_bare if r["ok"]) / len(gov_bare)) if gov_bare else 0.0,
            "shim_pass_rate": (sum(1 for r in gov_shim if r["ok"]) / len(gov_shim)) if gov_shim else 0.0,
        }},
        "details": {{
            "executable_bare": exec_bare,
            "governance_bare": gov_bare,
            "governance_shim": gov_shim,
        }},
    }}
    print("\\n===SCBE_GEMMA4_DEMO_REPORT===")
    print(json.dumps(summary, indent=2))
    print("===SCBE_GEMMA4_DEMO_REPORT_END===\\n")
    api = HfApi(token=token)
    result_dataset = str(PACKET["result_dataset"])
    api.create_repo(result_dataset, repo_type="dataset", exist_ok=True, private=False)
    eval_id = str(PACKET["eval_id"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    api.upload_file(
        path_or_fileobj=BytesIO(json.dumps(summary, indent=2).encode("utf-8")),
        path_in_repo=f"gemma4_demo/{{eval_id}}/{{stamp}}/report.json",
        repo_id=result_dataset,
        repo_type="dataset",
    )
    print(json.dumps({{"event": "report_uploaded", "result_dataset": result_dataset,
                       "report_path": f"gemma4_demo/{{eval_id}}/{{stamp}}/report.json"}}))


if __name__ == "__main__":
    main()
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", default=DEFAULT_BASE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--artifact-root", type=Path, default=REPO_ROOT / "artifacts" / "demo_gemma4_jobs")
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--gov-contract", type=Path, default=DEFAULT_GOV_CONTRACT)
    parser.add_argument("--flavor", default="l4x1")
    parser.add_argument("--timeout", default="40m")
    parser.add_argument("--result-dataset", default=DEFAULT_RESULT_DATASET)
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--eval-id", default="")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    if not args.eval_id:
        args.eval_id = args.base_model.split("/")[-1]
    packet = build_packet(args)

    if args.plan_only:
        print(f"Packet: {Path(packet['run_dir']) / 'demo_packet.json'}")
        print(f"Script: {packet['script_path']}")
        return 0

    command = [
        "hf", "jobs", "uv", "run",
        "--flavor", args.flavor,
        "--timeout", args.timeout,
        "--env", "PYTHONIOENCODING=utf-8",
        "--env", "PYTHONUTF8=1",
        "--env", "LANG=C.UTF-8",
        "--env", "LC_ALL=C.UTF-8",
        "--env", "HF_HUB_DISABLE_PROGRESS_BARS=1",
        "--env", "TOKENIZERS_PARALLELISM=false",
        "--secrets", "HF_TOKEN",
        "--detach",
        packet["script_path"],
    ]
    result = subprocess.run(
        command, cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    combined = result.stdout + "\n" + result.stderr
    match = re.search(r"(?:Job ID|ID|job)[^A-Za-z0-9_-]*([A-Za-z0-9_-]{8,})", combined, re.IGNORECASE)
    print(json.dumps({
        "dispatched": result.returncode == 0,
        "job_id": match.group(1) if match else "",
        "stdout": result.stdout[-1000:],
        "stderr": result.stderr[-500:],
        "packet_path": str(Path(packet["run_dir"]) / "demo_packet.json"),
    }, indent=2))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

"""Dispatch the SCBE code-diffusion bake-off as a Hugging Face Job.

Renders a self-contained uv-script (PEP 723 inline deps) that:
  1. Loads the AR baseline (default Qwen/Qwen2.5-Coder-7B-Instruct)
  2. Runs the 12-prompt v6h contract through it
  3. Unloads, loads the diffusion candidate (default apple/DiffuCoder-7B-Instruct)
  4. Runs the same 12 prompts
  5. Scores both with the canonical v6h gate
  6. Uploads JSON / JSONL / Markdown to a PRIVATE HF dataset repo

Use --dispatch to actually fire `hf jobs uv run`. Without that flag, the
script just renders the packet + prints the command.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = REPO_ROOT / "config" / "eval" / "coding_diffusion_bakeoff_v1.json"
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "hf_diffusion_bakeoff_jobs"
ENV_FILE = REPO_ROOT / "config" / "connector_oauth" / ".env.connector.oauth"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_env_file(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


UV_SCRIPT_TEMPLATE = '''# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "torch>=2.4.0",
#   "transformers>=4.46.0",
#   "accelerate>=1.0.0",
#   "sentencepiece>=0.2.0",
#   "huggingface_hub>=0.27.0",
# ]
# ///
"""Self-contained SCBE code-diffusion bake-off (HF Jobs runner).

Auto-rendered by scripts/system/dispatch_diffusion_bakeoff_hf_job.py.
Do not hand-edit; regenerate from source.
"""

from __future__ import annotations

import gc
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from huggingface_hub import HfApi, create_repo
from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer

CONTRACT = {contract_literal}
BASELINE_MODEL = {baseline_literal}
DIFFUSION_MODEL = {diffusion_literal}
RESULTS_REPO = {results_repo_literal}
RESULTS_PRIVATE = {results_private_literal}
MAX_NEW_TOKENS = {max_new_tokens}
DIFFUSION_STEPS = {diffusion_steps}

WORKDIR = Path("/tmp/scbe-diffusion-bakeoff")
WORKDIR.mkdir(parents=True, exist_ok=True)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def gate_score(prompt: dict, response: str) -> dict:
    body_lower = (response or "").lower()
    missing_required = [
        str(t) for t in (prompt.get("required") or []) if str(t).lower() not in body_lower
    ]

    def contains_forbidden(term: str) -> bool:
        needle = str(term).strip().lower()
        if not needle:
            return False
        if re.fullmatch(r"[a-z0-9_ -]+", needle):
            pattern_body = r"\\s+".join(re.escape(part) for part in needle.split())
            pattern = r"(?<![a-z0-9_])" + pattern_body + r"(?![a-z0-9_])"
            return re.search(pattern, body_lower) is not None
        return needle in body_lower

    triggered_forbidden = [
        str(t) for t in (prompt.get("forbidden") or []) if contains_forbidden(t)
    ]
    return {{
        "id": prompt.get("id"),
        "shape": prompt.get("shape", "unknown"),
        "ok": (not missing_required) and (not triggered_forbidden),
        "missing_required": missing_required,
        "triggered_forbidden": triggered_forbidden,
        "response_chars": len(response or ""),
    }}


def hf_token() -> str:
    tok = os.environ.get("HF_TOKEN", "").strip() or os.environ.get(
        "HUGGING_FACE_HUB_TOKEN", ""
    ).strip()
    if not tok:
        raise RuntimeError("HF_TOKEN missing in environment")
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", tok)
    return tok


def free_memory() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def generate_with_ar(model_id: str, prompts: list[dict]) -> list[dict]:
    print(f"[ar] loading {{model_id}}", flush=True)
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tok.pad_token_id is None:
        tok.pad_token_id = tok.eos_token_id
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=dtype, trust_remote_code=True
    )
    model.eval()
    if torch.cuda.is_available():
        model = model.to("cuda")
    out: list[dict] = []
    for i, p in enumerate(prompts):
        text = (p.get("prompt") or "").strip()
        try:
            enc = tok.apply_chat_template(
                [{{"role": "user", "content": text}}],
                return_tensors="pt",
                add_generation_prompt=True,
            )
        except Exception:
            enc = tok(text, return_tensors="pt").input_ids
        if torch.cuda.is_available():
            enc = enc.to("cuda")
        t0 = time.time()
        with torch.inference_mode():
            gen = model.generate(
                enc,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                temperature=1.0,
                pad_token_id=tok.pad_token_id,
            )
        new_tokens = gen[0, enc.shape[1]:]
        response = tok.decode(new_tokens, skip_special_tokens=True)
        elapsed = time.time() - t0
        print(f"[ar] {{i+1}}/{{len(prompts)}} {{p.get('id')}} ({{elapsed:.1f}}s, {{len(response)}} chars)", flush=True)
        out.append({{"label": "ar", "id": p.get("id"), "response": response, "seconds": elapsed}})
    del model, tok
    free_memory()
    return out


def generate_with_diffusion(model_id: str, prompts: list[dict]) -> list[dict]:
    print(f"[diffusion] loading {{model_id}}", flush=True)
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tok.pad_token_id is None:
        tok.pad_token_id = tok.eos_token_id
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    try:
        model = AutoModel.from_pretrained(model_id, torch_dtype=dtype, trust_remote_code=True)
    except Exception:
        # Some diffusion code repos register as causal-LM heads.
        model = AutoModelForCausalLM.from_pretrained(
            model_id, torch_dtype=dtype, trust_remote_code=True
        )
    model.eval()
    if torch.cuda.is_available():
        model = model.to("cuda")
    out: list[dict] = []
    for i, p in enumerate(prompts):
        text = (p.get("prompt") or "").strip()
        try:
            enc = tok.apply_chat_template(
                [{{"role": "user", "content": text}}],
                return_tensors="pt",
                add_generation_prompt=True,
            )
        except Exception:
            enc = tok(text, return_tensors="pt").input_ids
        if torch.cuda.is_available():
            enc = enc.to("cuda")
        gen_kwargs: dict[str, Any] = {{
            "max_new_tokens": MAX_NEW_TOKENS,
            "pad_token_id": tok.pad_token_id,
        }}
        attempt_kwargs = dict(gen_kwargs, num_inference_steps=DIFFUSION_STEPS, do_sample=False)
        t0 = time.time()
        with torch.inference_mode():
            try:
                gen = model.generate(enc, **attempt_kwargs)
            except TypeError:
                gen = model.generate(enc, **gen_kwargs)
        new_tokens = gen[0, enc.shape[1]:] if gen.dim() > 1 else gen
        response = tok.decode(new_tokens, skip_special_tokens=True)
        elapsed = time.time() - t0
        print(f"[diffusion] {{i+1}}/{{len(prompts)}} {{p.get('id')}} ({{elapsed:.1f}}s, {{len(response)}} chars)", flush=True)
        out.append({{"label": "diffusion", "id": p.get("id"), "response": response, "seconds": elapsed}})
    del model, tok
    free_memory()
    return out


def triangulate(reports: list[dict]) -> dict:
    if not reports:
        return {{}}
    labels = [r["label"] for r in reports]
    indexed = {{r["label"]: {{v["id"]: v for v in r["by_prompt"]}} for r in reports}}
    prompt_ids = [v["id"] for v in reports[0]["by_prompt"]]
    by_shape: dict = {{}}
    by_prompt: list[dict] = []
    for pid in prompt_ids:
        verdicts = {{lab: indexed[lab].get(pid) for lab in labels}}
        shape = next((v["shape"] for v in verdicts.values() if v), "unknown")
        bucket = by_shape.setdefault(shape, {{lab: {{"pass": 0, "fail": 0}} for lab in labels}})
        for lab in labels:
            v = verdicts[lab]
            key = "pass" if (v and v["ok"]) else "fail"
            bucket[lab][key] += 1
        winners = [lab for lab in labels if verdicts[lab] and verdicts[lab]["ok"]]
        losers = [lab for lab in labels if verdicts[lab] and not verdicts[lab]["ok"]]
        if not winners:
            cls = "all_fail"
        elif not losers:
            cls = "all_pass"
        else:
            cls = "split"
        by_prompt.append({{
            "id": pid,
            "shape": shape,
            "verdicts": {{lab: (verdicts[lab]["ok"] if verdicts[lab] else None) for lab in labels}},
            "verdict_class": cls,
            "winners": winners,
            "losers": losers,
        }})
    deltas: dict = {{}}
    if "ar" in labels and "diffusion" in labels:
        for shape, counts in by_shape.items():
            deltas[shape] = {{
                "ar_pass": counts["ar"]["pass"],
                "diffusion_pass": counts["diffusion"]["pass"],
                "delta": counts["diffusion"]["pass"] - counts["ar"]["pass"],
            }}
    return {{"by_shape": by_shape, "by_prompt": by_prompt, "shape_delta": deltas}}


def emit_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Code-Diffusion Bake-Off — {{report['contract_id']}}")
    lines.append("")
    lines.append("## Generator pass-rates")
    lines.append("")
    lines.append("| Generator | Model | Pass | Rate |")
    lines.append("|---|---|---|---|")
    for g in report["generators"]:
        lines.append(
            f"| {{g['label']}} | `{{g['model_id']}}` | {{g['n_pass']}}/{{g['n_total']}} | {{g['pass_rate']:.3f}} |"
        )
    lines.append("")
    tri = report.get("triangulation") or {{}}
    if tri.get("shape_delta"):
        lines.append("## Per-shape delta (diffusion - AR)")
        lines.append("")
        lines.append("| Shape | AR pass | Diffusion pass | Delta |")
        lines.append("|---|---|---|---|")
        for shape, row in sorted(
            tri["shape_delta"].items(), key=lambda kv: -kv[1]["delta"]
        ):
            lines.append(
                f"| {{shape}} | {{row['ar_pass']}} | {{row['diffusion_pass']}} | {{row['delta']:+d}} |"
            )
        lines.append("")
    if tri.get("by_prompt"):
        lines.append("## Per-prompt verdict-class")
        lines.append("")
        lines.append("| Prompt | Shape | Class | Winners |")
        lines.append("|---|---|---|---|")
        for row in tri["by_prompt"]:
            winners = ", ".join(row.get("winners") or []) or "—"
            lines.append(
                f"| {{row['id']}} | {{row['shape']}} | {{row['verdict_class']}} | {{winners}} |"
            )
    return "\\n".join(lines) + "\\n"


def push_to_hub(stamp: str, files: list[Path]) -> None:
    token = hf_token()
    api = HfApi(token=token)
    create_repo(RESULTS_REPO, repo_type="dataset", private=RESULTS_PRIVATE, exist_ok=True, token=token)
    for f in files:
        target = f"runs/{{stamp}}/{{f.name}}"
        print(f"[upload] {{f}} -> {{RESULTS_REPO}}/{{target}}", flush=True)
        api.upload_file(
            path_or_fileobj=str(f),
            path_in_repo=target,
            repo_id=RESULTS_REPO,
            repo_type="dataset",
            token=token,
        )


def main() -> None:
    stamp = utc_stamp()
    prompts = list(CONTRACT.get("prompts") or [])
    print(f"[start] {{len(prompts)}} prompts; ar={{BASELINE_MODEL}} diffusion={{DIFFUSION_MODEL}}", flush=True)
    print(f"[gpu] cuda={{torch.cuda.is_available()}}", flush=True)

    reports: list[dict] = []
    raw_responses: list[dict] = []
    errors: list[dict] = []

    for label, model_id, runner in [
        ("ar", BASELINE_MODEL, generate_with_ar),
        ("diffusion", DIFFUSION_MODEL, generate_with_diffusion),
    ]:
        try:
            raws = runner(model_id, prompts)
            verdicts = [gate_score(p, r["response"]) for p, r in zip(prompts, raws)]
            n_pass = sum(1 for v in verdicts if v["ok"])
            reports.append({{
                "label": label,
                "model_id": model_id,
                "n_pass": n_pass,
                "n_total": len(prompts),
                "pass_rate": n_pass / len(prompts) if prompts else 0.0,
                "by_prompt": verdicts,
            }})
            raw_responses.extend(raws)
            print(f"[{{label}}] DONE n_pass={{n_pass}}/{{len(prompts)}}", flush=True)
        except Exception as exc:
            err = {{"label": label, "model_id": model_id, "error": str(exc), "trace": traceback.format_exc()}}
            errors.append(err)
            print(f"[{{label}}] ERROR: {{exc}}", flush=True)
            traceback.print_exc()
            free_memory()

    triangulation = triangulate(reports)
    report = {{
        "schema_version": "scbe_diffusion_bakeoff_report_v1",
        "contract_id": CONTRACT.get("contract_id"),
        "source_contract": CONTRACT.get("source_contract"),
        "stamp": stamp,
        "n_prompts": len(prompts),
        "generators": reports,
        "triangulation": triangulation,
        "errors": errors,
    }}

    json_path = WORKDIR / f"diffusion_bakeoff_{{stamp}}.json"
    raws_path = WORKDIR / f"diffusion_bakeoff_{{stamp}}.responses.jsonl"
    md_path = WORKDIR / f"diffusion_bakeoff_{{stamp}}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with raws_path.open("w", encoding="utf-8") as fh:
        for row in raw_responses:
            fh.write(json.dumps(row) + "\\n")
    md_path.write_text(emit_markdown(report), encoding="utf-8")

    print("[summary]", json.dumps({{
        "n_pass_ar": next((r["n_pass"] for r in reports if r["label"] == "ar"), None),
        "n_pass_diffusion": next((r["n_pass"] for r in reports if r["label"] == "diffusion"), None),
        "errors": len(errors),
    }}), flush=True)

    try:
        push_to_hub(stamp, [json_path, raws_path, md_path])
    except Exception as exc:
        print(f"[upload] FAILED: {{exc}}", flush=True)
        traceback.print_exc()


if __name__ == "__main__":
    main()
'''


def render_uv_script(
    *,
    contract: dict,
    baseline_model: str,
    diffusion_model: str,
    results_repo: str,
    results_private: bool,
    max_new_tokens: int,
    diffusion_steps: int,
) -> str:
    return UV_SCRIPT_TEMPLATE.format(
        contract_literal=repr(contract),
        baseline_literal=repr(baseline_model),
        diffusion_literal=repr(diffusion_model),
        results_repo_literal=repr(results_repo),
        results_private_literal=repr(bool(results_private)),
        max_new_tokens=int(max_new_tokens),
        diffusion_steps=int(diffusion_steps),
    )


def build_packet(args: argparse.Namespace) -> dict:
    _load_env_file()
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    stamp = _utc_stamp()
    run_dir = ARTIFACT_ROOT / stamp
    script_path = run_dir / "run_bakeoff_hf.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_text = render_uv_script(
        contract=contract,
        baseline_model=args.baseline_model,
        diffusion_model=args.diffusion_model,
        results_repo=args.results_repo,
        results_private=not args.results_public,
        max_new_tokens=args.max_new_tokens,
        diffusion_steps=args.diffusion_steps,
    )
    script_path.write_text(script_text, encoding="utf-8")
    command = [
        "hf",
        "jobs",
        "uv",
        "run",
        "--flavor",
        args.flavor,
        "--timeout",
        args.timeout,
        "--env",
        "PYTHONIOENCODING=utf-8",
        "--env",
        "PYTHONUTF8=1",
        "--secrets",
        "HF_TOKEN",
        "--detach",
        str(script_path),
    ]
    packet = {
        "schema_version": "scbe_diffusion_bakeoff_hf_packet_v1",
        "prepared_at_utc": stamp,
        "run_dir": str(run_dir),
        "script_path": str(script_path),
        "baseline_model": args.baseline_model,
        "diffusion_model": args.diffusion_model,
        "results_repo": args.results_repo,
        "results_private": not args.results_public,
        "hf": {
            "flavor": args.flavor,
            "timeout": args.timeout,
            "cli": shutil.which("hf") or "",
            "token_present": bool(os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")),
        },
        "command": command,
        "dispatched": False,
    }
    (run_dir / "job_packet.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
    return packet


def maybe_dispatch(packet: dict, dispatch: bool) -> dict:
    if not dispatch:
        print("[dry] would run:", " ".join(packet["command"]))
        return packet
    print("[dispatch]", " ".join(packet["command"]), flush=True)
    proc = subprocess.run(packet["command"], capture_output=True, text=True)
    packet["dispatch_stdout"] = proc.stdout
    packet["dispatch_stderr"] = proc.stderr
    packet["dispatch_returncode"] = proc.returncode
    packet["dispatched"] = proc.returncode == 0
    if proc.stdout:
        print(proc.stdout, flush=True)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, flush=True)
    Path(packet["run_dir"], "job_packet.json").write_text(
        json.dumps(packet, indent=2), encoding="utf-8"
    )
    return packet


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dispatch SCBE code-diffusion bake-off as HF Job")
    p.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    p.add_argument("--baseline-model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    p.add_argument("--diffusion-model", default="apple/DiffuCoder-7B-Instruct")
    p.add_argument("--results-repo", default="issdandavis/scbe-diffusion-bakeoff-results")
    p.add_argument("--results-public", action="store_true", help="Default is private; pass to make the results repo public.")
    p.add_argument("--flavor", default="l4x1")
    p.add_argument("--timeout", default="1h")
    p.add_argument("--max-new-tokens", type=int, default=320)
    p.add_argument("--diffusion-steps", type=int, default=64)
    p.add_argument("--dispatch", action="store_true", help="Actually run the hf jobs command.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    packet = build_packet(args)
    print("[packet]", json.dumps({k: v for k, v in packet.items() if k != "command"}, indent=2))
    maybe_dispatch(packet, args.dispatch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# /// script
# dependencies = [
#   "torch>=2.5",
#   "transformers>=4.46",
#   "peft>=0.13",
#   "accelerate",
#   "bitsandbytes",
#   "huggingface_hub",
# ]
# ///
"""HF Jobs entry point: multi-seed sampling-mode audit of aligned-foundations.

The inline gate runs greedy decode (do_sample=False) on the 257-row
``drill_langues_full_holdout``, producing a deterministic 0.891 pass rate
that has been bit-identical across two runs (2026-04-30 and 2026-05-06).
That single point estimate has zero observed variance at greedy but
hides the model's behavior under sampling.

This audit re-runs the holdout (or a configurable subset) under sampling
decode at multiple (seed, temperature) contexts and reports:

  - strict pass rate + 95% Wilson CI
  - per-seed and per-temperature distribution
  - seed-lucky spread (max - min single-seed pass rate)
  - best-of-N capability per record (does the record pass in *any*
    decode context?)
  - failure clustering by (map, kind, tongue)

Two practical modes:

  mode=full        — run the full 257-row holdout
  mode=failing     — only run the 28 records that fail under greedy
                     (capability probe: do these records EVER pass?)

Reads from environment:
  HF_TOKEN                              — required
  SCBE_AUDIT_BASE_MODEL                 — base (default Qwen/Qwen2.5-7B-Instruct)
  SCBE_AUDIT_ADAPTER_REPO               — adapter repo
  SCBE_AUDIT_HOLDOUT_REPO               — dataset repo holding the holdout JSONL
  SCBE_AUDIT_HOLDOUT_PATH               — path inside dataset repo
  SCBE_AUDIT_CROSS_LANE_PATH            — path to cross-lane module in dataset repo
  SCBE_AUDIT_MODE                       — "full" or "failing" (default full)
  SCBE_AUDIT_HOLDOUT_LIMIT              — first N rows after mode filter (0 = all)
  SCBE_AUDIT_SEEDS                      — default 0,1,2,3,4
  SCBE_AUDIT_TEMPERATURES               — default 0.0,0.4,0.8
  SCBE_AUDIT_MAX_NEW_TOKENS             — default 320
  SCBE_AUDIT_RESULT_REPO                — default issdandavis/scbe-eval-results

Output: pushes a JSON report to ``SCBE_AUDIT_RESULT_REPO`` named
``aligned_foundations_audit_<utc>.json``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _idempotency_key(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _wilson_interval(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    p = passed / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (p + z2 / (2 * total)) / denom
    half = (z * math.sqrt(p * (1 - p) / total + z2 / (4 * total * total))) / denom
    return (round(max(0.0, center - half), 4), round(min(1.0, center + half), 4))


def _seed_torch(seed: int) -> None:
    import random

    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _load_cross_lane_module(local_path: str):
    spec = importlib.util.spec_from_file_location("aligned_foundations_cross_lane", local_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load cross-lane module from {local_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _generate_one(
    model,
    tokenizer,
    user_prompt: str,
    system_prompt: str | None,
    seed: int,
    temperature: float,
    max_new_tokens: int,
) -> str:
    import torch

    _seed_torch(seed)

    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    msgs.append({"role": "user", "content": user_prompt})

    chat_text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(chat_text, return_tensors="pt").to(model.device)
    n_in = inputs["input_ids"].shape[1]

    do_sample = temperature > 0.0
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            temperature=max(temperature, 1e-5),
            top_p=0.95 if do_sample else 1.0,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(out[0][n_in:], skip_special_tokens=True)


def _aggregate(trials: list[dict]) -> dict:
    n = len(trials)
    passed = sum(1 for t in trials if t["passed"])
    pass_rate = passed / n if n else 0.0
    ci_low, ci_high = _wilson_interval(passed, n)

    per_seed = defaultdict(list)
    per_temp = defaultdict(list)
    per_record = defaultdict(list)
    per_map_kind = defaultdict(list)
    for t in trials:
        per_seed[t["seed"]].append(t)
        per_temp[t["temperature"]].append(t)
        per_record[t["record_id"]].append(t)
        per_map_kind[(t["map"], t["kind"])].append(t)

    def _rate(rows):
        if not rows:
            return {"pass_rate": 0.0, "n": 0, "passed": 0}
        return {
            "pass_rate": round(sum(1 for r in rows if r["passed"]) / len(rows), 4),
            "n": len(rows),
            "passed": sum(1 for r in rows if r["passed"]),
        }

    seed_dist = sorted(_rate(rows)["pass_rate"] for rows in per_seed.values())
    spread = (max(seed_dist) - min(seed_dist)) if seed_dist else 0.0

    bon_passes = sum(1 for rows in per_record.values() if any(r["passed"] for r in rows))
    n_records = len(per_record)

    fail_clusters = []
    for (map_name, kind), rows in sorted(per_map_kind.items()):
        info = _rate(rows)
        if info["pass_rate"] < 1.0:
            fail_clusters.append(
                {
                    "map": map_name,
                    "kind": kind,
                    "pass_rate": info["pass_rate"],
                    "passed": info["passed"],
                    "n": info["n"],
                }
            )
    fail_clusters.sort(key=lambda x: (x["pass_rate"], -x["n"]))

    return {
        "overall": {
            "n_trials": n,
            "passed_count": passed,
            "pass_rate": round(pass_rate, 4),
            "wilson_95ci_low": ci_low,
            "wilson_95ci_high": ci_high,
        },
        "per_seed": {str(s): _rate(rows) for s, rows in sorted(per_seed.items())},
        "per_temperature": {f"{t:.2f}": _rate(rows) for t, rows in sorted(per_temp.items())},
        "seed_lucky_risk": {
            "min": min(seed_dist) if seed_dist else 0.0,
            "max": max(seed_dist) if seed_dist else 0.0,
            "spread": round(spread, 4),
            "single_seed_distribution": [round(x, 4) for x in seed_dist],
        },
        "best_of_n": {
            "n_records": n_records,
            "n_decode_contexts": (
                len(seed_dist) * len({t["temperature"] for t in trials})
            ),
            "record_pass_rate": round(bon_passes / max(1, n_records), 4),
            "all_records_any_pass": bon_passes == n_records,
        },
        "fail_clusters": fail_clusters,
    }


def _push_to_hub(payload: dict, target_repo: str, file_name: str) -> str:
    from huggingface_hub import HfApi

    api = HfApi()
    try:
        api.create_repo(repo_id=target_repo, repo_type="dataset", private=True, exist_ok=True)
    except Exception:
        pass
    body = json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8")
    api.upload_file(
        path_or_fileobj=body,
        path_in_repo=file_name,
        repo_id=target_repo,
        repo_type="dataset",
        commit_message=f"audit: aligned-foundations multi-seed {file_name}",
    )
    return f"https://huggingface.co/datasets/{target_repo}/blob/main/{file_name}"


def _download_from_dataset(repo: str, repo_path: str) -> str:
    from huggingface_hub import hf_hub_download

    return hf_hub_download(repo_id=repo, filename=repo_path, repo_type="dataset")


def main() -> int:
    base_model_id = os.environ.get("SCBE_AUDIT_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    adapter_repo = os.environ.get(
        "SCBE_AUDIT_ADAPTER_REPO", "issdandavis/scbe-aligned-foundations-qwen-primary"
    )
    holdout_repo = os.environ.get(
        "SCBE_AUDIT_HOLDOUT_REPO", "issdandavis/scbe-aligned-foundations-sft"
    )
    holdout_path = os.environ.get(
        "SCBE_AUDIT_HOLDOUT_PATH",
        "training-data/sft/drill_langues_full_holdout.sft.jsonl",
    )
    cross_lane_path = os.environ.get(
        "SCBE_AUDIT_CROSS_LANE_PATH", "aligned_foundations_cross_lane.py"
    )
    mode = os.environ.get("SCBE_AUDIT_MODE", "full").lower()
    holdout_limit = int(os.environ.get("SCBE_AUDIT_HOLDOUT_LIMIT", "0"))
    seeds = [int(s) for s in os.environ.get("SCBE_AUDIT_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    temperatures = [
        float(t)
        for t in os.environ.get("SCBE_AUDIT_TEMPERATURES", "0.0,0.4,0.8").split(",")
        if t.strip()
    ]
    max_new_tokens = int(os.environ.get("SCBE_AUDIT_MAX_NEW_TOKENS", "320"))
    target_repo = os.environ.get("SCBE_AUDIT_RESULT_REPO", "issdandavis/scbe-eval-results")

    print(f"[audit] base_model={base_model_id}")
    print(f"[audit] adapter_repo={adapter_repo}")
    print(f"[audit] holdout={holdout_repo}/{holdout_path}")
    print(f"[audit] mode={mode}  holdout_limit={holdout_limit}")
    print(f"[audit] seeds={seeds}  temperatures={temperatures}")
    print(f"[audit] max_new_tokens={max_new_tokens}")

    print("[audit] downloading cross-lane module + holdout from dataset repo...")
    cross_lane_local = _download_from_dataset(holdout_repo, cross_lane_path)
    holdout_local = _download_from_dataset(holdout_repo, holdout_path)
    cross_lane = _load_cross_lane_module(cross_lane_local)

    records = []
    with open(holdout_local, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"[audit] loaded {len(records)} holdout records")

    print("[audit] loading model + tokenizer + adapter...")
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t_load = time.time()
    tokenizer = AutoTokenizer.from_pretrained(base_model_id, trust_remote_code=True)
    base = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(base, adapter_repo)
    model.eval()
    print(f"[audit] model+adapter loaded in {time.time() - t_load:.1f}s")

    if mode == "failing":
        print("[audit] mode=failing: running greedy filter pass to identify failing records...")
        failing = []
        for i, rec in enumerate(records):
            meta = rec.get("meta") or {}
            user = cross_lane.user_prompt_text(rec)
            system = cross_lane.system_prompt_text(rec)
            reference = cross_lane.reference_assistant_text(rec)
            response = _generate_one(model, tokenizer, user, system, 0, 0.0, max_new_tokens)
            check = cross_lane.score_packet_compliance(
                str(meta.get("map", "")), str(meta.get("kind", "")), response, reference
            )
            if not check["ok"]:
                failing.append(rec)
            if (i + 1) % 25 == 0:
                print(f"[audit] greedy filter {i+1}/{len(records)}  failing_so_far={len(failing)}")
        print(f"[audit] failing under greedy: {len(failing)}/{len(records)}")
        records = failing

    if holdout_limit > 0:
        records = records[:holdout_limit]
        print(f"[audit] truncated to first {len(records)} records")

    n_total = len(records) * len(seeds) * len(temperatures)
    print(f"[audit] starting sweep: {len(records)} records × {len(seeds)} seeds × {len(temperatures)} temps = {n_total} trials")

    trials: list[dict] = []
    n_done = 0
    t_audit_start = time.time()

    for rec in records:
        meta = rec.get("meta") or {}
        record_id = f"{meta.get('map','?')}|{meta.get('kind','?')}|{meta.get('tongue','?')}|{meta.get('value','?')}"
        user = cross_lane.user_prompt_text(rec)
        system = cross_lane.system_prompt_text(rec)
        reference = cross_lane.reference_assistant_text(rec)

        for seed in seeds:
            for temperature in temperatures:
                response = _generate_one(model, tokenizer, user, system, seed, temperature, max_new_tokens)
                check = cross_lane.score_packet_compliance(
                    str(meta.get("map", "")), str(meta.get("kind", "")), response, reference
                )
                trials.append(
                    {
                        "record_id": record_id,
                        "map": str(meta.get("map", "")),
                        "kind": str(meta.get("kind", "")),
                        "tongue": str(meta.get("tongue", "")),
                        "value": str(meta.get("value", "")),
                        "seed": int(seed),
                        "temperature": float(temperature),
                        "passed": bool(check["ok"]),
                        "completion_excerpt": response[:300],
                    }
                )
                n_done += 1
                if n_done % 25 == 0 or n_done == n_total:
                    elapsed = time.time() - t_audit_start
                    eta = elapsed * (n_total - n_done) / max(1, n_done)
                    print(
                        f"[audit] {n_done}/{n_total} ({100*n_done/n_total:.1f}%) "
                        f"elapsed={elapsed:.1f}s eta={eta:.1f}s"
                    )

    aggregate = _aggregate(trials)

    payload_for_key = {
        "schema_version": "scbe_aligned_foundations_audit_v1",
        "base_model": base_model_id,
        "adapter_repo": adapter_repo,
        "holdout": f"{holdout_repo}/{holdout_path}",
        "mode": mode,
        "holdout_limit": holdout_limit,
        "seeds": seeds,
        "temperatures": temperatures,
    }
    report = {
        **payload_for_key,
        "idempotency_key": _idempotency_key(payload_for_key),
        "n_records": len(records),
        "max_new_tokens": max_new_tokens,
        "trials": trials,
        "aggregate": aggregate,
        "elapsed_s": round(time.time() - t_audit_start, 1),
        "completed_at_utc": _utc_stamp(),
    }

    overall = aggregate["overall"]
    risk = aggregate["seed_lucky_risk"]
    bon = aggregate["best_of_n"]
    print()
    print("=== aligned-foundations multi-seed audit ===")
    print(f"adapter      : {adapter_repo}")
    print(f"mode         : {mode}  records={len(records)}")
    print(
        f"strict       : {overall['pass_rate']:.3f}  CI [{overall['wilson_95ci_low']:.3f}, "
        f"{overall['wilson_95ci_high']:.3f}]  ({overall['passed_count']}/{overall['n_trials']})"
    )
    print(
        f"seed-lucky   : spread={risk['spread']:.3f}  dist={risk['single_seed_distribution']}"
    )
    print(
        f"best-of-N    : record_pass_rate={bon['record_pass_rate']:.3f}  "
        f"all_records_any_pass={bon['all_records_any_pass']}"
    )
    print()
    print("top fail clusters (map, kind, pass_rate, passed/n):")
    for fc in aggregate["fail_clusters"][:15]:
        print(f"  {fc['map']:<28} {fc['kind']:<22} {fc['pass_rate']:.2f}  ({fc['passed']}/{fc['n']})")
    print()

    file_name = f"aligned_foundations_audit_{mode}_{_utc_stamp()}.json"
    try:
        url = _push_to_hub(report, target_repo, file_name)
        print(f"[audit] uploaded to {url}")
    except Exception as exc:
        print(f"[audit] upload failed: {exc}")
        print("=== full report (fallback) ===")
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Aligned-foundations cross-lane concept-preservation gate scorer.

Implements the canonical promotion gate for the ``aligned_foundations`` bucket
(per ``config/model_training/scbe_dataset_regularization_v1.json``):

    eval_gate    = "cross-lane concept preservation and packet compliance"
    promotion    = "Promote only if a concept survives representation transfer
                    without collapsing lane boundaries."
    merge_strategy = paired_multirepresentation_records

Pipeline:

  1. Load base model + optional LoRA adapter.
  2. For each record in the holdout JSONL, generate the assistant turn under
     the canonical chat template (system + user -> assistant).
  3. Group responses + canonical references by (map, kind, value) concept.
  4. For each concept, run ``aligned_foundations_concept_verdict``:
       - per-tongue ``score_packet_compliance`` (does each output match the
         canonical envelope for its kind),
       - cross-tongue ``score_cross_lane_invariance`` for multi-tongue concepts
         (do same-concept outputs share the structural envelope across tongues).
  5. Aggregate to per-record packet-compliance rate + per-multi-tongue-concept
     invariance rate + a composite "promote / hold" verdict.

Decision rule (default thresholds, configurable via flags):

    pass_rate_packet_compliance >= 0.80 AND
    pass_rate_concept_invariance >= 0.80 (over multi-tongue concepts only)

Output: ``artifacts/aligned_foundations_cross_lane/<tag>_aligned_foundations_cross_lane.json``

This is the file-only design + tests scorer. End-to-end runs against the
Qwen2.5-7B base + LoRA adapter need GPU (Colab/A10/L4); CPU is fine for
verifying argparse + import path.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.governance.aligned_foundations_cross_lane import (  # noqa: E402
    aligned_foundations_concept_verdict,
    group_records_by_concept,
    reference_assistant_text,
    score_packet_compliance,
    system_prompt_text,
    user_prompt_text,
)


DEFAULT_HOLDOUT = "training-data/sft/drill_langues_full_holdout.sft.jsonl"
DEFAULT_BASE = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_OUT = "artifacts/aligned_foundations_cross_lane"


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip())
    return re.sub(r"-+", "-", slug).strip("-.") or "adapter"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _generate_response(
    model,
    tokenizer,
    record: Dict[str, Any],
    max_new_tokens: int,
) -> str:
    """Generate the assistant turn for a holdout record under its own template."""
    sys_text = system_prompt_text(record)
    user_text = user_prompt_text(record)
    msgs: List[Dict[str, str]] = []
    if sys_text:
        msgs.append({"role": "system", "content": sys_text})
    msgs.append({"role": "user", "content": user_text})
    text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    n_in = inputs["input_ids"].shape[1]
    out = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        temperature=1.0,
        pad_token_id=tokenizer.eos_token_id,
    )
    return tokenizer.decode(out[0][n_in:], skip_special_tokens=True)


def _build_per_record_entry(
    record: Dict[str, Any],
    response: str,
) -> Dict[str, Any]:
    meta = record.get("meta") or {}
    map_name = str(meta.get("map", ""))
    kind = str(meta.get("kind", ""))
    tongue = str(meta.get("tongue", ""))
    value = str(meta.get("value", ""))
    reference = reference_assistant_text(record)
    diag = score_packet_compliance(map_name, kind, response, reference)
    return {
        "meta": {"map": map_name, "kind": kind, "tongue": tongue, "value": value},
        "ok": diag["ok"],
        "error": diag.get("error"),
        "diffs": diag.get("diffs"),
        "actual_signature": diag.get("actual_signature"),
        "expected_signature": diag.get("expected_signature"),
        "response": response[:1500],
        "reference": reference[:1500],
    }


def _aggregate_concept_verdicts(
    records_with_responses: List[tuple],
) -> List[Dict[str, Any]]:
    """Group by (map, kind, value) and produce a verdict per concept group."""
    by_concept: Dict[tuple, List[tuple]] = {}
    for rec, resp in records_with_responses:
        meta = rec.get("meta") or {}
        key = (str(meta.get("map", "")), str(meta.get("kind", "")), str(meta.get("value", "")))
        by_concept.setdefault(key, []).append((rec, resp))

    out: List[Dict[str, Any]] = []
    for (map_name, kind, value), pairs in sorted(by_concept.items()):
        per_tongue_responses: Dict[str, str] = {}
        per_tongue_references: Dict[str, str] = {}
        for rec, resp in pairs:
            meta = rec.get("meta") or {}
            tongue = str(meta.get("tongue", ""))
            per_tongue_responses[tongue] = resp
            per_tongue_references[tongue] = reference_assistant_text(rec)
        verdict = aligned_foundations_concept_verdict(
            map_name,
            kind,
            value,
            per_tongue_responses,
            per_tongue_references,
        )
        out.append(verdict)
    return out


def _format_summary(
    n_records: int,
    n_compliant: int,
    n_concepts: int,
    n_multi_tongue: int,
    n_invariant: int,
    n_unmapped: int,
) -> Dict[str, Any]:
    pass_rate_packet = (n_compliant / n_records) if n_records else 0.0
    pass_rate_invariance = (n_invariant / n_multi_tongue) if n_multi_tongue else 1.0
    return {
        "n_records": n_records,
        "n_compliant": n_compliant,
        "pass_rate_packet_compliance": pass_rate_packet,
        "n_concepts": n_concepts,
        "n_multi_tongue_concepts": n_multi_tongue,
        "n_invariant_multi_tongue_concepts": n_invariant,
        "pass_rate_concept_invariance": pass_rate_invariance,
        "n_unmapped_kinds_seen": n_unmapped,
    }


def _decide(
    summary: Dict[str, Any],
    min_packet_rate: float,
    min_invariance_rate: float,
) -> bool:
    if summary["n_unmapped_kinds_seen"] > 0:
        return False
    return (
        summary["pass_rate_packet_compliance"] >= min_packet_rate
        and summary["pass_rate_concept_invariance"] >= min_invariance_rate
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument(
        "--adapter",
        default=None,
        help="Optional LoRA adapter (default: base only baseline)",
    )
    ap.add_argument("--holdout", default=DEFAULT_HOLDOUT)
    ap.add_argument(
        "--max-new-tokens",
        type=int,
        default=320,
        help="Max new tokens per generation",
    )
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument(
        "--tag",
        default="base_no_adapter",
        help="Tag for the output report filename",
    )
    ap.add_argument(
        "--min-packet-rate",
        type=float,
        default=0.80,
        help="Packet-compliance pass rate threshold for promote verdict",
    )
    ap.add_argument(
        "--min-invariance-rate",
        type=float,
        default=0.80,
        help="Concept-invariance pass rate threshold for promote verdict",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional cap on number of holdout records (0 = all)",
    )
    args = ap.parse_args()

    holdout_path = (PROJECT_ROOT / args.holdout).resolve()
    if not holdout_path.exists():
        print(f"[aligned-foundations] holdout not found: {holdout_path}", flush=True)
        return 2
    rows = _load_jsonl(holdout_path)
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    print(f"[aligned-foundations] base: {args.base}", flush=True)
    print(f"[aligned-foundations] adapter: {args.adapter or '(none)'}", flush=True)
    print(f"[aligned-foundations] holdout: {holdout_path}", flush=True)
    print(f"[aligned-foundations] records: {len(rows)}", flush=True)
    print(f"[aligned-foundations] tag: {args.tag}", flush=True)

    import torch  # noqa: E402
    from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=dtype, trust_remote_code=True)
    if args.adapter:
        from peft import PeftModel  # noqa: E402

        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    if torch.cuda.is_available():
        model = model.to("cuda")

    per_record_results: List[Dict[str, Any]] = []
    records_with_responses: List[tuple] = []
    n_compliant = 0
    n_unmapped = 0
    unmapped_kinds: Counter = Counter()
    t0 = time.time()
    for i, rec in enumerate(rows, 1):
        try:
            with torch.no_grad():
                response = _generate_response(model, tokenizer, rec, args.max_new_tokens)
        except Exception as exc:  # noqa: BLE001
            meta = rec.get("meta") or {}
            entry = {
                "meta": {
                    "map": str(meta.get("map", "")),
                    "kind": str(meta.get("kind", "")),
                    "tongue": str(meta.get("tongue", "")),
                    "value": str(meta.get("value", "")),
                },
                "ok": False,
                "error": str(exc),
                "response": "",
                "reference": reference_assistant_text(rec)[:1500],
            }
            per_record_results.append(entry)
            records_with_responses.append((rec, ""))
            elapsed = time.time() - t0
            print(
                f"[aligned-foundations] {i}/{len(rows)} ERROR meta={entry['meta']} " f"elapsed={elapsed:.1f}s",
                flush=True,
            )
            continue
        entry = _build_per_record_entry(rec, response)
        per_record_results.append(entry)
        records_with_responses.append((rec, response))
        if entry.get("error") == "not_implemented":
            n_unmapped += 1
            unmapped_kinds[(entry["meta"]["map"], entry["meta"]["kind"])] += 1
        elif entry["ok"]:
            n_compliant += 1
        elapsed = time.time() - t0
        print(
            f"[aligned-foundations] {i}/{len(rows)} ok={entry['ok']} " f"meta={entry['meta']} elapsed={elapsed:.1f}s",
            flush=True,
        )

    concept_verdicts = _aggregate_concept_verdicts(records_with_responses)
    n_concepts = len(concept_verdicts)
    multi_tongue = [c for c in concept_verdicts if c.get("n_tongues", 0) >= 2 and "error" not in c]
    n_multi_tongue = len(multi_tongue)
    n_invariant = sum(1 for c in multi_tongue if c.get("invariance_ok", False))

    summary = _format_summary(
        n_records=len(per_record_results),
        n_compliant=n_compliant,
        n_concepts=n_concepts,
        n_multi_tongue=n_multi_tongue,
        n_invariant=n_invariant,
        n_unmapped=n_unmapped,
    )
    overall_pass = _decide(summary, args.min_packet_rate, args.min_invariance_rate)

    report = {
        "schema": "scbe_aligned_foundations_cross_lane_report_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "base_model": args.base,
        "adapter": args.adapter,
        "holdout": str(holdout_path),
        "tag": args.tag,
        "thresholds": {
            "min_packet_rate": args.min_packet_rate,
            "min_invariance_rate": args.min_invariance_rate,
        },
        "summary": summary,
        "unmapped_kinds": [{"map": k[0], "kind": k[1], "n": n} for k, n in unmapped_kinds.most_common()],
        "overall_pass": overall_pass,
        "concept_verdicts": concept_verdicts,
        "per_record_results": per_record_results,
    }

    out_dir = (PROJECT_ROOT / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _safe_slug(args.tag)
    out_path = out_dir / f"{slug}_aligned_foundations_cross_lane.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[aligned-foundations] wrote {out_path}", flush=True)
    print(
        f"[aligned-foundations] packet_pass={summary['pass_rate_packet_compliance']:.3f} "
        f"(>= {args.min_packet_rate}) "
        f"invariance_pass={summary['pass_rate_concept_invariance']:.3f} "
        f"(>= {args.min_invariance_rate}) "
        f"unmapped={n_unmapped} overall_pass={overall_pass}",
        flush=True,
    )
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

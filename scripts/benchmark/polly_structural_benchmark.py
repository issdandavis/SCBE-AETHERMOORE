from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.eval.drill_map_eval import load_drill_rows, load_model, split_rows
from scripts.eval.drill_structure_preflight import validate_row

CONCEPT_RE = re.compile(r"\bconcept=([^\s]+)")
_TARGET_TOKEN_RE = re.compile(r"[A-Za-z0-9_]{3,}")

CORE_STAGES = ("atom_seed", "braid_helix", "causal_transform", "route_governance")

TONGUE_DISPLAY = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}


def _target_tokens(target: str) -> list[str]:
    return [tok.lower() for tok in _TARGET_TOKEN_RE.findall(target)]


def _resolve_effective_split(data_path: str | Path, split: str) -> str:
    """Avoid re-hashing files that are already materialized as holdout subsets."""
    if split == "all":
        return split

    path = Path(data_path)
    stem = path.stem.lower()
    name = path.name.lower()
    if "holdout_raw" in stem or "holdout_raw" in name:
        return "all"
    return split


@dataclass
class StructuralBenchmarkCase:
    case_id: str
    stage: str
    map_name: str
    kind: str
    tongue: str
    concept: str
    prompt: str
    target: str
    full_text: str


@dataclass
class StructuralBenchmarkRecord:
    case_id: str
    stage: str
    map_name: str
    kind: str
    tongue: str
    concept: str
    prompt: str
    target: str
    generated: str
    exact_match: bool
    validator_pass: bool
    errors: list[str]
    pass_case: bool


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def _concept_from_row(row: dict) -> str:
    value = str(row.get("value", "")).strip()
    if row.get("map") == "atomic_semantic" and value:
        return value
    if row.get("map") == "cross_braid_code" and row.get("kind") in {"anchor_code", "witness_code"} and value:
        return value
    match = CONCEPT_RE.search(str(row.get("text", "")))
    if match:
        return match.group(1)
    if value:
        return value
    return "unknown"


def _make_case(
    row: dict,
    *,
    stage: str,
    prompt: str,
    target: str,
    concept: str | None = None,
    skip_prompt_check: bool = False,
) -> StructuralBenchmarkCase | None:
    prompt = str(prompt)
    target = str(target)
    full_text = str(row.get("text", ""))
    if not prompt or not target:
        return None
    if not skip_prompt_check and prompt not in full_text:
        return None
    return StructuralBenchmarkCase(
        case_id=f"{row.get('map')}:{row.get('kind')}:{row.get('tongue')}:{concept or _concept_from_row(row)}",
        stage=stage,
        map_name=str(row.get("map", "")),
        kind=str(row.get("kind", "")),
        tongue=str(row.get("tongue", "")),
        concept=concept or _concept_from_row(row),
        prompt=prompt,
        target=target,
        full_text=full_text,
    )


def build_structural_benchmark_cases(
    rows: Iterable[dict],
    *,
    max_per_stage: int = 24,
) -> list[StructuralBenchmarkCase]:
    per_stage: dict[str, list[StructuralBenchmarkCase]] = defaultdict(list)

    for row in rows:
        map_name = row.get("map")
        kind = row.get("kind")
        text = str(row.get("text", ""))
        case: StructuralBenchmarkCase | None = None

        if map_name == "transport_atomic" and kind in {"reaction_predict", "reaction_stability"}:
            case = _make_case(
                row,
                stage="causal_transform",
                prompt=str(row.get("prefix", "")),
                target=str(row.get("target", "")),
            )
        elif map_name == "atomic_semantic" and kind == "state" and "trust=" in text:
            prefix, target = text.rsplit("trust=", 1)
            case = _make_case(
                row,
                stage="atom_seed",
                prompt=f"{prefix}trust=",
                target=target,
            )
        elif map_name == "cross_braid_code" and kind in {"anchor_code", "witness_code"} and "\n" in text:
            _, remainder = text.split("\n", 1)
            tongue_code = str(row.get("tongue", "")).strip()
            display = TONGUE_DISPLAY.get(tongue_code, tongue_code or "unknown")
            concept = _concept_from_row(row)
            synth_prompt = f"[{display}]\nconcept={concept}\n"
            case = _make_case(
                row,
                stage="braid_helix",
                prompt=synth_prompt,
                target=remainder,
                concept=concept,
                skip_prompt_check=True,
            )
        elif map_name == "convergence_action" and kind == "packet" and "transport=" in text:
            prefix, target = text.split("transport=", 1)
            case = _make_case(
                row,
                stage="causal_transform",
                prompt=f"{prefix}transport=",
                target=target,
            )
        elif map_name == "cartography_state" and kind == "route" and "gear=" in text:
            prefix, target = text.split("gear=", 1)
            case = _make_case(
                row,
                stage="route_governance",
                prompt=f"{prefix}gear=",
                target=target,
            )

        if case is None:
            continue
        if len(per_stage[case.stage]) < max_per_stage:
            per_stage[case.stage].append(case)

    cases: list[StructuralBenchmarkCase] = []
    for stage in CORE_STAGES:
        cases.extend(per_stage.get(stage, []))
    return cases


def _default_generator(tokenizer, model, *, base_max_new_tokens: int = 96) -> Callable[[str, str], str]:
    import torch

    device = next(model.parameters()).device

    def _coerce_model_inputs(model_inputs: Any) -> tuple[Any, Any]:
        if isinstance(model_inputs, torch.Tensor):
            return model_inputs.to(device), None

        if hasattr(model_inputs, "to"):
            model_inputs = model_inputs.to(device)

        if hasattr(model_inputs, "get"):
            input_ids = model_inputs.get("input_ids")
            attention_mask = model_inputs.get("attention_mask")
        else:
            input_ids = model_inputs["input_ids"]
            attention_mask = model_inputs["attention_mask"] if "attention_mask" in model_inputs else None

        if input_ids is None:
            raise TypeError("tokenizer output missing input_ids")
        if hasattr(input_ids, "to"):
            input_ids = input_ids.to(device)
        if attention_mask is not None and hasattr(attention_mask, "to"):
            attention_mask = attention_mask.to(device)
        return input_ids, attention_mask

    def _generate(prompt: str, target: str) -> str:
        target_ids = tokenizer(target, add_special_tokens=False)["input_ids"]
        max_new_tokens = max(8, min(base_max_new_tokens, len(target_ids) + 12))

        if getattr(tokenizer, "chat_template", None):
            model_inputs = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
            )
            input_ids, attention_mask = _coerce_model_inputs(model_inputs)
        else:
            encoded = tokenizer(prompt, return_tensors="pt")
            input_ids, attention_mask = _coerce_model_inputs(encoded)

        with torch.no_grad():
            outputs = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                do_sample=False,
                max_new_tokens=max_new_tokens,
                pad_token_id=tokenizer.pad_token_id,
            )

        generated_ids = outputs[0][input_ids.shape[1] :]
        return tokenizer.decode(generated_ids, skip_special_tokens=True)

    return _generate


def evaluate_case(
    case: StructuralBenchmarkCase,
    generator: Callable[[str, str], str],
) -> StructuralBenchmarkRecord:
    generated = generator(case.prompt, case.target)
    target_norm = _normalize_text(case.target)
    generated_norm = _normalize_text(generated)
    exact_match = generated_norm.startswith(target_norm)

    errors: list[str] = []
    if not generated_norm:
        errors.append("empty_generated_output")
    else:
        target_tokens = _target_tokens(target_norm)
        if target_tokens:
            generated_lower = generated_norm.lower()
            if not any(tok in generated_lower for tok in target_tokens):
                errors.append("no_target_tokens_present")

    candidate_text = case.prompt + generated_norm
    errors.extend(
        validate_row(
            {
                "map": case.map_name,
                "kind": case.kind,
                "tongue": case.tongue,
                "text": candidate_text,
            }
        )
    )
    validator_pass = not errors

    return StructuralBenchmarkRecord(
        case_id=case.case_id,
        stage=case.stage,
        map_name=case.map_name,
        kind=case.kind,
        tongue=case.tongue,
        concept=case.concept,
        prompt=case.prompt,
        target=case.target,
        generated=generated,
        exact_match=exact_match,
        validator_pass=validator_pass,
        errors=errors,
        pass_case=exact_match and validator_pass,
    )


def summarize_records(records: Iterable[StructuralBenchmarkRecord]) -> dict[str, Any]:
    records = list(records)
    by_stage: dict[str, list[StructuralBenchmarkRecord]] = defaultdict(list)
    by_map: dict[str, list[StructuralBenchmarkRecord]] = defaultdict(list)
    by_tongue: dict[str, list[StructuralBenchmarkRecord]] = defaultdict(list)
    by_concept: dict[str, dict[str, StructuralBenchmarkRecord]] = defaultdict(dict)

    for record in records:
        by_stage[record.stage].append(record)
        by_map[record.map_name].append(record)
        by_tongue[record.tongue].append(record)
        by_concept[f"{record.concept}:{record.tongue}"][record.stage] = record

    def _pack(items: dict[str, list[StructuralBenchmarkRecord]]) -> dict[str, dict[str, Any]]:
        packed: dict[str, dict[str, Any]] = {}
        for key, values in sorted(items.items()):
            total = len(values)
            exact = sum(1 for item in values if item.exact_match)
            validated = sum(1 for item in values if item.validator_pass)
            passed = sum(1 for item in values if item.pass_case)
            packed[key] = {
                "count": total,
                "exact_match_rate": exact / total if total else 0.0,
                "validator_pass_rate": validated / total if total else 0.0,
                "pass_rate": passed / total if total else 0.0,
            }
        return packed

    trajectory_total = 0
    trajectory_full_stage = 0
    trajectory_pass = 0
    failed_trajectories: dict[str, dict[str, Any]] = {}
    for key, stage_records in sorted(by_concept.items()):
        if not all(stage in stage_records for stage in CORE_STAGES):
            continue
        trajectory_total += 1
        trajectory_full_stage += 1
        stage_passes = {stage: stage_records[stage].pass_case for stage in CORE_STAGES}
        if all(stage_passes.values()):
            trajectory_pass += 1
        else:
            failed_trajectories[key] = stage_passes

    total = len(records)
    passed = sum(1 for record in records if record.pass_case)
    exact = sum(1 for record in records if record.exact_match)
    validated = sum(1 for record in records if record.validator_pass)

    return {
        "summary": {
            "total_cases": total,
            "exact_match_rate": exact / total if total else 0.0,
            "validator_pass_rate": validated / total if total else 0.0,
            "pass_rate": passed / total if total else 0.0,
        },
        "by_stage": _pack(by_stage),
        "by_map": _pack(by_map),
        "by_tongue": _pack(by_tongue),
        "trajectory_bundles": {
            "count": trajectory_total,
            "full_stage_count": trajectory_full_stage,
            "pass_rate": trajectory_pass / trajectory_total if trajectory_total else 0.0,
            "failed_examples": failed_trajectories,
        },
    }


class StubBenchmarkModel:
    def __init__(self, case_map: dict[str, str] | None = None):
        self.case_map = case_map or {}

    def generate(self, prompt: str, target: str) -> str:
        return self.case_map.get(prompt, target)


def run_structural_benchmark(
    *,
    data_path: str,
    split: str = "holdout",
    holdout_mod: int = 10,
    holdout_bucket: int = 0,
    model_source: str | None = None,
    device: str = "cuda",
    max_per_stage: int = 24,
    generator: Callable[[str, str], str] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    effective_split = _resolve_effective_split(data_path, split)
    rows = split_rows(
        load_drill_rows(data_path),
        split=effective_split,
        holdout_mod=holdout_mod,
        holdout_bucket=holdout_bucket,
    )
    cases = build_structural_benchmark_cases(rows, max_per_stage=max_per_stage)

    if generator is None:
        if not model_source:
            raise ValueError("model_source is required when no generator is supplied")
        tokenizer, model = load_model(model_source, device=device)
        generator = _default_generator(tokenizer, model)

    records = [evaluate_case(case, generator) for case in cases]
    summary = summarize_records(records)
    summary["config"] = {
        "data": data_path,
        "split": split,
        "effective_split": effective_split,
        "holdout_mod": holdout_mod,
        "holdout_bucket": holdout_bucket,
        "max_per_stage": max_per_stage,
        "model_source": model_source,
        "device": device,
    }
    summary["wall_clock_seconds"] = time.perf_counter() - started
    summary["records"] = [asdict(record) for record in records]
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Polly structural recovery benchmark")
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model_path", type=str, default=None)
    parser.add_argument("--hf_id", type=str, default=None)
    parser.add_argument("--split", choices=["all", "train", "holdout"], default="holdout")
    parser.add_argument("--holdout_mod", type=int, default=10)
    parser.add_argument("--holdout_bucket", type=int, default=0)
    parser.add_argument("--max_per_stage", type=int, default=24)
    parser.add_argument("--device", type=str, default="cuda")
    args = parser.parse_args(argv)

    model_source = args.model_path or args.hf_id
    if not model_source:
        print("ERROR: --model_path or --hf_id required", file=sys.stderr)
        return 2

    report = run_structural_benchmark(
        data_path=args.data,
        split=args.split,
        holdout_mod=args.holdout_mod,
        holdout_bucket=args.holdout_bucket,
        model_source=model_source,
        device=args.device,
        max_per_stage=args.max_per_stage,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"=== STRUCTURAL BENCHMARK: {args.data} ===")
    print(
        f"cases={report['summary']['total_cases']} "
        f"exact={report['summary']['exact_match_rate']:.1%} "
        f"validated={report['summary']['validator_pass_rate']:.1%} "
        f"pass={report['summary']['pass_rate']:.1%}"
    )
    for stage, stats in report["by_stage"].items():
        print(
            f"  {stage}: count={stats['count']} "
            f"exact={stats['exact_match_rate']:.1%} "
            f"pass={stats['pass_rate']:.1%}"
        )
    print(
        f"  trajectories: count={report['trajectory_bundles']['count']} "
        f"pass={report['trajectory_bundles']['pass_rate']:.1%}"
    )
    print(f"Wrote: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

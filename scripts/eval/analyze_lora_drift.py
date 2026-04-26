#!/usr/bin/env python3
"""Analyze pairwise LoRA adapter drift before merge.

For each local LoRA adapter, this computes per-module delta matrices B @ A and
compares adapters on shared modules with cosine similarity and sign-conflict
rate. The output is a decision matrix: route, linear, TIES, or DARE-TIES.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "artifacts" / "adapter_registry" / "registry.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "adapter_registry" / "drift"
MAX_SIGN_COMPARE_ELEMENTS = 200_000


def safe_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def load_registry_adapters(path: Path) -> list[Path]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    paths: list[Path] = []
    for adapter in payload.get("adapters", []):
        for row in adapter.get("local_adapters") or []:
            value = row.get("local_adapter_dir")
            if value:
                paths.append((REPO_ROOT / value).resolve())
    return paths


def find_default_adapters() -> list[Path]:
    root = REPO_ROOT / "artifacts" / "kaggle_output"
    return sorted({path.parent for path in root.rglob("adapter_config.json") if (path.parent / "adapter_model.safetensors").exists()})


def load_lora_deltas(adapter_dir: Path) -> dict[str, Any]:
    import numpy as np
    from safetensors.numpy import load_file

    model_path = adapter_dir / "adapter_model.safetensors"
    if not model_path.exists():
        raise FileNotFoundError(f"missing adapter_model.safetensors: {adapter_dir}")
    tensors = load_file(str(model_path))
    deltas: dict[str, Any] = {}
    for key, a_weight in tensors.items():
        if not key.endswith("lora_A.weight"):
            continue
        b_key = key[: -len("lora_A.weight")] + "lora_B.weight"
        b_weight = tensors.get(b_key)
        if b_weight is None:
            continue
        module = key[: -len(".lora_A.weight")]
        delta = np.matmul(b_weight.astype("float32"), a_weight.astype("float32")).reshape(-1)
        norm = float(np.linalg.norm(delta))
        if norm > 0 and math.isfinite(norm):
            deltas[module] = delta
    return deltas


def compare_delta_sets(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    shared = sorted(set(left) & set(right))
    cosines = []
    conflicts = []
    compared = 0
    for module in shared:
        a = left[module]
        b = right[module]
        if tuple(a.shape) != tuple(b.shape):
            continue
        a_norm = float(np.linalg.norm(a))
        b_norm = float(np.linalg.norm(b))
        if a_norm == 0.0 or b_norm == 0.0:
            continue
        cosines.append(float(np.dot(a, b) / (a_norm * b_norm)))
        if a.size > MAX_SIGN_COMPARE_ELEMENTS:
            idx = np.linspace(0, a.size - 1, num=MAX_SIGN_COMPARE_ELEMENTS, dtype=np.int64)
            a_cmp = a[idx]
            b_cmp = b[idx]
        else:
            a_cmp = a
            b_cmp = b
        nonzero = (a_cmp != 0) & (b_cmp != 0)
        if int(nonzero.sum()) == 0:
            continue
        conflicts.append(float(np.mean(np.signbit(a_cmp[nonzero]) != np.signbit(b_cmp[nonzero]))))
        compared += 1
    avg_cosine = sum(cosines) / len(cosines) if cosines else None
    avg_conflict = sum(conflicts) / len(conflicts) if conflicts else None
    return {
        "shared_modules": len(shared),
        "compared_modules": compared,
        "avg_cosine": avg_cosine,
        "avg_sign_conflict_rate": avg_conflict,
        "decision": decide_merge(avg_cosine, avg_conflict, compared),
    }


def decide_merge(avg_cosine: float | None, avg_conflict: float | None, compared_modules: int) -> str:
    if compared_modules == 0 or avg_cosine is None or avg_conflict is None:
        return "route_only_insufficient_overlap"
    if avg_conflict <= 0.10 and avg_cosine >= 0.25:
        return "linear_candidate"
    if avg_conflict <= 0.25 and avg_cosine >= 0.0:
        return "ties_candidate"
    if avg_conflict <= 0.45:
        return "dare_ties_candidate"
    return "route_only_conflict_high"


def analyze(adapters: list[Path]) -> dict[str, Any]:
    loaded = []
    for path in adapters:
        try:
            deltas = load_lora_deltas(path)
            loaded.append({"path": path, "deltas": deltas, "error": ""})
        except Exception as exc:
            loaded.append({"path": path, "deltas": {}, "error": str(exc)})

    pairs = []
    for i, left in enumerate(loaded):
        for right in loaded[i + 1 :]:
            result = compare_delta_sets(left["deltas"], right["deltas"]) if not left["error"] and not right["error"] else {
                "shared_modules": 0,
                "compared_modules": 0,
                "avg_cosine": None,
                "avg_sign_conflict_rate": None,
                "decision": "route_only_load_error",
            }
            pairs.append(
                {
                    "left": safe_rel(left["path"]),
                    "right": safe_rel(right["path"]),
                    **result,
                }
            )

    return {
        "schema_version": "scbe_lora_drift_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "adapters": [
            {
                "path": safe_rel(row["path"]),
                "module_count": len(row["deltas"]),
                "load_error": row["error"],
            }
            for row in loaded
        ],
        "pairs": pairs,
        "policy": {
            "linear_candidate": "Low sign conflict and positive cosine; still requires executable gates.",
            "ties_candidate": "Moderate conflict; use TIES-style conflict handling before merge.",
            "dare_ties_candidate": "High enough conflict that DARE-TIES is safer than linear if routing latency forces a merge.",
            "route_only": "Do not merge; route adapters by lane.",
        },
    }


def write_report(payload: dict[str, Any], output_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "drift_report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# LoRA Drift Report",
        "",
        f"Generated: `{payload['generated_at_utc']}`",
        "",
        "## Adapters",
        "",
        "| Adapter | Modules | Load Error |",
        "| --- | ---: | --- |",
    ]
    for row in payload["adapters"]:
        lines.append(f"| `{row['path']}` | {row['module_count']} | {str(row['load_error']).replace('|', '\\|')} |")
    lines.extend(
        [
            "",
            "## Pairwise Decisions",
            "",
            "| Left | Right | Shared | Compared | Cosine | Sign Conflict | Decision |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in payload["pairs"]:
        cosine = "" if row["avg_cosine"] is None else f"{row['avg_cosine']:.4f}"
        conflict = "" if row["avg_sign_conflict_rate"] is None else f"{row['avg_sign_conflict_rate']:.2%}"
        lines.append(
            f"| `{row['left']}` | `{row['right']}` | {row['shared_modules']} | {row['compared_modules']} | "
            f"{cosine} | {conflict} | `{row['decision']}` |"
        )
    (out_dir / "drift_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    latest = output_root / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "drift_report.json").write_text((out_dir / "drift_report.json").read_text(encoding="utf-8"), encoding="utf-8")
    (latest / "drift_report.md").write_text((out_dir / "drift_report.md").read_text(encoding="utf-8"), encoding="utf-8")
    return out_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=Path, action="append", default=[], help="Local adapter directory. Repeatable.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--use-registry", action="store_true", help="Analyze local adapter dirs listed in registry.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    adapters = [path.resolve() for path in args.adapter]
    if args.use_registry:
        adapters.extend(load_registry_adapters(args.registry))
    if not adapters:
        adapters = find_default_adapters()
    adapters = sorted(set(adapters))
    payload = analyze(adapters)
    out_dir = write_report(payload, args.output_root)
    print(f"Drift JSON: {out_dir / 'drift_report.json'}")
    print(f"Drift MD:   {out_dir / 'drift_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

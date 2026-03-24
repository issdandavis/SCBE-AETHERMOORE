#!/usr/bin/env python3
"""Probe attention tensors with whole/edge/signal/thermal mirror operators."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.probe_attention_fft import (  # noqa: E402
    DEFAULT_MAX_LENGTH,
    DEFAULT_MODEL_ID,
    build_control_matrix,
    extract_attentions,
    load_model_bundle,
    parse_index_list,
    resolve_prompts,
    resolve_token,
    safe_slug,
    select_indices,
    utc_now,
    utc_stamp,
)
from src.minimal.mirror_problem_fft import (  # noqa: E402
    apply_thermal_mirage,
    apply_thermal_mirror,
    edge_mirror,
    probe_attention_matrix,
    signal_mirror,
    whole_mirror,
)


DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "thermal_mirror"
DIFFERENTIAL_PAIRS = (
    ("D_w_e", "whole", "edge"),
    ("D_w_s", "whole", "signal"),
    ("D_w_t", "whole", "thermal"),
    ("D_e_s", "edge", "signal"),
    ("D_e_t", "edge", "thermal"),
    ("D_s_t", "signal", "thermal"),
    ("D_o_t", "original", "thermal"),
)


def _tensor_to_heads(array_like: Any) -> np.ndarray:
    if hasattr(array_like, "detach"):
        array = array_like.detach().cpu().float().numpy()
    else:
        array = np.asarray(array_like, dtype=np.float64)
    if array.ndim == 4:
        array = array[0]
    if array.ndim != 3:
        raise ValueError(f"Expected attention tensor with 3 dims after batch strip, got shape {array.shape}")
    return array


def _profile_summary(values: np.ndarray) -> dict[str, Any]:
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    return {
        "min": float(np.min(vector)),
        "max": float(np.max(vector)),
        "mean": float(np.mean(vector)),
        "preview": [float(x) for x in vector[: min(8, vector.size)]],
    }


def _empty_probe_bucket() -> dict[str, list[float]]:
    return {
        "s_specs": [],
        "peak_ratios": [],
        "spectral_entropies": [],
        "energy_totals": [],
    }


def _push_probe(bucket: dict[str, list[float]], candidate: dict[str, Any]) -> None:
    bucket["s_specs"].append(float(candidate["s_spec"]))
    bucket["peak_ratios"].append(float(candidate["peak_ratio"]))
    bucket["spectral_entropies"].append(float(candidate["spectral_entropy"]))
    bucket["energy_totals"].append(float(candidate["energy_total"]))


def _bucket_summary(bucket: dict[str, list[float]]) -> dict[str, Any]:
    count = len(bucket["s_specs"])
    return {
        "count": count,
        "average_s_spec": float(np.mean(bucket["s_specs"])) if count else 0.0,
        "average_peak_ratio": float(np.mean(bucket["peak_ratios"])) if count else 0.0,
        "average_spectral_entropy": float(np.mean(bucket["spectral_entropies"])) if count else 0.0,
        "average_energy_total": float(np.mean(bucket["energy_totals"])) if count else 0.0,
    }


def build_mirror_report(
    matrix: np.ndarray,
    *,
    mode: str,
    alpha: float,
    heat_source: str,
    min_scale: float,
    thermal_variant: str = "phase_mirage",
    sigma: float = 3.0,
) -> dict[str, Any]:
    original = np.asarray(matrix, dtype=np.float64)
    if thermal_variant == "phase_mirage":
        thermal_matrix, thermal_profile = apply_thermal_mirage(original, alpha=alpha, sigma=sigma)
    elif thermal_variant == "attenuation":
        thermal_matrix, thermal_profile = apply_thermal_mirror(
            original,
            alpha=alpha,
            source=heat_source,
            min_scale=min_scale,
        )
    else:
        raise ValueError(f"unsupported thermal variant: {thermal_variant}")
    transforms = {
        "original": original,
        "whole": whole_mirror(original),
        "edge": edge_mirror(original),
        "signal": signal_mirror(original),
        "thermal": thermal_matrix,
    }
    transform_reports = {
        name: {
            "matrix_shape": list(candidate_matrix.shape),
            "candidate": asdict(probe_attention_matrix(candidate_matrix, mode=mode)),
        }
        for name, candidate_matrix in transforms.items()
    }

    differential_reports: dict[str, Any] = {}
    for label, left_name, right_name in DIFFERENTIAL_PAIRS:
        left = transforms[left_name]
        right = transforms[right_name]
        if left.shape != right.shape:
            continue
        delta = left - right
        differential_reports[label] = {
            "pair": [left_name, right_name],
            "matrix_shape": list(delta.shape),
            "candidate": asdict(probe_attention_matrix(delta, mode=mode)),
        }

    return {
        "matrix_shape": list(original.shape),
        "transforms": transform_reports,
        "differentials": differential_reports,
        "thermal_profile": {
            "variant": thermal_variant,
            "source": heat_source,
            "alpha": float(alpha),
            "min_scale": float(min_scale),
            "sigma": float(sigma),
            **(
                {
                    "row_heat": _profile_summary(np.asarray(thermal_profile["row_heat"])),
                    "col_heat": _profile_summary(np.asarray(thermal_profile["col_heat"])),
                    "row_scale": _profile_summary(np.asarray(thermal_profile["row_scale"])),
                    "col_scale": _profile_summary(np.asarray(thermal_profile["col_scale"])),
                }
                if thermal_variant == "attenuation"
                else {
                    "heat_field": _profile_summary(np.asarray(thermal_profile["heat_field"])),
                    "phase_field": _profile_summary(np.asarray(thermal_profile["phase_field"])),
                }
            ),
        },
    }


def _aggregate_head_report(
    transform_buckets: dict[str, dict[str, list[float]]],
    differential_buckets: dict[str, dict[str, list[float]]],
    report: dict[str, Any],
) -> None:
    for name, transform in report["transforms"].items():
        bucket = transform_buckets.setdefault(name, _empty_probe_bucket())
        _push_probe(bucket, transform["candidate"])
    for name, differential in report["differentials"].items():
        bucket = differential_buckets.setdefault(name, _empty_probe_bucket())
        _push_probe(bucket, differential["candidate"])


def analyze_attention_stack(
    attentions: list[Any] | tuple[Any, ...],
    *,
    mode: str,
    alpha: float,
    heat_source: str,
    min_scale: float,
    thermal_variant: str = "phase_mirage",
    sigma: float = 3.0,
    layer_indices: list[int] | None = None,
    head_indices: list[int] | None = None,
    max_layers: int | None = None,
    max_heads: int | None = None,
) -> dict[str, Any]:
    selected_layers = select_indices(len(attentions), layer_indices, max_layers)
    layer_reports: list[dict[str, Any]] = []
    transform_buckets: dict[str, dict[str, list[float]]] = {}
    differential_buckets: dict[str, dict[str, list[float]]] = {}

    for layer_index in selected_layers:
        heads = _tensor_to_heads(attentions[layer_index])
        selected_heads = select_indices(heads.shape[0], head_indices, max_heads)
        head_reports: list[dict[str, Any]] = []

        for head_index in selected_heads:
            report = build_mirror_report(
                heads[head_index],
                mode=mode,
                alpha=alpha,
                heat_source=heat_source,
                min_scale=min_scale,
                thermal_variant=thermal_variant,
                sigma=sigma,
            )
            _aggregate_head_report(transform_buckets, differential_buckets, report)
            head_reports.append({"head_index": head_index, **report})

        layer_reports.append(
            {
                "layer_index": layer_index,
                "head_count": len(head_reports),
                "heads": head_reports,
            }
        )

    total_heads = sum(layer["head_count"] for layer in layer_reports)
    return {
        "layer_count": len(layer_reports),
        "head_count": total_heads,
        "mode": mode,
        "alpha": float(alpha),
        "heat_source": heat_source,
        "min_scale": float(min_scale),
        "thermal_variant": thermal_variant,
        "sigma": float(sigma),
        "transform_summaries": {name: _bucket_summary(bucket) for name, bucket in sorted(transform_buckets.items())},
        "differential_summaries": {
            name: _bucket_summary(bucket) for name, bucket in sorted(differential_buckets.items())
        },
        "layers": layer_reports,
    }


def analyze_prompt_batch(
    extractions: list[dict[str, Any]],
    *,
    mode: str,
    alpha: float,
    heat_source: str,
    min_scale: float,
    thermal_variant: str = "phase_mirage",
    sigma: float = 3.0,
    layer_indices: list[int] | None = None,
    head_indices: list[int] | None = None,
    max_layers: int | None = None,
    max_heads: int | None = None,
) -> dict[str, Any]:
    if not extractions:
        raise ValueError("at least one extraction is required")

    prompt_reports: list[dict[str, Any]] = []
    transform_buckets: dict[str, dict[str, list[float]]] = {}
    differential_buckets: dict[str, dict[str, list[float]]] = {}

    for extraction in extractions:
        analysis = analyze_attention_stack(
            extraction["attentions"],
            mode=mode,
            alpha=alpha,
            heat_source=heat_source,
            min_scale=min_scale,
            thermal_variant=thermal_variant,
            sigma=sigma,
            layer_indices=layer_indices,
            head_indices=head_indices,
            max_layers=max_layers,
            max_heads=max_heads,
        )
        prompt_reports.append(
            {
                "prompt": extraction["prompt"],
                "sequence_length": extraction.get("sequence_length"),
                "token_count": extraction.get("token_count"),
                "analysis": analysis,
            }
        )
        for layer in analysis["layers"]:
            for head in layer["heads"]:
                _aggregate_head_report(transform_buckets, differential_buckets, head)

    total_heads = sum(
        layer["head_count"] for prompt_report in prompt_reports for layer in prompt_report["analysis"]["layers"]
    )
    return {
        "prompt_count": len(prompt_reports),
        "head_count": total_heads,
        "mode": mode,
        "alpha": float(alpha),
        "heat_source": heat_source,
        "min_scale": float(min_scale),
        "thermal_variant": thermal_variant,
        "sigma": float(sigma),
        "transform_summaries": {name: _bucket_summary(bucket) for name, bucket in sorted(transform_buckets.items())},
        "differential_summaries": {
            name: _bucket_summary(bucket) for name, bucket in sorted(differential_buckets.items())
        },
        "prompt_reports": prompt_reports,
    }


def analyze_control_matrix(
    kind: str,
    *,
    size: int,
    mode: str,
    alpha: float,
    heat_source: str,
    min_scale: float,
    thermal_variant: str = "phase_mirage",
    sigma: float = 3.0,
    seed: int = 7,
) -> dict[str, Any]:
    matrix = build_control_matrix(kind, size, seed=seed)
    report = build_mirror_report(
        matrix,
        mode=mode,
        alpha=alpha,
        heat_source=heat_source,
        min_scale=min_scale,
        thermal_variant=thermal_variant,
        sigma=sigma,
    )
    transform_buckets: dict[str, dict[str, list[float]]] = {}
    differential_buckets: dict[str, dict[str, list[float]]] = {}
    _aggregate_head_report(transform_buckets, differential_buckets, report)
    return {
        "control_kind": kind,
        "size": size,
        "mode": mode,
        "alpha": float(alpha),
        "heat_source": heat_source,
        "min_scale": float(min_scale),
        "thermal_variant": thermal_variant,
        "sigma": float(sigma),
        "transform_summaries": {name: _bucket_summary(bucket) for name, bucket in sorted(transform_buckets.items())},
        "differential_summaries": {
            name: _bucket_summary(bucket) for name, bucket in sorted(differential_buckets.items())
        },
        "matrix_report": report,
    }


def write_report(report: dict[str, Any], *, output_root: Path, label: str) -> Path:
    bundle_dir = output_root / f"{safe_slug(label)}-{utc_stamp()}"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    path = bundle_dir / "thermal_mirror_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def build_report(
    *,
    model_id: str | None = None,
    bundle: Any | None = None,
    extraction: dict[str, Any] | None = None,
    analysis: dict[str, Any],
    prompt: str | None = None,
    token_env: str,
    control_kind: str | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "generated_at_utc": utc_now(),
        "record_type": "thermal_mirror_probe_v1",
        "analysis": analysis,
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    if control_kind:
        report["control_kind"] = control_kind
        report["model_id"] = "synthetic-control"
        return report

    report["model_id"] = model_id or (bundle.model_id if bundle else "")
    report["prompt"] = prompt or ""
    report["token_env"] = token_env
    if bundle:
        report["model"] = {
            "source": bundle.source,
            "device": bundle.device,
            "dtype": bundle.dtype,
            "base_model_id": bundle.base_model_id,
        }
    if extraction:
        report["input"] = {
            "sequence_length": extraction.get("sequence_length"),
            "token_count": extraction.get("token_count"),
            "tokens_preview": extraction.get("tokens", [])[:24],
        }
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe attention tensors with thermal mirror operators.")
    parser.add_argument("prompt", nargs="?", default="", help="Prompt to run through the model forward pass.")
    parser.add_argument("--prompt-file", default="", help="Optional UTF-8 file containing the prompt.")
    parser.add_argument(
        "--prompt-list-file", default="", help="Optional file with one prompt per line or a JSON array."
    )
    parser.add_argument("--use-default-prompt-set", action="store_true", help="Use the built-in semantic prompt batch.")
    parser.add_argument("--max-prompts", type=int, default=0)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--token-env", default="HF_TOKEN")
    parser.add_argument("--mode", default="flatten", choices=["row_mean", "column_mean", "diagonal", "flatten"])
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    parser.add_argument("--layer-indices", default="")
    parser.add_argument("--head-indices", default="")
    parser.add_argument("--max-layers", type=int, default=1)
    parser.add_argument("--max-heads", type=int, default=4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--attn-implementation", default="eager")
    parser.add_argument("--torch-dtype", default="auto")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--control", choices=["uniform", "banded", "random"], default="")
    parser.add_argument("--size", type=int, default=16)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--heat-source", choices=["l2_norm", "abs_mean"], default="l2_norm")
    parser.add_argument("--min-scale", type=float, default=0.05)
    parser.add_argument("--thermal-variant", choices=["phase_mirage", "attenuation"], default="phase_mirage")
    parser.add_argument("--sigma", type=float, default=3.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_root = Path(args.output_root)

    if args.control:
        analysis = analyze_control_matrix(
            args.control,
            size=args.size,
            mode=args.mode,
            alpha=args.alpha,
            heat_source=args.heat_source,
            min_scale=args.min_scale,
            thermal_variant=args.thermal_variant,
            sigma=args.sigma,
            seed=args.seed,
        )
        report = build_report(
            analysis=analysis,
            token_env=args.token_env,
            control_kind=args.control,
        )
        artifact_path = write_report(report, output_root=output_root, label=f"control-{args.control}")
    else:
        prompts = resolve_prompts(
            args.prompt,
            prompt_file=args.prompt_file or None,
            prompt_list_file=args.prompt_list_file or None,
            use_default_prompt_set=args.use_default_prompt_set,
            max_prompts=args.max_prompts or None,
        )
        token = resolve_token(args.token_env)
        bundle = load_model_bundle(
            args.model_id,
            token=token,
            requested_device=args.device,
            attn_implementation=args.attn_implementation or None,
            torch_dtype_name=args.torch_dtype or None,
        )
        extractions = [extract_attentions(bundle, prompt, max_length=args.max_length) for prompt in prompts]
        analysis = analyze_prompt_batch(
            extractions,
            mode=args.mode,
            alpha=args.alpha,
            heat_source=args.heat_source,
            min_scale=args.min_scale,
            thermal_variant=args.thermal_variant,
            sigma=args.sigma,
            layer_indices=parse_index_list(args.layer_indices),
            head_indices=parse_index_list(args.head_indices),
            max_layers=args.max_layers,
            max_heads=args.max_heads,
        )
        report = build_report(
            model_id=args.model_id,
            bundle=bundle,
            extraction=extractions[0],
            analysis=analysis,
            prompt=prompts[0] if len(prompts) == 1 else "",
            token_env=args.token_env,
        )
        report["prompt_count"] = len(prompts)
        if len(prompts) > 1:
            report["prompt_set_preview"] = prompts[: min(5, len(prompts))]
        artifact_path = write_report(report, output_root=output_root, label=args.model_id)

    payload = {**report, "artifact_path": str(artifact_path)}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Thermal mirror probe complete: {artifact_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

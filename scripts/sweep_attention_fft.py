#!/usr/bin/env python3
"""Sweep attention FFT probe across multiple prompts, layers, heads, and projection modes.

Builds on Codex's probe_attention_fft.py to run the full experiment matrix:
- 5 semantic prompts (same meaning, different phrasing)
- 3 control prompts (shuffled tokens, nonsense, repeated)
- 4 projection modes (flatten, row_mean, column_mean, diagonal)
- All layers and heads the model exposes

Outputs a single JSON report with per-head metrics for paper Section 11.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.probe_attention_fft import (
    load_model_bundle,
    extract_attentions,
    analyze_attention_stack,
    resolve_token,
    utc_now,
)

# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------

SEMANTIC_PROMPTS = [
    "Explain why governed attention might differ from learned attention.",
    "What makes governed attention different from attention that is learned?",
    "How does attention that follows geometric rules compare to freely learned attention?",
    "Describe the contrast between prescribed attention weights and discovered ones.",
    "Why would structured attention behave differently than attention found by gradient descent?",
]

CONTROL_PROMPTS = {
    "nonsense": "Glorp fizz quantum banana seventeen the the the wombat.",
    "repeated": "attention attention attention attention attention attention attention attention",
    "numeric": "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20",
}

PROJECTION_MODES = ["flatten", "row_mean", "diagonal"]

DEFAULT_MODEL_ID = "issdandavis/scbe-pivot-qwen-0.5b"
MAX_LENGTH = 96


def run_sweep(
    model_id: str = DEFAULT_MODEL_ID,
    max_layers: int | None = None,
    max_heads: int | None = None,
) -> dict:
    """Run the full experiment matrix and return a structured report."""

    token = resolve_token("HF_TOKEN")
    print(f"Loading model: {model_id}")
    bundle = load_model_bundle(
        model_id,
        token=token,
        requested_device="auto",
        attn_implementation="eager",
    )
    print(f"Model loaded: {bundle.source} on {bundle.device} ({bundle.dtype})")

    all_prompts = {
        **{f"semantic_{i}": p for i, p in enumerate(SEMANTIC_PROMPTS)},
        **{f"control_{k}": v for k, v in CONTROL_PROMPTS.items()},
    }

    results: list[dict] = []

    for prompt_key, prompt_text in all_prompts.items():
        print(f"  Probing: {prompt_key[:40]}...")
        try:
            extraction = extract_attentions(bundle, prompt_text, max_length=MAX_LENGTH)
        except Exception as exc:
            print(f"    SKIP (extraction failed): {exc}")
            continue

        n_layers = len(extraction["attentions"])
        seq_len = extraction["sequence_length"]

        for mode in PROJECTION_MODES:
            try:
                analysis = analyze_attention_stack(
                    extraction["attentions"],
                    mode=mode,
                    max_layers=max_layers,
                    max_heads=max_heads,
                )
            except Exception as exc:
                print(f"    SKIP mode={mode}: {exc}")
                continue

            results.append({
                "prompt_key": prompt_key,
                "prompt_text": prompt_text,
                "mode": mode,
                "sequence_length": seq_len,
                "total_layers": n_layers,
                "analysis": analysis,
            })

    # Aggregate across semantic vs control prompts
    semantic_s_specs = []
    control_s_specs = []
    semantic_entropies = []
    control_entropies = []
    semantic_banded_rates = []
    control_banded_rates = []

    for r in results:
        a = r["analysis"]
        if r["prompt_key"].startswith("semantic_"):
            semantic_s_specs.append(a["average_s_spec"])
            semantic_entropies.append(a["average_spectral_entropy"])
            semantic_banded_rates.append(a["banded_vote_rate"])
        else:
            control_s_specs.append(a["average_s_spec"])
            control_entropies.append(a["average_spectral_entropy"])
            control_banded_rates.append(a["banded_vote_rate"])

    summary = {
        "semantic": {
            "count": len(semantic_s_specs),
            "mean_s_spec": float(np.mean(semantic_s_specs)) if semantic_s_specs else None,
            "std_s_spec": float(np.std(semantic_s_specs)) if semantic_s_specs else None,
            "mean_spectral_entropy": float(np.mean(semantic_entropies)) if semantic_entropies else None,
            "mean_banded_vote_rate": float(np.mean(semantic_banded_rates)) if semantic_banded_rates else None,
        },
        "control": {
            "count": len(control_s_specs),
            "mean_s_spec": float(np.mean(control_s_specs)) if control_s_specs else None,
            "std_s_spec": float(np.std(control_s_specs)) if control_s_specs else None,
            "mean_spectral_entropy": float(np.mean(control_entropies)) if control_entropies else None,
            "mean_banded_vote_rate": float(np.mean(control_banded_rates)) if control_banded_rates else None,
        },
    }

    # Per-mode breakdown
    mode_summary = {}
    for mode in PROJECTION_MODES:
        mode_results = [r for r in results if r["mode"] == mode]
        if mode_results:
            specs = [r["analysis"]["average_s_spec"] for r in mode_results]
            mode_summary[mode] = {
                "count": len(specs),
                "mean_s_spec": float(np.mean(specs)),
                "std_s_spec": float(np.std(specs)),
            }

    # Per-layer breakdown (across all prompts and modes)
    layer_data: dict[int, list[float]] = {}
    for r in results:
        for layer in r["analysis"].get("layers", []):
            li = layer["layer_index"]
            for head in layer.get("heads", []):
                layer_data.setdefault(li, []).append(head["candidate"]["s_spec"])

    layer_summary = {}
    for li in sorted(layer_data.keys()):
        vals = layer_data[li]
        layer_summary[f"layer_{li}"] = {
            "head_measurements": len(vals),
            "mean_s_spec": float(np.mean(vals)),
            "std_s_spec": float(np.std(vals)),
            "min_s_spec": float(np.min(vals)),
            "max_s_spec": float(np.max(vals)),
        }

    report = {
        "generated_at_utc": utc_now(),
        "record_type": "attention_fft_sweep_v1",
        "model_id": model_id,
        "model_source": bundle.source,
        "model_device": bundle.device,
        "model_dtype": bundle.dtype,
        "base_model_id": bundle.base_model_id,
        "prompt_count": len(all_prompts),
        "mode_count": len(PROJECTION_MODES),
        "total_probe_runs": len(results),
        "summary": summary,
        "mode_summary": mode_summary,
        "layer_summary": layer_summary,
        "results": results,
    }

    return report


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sweep attention FFT probe across prompts and modes.")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--max-layers", type=int, default=None, help="Limit layers (None = all)")
    parser.add_argument("--max-heads", type=int, default=None, help="Limit heads per layer (None = all)")
    parser.add_argument("--output", default="", help="Output JSON path (default: artifacts/attention_fft/sweep_report.json)")
    args = parser.parse_args()

    report = run_sweep(
        model_id=args.model_id,
        max_layers=args.max_layers,
        max_heads=args.max_heads,
    )

    output_path = args.output or str(
        PROJECT_ROOT / "artifacts" / "attention_fft" / f"sweep-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSweep complete: {output_path}")
    print(f"  Probes: {report['total_probe_runs']}")
    print(f"  Semantic mean S_spec: {report['summary']['semantic']['mean_s_spec']}")
    print(f"  Control mean S_spec: {report['summary']['control']['mean_s_spec']}")

    if report["layer_summary"]:
        print(f"  Layers analyzed: {len(report['layer_summary'])}")
        for layer_key, stats in report["layer_summary"].items():
            print(f"    {layer_key}: mean={stats['mean_s_spec']:.4f} std={stats['std_s_spec']:.4f} range=[{stats['min_s_spec']:.4f}, {stats['max_s_spec']:.4f}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

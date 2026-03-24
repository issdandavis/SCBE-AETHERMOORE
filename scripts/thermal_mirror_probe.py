#!/usr/bin/env python3
"""Thermal Mirror Probe — Mirage Spectral Mapping on Transformer Weights.

Instead of hard geometric mirrors (M_w = -W, M_e = W.T), this probe
applies a continuous thermal deformation field where the model's own
activation magnitudes define the temperature. High-activation regions
"mirage away" — their spectral contribution is suppressed exponentially.

The key difference from the standard mirror differential:
- Standard mirror: all frequencies preserved, just reordered
- Thermal mirror: frequencies selectively suppressed in "hot zones"
- The delta between original and thermally-deformed S_spec reveals
  which frequencies the model itself is "burning away"

Three temperature sources:
  T_self(W)   = row-wise L2 norm of W (self-activation magnitude)
  T_column(W) = column-wise L2 norm of W (input-activation magnitude)
  T_diag(W)   = diagonal magnitude (self-attention strength)

Thermal deformation:
  M_thermo(W, T, alpha) = W * exp(-alpha * T_normalized)

Origin: Issac Davis concept ("how do you create a field between a mirror
and yourself without a physical obstruction? heat."), formalized through
Codex and Claude.

Usage:
  C:/Users/issda/Python312/python.exe scripts/thermal_mirror_probe.py
  C:/Users/issda/Python312/python.exe scripts/thermal_mirror_probe.py --model distilbert-base-uncased --alpha 0.5 1.0 2.0 5.0
  C:/Users/issda/Python312/python.exe scripts/thermal_mirror_probe.py --model issdandavis/scbe-pivot-qwen-0.5b --json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

EPSILON = 1e-10
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "thermal_mirror"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpectralMeasurement:
    s_spec: float
    peak_ratio: float
    spectral_entropy: float
    energy_total: float


@dataclass(frozen=True)
class ThermalProbeResult:
    layer: int
    weight_type: str
    shape: list[int]
    alpha: float
    temperature_source: str
    original: SpectralMeasurement
    deformed: SpectralMeasurement
    delta_s_spec: float
    suppression_ratio: float
    temperature_stats: dict


# ---------------------------------------------------------------------------
# Spectral measurement (2D FFT)
# ---------------------------------------------------------------------------


def spectral_measure_2d(W: np.ndarray) -> SpectralMeasurement:
    fft2d = np.fft.fft2(W)
    power = np.abs(fft2d) ** 2
    total = float(power.sum())
    if total < EPSILON:
        return SpectralMeasurement(s_spec=0.0, peak_ratio=0.0, spectral_entropy=0.0, energy_total=0.0)
    peak = float(power.max())
    probs = power / (total + EPSILON)
    entropy = float(-np.sum(probs * np.log2(probs + EPSILON)))
    return SpectralMeasurement(
        s_spec=peak / total,
        peak_ratio=peak / total,
        spectral_entropy=entropy,
        energy_total=total,
    )


# ---------------------------------------------------------------------------
# Temperature fields
# ---------------------------------------------------------------------------


def temperature_row_norm(W: np.ndarray) -> np.ndarray:
    """T_self: each row's L2 norm, broadcast to matrix shape."""
    row_norms = np.linalg.norm(W, axis=1, keepdims=True)
    max_norm = row_norms.max()
    if max_norm < EPSILON:
        return np.zeros_like(W)
    return np.broadcast_to(row_norms / max_norm, W.shape).copy()


def temperature_col_norm(W: np.ndarray) -> np.ndarray:
    """T_column: each column's L2 norm, broadcast to matrix shape."""
    col_norms = np.linalg.norm(W, axis=0, keepdims=True)
    max_norm = col_norms.max()
    if max_norm < EPSILON:
        return np.zeros_like(W)
    return np.broadcast_to(col_norms / max_norm, W.shape).copy()


def temperature_elementwise(W: np.ndarray) -> np.ndarray:
    """T_element: absolute value of each element, normalized."""
    abs_W = np.abs(W)
    max_val = abs_W.max()
    if max_val < EPSILON:
        return np.zeros_like(W)
    return abs_W / max_val


def temperature_diagonal(W: np.ndarray) -> np.ndarray:
    """T_diag: diagonal magnitude broadcast to full matrix.
    For non-square matrices, use min(rows, cols) diagonal."""
    min_dim = min(W.shape)
    diag = np.abs(np.diag(W[:min_dim, :min_dim]))
    max_diag = diag.max() if diag.size > 0 else 0
    if max_diag < EPSILON:
        return np.zeros_like(W)
    # Broadcast: each row i gets temperature from diag[i % min_dim]
    T = np.zeros_like(W)
    for i in range(W.shape[0]):
        T[i, :] = diag[i % min_dim] / max_diag
    return T


TEMPERATURE_SOURCES = {
    "row_norm": temperature_row_norm,
    "col_norm": temperature_col_norm,
    "elementwise": temperature_elementwise,
    "diagonal": temperature_diagonal,
}


# ---------------------------------------------------------------------------
# Thermal deformation
# ---------------------------------------------------------------------------


def thermal_deform(W: np.ndarray, T: np.ndarray, alpha: float) -> np.ndarray:
    """M_thermo(W, T, alpha) = W * exp(-alpha * T)"""
    return W * np.exp(-alpha * T)


# ---------------------------------------------------------------------------
# Single weight analysis
# ---------------------------------------------------------------------------


def analyze_thermal(
    W: np.ndarray,
    layer: int,
    weight_type: str,
    alpha: float,
    temp_source: str,
) -> ThermalProbeResult:
    T_func = TEMPERATURE_SOURCES[temp_source]
    T = T_func(W)

    original = spectral_measure_2d(W)
    W_deformed = thermal_deform(W, T, alpha)
    deformed = spectral_measure_2d(W_deformed)

    delta = original.s_spec - deformed.s_spec
    suppression = deformed.energy_total / (original.energy_total + EPSILON)

    return ThermalProbeResult(
        layer=layer,
        weight_type=weight_type,
        shape=list(W.shape),
        alpha=alpha,
        temperature_source=temp_source,
        original=original,
        deformed=deformed,
        delta_s_spec=delta,
        suppression_ratio=suppression,
        temperature_stats={
            "mean": float(T.mean()),
            "std": float(T.std()),
            "max": float(T.max()),
            "min": float(T.min()),
            "nonzero_fraction": float((T > EPSILON).mean()),
        },
    )


# ---------------------------------------------------------------------------
# Model weight extraction (reuse from mirror_differential_telemetry.py)
# ---------------------------------------------------------------------------


def find_qkv_weights(model, layer_idx: int) -> dict[str, np.ndarray]:
    weights = {}
    layer = None

    if hasattr(model, "transformer") and hasattr(model.transformer, "layer"):
        layer = model.transformer.layer[layer_idx]
    elif hasattr(model, "encoder") and hasattr(model.encoder, "layer"):
        layer = model.encoder.layer[layer_idx]
    elif hasattr(model, "model") and hasattr(model.model, "layers"):
        layer = model.model.layers[layer_idx]

    if layer is None:
        return weights

    attn = getattr(layer, "attention", None)
    if attn:
        for name, attr in [("Q", "q_lin"), ("K", "k_lin"), ("V", "v_lin")]:
            proj = getattr(attn, attr, None)
            if proj and hasattr(proj, "weight"):
                weights[name] = proj.weight.detach().cpu().float().numpy()

    if not weights and attn:
        self_attn = getattr(attn, "self", None)
        if self_attn:
            for name, attr in [("Q", "query"), ("K", "key"), ("V", "value")]:
                proj = getattr(self_attn, attr, None)
                if proj and hasattr(proj, "weight"):
                    weights[name] = proj.weight.detach().cpu().float().numpy()

    self_attn = getattr(layer, "self_attn", None)
    if not weights and self_attn:
        for name, attr in [("Q", "q_proj"), ("K", "k_proj"), ("V", "v_proj")]:
            proj = getattr(self_attn, attr, None)
            if proj and hasattr(proj, "weight"):
                weights[name] = proj.weight.detach().cpu().float().numpy()

    return weights


def count_layers(model) -> int:
    if hasattr(model, "transformer") and hasattr(model.transformer, "layer"):
        return len(model.transformer.layer)
    if hasattr(model, "encoder") and hasattr(model.encoder, "layer"):
        return len(model.encoder.layer)
    if hasattr(model, "model") and hasattr(model.model, "layers"):
        return len(model.model.layers)
    return 0


# ---------------------------------------------------------------------------
# Full sweep
# ---------------------------------------------------------------------------


def run_thermal_sweep(
    model_id: str = "distilbert-base-uncased",
    alphas: list[float] | None = None,
    temp_sources: list[str] | None = None,
    max_layers: int | None = None,
    token: str | None = None,
) -> dict:
    import torch
    from transformers import AutoModel

    if alphas is None:
        alphas = [0.5, 1.0, 2.0, 5.0, 10.0]
    if temp_sources is None:
        temp_sources = list(TEMPERATURE_SOURCES.keys())

    print(f"Loading model: {model_id}")
    kwargs = {"token": token} if token else {}
    # Try CausalLM first (most common for decoder models like Qwen, LLaMA, GPT)
    # then fall back to AutoModel (BERT, DistilBERT, etc.)
    try:
        from transformers import AutoModelForCausalLM

        model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    except Exception:
        model = AutoModel.from_pretrained(model_id, **kwargs)

    model.eval()
    n_layers = count_layers(model)
    if max_layers:
        n_layers = min(n_layers, max_layers)

    # Noise baseline
    sample_weights = find_qkv_weights(model, 0)
    if not sample_weights:
        raise RuntimeError(f"Could not find Q/K/V weights in {model_id}")
    sample_shape = list(sample_weights.values())[0].shape
    noise_baseline = float(np.mean([spectral_measure_2d(np.random.randn(*sample_shape)).s_spec for _ in range(10)]))

    print(f"Layers: {n_layers}, Shape: {sample_shape}, Noise baseline: {noise_baseline:.6f}")
    print(f"Alphas: {alphas}")
    print(f"Temperature sources: {temp_sources}")
    print()

    all_results: list[ThermalProbeResult] = []

    for layer_idx in range(n_layers):
        qkv = find_qkv_weights(model, layer_idx)
        for wtype, W in qkv.items():
            for temp_src in temp_sources:
                for alpha in alphas:
                    result = analyze_thermal(W, layer_idx, wtype, alpha, temp_src)
                    all_results.append(result)

            # Print summary for this weight at alpha=2.0, row_norm
            key_result = next(
                (
                    r
                    for r in all_results
                    if r.layer == layer_idx
                    and r.weight_type == wtype
                    and r.alpha == 2.0
                    and r.temperature_source == "row_norm"
                ),
                None,
            )
            if key_result:
                print(
                    f"  L{layer_idx} {wtype}: orig={key_result.original.s_spec:.4f} "
                    f"deformed={key_result.deformed.s_spec:.4f} "
                    f"delta={key_result.delta_s_spec:.4f} "
                    f"suppression={key_result.suppression_ratio:.4f}"
                )

    # Aggregate summaries
    summary = {}
    for wtype in ["Q", "K", "V"]:
        for temp_src in temp_sources:
            for alpha in alphas:
                subset = [
                    r
                    for r in all_results
                    if r.weight_type == wtype and r.temperature_source == temp_src and r.alpha == alpha
                ]
                if not subset:
                    continue
                key = f"{wtype}_{temp_src}_a{alpha}"
                summary[key] = {
                    "weight_type": wtype,
                    "temperature_source": temp_src,
                    "alpha": alpha,
                    "count": len(subset),
                    "mean_original_s_spec": float(np.mean([r.original.s_spec for r in subset])),
                    "mean_deformed_s_spec": float(np.mean([r.deformed.s_spec for r in subset])),
                    "mean_delta_s_spec": float(np.mean([r.delta_s_spec for r in subset])),
                    "mean_suppression_ratio": float(np.mean([r.suppression_ratio for r in subset])),
                    "original_vs_noise": (
                        float(np.mean([r.original.s_spec for r in subset])) / noise_baseline
                        if noise_baseline > 0
                        else 0
                    ),
                    "deformed_vs_noise": (
                        float(np.mean([r.deformed.s_spec for r in subset])) / noise_baseline
                        if noise_baseline > 0
                        else 0
                    ),
                }

    # Cross-alpha comparison: how does deformation scale with temperature?
    alpha_scaling = {}
    for wtype in ["Q", "K", "V"]:
        for temp_src in temp_sources:
            points = []
            for alpha in sorted(alphas):
                subset = [
                    r
                    for r in all_results
                    if r.weight_type == wtype and r.temperature_source == temp_src and r.alpha == alpha
                ]
                if subset:
                    points.append(
                        {
                            "alpha": alpha,
                            "mean_deformed_s_spec": float(np.mean([r.deformed.s_spec for r in subset])),
                            "mean_suppression": float(np.mean([r.suppression_ratio for r in subset])),
                        }
                    )
            if points:
                alpha_scaling[f"{wtype}_{temp_src}"] = points

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "record_type": "thermal_mirror_probe_v1",
        "model_id": model_id,
        "weight_shape": list(sample_shape),
        "noise_baseline": noise_baseline,
        "layers_analyzed": n_layers,
        "alphas": alphas,
        "temperature_sources": temp_sources,
        "total_measurements": len(all_results),
        "summary": summary,
        "alpha_scaling": alpha_scaling,
        "results": [asdict(r) for r in all_results],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Thermal Mirror Probe on transformer weights.")
    parser.add_argument("--model", default="distilbert-base-uncased")
    parser.add_argument("--alpha", type=float, nargs="+", default=[0.5, 1.0, 2.0, 5.0, 10.0])
    parser.add_argument("--temp-sources", nargs="+", default=list(TEMPERATURE_SOURCES.keys()))
    parser.add_argument("--max-layers", type=int, default=None)
    parser.add_argument("--token-env", default="HF_TOKEN")
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    import os

    token = os.environ.get(args.token_env, "").strip() or None

    result = run_thermal_sweep(
        model_id=args.model,
        alphas=args.alpha,
        temp_sources=args.temp_sources,
        max_layers=args.max_layers,
        token=token,
    )

    output_path = args.output or str(
        DEFAULT_OUTPUT_ROOT / f"thermal-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"\nThermal Mirror Probe complete: {output_path}")
    print(f"  Total measurements: {result['total_measurements']}")

    # Print the key comparison: Q vs K vs V at alpha=2.0, row_norm
    for wtype in ["Q", "K", "V"]:
        key = f"{wtype}_row_norm_a2.0"
        if key in result["summary"]:
            s = result["summary"][key]
            print(
                f"  {wtype} (row_norm, a=2.0): "
                f"orig={s['mean_original_s_spec']:.4f} ({s['original_vs_noise']:.2f}x noise) -> "
                f"deformed={s['mean_deformed_s_spec']:.4f} ({s['deformed_vs_noise']:.2f}x noise), "
                f"delta={s['mean_delta_s_spec']:.4f}, suppression={s['mean_suppression_ratio']:.4f}"
            )

    if args.json:
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

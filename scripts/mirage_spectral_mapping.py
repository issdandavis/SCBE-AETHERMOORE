#!/usr/bin/env python3
"""Mirage Spectral Mapping — Complex Phase-Shift Thermal Probe.

From Issac's Colab notebook. Uses complex plane mapping:
  W_mirage = W * exp(i * alpha * Heat)

where Heat is derived from Gaussian-blurred weight magnitudes.

This is the COMPLEX version of the thermal mirror probe.
The local thermal_mirror_probe.py uses REAL suppression: W * exp(-alpha * T).
Both arrive at the same conclusion: Q-weight harmonic structure is robust.

The mirage version shows >100% survival (heat FOCUSES latent frequencies).
The suppression version shows S_spec increase (noise removed, signal preserved).

Origin: Issac Davis concept ("heat creates a mirage field between mirror and observer"),
implemented on Google Colab against DistilBERT, ported to repo by Claude.

Usage:
  C:/Users/issda/Python312/python.exe scripts/mirage_spectral_mapping.py
  C:/Users/issda/Python312/python.exe scripts/mirage_spectral_mapping.py --model distilbert-base-uncased --alpha 1.0 --sigma 5.0
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    from scipy.ndimage import gaussian_filter
except ImportError:
    gaussian_filter = None

EPSILON = 1e-10
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "mirage_spectral"


@dataclass(frozen=True)
class MirageResult:
    layer: int
    weight_type: str
    s_spec_original: float
    s_spec_mirage: float
    survival_percent: float
    alpha: float
    sigma: float


def spectral_coherence_complex(matrix: np.ndarray) -> float:
    """S_spec for potentially complex matrices. Uses peak/mean ratio."""
    fft2d = np.fft.fft2(matrix)
    power = np.abs(fft2d) ** 2
    total = power.sum()
    if total < EPSILON:
        return 0.0
    peak = power.max()
    mean = power.mean()
    if mean < EPSILON:
        return 0.0
    return float(peak / mean)


def apply_thermodynamic_mirage(W: np.ndarray, alpha: float = 1.0, sigma: float = 3.0):
    """Apply mirage gradient via complex phase shift.

    1. Heat source: magnitude of weights
    2. Diffusion: Gaussian blur (sigma) simulates thermodynamic spread
    3. Mirage: W -> W * exp(i * alpha * heat_normalized)

    This maps the weight matrix into the complex plane using its own
    activation magnitude as the phase field. Connection to Layer 1:
    c = a * exp(i * phi) where a=weight, phi=heat.
    """
    if gaussian_filter is None:
        # Fallback: use a simple box blur
        from scipy.signal import fftconvolve

        kernel_size = max(1, int(sigma * 3))
        kernel = np.ones((kernel_size, kernel_size)) / (kernel_size**2)
        heat = fftconvolve(np.abs(W), kernel, mode="same")
    else:
        heat = gaussian_filter(np.abs(W), sigma=sigma)

    max_heat = heat.max()
    if max_heat < EPSILON:
        return W.astype(complex), np.zeros_like(W)

    heat_norm = (heat / max_heat) * (np.pi * alpha)
    W_mirage = W * np.exp(1j * heat_norm)

    return W_mirage, heat_norm


def find_qkv_weights(model, layer_idx: int) -> dict[str, np.ndarray]:
    """Extract Q, K, V weights from a transformer layer."""
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


def run_mirage_sweep(
    model_id: str = "distilbert-base-uncased",
    alpha: float = 1.0,
    sigma: float = 5.0,
    max_layers: int | None = None,
    token: str | None = None,
) -> dict:

    print(f"Loading model: {model_id}")
    kwargs = {"token": token} if token else {}
    try:
        from transformers import AutoModelForCausalLM

        model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    except Exception:
        from transformers import AutoModel

        model = AutoModel.from_pretrained(model_id, **kwargs)

    model.eval()
    n_layers = count_layers(model)
    if max_layers:
        n_layers = min(n_layers, max_layers)

    print(f"Layers: {n_layers}, Alpha: {alpha}, Sigma: {sigma}")

    results: list[MirageResult] = []

    for layer_idx in range(n_layers):
        qkv = find_qkv_weights(model, layer_idx)
        for wtype, W in qkv.items():
            s_orig = spectral_coherence_complex(W)
            W_mirage, _ = apply_thermodynamic_mirage(W, alpha=alpha, sigma=sigma)
            s_mirage = spectral_coherence_complex(W_mirage)
            survival = (s_mirage / s_orig * 100) if s_orig > EPSILON else 0.0

            results.append(
                MirageResult(
                    layer=layer_idx,
                    weight_type=wtype,
                    s_spec_original=s_orig,
                    s_spec_mirage=s_mirage,
                    survival_percent=survival,
                    alpha=alpha,
                    sigma=sigma,
                )
            )

            print(f"  L{layer_idx} {wtype}: orig={s_orig:.2f} mirage={s_mirage:.2f} survival={survival:.1f}%")

    # Summary
    summary = {}
    for wtype in ["Q", "K", "V"]:
        subset = [r for r in results if r.weight_type == wtype]
        if subset:
            summary[wtype] = {
                "mean_original": float(np.mean([r.s_spec_original for r in subset])),
                "mean_mirage": float(np.mean([r.s_spec_mirage for r in subset])),
                "mean_survival": float(np.mean([r.survival_percent for r in subset])),
            }

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "record_type": "mirage_spectral_mapping_v1",
        "model_id": model_id,
        "alpha": alpha,
        "sigma": sigma,
        "layers_analyzed": n_layers,
        "summary": summary,
        "results": [asdict(r) for r in results],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Mirage Spectral Mapping on transformer weights.")
    parser.add_argument("--model", default="distilbert-base-uncased")
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--sigma", type=float, default=5.0)
    parser.add_argument("--max-layers", type=int, default=None)
    parser.add_argument("--token-env", default="HF_TOKEN")
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    import os

    token = os.environ.get(args.token_env, "").strip() or None

    result = run_mirage_sweep(
        model_id=args.model,
        alpha=args.alpha,
        sigma=args.sigma,
        max_layers=args.max_layers,
        token=token,
    )

    output_path = args.output or str(
        DEFAULT_OUTPUT_ROOT / f"mirage-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"\nMirage Spectral Mapping complete: {output_path}")
    for wtype, stats in result["summary"].items():
        print(
            f"  {wtype}: orig={stats['mean_original']:.2f} mirage={stats['mean_mirage']:.2f} survival={stats['mean_survival']:.1f}%"
        )

    if args.json:
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

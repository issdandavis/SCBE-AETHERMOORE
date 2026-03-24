#!/usr/bin/env python3
"""Mirror Differential Telemetry — Applied to transformer attention weights.

From the SCBE math verification:
- M_w(u) = -u is a hyperbolic isometry (d_H preserved)
- L6 Breathing is the ONLY mirror-breaking transform in the 14-layer pipeline
- 13 of 14 layers are mirror-invariant

This script applies the same framework to actual Q, K, V weight matrices.

Three mirrors:
  M_w(W) = -W            (whole-weight mirror — negation)
  M_e(W) = W.T           (edge mirror — transpose = boundary flip)
  M_s(W) = W[::-1, :]    (row-order mirror — signal reversal)

For each: compute spectral coherence of original, mirrored, and cross-deltas.
The DELTA between mirrors reveals hidden structure the mirrors alone cannot show.

Origin: Issac Davis concept ("shapes have phases and mirrors of themselves as
wholes and as edges... the changes show the changes"), formalized through
Codex (Colab run on DistilBERT) and Claude (SCBE math verification).

Usage:
  # With Python that has torch + transformers:
  C:/Users/issda/Python312/python.exe scripts/mirror_differential_telemetry.py
  C:/Users/issda/Python312/python.exe scripts/mirror_differential_telemetry.py --model distilbert-base-uncased
  C:/Users/issda/Python312/python.exe scripts/mirror_differential_telemetry.py --model issdandavis/scbe-pivot-qwen-0.5b --json
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
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "mirror_differential"


@dataclass(frozen=True)
class MirrorProbe:
    s_spec: float
    energy_total: float


@dataclass(frozen=True)
class MirrorDifferential:
    delta_s_spec: float
    delta_mean: float
    delta_max: float


@dataclass(frozen=True)
class WeightMirrorReport:
    layer: int
    weight_type: str
    shape: list[int]
    original: MirrorProbe
    mirror_whole: MirrorProbe
    mirror_edge: MirrorProbe
    mirror_signal: MirrorProbe
    delta_whole_edge: MirrorDifferential
    delta_whole_signal: MirrorDifferential
    delta_edge_signal: MirrorDifferential
    whole_isometry_preserved: bool


def spectral_coherence_2d(W: np.ndarray) -> MirrorProbe:
    """S_spec via 2D FFT: peak power / total power."""
    fft2d = np.fft.fft2(W)
    power = np.abs(fft2d) ** 2
    total = float(power.sum())
    if total < EPSILON:
        return MirrorProbe(s_spec=0.0, energy_total=0.0)
    peak = float(power.max())
    return MirrorProbe(s_spec=peak / total, energy_total=total)


def mirror_whole(W: np.ndarray) -> np.ndarray:
    return -W


def mirror_edge(W: np.ndarray) -> np.ndarray:
    return W.T


def mirror_signal(W: np.ndarray) -> np.ndarray:
    return W[::-1, :]


def compute_delta(W_a: np.ndarray, W_b: np.ndarray) -> MirrorDifferential:
    delta = W_a - W_b
    probe = spectral_coherence_2d(delta)
    return MirrorDifferential(
        delta_s_spec=probe.s_spec,
        delta_mean=float(np.abs(delta).mean()),
        delta_max=float(np.abs(delta).max()),
    )


def analyze_weight_matrix(W: np.ndarray, layer: int, weight_type: str) -> WeightMirrorReport:
    Mw = mirror_whole(W)
    Me = mirror_edge(W)
    Ms = mirror_signal(W)

    orig = spectral_coherence_2d(W)
    p_mw = spectral_coherence_2d(Mw)
    p_me = spectral_coherence_2d(Me)
    p_ms = spectral_coherence_2d(Ms)

    return WeightMirrorReport(
        layer=layer,
        weight_type=weight_type,
        shape=list(W.shape),
        original=orig,
        mirror_whole=p_mw,
        mirror_edge=p_me,
        mirror_signal=p_ms,
        delta_whole_edge=compute_delta(Mw, Me),
        delta_whole_signal=compute_delta(Mw, Ms),
        delta_edge_signal=compute_delta(Me, Ms),
        whole_isometry_preserved=abs(p_mw.s_spec - orig.s_spec) < 0.001,
    )


def find_qkv_weights(model, layer_idx: int):
    """Extract Q, K, V weight tensors from a transformer layer.

    Supports multiple architectures: DistilBERT, BERT, Qwen2, GPT-2, LLaMA-style.
    """
    layer = None
    weights = {}

    # Try common layer access patterns
    if hasattr(model, "transformer") and hasattr(model.transformer, "layer"):
        layer = model.transformer.layer[layer_idx]
    elif hasattr(model, "encoder") and hasattr(model.encoder, "layer"):
        layer = model.encoder.layer[layer_idx]
    elif hasattr(model, "model") and hasattr(model.model, "layers"):
        layer = model.model.layers[layer_idx]

    if layer is None:
        return weights

    # DistilBERT style: attention.q_lin, attention.k_lin, attention.v_lin
    attn = getattr(layer, "attention", None)
    if attn:
        for name, attr in [("Q", "q_lin"), ("K", "k_lin"), ("V", "v_lin")]:
            proj = getattr(attn, attr, None)
            if proj and hasattr(proj, "weight"):
                weights[name] = proj.weight.detach().cpu().float().numpy()

    # BERT style: attention.self.query, attention.self.key, attention.self.value
    if not weights and attn:
        self_attn = getattr(attn, "self", None)
        if self_attn:
            for name, attr in [("Q", "query"), ("K", "key"), ("V", "value")]:
                proj = getattr(self_attn, attr, None)
                if proj and hasattr(proj, "weight"):
                    weights[name] = proj.weight.detach().cpu().float().numpy()

    # Qwen2 / LLaMA style: self_attn.q_proj, self_attn.k_proj, self_attn.v_proj
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


def run_mirror_analysis(
    model_id: str = "distilbert-base-uncased",
    max_layers: int | None = None,
    token: str | None = None,
) -> dict:
    import torch
    from transformers import AutoModel

    print(f"Loading model: {model_id}")
    kwargs = {"token": token} if token else {}
    try:
        model = AutoModel.from_pretrained(model_id, **kwargs)
    except Exception:
        from transformers import AutoModelForCausalLM

        model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)

    model.eval()
    n_layers = count_layers(model)
    if max_layers:
        n_layers = min(n_layers, max_layers)

    print(f"Layers: {n_layers}")

    # Noise baseline
    sample_weights = find_qkv_weights(model, 0)
    if not sample_weights:
        raise RuntimeError(f"Could not find Q/K/V weights in {model_id}")
    sample_shape = list(sample_weights.values())[0].shape
    noise_baseline = float(np.mean([spectral_coherence_2d(np.random.randn(*sample_shape)).s_spec for _ in range(10)]))

    print(f"Weight shape: {sample_shape}, Noise baseline: {noise_baseline:.6f}")
    print()

    reports: list[WeightMirrorReport] = []

    for layer_idx in range(n_layers):
        qkv = find_qkv_weights(model, layer_idx)
        for wtype, W in qkv.items():
            report = analyze_weight_matrix(W, layer_idx, wtype)
            reports.append(report)
            ratio = report.original.s_spec / noise_baseline if noise_baseline > 0 else 0
            iso = "Y" if report.whole_isometry_preserved else "N"
            print(
                f"  L{layer_idx} {wtype}: S={report.original.s_spec:.4f} ({ratio:.2f}x noise) "
                f"Me={report.mirror_edge.s_spec:.4f} Ms={report.mirror_signal.s_spec:.4f} "
                f"D_we={report.delta_whole_edge.delta_s_spec:.4f} iso={iso}"
            )

    # Aggregate by weight type
    summary = {}
    for wtype in ["Q", "K", "V"]:
        subset = [r for r in reports if r.weight_type == wtype]
        if not subset:
            continue
        summary[wtype] = {
            "count": len(subset),
            "mean_s_spec": float(np.mean([r.original.s_spec for r in subset])),
            "mean_s_spec_vs_noise": (
                float(np.mean([r.original.s_spec for r in subset])) / noise_baseline if noise_baseline > 0 else 0
            ),
            "mean_edge_s_spec": float(np.mean([r.mirror_edge.s_spec for r in subset])),
            "mean_signal_s_spec": float(np.mean([r.mirror_signal.s_spec for r in subset])),
            "mean_delta_we": float(np.mean([r.delta_whole_edge.delta_s_spec for r in subset])),
            "mean_delta_ws": float(np.mean([r.delta_whole_signal.delta_s_spec for r in subset])),
            "mean_delta_es": float(np.mean([r.delta_edge_signal.delta_s_spec for r in subset])),
            "all_isometries_preserved": all(r.whole_isometry_preserved for r in subset),
        }

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "record_type": "mirror_differential_telemetry_v1",
        "model_id": model_id,
        "weight_shape": list(sample_shape),
        "noise_baseline": noise_baseline,
        "layers_analyzed": n_layers,
        "total_weights_analyzed": len(reports),
        "summary": summary,
        "reports": [asdict(r) for r in reports],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Mirror Differential Telemetry on transformer weights.")
    parser.add_argument("--model", default="distilbert-base-uncased")
    parser.add_argument("--max-layers", type=int, default=None)
    parser.add_argument("--token-env", default="HF_TOKEN")
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    import os

    token = os.environ.get(args.token_env, "").strip() or None

    result = run_mirror_analysis(
        model_id=args.model,
        max_layers=args.max_layers,
        token=token,
    )

    output_path = args.output or str(
        DEFAULT_OUTPUT_ROOT / f"mirror-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"\nMirror Differential Telemetry complete: {output_path}")
    for wtype, stats in result["summary"].items():
        print(
            f"  {wtype}: S_spec={stats['mean_s_spec']:.4f} ({stats['mean_s_spec_vs_noise']:.2f}x noise), D_we={stats['mean_delta_we']:.4f}, iso={'YES' if stats['all_isometries_preserved'] else 'NO'}"
        )

    if args.json:
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

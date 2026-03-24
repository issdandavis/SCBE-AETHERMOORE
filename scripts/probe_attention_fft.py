#!/usr/bin/env python3
"""Probe transformer attention tensors with the minimal mirror-problem FFT metrics."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from src.minimal.mirror_problem_fft import (
    compare_attention_to_controls,
    make_banded_control,
    make_random_control,
    make_uniform_control,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "attention_fft"
DEFAULT_MODEL_ID = "issdandavis/scbe-pivot-qwen-0.5b"
DEFAULT_PROMPT = "Explain why governed attention might differ from learned attention."
DEFAULT_MAX_LENGTH = 128
DEFAULT_PROMPT_SET = [
    "The quantum field oscillates at harmonic frequencies.",
    "Stars transmit information between nodes across the galaxy.",
    "Attention mechanisms distribute weights based on semantic intent.",
    "The game itself is the problem and the solution.",
    "You can only eat the meals you eat.",
    "Multiple Go boards with different weight distributions.",
    "Gravity times both internal and external forces at micro and macro scales.",
    "Shapes and stuff make things and stuff.",
]


@dataclass(frozen=True)
class ModelBundle:
    model: Any
    tokenizer: Any
    model_id: str
    source: str
    device: str
    dtype: str
    base_model_id: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip())
    slug = re.sub(r"-+", "-", slug).strip("-.")
    return slug or "model"


def parse_index_list(raw: str) -> list[int] | None:
    cleaned = str(raw or "").strip()
    if not cleaned:
        return None
    values: list[int] = []
    for chunk in cleaned.split(","):
        part = chunk.strip()
        if not part:
            continue
        values.append(int(part))
    return values or None


def resolve_prompt(inline_prompt: str | None = None, prompt_file: str | None = None) -> str:
    if prompt_file:
        text = Path(prompt_file).read_text(encoding="utf-8").strip()
        if text:
            return text
    if inline_prompt and inline_prompt.strip():
        return inline_prompt.strip()
    return DEFAULT_PROMPT


def _load_prompt_list_file(path: str) -> list[str]:
    raw = Path(path).read_text(encoding="utf-8").strip()
    if not raw:
        return []
    if raw.startswith("["):
        payload = json.loads(raw)
        if not isinstance(payload, list):
            raise ValueError("prompt list JSON must be an array of strings")
        return [str(item).strip() for item in payload if str(item).strip()]
    return [line.strip() for line in raw.splitlines() if line.strip()]


def resolve_prompts(
    inline_prompt: str | None = None,
    *,
    prompt_file: str | None = None,
    prompt_list_file: str | None = None,
    use_default_prompt_set: bool = False,
    max_prompts: int | None = None,
) -> list[str]:
    if prompt_list_file:
        prompts = _load_prompt_list_file(prompt_list_file)
    elif use_default_prompt_set:
        prompts = list(DEFAULT_PROMPT_SET)
    else:
        prompts = [resolve_prompt(inline_prompt, prompt_file)]
    if max_prompts is not None:
        return prompts[: max(0, max_prompts)]
    return prompts


def resolve_token(token_env: str) -> str | None:
    for key in [token_env, "HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGINGFACE_API_KEY"]:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def select_indices(total: int, explicit: list[int] | None = None, max_items: int | None = None) -> list[int]:
    if explicit:
        return [index for index in explicit if 0 <= index < total]
    indices = list(range(total))
    if max_items is not None:
        return indices[: max(0, max_items)]
    return indices


def _lazy_hf_imports() -> tuple[Any, Any, Any, Any]:
    import torch
    from huggingface_hub import hf_hub_download  # type: ignore[import-untyped]
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not getattr(torch, "__version__", None) or not hasattr(torch, "nn"):
        raise RuntimeError("PyTorch runtime is incomplete in this interpreter. Use a runtime with torch.nn available.")

    return torch, hf_hub_download, AutoModelForCausalLM, AutoTokenizer


def _lazy_peft_model() -> Any:
    from peft import PeftModel

    return PeftModel


def _choose_device(torch_mod: Any, requested: str) -> str:
    if requested and requested != "auto":
        return requested
    cuda = getattr(torch_mod, "cuda", None)
    if cuda is not None and hasattr(cuda, "is_available") and cuda.is_available():
        return "cuda"
    return "cpu"


def _model_dtype_name(model: Any) -> str:
    try:
        dtype = next(model.parameters()).dtype
        return str(dtype).replace("torch.", "")
    except Exception:
        return "unknown"


def _resolve_torch_dtype(torch_mod: Any, dtype_name: str | None) -> Any:
    cleaned = str(dtype_name or "").strip().casefold()
    if not cleaned or cleaned == "auto":
        return "auto"
    attr_name = cleaned
    if not hasattr(torch_mod, attr_name):
        raise ValueError(f"Unsupported torch dtype: {dtype_name}")
    return getattr(torch_mod, attr_name)


def _load_direct_model(
    model_id: str,
    *,
    token: str | None,
    device: str,
    attn_implementation: str | None,
    torch_dtype_name: str | None,
) -> ModelBundle:
    torch_mod, _hf_hub_download, AutoModelForCausalLM, AutoTokenizer = _lazy_hf_imports()
    model_kwargs: dict[str, Any] = {
        "token": token,
        "torch_dtype": _resolve_torch_dtype(torch_mod, torch_dtype_name),
        "low_cpu_mem_usage": True,
    }
    if attn_implementation:
        model_kwargs["attn_implementation"] = attn_implementation

    try:
        model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
    except TypeError:
        model_kwargs.pop("attn_implementation", None)
        model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model.to(device)
    model.eval()
    return ModelBundle(
        model=model,
        tokenizer=tokenizer,
        model_id=model_id,
        source="direct",
        device=device,
        dtype=_model_dtype_name(model),
    )


def _load_adapter_model(
    model_id: str,
    *,
    token: str | None,
    device: str,
    attn_implementation: str | None,
    torch_dtype_name: str | None,
) -> ModelBundle:
    torch_mod, hf_hub_download, AutoModelForCausalLM, AutoTokenizer = _lazy_hf_imports()
    PeftModel = _lazy_peft_model()

    if not token:
        raise RuntimeError("Adapter probing requires HF_TOKEN or equivalent env var.")

    adapter_config_path = hf_hub_download(repo_id=model_id, filename="adapter_config.json", token=token)
    adapter_config = json.loads(Path(adapter_config_path).read_text(encoding="utf-8"))
    configured_base_model = str(adapter_config.get("base_model_name_or_path", "")).strip()
    if not configured_base_model:
        raise RuntimeError(f"Adapter repo does not define base_model_name_or_path: {model_id}")

    base_candidates: list[str] = [configured_base_model]
    lowered = configured_base_model.casefold()
    if "qwen2.5-0.5b" in lowered and "qwen/qwen2.5-0.5b-instruct" not in lowered:
        base_candidates.append("Qwen/Qwen2.5-0.5B-Instruct")

    model_kwargs: dict[str, Any] = {
        "token": token,
        "torch_dtype": _resolve_torch_dtype(torch_mod, torch_dtype_name),
        "low_cpu_mem_usage": True,
    }
    if attn_implementation:
        model_kwargs["attn_implementation"] = attn_implementation
    base_model = None
    selected_base_model = ""
    base_errors: list[str] = []
    for candidate in base_candidates:
        try:
            try:
                base_model = AutoModelForCausalLM.from_pretrained(candidate, **model_kwargs)
            except TypeError:
                retry_kwargs = dict(model_kwargs)
                retry_kwargs.pop("attn_implementation", None)
                base_model = AutoModelForCausalLM.from_pretrained(candidate, **retry_kwargs)
            selected_base_model = candidate
            break
        except Exception as exc:
            base_errors.append(f"{candidate}: {exc}")
    if base_model is None:
        joined = " | ".join(base_errors) if base_errors else "no base model candidates were available"
        raise RuntimeError(f"Unable to load a base model for attention probing: {joined}")
    model = PeftModel.from_pretrained(base_model, model_id, token=token)
    tokenizer = None
    for candidate in [model_id, selected_base_model]:
        try:
            tokenizer = AutoTokenizer.from_pretrained(candidate, token=token)
            break
        except Exception:
            continue
    if tokenizer is None:
        raise RuntimeError(f"Unable to load tokenizer for model {model_id}")
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model.to(device)
    model.eval()
    return ModelBundle(
        model=model,
        tokenizer=tokenizer,
        model_id=model_id,
        source="peft_adapter",
        device=device,
        dtype=_model_dtype_name(model),
        base_model_id=selected_base_model,
    )


def load_model_bundle(
    model_id: str,
    *,
    token: str | None,
    requested_device: str = "auto",
    attn_implementation: str | None = None,
    torch_dtype_name: str | None = None,
) -> ModelBundle:
    torch_mod, _hf_hub_download, _AutoModelForCausalLM, _AutoTokenizer = _lazy_hf_imports()
    device = _choose_device(torch_mod, requested_device)

    direct_error = None
    try:
        return _load_direct_model(
            model_id,
            token=token,
            device=device,
            attn_implementation=attn_implementation,
            torch_dtype_name=torch_dtype_name,
        )
    except Exception as exc:
        direct_error = exc

    try:
        return _load_adapter_model(
            model_id,
            token=token,
            device=device,
            attn_implementation=attn_implementation,
            torch_dtype_name=torch_dtype_name,
        )
    except Exception as adapter_exc:
        raise RuntimeError(
            f"Unable to load attention probe model '{model_id}'. "
            f"Direct load failed: {direct_error}. Adapter load failed: {adapter_exc}"
        ) from adapter_exc


def encode_prompt(tokenizer: Any, prompt: str, *, max_length: int) -> dict[str, Any]:
    if getattr(tokenizer, "chat_template", None):
        prompt = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=False,
        )
    encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)
    return dict(encoded)


def extract_attentions(bundle: ModelBundle, prompt: str, *, max_length: int) -> dict[str, Any]:
    torch_mod, _hf_hub_download, _AutoModelForCausalLM, _AutoTokenizer = _lazy_hf_imports()

    encoded = encode_prompt(bundle.tokenizer, prompt, max_length=max_length)
    device_inputs: dict[str, Any] = {}
    for key, value in encoded.items():
        if hasattr(value, "to"):
            device_inputs[key] = value.to(bundle.device)
        else:
            device_inputs[key] = value

    with torch_mod.no_grad():
        outputs = bundle.model(
            **device_inputs,
            output_attentions=True,
            use_cache=False,
            return_dict=True,
        )
    attentions = getattr(outputs, "attentions", None)
    if not attentions:
        raise RuntimeError("Model forward pass did not return attention tensors.")

    input_ids = device_inputs.get("input_ids")
    sequence_length = int(input_ids.shape[-1]) if hasattr(input_ids, "shape") else None
    token_list: list[str] = []
    if input_ids is not None:
        try:
            token_list = bundle.tokenizer.convert_ids_to_tokens(input_ids[0].detach().cpu().tolist())
        except Exception:
            token_list = []

    return {
        "attentions": attentions,
        "sequence_length": sequence_length,
        "tokens": token_list,
        "token_count": len(token_list),
        "prompt": prompt,
    }


def extract_hidden_matrix(bundle: ModelBundle, prompt: str, *, max_length: int) -> dict[str, Any]:
    torch_mod, _hf_hub_download, _AutoModelForCausalLM, _AutoTokenizer = _lazy_hf_imports()

    encoded = encode_prompt(bundle.tokenizer, prompt, max_length=max_length)
    device_inputs: dict[str, Any] = {}
    for key, value in encoded.items():
        if hasattr(value, "to"):
            device_inputs[key] = value.to(bundle.device)
        else:
            device_inputs[key] = value

    with torch_mod.no_grad():
        outputs = bundle.model(
            **device_inputs,
            output_hidden_states=True,
            use_cache=False,
            return_dict=True,
        )

    hidden_states = getattr(outputs, "hidden_states", None)
    if hidden_states:
        hidden_matrix = hidden_states[-1][0].detach().cpu().double().numpy()
    elif hasattr(outputs, "last_hidden_state"):
        hidden_matrix = outputs.last_hidden_state[0].detach().cpu().double().numpy()
    else:
        raise RuntimeError("Model forward pass did not return hidden states.")

    input_ids = device_inputs.get("input_ids")
    token_list: list[str] = []
    if input_ids is not None:
        try:
            token_list = bundle.tokenizer.convert_ids_to_tokens(input_ids[0].detach().cpu().tolist())
        except Exception:
            token_list = []

    return {
        "hidden_matrix": hidden_matrix,
        "matrix_shape": list(hidden_matrix.shape),
        "sequence_length": int(hidden_matrix.shape[0]),
        "feature_count": int(hidden_matrix.shape[1]) if hidden_matrix.ndim == 2 else 0,
        "tokens": token_list,
        "token_count": len(token_list),
        "prompt": prompt,
    }


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


def _build_head_report(matrix: np.ndarray, *, mode: str) -> dict[str, Any]:
    comparison = compare_attention_to_controls(matrix, mode=mode)
    candidate = comparison.candidate
    banded_gap = abs(candidate.s_spec - comparison.banded_control.s_spec)
    random_gap = abs(candidate.s_spec - comparison.random_control.s_spec)
    return {
        "matrix_shape": list(matrix.shape),
        "candidate": asdict(candidate),
        "controls": {
            "uniform": asdict(comparison.uniform_control),
            "banded": asdict(comparison.banded_control),
            "random": asdict(comparison.random_control),
        },
        "banded_gap": banded_gap,
        "random_gap": random_gap,
        "closer_to_banded_than_random": banded_gap < random_gap,
    }


def analyze_attention_stack(
    attentions: list[Any] | tuple[Any, ...],
    *,
    mode: str = "flatten",
    layer_indices: list[int] | None = None,
    head_indices: list[int] | None = None,
    max_layers: int | None = None,
    max_heads: int | None = None,
) -> dict[str, Any]:
    selected_layers = select_indices(len(attentions), layer_indices, max_layers)
    layer_reports: list[dict[str, Any]] = []
    s_specs: list[float] = []
    peak_ratios: list[float] = []
    entropies: list[float] = []
    banded_votes = 0

    for layer_index in selected_layers:
        heads = _tensor_to_heads(attentions[layer_index])
        selected_heads = select_indices(heads.shape[0], head_indices, max_heads)
        head_reports: list[dict[str, Any]] = []

        for head_index in selected_heads:
            matrix = heads[head_index]
            head_report = _build_head_report(matrix, mode=mode)
            candidate = head_report["candidate"]
            if head_report["closer_to_banded_than_random"]:
                banded_votes += 1
            s_specs.append(candidate["s_spec"])
            peak_ratios.append(candidate["peak_ratio"])
            entropies.append(candidate["spectral_entropy"])
            head_reports.append({"head_index": head_index, **head_report})

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
        "average_s_spec": float(np.mean(s_specs)) if s_specs else 0.0,
        "average_peak_ratio": float(np.mean(peak_ratios)) if peak_ratios else 0.0,
        "average_spectral_entropy": float(np.mean(entropies)) if entropies else 0.0,
        "banded_vote_rate": (banded_votes / total_heads) if total_heads else 0.0,
        "mode": mode,
        "layers": layer_reports,
    }


def analyze_prompt_batch(
    extractions: list[dict[str, Any]],
    *,
    mode: str = "flatten",
    layer_indices: list[int] | None = None,
    head_indices: list[int] | None = None,
    max_layers: int | None = None,
    max_heads: int | None = None,
) -> dict[str, Any]:
    if not extractions:
        raise ValueError("at least one extraction is required")

    prompt_reports: list[dict[str, Any]] = []
    aggregate: dict[tuple[int, int], dict[str, Any]] = {}

    for extraction in extractions:
        analysis = analyze_attention_stack(
            extraction["attentions"],
            mode=mode,
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
            layer_index = layer["layer_index"]
            for head in layer["heads"]:
                head_index = head["head_index"]
                key = (layer_index, head_index)
                bucket = aggregate.setdefault(
                    key,
                    {
                        "layer_index": layer_index,
                        "head_index": head_index,
                        "matrix_shape": head["matrix_shape"],
                        "s_specs": [],
                        "peak_ratios": [],
                        "entropies": [],
                        "banded_votes": 0,
                        "banded_gaps": [],
                        "random_gaps": [],
                    },
                )
                bucket["s_specs"].append(head["candidate"]["s_spec"])
                bucket["peak_ratios"].append(head["candidate"]["peak_ratio"])
                bucket["entropies"].append(head["candidate"]["spectral_entropy"])
                bucket["banded_gaps"].append(head["banded_gap"])
                bucket["random_gaps"].append(head["random_gap"])
                bucket["banded_votes"] += 1 if head["closer_to_banded_than_random"] else 0

    layer_map: dict[int, list[dict[str, Any]]] = {}
    all_s_specs: list[float] = []
    all_peak_ratios: list[float] = []
    all_entropies: list[float] = []
    total_votes = 0

    for (_layer_index, _head_index), bucket in sorted(aggregate.items()):
        all_s_specs.extend(bucket["s_specs"])
        all_peak_ratios.extend(bucket["peak_ratios"])
        all_entropies.extend(bucket["entropies"])
        total_votes += bucket["banded_votes"]
        head_report = {
            "head_index": bucket["head_index"],
            "matrix_shape": bucket["matrix_shape"],
            "prompt_count": len(bucket["s_specs"]),
            "candidate_mean": {
                "s_spec": float(np.mean(bucket["s_specs"])),
                "peak_ratio": float(np.mean(bucket["peak_ratios"])),
                "spectral_entropy": float(np.mean(bucket["entropies"])),
            },
            "banded_gap_mean": float(np.mean(bucket["banded_gaps"])),
            "random_gap_mean": float(np.mean(bucket["random_gaps"])),
            "closer_to_banded_rate": bucket["banded_votes"] / len(bucket["s_specs"]),
        }
        layer_map.setdefault(bucket["layer_index"], []).append(head_report)

    layers = [
        {
            "layer_index": layer_index,
            "head_count": len(heads),
            "heads": heads,
        }
        for layer_index, heads in sorted(layer_map.items())
    ]
    total_heads = sum(layer["head_count"] for layer in layers)

    return {
        "prompt_count": len(prompt_reports),
        "layer_count": len(layers),
        "head_count": total_heads,
        "average_s_spec": float(np.mean(all_s_specs)) if all_s_specs else 0.0,
        "average_peak_ratio": float(np.mean(all_peak_ratios)) if all_peak_ratios else 0.0,
        "average_spectral_entropy": float(np.mean(all_entropies)) if all_entropies else 0.0,
        "banded_vote_rate": (total_votes / len(all_s_specs)) if all_s_specs else 0.0,
        "mode": mode,
        "layers": layers,
        "prompt_reports": prompt_reports,
    }


def analyze_precision_drift(
    model_id: str,
    prompts: list[str],
    *,
    token: str | None,
    requested_device: str,
    attn_implementation: str | None,
    max_length: int,
    dtype_a: str,
    dtype_b: str,
    mode: str,
) -> dict[str, Any]:
    if not prompts:
        raise ValueError("at least one prompt is required for precision drift analysis")

    bundle_a = load_model_bundle(
        model_id,
        token=token,
        requested_device=requested_device,
        attn_implementation=attn_implementation,
        torch_dtype_name=dtype_a,
    )
    bundle_b = load_model_bundle(
        model_id,
        token=token,
        requested_device=requested_device,
        attn_implementation=attn_implementation,
        torch_dtype_name=dtype_b,
    )

    prompt_reports: list[dict[str, Any]] = []
    s_specs: list[float] = []
    peak_ratios: list[float] = []
    spectral_entropies: list[float] = []
    banded_votes = 0

    for prompt in prompts:
        hidden_a = extract_hidden_matrix(bundle_a, prompt, max_length=max_length)
        hidden_b = extract_hidden_matrix(bundle_b, prompt, max_length=max_length)
        drift_matrix = hidden_b["hidden_matrix"] - hidden_a["hidden_matrix"]
        head_report = _build_head_report(drift_matrix, mode=mode)
        s_specs.append(head_report["candidate"]["s_spec"])
        peak_ratios.append(head_report["candidate"]["peak_ratio"])
        spectral_entropies.append(head_report["candidate"]["spectral_entropy"])
        banded_votes += 1 if head_report["closer_to_banded_than_random"] else 0
        prompt_reports.append(
            {
                "prompt": prompt,
                "matrix_shape": list(drift_matrix.shape),
                "sequence_length": hidden_a["sequence_length"],
                "feature_count": hidden_a["feature_count"],
                "candidate": head_report["candidate"],
                "controls": head_report["controls"],
                "banded_gap": head_report["banded_gap"],
                "random_gap": head_report["random_gap"],
                "closer_to_banded_than_random": head_report["closer_to_banded_than_random"],
                "max_abs_drift": float(np.max(np.abs(drift_matrix))),
                "mean_abs_drift": float(np.mean(np.abs(drift_matrix))),
            }
        )

    return {
        "prompt_count": len(prompt_reports),
        "mode": mode,
        "dtype_a": dtype_a,
        "dtype_b": dtype_b,
        "device": requested_device,
        "average_s_spec": float(np.mean(s_specs)) if s_specs else 0.0,
        "average_peak_ratio": float(np.mean(peak_ratios)) if peak_ratios else 0.0,
        "average_spectral_entropy": float(np.mean(spectral_entropies)) if spectral_entropies else 0.0,
        "closer_to_banded_rate": (banded_votes / len(prompt_reports)) if prompt_reports else 0.0,
        "max_abs_drift": float(max(report["max_abs_drift"] for report in prompt_reports)),
        "mean_abs_drift": float(np.mean([report["mean_abs_drift"] for report in prompt_reports])),
        "prompt_reports": prompt_reports,
        "source_models": {
            "a": {
                "source": bundle_a.source,
                "device": bundle_a.device,
                "dtype": bundle_a.dtype,
                "base_model_id": bundle_a.base_model_id,
            },
            "b": {
                "source": bundle_b.source,
                "device": bundle_b.device,
                "dtype": bundle_b.dtype,
                "base_model_id": bundle_b.base_model_id,
            },
        },
    }


def build_control_matrix(kind: str, size: int, seed: int = 7) -> np.ndarray:
    if kind == "uniform":
        return make_uniform_control(size)
    if kind == "banded":
        return make_banded_control(size)
    if kind == "random":
        return make_random_control(size, seed=seed)
    raise ValueError(f"Unknown control kind: {kind}")


def analyze_control_matrix(kind: str, *, size: int, mode: str, seed: int = 7) -> dict[str, Any]:
    matrix = build_control_matrix(kind, size, seed=seed)
    comparison = compare_attention_to_controls(matrix, mode=mode)
    candidate = comparison.candidate
    banded_gap = abs(candidate.s_spec - comparison.banded_control.s_spec)
    random_gap = abs(candidate.s_spec - comparison.random_control.s_spec)
    return {
        "control_kind": kind,
        "size": size,
        "mode": mode,
        "candidate": asdict(candidate),
        "controls": {
            "uniform": asdict(comparison.uniform_control),
            "banded": asdict(comparison.banded_control),
            "random": asdict(comparison.random_control),
        },
        "banded_gap": banded_gap,
        "random_gap": random_gap,
        "closer_to_banded_than_random": banded_gap < random_gap,
    }


def write_report(report: dict[str, Any], *, output_root: Path, label: str) -> Path:
    bundle_dir = output_root / f"{safe_slug(label)}-{utc_stamp()}"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    path = bundle_dir / "attention_fft_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def build_report(
    *,
    model_id: str | None = None,
    bundle: ModelBundle | None = None,
    extraction: dict[str, Any] | None = None,
    analysis: dict[str, Any],
    prompt: str | None = None,
    token_env: str,
    control_kind: str | None = None,
    precision_drift: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "generated_at_utc": utc_now(),
        "record_type": "attention_fft_probe_v1",
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
    if precision_drift:
        report["precision_drift"] = precision_drift
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe attention tensors with the mirror-problem FFT metrics.")
    parser.add_argument("prompt", nargs="?", default="", help="Prompt to run through the model forward pass.")
    parser.add_argument("--prompt-file", default="", help="Optional UTF-8 file containing the prompt.")
    parser.add_argument(
        "--prompt-list-file", default="", help="Optional file with one prompt per line or a JSON string array."
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
    parser.add_argument("--precision-drift", action="store_true")
    parser.add_argument("--drift-device", default="cpu")
    parser.add_argument("--drift-dtype-a", default="float32")
    parser.add_argument("--drift-dtype-b", default="float64")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = args.mode
    output_root = Path(args.output_root)

    if args.control:
        analysis = analyze_control_matrix(args.control, size=args.size, mode=mode, seed=args.seed)
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
            mode=mode,
            layer_indices=parse_index_list(args.layer_indices),
            head_indices=parse_index_list(args.head_indices),
            max_layers=args.max_layers,
            max_heads=args.max_heads,
        )
        precision_drift = None
        if args.precision_drift:
            precision_drift = analyze_precision_drift(
                args.model_id,
                prompts,
                token=token,
                requested_device=args.drift_device,
                attn_implementation=args.attn_implementation or None,
                max_length=args.max_length,
                dtype_a=args.drift_dtype_a,
                dtype_b=args.drift_dtype_b,
                mode=mode,
            )
        report = build_report(
            model_id=args.model_id,
            bundle=bundle,
            extraction=extractions[0],
            analysis=analysis,
            prompt=prompts[0] if len(prompts) == 1 else "",
            token_env=args.token_env,
            precision_drift=precision_drift,
        )
        report["prompt_count"] = len(prompts)
        if len(prompts) > 1:
            report["prompt_set_preview"] = prompts[: min(5, len(prompts))]
        artifact_path = write_report(report, output_root=output_root, label=args.model_id)

    payload = {**report, "artifact_path": str(artifact_path)}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Attention FFT probe complete: {artifact_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

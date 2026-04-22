from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AdapterResolution:
    run_dir: Path
    adapter_dir: Path
    source: str


FINAL_FILES = {
    "adapter_config.json",
    "adapter_model.safetensors",
    "chat_template.jinja",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "added_tokens.json",
    "generation_config.json",
    "README.md",
}


def checkpoint_dirs(run_dir: Path) -> list[Path]:
    if not run_dir.exists():
        return []
    rows: list[tuple[int, Path]] = []
    for entry in run_dir.iterdir():
        if not entry.is_dir() or not entry.name.startswith("checkpoint-"):
            continue
        try:
            step = int(entry.name.split("checkpoint-", 1)[1])
        except ValueError:
            continue
        if (entry / "adapter_model.safetensors").exists():
            rows.append((step, entry))
    return [path for _, path in sorted(rows)]


def latest_checkpoint_dir(run_dir: Path) -> Path | None:
    checkpoints = checkpoint_dirs(run_dir)
    return checkpoints[-1] if checkpoints else None


def best_available_adapter_dir(run_dir: Path) -> AdapterResolution | None:
    final_dir = run_dir / "lora_final"
    if (final_dir / "adapter_model.safetensors").exists():
        return AdapterResolution(run_dir=run_dir, adapter_dir=final_dir, source="lora_final")

    checkpoint_dir = latest_checkpoint_dir(run_dir)
    if checkpoint_dir is not None:
        return AdapterResolution(run_dir=run_dir, adapter_dir=checkpoint_dir, source=checkpoint_dir.name)

    return None


def resolve_run_alias(run_dir: Path) -> Path | None:
    if run_dir.exists():
        return run_dir
    parent = run_dir.parent
    if not parent.exists():
        return None
    candidates: list[tuple[int, float, Path]] = []
    for entry in parent.iterdir():
        if not entry.is_dir():
            continue
        if entry.name == run_dir.name or entry.name.startswith(run_dir.name + "-") or run_dir.name.startswith(entry.name + "-"):
            resolution = best_available_adapter_dir(entry)
            score = 2 if resolution and resolution.source == "lora_final" else 1 if resolution else 0
            candidates.append((score, entry.stat().st_mtime, entry))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1], item[2].name))
    return candidates[-1][2]


def resolve_best_available_adapter(path_like: Path) -> AdapterResolution | None:
    if path_like.is_dir() and (path_like / "adapter_model.safetensors").exists():
        return AdapterResolution(run_dir=path_like.parent, adapter_dir=path_like, source=path_like.name)

    resolved_run = resolve_run_alias(path_like)
    if resolved_run is None:
        return None
    return best_available_adapter_dir(resolved_run)


def materialize_final_adapter(run_dir: Path, *, source_dir: Path | None = None, overwrite: bool = False) -> Path:
    resolution = best_available_adapter_dir(run_dir) if source_dir is None else AdapterResolution(run_dir, source_dir, source_dir.name)
    if resolution is None:
        raise FileNotFoundError(f"No adapter checkpoint available under {run_dir}")

    final_dir = run_dir / "lora_final"
    if final_dir.exists():
        if not overwrite:
            return final_dir
        shutil.rmtree(final_dir)
    temp_dir = run_dir / "lora_final.__tmp__"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    for item in resolution.adapter_dir.iterdir():
        if not item.is_file():
            continue
        if item.name not in FINAL_FILES and not item.name.endswith((".json", ".jinja")):
            continue
        shutil.copy2(item, temp_dir / item.name)

    report = {
        "materialized_from": str(resolution.adapter_dir.resolve()),
        "source": resolution.source,
        "final_dir": str(final_dir.resolve()),
    }
    (temp_dir / "recovery_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    temp_dir.replace(final_dir)
    return final_dir

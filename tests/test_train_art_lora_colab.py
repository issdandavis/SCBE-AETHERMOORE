from __future__ import annotations

import json
from pathlib import Path

from scripts.train_art_lora_colab import (
    build_config,
    build_notebook,
    build_training_plan,
    load_training_entries,
    merged_quality_weights,
    parse_quality_overrides,
    render_report,
)


def write_metadata(dataset_dir: Path, rows: list[dict[str, str]]) -> None:
    metadata_path = dataset_dir / "metadata.jsonl"
    metadata_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_build_training_plan_uses_quality_weights_and_ignores_missing_files(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "art-style-lora"
    dataset_dir.mkdir()
    (dataset_dir / "anchor.png").write_bytes(b"anchor")
    (dataset_dir / "good.png").write_bytes(b"good")
    write_metadata(
        dataset_dir,
        [
            {"file_name": "anchor.png", "text": "anchor ref", "source": "ref", "quality": "anchor"},
            {"file_name": "good.png", "text": "good panel", "source": "panel", "quality": "good"},
            {"file_name": "missing.png", "text": "missing panel", "source": "panel", "quality": "hero"},
        ],
    )

    weights = merged_quality_weights()
    entries = load_training_entries(dataset_dir, weights)
    plan = build_training_plan(
        entries,
        train_batch_size=1,
        gradient_accumulation_steps=2,
        target_effective_epochs=10,
        quality_weights=weights,
    )

    assert plan["usable_entry_count"] == 2
    assert plan["missing_files"] == ["missing.png"]
    assert plan["weighted_example_count"] == 8
    assert plan["recommended_max_train_steps"] == 40
    assert plan["quality_breakdown"][0]["quality"] == "anchor"
    assert plan["quality_breakdown"][0]["weighted_examples"] == 5


def test_build_notebook_writes_weighted_dataset_prep_and_training_command(tmp_path: Path) -> None:
    weights = merged_quality_weights()
    dataset_dir = tmp_path / "art-style-lora"
    dataset_dir.mkdir()
    (dataset_dir / "anchor.png").write_bytes(b"anchor")
    write_metadata(
        dataset_dir,
        [{"file_name": "anchor.png", "text": "anchor ref", "source": "ref", "quality": "anchor"}],
    )
    entries = load_training_entries(dataset_dir, weights)
    plan = build_training_plan(
        entries,
        train_batch_size=1,
        gradient_accumulation_steps=4,
        target_effective_epochs=12,
        quality_weights=weights,
    )

    class Args:
        base_model = "black-forest-labs/FLUX.1-schnell"
        colab_dataset_dir = "training-data/art-style-lora"
        prepared_dataset_dir = "training-data/art-style-lora-weighted"
        output_dir = "six-tongues-lora-output"
        hub_model_id = "issdandavis/six-tongues-art-lora"
        trigger_word = "sixtongues_style"
        lora_rank = 16
        lora_alpha = 16
        learning_rate = 1e-4
        lr_scheduler = "constant"
        train_batch_size = 1
        gradient_accumulation_steps = 4
        max_train_steps = None
        save_steps = None
        resolution = 1024
        seed = 42
        eval_num_inference_steps = 4
        eval_guidance_scale = 0.0

    config = build_config(Args(), plan, weights)
    notebook_path = tmp_path / "six_tongues_lora_training.ipynb"
    build_notebook(notebook_path, config=config, plan=plan)
    notebook_text = notebook_path.read_text(encoding="utf-8")

    assert "weighted_manifest.jsonl" in notebook_text
    assert "train_dreambooth_lora_flux.py" in notebook_text
    assert "art-style-lora-weighted" in notebook_text


def test_render_report_mentions_shared_trigger_and_weighted_examples(tmp_path: Path) -> None:
    weights = merged_quality_weights(parse_quality_overrides(["anchor=6"]))
    dataset_dir = tmp_path / "art-style-lora"
    dataset_dir.mkdir()
    (dataset_dir / "anchor.png").write_bytes(b"anchor")
    write_metadata(
        dataset_dir,
        [{"file_name": "anchor.png", "text": "anchor ref", "source": "ref", "quality": "anchor"}],
    )
    entries = load_training_entries(dataset_dir, weights)
    plan = build_training_plan(
        entries,
        train_batch_size=1,
        gradient_accumulation_steps=1,
        target_effective_epochs=10,
        quality_weights=weights,
    )

    class Args:
        base_model = "black-forest-labs/FLUX.1-schnell"
        colab_dataset_dir = "training-data/art-style-lora"
        prepared_dataset_dir = "training-data/art-style-lora-weighted"
        output_dir = "six-tongues-lora-output"
        hub_model_id = "issdandavis/six-tongues-art-lora"
        trigger_word = "sixtongues_style"
        lora_rank = 16
        lora_alpha = 16
        learning_rate = 1e-4
        lr_scheduler = "constant"
        train_batch_size = 1
        gradient_accumulation_steps = 1
        max_train_steps = None
        save_steps = None
        resolution = 1024
        seed = 42
        eval_num_inference_steps = 4
        eval_guidance_scale = 0.0

    config = build_config(Args(), plan, weights)
    report = render_report(
        dataset_dir=dataset_dir,
        colab_dataset_dir=Args.colab_dataset_dir,
        prepared_dataset_dir=Args.prepared_dataset_dir,
        notebook_path=tmp_path / "notebook.ipynb",
        plan_path=tmp_path / "plan.json",
        quality_weights=weights,
        config=config,
        plan=plan,
    )

    assert "shared trigger prompt plus weighted file repetition" in report
    assert "`anchor`: 1 files x weight 6 -> 6 effective examples" in report

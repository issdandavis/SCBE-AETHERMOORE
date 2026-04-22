#!/usr/bin/env python3
"""Package SCBE products into deliverable ZIP files.

Creates two product ZIPs:
1. AI Governance Toolkit ($29) — templates, decision records, architecture docs
2. AI Security Training Vault ($29) — SFT pairs, benchmark scripts, Colab notebook

Usage:
    python scripts/package_products.py
    python scripts/package_products.py --product toolkit
    python scripts/package_products.py --product vault
    python scripts/package_products.py --output-dir /path/to/output
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUTPUT = REPO_ROOT / "products" / "packaged"

# ---- Product: AI Governance Toolkit ----

TOOLKIT_FILES = [
    # Architecture docs
    ("LAYER_INDEX.md", "docs/LAYER_INDEX.md"),
    ("SYSTEM_ARCHITECTURE.md", "docs/SYSTEM_ARCHITECTURE.md"),
    ("ARCHITECTURE.md", "docs/ARCHITECTURE.md"),
    ("docs/LANGUES_WEIGHTING_SYSTEM.md", "docs/LANGUES_WEIGHTING_SYSTEM.md"),
    ("docs/CORE_AXIOMS_CANONICAL_INDEX.md", "docs/CORE_AXIOMS_CANONICAL_INDEX.md"),
    ("docs/specs/LAYER_12_CANONICAL_FORMULA.md", "docs/LAYER_12_CANONICAL_FORMULA.md"),
    # Governance templates
    ("config/scbe_core_axioms_v1.yaml", "templates/scbe_core_axioms.yaml"),
    ("training-data/schemas/training_schema.json", "templates/training_schema.json"),
    # Quickstart
    ("docs/QUICKSTART_MONETIZATION.md", "quickstart/DEMO_FLOW.md"),
]

TOOLKIT_README = """# SCBE AI Governance Toolkit

Thank you for purchasing the AI Governance Toolkit from AetherMoore.

## What's Inside

- `docs/` — Complete 14-layer architecture documentation
- `templates/` — Governance configuration templates (YAML/JSON)
- `quickstart/` — Demo flow to get started immediately

## Quick Start

1. Read `docs/LAYER_INDEX.md` for the full 14-layer pipeline overview
2. Copy `templates/scbe_core_axioms.yaml` into your project
3. Follow `quickstart/DEMO_FLOW.md` for a hands-on walkthrough

## Support

- Email: ai@aethermoore.com
- GitHub: https://github.com/issdandavis/SCBE-AETHERMOORE

## License

MIT License — use commercially, modify freely, attribution appreciated.

(c) 2026 Issac Davis / AetherMoore
"""

# ---- Product: AI Security Training Vault ----

# We include a curated subset of SFT data (not the massive claude exports)
VAULT_SFT_FILES = [
    "training-data/sft/aetherbrowser_commands_v1.jsonl",
    "training-data/sft/api_usage_pairs.jsonl",
    "training-data/sft/architecture_explainer_v1.jsonl",
    "training-data/sft/attention_residuals_sft.jsonl",
    "training-data/sft/biblical_null_space_probes.jsonl",
    "training-data/sft/code_brushes_sft.jsonl",
    "training-data/sft/code_substrate_l0_sft.jsonl",
    "training-data/sft/codex_skill_tutorials_10th_grade.jsonl",
]

VAULT_EXTRA_FILES = [
    # Schema
    ("training-data/schemas/training_schema.json", "schemas/training_schema.json"),
    # Benchmark scripts
    ("scripts/benchmark/scbe_vs_baseline.py", "benchmark/scbe_vs_baseline.py"),
    ("scripts/benchmark/scbe_vs_industry.py", "benchmark/scbe_vs_industry.py"),
    ("scripts/benchmark/context_embedding_benchmark.py", "benchmark/context_embedding_benchmark.py"),
    ("scripts/benchmark/null_space_ablation.py", "benchmark/null_space_ablation.py"),
    # Architecture reference
    ("docs/specs/LAYER_12_CANONICAL_FORMULA.md", "docs/LAYER_12_CANONICAL_FORMULA.md"),
]

VAULT_README = """# SCBE AI Security Training Vault

Thank you for purchasing the AI Security Training Vault from AetherMoore.

## What's Inside

- `sft/` — Curated supervised fine-tuning pairs for AI safety tasks
- `benchmark/` — Benchmark scripts to evaluate your fine-tuned model
- `schemas/` — Data format documentation
- `docs/` — Architecture reference

## Quick Start

1. Install dependencies: `pip install transformers datasets`
2. Load the data:
   ```python
   from datasets import load_dataset
   ds = load_dataset("json", data_files="sft/*.jsonl")
   ```
3. Fine-tune with any framework (HuggingFace, Axolotl, OpenAI API)
4. Benchmark: `python benchmark/scbe_vs_baseline.py`

## Data Format

Each JSONL file contains records with `instruction` and `response` fields,
suitable for standard SFT training pipelines.

## Support

- Email: ai@aethermoore.com
- GitHub: https://github.com/issdandavis/SCBE-AETHERMOORE
- HuggingFace: https://huggingface.co/issdandavis

## License

MIT License — use commercially, modify freely, attribution appreciated.

(c) 2026 Issac Davis / AetherMoore
"""


def _count_jsonl_records(path: Path) -> int:
    """Count non-empty lines in a JSONL file."""
    count = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
    except OSError as exc:
        print(f"[WARN] Failed to count records in {path}: {exc}", file=sys.stderr)
    return count


def package_toolkit(output_dir: Path) -> Path:
    """Package the AI Governance Toolkit."""
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / "SCBE_AI_Governance_Toolkit_v1.zip"

    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("README.md", TOOLKIT_README)
        zf.writestr("LICENSE", "MIT License\n\nCopyright (c) 2026 Issac Davis / AetherMoore\n")

        for src_rel, dst_rel in TOOLKIT_FILES:
            src = REPO_ROOT / src_rel
            if src.exists():
                zf.write(src, dst_rel)
                print(f"  + {dst_rel}")
            else:
                print(f"  ! MISSING: {src_rel}")

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\nToolkit packaged: {zip_path} ({size_mb:.1f} MB)")
    return zip_path


def package_vault(output_dir: Path) -> Path:
    """Package the AI Security Training Vault."""
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / "SCBE_AI_Security_Training_Vault_v1.zip"

    total_records = 0

    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("README.md", VAULT_README)
        zf.writestr("LICENSE", "MIT License\n\nCopyright (c) 2026 Issac Davis / AetherMoore\n")

        # SFT data files
        for sft_rel in VAULT_SFT_FILES:
            src = REPO_ROOT / sft_rel
            if src.exists():
                dst = f"sft/{src.name}"
                zf.write(src, dst)
                count = _count_jsonl_records(src)
                total_records += count
                print(f"  + {dst} ({count} records)")
            else:
                print(f"  ! MISSING: {sft_rel}")

        # Extra files
        for src_rel, dst_rel in VAULT_EXTRA_FILES:
            src = REPO_ROOT / src_rel
            if src.exists():
                zf.write(src, dst_rel)
                print(f"  + {dst_rel}")
            else:
                print(f"  ! MISSING: {src_rel}")

        # Metadata
        metadata = {
            "product": "SCBE AI Security Training Vault",
            "version": "1.0",
            "total_sft_records": total_records,
            "packaged_at": datetime.now(timezone.utc).isoformat(),
            "author": "Issac Davis",
            "license": "MIT",
        }
        zf.writestr("metadata.json", json.dumps(metadata, indent=2))

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\nVault packaged: {zip_path} ({size_mb:.1f} MB, {total_records} SFT records)")
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Package SCBE products for delivery")
    parser.add_argument("--product", choices=["toolkit", "vault", "all"], default="all")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    print(f"Output directory: {args.output_dir}\n")

    if args.product in ("toolkit", "all"):
        print("=== Packaging AI Governance Toolkit ===")
        package_toolkit(args.output_dir)
        print()

    if args.product in ("vault", "all"):
        print("=== Packaging AI Security Training Vault ===")
        package_vault(args.output_dir)
        print()

    print("Done. Upload these ZIPs to your delivery system (GitHub Releases, S3, or direct email).")


if __name__ == "__main__":
    main()

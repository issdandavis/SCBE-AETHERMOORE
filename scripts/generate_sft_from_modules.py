#!/usr/bin/env python3
"""Generate SFT training pairs from Python module docstrings and signatures.

Part of the Ouroboros loop: codebase -> SFT data -> model -> governance -> codebase.

Scans specified Python files, extracts docstrings from classes/functions/modules,
and generates instruction/response pairs for fine-tuning.

Usage:
    python scripts/generate_sft_from_modules.py
    python scripts/generate_sft_from_modules.py --output training-data/sft_codebase_new.jsonl
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

TRAINING_DATA_DIR = Path(__file__).parent.parent / "training-data"

# Modules to extract from (relative to project root)
DEFAULT_MODULES = [
    "src/symphonic_cipher/scbe_aethermoore/trinary.py",
    "src/symphonic_cipher/scbe_aethermoore/negabinary.py",
    "src/symphonic_cipher/scbe_aethermoore/flock_shepherd.py",
]

CATEGORY_MAP = {
    "trinary": "encoding-systems",
    "negabinary": "encoding-systems",
    "flock_shepherd": "fleet-management",
}


def extract_docstrings(filepath: Path) -> list[dict[str, Any]]:
    """Extract module, class, and function docstrings from a Python file."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    records: list[dict[str, Any]] = []
    module_name = filepath.stem

    # Module docstring
    module_doc = ast.get_docstring(tree)
    if module_doc and len(module_doc) >= 30:
        records.append({
            "type": "module",
            "name": module_name,
            "docstring": module_doc,
            "filepath": str(filepath),
        })

    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node)
            if not doc or len(doc) < 10:
                continue

            # Get function signature
            sig = ""
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = []
                for arg in node.args.args:
                    annotation = ""
                    if arg.annotation:
                        annotation = f": {ast.unparse(arg.annotation)}"
                    args.append(f"{arg.arg}{annotation}")
                returns = ""
                if node.returns:
                    returns = f" -> {ast.unparse(node.returns)}"
                sig = f"def {node.name}({', '.join(args)}){returns}"
            elif isinstance(node, ast.ClassDef):
                bases = ", ".join(ast.unparse(b) for b in node.bases)
                sig = f"class {node.name}({bases})" if bases else f"class {node.name}"

            records.append({
                "type": "class" if isinstance(node, ast.ClassDef) else "function",
                "name": node.name,
                "signature": sig,
                "docstring": doc,
                "filepath": str(filepath),
                "line": node.lineno,
            })

    return records


def docstring_to_sft(record: dict[str, Any], module_name: str) -> dict[str, Any]:
    """Convert a docstring record to an SFT instruction/response pair."""
    category = CATEGORY_MAP.get(module_name, "architecture")

    if record["type"] == "module":
        instruction = f"What is the {record['name']} module in SCBE-AETHERMOORE and what does it provide?"
        response = record["docstring"]
    elif record["type"] == "class":
        instruction = f"Explain the {record['name']} class in the SCBE-AETHERMOORE {module_name} module."
        response = f"```python\n{record['signature']}\n```\n\n{record['docstring']}"
    else:
        instruction = f"What does the `{record['name']}` function do in {module_name}?"
        response = f"```python\n{record['signature']}\n```\n\n{record['docstring']}"

    return {
        "instruction": instruction,
        "response": response,
        "category": category,
        "metadata": {
            "source_file": record["filepath"].replace("\\", "/"),
            "origin": "codebase_docs",
            "source_type": "code_doc",
            "track": "functions" if record["type"] == "function" else "system",
            "quality": {"dedup": True, "validated": True},
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SFT pairs from module docstrings")
    parser.add_argument(
        "--output",
        default=str(TRAINING_DATA_DIR / "sft_codebase_new.jsonl"),
        help="Output JSONL path",
    )
    parser.add_argument(
        "--modules",
        nargs="*",
        default=DEFAULT_MODULES,
        help="Python files to extract from",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    all_records: list[dict[str, Any]] = []

    print("--- Extracting docstrings ---", file=sys.stderr)
    for mod_path in args.modules:
        filepath = project_root / mod_path
        if not filepath.exists():
            print(f"  SKIP (not found): {mod_path}", file=sys.stderr)
            continue

        extracted = extract_docstrings(filepath)
        module_name = filepath.stem
        sft_pairs = [docstring_to_sft(r, module_name) for r in extracted]
        print(f"  {filepath.name}: {len(sft_pairs)} pairs", file=sys.stderr)
        all_records.extend(sft_pairs)

    # Assign IDs
    for i, record in enumerate(all_records):
        record["id"] = f"sft-gen-{i+1:04d}"

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nGenerated {len(all_records)} SFT pairs -> {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

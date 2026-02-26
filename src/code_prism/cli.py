from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .builder import CodePrismBuilder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Code Prism transpilation scaffold.")
    parser.add_argument("--input", required=True, help="Source file to translate.")
    parser.add_argument("--source-lang", required=True, help="Source language (python/typescript).")
    parser.add_argument(
        "--targets",
        required=True,
        nargs="+",
        help="Target languages (e.g. typescript go).",
    )
    parser.add_argument(
        "--out-dir",
        default="artifacts/code_prism",
        help="Output directory for translated files.",
    )
    parser.add_argument(
        "--module-name",
        default="prism_module",
        help="Module label used in the IR.",
    )
    parser.add_argument(
        "--tongue-combo",
        default="KO+CA",
        help="Six Tongue combo label for metadata routing.",
    )
    return parser.parse_args()


def _extension(language: str) -> str:
    lang = language.lower()
    if lang == "python":
        return ".py"
    if lang in {"typescript", "ts"}:
        return ".ts"
    if lang == "go":
        return ".go"
    return ".txt"


def main() -> None:
    args = parse_args()
    source_path = Path(args.input)
    source_code = source_path.read_text(encoding="utf-8")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    builder = CodePrismBuilder()
    results = builder.translate(
        source_code=source_code,
        source_language=args.source_lang,
        target_languages=args.targets,
        module_name=args.module_name,
        tongue_combo=args.tongue_combo,
    )

    summary = {}
    for language, artifact in results.items():
        ext = _extension(language)
        out_file = out_dir / f"{args.module_name}.{language}{ext}"
        if artifact.code:
            out_file.write_text(artifact.code, encoding="utf-8")
        summary[language] = {
            "valid": artifact.valid,
            "issues": [{"code": i.code, "message": i.message} for i in artifact.issues],
            "metadata": artifact.metadata,
            "output_file": str(out_file) if artifact.code else None,
        }

    (out_dir / f"{args.module_name}.summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()


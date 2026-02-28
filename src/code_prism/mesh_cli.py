from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .mesh import CodeMeshBuilder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Code Mesh native-system transpilation scaffold.")
    parser.add_argument("--input", required=True, help="Source file to translate.")
    parser.add_argument("--source-lang", required=True, help="Source language (python/typescript).")
    parser.add_argument(
        "--target-systems",
        required=True,
        nargs="+",
        help="Native target systems (e.g. node_runtime go_runtime mcp_python).",
    )
    parser.add_argument(
        "--out-dir",
        default="artifacts/code_mesh",
        help="Output directory for translated files and governance summaries.",
    )
    parser.add_argument(
        "--module-name",
        default="mesh_module",
        help="Module label used in IR artifacts.",
    )
    parser.add_argument(
        "--tongue-combo",
        default=None,
        help="Optional explicit Six Tongue combo (e.g. KO+CA+DR).",
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

    builder = CodeMeshBuilder()
    results = builder.translate_to_native(
        source_code=source_code,
        source_language=args.source_lang,
        target_systems=args.target_systems,
        module_name=args.module_name,
        tongue_combo=args.tongue_combo,
    )

    summary = {}
    for target_system, artifact in results.items():
        ext = _extension(artifact.target_language)
        if ext == f".{artifact.target_language.lower()}":
            out_file = out_dir / f"{args.module_name}.{target_system}{ext}"
        else:
            out_file = out_dir / f"{args.module_name}.{target_system}.{artifact.target_language}{ext}"
        if artifact.code:
            out_file.write_text(artifact.code, encoding="utf-8")

        summary[target_system] = {
            "target_language": artifact.target_language,
            "valid": artifact.valid,
            "issues": [{"code": i.code, "message": i.message} for i in artifact.issues],
            "metadata": artifact.metadata,
            "state_vector": artifact.state_vector,
            "gate_report": artifact.gate_report,
            "mesh_overlay_230_bits": artifact.mesh_overlay_230_bits,
            "mesh_overlay_230_hex": artifact.mesh_overlay_230_hex,
            "decision_record": {
                "action": artifact.decision_record.action if artifact.decision_record else None,
                "reason": artifact.decision_record.reason if artifact.decision_record else None,
                "confidence": artifact.decision_record.confidence if artifact.decision_record else None,
                "timestamp_utc": artifact.decision_record.timestamp_utc if artifact.decision_record else None,
                "signature": artifact.decision_record.signature if artifact.decision_record else None,
            },
            "output_file": str(out_file) if artifact.code else None,
        }

    (out_dir / f"{args.module_name}.mesh.summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build a portable SCBE training package from raw sources and normalized JSONL lanes."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "training-data" / "packages"
PACKAGE_SCHEMA_PATH = REPO_ROOT / "schemas" / "training_package_manifest.schema.json"
ROUTE_SCHEMA_PATH = REPO_ROOT / "schemas" / "route_consistency_record.schema.json"
MODEL_TRACE_SCHEMA_PATH = REPO_ROOT / "schemas" / "model_trace_record.schema.json"
RIGHTS_SCHEMA_PATH = REPO_ROOT / "schemas" / "ingestion_rights_record.schema.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip().lower()).strip("-")
    return value or "package"


def _safe_relative(path: Path, root: Path | None = None) -> str:
    base = root or REPO_ROOT
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except Exception:
        return str(path.resolve())


def _has_glob_pattern(value: str) -> bool:
    return any(token in value for token in ("*", "?", "["))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expand_inputs(inputs: Sequence[str]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for raw in inputs:
        value = raw.strip()
        if not value:
            continue
        matches: list[Path] = []
        if _has_glob_pattern(value):
            matches = [Path(match) for match in glob.glob(value, recursive=True)]
        else:
            candidate = Path(value).expanduser()
            if candidate.exists():
                if candidate.is_dir():
                    matches = [path for path in candidate.rglob("*") if path.is_file()]
                elif candidate.is_file():
                    matches = [candidate]
        for match in matches:
            resolved = str(match.resolve()).lower()
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(match)
    return sorted(out)


def _stage_file(source_path: Path, destination_dir: Path, label: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    fingerprint = hashlib.sha256(str(source_path.resolve()).encode("utf-8")).hexdigest()[:10]
    target_name = f"{fingerprint}_{_slug(label)}{source_path.suffix.lower()}"
    target_path = destination_dir / target_name
    shutil.copy2(source_path, target_path)
    return target_path


def _count_jsonl_rows(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _load_validator(path: Path) -> Draft202012Validator:
    return Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


def _validate_jsonl(path: Path, validator: Draft202012Validator) -> int:
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        validator.validate(json.loads(stripped))
        count += 1
    return count


def _stage_group(
    *,
    inputs: Sequence[Path],
    destination_dir: Path,
    validator: Draft202012Validator | None = None,
) -> tuple[list[dict[str, Any]], int]:
    staged: list[dict[str, Any]] = []
    total_rows = 0
    for source_path in inputs:
        row_count = _validate_jsonl(source_path, validator) if validator else _count_jsonl_rows(source_path)
        staged_path = _stage_file(source_path, destination_dir, source_path.stem)
        total_rows += row_count
        staged.append(
            {
                "original_path": str(source_path.resolve()),
                "staged_path": str(staged_path.resolve()),
                "size_bytes": source_path.stat().st_size,
                "sha256": _sha256_file(source_path),
                "record_count": row_count,
            }
        )
    return staged, total_rows


def _stage_raw_sources(inputs: Sequence[Path], destination_dir: Path) -> list[dict[str, Any]]:
    staged: list[dict[str, Any]] = []
    for source_path in inputs:
        subdir = destination_dir / _slug(source_path.suffix.lstrip(".") or "raw")
        staged_path = _stage_file(source_path, subdir, source_path.stem)
        staged.append(
            {
                "original_path": str(source_path.resolve()),
                "staged_path": str(staged_path.resolve()),
                "size_bytes": source_path.stat().st_size,
                "sha256": _sha256_file(source_path),
                "record_count": None,
            }
        )
    return staged


def _merge_jsonl(staged_entries: Sequence[dict[str, Any]], output_path: Path) -> str | None:
    if not staged_entries:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for entry in staged_entries:
            staged_path = Path(entry["staged_path"])
            content = staged_path.read_text(encoding="utf-8").strip()
            if not content:
                continue
            handle.write(content)
            handle.write("\n")
    return str(output_path.resolve())


def _build_report(manifest: dict[str, Any]) -> str:
    counts = manifest["counts"]
    outputs = manifest["outputs"]
    lines = [
        "# SCBE Training Package",
        "",
        f"- package_id: `{manifest['package_id']}`",
        f"- created_at_utc: `{manifest['created_at_utc']}`",
        f"- package_dir: `{_safe_relative(Path(manifest['package_dir']))}`",
        f"- source_files: `{counts['source_files']}`",
        f"- sft_rows: `{counts['sft_rows']}`",
        f"- route_consistency_rows: `{counts['route_consistency_rows']}`",
        f"- model_trace_rows: `{counts['model_trace_rows']}`",
        f"- rights_rows: `{counts['rights_rows']}`",
        "",
        "## Outputs",
        f"- merged_sft: `{_safe_relative(Path(outputs['merged_sft'])) if outputs['merged_sft'] else '(none)'}`",
        f"- merged_route_consistency: `{_safe_relative(Path(outputs['merged_route_consistency'])) if outputs['merged_route_consistency'] else '(none)'}`",
        f"- merged_model_traces: `{_safe_relative(Path(outputs['merged_model_traces'])) if outputs['merged_model_traces'] else '(none)'}`",
        f"- merged_rights: `{_safe_relative(Path(outputs['merged_rights'])) if outputs['merged_rights'] else '(none)'}`",
    ]
    if manifest.get("notes"):
        lines.extend(["", "## Notes", manifest["notes"]])
    return "\n".join(lines) + "\n"


def build_training_package(
    *,
    package_name: str,
    source_inputs: Sequence[str],
    sft_inputs: Sequence[str],
    route_inputs: Sequence[str],
    model_trace_inputs: Sequence[str],
    rights_inputs: Sequence[str],
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    package_stamp: str | None = None,
    notes: str | None = None,
    create_archive: bool = False,
) -> dict[str, Any]:
    source_files = _expand_inputs(source_inputs)
    sft_files = _expand_inputs(sft_inputs)
    route_files = _expand_inputs(route_inputs)
    model_trace_files = _expand_inputs(model_trace_inputs)
    rights_files = _expand_inputs(rights_inputs)

    if not any((source_files, sft_files, route_files, model_trace_files, rights_files)):
        raise ValueError("No training package inputs were found")

    stamp = package_stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    package_id = f"{_slug(package_name)}-{stamp}"
    package_dir = output_root / package_id
    package_dir.mkdir(parents=True, exist_ok=True)

    route_validator = _load_validator(ROUTE_SCHEMA_PATH)
    model_trace_validator = _load_validator(MODEL_TRACE_SCHEMA_PATH)
    rights_validator = _load_validator(RIGHTS_SCHEMA_PATH)
    manifest_validator = _load_validator(PACKAGE_SCHEMA_PATH)

    staged_sources = _stage_raw_sources(source_files, package_dir / "sources")
    staged_sft, sft_rows = _stage_group(inputs=sft_files, destination_dir=package_dir / "normalized" / "sft")
    staged_route, route_rows = _stage_group(
        inputs=route_files,
        destination_dir=package_dir / "normalized" / "route_consistency",
        validator=route_validator,
    )
    staged_model_traces, model_trace_rows = _stage_group(
        inputs=model_trace_files,
        destination_dir=package_dir / "normalized" / "model_traces",
        validator=model_trace_validator,
    )
    staged_rights, rights_rows = _stage_group(
        inputs=rights_files,
        destination_dir=package_dir / "normalized" / "rights",
        validator=rights_validator,
    )

    merged_sft = _merge_jsonl(staged_sft, package_dir / "normalized" / "sft_merged.jsonl")
    merged_route = _merge_jsonl(staged_route, package_dir / "normalized" / "route_consistency_merged.jsonl")
    merged_model_traces = _merge_jsonl(staged_model_traces, package_dir / "normalized" / "model_traces_merged.jsonl")
    merged_rights = _merge_jsonl(staged_rights, package_dir / "normalized" / "rights_merged.jsonl")

    manifest = {
        "schema_version": "scbe_training_package_manifest_v1",
        "package_id": package_id,
        "package_name": package_name,
        "created_at_utc": _utc_now_iso(),
        "package_dir": str(package_dir.resolve()),
        "notes": notes,
        "counts": {
            "source_files": len(staged_sources),
            "sft_files": len(staged_sft),
            "sft_rows": sft_rows,
            "route_consistency_files": len(staged_route),
            "route_consistency_rows": route_rows,
            "model_trace_files": len(staged_model_traces),
            "model_trace_rows": model_trace_rows,
            "rights_files": len(staged_rights),
            "rights_rows": rights_rows,
        },
        "inputs": {
            "raw_sources": [str(path.resolve()) for path in source_files],
            "normalized": {
                "sft": [str(path.resolve()) for path in sft_files],
                "route_consistency": [str(path.resolve()) for path in route_files],
                "model_traces": [str(path.resolve()) for path in model_trace_files],
                "rights": [str(path.resolve()) for path in rights_files],
            },
        },
        "staged": {
            "source_files": staged_sources,
            "normalized_files": {
                "sft": staged_sft,
                "route_consistency": staged_route,
                "model_traces": staged_model_traces,
                "rights": staged_rights,
            },
        },
        "outputs": {
            "merged_sft": merged_sft,
            "merged_route_consistency": merged_route,
            "merged_model_traces": merged_model_traces,
            "merged_rights": merged_rights,
            "report": str((package_dir / "package_report.md").resolve()),
            "archive": None,
        },
    }
    manifest_validator.validate(manifest)

    manifest_path = package_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    report_path = package_dir / "package_report.md"
    report_path.write_text(_build_report(manifest), encoding="utf-8")

    archive_path: str | None = None
    if create_archive:
        archive_base = output_root / package_id
        archive_path = shutil.make_archive(str(archive_base), "zip", root_dir=package_dir)
        manifest["outputs"]["archive"] = str(Path(archive_path).resolve())
        manifest_validator.validate(manifest)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        report_path.write_text(_build_report(manifest), encoding="utf-8")

    return {
        "package_id": package_id,
        "package_dir": str(package_dir.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "report_path": str(report_path.resolve()),
        "archive_path": archive_path,
        "counts": manifest["counts"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-name", required=True, help="Logical name for the package.")
    parser.add_argument("--source", action="append", default=[], help="Raw source file, directory, or glob.")
    parser.add_argument("--sft", action="append", default=[], help="SFT JSONL file, directory, or glob.")
    parser.add_argument(
        "--route-records",
        action="append",
        default=[],
        help="Route consistency JSONL file, directory, or glob.",
    )
    parser.add_argument(
        "--model-traces",
        action="append",
        default=[],
        help="Model trace JSONL file, directory, or glob.",
    )
    parser.add_argument(
        "--rights-records",
        action="append",
        default=[],
        help="Ingestion rights JSONL file, directory, or glob.",
    )
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Package output root.")
    parser.add_argument("--package-stamp", default=None, help="Optional deterministic timestamp suffix.")
    parser.add_argument("--notes", default=None, help="Optional note stored in the manifest.")
    parser.add_argument("--archive", action="store_true", help="Create a zip archive alongside the package dir.")
    args = parser.parse_args()

    result = build_training_package(
        package_name=args.package_name,
        source_inputs=args.source,
        sft_inputs=args.sft,
        route_inputs=args.route_records,
        model_trace_inputs=args.model_traces,
        rights_inputs=args.rights_records,
        output_root=Path(args.output_root),
        package_stamp=args.package_stamp,
        notes=args.notes,
        create_archive=args.archive,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

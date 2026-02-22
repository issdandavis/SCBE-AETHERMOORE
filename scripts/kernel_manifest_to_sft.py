#!/usr/bin/env python3
"""
Convert canonical kernel manifest files into SFT records.

This builds a kernel-focused dataset directly from training/kernel_manifest.yaml.
If a manifest file is a thin re-export (src/harmonic -> packages/kernel/src/*),
the target kernel source is loaded and used as primary content.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

import yaml


DECL_RE = re.compile(
    r"(?m)^(?:export\s+)?(?:async\s+)?(?:function|class|interface|type|const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)"
)
REEXPORT_RE = re.compile(r"""export\s+\*\s+from\s+['"](.+?)['"]""")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert kernel manifest files into SFT JSONL")
    parser.add_argument(
        "--manifest",
        default="training/kernel_manifest.yaml",
        help="Path to kernel manifest YAML",
    )
    parser.add_argument(
        "--output",
        default="training-data/sft_kernel_manifest.jsonl",
        help="Output JSONL file",
    )
    parser.add_argument(
        "--max-response-chars",
        type=int,
        default=3200,
        help="Max response text length",
    )
    return parser.parse_args()


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    chunk = text[:limit]
    cut = max(chunk.rfind("\n\n"), chunk.rfind(". "))
    if cut > limit // 2:
        return chunk[: cut + 1].strip()
    return chunk.strip() + "..."


def split_sections_from_source(path: Path, text: str) -> list[tuple[str, str]]:
    suffix = path.suffix.lower()

    if suffix in {".md", ".rst"}:
        sections: list[tuple[str, str]] = []
        heading_re = re.compile(r"(?m)^#{1,3}\s+(.+?)\s*$")
        matches = list(heading_re.finditer(text))
        if not matches:
            return [(f"{path.name} overview", clean_text(text))]
        for i, m in enumerate(matches):
            title = m.group(1).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = clean_text(text[start:end])
            if body:
                sections.append((title, body))
        return sections

    # Code-like split: declarations + file overview.
    sections = []
    overview = clean_text(text[:2200])
    if overview:
        sections.append((f"{path.name} overview", overview))

    lines = text.splitlines()
    for m in DECL_RE.finditer(text):
        name = m.group(1)
        start_char = m.start()
        line_no = text.count("\n", 0, start_char)
        start = max(0, line_no - 3)
        end = min(len(lines), line_no + 26)
        snippet = clean_text("\n".join(lines[start:end]))
        if len(snippet) >= 120:
            sections.append((f"{path.name}:{name}", snippet))
        if len(sections) >= 8:
            break
    return sections


def resolve_primary_content(repo_root: Path, manifest_path: Path, rel_file: str) -> tuple[Path, str]:
    src = (repo_root / rel_file).resolve()
    if not src.exists():
        return src, ""
    text = src.read_text(encoding="utf-8", errors="ignore")
    m = REEXPORT_RE.search(text)
    if not m:
        return src, text

    # Resolve re-export target relative to source file location.
    target = (src.parent / m.group(1)).resolve()
    if target.exists() and target.is_file():
        target_text = target.read_text(encoding="utf-8", errors="ignore")
        if target_text.strip():
            return target, target_text
    return src, text


def build_records(repo_root: Path, manifest: dict, max_chars: int) -> list[dict]:
    kernel_files = manifest.get("kernel", [])
    if not isinstance(kernel_files, list):
        raise ValueError("Invalid manifest: 'kernel' must be a list")

    records: list[dict] = []
    idx = 1
    for rel_file in kernel_files:
        if not isinstance(rel_file, str):
            continue
        primary_path, primary_text = resolve_primary_content(repo_root, Path("training/kernel_manifest.yaml"), rel_file)
        if not primary_text.strip():
            continue

        sections = split_sections_from_source(primary_path, primary_text)
        for title, body in sections:
            response = truncate(body, max_chars)
            if len(response) < 120:
                continue
            instruction = (
                f"Explain the kernel component '{title}' and how it contributes to the SCBE core pipeline."
            )
            records.append(
                {
                    "id": f"sft-kernel-{idx:04d}",
                    "category": "kernel-docs",
                    "instruction": instruction,
                    "response": response,
                    "metadata": {
                        "source": "scbe_aethermoore",
                        "version": "3.3.0",
                        "author": "Issac Davis",
                        "origin": "kernel_manifest_docs",
                        "kernel_manifest_file": rel_file,
                        "source_file": str(primary_path.relative_to(repo_root)).replace("\\", "/"),
                    },
                }
            )
            idx += 1
    return records


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / args.manifest
    output_path = repo_root / args.output

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Invalid manifest format")

    records = build_records(repo_root, manifest, args.max_response_chars)
    count = write_jsonl(output_path, records)

    print(
        json.dumps(
            {
                "manifest": str(manifest_path).replace("\\", "/"),
                "output": str(output_path).replace("\\", "/"),
                "records": count,
            }
        )
    )


if __name__ == "__main__":
    main()


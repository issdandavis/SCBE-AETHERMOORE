#!/usr/bin/env python3
"""Download and sweep a public-domain reference book.

Default reference: Frankenstein from Project Gutenberg.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.benchmark.book_quality_sweep import DEFAULT_OUTPUT_ROOT, score_book  # noqa: E402

DEFAULT_SOURCE_URL = "https://www.gutenberg.org/ebooks/84.txt.utf-8"
DEFAULT_TITLE = "Frankenstein; or, the Modern Prometheus"
DEFAULT_AUTHOR = "Mary Wollstonecraft Shelley"
DEFAULT_CACHE_ROOT = REPO_ROOT / "artifacts" / "benchmarks" / "fiction_quality" / "reference_books" / "frankenstein"


def _download_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "SCBE-AETHERMOORE benchmark/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def _strip_gutenberg_boilerplate(text: str) -> str:
    start_match = re.search(r"\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK .*?\*\*\*", text, re.I)
    end_match = re.search(r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK .*?\*\*\*", text, re.I)
    if start_match:
        text = text[start_match.end() :]
    if end_match:
        text = text[: end_match.start()]
    return text.strip()


def _split_chapters(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^(Letter\s+\d+|Chapter\s+\d+)\b.*$", text, re.I))
    if not matches:
        return [("reference-001.md", text)]
    chapters: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title = match.group(1).lower().replace(" ", "-")
        body = text[start:end].strip()
        if body:
            chapters.append((f"{index + 1:03d}-{title}.md", body))
    return chapters


def prepare_reference_book(
    *,
    source_url: str = DEFAULT_SOURCE_URL,
    cache_root: Path = DEFAULT_CACHE_ROOT,
    title: str = DEFAULT_TITLE,
    author: str = DEFAULT_AUTHOR,
    refresh: bool = False,
) -> dict[str, object]:
    cache_root.mkdir(parents=True, exist_ok=True)
    raw_path = cache_root / "source.txt"
    chapters_root = cache_root / "chapters"
    meta_path = cache_root / "source_manifest.json"

    if refresh or not raw_path.exists():
        raw_path.write_text(_download_text(source_url), encoding="utf-8")

    text = _strip_gutenberg_boilerplate(raw_path.read_text(encoding="utf-8"))
    chapters = _split_chapters(text)
    chapters_root.mkdir(parents=True, exist_ok=True)
    for old in chapters_root.glob("*.md"):
        old.unlink()
    for filename, body in chapters:
        (chapters_root / filename).write_text(body + "\n", encoding="utf-8")

    manifest = {
        "schema_version": "scbe_reference_book_manifest_v1",
        "title": title,
        "author": author,
        "source_url": source_url,
        "cache_root": str(cache_root),
        "raw_path": str(raw_path),
        "chapters_root": str(chapters_root),
        "chapter_count": len(chapters),
        "source_note": "Project Gutenberg public-domain source; benchmark is local reference scoring, not a literary authority claim.",
    }
    meta_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def run_reference_sweep(
    *,
    source_url: str = DEFAULT_SOURCE_URL,
    cache_root: Path = DEFAULT_CACHE_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    title: str = DEFAULT_TITLE,
    author: str = DEFAULT_AUTHOR,
    refresh: bool = False,
) -> dict[str, object]:
    manifest = prepare_reference_book(
        source_url=source_url,
        cache_root=cache_root,
        title=title,
        author=author,
        refresh=refresh,
    )
    internal_output_root = cache_root / "sweep"
    report = score_book(book_root=Path(str(manifest["chapters_root"])), output_root=internal_output_root)
    comparison = {
        "schema_version": "scbe_reference_book_quality_sweep_v1",
        "reference": manifest,
        "report_summary": {
            "sample_count": report["sample_count"],
            "chapter_count": report["chapter_count"],
            "average_score": report["average_score"],
            "hold_count": report["hold_count"],
            "average_ai_likelihood": round(
                sum(row["ai_likelihood_score"] for row in report["rows"]) / len(report["rows"]), 3
            )
            if report["rows"]
            else 0.0,
            "weakest_samples": [
                {
                    "id": row["id"],
                    "score": row["score"],
                    "ai_likelihood_score": row["ai_likelihood_score"],
                    "weakest_dimensions": row["weakest_dimensions"],
                }
                for row in report["weakest_samples"][:8]
            ],
        },
        "artifact_paths": {
            "reference_json": str(output_root / "reference_book_quality_sweep_latest.json"),
            "reference_markdown": str(output_root / "reference_book_quality_sweep_latest.md"),
            "internal_book_sweep_json": report["artifact_paths"]["json"],
            "internal_book_sweep_markdown": report["artifact_paths"]["markdown"],
        },
    }
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "reference_book_quality_sweep_latest.json"
    md_path = output_root / "reference_book_quality_sweep_latest.md"
    json_path.write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(comparison), encoding="utf-8")
    return {**comparison, "reference_artifact_paths": {"json": str(json_path), "markdown": str(md_path)}}


def render_markdown(payload: dict[str, object]) -> str:
    reference = payload["reference"]
    summary = payload["report_summary"]
    lines = [
        "# Reference Book Quality Sweep",
        "",
        f"- title: {reference['title']}",
        f"- author: {reference['author']}",
        f"- source: {reference['source_url']}",
        f"- chapters: `{summary['chapter_count']}`",
        f"- samples: `{summary['sample_count']}`",
        f"- average quality score: `{summary['average_score']}`",
        f"- average AI-likelihood: `{summary['average_ai_likelihood']}`",
        f"- hold count: `{summary['hold_count']}`",
        "",
        "## Weakest Samples",
        "",
    ]
    for row in summary["weakest_samples"]:
        lines.append(
            f"- `{row['id']}` score `{row['score']}` ai `{row['ai_likelihood_score']}` "
            f"weakest `{json.dumps(dict(row['weakest_dimensions']), sort_keys=True)}`"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--author", default=DEFAULT_AUTHOR)
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = run_reference_sweep(
        source_url=args.source_url,
        cache_root=args.cache_root,
        output_root=args.output_root,
        title=args.title,
        author=args.author,
        refresh=args.refresh,
    )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

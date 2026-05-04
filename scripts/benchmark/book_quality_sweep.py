#!/usr/bin/env python3
"""Sweep the reader-edition manuscript with the fiction-quality benchmark.

The scorer is calibrated for short passages, so this script samples chapter
windows instead of pretending a whole novel can be judged as one blob.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.benchmark.fiction_quality_benchmark import DEFAULT_CONFIG, load_config, score_row  # noqa: E402

DEFAULT_BOOK_ROOT = REPO_ROOT / "content" / "book" / "reader-edition"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "benchmarks" / "fiction_quality"
SCHEMA_VERSION = "scbe_book_quality_sweep_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text)


def _sentences(text: str) -> list[str]:
    return [item.strip() for item in re.findall(r"[^.!?]+[.!?]?", text) if item.strip()]


def _strip_markdown(text: str) -> str:
    text = re.sub(r"^#.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_`>#]", " ", text)
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _sentence_window(sentences: list[str], start_sentence: int, target_words: int) -> str:
    picked: list[str] = []
    word_count = 0
    for sentence in sentences[start_sentence:]:
        if not sentence:
            continue
        picked.append(sentence)
        word_count += len(_words(sentence))
        if word_count >= target_words:
            break
    return " ".join(picked).strip()


def _sample_windows(text: str, size: int) -> list[tuple[str, str]]:
    sentences = _sentences(text)
    words = _words(text)
    if len(words) <= size or len(sentences) <= 1:
        return [("full", text)]
    sentence_word_offsets: list[int] = []
    running = 0
    for sentence in sentences:
        sentence_word_offsets.append(running)
        running += len(_words(sentence))
    target_starts = {
        "opening": 0,
        "middle": max(0, (len(words) - size) // 2),
        "closing": max(0, len(words) - size),
    }
    windows: list[tuple[str, str]] = []
    for label, target in target_starts.items():
        start_sentence = 0
        for index, offset in enumerate(sentence_word_offsets):
            if offset <= target:
                start_sentence = index
            else:
                break
        windows.append((label, _sentence_window(sentences, start_sentence, size)))
    return windows


def _chapter_files(book_root: Path) -> list[Path]:
    files = [
        path
        for path in book_root.glob("*.md")
        if path.name not in {"the-six-tongues-protocol-full.md", "00-dedication.md", "zz-back-matter.md"}
    ]
    return sorted(files, key=lambda path: path.name)


def score_book(
    *,
    book_root: Path = DEFAULT_BOOK_ROOT,
    config_path: Path = DEFAULT_CONFIG,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    window_words: int = 135,
) -> dict[str, Any]:
    config = load_config(config_path)
    book_root = book_root.resolve()
    rows: list[dict[str, Any]] = []

    for path in _chapter_files(book_root):
        text = _strip_markdown(path.read_text(encoding="utf-8"))
        words = _words(text)
        if not words:
            continue
        for window_label, passage in _sample_windows(text, window_words):
            result = score_row(
                {
                    "id": f"{path.stem}:{window_label}",
                    "prompt": "Score this manuscript passage for prose quality only. Ignore whether it is AI-generated.",
                    "response": passage,
                    "constraints": {"min_words": 55, "max_words": 180, "required_terms": []},
                },
                config,
            )
            rows.append(
                {
                    "id": result["id"],
                    "chapter_path": str(path.relative_to(REPO_ROOT)),
                    "window": window_label,
                    "score": result["score"],
                    "decision": result["decision"],
                    "tier": result["tier"],
                    "dimension_scores": result["dimension_scores"],
                    "weakest_dimensions": sorted(result["dimension_scores"].items(), key=lambda item: item[1])[:4],
                    "ai_likelihood_score": result["ai_detection"]["ai_likelihood_score"],
                    "ai_detection_label": result["ai_detection"]["label"],
                    "ai_detection_signals": result["ai_detection"]["signals"],
                    "feedback": result["course_feedback"],
                    "passage": passage,
                }
            )

    chapter_summary: dict[str, dict[str, Any]] = {}
    for chapter in sorted({row["chapter_path"] for row in rows}):
        chapter_rows = [row for row in rows if row["chapter_path"] == chapter]
        chapter_summary[chapter] = {
            "samples": len(chapter_rows),
            "average_score": round(sum(row["score"] for row in chapter_rows) / len(chapter_rows), 3),
            "minimum_score": min(row["score"] for row in chapter_rows),
            "hold_count": sum(1 for row in chapter_rows if row["decision"] == "HOLD"),
            "average_ai_likelihood": round(
                sum(row["ai_likelihood_score"] for row in chapter_rows) / len(chapter_rows), 3
            ),
        }

    average = round(sum(row["score"] for row in rows) / len(rows), 3) if rows else 0.0
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "book_root": str(book_root),
        "window_words": window_words,
        "sample_count": len(rows),
        "chapter_count": len(chapter_summary),
        "average_score": average,
        "hold_count": sum(1 for row in rows if row["decision"] == "HOLD"),
        "ai_detection_boundary": "AI-likelihood is reported separately and is not included in prose quality scoring.",
        "chapter_summary": chapter_summary,
        "weakest_samples": sorted(rows, key=lambda row: row["score"])[:12],
        "highest_ai_likelihood_samples": sorted(rows, key=lambda row: row["ai_likelihood_score"], reverse=True)[:12],
        "rows": rows,
    }

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "book_quality_sweep_latest.json"
    md_path = output_root / "book_quality_sweep_latest.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {**payload, "artifact_paths": {"json": str(json_path), "markdown": str(md_path)}}


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Book Quality Sweep",
        "",
        f"- samples: `{payload['sample_count']}`",
        f"- chapters: `{payload['chapter_count']}`",
        f"- average score: `{payload['average_score']}`",
        f"- hold count: `{payload['hold_count']}`",
        f"- boundary: {payload['ai_detection_boundary']}",
        "",
        "## Weakest Samples",
        "",
    ]
    for row in payload["weakest_samples"]:
        lines.extend(
            [
                f"### `{row['id']}`",
                "",
                f"- file: `{row['chapter_path']}`",
                f"- score: `{row['score']}`",
                f"- ai-likelihood: `{row['ai_likelihood_score']}` `{row['ai_detection_label']}`",
                f"- weakest dimensions: `{json.dumps(dict(row['weakest_dimensions']), sort_keys=True)}`",
                f"- feedback: {' '.join(row['feedback'])}",
                "",
            ]
        )
    lines.extend(["## Highest AI-Likelihood Samples", ""])
    for row in payload["highest_ai_likelihood_samples"]:
        lines.append(
            f"- `{row['id']}` file `{row['chapter_path']}` quality `{row['score']}` "
            f"ai `{row['ai_likelihood_score']}` label `{row['ai_detection_label']}`"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-root", type=Path, default=DEFAULT_BOOK_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--window-words", type=int, default=135)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = score_book(
        book_root=args.book_root,
        config_path=args.config,
        output_root=args.output_root,
        window_words=args.window_words,
    )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if payload["sample_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

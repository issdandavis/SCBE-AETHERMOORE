"""
Rebuild the Six Tongues Protocol EPUB from source markdown and stage for KDP upload.

Usage:
    python scripts/publish/rebuild_and_stage_kdp.py [--open-kdp]

Workflow:
    1. Builds full manuscript from individual chapter files
    2. Converts to EPUB via pandoc
    3. Copies EPUB + cover to staging directory
    4. Optionally opens KDP bookshelf in browser

The staged EPUB at artifacts/book/kdp/the-six-tongues-protocol.epub
is what you upload to KDP.
"""

import os
import sys
import shutil
import subprocess
import json
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────
REPO = Path(r"C:\Users\issda\SCBE-AETHERMOORE")
READER_DIR = REPO / "content" / "book" / "reader-edition"
FULL_MD = READER_DIR / "the-six-tongues-protocol-full.md"
COVER_JPG = REPO / "content" / "book" / "SixTonguesProtocol_Cover_KDP.jpg"
ONEDRIVE_COVER = Path(r"C:\Users\issda\OneDrive\Books\The Six Tongues Protocol\SixTonguesProtocol_Cover_KDP.jpg")
STAGE_DIR = REPO / "artifacts" / "book" / "kdp"
ONEDRIVE_OUT = Path(r"C:\Users\issda\OneDrive\Books\The Six Tongues Protocol")

# Chapter reading order (matches build_kdp.py)
CHAPTER_FILES = [
    "00-dedication.md",
    "ch01.md",
    "interlude-01-pollys-vigil.md",
    "ch02.md",
    "ch03.md",
    "ch04.md",
    "ch05.md",
    "interlude-06-jorren-records.md",
    "ch06.md",
    "ch07.md",
    "interlude-04-brams-report.md",
    "ch08.md",
    "interlude-09-tovak-hides.md",
    "ch09.md",
    "interlude-02-the-garden-before.md",
    "ch10.md",
    "interlude-03-sennas-morning.md",
    "ch11.md",
    "ch12.md",
    "ch13.md",
    "interlude-07-nadia-runs.md",
    "ch14.md",
    "ch14b-the-ordinary.md",
    "ch15.md",
    "ch16.md",
    "ch16b-the-fizzlecress-incident.md",
    "ch17.md",
    "ch18.md",
    "ch19.md",
    "ch20.md",
    "interlude-10-arias-garden.md",
    "ch21.md",
    "ch21b-senna-after.md",
    "ch22.md",
    "ch23.md",
    "ch24.md",
    "interlude-08-the-pipe.md",
    "ch25.md",
    "interlude-05-alexanders-hold.md",
    "ch26.md",
    "ch27.md",
    "ch-rootlight.md",
    "zz-back-matter.md",
]

METADATA = {
    "title": "The Six Tongues Protocol",
    "author": "Issac Davis",
    "language": "en",
    "rights": "Copyright 2026 Issac Daniel Davis",
}

KDP_BOOKSHELF_URL = "https://kdp.amazon.com/en_US/bookshelf"


def build_full_manuscript():
    """Concatenate individual chapter files into one markdown document."""
    print("[1/5] Building full manuscript from chapter files...")

    front_matter = f"""---
title: "{METADATA['title']}"
author: "{METADATA['author']}"
lang: {METADATA['language']}
rights: "{METADATA['rights']}"
---

"""

    parts = [front_matter]
    word_count = 0

    for fname in CHAPTER_FILES:
        fpath = READER_DIR / fname
        if not fpath.exists():
            print(f"  WARNING: Missing {fname}")
            continue
        text = fpath.read_text(encoding="utf-8")
        parts.append(text)
        parts.append("\n\n")
        word_count += len(text.split())

    full_text = "".join(parts)

    # Write the concatenated manuscript for pandoc
    build_md = STAGE_DIR / "six-tongues-protocol-build.md"
    build_md.write_text(full_text, encoding="utf-8")

    print(f"  {len(CHAPTER_FILES)} files, ~{word_count:,} words")
    return build_md, word_count


def build_epub(source_md):
    """Convert markdown to EPUB using pypandoc."""
    print("[2/5] Converting to EPUB via pypandoc...")

    import pypandoc

    epub_out = STAGE_DIR / "the-six-tongues-protocol.epub"

    extra_args = [
        "--toc",
        "--toc-depth=1",
        "--split-level=1",
        f"--metadata=title:{METADATA['title']}",
        f"--metadata=author:{METADATA['author']}",
        f"--metadata=lang:{METADATA['language']}",
        "--epub-title-page=false",
    ]

    # Add cover if available
    cover = None
    for candidate in [COVER_JPG, ONEDRIVE_COVER]:
        if candidate.exists():
            cover = candidate
            break
    if cover:
        extra_args.append(f"--epub-cover-image={cover}")
        print(f"  Cover: {cover.name}")

    pypandoc.convert_file(
        str(source_md),
        "epub",
        outputfile=str(epub_out),
        extra_args=extra_args,
    )

    size_kb = epub_out.stat().st_size / 1024
    print(f"  Output: {epub_out} ({size_kb:.0f} KB)")
    return epub_out


def copy_to_onedrive(epub_path):
    """Copy EPUB to OneDrive for easy KDP upload."""
    print("[3/5] Copying to OneDrive staging...")

    ONEDRIVE_OUT.mkdir(parents=True, exist_ok=True)
    dest = ONEDRIVE_OUT / "the-six-tongues-protocol.epub"
    shutil.copy2(epub_path, dest)
    print(f"  Staged: {dest}")
    return dest


def write_build_report(word_count, epub_path):
    """Write build metadata for audit trail."""
    print("[4/5] Writing build report...")

    report = {
        "built_at": datetime.now().isoformat(),
        "word_count": word_count,
        "chapter_count": len(CHAPTER_FILES),
        "epub_path": str(epub_path),
        "epub_size_bytes": epub_path.stat().st_size,
        "source_dir": str(READER_DIR),
    }

    report_path = STAGE_DIR / "build-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"  Report: {report_path}")


def open_kdp():
    """Open KDP bookshelf in default browser."""
    print("[5/5] Opening KDP bookshelf...")
    import webbrowser

    webbrowser.open(KDP_BOOKSHELF_URL)
    print(f"  Opened: {KDP_BOOKSHELF_URL}")
    print("  Next: Click '...' > Edit content > Upload Manuscript > select the staged EPUB")


def main():
    open_browser = "--open-kdp" in sys.argv

    STAGE_DIR.mkdir(parents=True, exist_ok=True)

    source_md, word_count = build_full_manuscript()
    epub_path = build_epub(source_md)
    onedrive_path = copy_to_onedrive(epub_path)
    write_build_report(word_count, epub_path)

    if open_browser:
        open_kdp()
    else:
        print("\n[Done] EPUB staged. Run with --open-kdp to open KDP bookshelf.")
        print(f"  Upload this file: {onedrive_path}")


if __name__ == "__main__":
    main()

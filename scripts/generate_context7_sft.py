#!/usr/bin/env python3
"""Generate SFT training data from Context7 library documentation.

This script is designed to be driven by Claude Code (which has MCP access to Context7).
It reads pre-fetched markdown docs from a staging directory and converts them to
oriented SFT pairs using the auto_marker pipeline.

Workflow:
  1. Claude fetches docs via Context7 MCP → saves to training/intake/context7/
  2. This script reads those markdown files and generates oriented SFT pairs
  3. Output goes to training-data/sft/context7_harvested.jsonl

Can also accept markdown directly via stdin for piping.

Usage:
    # Process all staged docs
    python scripts/generate_context7_sft.py

    # Process a specific file
    python scripts/generate_context7_sft.py --input training/intake/context7/fastapi.md

    # Pipe markdown directly
    cat some_doc.md | python scripts/generate_context7_sft.py --stdin --library fastapi
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from training.auto_marker import (
    chunk_markdown_to_pairs,
    orient_record,
    write_oriented_jsonl,
)

INTAKE_DIR = PROJECT_ROOT / "training" / "intake" / "context7"
OUTPUT_PATH = PROJECT_ROOT / "training-data" / "sft" / "context7_harvested.jsonl"

# ---------------------------------------------------------------------------
# Target library list — what we want to harvest from Context7
# ---------------------------------------------------------------------------

TARGET_LIBRARIES = {
    # --- Cybersecurity ---
    "cryptography": {"query": "encryption, hashing, key management, TLS", "category": "cyber"},
    "owasp": {"query": "web security vulnerabilities, injection, XSS, CSRF", "category": "cyber"},
    "pyjwt": {"query": "JWT token creation, verification, claims", "category": "cyber"},
    "bcrypt": {"query": "password hashing, salt generation", "category": "cyber"},
    "paramiko": {"query": "SSH connections, key authentication, SFTP", "category": "cyber"},
    "scapy": {"query": "network packet crafting, sniffing, analysis", "category": "cyber"},

    # --- ML/AI ---
    "transformers": {"query": "model loading, fine-tuning, inference, tokenization", "category": "science"},
    "datasets": {"query": "dataset loading, processing, streaming, hub upload", "category": "science"},
    "peft": {"query": "LoRA, QLoRA, parameter efficient fine-tuning", "category": "science"},
    "trl": {"query": "SFT trainer, DPO trainer, RLHF, reward modeling", "category": "science"},
    "vllm": {"query": "LLM serving, inference optimization, batching", "category": "science"},
    "accelerate": {"query": "distributed training, mixed precision, device placement", "category": "science"},
    "torch": {"query": "tensors, autograd, neural network modules, optimization", "category": "science"},
    "numpy": {"query": "array operations, linear algebra, FFT, random", "category": "math"},
    "scipy": {"query": "optimization, signal processing, spatial, statistics", "category": "math"},

    # --- Infrastructure ---
    "fastapi": {"query": "routes, dependencies, middleware, OpenAPI, WebSocket", "category": "infra"},
    "express": {"query": "routing, middleware, error handling, request/response", "category": "infra"},
    "docker": {"query": "Dockerfile, compose, networking, volumes, multi-stage", "category": "infra"},
    "kubernetes": {"query": "pods, deployments, services, ingress, helm", "category": "infra"},
    "nginx": {"query": "reverse proxy, load balancing, SSL termination", "category": "infra"},
    "terraform": {"query": "providers, resources, modules, state management", "category": "infra"},

    # --- Testing ---
    "pytest": {"query": "fixtures, parametrize, markers, plugins, conftest", "category": "code"},
    "vitest": {"query": "test runner, mocking, assertions, coverage, watch mode", "category": "code"},
    "playwright": {"query": "browser automation, selectors, assertions, fixtures", "category": "code"},

    # --- Frontend ---
    "react": {"query": "hooks, components, state management, effects, context", "category": "code"},
    "tailwindcss": {"query": "utility classes, responsive design, dark mode, plugins", "category": "code"},
    "gradio": {"query": "interface, blocks, components, events, deployment", "category": "code"},

    # --- Data/DB ---
    "sqlalchemy": {"query": "ORM, engine, session, queries, migrations", "category": "code"},
    "redis": {"query": "caching, pub/sub, streams, data structures", "category": "infra"},
    "postgresql": {"query": "queries, indexing, JSON, full-text search, performance", "category": "infra"},

    # --- Python core ---
    "python": {"query": "asyncio, typing, dataclasses, pathlib, subprocess", "category": "code"},

    # --- Hugging Face ecosystem ---
    "huggingface_hub": {"query": "model upload, dataset push, API client, spaces", "category": "science"},
    "tokenizers": {"query": "BPE, WordPiece, tokenizer training, encoding", "category": "science"},
    "safetensors": {"query": "tensor serialization, safe loading, format spec", "category": "science"},
}


def process_staged_file(filepath: Path, library_name: str | None = None) -> list:
    """Process a single staged markdown file into oriented records."""
    name = library_name or filepath.stem
    text = filepath.read_text(encoding="utf-8", errors="ignore")

    if len(text.strip()) < 50:
        print(f"  SKIP (too short): {filepath.name}", file=sys.stderr)
        return []

    records = chunk_markdown_to_pairs(
        markdown=text,
        source_name=name,
        source_type="context7_docs",
    )
    return records


def process_all_staged() -> list:
    """Process all markdown files in the intake directory."""
    if not INTAKE_DIR.exists():
        INTAKE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created intake dir: {INTAKE_DIR}", file=sys.stderr)
        print("No files to process. Fetch docs via Context7 MCP first.", file=sys.stderr)
        return []

    all_records = []
    for md_file in sorted(INTAKE_DIR.glob("*.md")):
        records = process_staged_file(md_file)
        print(f"  {md_file.name}: {len(records)} pairs", file=sys.stderr)
        all_records.extend(records)

    return all_records


def process_stdin(library_name: str) -> list:
    """Process markdown from stdin."""
    text = sys.stdin.read()
    return chunk_markdown_to_pairs(
        markdown=text,
        source_name=library_name,
        source_type="context7_docs",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SFT from Context7 docs")
    parser.add_argument("--input", help="Process a specific markdown file")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--library", default="unknown", help="Library name (for stdin)")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output JSONL path")
    parser.add_argument("--append", action="store_true", help="Append to existing output")
    parser.add_argument("--list-targets", action="store_true", help="List target libraries")
    args = parser.parse_args()

    if args.list_targets:
        print(f"{'Library':<20} {'Category':<12} Query")
        print("-" * 80)
        for lib, cfg in TARGET_LIBRARIES.items():
            print(f"{lib:<20} {cfg['category']:<12} {cfg['query'][:50]}")
        print(f"\nTotal: {len(TARGET_LIBRARIES)} libraries")
        return

    if args.stdin:
        records = process_stdin(args.library)
    elif args.input:
        records = process_staged_file(Path(args.input))
    else:
        records = process_all_staged()

    if not records:
        print("No records generated.", file=sys.stderr)
        return

    written = write_oriented_jsonl(records, args.output, append=args.append)
    print(f"\nWrote {written} oriented records to {args.output}", file=sys.stderr)

    # Summary stats
    from collections import Counter
    layers = Counter(r.layer for r in records)
    categories = Counter(r.category for r in records)
    tongues = Counter(r.dominant_tongue for r in records)

    print(f"\n--- Layer distribution ---", file=sys.stderr)
    for k, v in layers.most_common():
        print(f"  {k}: {v}", file=sys.stderr)
    print(f"\n--- Category distribution ---", file=sys.stderr)
    for k, v in categories.most_common():
        print(f"  {k}: {v}", file=sys.stderr)
    print(f"\n--- Dominant tongue distribution ---", file=sys.stderr)
    for k, v in tongues.most_common():
        print(f"  {k}: {v}", file=sys.stderr)


if __name__ == "__main__":
    main()

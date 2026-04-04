#!/usr/bin/env python3
"""
docs_to_sft.py - Convert 280+ SCBE-AETHERMOORE markdown docs into JSONL SFT training pairs.

Walks designated doc directories, splits each file by ## headings,
generates structured Q&A pairs per section, applies quality filters,
and writes chat-format SFT JSONL.

Author: Issac Davis
Date: 2026-03-29
"""

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SOURCE_DIRS = [
    PROJECT_ROOT / "docs" / "research",
    PROJECT_ROOT / "docs" / "specs",
    PROJECT_ROOT / "docs" / "00-overview",
    PROJECT_ROOT / "docs" / "01-architecture",
    PROJECT_ROOT / "docs" / "05-industry-guides",
]

OUTPUT_DIR = PROJECT_ROOT / "training-data" / "sft"
OUTPUT_FILE = OUTPUT_DIR / "docs_auto_sft.jsonl"

SYSTEM_PROMPT = (
    "You are an expert on the SCBE-AETHERMOORE AI governance framework. "
    "You provide accurate, detailed technical explanations about its architecture, "
    "security pipeline, Sacred Tongues system, quantum axioms, and deployment patterns."
)

MIN_SECTION_CHARS = 50
MAX_RESPONSE_CHARS = 2000

# Technical terms that indicate meaningful content (at least one must be present)
TECHNICAL_TERMS = {
    # Core SCBE terms
    "scbe", "aethermoore", "aethermoor", "governance", "pipeline", "axiom",
    "hyperbolic", "poincare", "poincaré", "harmonic", "symphonic", "cipher",
    "tongue", "tongues", "langues", "sacred", "spectral", "quantum",
    # Architecture terms
    "layer", "mesh", "node", "embedding", "tensor", "manifold", "lattice",
    "topology", "topological", "hamiltonian", "mobius", "möbius",
    # Security / crypto terms
    "cryptographic", "post-quantum", "pqc", "dilithium", "kyber", "ml-dsa",
    "ml-kem", "aes", "encryption", "signature", "seal", "envelope",
    # AI / ML terms
    "model", "training", "inference", "fine-tuning", "finetuning", "sft",
    "dpo", "grpo", "rlhf", "reward", "policy", "dataset", "tokenizer",
    "transformer", "llm", "lora", "peft", "gguf",
    # Decision terms
    "allow", "deny", "quarantine", "escalate", "risk", "safety", "audit",
    # Geometry terms
    "geoseed", "sphere", "seed", "dimension", "21d", "14-layer", "6-tongue",
    "ko", "av", "ru", "ca", "um", "dr",
    # Infrastructure terms
    "api", "endpoint", "webhook", "workflow", "n8n", "docker", "kubernetes",
    "deploy", "cloud", "huggingface", "vertex", "airtable", "notion",
    # Agent terms
    "agent", "swarm", "fleet", "browser", "hydra", "aetherbrowse",
    # General technical
    "algorithm", "function", "protocol", "architecture", "implementation",
    "framework", "configuration", "schema", "parameter", "specification",
    "formula", "equation", "metric", "threshold", "gradient", "vector",
    "matrix", "coefficient", "optimization", "convergence",
}

# Patterns indicating a section is just a link list or TOC
SKIP_PATTERNS = [
    # Sections that are mostly links
    re.compile(r"^(\s*[-*]\s*\[.+?\]\(.+?\)\s*\n?){3,}$", re.MULTILINE),
    # Sections that are just "See also:" or "Related:"
    re.compile(r"^\s*(see also|related|references|links|table of contents)\s*:?\s*$", re.IGNORECASE),
]

# Code / formula indicators
CODE_FORMULA_PATTERNS = [
    re.compile(r"```"),              # fenced code block
    re.compile(r"`[^`]+`"),          # inline code
    re.compile(r"[=+\-*/^]{2,}"),   # math operators
    re.compile(r"\b\w+\(.*?\)"),    # function calls
    re.compile(r"\\frac|\\sum|\\int|\\sqrt"),  # LaTeX math
    re.compile(r"H\(.*?\)\s*="),    # formula definitions
    re.compile(r"d_H\s*="),         # distance formula
    re.compile(r"\bO\(.*?\)"),      # big-O notation
]


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean_markdown(text: str) -> str:
    """Remove markdown formatting noise while preserving technical content."""
    # Remove horizontal rules
    text = re.sub(r"^---+\s*$", "", text, flags=re.MULTILINE)
    # Remove image syntax but keep alt text
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    # Remove link syntax but keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove bold/italic markers
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def clean_heading(heading: str) -> str:
    """Clean a markdown heading for use in questions."""
    # Remove heading markers
    heading = re.sub(r"^#+\s*", "", heading)
    # Remove numbering like "1." or "1.2"
    heading = re.sub(r"^\d+(\.\d+)*\.?\s*", "", heading)
    # Remove backticks
    heading = heading.replace("`", "")
    # Remove trailing punctuation
    heading = heading.rstrip(":")
    return heading.strip()


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------

def extract_sections(content: str, filepath: Path) -> List[Tuple[str, str]]:
    """Split markdown by ## headings, returning (heading, body) pairs.

    Also includes the file-level # heading with its intro paragraph if present.
    """
    sections: List[Tuple[str, str]] = []

    # Split on ## headings (level 2)
    parts = re.split(r"^(##\s+.+)$", content, flags=re.MULTILINE)

    # Handle content before first ## heading (intro under # heading)
    if parts[0].strip():
        # Try to get the # title
        title_match = re.match(r"^#\s+(.+)$", parts[0], re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            # Body is everything after the # title line
            body_start = parts[0].index(title_match.group(0)) + len(title_match.group(0))
            body = parts[0][body_start:].strip()
            if body:
                sections.append((title, body))

    # Pair ## headings with their bodies
    i = 1
    while i < len(parts):
        if i + 1 < len(parts):
            heading = parts[i].strip()
            body = parts[i + 1].strip()
            sections.append((heading, body))
            i += 2
        else:
            # Orphan heading with no body
            i += 1

    return sections


# ---------------------------------------------------------------------------
# Quality filters
# ---------------------------------------------------------------------------

def is_link_list(text: str) -> bool:
    """Check if text is predominantly a list of links."""
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return True
    link_lines = sum(1 for l in lines if re.match(r"^\s*[-*]\s*\[", l))
    return len(lines) > 0 and link_lines / len(lines) > 0.7


def is_toc(text: str) -> bool:
    """Check if text is a table of contents."""
    lower = text.lower()
    if "table of contents" in lower:
        return True
    # If most lines are just numbered/bulleted links
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return True
    toc_lines = sum(
        1 for l in lines
        if re.match(r"^\s*(\d+\.|\-|\*)\s*\[", l)
    )
    return len(lines) >= 3 and toc_lines / len(lines) > 0.8


def has_technical_term(text: str) -> bool:
    """Check that the text contains at least one technical term."""
    lower = text.lower()
    return any(term in lower for term in TECHNICAL_TERMS)


def has_code_or_formula(text: str) -> bool:
    """Check if the section contains code blocks or mathematical formulas."""
    return any(pat.search(text) for pat in CODE_FORMULA_PATTERNS)


def should_skip_section(heading: str, body: str) -> bool:
    """Return True if this section should be skipped."""
    clean_body = body.strip()

    # Too short
    if len(clean_body) < MIN_SECTION_CHARS:
        return True

    # Just links
    if is_link_list(clean_body):
        return True

    # Just a TOC
    if is_toc(clean_body):
        return True

    # No technical content
    combined = heading + " " + clean_body
    if not has_technical_term(combined):
        return True

    # Skip "see also" / "references" sections
    heading_lower = heading.lower()
    skip_headings = {"see also", "references", "links", "table of contents", "changelog", "license"}
    clean_h = clean_heading(heading).lower()
    if clean_h in skip_headings:
        return True

    return False


# ---------------------------------------------------------------------------
# Question generation
# ---------------------------------------------------------------------------

def generate_questions(heading: str, body: str, source_file: str) -> List[str]:
    """Generate question variations from a section heading."""
    clean_h = clean_heading(heading)
    if not clean_h:
        return []

    questions = []

    # Determine question style based on heading content
    h_lower = clean_h.lower()

    # "What is" question
    if any(h_lower.startswith(w) for w in ("how", "why", "when", "where", "what")):
        # Heading is already a question
        q = clean_h
        if not q.endswith("?"):
            q += "?"
        questions.append(q)
    else:
        questions.append(f"What is {clean_h}?")

    # "Explain" question
    questions.append(f"Explain {clean_h} in the SCBE-AETHERMOORE framework.")

    # "How does" question if code/formulas present
    if has_code_or_formula(body):
        if h_lower.startswith("how"):
            pass  # Already covered
        else:
            questions.append(f"How does {clean_h} work technically?")

    return questions


# ---------------------------------------------------------------------------
# SFT pair generation
# ---------------------------------------------------------------------------

def make_sft_record(question: str, answer: str) -> Dict:
    """Create a chat-format SFT record."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
    }


def content_hash(text: str) -> str:
    """Generate a hash for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def process_file(filepath: Path, seen_hashes: Set[str]) -> List[Dict]:
    """Process a single markdown file into SFT pairs."""
    pairs: List[Dict] = []

    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  WARN: Could not read {filepath}: {e}")
        return pairs

    if not content.strip():
        return pairs

    sections = extract_sections(content, filepath)
    source_name = filepath.relative_to(PROJECT_ROOT).as_posix()

    for heading, body in sections:
        if should_skip_section(heading, body):
            continue

        # Clean the response
        response = clean_markdown(body)

        # Re-check length after cleaning (cleaning can shorten content)
        if len(response) < MIN_SECTION_CHARS:
            continue

        # Truncate if too long
        if len(response) > MAX_RESPONSE_CHARS:
            # Try to truncate at a sentence boundary
            truncated = response[:MAX_RESPONSE_CHARS]
            last_period = truncated.rfind(".")
            last_newline = truncated.rfind("\n")
            cut_at = max(last_period, last_newline)
            if cut_at > MAX_RESPONSE_CHARS * 0.6:
                response = truncated[:cut_at + 1].rstrip()
            else:
                response = truncated.rstrip()

        # Dedup check on response content
        h = content_hash(response)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        # Generate questions
        questions = generate_questions(heading, body, source_name)

        for q in questions:
            # Also dedup on the full Q+A pair
            pair_hash = content_hash(q + response)
            if pair_hash in seen_hashes:
                continue
            seen_hashes.add(pair_hash)

            pairs.append(make_sft_record(q, response))

    return pairs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("SCBE-AETHERMOORE Docs -> SFT Training Pair Generator")
    print("=" * 70)
    print()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    seen_hashes: Set[str] = set()
    all_pairs: List[Dict] = []
    total_files = 0
    total_files_scanned = 0
    dir_stats: Dict[str, Dict[str, int]] = {}

    for src_dir in SOURCE_DIRS:
        dir_label = src_dir.relative_to(PROJECT_ROOT).as_posix()
        dir_stats[dir_label] = {"files": 0, "pairs": 0, "scanned": 0}

        if not src_dir.exists():
            print(f"  SKIP: Directory not found: {dir_label}")
            continue

        md_files = sorted(src_dir.rglob("*.md"))
        if not md_files:
            print(f"  SKIP: No .md files in {dir_label}")
            continue

        dir_stats[dir_label]["scanned"] = len(md_files)
        total_files_scanned += len(md_files)
        print(f"Processing {dir_label}/ ({len(md_files)} files)...")

        for filepath in md_files:
            pairs = process_file(filepath, seen_hashes)
            if pairs:
                dir_stats[dir_label]["files"] += 1
                dir_stats[dir_label]["pairs"] += len(pairs)
                total_files += 1
                all_pairs.extend(pairs)

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for record in all_pairs:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    actual_count = len(all_pairs)

    # Print stats
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    print(f"  Output file    : {OUTPUT_FILE}")
    print(f"  Files scanned  : {total_files_scanned}")
    print(f"  Files w/ pairs : {total_files}")
    print(f"  Total pairs    : {actual_count}")
    print()
    print(f"  {'Directory':<40} {'Scanned':>8} {'W/Pairs':>8} {'Pairs':>8}")
    print(f"  {'-'*40} {'-'*8} {'-'*8} {'-'*8}")
    for dir_label, stats in dir_stats.items():
        print(f"  {dir_label:<40} {stats['scanned']:>8} {stats['files']:>8} {stats['pairs']:>8}")
    print()

    # Quick sample
    if all_pairs:
        print("Sample pair:")
        print("-" * 70)
        sample = all_pairs[0]
        print(f"  System : {sample['messages'][0]['content'][:80]}...")
        print(f"  User   : {sample['messages'][1]['content']}")
        print(f"  Assist : {sample['messages'][2]['content'][:120]}...")
        print()

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

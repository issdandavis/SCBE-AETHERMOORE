#!/usr/bin/env python3
"""
codebase_to_sft.py - Mine SCBE-AETHERMOORE codebase documentation for SFT training pairs.

Reads markdown docs and Python source docstrings, splits by section,
and generates instruction/response SFT pairs in JSONL format.

Author: Issac Davis
Date: 2026-02-21
"""

import json
import os
import re
import hashlib
import textwrap
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "training-data"
OUTPUT_FILE = OUTPUT_DIR / "sft_codebase.jsonl"

VERSION = "3.3.0"
AUTHOR = "Issac Davis"
SOURCE_TAG = "scbe_aethermoore"
ORIGIN_TAG = "codebase_docs"
DEFAULT_TRACK = "system"

GOVERNANCE_CATEGORIES = {
    "governance",
    "safety",
}

LEGACY_SOURCE_PREFIXES = (
    "src/symphonic_cipher/",
)

FUNCTION_SOURCE_PREFIXES = (
    "src/",
    "scripts/",
    "mcp/",
)

# Minimum content length (chars) for a section to generate pairs
MIN_SECTION_CHARS = 100

# Markdown documentation files to mine (relative to PROJECT_ROOT)
MD_SOURCES = [
    "README.md",
    "SYSTEM_ARCHITECTURE.md",
    "ARCHITECTURE.md",
    "SPEC.md",
    "CONCEPTS.md",
    "docs/TECHNICAL_REFERENCE.md",
    "docs/SCBE_COMPLETE_SYSTEM.md",
    "docs/AXIOM_CROSS_REFERENCE.md",
    "docs/CORE_AXIOMS_CANONICAL_INDEX.md",
    "docs/LANGUES_WEIGHTING_SYSTEM.md",
    "docs/SCBE_TOPOLOGICAL_CFI_UNIFIED.md",
    "docs/AGENT_ARCHITECTURE.md",
    "docs/CAPABILITIES.md",
    "docs/SACRED_TONGUE_SPECTRAL_MAP.md",
    "docs/SPIRALVERSE_CODEX.md",
    "docs/PHDM_BRAIN_ARCHITECTURE.md",
    "docs/PHDM_NOMENCLATURE.md",
]

# Python source files to mine for docstrings
PY_SOURCES = [
    "src/symphonic_cipher/harmonic_scaling_law.py",
    "src/symphonic_cipher/qasi_core.py",
    "src/symphonic_cipher/ai_verifier.py",
    "src/symphonic_cipher/dual_lattice_consensus.py",
    "src/symphonic_cipher/topological_cfi.py",
    "src/symphonic_cipher/core.py",
    "src/symphonic_cipher/dsp.py",
    "src/symphonic_cipher/symphonic_core.py",
    "src/symphonic_cipher/flat_slope_encoder.py",
    "src/symphonic_cipher/scbe_aethermoore_core.py",
]

# ---------------------------------------------------------------------------
# Category detection
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "math": [
        "axiom", "theorem", "proof", "formula", "equation", "convex",
        "monoton", "metric", "isometry", "lipschitz", "arcosh", "tanh",
        "d_H", "H(d", "R^(d", "eigenvalue", "norm", "gradient",
        "diffeomorphism", "gyrovector", "mobius", "poincare", "hyperbolic distance",
    ],
    "architecture": [
        "14-layer", "pipeline", "layer 1", "layer 2", "system architecture",
        "data flow", "component", "module", "implementation structure",
        "project structure", "source index",
    ],
    "governance": [
        "governance", "decision", "allow", "quarantine", "deny", "risk",
        "policy", "roundtable", "consensus", "constitutional", "escalat",
        "authorization", "tier",
    ],
    "crypto": [
        "kyber", "dilithium", "pqc", "post-quantum", "aes-256", "hkdf",
        "sha-256", "hmac", "encrypt", "signature", "dual-lattice",
        "ml-kem", "ml-dsa", "key exchange", "nonce", "replay",
    ],
    "layers": [
        "realification", "breathing transform", "phase transform",
        "spectral coherence", "spin coherence", "triadic", "harmonic wall",
        "audio axis", "realm distance", "multi-well",
    ],
    "topology": [
        "topolog", "hamiltonian path", "control-flow integrity", "cfi",
        "euler characteristic", "manifold", "quasicrystal", "phdm",
        "polyhedr", "icosahedral",
    ],
    "constants": [
        "constant", "phi_aether", "lambda_isaac", "omega_spiral",
        "golden ratio", "phi =", "sacred tongue", "six tongue",
        "langues", "weight profile", "kor'aelin", "avali", "runethic",
        "cassisivadan", "umbroth", "draumric",
    ],
    "safety": [
        "ai safety", "verifier", "ai_verifier", "intent classif",
        "malicious", "anomaly", "detect", "constitutional check",
        "audit", "compliance",
    ],
}


def classify_category(title: str, content: str) -> str:
    """Classify a section into one of the SFT categories."""
    combined = (title + " " + content).lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw.lower() in combined)
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "architecture"  # default fallback
    return best


def normalize_source_path(source_file: str) -> str:
    return source_file.replace("\\", "/")


def is_legacy_source(source_file: str) -> bool:
    normalized = normalize_source_path(source_file)
    return any(normalized.startswith(prefix) for prefix in LEGACY_SOURCE_PREFIXES)


def infer_track(category: str, source_file: str) -> str:
    """Split training records into system/governance/functions tracks."""
    normalized = normalize_source_path(source_file)
    if category in GOVERNANCE_CATEGORIES:
        return "governance"
    if any(normalized.startswith(prefix) for prefix in FUNCTION_SOURCE_PREFIXES):
        return "functions"
    return DEFAULT_TRACK


# ---------------------------------------------------------------------------
# Instruction templates
# ---------------------------------------------------------------------------

INSTRUCTION_TEMPLATES = {
    "math": [
        "Explain the mathematical foundations of {topic} in SCBE-AETHERMOORE.",
        "What are the mathematical properties of {topic} in the SCBE framework?",
        "Describe the formal axioms related to {topic} in SCBE-AETHERMOORE.",
    ],
    "architecture": [
        "Describe the architecture of {topic} in SCBE-AETHERMOORE.",
        "How is {topic} structured in the SCBE-AETHERMOORE system?",
        "What is {topic} and how does it fit into the SCBE architecture?",
    ],
    "governance": [
        "How does {topic} work in SCBE-AETHERMOORE's governance framework?",
        "Explain the governance mechanism for {topic} in SCBE-AETHERMOORE.",
        "What role does {topic} play in SCBE-AETHERMOORE decision-making?",
    ],
    "crypto": [
        "Describe the cryptographic approach to {topic} in SCBE-AETHERMOORE.",
        "How does SCBE-AETHERMOORE implement {topic} for post-quantum security?",
        "What is {topic} and how is it used in SCBE-AETHERMOORE's crypto layer?",
    ],
    "layers": [
        "How does {topic} function within the SCBE 14-layer pipeline?",
        "Explain the role of {topic} in the SCBE-AETHERMOORE pipeline.",
        "Describe {topic} as implemented in the SCBE layer architecture.",
    ],
    "topology": [
        "What is the topological approach to {topic} in SCBE-AETHERMOORE?",
        "Describe how {topic} uses topological methods in SCBE-AETHERMOORE.",
        "Explain the connection between {topic} and topology in SCBE.",
    ],
    "constants": [
        "What are the key constants and parameters for {topic} in SCBE-AETHERMOORE?",
        "Describe {topic} in the SCBE-AETHERMOORE Six Sacred Tongues system.",
        "How does {topic} define the SCBE weighting and protocol system?",
    ],
    "safety": [
        "How does SCBE-AETHERMOORE ensure AI safety through {topic}?",
        "Explain the AI safety mechanisms related to {topic} in SCBE.",
        "What is {topic} and how does it protect against AI threats in SCBE?",
    ],
}

# Generic fallback templates for variety
GENERIC_TEMPLATES = [
    "Explain {topic} in the context of the SCBE-AETHERMOORE framework.",
    "What is {topic} in SCBE-AETHERMOORE?",
    "Describe how {topic} works in SCBE-AETHERMOORE.",
    "How does SCBE-AETHERMOORE handle {topic}?",
    "What are the key aspects of {topic} in SCBE-AETHERMOORE?",
]


def select_templates(category: str, count: int, seed: int) -> List[str]:
    """Select instruction templates for a category, deterministically varied."""
    templates = INSTRUCTION_TEMPLATES.get(category, GENERIC_TEMPLATES)
    selected = []
    for i in range(count):
        idx = (seed + i) % len(templates)
        selected.append(templates[idx])
    return selected


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

def split_md_sections(text: str) -> List[Tuple[str, str]]:
    """Split markdown text into (heading, content) pairs by ## headers.

    Also handles # headers and --- separated sections.
    """
    sections = []
    lines = text.split("\n")
    current_heading = "Overview"
    current_lines: List[str] = []

    for line in lines:
        # Match ## or # headers
        header_match = re.match(r'^(#{1,3})\s+(.+)$', line)
        if header_match:
            # Save previous section
            content = "\n".join(current_lines).strip()
            if content:
                sections.append((current_heading, content))
            current_heading = header_match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    content = "\n".join(current_lines).strip()
    if content:
        sections.append((current_heading, content))

    return sections


def extract_topic_from_heading(heading: str) -> str:
    """Extract a clean topic phrase from a markdown heading."""
    # Remove numbering like "1.2", "3.1", "Part 1:"
    topic = re.sub(r'^\d+[\.\d]*\s*', '', heading)
    topic = re.sub(r'^Part\s+\d+:\s*', '', topic, flags=re.IGNORECASE)
    topic = re.sub(r'^Appendix\s+[A-Z]:\s*', '', topic, flags=re.IGNORECASE)
    # Remove parenthetical annotations
    topic = re.sub(r'\s*\([^)]*\)\s*', ' ', topic).strip()
    # Clean up
    topic = topic.strip(" :#*-")
    if not topic:
        topic = heading.strip(" :#*-")
    return topic


def clean_response(content: str) -> str:
    """Clean content for use as an SFT response.

    Preserves structure but normalizes whitespace.
    """
    # Collapse triple+ newlines into double
    content = re.sub(r'\n{3,}', '\n\n', content)
    # Strip trailing whitespace per line
    content = "\n".join(line.rstrip() for line in content.split("\n"))
    return content.strip()


# ---------------------------------------------------------------------------
# Python docstring extraction
# ---------------------------------------------------------------------------

def extract_py_docstrings(filepath: Path) -> List[Tuple[str, str]]:
    """Extract module-level and class/function docstrings from Python file."""
    sections = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, IOError):
        return sections

    # Module-level docstring
    module_match = re.match(r'^(?:#!.*\n)?(?:\s*\n)*"""(.*?)"""', text, re.DOTALL)
    if not module_match:
        module_match = re.match(r"^(?:#!.*\n)?(?:\s*\n)*'''(.*?)'''", text, re.DOTALL)
    if module_match:
        doc = module_match.group(1).strip()
        if len(doc) >= MIN_SECTION_CHARS:
            module_name = filepath.stem
            sections.append((f"Module: {module_name}", doc))

    # Class and function docstrings
    pattern = re.compile(
        r'(?:class|def)\s+(\w+)[^:]*:\s*\n\s+"""(.*?)"""',
        re.DOTALL
    )
    for match in pattern.finditer(text):
        name = match.group(1)
        doc = match.group(2).strip()
        if len(doc) >= MIN_SECTION_CHARS:
            sections.append((f"Function/Class: {name}", doc))

    return sections


# ---------------------------------------------------------------------------
# SFT pair generation
# ---------------------------------------------------------------------------

def determine_pair_count(content: str) -> int:
    """Determine how many SFT pairs to generate from section content."""
    length = len(content)
    if length < 200:
        return 1
    elif length < 600:
        return 2
    else:
        return 3


def generate_sft_id(index: int) -> str:
    """Generate a sequential SFT pair ID."""
    return f"sft-cb-{index:03d}"


def generate_pairs_from_section(
    heading: str,
    content: str,
    source_file: str,
    start_id: int,
    source_type: str = "docstring",
) -> Tuple[List[Dict], int]:
    """Generate SFT pairs from a single section.

    Returns (list_of_pairs, next_id).
    """
    pairs = []
    topic = extract_topic_from_heading(heading)
    category = classify_category(heading, content)
    count = determine_pair_count(content)

    # Use a hash-based seed for deterministic but varied template selection
    seed = int(hashlib.md5((heading + source_file).encode()).hexdigest()[:8], 16)
    templates = select_templates(category, count, seed)

    response = clean_response(content)
    track = infer_track(category, source_file)
    legacy = source_type == "legacy_docstring"

    # For multiple pairs from the same section, vary the instruction
    for i in range(count):
        if legacy:
            instruction = (
                f"Describe the intended behavior of `{topic}` from legacy module "
                f"`{source_file}` based on its docstring."
            )
        else:
            instruction = templates[i].format(topic=topic)

        rendered_response = response
        if legacy:
            rendered_response = "[LEGACY - UNVERIFIED] " + response

        pair = {
            "id": generate_sft_id(start_id),
            "category": category,
            "instruction": instruction,
            "response": rendered_response,
            "metadata": {
                "source": SOURCE_TAG,
                "version": VERSION,
                "author": AUTHOR,
                "origin": ORIGIN_TAG,
                "source_file": source_file,
                "track": track,
                "source_type": source_type,
                "quality": {
                    "dedup": True,
                    "validated": not legacy,
                },
            },
        }
        pairs.append(pair)
        start_id += 1

    return pairs, start_id


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def process_md_file(filepath: Path, rel_path: str, start_id: int) -> Tuple[List[Dict], int]:
    """Process a single markdown file into SFT pairs."""
    pairs = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, IOError) as e:
        print(f"  [SKIP] {rel_path}: {e}")
        return pairs, start_id

    sections = split_md_sections(text)
    section_count = 0

    for heading, content in sections:
        if len(content) < MIN_SECTION_CHARS:
            continue
        section_count += 1
        new_pairs, start_id = generate_pairs_from_section(
            heading, content, rel_path, start_id, source_type="markdown_doc"
        )
        pairs.extend(new_pairs)

    print(f"  [OK] {rel_path}: {section_count} sections -> {len(pairs)} pairs")
    return pairs, start_id


def process_py_file(filepath: Path, rel_path: str, start_id: int) -> Tuple[List[Dict], int]:
    """Process a single Python file for docstring-based SFT pairs."""
    pairs = []
    sections = extract_py_docstrings(filepath)

    if not sections:
        print(f"  [SKIP] {rel_path}: no substantial docstrings")
        return pairs, start_id

    section_count = 0
    for heading, content in sections:
        if len(content) < MIN_SECTION_CHARS:
            continue
        section_count += 1
        source_type = "legacy_docstring" if is_legacy_source(rel_path) else "docstring"
        new_pairs, start_id = generate_pairs_from_section(
            heading, content, rel_path, start_id, source_type=source_type
        )
        pairs.extend(new_pairs)

    print(f"  [OK] {rel_path}: {section_count} docstrings -> {len(pairs)} pairs")
    return pairs, start_id


def main():
    print("=" * 72)
    print("SCBE-AETHERMOORE Codebase -> SFT Training Pair Generator")
    print("=" * 72)

    all_pairs: List[Dict] = []
    current_id = 1

    # ---- Phase 1: Markdown documentation ----
    print("\n--- Phase 1: Mining Markdown Documentation ---")
    md_found = 0
    for rel_path in MD_SOURCES:
        filepath = PROJECT_ROOT / rel_path
        if not filepath.exists():
            print(f"  [MISS] {rel_path}: file not found")
            continue
        md_found += 1
        new_pairs, current_id = process_md_file(filepath, rel_path, current_id)
        all_pairs.extend(new_pairs)

    # Also scan for any .md files in docs/ not already listed
    docs_dir = PROJECT_ROOT / "docs"
    if docs_dir.is_dir():
        already_listed = {s.replace("/", os.sep) for s in MD_SOURCES}
        for md_file in sorted(docs_dir.glob("*.md")):
            rel = str(md_file.relative_to(PROJECT_ROOT)).replace("\\", "/")
            if rel in {s for s in MD_SOURCES}:
                continue
            # Only process files larger than 2KB to get substantial content
            if md_file.stat().st_size < 2048:
                continue
            md_found += 1
            new_pairs, current_id = process_md_file(md_file, rel, current_id)
            all_pairs.extend(new_pairs)

    print(f"\n  Markdown files processed: {md_found}")

    # ---- Phase 2: Python source docstrings ----
    print("\n--- Phase 2: Mining Python Source Docstrings ---")
    py_found = 0
    for rel_path in PY_SOURCES:
        filepath = PROJECT_ROOT / rel_path
        if not filepath.exists():
            print(f"  [MISS] {rel_path}: file not found")
            continue
        py_found += 1
        new_pairs, current_id = process_py_file(filepath, rel_path, current_id)
        all_pairs.extend(new_pairs)

    print(f"\n  Python files processed: {py_found}")

    # ---- Phase 3: Write output ----
    print("\n--- Phase 3: Writing Output ---")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"  Output: {OUTPUT_FILE}")
    print(f"  Total SFT pairs: {len(all_pairs)}")

    # ---- Summary ----
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    cat_counts: Dict[str, int] = {}
    for pair in all_pairs:
        cat = pair["category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    for cat in sorted(cat_counts):
        print(f"  {cat:15s}: {cat_counts[cat]:4d} pairs")

    print(f"  {'TOTAL':15s}: {len(all_pairs):4d} pairs")
    print(f"\n  Output file: {OUTPUT_FILE}")
    file_size = OUTPUT_FILE.stat().st_size
    print(f"  File size:   {file_size:,} bytes ({file_size / 1024:.1f} KB)")

    if len(all_pairs) >= 50:
        print("\n  [PASS] Target met: >= 50 SFT pairs generated.")
    else:
        print(f"\n  [WARN] Below target: {len(all_pairs)} < 50 pairs.")

    print("=" * 72)


if __name__ == "__main__":
    main()

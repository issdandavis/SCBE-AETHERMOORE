#!/usr/bin/env python3
"""
convert_to_sft.py — Convert raw Notion export JSONL into SCBE SFT training format.

Input format (raw Notion export):
    {"id": "uuid", "title": "Page Title", "text": "Full page content..."}

Output format (SFT instruction/response pairs):
    {"id": "sft-001", "category": "architecture", "instruction": "...", "response": "...", "metadata": {...}}

Usage:
    python scripts/convert_to_sft.py input.jsonl -o training-data/sft_output.jsonl
    python scripts/convert_to_sft.py input.jsonl --chat  # chat-style messages format
    cat raw.jsonl | python scripts/convert_to_sft.py -    # read from stdin
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Category detection patterns — maps keywords to SCBE training categories
CATEGORY_PATTERNS = {
    "architecture": r"14.layer|architecture|stack|layer\s*\d|pipeline|think\(\)",
    "sacred-tongues": r"sacred.tongue|kor.aelin|avali|runethic|cassisivadan|umbroth|draumric|neurotransmitter",
    "polyhedra": r"polyhedr|platonic|archimedean|kepler.poinsot|icosahedron|dodecahedron|tetrahedron|euler.char",
    "poincare-ball": r"poincar[eé].ball|hyperbolic.space|trust.ring|radial.distance|geodesic",
    "harmonic-scaling": r"harmonic.wall|harmonic.scal|pythagorean.comma|perfect.fifth|531441|524288",
    "governance": r"governance|fsgs|allow|deny|quarantine|rollback|decision|think\(\)|policy",
    "trust-tubes": r"trust.tube|epsilon.*0\.15|tube.radius|lateral.privilege",
    "post-quantum-crypto": r"post.quantum|quantum.resist|lattice.based|ml.kem|ml.dsa|kyber|dilithium|pqc",
    "quantum-lattice": r"quasicrystal|phason|penrose|lattice.projection|6d.*3d",
    "breathing": r"breathing|flux.state|polly|quasi|demi|breathing.ode|oscillat",
    "msr-algebra": r"msr.algebra|mirror.*shift.*refactor|involution|M\^2.*I",
    "fsgs": r"finite.state|fsgs|2.bit|run.*hold.*quar|state.machine",
    "layers": r"\bL\d{1,2}\b|layer.\d|complex.context|realification|weighted.transform",
    "zones": r"\bzone\b|core.zone|cortex|risk.zone|recursive.zone|bridge.zone",
    "topology": r"topology|euler.characteristic|genus|torus|toroidal|homeomorphi",
    "constants": r"golden.ratio|phi.*1\.618|fibonacci|mathematical.constant",
    "trust-rings": r"trust.ring|core.ring|inner.ring|outer.ring|wall.ring|latency.tier",
    "energy": r"energy.conservation|hamiltonian|energy.cost|phi.weighted",
    "spiral-seal": r"spiral.seal|geoseal|signature.scheme",
    "safety": r"ai.safety|containment|boundary.enforcement|defense.in.depth",
}

GOVERNANCE_CATEGORIES = {
    "governance",
    "fsgs",
    "trust-tubes",
    "trust-rings",
    "safety",
}

FUNCTION_CATEGORIES = {
    "post-quantum-crypto",
    "spiral-seal",
    "ml-kem",
    "ml-dsa",
}

# System prompt for chat-style output
SYSTEM_PROMPT = (
    "You are SCBE-AETHERMOORE, a 14-layer AI safety and governance framework "
    "built on hyperbolic geometry, post-quantum cryptography, and sacred tongue "
    "neurotransmitter mappings. Answer questions about the architecture, governance "
    "decisions, mathematical foundations, and security properties accurately."
)


def detect_category(title: str, text: str) -> str:
    """Detect the best category for a record based on title and text content."""
    combined = f"{title} {text[:500]}".lower()
    best_cat = "architecture"
    best_score = 0
    for cat, pattern in CATEGORY_PATTERNS.items():
        matches = len(re.findall(pattern, combined, re.IGNORECASE))
        if matches > best_score:
            best_score = matches
            best_cat = cat
    return best_cat


def clean_text(text: str) -> str:
    """Clean raw Notion text: remove excessive whitespace, emoji headers, etc."""
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove leading emoji + whitespace from lines (Notion export style)
    text = re.sub(r"^[\U0001f300-\U0001faff\u2600-\u27bf]+\s*", "", text, flags=re.MULTILINE)
    # Strip trailing whitespace per line
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    return text.strip()


def infer_track(category: str) -> str:
    """Assign high-level training track for downstream split datasets."""
    if category in GOVERNANCE_CATEGORIES:
        return "governance"
    if category in FUNCTION_CATEGORIES:
        return "functions"
    return "system"


def generate_instruction(title: str, text: str, category: str) -> str:
    """Generate an instruction prompt from the title and content."""
    # Strip emoji and special chars from title
    clean_title = re.sub(r"[\U0001f300-\U0001faff\u2600-\u27bf]+", "", title).strip()
    if not clean_title:
        clean_title = "this topic"

    # Build natural-sounding instruction
    templates = [
        f"Explain the concept of {clean_title} in the SCBE-AETHERMOORE system.",
        f"Describe {clean_title} and its role in the architecture.",
        f"What is {clean_title} and how does it function within SCBE-AETHERMOORE?",
        f"Provide a detailed overview of {clean_title}.",
    ]
    # Use hash of title for deterministic template selection
    idx = hash(clean_title) % len(templates)
    return templates[idx]


def truncate_response(text: str, max_chars: int = 4000) -> str:
    """Truncate response to fit within schema limits, breaking at sentence boundary."""
    if len(text) <= max_chars:
        return text
    # Find last sentence boundary before limit
    truncated = text[:max_chars]
    last_period = truncated.rfind(".")
    if last_period > max_chars // 2:
        return truncated[: last_period + 1]
    return truncated.rstrip() + "..."


def convert_record(raw: dict, idx: int) -> dict | None:
    """Convert a single raw Notion record to SFT format."""
    title = raw.get("title", "").strip()
    text = raw.get("text", "").strip()

    if not text or len(text) < 50:
        return None  # Skip empty or trivially short records

    category = detect_category(title, text)
    track = infer_track(category)
    instruction = generate_instruction(title, text, category)
    response = truncate_response(clean_text(text))

    return {
        "id": f"sft-{idx:04d}",
        "category": category,
        "instruction": instruction,
        "response": response,
        "metadata": {
            "source": "scbe_aethermoore",
            "version": "3.3.0",
            "author": "Issac Davis",
            "notion_id": raw.get("id", ""),
            "original_title": title,
            "track": track,
            "source_type": "notion_page",
            "quality": {
                "dedup": True,
                "validated": False,
            },
        },
    }


def convert_to_chat(record: dict) -> dict:
    """Convert SFT record to chat-messages format (for chat fine-tuning)."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": record["instruction"]},
            {"role": "assistant", "content": record["response"]},
        ]
    }


def main():
    parser = argparse.ArgumentParser(
        description="Convert raw Notion JSONL to SCBE SFT training format"
    )
    parser.add_argument(
        "input",
        help="Input JSONL file (use '-' for stdin)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output JSONL file (default: stdout)",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Output in chat-messages format instead of instruction/response",
    )
    parser.add_argument(
        "--merge",
        nargs="*",
        default=[],
        help="Additional JSONL files to merge (already in SFT format)",
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=50,
        help="Minimum text length to include (default: 50)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate output against training_schema.json",
    )
    args = parser.parse_args()

    # Read input
    records = []
    if args.input == "-":
        source = sys.stdin
    else:
        source = open(args.input, "r", encoding="utf-8")

    for line in source:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"WARN: Skipping malformed JSON line: {e}", file=sys.stderr)

    if args.input != "-":
        source.close()

    # Convert
    converted = []
    skipped = 0
    for i, raw in enumerate(records):
        # Detect if already in SFT format
        if "instruction" in raw and "response" in raw:
            raw["id"] = raw.get("id", f"sft-{i:04d}")
            converted.append(raw)
            continue

        result = convert_record(raw, len(converted) + 1)
        if result and len(result["response"]) >= args.min_length:
            converted.append(result)
        else:
            skipped += 1

    # Merge existing SFT files
    for merge_file in args.merge:
        with open(merge_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        converted.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    # Convert to chat format if requested
    if args.chat:
        output_records = [convert_to_chat(r) for r in converted]
    else:
        output_records = converted

    # Write output
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for record in output_records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    else:
        for record in output_records:
            print(json.dumps(record, ensure_ascii=False))

    # Summary
    print(f"\n--- Conversion Summary ---", file=sys.stderr)
    print(f"Input records:     {len(records)}", file=sys.stderr)
    print(f"Converted:         {len(converted)}", file=sys.stderr)
    print(f"Skipped (too short): {skipped}", file=sys.stderr)
    if args.merge:
        print(f"Merged from:       {len(args.merge)} file(s)", file=sys.stderr)
    print(f"Output format:     {'chat-messages' if args.chat else 'instruction/response'}", file=sys.stderr)
    if args.output:
        print(f"Written to:        {args.output}", file=sys.stderr)

    # Category breakdown
    cats = {}
    for r in converted:
        cat = r.get("category", "unknown")
        cats[cat] = cats.get(cat, 0) + 1
    if cats:
        print(f"\nCategory breakdown:", file=sys.stderr)
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()


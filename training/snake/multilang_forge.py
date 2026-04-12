"""Stage 6: Multi-Language Forge — Polyglot training data generation.

Takes instruction/response pairs from prior stages and generates code equivalents
across the FFX Sphere Grid. Each variant is tagged with tongue affinity coordinates.

7 Training Data Patterns:
  1. Same concept, N languages
  2. Cross-language bridge (FFI/WASM interop)
  3. Tongue migration (rewrite shifting tongue activation)
  4. Esoteric reduction (strip to pure intent)
  5. Null-pattern language (what's MISSING is the signal)
  6. International equivalent (same logic, different cultural lens)
  7. Polyglot build (3 files that compile together)
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from .config import TONGUES, TONGUE_WEIGHTS, PHI
from .sphere_grid import (
    ALL_LANGUAGES,
    FOUNDATION_LANGUAGES,
    ESOTERIC_LANGUAGES,
    INTERNATIONAL_LANGUAGES,
    LANGUAGE_BY_NAME,
    LanguageNode,
    closest_language,
    interop_path,
    languages_by_tongue,
    tongue_distance,
)


# ---------------------------------------------------------------------------
# Forge output
# ---------------------------------------------------------------------------


@dataclass
class ForgedRecord:
    """A single training record produced by the forge."""

    instruction: str
    response: str
    pattern: str        # Which of the 7 patterns generated this
    source_language: str
    target_language: str
    tongue_affinity: dict[str, float]
    sphere_coordinate: list[float]
    interop_bridge: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "instruction": self.instruction,
            "response": self.response,
            "pattern": self.pattern,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "tongue_affinity": self.tongue_affinity,
            "sphere_coordinate": self.sphere_coordinate,
            "interop_bridge": self.interop_bridge,
        }


@dataclass
class ForgeResult:
    """Output of the multi-language forge for a single input record."""

    records: list[ForgedRecord] = field(default_factory=list)
    languages_covered: list[str] = field(default_factory=list)
    patterns_used: list[str] = field(default_factory=list)
    total_variants: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "languages_covered": self.languages_covered,
            "patterns_used": self.patterns_used,
            "total_variants": self.total_variants,
        }


# ---------------------------------------------------------------------------
# Code templates per language (structural skeletons)
# ---------------------------------------------------------------------------

# These are STRUCTURAL templates — the forge fills them with domain-specific content
# based on the instruction/response pair from prior stages.

_LANG_TEMPLATES: dict[str, str] = {
    "Python": (
        "```python\n"
        "def {func_name}({params}):\n"
        '    """{docstring}"""\n'
        "    {body}\n"
        "```"
    ),
    "TypeScript": (
        "```typescript\n"
        "function {func_name}({params}): {return_type} {{\n"
        "  {body}\n"
        "}}\n"
        "```"
    ),
    "Rust": (
        "```rust\n"
        "fn {func_name}({params}) -> {return_type} {{\n"
        "    {body}\n"
        "}}\n"
        "```"
    ),
    "Go": (
        "```go\n"
        "func {func_name}({params}) {return_type} {{\n"
        "\t{body}\n"
        "}}\n"
        "```"
    ),
    "C": (
        "```c\n"
        "{return_type} {func_name}({params}) {{\n"
        "    {body}\n"
        "}}\n"
        "```"
    ),
    "Shell": (
        "```bash\n"
        "{func_name}() {{\n"
        "    {body}\n"
        "}}\n"
        "```"
    ),
    "Haskell": (
        "```haskell\n"
        "{func_name} :: {params} -> {return_type}\n"
        "{func_name} {body}\n"
        "```"
    ),
    "SQL": (
        "```sql\n"
        "-- {docstring}\n"
        "{body}\n"
        "```"
    ),
}


# ---------------------------------------------------------------------------
# Concept extraction
# ---------------------------------------------------------------------------


def _extract_concept(instruction: str, response: str) -> dict[str, str]:
    """Extract a codeable concept from an instruction/response pair.

    Returns a dict with func_name, params, body, docstring, return_type.
    """
    # Hash the content for deterministic naming
    content_hash = hashlib.md5(f"{instruction}{response}".encode()).hexdigest()[:6]

    # Extract keywords from instruction for naming
    words = re.findall(r"\b[a-z_]+\b", instruction.lower())
    meaningful = [w for w in words if len(w) > 3 and w not in {
        "what", "does", "this", "that", "with", "from", "have", "they",
        "which", "their", "about", "would", "could", "should", "there",
        "these", "those", "been", "will", "more", "when", "some",
    }][:3]

    func_name = "_".join(meaningful) if meaningful else f"process_{content_hash}"
    func_name = re.sub(r"[^a-z0-9_]", "", func_name)

    # Extract a one-line docstring from the instruction
    docstring = instruction[:100].replace('"', "'")

    # Build a minimal body from response keywords
    resp_words = response[:200].split()
    body_hint = " ".join(resp_words[:20]) + "..."

    return {
        "func_name": func_name,
        "params": "data",
        "body": f"# {body_hint}",
        "docstring": docstring,
        "return_type": "Any",
        "concept_hash": content_hash,
    }


# ---------------------------------------------------------------------------
# Pattern generators
# ---------------------------------------------------------------------------


def _pattern_1_same_concept(
    instruction: str, response: str, concept: dict, tongue_profile: dict[str, float],
) -> list[ForgedRecord]:
    """Pattern 1: Same concept expressed in N languages."""
    records = []

    # Pick languages: foundation trio + closest to tongue profile + 1 random standard
    target_langs = [l.name for l in FOUNDATION_LANGUAGES]
    closest = closest_language(tongue_profile, tier="standard")
    if closest.name not in target_langs:
        target_langs.append(closest.name)

    for lang_name in target_langs:
        lang = LANGUAGE_BY_NAME.get(lang_name)
        if not lang:
            continue

        template = _LANG_TEMPLATES.get(lang_name)
        if template:
            code = template.format(**concept)
        else:
            code = f"```{lang_name.lower()}\n// {concept['docstring']}\n// Implementation in {lang_name}\n```"

        records.append(ForgedRecord(
            instruction=f"Implement the following in {lang_name}: {instruction[:200]}",
            response=code,
            pattern="same_concept",
            source_language="natural",
            target_language=lang_name,
            tongue_affinity=lang.affinity,
            sphere_coordinate=lang.coordinate,
        ))

    return records


def _pattern_2_cross_bridge(
    instruction: str, response: str, concept: dict,
) -> list[ForgedRecord]:
    """Pattern 2: Cross-language bridge examples (FFI/WASM interop)."""
    records = []

    bridges = [
        ("Rust", "Python", "PyO3"),
        ("Rust", "TypeScript", "wasm-bindgen"),
        ("Python", "Rust", "PyO3/maturin"),
    ]

    for src, tgt, method in bridges:
        src_lang = LANGUAGE_BY_NAME.get(src)
        tgt_lang = LANGUAGE_BY_NAME.get(tgt)
        if not src_lang or not tgt_lang:
            continue

        bridge_instruction = (
            f"Write a {src} function '{concept['func_name']}' and show how to call it "
            f"from {tgt} via {method}. Context: {instruction[:150]}"
        )

        # Generate bridge code skeleton
        src_template = _LANG_TEMPLATES.get(src, "```\n// {func_name}\n```")
        src_code = src_template.format(**concept)

        bridge_code = (
            f"// {src} implementation:\n{src_code}\n\n"
            f"// {tgt} calling via {method}:\n"
            f"// import {{ {concept['func_name']} }} from './{concept['func_name']}';\n"
            f"// const result = {concept['func_name']}(data);"
        )

        records.append(ForgedRecord(
            instruction=bridge_instruction,
            response=bridge_code,
            pattern="cross_bridge",
            source_language=src,
            target_language=tgt,
            tongue_affinity=tgt_lang.affinity,
            sphere_coordinate=tgt_lang.coordinate,
            interop_bridge=method,
        ))

    return records


def _pattern_3_tongue_migration(
    instruction: str, response: str, concept: dict, tongue_profile: dict[str, float],
) -> list[ForgedRecord]:
    """Pattern 3: Tongue migration — rewrite shifting tongue activation.

    e.g., CA-style C code rewritten as AV-style Python (compute→wisdom shift).
    """
    records = []

    # Find the dominant tongue in the profile
    dominant = max(tongue_profile, key=tongue_profile.get)

    # Pick a migration target (the mirror opposite)
    from .config import TONGUE_MIRROR_PAIRS
    target_tongue = None
    for a, b in TONGUE_MIRROR_PAIRS:
        if dominant == a:
            target_tongue = b
            break
        if dominant == b:
            target_tongue = a
            break

    if not target_tongue:
        target_tongue = "AV"  # Default: migrate toward wisdom

    # Pick representative languages
    src_langs = languages_by_tongue(dominant)
    tgt_langs = languages_by_tongue(target_tongue)

    if src_langs and tgt_langs:
        src = src_langs[0]
        tgt = tgt_langs[0]

        mig_instruction = (
            f"Rewrite this {dominant}-style ({src.name}) implementation as "
            f"{target_tongue}-style ({tgt.name}). The translation is not just syntax — "
            f"it's a tongue-SHIFT from {dominant} to {target_tongue}.\n\n"
            f"Original concept: {instruction[:200]}"
        )

        records.append(ForgedRecord(
            instruction=mig_instruction,
            response=(
                f"// Tongue migration: {dominant}→{target_tongue}\n"
                f"// Source: {src.name} ({src.description})\n"
                f"// Target: {tgt.name} ({tgt.description})\n\n"
                f"// The shift changes not just syntax but PERSPECTIVE:\n"
                f"// - {dominant} sees: {_tongue_lens(dominant)}\n"
                f"// - {target_tongue} sees: {_tongue_lens(target_tongue)}\n\n"
                f"// Migrated implementation would emphasize {target_tongue} concerns."
            ),
            pattern="tongue_migration",
            source_language=src.name,
            target_language=tgt.name,
            tongue_affinity=tgt.affinity,
            sphere_coordinate=tgt.coordinate,
        ))

    return records


def _tongue_lens(tongue: str) -> str:
    """What does this tongue SEE in code?"""
    lenses = {
        "KO": "purpose, commands, what it DOES",
        "AV": "knowledge, assumptions, what it KNOWS",
        "RU": "rules, constraints, what it GOVERNS",
        "CA": "logic, computation, what it COMPUTES",
        "UM": "threats, defenses, what it PROTECTS",
        "DR": "structure, patterns, what it BUILDS",
    }
    return lenses.get(tongue, "unknown perspective")


def _pattern_4_esoteric_reduction(
    instruction: str, response: str, concept: dict,
) -> list[ForgedRecord]:
    """Pattern 4: Esoteric reduction — strip to pure intent (KO).

    Express a concept in Brainfuck/APL to force finding the raw INTENT
    underneath all the structural sugar.
    """
    records = []

    for lang in ESOTERIC_LANGUAGES[:3]:  # Brainfuck, Whitespace, Befunge
        eso_instruction = (
            f"Express the core intent of this concept in {lang.name}. "
            f"Strip away all structure — find the raw command.\n\n"
            f"Concept: {instruction[:200]}"
        )

        if lang.name == "Brainfuck":
            code = (
                f"// Brainfuck reduction of: {concept['func_name']}\n"
                f"// In BF, there is only: > < + - . , [ ]\n"
                f"// The 8 commands ARE the intent, nothing else.\n"
                f"// This forces you to find what the code ACTUALLY does.\n"
                f"++++++[>++++++++++<-]>++.  // Intent distilled"
            )
        elif lang.name == "Whitespace":
            code = (
                f"// Whitespace reduction: what's ABSENT is the program\n"
                f"// The visible code is NOTHING — only spaces/tabs/newlines matter\n"
                f"// This is the null-pattern: the training signal is in the GAPS\n"
                f"// Concept: {concept['docstring']}\n"
                f"   \t\t \t  \t\n\t\n   // Intent hidden in whitespace"
            )
        else:
            code = (
                f"// {lang.name} reduction of: {concept['func_name']}\n"
                f"// {lang.description}\n"
                f"// Reduced concept: {concept['docstring']}"
            )

        records.append(ForgedRecord(
            instruction=eso_instruction,
            response=code,
            pattern="esoteric_reduction",
            source_language="natural",
            target_language=lang.name,
            tongue_affinity=lang.affinity,
            sphere_coordinate=lang.coordinate,
        ))

    return records


def _pattern_5_null_language(
    instruction: str, response: str, concept: dict,
) -> list[ForgedRecord]:
    """Pattern 5: Null-pattern language analysis.

    What does a language LACK compared to others? The absence IS the signal.
    """
    comparisons = [
        ("Brainfuck", "Python", "structure, types, libraries, readability"),
        ("Assembly", "Rust", "memory safety, abstractions, type system"),
        ("SQL", "TypeScript", "control flow, variables, side effects"),
    ]

    records = []
    for lang_a, lang_b, lacks in comparisons:
        node_a = LANGUAGE_BY_NAME.get(lang_a)
        node_b = LANGUAGE_BY_NAME.get(lang_b)
        if not node_a or not node_b:
            continue

        dist = tongue_distance(lang_a, lang_b)

        null_instruction = (
            f"What does {lang_a} LACK compared to {lang_b} for implementing: "
            f"{instruction[:150]}? The absence is the training signal."
        )

        null_response = (
            f"Tongue distance: {dist:.4f} (phi-weighted Euclidean)\n\n"
            f"{lang_a} ({node_a.home_tongue}) lacks: {lacks}\n"
            f"{lang_b} ({node_b.home_tongue}) provides: what {lang_a} cannot express\n\n"
            f"The NULL PATTERN: everything {lang_a} forces you to do WITHOUT\n"
            f"is exactly what {lang_b} takes for granted. The gap between them\n"
            f"= the training signal. High gap = high friction = high learning."
        )

        records.append(ForgedRecord(
            instruction=null_instruction,
            response=null_response,
            pattern="null_language",
            source_language=lang_a,
            target_language=lang_b,
            tongue_affinity=node_b.affinity,
            sphere_coordinate=node_b.coordinate,
        ))

    return records


def _pattern_6_international(
    instruction: str, response: str, concept: dict,
) -> list[ForgedRecord]:
    """Pattern 6: International equivalent — same logic through different cultural lens."""
    records = []

    for lang in INTERNATIONAL_LANGUAGES[:3]:  # Wenyan, EPL, Rapira
        intl_instruction = (
            f"Translate this concept to {lang.name} ({lang.description}). "
            f"Not just syntax — express through a {lang.home_tongue} cultural lens.\n\n"
            f"Concept: {instruction[:200]}"
        )

        intl_response = (
            f"// {lang.name}: {lang.description}\n"
            f"// Home tongue: {lang.home_tongue} ({_tongue_lens(lang.home_tongue)})\n"
            f"// Cultural context shapes HOW the concept is expressed.\n"
            f"// The same algorithm looks different through {lang.home_tongue} eyes.\n\n"
            f"// Concept: {concept['func_name']}\n"
            f"// {concept['docstring']}"
        )

        records.append(ForgedRecord(
            instruction=intl_instruction,
            response=intl_response,
            pattern="international",
            source_language="English",
            target_language=lang.name,
            tongue_affinity=lang.affinity,
            sphere_coordinate=lang.coordinate,
        ))

    return records


def _pattern_7_polyglot_build(
    instruction: str, response: str, concept: dict,
) -> list[ForgedRecord]:
    """Pattern 7: Polyglot build — 3 files that compile together.

    Rust handles crypto/core, Python orchestrates, TypeScript serves the API.
    """
    func = concept["func_name"]
    doc = concept["docstring"]

    build_instruction = (
        f"Build a module where Rust handles the core logic, Python orchestrates, "
        f"and TypeScript serves the API. All 3 files must work together in one build.\n\n"
        f"Concept: {instruction[:200]}"
    )

    rust_code = (
        f"```rust\n"
        f"// rust/src/lib.rs — Core logic (UM tongue: security + performance)\n"
        f"use pyo3::prelude::*;\n\n"
        f"#[pyfunction]\n"
        f"fn {func}(data: &str) -> PyResult<String> {{\n"
        f"    // {doc}\n"
        f'    Ok(format!("processed: {{}}", data))\n'
        f"}}\n\n"
        f"#[pymodule]\n"
        f"fn core_module(m: &Bound<'_, PyModule>) -> PyResult<()> {{\n"
        f"    m.add_function(wrap_pyfunction!({func}, m)?)?;\n"
        f"    Ok(())\n"
        f"}}\n"
        f"```"
    )

    python_code = (
        f"```python\n"
        f"# orchestrator.py — Orchestration layer (AV tongue: wisdom + knowledge)\n"
        f"import core_module  # Rust via PyO3\n\n"
        f"def orchestrate(data: str) -> dict:\n"
        f'    """{doc}"""\n'
        f"    result = core_module.{func}(data)\n"
        f'    return {{"result": result, "status": "ok"}}\n'
        f"```"
    )

    ts_code = (
        f"```typescript\n"
        f"// api/server.ts — API layer (DR tongue: architecture + structure)\n"
        f"import {{ spawn }} from 'child_process';\n\n"
        f"async function handle{func.title().replace('_','')}(req: Request): Promise<Response> {{\n"
        f"  // {doc}\n"
        f"  const py = spawn('python', ['-c', `import orchestrator; print(orchestrator.orchestrate('${{req.body}}'))`]);\n"
        f"  return new Response(await collectOutput(py));\n"
        f"}}\n"
        f"```"
    )

    build_config = (
        f"```toml\n"
        f"# Build config — all 3 compile together:\n"
        f"# 1. cargo build --release (Rust → .so/.dll)\n"
        f"# 2. maturin develop (Rust → Python wheel)\n"
        f"# 3. npm run build (TypeScript → JS)\n"
        f"# 4. python orchestrator.py (ties it all together)\n"
        f"```"
    )

    response_text = f"{rust_code}\n\n{python_code}\n\n{ts_code}\n\n{build_config}"

    rust_node = LANGUAGE_BY_NAME["Rust"]
    return [ForgedRecord(
        instruction=build_instruction,
        response=response_text,
        pattern="polyglot_build",
        source_language="natural",
        target_language="Rust+Python+TypeScript",
        tongue_affinity={"KO": 0.1, "AV": 0.2, "RU": 0.1, "CA": 0.15, "UM": 0.25, "DR": 0.2},
        sphere_coordinate=rust_node.coordinate,  # Anchored on Rust (core)
        interop_bridge="PyO3+wasm-bindgen+subprocess",
    )]


# ---------------------------------------------------------------------------
# Main forge function
# ---------------------------------------------------------------------------


def forge(
    instruction: str,
    response: str,
    tongue_profile: dict[str, float],
    patterns: list[str] | None = None,
) -> ForgeResult:
    """Forge multi-language training data from an instruction/response pair.

    Args:
        instruction: Original instruction text
        response: Original response text
        tongue_profile: 6D tongue activation from auto_marker
        patterns: Which patterns to generate (None = all 7)

    Returns:
        ForgeResult with all generated records
    """
    concept = _extract_concept(instruction, response)

    all_patterns = {
        "same_concept": lambda: _pattern_1_same_concept(instruction, response, concept, tongue_profile),
        "cross_bridge": lambda: _pattern_2_cross_bridge(instruction, response, concept),
        "tongue_migration": lambda: _pattern_3_tongue_migration(instruction, response, concept, tongue_profile),
        "esoteric_reduction": lambda: _pattern_4_esoteric_reduction(instruction, response, concept),
        "null_language": lambda: _pattern_5_null_language(instruction, response, concept),
        "international": lambda: _pattern_6_international(instruction, response, concept),
        "polyglot_build": lambda: _pattern_7_polyglot_build(instruction, response, concept),
    }

    selected = patterns or list(all_patterns.keys())

    records: list[ForgedRecord] = []
    patterns_used: list[str] = []

    for pat_name in selected:
        gen = all_patterns.get(pat_name)
        if gen:
            generated = gen()
            records.extend(generated)
            if generated:
                patterns_used.append(pat_name)

    languages_covered = list({r.target_language for r in records})

    return ForgeResult(
        records=records,
        languages_covered=sorted(languages_covered),
        patterns_used=patterns_used,
        total_variants=len(records),
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_instruction = "How does OAuth2 authentication work?"
    test_response = (
        "OAuth2 uses bearer tokens for API authentication. "
        "Always validate tokens server-side to prevent injection attacks."
    )
    test_profile = {"KO": 0.05, "AV": 0.10, "RU": 0.15, "CA": 0.20, "UM": 0.35, "DR": 0.15}

    result = forge(test_instruction, test_response, test_profile)

    print(f"Multi-Language Forge")
    print(f"  Total variants:    {result.total_variants}")
    print(f"  Languages covered: {result.languages_covered}")
    print(f"  Patterns used:     {result.patterns_used}")

    for rec in result.records[:3]:
        print(f"\n  [{rec.pattern}] {rec.source_language} → {rec.target_language}")
        print(f"    Instruction: {rec.instruction[:80]}...")

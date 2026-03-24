"""
Auto-Ledger: SFT Data Quality Pipeline
========================================

Takes raw SFT pairs, audits them, encodes through the 21D PHDM embedding,
maps through Sacred Tongue domain separation, and produces clean training data.

Pipeline:
  Raw SFT pair
    → Quality audit (length, format, duplicates)
    → PHDM 21D embedding (categorization)
    → Sacred Tongue domain tagging (which tongue governs this data)
    → Curriculum level assignment (beginner → advanced)
    → Clean JSONL output with full metadata

Usage:
    python -m src.training.auto_ledger                    # process all sft_records
    python -m src.training.auto_ledger --push             # process + push to HF
    python -m src.training.auto_ledger --file path.jsonl  # process specific file
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

# =============================================================================
# Quality Thresholds
# =============================================================================

MIN_INSTRUCTION_LENGTH = 10
MAX_INSTRUCTION_LENGTH = 2000
MIN_OUTPUT_LENGTH = 5
MAX_OUTPUT_LENGTH = 10000
DUPLICATE_HASH_SET: set[str] = set()


# =============================================================================
# Curriculum Levels
# =============================================================================


class CurriculumLevel:
    """Progressive learning levels — the model advances through these."""

    FOUNDATION = "foundation"  # Basic Q&A, simple governance
    PRACTITIONER = "practitioner"  # Multi-step tasks, tongue encoding
    SPECIALIST = "specialist"  # Domain-specific (crypto, browser, lore)
    ARCHITECT = "architect"  # System-level decisions, cross-domain
    MASTER = "master"  # Novel situations, creative synthesis


# Complexity scoring keywords
_FOUNDATION_KEYWORDS = {"what", "define", "list", "explain", "describe"}
_PRACTITIONER_KEYWORDS = {"how", "implement", "build", "configure", "setup"}
_SPECIALIST_KEYWORDS = {"optimize", "debug", "secure", "encrypt", "governance"}
_ARCHITECT_KEYWORDS = {"design", "architect", "integrate", "scale", "coordinate"}
_MASTER_KEYWORDS = {"novel", "creative", "synthesize", "invent", "research"}


# =============================================================================
# Sacred Tongue Domain Mapping
# =============================================================================

TONGUE_DOMAIN_KEYWORDS = {
    "KO": {"intent", "command", "control", "flow", "nonce", "orchestrate", "decide", "route"},
    "AV": {"transport", "context", "metadata", "header", "api", "message", "send", "receive"},
    "RU": {"policy", "rule", "bind", "salt", "constraint", "validate", "enforce", "permission"},
    "CA": {"compute", "cipher", "encrypt", "decrypt", "transform", "process", "execute", "calculate"},
    "UM": {"security", "redact", "hide", "veil", "protect", "shield", "obscure", "mask"},
    "DR": {"schema", "structure", "auth", "tag", "verify", "sign", "certify", "format"},
}


# =============================================================================
# Data Entry (ledgered SFT pair)
# =============================================================================


@dataclass
class LedgerEntry:
    """A fully audited, encoded SFT training pair."""

    instruction: str
    output: str
    label: str

    # Quality metrics
    quality_score: float = 0.0
    instruction_length: int = 0
    output_length: int = 0
    is_duplicate: bool = False

    # PHDM embedding
    phdm_category: str = "unknown"
    phdm_confidence: float = 0.0
    phdm_embedding: list[float] = field(default_factory=list)

    # Sacred Tongue domain
    primary_tongue: str = "KO"
    tongue_scores: dict[str, float] = field(default_factory=dict)

    # Curriculum
    curriculum_level: str = CurriculumLevel.FOUNDATION
    complexity_score: float = 0.0

    # Provenance
    source_file: str = ""
    content_hash: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_training_dict(self) -> dict:
        """Output format for HuggingFace training."""
        return {
            "instruction": self.instruction,
            "output": self.output,
            "label": self.label,
            "tongue": self.primary_tongue,
            "curriculum": self.curriculum_level,
            "quality": round(self.quality_score, 3),
            "complexity": round(self.complexity_score, 3),
            "phdm_category": self.phdm_category,
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
        }

    def to_full_dict(self) -> dict:
        """Full metadata for audit trail."""
        d = self.to_training_dict()
        d.update(
            {
                "instruction_length": self.instruction_length,
                "output_length": self.output_length,
                "is_duplicate": self.is_duplicate,
                "phdm_confidence": round(self.phdm_confidence, 3),
                "tongue_scores": {k: round(v, 3) for k, v in self.tongue_scores.items()},
                "source_file": self.source_file,
            }
        )
        return d


# =============================================================================
# PHDM Classifier (reuse from dual_core)
# =============================================================================

_phdm_classifier = None


def get_phdm_classifier():
    """Lazy-load PHDM classifier."""
    global _phdm_classifier
    if os.environ.get("SCBE_DISABLE_HF_CLASSIFIER", "").strip().lower() in {"1", "true", "yes", "on"}:
        return None
    if _phdm_classifier is None:
        try:
            from src.kernel.dual_core import PHDMClassifier

            _phdm_classifier = PHDMClassifier.from_hub()
        except Exception as e:
            print(f"[LEDGER] PHDM not available: {e}")
    return _phdm_classifier


# =============================================================================
# Pipeline Steps
# =============================================================================


def audit_quality(instruction: str, output: str) -> tuple[float, list[str]]:
    """Step 1: Quality audit. Returns (score, issues)."""
    issues = []
    score = 1.0

    # Length checks
    if len(instruction) < MIN_INSTRUCTION_LENGTH:
        issues.append("instruction_too_short")
        score -= 0.3
    if len(instruction) > MAX_INSTRUCTION_LENGTH:
        issues.append("instruction_too_long")
        score -= 0.1
    if len(output) < MIN_OUTPUT_LENGTH:
        issues.append("output_too_short")
        score -= 0.3
    if len(output) > MAX_OUTPUT_LENGTH:
        issues.append("output_too_long")
        score -= 0.1

    # Content checks
    if instruction.strip() == output.strip():
        issues.append("instruction_equals_output")
        score -= 0.5
    if not instruction.strip() or not output.strip():
        issues.append("empty_content")
        score = 0.0

    # Format checks
    if instruction.count("\n") > 50:
        issues.append("excessive_newlines_instruction")
        score -= 0.1

    # Duplicate check
    content_hash = hashlib.sha256(f"{instruction}::{output}".encode()).hexdigest()[:16]
    if content_hash in DUPLICATE_HASH_SET:
        issues.append("duplicate")
        score -= 0.5
    DUPLICATE_HASH_SET.add(content_hash)

    return max(0.0, min(1.0, score)), issues


def classify_phdm(text: str) -> tuple[str, float, list[float]]:
    """Step 2: PHDM 21D embedding classification."""
    classifier = get_phdm_classifier()
    if classifier is None:
        return "unknown", 0.0, []

    categories = classifier.classify(text, top_k=1)
    embedding = classifier.embed(text).tolist()

    if categories:
        return categories[0][0], categories[0][1], embedding
    return "unknown", 0.0, embedding


def assign_tongue(instruction: str, output: str) -> tuple[str, dict[str, float]]:
    """Step 3: Sacred Tongue domain assignment."""
    combined = f"{instruction} {output}".lower()
    tokens = set(combined.split())

    scores = {}
    for tongue, keywords in TONGUE_DOMAIN_KEYWORDS.items():
        overlap = len(tokens & keywords)
        scores[tongue] = overlap / max(len(keywords), 1)

    # Default to KO if no clear domain
    if max(scores.values()) == 0:
        scores["KO"] = 0.1

    primary = max(scores, key=lambda k: scores[k])
    return primary, scores


def assign_curriculum(instruction: str, output: str) -> tuple[str, float]:
    """Step 4: Curriculum level assignment."""
    combined = f"{instruction} {output}".lower()
    tokens = set(combined.split())

    # Score each level
    scores = {
        CurriculumLevel.FOUNDATION: len(tokens & _FOUNDATION_KEYWORDS) * 1.0,
        CurriculumLevel.PRACTITIONER: len(tokens & _PRACTITIONER_KEYWORDS) * 2.0,
        CurriculumLevel.SPECIALIST: len(tokens & _SPECIALIST_KEYWORDS) * 3.0,
        CurriculumLevel.ARCHITECT: len(tokens & _ARCHITECT_KEYWORDS) * 4.0,
        CurriculumLevel.MASTER: len(tokens & _MASTER_KEYWORDS) * 5.0,
    }

    # Add complexity from length
    word_count = len(combined.split())
    if word_count > 200:
        scores[CurriculumLevel.ARCHITECT] += 2.0
    if word_count > 500:
        scores[CurriculumLevel.MASTER] += 2.0

    best_level = max(scores, key=lambda k: scores[k])
    complexity = sum(scores.values()) / max(sum(1 for v in scores.values() if v > 0), 1)

    return best_level, complexity


# =============================================================================
# Main Pipeline
# =============================================================================


def process_pair(instruction: str, output: str, label: str = "general", source_file: str = "") -> LedgerEntry | None:
    """Run a single SFT pair through the full pipeline."""

    # Step 1: Quality audit
    quality, issues = audit_quality(instruction, output)
    is_duplicate = "duplicate" in issues

    # Skip zero-quality entries
    if quality <= 0.0:
        return None

    # Step 2: PHDM classification
    phdm_cat, phdm_conf, phdm_emb = classify_phdm(instruction)

    # Step 3: Tongue domain
    tongue, tongue_scores = assign_tongue(instruction, output)

    # Step 4: Curriculum level
    level, complexity = assign_curriculum(instruction, output)

    # Build ledger entry
    content_hash = hashlib.sha256(f"{instruction}::{output}".encode()).hexdigest()[:16]

    return LedgerEntry(
        instruction=instruction,
        output=output,
        label=label,
        quality_score=quality,
        instruction_length=len(instruction),
        output_length=len(output),
        is_duplicate=is_duplicate,
        phdm_category=phdm_cat,
        phdm_confidence=phdm_conf,
        phdm_embedding=phdm_emb[:21] if phdm_emb else [],  # 21D
        primary_tongue=tongue,
        tongue_scores=tongue_scores,
        curriculum_level=level,
        complexity_score=complexity,
        source_file=source_file,
        content_hash=content_hash,
    )


def process_jsonl_file(path: Path) -> list[LedgerEntry]:
    """Process a JSONL file of SFT pairs."""
    entries = []
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                instruction = data.get("instruction", data.get("input", ""))
                output = data.get("output", data.get("response", ""))
                label = data.get("label", "general")

                entry = process_pair(instruction, output, label, source_file=str(path))
                if entry:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue
    return entries


def run_pipeline(sft_dir: Path | None = None, push_to_hf: bool = False) -> dict:
    """Run the full auto-ledger pipeline."""
    if sft_dir is None:
        sft_dir = Path(__file__).resolve().parent.parent.parent / "training" / "sft_records"

    all_entries: list[LedgerEntry] = []
    files_processed = 0

    # Process all JSONL files
    for jsonl_file in sorted(sft_dir.glob("*.jsonl")):
        print(f"  Processing {jsonl_file.name}...")
        entries = process_jsonl_file(jsonl_file)
        all_entries.extend(entries)
        files_processed += 1
        print(f"    {len(entries)} clean entries from {jsonl_file.name}")

    if not all_entries:
        print("No entries to process.")
        return {"total": 0}

    # Write clean output
    out_dir = Path(__file__).resolve().parent.parent.parent / "training" / "ledgered"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Training-ready file (minimal, clean)
    train_file = out_dir / "sft_ledgered_clean.jsonl"
    with open(train_file, "w", encoding="utf-8") as f:
        for entry in all_entries:
            if entry.quality_score >= 0.5 and not entry.is_duplicate:
                f.write(json.dumps(entry.to_training_dict()) + "\n")

    # Full audit trail
    audit_file = out_dir / "sft_ledgered_full.jsonl"
    with open(audit_file, "w", encoding="utf-8") as f:
        for entry in all_entries:
            f.write(json.dumps(entry.to_full_dict()) + "\n")

    # Per-curriculum splits
    for level in [
        CurriculumLevel.FOUNDATION,
        CurriculumLevel.PRACTITIONER,
        CurriculumLevel.SPECIALIST,
        CurriculumLevel.ARCHITECT,
        CurriculumLevel.MASTER,
    ]:
        level_entries = [
            e for e in all_entries if e.curriculum_level == level and e.quality_score >= 0.5 and not e.is_duplicate
        ]
        if level_entries:
            level_file = out_dir / f"sft_{level}.jsonl"
            with open(level_file, "w", encoding="utf-8") as f:
                for entry in level_entries:
                    f.write(json.dumps(entry.to_training_dict()) + "\n")

    # Per-tongue splits
    for tongue in ["KO", "AV", "RU", "CA", "UM", "DR"]:
        tongue_entries = [
            e for e in all_entries if e.primary_tongue == tongue and e.quality_score >= 0.5 and not e.is_duplicate
        ]
        if tongue_entries:
            tongue_file = out_dir / f"sft_tongue_{tongue}.jsonl"
            with open(tongue_file, "w", encoding="utf-8") as f:
                for entry in tongue_entries:
                    f.write(json.dumps(entry.to_training_dict()) + "\n")

    # Stats
    clean_count = sum(1 for e in all_entries if e.quality_score >= 0.5 and not e.is_duplicate)
    duplicate_count = sum(1 for e in all_entries if e.is_duplicate)
    low_quality_count = sum(1 for e in all_entries if e.quality_score < 0.5)

    curriculum_dist = {}
    tongue_dist = {}
    for e in all_entries:
        if e.quality_score >= 0.5 and not e.is_duplicate:
            curriculum_dist[e.curriculum_level] = curriculum_dist.get(e.curriculum_level, 0) + 1
            tongue_dist[e.primary_tongue] = tongue_dist.get(e.primary_tongue, 0) + 1

    stats = {
        "files_processed": files_processed,
        "total_raw": len(all_entries),
        "clean": clean_count,
        "duplicates_removed": duplicate_count,
        "low_quality_removed": low_quality_count,
        "curriculum_distribution": curriculum_dist,
        "tongue_distribution": tongue_dist,
        "output_dir": str(out_dir),
    }

    # Save stats
    with open(out_dir / "ledger_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    # Push to HuggingFace
    if push_to_hf:
        try:
            from huggingface_hub import HfApi

            api = HfApi(token=os.environ.get("HF_TOKEN"))
            api.upload_file(
                path_or_fileobj=str(train_file),
                path_in_repo="data/sft_ledgered_clean.jsonl",
                repo_id="issdandavis/scbe-aethermoore-training-data",
                repo_type="dataset",
            )
            print("Pushed ledgered data to HuggingFace")
        except Exception as e:
            print(f"HF push failed: {e}")

    return stats


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    push = "--push" in args

    print("=" * 60)
    print("  SCBE Auto-Ledger: SFT Data Quality Pipeline")
    print("=" * 60)

    stats = run_pipeline(push_to_hf=push)

    print(f"\n  Raw:       {stats.get('total_raw', 0)}")
    print(f"  Clean:     {stats.get('clean', 0)}")
    print(f"  Dupes:     {stats.get('duplicates_removed', 0)}")
    print(f"  Low-Q:     {stats.get('low_quality_removed', 0)}")
    print(f"\n  Curriculum: {stats.get('curriculum_distribution', {})}")
    print(f"  Tongues:    {stats.get('tongue_distribution', {})}")
    print(f"\n  Output:    {stats.get('output_dir', '')}")

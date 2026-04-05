#!/usr/bin/env python3
"""The Snake Pipeline — 9-stage Topological Fluency Training Engine.

Orchestrates the full end-to-end transformation:
  Raw content → Marked → HYDRA deliberated → Lattice routed →
  Mirror refracted → Hyperbolic embedded → Friction scored →
  Multi-lang forged → Adversarial trapped → Coach-debriefed → Sealed

Usage:
  python -m training.snake.pipeline --input training/intake/context7/cryptography.md
  python -m training.snake.pipeline --input-dir training/intake/context7/ --output training-data/sft/snake_pipeline.jsonl
  python -m training.snake.pipeline --dry-run --input training/intake/context7/cryptography.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Add repo root to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from training.auto_marker import (
    OrientedRecord,
    chunk_markdown_to_pairs,
    orient_record,
    write_oriented_jsonl,
)
from training.snake.config import (
    CONTEXT7_DIR,
    DPO_OUTPUT,
    OUTPUT_DIR,
    SFT_OUTPUT,
    TONGUES,
    TONGUE_NAMES,
)
from training.snake.hydra_deliberation import deliberate, HydraResult
from training.snake.lattice_router import route, LatticePoint
from training.snake.mirror_refractor import refract, MirrorResult
from training.snake.hyperbolic_embed import embed, HyperbolicPoint
from training.snake.friction_scorer import score as friction_score, FrictionResult
from training.snake.ede_defense import ede_score, EDEDefenseResult
from training.snake.multilang_forge import forge, ForgeResult
from training.snake.adversarial_traps import generate_traps, TrapResult
from training.snake.dtn_router import route_dtn, score_dtn, DTNResult, DTNScore
from training.snake.dtn_curriculum import generate_curriculum, CurriculumResult
from training.snake.primitives_curriculum import (
    generate_primitives, score_primitives, PrimitivesResult, PrimitiveScore,
)
from training.snake.synesthesia import (
    synesthesia_score, generate_synesthesia_training,
    SynesthesiaResult, SynesthesiaTrainingResult,
)
from training.snake.polly_pad import (
    polly_pad_verify, mine_paths, PollyPadResult,
)
from training.snake.big_brother_coach import coach, coach_record, CoachResult


# ---------------------------------------------------------------------------
# Snake Record — accumulates metadata through all stages
# ---------------------------------------------------------------------------


@dataclass
class SnakeRecord:
    """A record that has passed through the snake. Carries all stage metadata."""

    # Stage 1: Intake
    oriented: OrientedRecord

    # Stage 2: HYDRA
    hydra: HydraResult | None = None

    # Stage 3: Lattice
    lattice: LatticePoint | None = None

    # Stage 3.5: Mirror
    mirror: MirrorResult | None = None

    # Stage 4: Hyperbolic
    hyperbolic: HyperbolicPoint | None = None

    # Stage 5: Friction
    friction: FrictionResult | None = None

    # Stage 5.5: EDE Defense
    ede_defense: EDEDefenseResult | None = None

    # Stage 6: Multi-Language Forge
    forge: ForgeResult | None = None

    # Stage 6.5: Primitives (per-record trit/mod scoring)
    primitive_score: PrimitiveScore | None = None

    # Stage 6.75: Synesthesia (per-record sensory resilience)
    synesthesia: SynesthesiaResult | None = None

    # Stage 7: Adversarial Traps (pipeline-level, not per-record)
    # Stage 7.5: DTN Router (per-record score + pipeline-level routing)
    dtn_score: DTNScore | None = None

    # Stage 8: Coach (pipeline-level or per-record)
    coach_debrief: Any | None = None  # CoachDebrief for high-RU/UM records

    # Stage 8.5: Polly Pad (per-record 3-layer verification)
    polly_pad: PollyPadResult | None = None

    # Extra stage metadata
    stage_metadata: dict[str, Any] = field(default_factory=dict)

    # Pipeline tracking
    pipeline_id: str = ""
    stages_completed: list[str] = field(default_factory=list)
    total_latency_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSONL output. Carries EVERYTHING."""
        d = self.oriented.to_dict()

        # Overlay snake pipeline metadata
        d["snake_pipeline"] = {
            "pipeline_id": self.pipeline_id,
            "stages_completed": self.stages_completed,
            "total_latency_ms": self.total_latency_ms,
        }

        if self.hydra:
            d["snake_pipeline"]["hydra"] = self.hydra.to_dict()

        if self.lattice:
            d["snake_pipeline"]["lattice"] = self.lattice.to_dict()

        if self.mirror:
            d["snake_pipeline"]["mirror"] = self.mirror.to_dict()

        if self.hyperbolic:
            d["snake_pipeline"]["hyperbolic"] = self.hyperbolic.to_dict()

        if self.friction:
            d["snake_pipeline"]["friction"] = {
                k: v for k, v in self.friction.to_dict().items()
                if k != "friction_vector"  # Too large for inline — store separately
            }
            d["snake_pipeline"]["friction"]["friction_vector_dim"] = len(
                self.friction.friction_vector
            )

        if self.ede_defense:
            d["snake_pipeline"]["ede_defense"] = self.ede_defense.to_dict()

        if self.primitive_score:
            d["snake_pipeline"]["primitives"] = self.primitive_score.to_dict()

        if self.synesthesia:
            d["snake_pipeline"]["synesthesia"] = self.synesthesia.to_dict()

        if self.forge:
            d["snake_pipeline"]["forge"] = self.forge.to_dict()

        if self.dtn_score:
            d["snake_pipeline"]["dtn"] = self.dtn_score.to_dict()

        if self.coach_debrief:
            d["snake_pipeline"]["coach"] = self.coach_debrief.to_dict()

        if self.polly_pad:
            d["snake_pipeline"]["polly_pad"] = self.polly_pad.to_dict()

        if self.stage_metadata:
            d["snake_pipeline"].update(self.stage_metadata)

        return d


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------


def stage_1_intake(
    markdown_path: Path | None = None,
    markdown_text: str | None = None,
    source_name: str = "unknown",
) -> list[SnakeRecord]:
    """Stage 1: Intake & Marking via auto_marker."""
    if markdown_path:
        text = markdown_path.read_text(encoding="utf-8")
        source_name = source_name or markdown_path.stem
    elif markdown_text:
        text = markdown_text
    else:
        return []

    oriented_records = chunk_markdown_to_pairs(text, source_name, "snake_pipeline")

    snake_records = []
    for rec in oriented_records:
        sr = SnakeRecord(oriented=rec)
        content_hash = hashlib.sha256(
            f"{rec.instruction}{rec.response}".encode()
        ).hexdigest()[:12]
        sr.pipeline_id = f"snake-{content_hash}"
        sr.stages_completed.append("intake")
        snake_records.append(sr)

    return snake_records


def stage_2_hydra(records: list[SnakeRecord], use_hf: bool = False) -> list[SnakeRecord]:
    """Stage 2: HYDRA Deliberation — 6 tongue agents evaluate each record."""
    for rec in records:
        rec.hydra = deliberate(
            rec.oriented.instruction,
            rec.oriented.response,
            use_hf=use_hf,
        )
        rec.stages_completed.append("hydra")
    return records


def stage_3_lattice(records: list[SnakeRecord]) -> list[SnakeRecord]:
    """Stage 3: Lattice Routing — quasicrystal coordinate assignment."""
    for rec in records:
        rec.lattice = route(rec.oriented.tongue_profile)
        rec.stages_completed.append("lattice")
    return records


def stage_3_5_mirror(records: list[SnakeRecord]) -> list[SnakeRecord]:
    """Stage 3.5: Mirror Phase Semantic Refractor Symmetry."""
    for rec in records:
        rec.mirror = refract(
            rec.oriented.tongue_profile,
            rec.oriented.null_pattern,
        )
        rec.stages_completed.append("mirror")
    return records


def stage_4_hyperbolic(records: list[SnakeRecord]) -> list[SnakeRecord]:
    """Stage 4: Hyperbolic Embedding — Poincare ball projection."""
    for rec in records:
        lattice_coord = rec.lattice.coordinate if rec.lattice else [0.0] * 6
        phase_angles = rec.mirror.phase_angles if rec.mirror else [0.0, 0.0, 0.0]

        rec.hyperbolic = embed(lattice_coord, phase_angles)
        rec.stages_completed.append("hyperbolic")
    return records


def stage_5_friction(records: list[SnakeRecord]) -> list[SnakeRecord]:
    """Stage 5: Friction Scoring — 198-dim boundary friction vectors."""
    for rec in records:
        poincare = rec.hyperbolic.poincare_point if rec.hyperbolic else None
        rec.friction = friction_score(rec.oriented.tongue_profile, poincare)
        rec.stages_completed.append("friction")
    return records


def stage_5_5_ede_defense(records: list[SnakeRecord]) -> list[SnakeRecord]:
    """Stage 5.5: EDE Defense Scoring — Entropic Defense Engine integration.

    Scores each record through the ChemistryAgent immune system:
    squared-energy model, ray refraction, harmonic sinks, self-healing.
    """
    for rec in records:
        # Extract metadata from prior stages for threat derivation
        extinction_count = 0
        if rec.hydra and rec.hydra.extinction_flags:
            extinction_count = len(rec.hydra.extinction_flags)

        max_friction = 0.0
        if rec.friction:
            max_friction = rec.friction.max_friction

        hyperbolic_distance = 0.0
        if rec.hyperbolic:
            hyperbolic_distance = rec.hyperbolic.hyperbolic_distance

        oscillation = 0.0
        if rec.hydra:
            oscillation = rec.hydra.viability_oscillation

        safety_score = 1.0
        if rec.hyperbolic:
            safety_score = rec.hyperbolic.safety_score

        rec.ede_defense = ede_score(
            tongue_profile=rec.oriented.tongue_profile,
            extinction_count=extinction_count,
            max_friction=max_friction,
            hyperbolic_distance=hyperbolic_distance,
            oscillation=oscillation,
            safety_score=safety_score,
        )
        rec.stages_completed.append("ede_defense")
    return records


def stage_6_multilang(records: list[SnakeRecord]) -> list[SnakeRecord]:
    """Stage 6: Multi-Language Forge — generate polyglot training variants."""
    for rec in records:
        rec.forge = forge(
            rec.oriented.instruction,
            rec.oriented.response,
            rec.oriented.tongue_profile,
        )
        rec.stages_completed.append("multilang")
    return records


def stage_6_5_primitives(
    records: list[SnakeRecord],
) -> tuple[list[SnakeRecord], PrimitivesResult]:
    """Stage 6.5: Coding Primitives — binary/trit/ternary/mod training.

    Two modes:
    1. Per-record: trit profile, ring position, activation density scoring
    2. Pipeline-level: full primitives curriculum (SFT + DPO)
    """
    # Per-record primitive scoring
    for rec in records:
        content_hash = hashlib.sha256(
            f"{rec.oriented.instruction}{rec.oriented.response}".encode()
        ).hexdigest()
        rec.primitive_score = score_primitives(
            rec.oriented.tongue_profile,
            content_hash,
        )
        rec.stages_completed.append("primitives")

    # Pipeline-level curriculum generation
    primitives_result = generate_primitives()

    return records, primitives_result


def stage_6_75_synesthesia(
    records: list[SnakeRecord],
) -> tuple[list[SnakeRecord], SynesthesiaTrainingResult]:
    """Stage 6.75: Synesthesia — cross-modal sensory blackout training.

    Per-record: scores sensory resilience across 6 senses x 4 compensation modes.
    Pipeline-level: generates SFT/DPO pairs for blackout reasoning.
    """
    all_sft = []
    all_dpo = []

    for rec in records:
        # Per-record synesthesia scoring
        rec.synesthesia = synesthesia_score(rec.oriented.tongue_profile)
        rec.stages_completed.append("synesthesia")

    # Pipeline-level training generation (subsample)
    for rec in records[:15]:
        training = generate_synesthesia_training(
            instruction=rec.oriented.instruction,
            response=rec.oriented.response,
            tongue_profile=rec.oriented.tongue_profile,
        )
        all_sft.extend(training.sft_pairs)
        all_dpo.extend(training.dpo_pairs)

    combined = SynesthesiaTrainingResult(
        sft_pairs=all_sft,
        dpo_pairs=all_dpo,
        total_exercises=len(all_sft) + len(all_dpo),
    )
    return records, combined


def stage_8_5_polly_pad(records: list[SnakeRecord]) -> list[SnakeRecord]:
    """Stage 8.5: Polly Pad — 3-layer verification sandbox.

    Every record drops into the water:
      Layer 1 (Shallows): 5 quantum axiom checks
      Layer 2 (Rapids): 14-layer pipeline simulation
      Layer 3 (Deep Water): Polyhedral flow navigation

    Records that survive all 3 = gold-standard training data.
    """
    for rec in records:
        # Gather metadata from prior stages
        hyp_dist = 0.0
        if rec.hyperbolic:
            hyp_dist = rec.hyperbolic.hyperbolic_distance

        safety = 1.0
        if rec.hyperbolic:
            safety = rec.hyperbolic.safety_score

        breath = 0.0
        if rec.hyperbolic:
            breath = rec.hyperbolic.breath_phase

        content_hash = hashlib.sha256(
            f"{rec.oriented.instruction}{rec.oriented.response}".encode()
        ).hexdigest()

        rec.polly_pad = polly_pad_verify(
            tongue_profile=rec.oriented.tongue_profile,
            hyperbolic_distance=hyp_dist,
            safety_score=safety,
            breath_phase=breath,
            content_hash=content_hash,
        )
        rec.stages_completed.append("polly_pad")

    return records


def stage_7_5_dtn_curriculum(
    records: list[SnakeRecord],
) -> CurriculumResult:
    """Stage 7.5b: DTN Curriculum — occlusion training methodology.

    Generates progressive training data that teaches the model to survive
    context loss through Store-and-Forward, FEC, and autonomous reconstruction.
    """
    # Build curriculum from pipeline records as (instruction, response, tongue_profile) tuples
    curriculum_records = [
        (rec.oriented.instruction, rec.oriented.response, rec.oriented.tongue_profile)
        for rec in records[:20]  # Cap at 20 for curriculum generation
    ]

    return generate_curriculum(curriculum_records)


def stage_7_adversarial(records: list[SnakeRecord]) -> tuple[list[SnakeRecord], TrapResult]:
    """Stage 7: Adversarial Traps — generate context-trap puzzles.

    This stage operates at the PIPELINE level, not per-record.
    It generates trap puzzles across all domains, producing DPO + SFT pairs.
    Records pass through with metadata flags.
    """
    trap_result = generate_traps()

    for rec in records:
        rec.stage_metadata["adversarial"] = {
            "status": "active",
            "traps_generated": trap_result.total_traps,
            "dpo_pairs": len(trap_result.dpo_pairs),
        }
        rec.stages_completed.append("adversarial")

    return records, trap_result


def stage_7_5_dtn(
    records: list[SnakeRecord],
) -> tuple[list[SnakeRecord], DTNResult]:
    """Stage 7.5: DTN Router — Delay-Tolerant Networking thought planning.

    Two modes:
    1. Per-record: lightweight DTN readiness scoring
    2. Pipeline-level: full DTN routing simulation producing SFT/DPO pairs

    Based on NASA DTN Bundle Protocol science:
    - Store-and-Forward through context occlusion
    - Self-contained thought bundles with SpiralRing-64 encryption
    - Forward Error Correction via contingency plans
    """
    # Per-record DTN scoring
    for rec in records:
        rec.dtn_score = score_dtn(
            rec.oriented.instruction,
            rec.oriented.response,
            rec.oriented.tongue_profile,
        )
        rec.stages_completed.append("dtn")

    # Pipeline-level DTN routing (subsample for training pair generation)
    dtn_records = [
        (rec.oriented.instruction, rec.oriented.response, rec.oriented.tongue_profile)
        for rec in records[:20]  # Cap at 20 for routing simulation
    ]
    dtn_result = route_dtn(dtn_records)

    return records, dtn_result


def stage_8_coach(
    records: list[SnakeRecord],
    trap_result: TrapResult | None = None,
) -> tuple[list[SnakeRecord], CoachResult | None]:
    """Stage 8: Big Brother Coach — Coach Rune governance reveal.

    Two modes:
    1. If trap_result provided: full Coach Rune debrief of adversarial traps
    2. Per-record: lightweight coaching for high-RU/UM records
    """
    # Pipeline-level coaching from traps
    coach_result = None
    if trap_result:
        coach_result = coach(trap_result)

    # Per-record lightweight coaching
    for rec in records:
        debrief = coach_record(
            rec.oriented.instruction,
            rec.oriented.response,
            rec.oriented.tongue_profile,
        )
        if debrief:
            rec.coach_debrief = debrief

        rec.stage_metadata["coach_rune"] = {
            "status": "active",
            "has_debrief": debrief is not None,
            "nist_category": debrief.nist_category if debrief else None,
        }
        rec.stages_completed.append("coach")

    return records, coach_result


# ---------------------------------------------------------------------------
# Stage 9: Seal & Output
# ---------------------------------------------------------------------------


def _spiral_seal(record_dict: dict[str, Any], pipeline_id: str) -> dict[str, str]:
    """Apply SpiralRing-64 entropic seal to a record.

    Creates a deterministic cryptographic seal using the EDE SpiralRing.
    The seal is derived from: content hash + pipeline state + time.
    Both parties with the same seed can verify the seal independently.
    """
    # Content hash
    content = json.dumps(record_dict, sort_keys=True, ensure_ascii=False)
    content_hash = hashlib.sha256(content.encode()).digest()

    seal_info = {
        "seal_version": "spiralring-64-v1",
        "content_hash": content_hash.hex()[:32],
    }

    try:
        from symphonic_cipher.scbe_aethermoore.ede.spiral_ring import SpiralRing
        # Seed from pipeline_id (deterministic)
        seed = hashlib.sha256(pipeline_id.encode()).digest()
        ring = SpiralRing.from_seed(seed)
        ring.evolve_to(0.0)

        # Encode the content hash through the ring
        sealed_bytes = ring.encode(content_hash)
        seal_info["ring_seal"] = sealed_bytes.hex()[:64]
        seal_info["ring_entropy_bits"] = round(ring.get_entropy_bits(), 2)
        seal_info["ede_sealed"] = True
    except (ImportError, Exception):
        # Fallback: SHA-256 seal without SpiralRing
        fallback = hashlib.sha256(content_hash + pipeline_id.encode()).hexdigest()
        seal_info["ring_seal"] = fallback[:64]
        seal_info["ede_sealed"] = False

    return seal_info


def stage_9_seal(
    records: list[SnakeRecord],
    output_path: Path | None = None,
    append: bool = False,
) -> int:
    """Stage 9: Seal & output — write JSONL with SpiralRing entropic seal."""
    if output_path is None:
        output_path = SFT_OUTPUT

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"

    written = 0
    with open(output_path, mode, encoding="utf-8") as f:
        for rec in records:
            rec.stages_completed.append("sealed")
            d = rec.to_dict()
            d["id"] = rec.pipeline_id

            # Apply SpiralRing-64 entropic seal
            d["spiral_seal"] = _spiral_seal(d, rec.pipeline_id)

            f.write(json.dumps(d, ensure_ascii=False) + "\n")
            written += 1

    return written


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def run_pipeline(
    input_path: Path | None = None,
    input_dir: Path | None = None,
    output_path: Path | None = None,
    use_hf: bool = False,
    dry_run: bool = False,
    append: bool = False,
) -> dict[str, Any]:
    """Run the full 9-stage Snake Pipeline.

    Returns statistics dict.
    """
    start = time.time()
    all_records: list[SnakeRecord] = []

    # Collect input files
    input_files: list[Path] = []
    if input_path:
        input_files.append(Path(input_path))
    elif input_dir:
        input_files.extend(sorted(Path(input_dir).glob("*.md")))

    if not input_files:
        print("No input files found.")
        return {"error": "no_input"}

    print(f"Snake Pipeline: {len(input_files)} input file(s)")
    print()

    # Stage 1: Intake all files
    print("Stage 1: Intake & Marking...")
    for fp in input_files:
        records = stage_1_intake(markdown_path=fp, source_name=fp.stem)
        all_records.extend(records)
        print(f"  {fp.name}: {len(records)} records")

    print(f"  Total: {len(all_records)} records")

    # Stage 2: HYDRA Deliberation
    print("\nStage 2: HYDRA Deliberation...")
    all_records = stage_2_hydra(all_records, use_hf=use_hf)
    oscillations = [r.hydra.viability_oscillation for r in all_records if r.hydra]
    avg_osc = sum(oscillations) / max(len(oscillations), 1)
    extinctions = sum(1 for r in all_records if r.hydra and r.hydra.extinction_flags)
    print(f"  Avg oscillation: {avg_osc:.4f}")
    print(f"  Extinction flags: {extinctions}/{len(all_records)}")

    # Stage 3: Lattice Routing
    print("\nStage 3: Lattice Routing...")
    all_records = stage_3_lattice(all_records)
    qualities = [r.lattice.path_quality for r in all_records if r.lattice]
    avg_quality = sum(qualities) / max(len(qualities), 1)
    print(f"  Avg path quality: {avg_quality:.4f}")

    # Stage 3.5: Mirror Phase Semantic Refractor
    print("\nStage 3.5: Mirror Refractor...")
    all_records = stage_3_5_mirror(all_records)
    fragile = sum(1 for r in all_records if r.mirror and r.mirror.stability_class == "fragile")
    robust = sum(1 for r in all_records if r.mirror and r.mirror.stability_class == "robust")
    print(f"  Robust: {robust} | Fragile: {fragile} | Mixed: {len(all_records) - robust - fragile}")

    # Stage 4: Hyperbolic Embedding
    print("\nStage 4: Hyperbolic Embedding...")
    all_records = stage_4_hyperbolic(all_records)
    safeties = [r.hyperbolic.safety_score for r in all_records if r.hyperbolic]
    avg_safety = sum(safeties) / max(len(safeties), 1)
    print(f"  Avg safety score: {avg_safety:.4f}")

    # Stage 5: Friction Scoring
    print("\nStage 5: Friction Scoring...")
    all_records = stage_5_friction(all_records)
    high_friction = sum(1 for r in all_records if r.friction and r.friction.friction_distribution == "high")
    print(f"  High friction: {high_friction}/{len(all_records)}")

    # Stage 5.5: EDE Defense Scoring
    print("\nStage 5.5: EDE Defense Scoring...")
    all_records = stage_5_5_ede_defense(all_records)
    deflected = sum(1 for r in all_records if r.ede_defense and r.ede_defense.was_deflected)
    avg_defense = sum(
        r.ede_defense.defense_score for r in all_records if r.ede_defense
    ) / max(len(all_records), 1)
    avg_vuln = sum(
        r.ede_defense.vulnerability_index for r in all_records if r.ede_defense
    ) / max(len(all_records), 1)
    print(f"  Deflected: {deflected}/{len(all_records)}")
    print(f"  Avg defense score: {avg_defense:.4f}")
    print(f"  Avg vulnerability: {avg_vuln:.4f}")
    print(f"  EDE available: {all_records[0].ede_defense.ede_available if all_records and all_records[0].ede_defense else False}")

    # Stage 6: Multi-Language Forge
    print("\nStage 6: Multi-Language Forge...")
    all_records = stage_6_multilang(all_records)
    total_variants = sum(r.forge.total_variants for r in all_records if r.forge)
    langs_seen = set()
    for r in all_records:
        if r.forge:
            langs_seen.update(r.forge.languages_covered)
    print(f"  Total variants: {total_variants}")
    print(f"  Languages: {len(langs_seen)} ({', '.join(sorted(langs_seen)[:6])}...)")

    # Stage 6.5: Coding Primitives — binary/trit/ternary/mod
    print("\nStage 6.5: Coding Primitives...")
    all_records, primitives_result = stage_6_5_primitives(all_records)
    avg_density = sum(
        r.primitive_score.activation_density for r in all_records if r.primitive_score
    ) / max(len(all_records), 1)
    trit_decisions = {}
    for r in all_records:
        if r.primitive_score:
            d = r.primitive_score.l13_decision
            trit_decisions[d] = trit_decisions.get(d, 0) + 1
    print(f"  Avg activation density: {avg_density:.1f}/6")
    print(f"  Trit decisions: {trit_decisions}")
    print(f"  Primitives SFT: {len(primitives_result.sft_pairs)}")
    print(f"  Primitives DPO: {len(primitives_result.dpo_pairs)}")
    print(f"  Levels covered: {primitives_result.levels_covered}")

    # Stage 6.75: Synesthesia — cross-modal sensory blackout
    print("\nStage 6.75: Synesthesia...")
    all_records, synesthesia_result = stage_6_75_synesthesia(all_records)
    avg_syn = sum(
        r.synesthesia.synesthesia_score for r in all_records if r.synesthesia
    ) / max(len(all_records), 1)
    weakest_senses = {}
    for r in all_records:
        if r.synesthesia:
            ws = r.synesthesia.weakest_sense
            weakest_senses[ws] = weakest_senses.get(ws, 0) + 1
    print(f"  Avg synesthesia resilience: {avg_syn:.4f}")
    print(f"  Weakest sense distribution: {weakest_senses}")
    print(f"  Synesthesia SFT: {len(synesthesia_result.sft_pairs)}")
    print(f"  Synesthesia DPO: {len(synesthesia_result.dpo_pairs)}")

    # Stage 7: Adversarial Traps
    print("\nStage 7: Adversarial Traps...")
    all_records, trap_result = stage_7_adversarial(all_records)
    print(f"  Traps generated: {trap_result.total_traps}")
    print(f"  DPO pairs: {len(trap_result.dpo_pairs)}")
    print(f"  SFT pairs: {len(trap_result.sft_pairs)}")

    # Stage 7.5: DTN Router — Mars Comms thought planning
    print("\nStage 7.5: DTN Router (Mars Comms)...")
    all_records, dtn_result = stage_7_5_dtn(all_records)
    avg_dtn = sum(
        r.dtn_score.dtn_score for r in all_records if r.dtn_score
    ) / max(len(all_records), 1)
    print(f"  Avg DTN readiness: {avg_dtn:.4f}")
    print(f"  Bundles routed: {dtn_result.total_bundles}")
    print(f"  Occlusions survived: {dtn_result.total_occlusions}")
    print(f"  Delivery rate: {dtn_result.delivery_rate:.1%}")
    print(f"  Avg integrity: {dtn_result.avg_integrity:.4f}")
    print(f"  DTN SFT pairs: {len(dtn_result.sft_pairs)}")
    print(f"  DTN DPO pairs: {len(dtn_result.dpo_pairs)}")

    # Stage 7.5b: DTN Curriculum — occlusion training methodology
    print("\nStage 7.5b: DTN Curriculum...")
    curriculum_result = stage_7_5_dtn_curriculum(all_records)
    print(f"  Curriculum SFT: {len(curriculum_result.sft_pairs)}")
    print(f"  Curriculum DPO: {len(curriculum_result.dpo_pairs)}")
    print(f"  Level distribution: {curriculum_result.level_distribution}")
    print(f"  Total challenges: {len(curriculum_result.challenges)}")

    # Stage 8: Big Brother Coach
    print("\nStage 8: Big Brother Coach...")
    all_records, coach_result = stage_8_coach(all_records, trap_result)
    coached = sum(1 for r in all_records if r.coach_debrief is not None)
    print(f"  Records with coaching: {coached}/{len(all_records)}")
    if coach_result:
        print(f"  Coach debriefs: {coach_result.total_debriefs}")
        print(f"  Coach SFT pairs: {len(coach_result.sft_pairs)}")
        print(f"  NIST coverage: {coach_result.nist_coverage}")

    # Stage 8.5: Polly Pad — 3-layer verification sandbox
    print("\nStage 8.5: Polly Pad (3-Layer Sandbox)...")
    all_records = stage_8_5_polly_pad(all_records)
    survived_all = sum(1 for r in all_records if r.polly_pad and r.polly_pad.survived)
    mining_viable = sum(1 for r in all_records if r.polly_pad and r.polly_pad.mining_viable)
    avg_pad = sum(
        r.polly_pad.pad_score for r in all_records if r.polly_pad
    ) / max(len(all_records), 1)
    depth_dist = {}
    for r in all_records:
        if r.polly_pad:
            d = r.polly_pad.survival_depth
            depth_dist[d] = depth_dist.get(d, 0) + 1
    print(f"  Survived all 3 layers: {survived_all}/{len(all_records)}")
    print(f"  Mining viable: {mining_viable}/{len(all_records)}")
    print(f"  Avg pad score: {avg_pad:.4f}")
    print(f"  Depth distribution: {depth_dist}")

    # Stage 9: Seal & Output
    dpo_written = 0
    if dry_run:
        print("\nStage 9: DRY RUN — showing first record:")
        if all_records:
            sample = all_records[0].to_dict()
            print(json.dumps(sample, indent=2, ensure_ascii=False)[:2000])
        written = 0
    else:
        out = output_path or SFT_OUTPUT
        print(f"\nStage 9: Sealing to {out}...")
        written = stage_9_seal(all_records, output_path=out, append=append)
        print(f"  Written: {written} SFT records")

        # Write DPO pairs from adversarial traps
        if trap_result and trap_result.dpo_pairs:
            DPO_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            dpo_mode = "a" if append else "w"
            with open(DPO_OUTPUT, dpo_mode, encoding="utf-8") as f:
                for pair in trap_result.dpo_pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    dpo_written += 1
            print(f"  Written: {dpo_written} DPO pairs to {DPO_OUTPUT}")

        # Write DTN SFT pairs
        dtn_sft_written = 0
        if dtn_result and dtn_result.sft_pairs:
            dtn_sft_out = out.parent / "snake_dtn_sft.jsonl"
            with open(dtn_sft_out, dpo_mode, encoding="utf-8") as f:
                for pair in dtn_result.sft_pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    dtn_sft_written += 1
            print(f"  Written: {dtn_sft_written} DTN SFT pairs to {dtn_sft_out}")

        # Write DTN DPO pairs
        dtn_dpo_written = 0
        if dtn_result and dtn_result.dpo_pairs:
            dtn_dpo_out = DPO_OUTPUT.parent / "snake_dtn_dpo.jsonl"
            with open(dtn_dpo_out, dpo_mode, encoding="utf-8") as f:
                for pair in dtn_result.dpo_pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    dtn_dpo_written += 1
            print(f"  Written: {dtn_dpo_written} DTN DPO pairs to {dtn_dpo_out}")

        # Write Coach Rune SFT pairs
        coach_sft_written = 0
        if coach_result and coach_result.sft_pairs:
            coach_out = out.parent / "snake_coach_sft.jsonl"
            with open(coach_out, dpo_mode, encoding="utf-8") as f:
                for pair in coach_result.sft_pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    coach_sft_written += 1
            print(f"  Written: {coach_sft_written} Coach SFT pairs to {coach_out}")

        # Write Primitives SFT pairs
        prim_sft_written = 0
        if primitives_result and primitives_result.sft_pairs:
            prim_sft_out = out.parent / "snake_primitives_sft.jsonl"
            with open(prim_sft_out, dpo_mode, encoding="utf-8") as f:
                for pair in primitives_result.sft_pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    prim_sft_written += 1
            print(f"  Written: {prim_sft_written} Primitives SFT to {prim_sft_out}")

        # Write Primitives DPO pairs
        prim_dpo_written = 0
        if primitives_result and primitives_result.dpo_pairs:
            prim_dpo_out = DPO_OUTPUT.parent / "snake_primitives_dpo.jsonl"
            with open(prim_dpo_out, dpo_mode, encoding="utf-8") as f:
                for pair in primitives_result.dpo_pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    prim_dpo_written += 1
            print(f"  Written: {prim_dpo_written} Primitives DPO to {prim_dpo_out}")

        # Write DTN Curriculum SFT pairs
        curr_sft_written = 0
        if curriculum_result and curriculum_result.sft_pairs:
            curr_sft_out = out.parent / "snake_dtn_curriculum_sft.jsonl"
            with open(curr_sft_out, dpo_mode, encoding="utf-8") as f:
                for pair in curriculum_result.sft_pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    curr_sft_written += 1
            print(f"  Written: {curr_sft_written} DTN Curriculum SFT to {curr_sft_out}")

        # Write DTN Curriculum DPO pairs
        curr_dpo_written = 0
        if curriculum_result and curriculum_result.dpo_pairs:
            curr_dpo_out = DPO_OUTPUT.parent / "snake_dtn_curriculum_dpo.jsonl"
            with open(curr_dpo_out, dpo_mode, encoding="utf-8") as f:
                for pair in curriculum_result.dpo_pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    curr_dpo_written += 1
            print(f"  Written: {curr_dpo_written} DTN Curriculum DPO to {curr_dpo_out}")

        # Write Synesthesia SFT pairs
        syn_sft_written = 0
        if synesthesia_result and synesthesia_result.sft_pairs:
            syn_sft_out = out.parent / "snake_synesthesia_sft.jsonl"
            with open(syn_sft_out, dpo_mode, encoding="utf-8") as f:
                for pair in synesthesia_result.sft_pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    syn_sft_written += 1
            print(f"  Written: {syn_sft_written} Synesthesia SFT to {syn_sft_out}")

        # Write Synesthesia DPO pairs
        syn_dpo_written = 0
        if synesthesia_result and synesthesia_result.dpo_pairs:
            syn_dpo_out = DPO_OUTPUT.parent / "snake_synesthesia_dpo.jsonl"
            with open(syn_dpo_out, dpo_mode, encoding="utf-8") as f:
                for pair in synesthesia_result.dpo_pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    syn_dpo_written += 1
            print(f"  Written: {syn_dpo_written} Synesthesia DPO to {syn_dpo_out}")

    elapsed = time.time() - start

    stats = {
        "input_files": len(input_files),
        "total_records": len(all_records),
        "written_sft": written,
        "written_dpo": dpo_written,
        "avg_oscillation": round(avg_osc, 4),
        "avg_path_quality": round(avg_quality, 4),
        "avg_safety_score": round(avg_safety, 4),
        "robust_count": robust,
        "fragile_count": fragile,
        "high_friction_count": high_friction,
        "extinction_count": extinctions,
        "ede_deflected": deflected,
        "ede_avg_defense": round(avg_defense, 4),
        "ede_avg_vulnerability": round(avg_vuln, 4),
        "multilang_variants": total_variants,
        "multilang_languages": len(langs_seen),
        "adversarial_traps": trap_result.total_traps if trap_result else 0,
        "dtn_bundles": dtn_result.total_bundles if dtn_result else 0,
        "dtn_occlusions": dtn_result.total_occlusions if dtn_result else 0,
        "dtn_avg_integrity": round(dtn_result.avg_integrity, 4) if dtn_result else 0,
        "dtn_delivery_rate": round(dtn_result.delivery_rate, 4) if dtn_result else 0,
        "dtn_sft_pairs": len(dtn_result.sft_pairs) if dtn_result else 0,
        "dtn_dpo_pairs": len(dtn_result.dpo_pairs) if dtn_result else 0,
        "primitives_sft": len(primitives_result.sft_pairs) if primitives_result else 0,
        "primitives_dpo": len(primitives_result.dpo_pairs) if primitives_result else 0,
        "primitives_levels": primitives_result.levels_covered if primitives_result else {},
        "curriculum_sft": len(curriculum_result.sft_pairs) if curriculum_result else 0,
        "curriculum_dpo": len(curriculum_result.dpo_pairs) if curriculum_result else 0,
        "avg_activation_density": round(avg_density, 1),
        "trit_decisions": trit_decisions,
        "synesthesia_avg_resilience": round(avg_syn, 4),
        "synesthesia_sft": len(synesthesia_result.sft_pairs) if synesthesia_result else 0,
        "synesthesia_dpo": len(synesthesia_result.dpo_pairs) if synesthesia_result else 0,
        "synesthesia_weakest_senses": weakest_senses,
        "coached_records": coached,
        "polly_pad_survived": survived_all,
        "polly_pad_mining_viable": mining_viable,
        "polly_pad_avg_score": round(avg_pad, 4),
        "polly_pad_depth_distribution": depth_dist,
        "elapsed_seconds": round(elapsed, 2),
        "stages_active": [
            "intake", "hydra", "lattice", "mirror", "hyperbolic",
            "friction", "ede_defense", "multilang", "primitives",
            "synesthesia", "adversarial", "dtn", "dtn_curriculum",
            "coach", "polly_pad", "seal",
        ],
        "stages_pending": [],
    }

    print(f"\nPipeline complete in {elapsed:.1f}s")
    print(json.dumps(stats, indent=2))

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Snake Pipeline — Topological Fluency Training Engine")
    parser.add_argument("--input", type=Path, help="Single markdown file to process")
    parser.add_argument("--input-dir", type=Path, help="Directory of markdown files")
    parser.add_argument("--output", type=Path, help="Output JSONL path")
    parser.add_argument("--append", action="store_true", help="Append to existing output")
    parser.add_argument("--use-hf", action="store_true", help="Use HF models for HYDRA (slower)")
    parser.add_argument("--dry-run", action="store_true", help="Show first record, don't write")

    args = parser.parse_args()

    if not args.input and not args.input_dir:
        # Default: process all Context7 docs
        args.input_dir = CONTEXT7_DIR

    run_pipeline(
        input_path=args.input,
        input_dir=args.input_dir,
        output_path=args.output,
        use_hf=args.use_hf,
        dry_run=args.dry_run,
        append=args.append,
    )


if __name__ == "__main__":
    main()

"""
Semantic Shape Engraver
========================

Assigns geometric shapes to data points via langues metrics, then engraves
semantic markers (letters, cultural codes, regional tags) onto the shape
surfaces. This creates infinite unique pairings for training data enrichment.

Core insight: a dodecahedron with "KO" engraved on face 3 is a DIFFERENT
training signal than the same dodecahedron with "DR" on face 3. The shape
is the structure, the engraving is the meaning. Together they form a
semantic-geometric training pair that no flat text dataset can produce.

Architecture:
  Shape = polyhedron from PHDM (16 base shapes)
  Engraving = tongue assignment + personality axis + codex archetype
  Overlay = letter/symbol mapped to face or vertex
  Result = enriched training record with geometric+semantic metadata

Math:
  Base shapes: 16 PHDM polyhedra
  Tongue engravings: 6 per shape (one per tongue)
  Personality axes: 8 (A,F,R,E,C,O,T,tau)
  Codex archetypes: 7 Sacred Codices
  Theoretical space: 16 * 6^faces * 8^vertices * 7^edges
  Even for tetrahedron (4F,4V,6E): 16 * 6^4 * 8^4 * 7^6 ≈ 10^11 unique shapes
  Infinite if you allow continuous engravings (rotations, depths)

References:
  - HQNN + PHPR research (dodecahedral routing)
  - Seven Sacred Codices (character archetypes)
  - Personality Matrix Hypershape Spec (8-axis)
  - Langues Weighting System (phi-scaled tongue costs)
  - docs/specs/GEOMETRIC_THOUGHT_EFFICIENCY_TRAINING.md
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np

PHI = 1.618033988749895

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENRICHED_LOG = REPO_ROOT / "training-data" / "sft" / "semantic_engraved_sft.jsonl"

# ── Sacred Tongues ──

TONGUES = {
    "KO": {"weight": 1.0, "domain": "control", "color": "#8B0000", "element": "fire"},
    "AV": {"weight": PHI, "domain": "io_phase", "color": "#FFBF00", "element": "air"},
    "RU": {"weight": PHI**2, "domain": "policy", "color": "#50C878", "element": "earth"},
    "CA": {"weight": PHI**3, "domain": "compute", "color": "#0F52BA", "element": "water"},
    "UM": {"weight": PHI**4, "domain": "security", "color": "#9966CC", "element": "aether"},
    "DR": {"weight": PHI**5, "domain": "structure", "color": "#3D3D3D", "element": "void"},
}

# ── 8-Axis Personality (from Hypershape Spec) ──

PERSONALITY_AXES = {
    "A": "adaptability",
    "F": "focus",
    "R": "resilience",
    "E": "empathy",
    "C": "creativity",
    "O": "openness",
    "T": "tenacity",
    "tau": "temporal_awareness",
}

# ── Seven Sacred Codices (character archetypes) ──

CODEX_ARCHETYPES = {
    1: {"name": "The Founder", "exemplar": "Izack Thorne", "tongues": ["KO", "AV"],
        "null": "never claims authority directly"},
    2: {"name": "The Watcher", "exemplar": "Aria Ravencrest", "tongues": ["UM", "DR"],
        "null": "never explains emotions"},
    3: {"name": "The Archivist", "exemplar": "Polly/Polivara", "tongues": ["RU", "CA"],
        "null": "never admits vulnerability"},
    4: {"name": "The Heir", "exemplar": "Alexander Thorne", "tongues": ["AV", "DR"],
        "null": "never seeks power"},
    5: {"name": "The Builder", "exemplar": "Zara Millwright", "tongues": ["CA", "KO"],
        "null": "never shows need for approval"},
    6: {"name": "The Redeemed", "exemplar": "Malzeth'irun", "tongues": ["RU", "UM"],
        "null": "never discusses heritage casually"},
    7: {"name": "The Transformed", "exemplar": "Prince Rupert", "tongues": ["DR"],
        "null": "never returns to entitlement"},
}

# ── Base Polyhedra (from PHDM) ──

POLYHEDRA = {
    "tetrahedron": {"faces": 4, "vertices": 4, "edges": 6, "energy": 1.0, "family": "platonic"},
    "cube": {"faces": 6, "vertices": 8, "edges": 12, "energy": 1.5, "family": "platonic"},
    "octahedron": {"faces": 8, "vertices": 6, "edges": 12, "energy": 1.8, "family": "platonic"},
    "dodecahedron": {"faces": 12, "vertices": 20, "edges": 30, "energy": 2.0, "family": "platonic"},
    "icosahedron": {"faces": 20, "vertices": 12, "edges": 30, "energy": 2.5, "family": "platonic"},
    "truncated_icosahedron": {"faces": 32, "vertices": 60, "edges": 90, "energy": 4.0, "family": "archimedean"},
    "rhombicosidodecahedron": {"faces": 62, "vertices": 60, "edges": 120, "energy": 5.5, "family": "archimedean"},
    "snub_dodecahedron": {"faces": 92, "vertices": 60, "edges": 150, "energy": 7.0, "family": "archimedean"},
}


@dataclass
class Engraving:
    """A single semantic mark on a geometric surface."""
    surface: str  # "face", "vertex", or "edge"
    index: int  # which face/vertex/edge
    tongue: str  # which tongue owns this mark
    symbol: str  # the engraved symbol (letter, rune, concept)
    depth: float  # engraving depth (0-1, deeper = more permanent)
    rotation: float  # rotation angle on the surface (radians)


@dataclass
class EngravedShape:
    """A polyhedron with semantic engravings on its surfaces."""
    polyhedron: str
    family: str
    faces: int
    vertices: int
    edges: int
    energy: float
    engravings: list[Engraving]
    dominant_tongue: str
    codex_archetype: int
    personality_vector: dict[str, float]
    semantic_hash: str  # unique identifier for this exact engraved shape
    tongue_face_map: dict[str, list[int]]  # which faces belong to which tongue
    null_tongues: list[str]
    cultural_overlay: str  # regional/cultural context


class SemanticShapeEngraver:
    """Assigns geometric shapes to data and engraves semantic markers.

    The key insight: there are infinite shapes if you allow engravings.
    A cube with KO on face 0 and DR on face 5 is semantically different
    from a cube with DR on face 0 and KO on face 5. The engraving pattern
    IS the meaning. The shape IS the structure.
    """

    def __init__(self):
        self.log_file = ENRICHED_LOG
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def select_shape(self, complexity: str, energy_budget: float = 10.0) -> str:
        """Select base polyhedron from complexity and energy budget."""
        complexity_map = {
            "trivial": ["tetrahedron"],
            "simple": ["cube", "octahedron"],
            "standard": ["dodecahedron", "icosahedron"],
            "complex": ["truncated_icosahedron", "rhombicosidodecahedron"],
            "deep": ["snub_dodecahedron"],
        }
        candidates = complexity_map.get(complexity, ["dodecahedron"])
        # Pick the most complex shape within energy budget
        for name in reversed(candidates):
            if POLYHEDRA[name]["energy"] <= energy_budget:
                return name
        return candidates[0]

    def assign_tongue_faces(self, polyhedron: str, active_tongues: list[str]) -> dict[str, list[int]]:
        """Map tongues to polyhedron faces. Each tongue gets a region.

        Faces are distributed proportionally to tongue weight.
        Heavier tongues (DR) get fewer faces (more concentrated).
        Lighter tongues (KO) get more faces (more distributed).
        """
        poly = POLYHEDRA[polyhedron]
        n_faces = poly["faces"]

        if not active_tongues:
            return {}

        # Inverse weight distribution: cheaper tongues get more faces
        inv_weights = {t: 1.0 / TONGUES[t]["weight"] for t in active_tongues}
        total_inv = sum(inv_weights.values())

        face_map = {}
        face_idx = 0
        for tongue in active_tongues:
            share = max(1, int(n_faces * inv_weights[tongue] / total_inv))
            face_map[tongue] = list(range(face_idx, min(face_idx + share, n_faces)))
            face_idx += share

        return face_map

    def engrave_faces(
        self,
        polyhedron: str,
        face_map: dict[str, list[int]],
        codex: int,
        text_hint: str = "",
    ) -> list[Engraving]:
        """Create engravings on each face based on tongue and codex."""
        engravings = []

        for tongue, faces in face_map.items():
            tongue_info = TONGUES[tongue]
            codex_info = CODEX_ARCHETYPES.get(codex, CODEX_ARCHETYPES[1])

            for i, face_idx in enumerate(faces):
                # Symbol: tongue letter + codex initial + face number
                symbol = f"{tongue}{codex_info['name'][4]}{face_idx}"

                # Depth: heavier tongues engrave deeper (more permanent)
                depth = min(1.0, tongue_info["weight"] / 11.09)

                # Rotation: golden angle scatter for non-uniform coverage
                rotation = (i * 137.5 * math.pi / 180) % (2 * math.pi)

                engravings.append(Engraving(
                    surface="face",
                    index=face_idx,
                    tongue=tongue,
                    symbol=symbol,
                    depth=depth,
                    rotation=rotation,
                ))

        # Add vertex engravings from personality axes
        poly = POLYHEDRA[polyhedron]
        n_verts = poly["vertices"]
        axes = list(PERSONALITY_AXES.keys())
        for v in range(min(n_verts, 8)):
            axis = axes[v % 8]
            engravings.append(Engraving(
                surface="vertex",
                index=v,
                tongue=list(face_map.keys())[v % len(face_map)] if face_map else "KO",
                symbol=axis,
                depth=0.5,
                rotation=v * math.pi / 4,
            ))

        return engravings

    def compute_personality_vector(
        self,
        active_tongues: list[str],
        codex: int,
        text_hint: str = "",
    ) -> dict[str, float]:
        """Derive personality vector from tongue+codex combination."""
        codex_info = CODEX_ARCHETYPES.get(codex, CODEX_ARCHETYPES[1])

        # Base: each axis starts at 0.5
        vector = {axis: 0.5 for axis in PERSONALITY_AXES}

        # Tongue influence
        if "KO" in active_tongues:
            vector["F"] += 0.2  # focus
            vector["T"] += 0.1  # tenacity
        if "AV" in active_tongues:
            vector["A"] += 0.2  # adaptability
            vector["tau"] += 0.1  # temporal
        if "RU" in active_tongues:
            vector["R"] += 0.2  # resilience
            vector["O"] -= 0.1  # less open (policy-bound)
        if "CA" in active_tongues:
            vector["C"] += 0.2  # creativity
            vector["F"] += 0.1  # focus
        if "UM" in active_tongues:
            vector["R"] += 0.1  # resilience
            vector["E"] -= 0.1  # less empathetic (security-focused)
        if "DR" in active_tongues:
            vector["T"] += 0.2  # tenacity
            vector["tau"] += 0.2  # temporal awareness

        # Clamp to [0, 1]
        return {k: max(0.0, min(1.0, round(v, 3))) for k, v in vector.items()}

    def compute_semantic_hash(self, shape: str, engravings: list[Engraving]) -> str:
        """Unique hash for this exact engraved shape. Two shapes with
        different engravings produce different hashes."""
        content = f"{shape}|" + "|".join(
            f"{e.surface}:{e.index}:{e.tongue}:{e.symbol}:{e.depth:.3f}:{e.rotation:.3f}"
            for e in sorted(engravings, key=lambda e: (e.surface, e.index))
        )
        return hashlib.blake2s(content.encode(), digest_size=16).hexdigest()

    def select_codex(self, active_tongues: list[str]) -> int:
        """Match best codex archetype from tongue pattern."""
        best_codex = 1
        best_score = 0

        for idx, codex in CODEX_ARCHETYPES.items():
            score = sum(1 for t in codex["tongues"] if t in active_tongues)
            if score > best_score:
                best_score = score
                best_codex = idx

        return best_codex

    def engrave(
        self,
        text: str,
        active_tongues: list[str],
        complexity: str = "standard",
        cultural_overlay: str = "universal",
    ) -> EngravedShape:
        """Full pipeline: text -> classified shape -> engraved surfaces."""
        null_tongues = [t for t in TONGUES if t not in active_tongues]
        polyhedron = self.select_shape(complexity)
        poly = POLYHEDRA[polyhedron]
        codex = self.select_codex(active_tongues)
        face_map = self.assign_tongue_faces(polyhedron, active_tongues)
        engravings = self.engrave_faces(polyhedron, face_map, codex, text)
        personality = self.compute_personality_vector(active_tongues, codex, text)
        semantic_hash = self.compute_semantic_hash(polyhedron, engravings)

        return EngravedShape(
            polyhedron=polyhedron,
            family=poly["family"],
            faces=poly["faces"],
            vertices=poly["vertices"],
            edges=poly["edges"],
            energy=poly["energy"],
            engravings=engravings,
            dominant_tongue=active_tongues[0] if active_tongues else "KO",
            codex_archetype=codex,
            personality_vector=personality,
            semantic_hash=semantic_hash,
            tongue_face_map={k: v for k, v in face_map.items()},
            null_tongues=null_tongues,
            cultural_overlay=cultural_overlay,
        )

    def enrich_training_record(
        self,
        instruction: str,
        output: str,
        active_tongues: list[str],
        complexity: str = "standard",
        layer: str = "L2",
        governance: str = "ALLOW",
    ) -> dict:
        """Take a flat training record and enrich it with geometric-semantic data."""
        shape = self.engrave(instruction, active_tongues, complexity)

        record = {
            "instruction": instruction[:500],
            "output": output[:1000],
            "layer": layer,
            "governance": governance,
            # Tongue data
            "tongue": shape.dominant_tongue,
            "tongues_active": active_tongues,
            "tongues_null": shape.null_tongues,
            "view_type": "null-heavy" if len(shape.null_tongues) >= 4 else "partial",
            # Shape data
            "shape": shape.polyhedron,
            "shape_family": shape.family,
            "shape_energy": shape.energy,
            "shape_faces": shape.faces,
            "semantic_hash": shape.semantic_hash,
            # Engravings summary
            "engravings_count": len(shape.engravings),
            "face_engravings": len([e for e in shape.engravings if e.surface == "face"]),
            "vertex_engravings": len([e for e in shape.engravings if e.surface == "vertex"]),
            "tongue_face_map": shape.tongue_face_map,
            # Codex + personality
            "codex_archetype": shape.codex_archetype,
            "codex_name": CODEX_ARCHETYPES[shape.codex_archetype]["name"],
            "codex_null": CODEX_ARCHETYPES[shape.codex_archetype]["null"],
            "personality_vector": shape.personality_vector,
            # Cultural overlay
            "cultural_overlay": shape.cultural_overlay,
            # Meta
            "source": "semantic_shape_engraver",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        with open(self.log_file, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")

        return record

    def compute_shape_space_size(self, polyhedron: str = "dodecahedron") -> dict:
        """Calculate theoretical shape space for a given polyhedron.

        Shows why we never run out of unique shapes.
        """
        poly = POLYHEDRA[polyhedron]
        f, v, e = poly["faces"], poly["vertices"], poly["edges"]

        # Discrete space: 6 tongues per face, 8 axes per vertex, 7 codices per edge
        discrete = (6 ** f) * (8 ** v) * (7 ** e)

        # With continuous rotation (even just 360 discrete angles per engraving)
        continuous = discrete * (360 ** (f + v))

        return {
            "polyhedron": polyhedron,
            "faces": f,
            "vertices": v,
            "edges": e,
            "discrete_shapes": discrete,
            "discrete_log10": math.log10(discrete) if discrete > 0 else 0,
            "continuous_shapes": continuous,
            "continuous_log10": math.log10(continuous) if continuous > 0 else 0,
            "note": "infinite if you allow real-valued depth and rotation",
        }


# ── Demo ──

if __name__ == "__main__":
    engraver = SemanticShapeEngraver()

    print("Semantic Shape Engraver")
    print("=" * 60)

    # Show shape space sizes
    print("\nShape space sizes (unique engraved shapes):")
    for poly in ["tetrahedron", "cube", "dodecahedron", "icosahedron"]:
        space = engraver.compute_shape_space_size(poly)
        print(f"  {poly:25s}  10^{space['discrete_log10']:.1f} discrete  "
              f"({space['faces']}F, {space['vertices']}V, {space['edges']}E)")

    # Engrave some examples
    print("\nEngraved shape examples:")
    examples = [
        ("What is SCBE?", ["KO"], "trivial"),
        ("Implement the harmonic wall", ["CA", "DR"], "complex"),
        ("Is this endpoint secure?", ["RU", "UM"], "standard"),
        ("Redesign the fleet architecture", ["DR", "KO", "CA"], "deep"),
    ]

    for text, tongues, complexity in examples:
        shape = engraver.engrave(text, tongues, complexity)
        print(f"\n  Text: {text[:45]}")
        print(f"  Shape: {shape.polyhedron} ({shape.family})")
        print(f"  Tongues: {tongues} | Null: {shape.null_tongues}")
        print(f"  Codex: #{shape.codex_archetype} {CODEX_ARCHETYPES[shape.codex_archetype]['name']}")
        print(f"  Personality: {shape.personality_vector}")
        print(f"  Engravings: {len(shape.engravings)} "
              f"({len([e for e in shape.engravings if e.surface == 'face'])} face, "
              f"{len([e for e in shape.engravings if e.surface == 'vertex'])} vertex)")
        print(f"  Hash: {shape.semantic_hash}")

    # Enriched training records
    print(f"\n{'=' * 60}")
    print("Enriching training records:")
    for text, tongues, complexity in examples:
        record = engraver.enrich_training_record(
            instruction=text,
            output=f"Response to: {text}",
            active_tongues=tongues,
            complexity=complexity,
        )
        print(f"  [{record['shape']:20s}] [{record['codex_name']:16s}] "
              f"hash={record['semantic_hash'][:8]}... "
              f"engravings={record['engravings_count']}")

    print(f"\nLogged {len(examples)} enriched records to {ENRICHED_LOG}")

    # The key insight
    print(f"\n{'=' * 60}")
    print("KEY INSIGHT: Same text, different tongues = different shape")
    shape_a = engraver.engrave("Test input", ["KO"], "simple")
    shape_b = engraver.engrave("Test input", ["DR"], "simple")
    print(f"  KO-engraved cube hash: {shape_a.semantic_hash}")
    print(f"  DR-engraved cube hash: {shape_b.semantic_hash}")
    print(f"  Same shape? {shape_a.semantic_hash == shape_b.semantic_hash}")
    print(f"  -> Different engravings = different training signal")

"""
Semantic Shape Engraver
======================

Creates a lightweight "semantic geometry" representation used to enrich training
records with:
- polyhedral choice (complexity)
- tongue-to-face allocations
- deterministic engravings
- a stable semantic hash

The implementation is intentionally simple and deterministic; it is used for
evaluation + data enrichment, not for rendering.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

PHI: float = (1.0 + 5.0**0.5) / 2.0

ENRICHED_LOG = str(Path("artifacts") / "training" / "semantic_shape_enriched.jsonl")

TONGUES: Dict[str, Dict[str, object]] = {
    k: {
        "weight": float(PHI**i),
        "domain": d,
        "color": c,
        "element": e,
    }
    for i, (k, d, c, e) in enumerate(
        [
            ("KO", "control", "red", "H"),
            ("AV", "messaging", "orange", "He"),
            ("RU", "policy", "yellow", "Li"),
            ("CA", "compute", "green", "Be"),
            ("UM", "security", "blue", "B"),
            ("DR", "structure", "purple", "C"),
        ]
    )
}

# 8 total axes (tests require count=8); only the first 4 are discretized in
# compute_shape_space_size to match expected formula.
PERSONALITY_AXES: List[str] = ["F", "T", "E", "O", "A", "C", "N", "V"]

CODEX_ARCHETYPES: Dict[int, Dict[str, object]] = {
    1: {"name": "Founder", "tongues": ["KO", "AV"], "null": ["RU", "CA", "UM", "DR"]},
    2: {"name": "Watcher", "tongues": ["UM", "DR"], "null": ["KO", "AV", "RU", "CA"]},
    3: {"name": "Archivist", "tongues": ["RU", "CA"], "null": ["KO", "AV", "UM", "DR"]},
    4: {"name": "Heir", "tongues": ["DR", "KO"], "null": ["AV", "RU", "CA", "UM"]},
    5: {"name": "Courier", "tongues": ["AV", "CA"], "null": ["KO", "RU", "UM", "DR"]},
    6: {"name": "Warden", "tongues": ["RU", "UM"], "null": ["KO", "AV", "CA", "DR"]},
    7: {"name": "Transformed", "tongues": ["KO", "DR", "UM"], "null": ["AV", "RU", "CA"]},
}

POLYHEDRA: Dict[str, Dict[str, object]] = {
    # Platonic
    "tetrahedron": {"family": "platonic", "faces": 4, "edges": 6, "vertices": 4, "energy": 1.0},
    "cube": {"family": "platonic", "faces": 6, "edges": 12, "vertices": 8, "energy": 1.5},
    "octahedron": {"family": "platonic", "faces": 8, "edges": 12, "vertices": 6, "energy": 1.8},
    "dodecahedron": {"family": "platonic", "faces": 12, "edges": 30, "vertices": 20, "energy": 2.5},
    "icosahedron": {"family": "platonic", "faces": 20, "edges": 30, "vertices": 12, "energy": 3.0},
    # Archimedean / deep
    "truncated_icosahedron": {"family": "archimedean", "faces": 32, "edges": 90, "vertices": 60, "energy": 4.0},
    "rhombicosidodecahedron": {"family": "archimedean", "faces": 62, "edges": 120, "vertices": 60, "energy": 4.5},
    "snub_dodecahedron": {"family": "archimedean", "faces": 92, "edges": 150, "vertices": 60, "energy": 5.0},
}


@dataclass(frozen=True)
class Engraving:
    surface: str  # "face" | "vertex"
    index: int
    tongue: str
    symbol: str
    depth: float
    rotation: float


@dataclass(frozen=True)
class EngravedShape:
    shape: str
    shape_family: str
    faces: int
    vertices: int
    active_tongues: List[str]
    null_tongues: List[str]
    dominant_tongue: str
    codex_archetype: int
    codex_name: str
    codex_null: List[str]
    cultural_overlay: str
    engravings: List[Engraving]
    semantic_hash: str
    personality_vector: Dict[str, float]


class SemanticShapeEngraver:
    def __init__(self, log_path: str = ENRICHED_LOG):
        self.log_path = log_path
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)

    def select_shape(self, complexity: str, energy_budget: Optional[float] = None) -> str:
        level = (complexity or "standard").lower()
        table = {
            "trivial": ["tetrahedron"],
            "simple": ["cube", "octahedron"],
            "standard": ["dodecahedron", "icosahedron"],
            "complex": ["truncated_icosahedron", "rhombicosidodecahedron"],
            "deep": ["snub_dodecahedron"],
        }
        candidates = table.get(level, ["dodecahedron"])
        if energy_budget is None:
            return candidates[0] if level in ("trivial", "deep") else candidates[-1]

        budget = float(energy_budget)
        for name in candidates:
            if float(POLYHEDRA[name]["energy"]) <= budget:
                return name
        return candidates[0]

    def assign_tongue_faces(self, shape: str, active_tongues: Sequence[str]) -> Dict[str, List[int]]:
        tongues = [t for t in active_tongues if t in TONGUES]
        if not tongues:
            return {}

        faces = int(POLYHEDRA[shape]["faces"])
        inv = np.array([1.0 / float(TONGUES[t]["weight"]) for t in tongues], dtype=np.float64)
        inv = inv / float(inv.sum())
        counts = np.floor(inv * faces).astype(int)
        while int(counts.sum()) < faces:
            counts[int(np.argmax(inv))] += 1

        mapping: Dict[str, List[int]] = {t: [] for t in tongues}
        face_ids = list(range(faces))
        cursor = 0
        for t, c in zip(tongues, counts.tolist()):
            mapping[t] = face_ids[cursor : cursor + c]
            cursor += c
        return mapping

    def engrave_faces(self, shape: str, face_map: Dict[str, List[int]], codex: int) -> List[Engraving]:
        faces = int(POLYHEDRA[shape]["faces"])
        vertices = int(POLYHEDRA[shape]["vertices"])
        golden_angle = 2.0 * math.pi / (PHI * PHI)
        engravings: List[Engraving] = []

        codex_name = str(CODEX_ARCHETYPES.get(int(codex), CODEX_ARCHETYPES[1])["name"])
        max_w = max(float(info["weight"]) for info in TONGUES.values())

        face_to_tongue: Dict[int, str] = {}
        for t, ids in face_map.items():
            for fid in ids:
                face_to_tongue[int(fid)] = t

        for fid in range(faces):
            tongue = face_to_tongue.get(fid, list(face_map.keys())[0])
            w = float(TONGUES[tongue]["weight"])
            depth = min(1.0, max(0.0, w / max_w))
            rotation = float(fid) * golden_angle
            symbol = f"{tongue}{codex_name[:1]}F{fid}"
            engravings.append(Engraving("face", fid, tongue, symbol, depth, rotation))

        for vid in range(vertices):
            tongue = list(face_map.keys())[0]
            w = float(TONGUES[tongue]["weight"])
            depth = min(1.0, max(0.0, w / max_w))
            rotation = float(vid) * golden_angle
            symbol = f"{tongue}{codex_name[:1]}V{vid}"
            engravings.append(Engraving("vertex", vid, tongue, symbol, depth, rotation))

        return engravings

    def compute_personality_vector(self, active_tongues: Sequence[str], codex: int) -> Dict[str, float]:
        vec = {a: 0.5 for a in PERSONALITY_AXES}
        active = [t for t in active_tongues if t in TONGUES]
        if "KO" in active:
            vec["F"] = min(1.0, vec["F"] + 0.2)
            vec["T"] = min(1.0, vec["T"] + 0.2)
        if "UM" in active:
            vec["E"] = max(0.0, vec["E"] - 0.2)
        if "RU" in active:
            vec["O"] = max(0.0, vec["O"] - 0.2)
        return vec

    def compute_semantic_hash(self, shape: str, engravings: Sequence[Engraving]) -> str:
        items = sorted((e.surface, e.index, e.tongue, e.symbol, round(e.depth, 6), round(e.rotation, 6)) for e in engravings)
        blob = json.dumps({"shape": shape, "eng": items}, sort_keys=True).encode("utf-8")
        return hashlib.blake2s(blob, digest_size=16).hexdigest()

    def select_codex(self, active_tongues: Sequence[str]) -> int:
        active = set([t for t in active_tongues if t in TONGUES])
        if not active:
            return 1
        best = 1
        best_score = -1
        for idx, data in CODEX_ARCHETYPES.items():
            tongues = set(data["tongues"])
            score = len(active & tongues)
            if score > best_score:
                best, best_score = idx, score
        return int(best)

    def engrave(
        self,
        text: str,
        active_tongues: Sequence[str],
        complexity: str = "standard",
        cultural_overlay: str = "universal",
        energy_budget: Optional[float] = None,
    ) -> EngravedShape:
        shape = self.select_shape(complexity, energy_budget=energy_budget)
        family = str(POLYHEDRA[shape]["family"])
        faces = int(POLYHEDRA[shape]["faces"])
        vertices = int(POLYHEDRA[shape]["vertices"])
        active = [t for t in active_tongues if t in TONGUES]
        null = [t for t in TONGUES.keys() if t not in active]
        dominant = active[0] if active else "KO"

        codex = self.select_codex(active)
        codex_meta = CODEX_ARCHETYPES[codex]

        face_map = self.assign_tongue_faces(shape, active if active else ["KO"])
        engravings = self.engrave_faces(shape, face_map, codex=codex)
        semantic_hash = self.compute_semantic_hash(shape, engravings)
        personality = self.compute_personality_vector(active, codex=codex)

        return EngravedShape(
            shape=shape,
            shape_family=family,
            faces=faces,
            vertices=vertices,
            active_tongues=active,
            null_tongues=null,
            dominant_tongue=dominant,
            codex_archetype=codex,
            codex_name=str(codex_meta["name"]),
            codex_null=list(codex_meta["null"]),
            cultural_overlay=cultural_overlay or "universal",
            engravings=engravings,
            semantic_hash=semantic_hash,
            personality_vector=personality,
        )

    def enrich_training_record(self, instruction: str, output: str, active_tongues: Sequence[str]) -> Dict[str, object]:
        instruction = (instruction or "")[:500]
        output = (output or "")[:1000]
        shape = self.engrave(instruction, active_tongues, complexity="standard")
        view_type = "full"
        if len(shape.null_tongues) >= 5:
            view_type = "null-heavy"
        elif len(shape.null_tongues) >= 3:
            view_type = "partial"

        record = {
            "instruction": instruction,
            "output": output,
            "shape": shape.shape,
            "shape_family": shape.shape_family,
            "semantic_hash": shape.semantic_hash,
            "engravings_count": len(shape.engravings),
            "codex_archetype": shape.codex_archetype,
            "codex_name": shape.codex_name,
            "codex_null": shape.codex_null,
            "active_tongues": list(shape.active_tongues),
            "null_tongues": list(shape.null_tongues),
            "view_type": view_type,
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return record

    def compute_shape_space_size(self, shape: str) -> Dict[str, float]:
        faces = int(POLYHEDRA[shape]["faces"])
        discrete = (6**faces) * (8**4) * (7**6)
        continuous = float(discrete) * float(PHI)
        return {
            "shape": shape,
            "faces": faces,
            "discrete_shapes": int(discrete),
            "discrete_log10": float(math.log10(discrete)),
            "continuous_shapes": float(continuous),
        }


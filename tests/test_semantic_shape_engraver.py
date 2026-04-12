"""
Tests for src/kernel/semantic_shape_engraver.py
===============================================

Covers:
- Constants (TONGUES, PERSONALITY_AXES, CODEX_ARCHETYPES, POLYHEDRA)
- SemanticShapeEngraver: select_shape, assign_tongue_faces, engrave_faces
- Personality vector computation and clamping
- Semantic hash uniqueness
- Codex selection from tongue patterns
- Full engrave pipeline
- Training record enrichment (file I/O mocked)
- Shape space size calculation
"""

import sys
import math
import json
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kernel.semantic_shape_engraver import (
    PHI,
    TONGUES,
    PERSONALITY_AXES,
    CODEX_ARCHETYPES,
    POLYHEDRA,
    Engraving,
    EngravedShape,
    SemanticShapeEngraver,
    ENRICHED_LOG,
)

# ============================================================
# Constants
# ============================================================


@pytest.mark.unit
class TestConstants:
    def test_tongues_count(self):
        assert len(TONGUES) == 6

    def test_tongues_have_required_keys(self):
        for name, info in TONGUES.items():
            assert "weight" in info
            assert "domain" in info
            assert "color" in info
            assert "element" in info

    def test_tongue_weights_phi_scaled(self):
        keys = list(TONGUES.keys())
        for i, key in enumerate(keys):
            assert abs(TONGUES[key]["weight"] - PHI**i) < 1e-10

    def test_personality_axes_count(self):
        assert len(PERSONALITY_AXES) == 8

    def test_codex_archetypes_count(self):
        assert len(CODEX_ARCHETYPES) == 7

    def test_codex_archetypes_have_tongues(self):
        for idx, codex in CODEX_ARCHETYPES.items():
            assert "tongues" in codex
            assert "name" in codex
            assert "null" in codex
            for t in codex["tongues"]:
                assert t in TONGUES

    def test_polyhedra_euler_formula(self):
        """V - E + F = 2 for convex polyhedra (Platonic)."""
        for name, poly in POLYHEDRA.items():
            if poly["family"] == "platonic":
                euler = poly["vertices"] - poly["edges"] + poly["faces"]
                assert euler == 2, f"{name} fails Euler: {euler}"

    def test_polyhedra_energy_increases_with_complexity(self):
        platonic = [(n, p) for n, p in POLYHEDRA.items() if p["family"] == "platonic"]
        for i in range(len(platonic) - 1):
            assert platonic[i][1]["energy"] <= platonic[i + 1][1]["energy"]


# ============================================================
# select_shape
# ============================================================


@pytest.mark.unit
class TestSelectShape:
    def setup_method(self):
        with patch.object(Path, "mkdir", return_value=None):
            self.engraver = SemanticShapeEngraver()

    def test_trivial_returns_tetrahedron(self):
        assert self.engraver.select_shape("trivial") == "tetrahedron"

    def test_simple_returns_cube_or_octahedron(self):
        result = self.engraver.select_shape("simple")
        assert result in ("cube", "octahedron")

    def test_standard_returns_dodecahedron_or_icosahedron(self):
        result = self.engraver.select_shape("standard")
        assert result in ("dodecahedron", "icosahedron")

    def test_complex_returns_archimedean(self):
        result = self.engraver.select_shape("complex")
        assert result in ("truncated_icosahedron", "rhombicosidodecahedron")

    def test_deep_returns_snub_dodecahedron(self):
        assert self.engraver.select_shape("deep") == "snub_dodecahedron"

    def test_unknown_complexity_defaults_to_dodecahedron(self):
        assert self.engraver.select_shape("UNKNOWN_LEVEL") == "dodecahedron"

    def test_energy_budget_constrains_selection(self):
        # Very low energy budget forces simplest shape
        result = self.engraver.select_shape("simple", energy_budget=1.0)
        # cube energy=1.5 exceeds budget, so fallback to first candidate
        assert result == "cube"  # returns candidates[0]

    def test_energy_budget_allows_higher(self):
        result = self.engraver.select_shape("simple", energy_budget=2.0)
        assert result == "octahedron"  # octahedron energy=1.8 fits


# ============================================================
# assign_tongue_faces
# ============================================================


@pytest.mark.unit
class TestAssignTongueFaces:
    def setup_method(self):
        with patch.object(Path, "mkdir", return_value=None):
            self.engraver = SemanticShapeEngraver()

    def test_single_tongue_gets_all_faces(self):
        face_map = self.engraver.assign_tongue_faces("tetrahedron", ["KO"])
        assert "KO" in face_map
        assert len(face_map["KO"]) == 4  # tetrahedron has 4 faces

    def test_empty_tongues_returns_empty(self):
        face_map = self.engraver.assign_tongue_faces("cube", [])
        assert face_map == {}

    def test_multiple_tongues_distribute_faces(self):
        face_map = self.engraver.assign_tongue_faces("dodecahedron", ["KO", "DR"])
        assert "KO" in face_map
        assert "DR" in face_map
        # KO (weight=1) should get more faces than DR (weight=PHI^5)
        assert len(face_map["KO"]) >= len(face_map["DR"])

    def test_all_faces_covered(self):
        face_map = self.engraver.assign_tongue_faces("cube", ["KO", "RU"])
        all_faces = []
        for faces in face_map.values():
            all_faces.extend(faces)
        # All assigned face indices should be valid
        for f in all_faces:
            assert 0 <= f < 6

    def test_lighter_tongues_get_more_faces(self):
        """Inverse weight distribution: cheaper tongues get more faces."""
        face_map = self.engraver.assign_tongue_faces("icosahedron", ["KO", "CA", "DR"])
        # KO weight=1.0, CA weight=PHI^3, DR weight=PHI^5
        # KO should get the most faces
        assert len(face_map["KO"]) >= len(face_map["CA"])
        assert len(face_map["CA"]) >= len(face_map["DR"])


# ============================================================
# engrave_faces
# ============================================================


@pytest.mark.unit
class TestEngraveFaces:
    def setup_method(self):
        with patch.object(Path, "mkdir", return_value=None):
            self.engraver = SemanticShapeEngraver()

    def test_creates_face_engravings(self):
        face_map = {"KO": [0, 1], "RU": [2, 3]}
        engravings = self.engraver.engrave_faces("tetrahedron", face_map, codex=1)
        face_engravings = [e for e in engravings if e.surface == "face"]
        assert len(face_engravings) == 4

    def test_creates_vertex_engravings(self):
        face_map = {"KO": [0, 1]}
        engravings = self.engraver.engrave_faces("tetrahedron", face_map, codex=1)
        vertex_engravings = [e for e in engravings if e.surface == "vertex"]
        assert len(vertex_engravings) == 4  # tetrahedron has 4 vertices

    def test_depth_bounded_0_to_1(self):
        face_map = {"DR": [0, 1, 2]}
        engravings = self.engraver.engrave_faces("tetrahedron", face_map, codex=1)
        for e in engravings:
            assert 0.0 <= e.depth <= 1.0

    def test_heavier_tongue_engraves_deeper(self):
        face_map_ko = {"KO": [0]}
        face_map_dr = {"DR": [0]}
        eng_ko = self.engraver.engrave_faces("tetrahedron", face_map_ko, codex=1)
        eng_dr = self.engraver.engrave_faces("tetrahedron", face_map_dr, codex=1)
        ko_face = [e for e in eng_ko if e.surface == "face"][0]
        dr_face = [e for e in eng_dr if e.surface == "face"][0]
        assert dr_face.depth > ko_face.depth

    def test_rotation_uses_golden_angle(self):
        face_map = {"KO": [0, 1, 2]}
        engravings = self.engraver.engrave_faces("tetrahedron", face_map, codex=1)
        face_eng = [e for e in engravings if e.surface == "face"]
        # First face rotation should be 0 * golden_angle
        assert face_eng[0].rotation == 0.0

    def test_symbol_format(self):
        face_map = {"KO": [0]}
        engravings = self.engraver.engrave_faces("tetrahedron", face_map, codex=1)
        face_eng = [e for e in engravings if e.surface == "face"][0]
        # Symbol = tongue + codex name[4] + face_idx
        assert face_eng.symbol.startswith("KO")


# ============================================================
# compute_personality_vector
# ============================================================


@pytest.mark.unit
class TestPersonalityVector:
    def setup_method(self):
        with patch.object(Path, "mkdir", return_value=None):
            self.engraver = SemanticShapeEngraver()

    def test_base_values_at_0_5(self):
        vector = self.engraver.compute_personality_vector([], codex=1)
        for axis, val in vector.items():
            assert val == 0.5

    def test_ko_boosts_focus_and_tenacity(self):
        vector = self.engraver.compute_personality_vector(["KO"], codex=1)
        assert vector["F"] > 0.5
        assert vector["T"] > 0.5

    def test_all_tongues_active(self):
        vector = self.engraver.compute_personality_vector(["KO", "AV", "RU", "CA", "UM", "DR"], codex=1)
        # All axes should be defined
        assert len(vector) == 8

    def test_clamped_to_0_1(self):
        """Even with all tongues active, values stay in [0, 1]."""
        vector = self.engraver.compute_personality_vector(["KO", "AV", "RU", "CA", "UM", "DR"], codex=1)
        for axis, val in vector.items():
            assert 0.0 <= val <= 1.0

    def test_um_reduces_empathy(self):
        vector = self.engraver.compute_personality_vector(["UM"], codex=1)
        assert vector["E"] < 0.5

    def test_ru_reduces_openness(self):
        vector = self.engraver.compute_personality_vector(["RU"], codex=1)
        assert vector["O"] < 0.5


# ============================================================
# compute_semantic_hash
# ============================================================


@pytest.mark.unit
class TestSemanticHash:
    def setup_method(self):
        with patch.object(Path, "mkdir", return_value=None):
            self.engraver = SemanticShapeEngraver()

    def test_same_inputs_same_hash(self):
        eng = [Engraving("face", 0, "KO", "KOF0", 0.5, 0.0)]
        h1 = self.engraver.compute_semantic_hash("cube", eng)
        h2 = self.engraver.compute_semantic_hash("cube", eng)
        assert h1 == h2

    def test_different_tongue_different_hash(self):
        eng_ko = [Engraving("face", 0, "KO", "KOF0", 0.5, 0.0)]
        eng_dr = [Engraving("face", 0, "DR", "DRF0", 0.5, 0.0)]
        h1 = self.engraver.compute_semantic_hash("cube", eng_ko)
        h2 = self.engraver.compute_semantic_hash("cube", eng_dr)
        assert h1 != h2

    def test_different_shape_different_hash(self):
        eng = [Engraving("face", 0, "KO", "KOF0", 0.5, 0.0)]
        h1 = self.engraver.compute_semantic_hash("cube", eng)
        h2 = self.engraver.compute_semantic_hash("tetrahedron", eng)
        assert h1 != h2

    def test_hash_is_hex_string(self):
        eng = [Engraving("face", 0, "KO", "KOF0", 0.5, 0.0)]
        h = self.engraver.compute_semantic_hash("cube", eng)
        assert len(h) == 32  # blake2s digest_size=16 -> 32 hex chars
        int(h, 16)  # should not raise

    def test_order_independent(self):
        """Engravings are sorted before hashing, so order doesn't matter."""
        e1 = Engraving("face", 0, "KO", "A", 0.5, 0.0)
        e2 = Engraving("face", 1, "DR", "B", 0.5, 0.0)
        h1 = self.engraver.compute_semantic_hash("cube", [e1, e2])
        h2 = self.engraver.compute_semantic_hash("cube", [e2, e1])
        assert h1 == h2


# ============================================================
# select_codex
# ============================================================


@pytest.mark.unit
class TestSelectCodex:
    def setup_method(self):
        with patch.object(Path, "mkdir", return_value=None):
            self.engraver = SemanticShapeEngraver()

    def test_ko_av_selects_founder(self):
        codex = self.engraver.select_codex(["KO", "AV"])
        assert codex == 1  # The Founder has tongues KO, AV

    def test_um_dr_selects_watcher(self):
        codex = self.engraver.select_codex(["UM", "DR"])
        assert codex == 2  # The Watcher has tongues UM, DR

    def test_ru_ca_selects_archivist(self):
        codex = self.engraver.select_codex(["RU", "CA"])
        assert codex == 3  # The Archivist has tongues RU, CA

    def test_no_tongues_defaults_to_1(self):
        codex = self.engraver.select_codex([])
        assert codex == 1  # default best_codex

    def test_single_tongue_partial_match(self):
        codex = self.engraver.select_codex(["DR"])
        # DR appears in codex 2 (Watcher), 4 (Heir), 7 (Transformed)
        assert codex in (2, 4, 7)


# ============================================================
# Full engrave pipeline
# ============================================================


@pytest.mark.integration
class TestEngravePipeline:
    def setup_method(self):
        with patch.object(Path, "mkdir", return_value=None):
            self.engraver = SemanticShapeEngraver()

    def test_engrave_returns_engraved_shape(self):
        shape = self.engraver.engrave("test input", ["KO", "RU"], "simple")
        assert isinstance(shape, EngravedShape)

    def test_engrave_has_engravings(self):
        shape = self.engraver.engrave("test", ["KO"], "trivial")
        assert len(shape.engravings) > 0

    def test_engrave_null_tongues(self):
        shape = self.engraver.engrave("test", ["KO"], "trivial")
        assert "KO" not in shape.null_tongues
        assert len(shape.null_tongues) == 5

    def test_engrave_dominant_tongue(self):
        shape = self.engraver.engrave("test", ["DR", "KO"], "standard")
        assert shape.dominant_tongue == "DR"  # first in list

    def test_engrave_cultural_overlay(self):
        shape = self.engraver.engrave("test", ["KO"], cultural_overlay="korean")
        assert shape.cultural_overlay == "korean"

    def test_engrave_default_overlay(self):
        shape = self.engraver.engrave("test", ["KO"])
        assert shape.cultural_overlay == "universal"

    def test_different_tongues_different_hash(self):
        s1 = self.engraver.engrave("test", ["KO"], "simple")
        s2 = self.engraver.engrave("test", ["DR"], "simple")
        assert s1.semantic_hash != s2.semantic_hash


# ============================================================
# enrich_training_record
# ============================================================


@pytest.mark.integration
class TestEnrichTrainingRecord:
    def setup_method(self):
        with patch.object(Path, "mkdir", return_value=None):
            self.engraver = SemanticShapeEngraver()

    def test_returns_record_dict(self):
        m = mock_open()
        with patch("builtins.open", m):
            record = self.engraver.enrich_training_record(
                instruction="What is SCBE?",
                output="SCBE is...",
                active_tongues=["KO"],
            )
        assert isinstance(record, dict)
        assert record["instruction"] == "What is SCBE?"

    def test_record_has_shape_data(self):
        m = mock_open()
        with patch("builtins.open", m):
            record = self.engraver.enrich_training_record(
                instruction="test",
                output="out",
                active_tongues=["KO", "CA"],
            )
        assert "shape" in record
        assert "shape_family" in record
        assert "semantic_hash" in record
        assert "engravings_count" in record

    def test_record_has_codex_data(self):
        m = mock_open()
        with patch("builtins.open", m):
            record = self.engraver.enrich_training_record(
                instruction="test",
                output="out",
                active_tongues=["KO"],
            )
        assert "codex_archetype" in record
        assert "codex_name" in record
        assert "codex_null" in record

    def test_record_truncates_long_instruction(self):
        m = mock_open()
        with patch("builtins.open", m):
            record = self.engraver.enrich_training_record(
                instruction="x" * 1000,
                output="out",
                active_tongues=["KO"],
            )
        assert len(record["instruction"]) == 500

    def test_record_truncates_long_output(self):
        m = mock_open()
        with patch("builtins.open", m):
            record = self.engraver.enrich_training_record(
                instruction="test",
                output="y" * 2000,
                active_tongues=["KO"],
            )
        assert len(record["output"]) == 1000

    def test_writes_to_log_file(self):
        m = mock_open()
        with patch("builtins.open", m):
            self.engraver.enrich_training_record(
                instruction="test",
                output="out",
                active_tongues=["KO"],
            )
        m.assert_called_once()
        handle = m()
        written = handle.write.call_args[0][0]
        parsed = json.loads(written.strip())
        assert parsed["instruction"] == "test"

    def test_view_type_null_heavy(self):
        m = mock_open()
        with patch("builtins.open", m):
            record = self.engraver.enrich_training_record(
                instruction="test",
                output="out",
                active_tongues=["KO"],  # 5 null tongues
            )
        assert record["view_type"] == "null-heavy"

    def test_view_type_partial(self):
        m = mock_open()
        with patch("builtins.open", m):
            record = self.engraver.enrich_training_record(
                instruction="test",
                output="out",
                active_tongues=["KO", "AV", "RU"],  # 3 null tongues
            )
        assert record["view_type"] == "partial"


# ============================================================
# compute_shape_space_size
# ============================================================


@pytest.mark.unit
class TestShapeSpaceSize:
    def setup_method(self):
        with patch.object(Path, "mkdir", return_value=None):
            self.engraver = SemanticShapeEngraver()

    def test_returns_dict(self):
        result = self.engraver.compute_shape_space_size("tetrahedron")
        assert isinstance(result, dict)

    def test_tetrahedron_space(self):
        result = self.engraver.compute_shape_space_size("tetrahedron")
        # 6^4 * 8^4 * 7^6 = 1296 * 4096 * 117649
        expected = (6**4) * (8**4) * (7**6)
        assert result["discrete_shapes"] == expected

    def test_log10_correct(self):
        result = self.engraver.compute_shape_space_size("cube")
        assert abs(result["discrete_log10"] - math.log10(result["discrete_shapes"])) < 1e-6

    def test_continuous_larger_than_discrete(self):
        result = self.engraver.compute_shape_space_size("dodecahedron")
        assert result["continuous_shapes"] > result["discrete_shapes"]

    def test_more_faces_larger_space(self):
        tet = self.engraver.compute_shape_space_size("tetrahedron")
        ico = self.engraver.compute_shape_space_size("icosahedron")
        assert ico["discrete_shapes"] > tet["discrete_shapes"]

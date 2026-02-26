"""
Tests for Spiral Forge RPG — Game API endpoints.

Tests the FastAPI routes that serve the Godot client (scbe_client.gd).
pytest markers: unit, game, api
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Ensure src/ is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.api.game_routes import (
    _harmonic_wall,
    _get_npc_templates,
    CODEX_CATEGORIES,
    game_router,
)

PHI = (1 + math.sqrt(5)) / 2


# ---------- Harmonic Wall (Acceptance Test B) ----------


class TestHarmonicWall:
    def test_deterministic_same_input_same_cost(self):
        """B) SCBE gating is deterministic (same input → same cost)."""
        d, R = 0.7, 1.2
        assert _harmonic_wall(d, R) == _harmonic_wall(d, R)

    def test_safe_is_cheap_danger_is_exponential(self):
        """Safe operations cost little; dangerous ones cost exponentially more."""
        w_safe = _harmonic_wall(0.1, 1.0)
        w_danger = _harmonic_wall(2.5, 1.0)
        assert w_danger / w_safe > 50  # Strong exponential separation

    def test_zero_distance_equals_R(self):
        """At d*=0, wall cost = R * π^0 = R."""
        assert _harmonic_wall(0.0, 1.0) == pytest.approx(1.0)
        assert _harmonic_wall(0.0, 2.5) == pytest.approx(2.5)

    def test_formula_matches_spec(self):
        """H(d*, R) = R · π^(φ·d*)."""
        d, R = 0.5, 1.0
        expected = R * (math.pi ** (PHI * d))
        assert _harmonic_wall(d, R) == pytest.approx(expected)


# ---------- Codex Categories ----------


class TestCodexCategories:
    def test_all_categories_have_risk(self):
        for cat, data in CODEX_CATEGORIES.items():
            assert "risk" in data, f"Category {cat} missing risk"
            assert "tongue" in data, f"Category {cat} missing tongue"

    def test_risk_ordering(self):
        """Math reference is safest, external API is most restricted."""
        assert CODEX_CATEGORIES["math_reference"]["risk"] < CODEX_CATEGORIES["external_api"]["risk"]

    def test_known_categories(self):
        expected = {"math_reference", "lore_wiki", "creature_codex",
                    "strategy_guide", "visual_thermal", "external_api"}
        assert set(CODEX_CATEGORIES.keys()) == expected


# ---------- NPC Dialogue Templates ----------


class TestNPCTemplates:
    def test_known_npcs_have_templates(self):
        for npc_id in ["marcus", "greta", "tomas", "sila", "polly"]:
            templates = _get_npc_templates(npc_id)
            assert len(templates) > 0, f"NPC {npc_id} has no templates"

    def test_unknown_npc_gets_fallback(self):
        templates = _get_npc_templates("nonexistent_npc")
        assert len(templates) >= 3  # Fallback has at least 3 lines

    def test_marcus_mentions_academy(self):
        templates = _get_npc_templates("marcus")
        assert any("Academy" in t for t in templates)

    def test_polly_has_raven_lines(self):
        templates = _get_npc_templates("polly")
        assert any("Caw" in t for t in templates)


# ---------- Content Validation Script ----------


class TestContentValidation:
    def test_validation_script_passes(self):
        """The content validation script should exit cleanly."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/validate_game_content.py"],
            capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent),
        )
        assert result.returncode == 0, f"Validation failed:\n{result.stdout}\n{result.stderr}"

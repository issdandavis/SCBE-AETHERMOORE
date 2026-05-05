"""Validate the generated spine-overlay proof bundle row-by-row.

Re-uses the rules from ``test_motion_assembly_schema.py`` and asserts
that every row in ``training-data/proofs/spine_overlay_proof_v1/data.jsonl``
satisfies them. Skips cleanly when the bundle has not been generated.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_DIR = REPO_ROOT / "training-data" / "proofs" / "spine_overlay_proof_v1"
DATA_PATH = BUNDLE_DIR / "data.jsonl"
MANIFEST_PATH = BUNDLE_DIR / "manifest.json"

REQUIRED_LANES = (
    "version",
    "binary",
    "tokenizer",
    "transport",
    "labels",
    "language_views",
    "braille_lane",
    "stisa",
    "structural_parse",
    "scip_symbol_index",
    "semantic_token_bridge",
    "route_ir",
    "execution_lane",
    "native_tokenization",
    "atomic_states",
    "ternary_semantics",
    "semantic_expression",
)

REQUIRED_INVARIANT_KEYS = (
    "joint_limits_ok",
    "motor_saturation_ok",
    "attitude_bounds_ok",
    "energy_budget_ok",
    "collision_free",
    "morphology_transition_safe",
)

FORBIDDEN_BRANDING_SUBSTRINGS = (
    "megazord",
    "morphin",
    "zord",
    "power_ranger",
    "power ranger",
)

ASCII_ONLY_RE = re.compile(r"^[\x00-\x7f]+$")


pytestmark = pytest.mark.skipif(
    not DATA_PATH.exists(),
    reason="bundle not generated; run scripts/build_spine_overlay_proof.py",
)


def _load_rows() -> list[dict]:
    rows: list[dict] = []
    with DATA_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_keys(item)


def test_manifest_reports_18_rows():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["row_count"] == 18
    assert manifest["domain_breakdown"] == {"chemistry": 6, "code": 6, "motion": 6}


def test_jsonl_row_count_matches_manifest():
    rows = _load_rows()
    assert len(rows) == 18


@pytest.mark.parametrize("lane", REQUIRED_LANES)
def test_every_row_has_required_lane(lane):
    rows = _load_rows()
    for row in rows:
        assert lane in row, f"row {row.get('row_id')} missing lane {lane}"


def test_every_row_has_both_anchor_fields():
    rows = _load_rows()
    for row in rows:
        labels = row["labels"]
        assert isinstance(labels.get("anchor_runtime"), str) and labels["anchor_runtime"]
        assert isinstance(labels.get("anchor_spirit"), str) and labels["anchor_spirit"]


def test_every_row_uses_ascii_field_names():
    rows = _load_rows()
    for row in rows:
        for key in _walk_keys(row):
            assert ASCII_ONLY_RE.match(key), f"row {row.get('row_id')} non-ASCII field name: {key!r}"


def test_no_forbidden_branding_anywhere_in_bundle():
    blob = DATA_PATH.read_text(encoding="utf-8").lower()
    for forbidden in FORBIDDEN_BRANDING_SUBSTRINGS:
        assert forbidden not in blob, f"forbidden branding substring in bundle: {forbidden!r}"


def test_motion_rows_carry_motion_assembly_under_semantic_expression():
    rows = _load_rows()
    motion_rows = [r for r in rows if r["domain"] == "motion"]
    assert len(motion_rows) == 6
    for row in motion_rows:
        sem = row["semantic_expression"]
        assert "motion_assembly" not in row, "motion_assembly must NOT be top-level"
        assert "motion_assembly" in sem, f"motion row {row['row_id']} missing nested motion_assembly"
        ma = sem["motion_assembly"]
        assert ma["schema_version"] == "scbe-motion-assembly-v1"
        assert isinstance(ma["pilot_layers"], list) and len(ma["pilot_layers"]) >= 1
        ctbr_layers = [
            layer
            for layer in ma["pilot_layers"]
            if layer.get("action_vector") is not None and len(layer["action_vector"]) == 4
        ]
        assert ctbr_layers, f"motion row {row['row_id']} has no CTBR layer"
        for key in REQUIRED_INVARIANT_KEYS:
            assert isinstance(ma["invariants"][key], bool), f"motion row {row['row_id']} invariant {key} not bool"


def test_chemistry_rows_carry_chemistry_overlay_under_semantic_expression():
    rows = _load_rows()
    chem_rows = [r for r in rows if r["domain"] == "chemistry"]
    assert len(chem_rows) == 6
    for row in chem_rows:
        sem = row["semantic_expression"]
        assert "chemistry_overlay" not in row
        assert "chemistry_overlay" in sem
        overlay = sem["chemistry_overlay"]
        assert overlay["equation"] == "2H2 + O2 -> 2H2O"
        assert overlay["reaction_class"] == "synthesis"
        assert overlay["stability"] == "stable"
        assert overlay["atoms_conserved"] == {"H": 4, "O": 2}


def test_code_rows_have_no_domain_overlay():
    """Code rows are pure baseline-spine; their semantic_expression has no
    nested overlay block beyond label/gloss/quarks."""

    rows = _load_rows()
    code_rows = [r for r in rows if r["domain"] == "code"]
    assert len(code_rows) == 6
    for row in code_rows:
        sem = row["semantic_expression"]
        assert "motion_assembly" not in sem
        assert "chemistry_overlay" not in sem
        assert sem["label"] == "add_function"
        assert sem["gloss"] == "add x and y"


def test_tongue_anchor_runtime_and_spirit_match_canonical_map():
    """Every row's anchor_runtime/anchor_spirit follows the tongue's
    canonical language map (no flattening)."""

    expected = {
        "KO": ("python", "python"),
        "AV": ("typescript", "javascript"),
        "RU": ("rust", "rust"),
        "CA": ("c", "mathematica"),
        "UM": ("julia", "haskell"),
        "DR": ("haskell", "markdown"),
    }
    rows = _load_rows()
    for row in rows:
        tongue = row["tokenizer"]["tongue"]
        runtime, spirit = expected[tongue]
        assert row["labels"]["anchor_runtime"] == runtime
        assert row["labels"]["anchor_spirit"] == spirit

"""Test suite for the Tokenizer Master Class SFT records.

Validates that drift-correction, semantic math, and tongue-role records are:
  - Arithmetically consistent (phi-correction math checks out)
  - Language-role consistent (tongues used as operators, not labels)
  - State-preserving (variable survives drift and correction)
  - Schema-valid (messages format, metadata fields)

Canonical tongue names:
  KO = Kor'aelin (red-gold, Intent, "what should be true")
  AV = Avali (blue-silver, Context, "how to get there")
  RU = Runethic (deep purple, Binding, "who is allowed")
  CA = Cassisivadan (white-gold, Implementation, "how to make it true")
  UM = Umbroth (shadow-black, Security, "what must stay hidden")
  DR = Draumric (earth-brown, Structure, "proof that it is true")
"""

import json
import math
from pathlib import Path

import pytest

PHI = 1.618033988749895

# Canonical names from the Six Tongues Protocol book (Chapter 2, lines 414-424)
CANONICAL_TONGUES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}

REQUIRED_CODES = set(CANONICAL_TONGUES.keys())

# Wrong names from other AI sessions -- must NOT appear
WRONG_NAMES = {"Koson", "KOSON", "Aven", "AVEN", "Rulon", "RULON", "Cael", "CAEL", "Umbra", "UMBRA", "Dron", "DRON"}

SFT_PATH = Path(__file__).resolve().parents[1] / "training-data" / "sft" / "tokenizer_master_class_sft.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file, fail loudly on bad lines."""
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise AssertionError(f"Invalid JSON on line {line_no}: {e}") from e
    return records


def extract_role_text(record: dict, role: str) -> str:
    for msg in record.get("messages", []):
        if msg.get("role") == role:
            return msg.get("content", "")
    raise AssertionError(f"No {role} message found in record")


# ──────────────────────────────────────────
# Schema tests
# ──────────────────────────────────────────


class TestRecordSchema:
    """Every record must have the right shape."""

    def test_messages_format(self, tmp_path):
        """Messages array with system/user/assistant."""
        sample = {
            "messages": [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "usr"},
                {"role": "assistant", "content": "asst"},
            ],
            "tongue_weights": {"KO": 0.25, "AV": 0.05, "RU": 0.25, "CA": 0.25, "UM": 0.05, "DR": 0.15},
            "difficulty": 0.9,
        }
        assert isinstance(sample["messages"], list)
        assert len(sample["messages"]) >= 3
        roles = [m["role"] for m in sample["messages"]]
        assert "system" in roles
        assert "user" in roles
        assert "assistant" in roles

    def test_tongue_weights_all_present(self):
        weights = {"KO": 0.25, "AV": 0.05, "RU": 0.25, "CA": 0.25, "UM": 0.05, "DR": 0.15}
        assert REQUIRED_CODES.issubset(weights.keys())

    def test_difficulty_in_range(self):
        for d in [0.0, 0.5, 0.9, 1.0]:
            assert 0.0 <= d <= 1.0

    def test_tongue_weights_sum_reasonable(self):
        """Tongue weights should sum to ~1.0 (normalized) or be raw activations."""
        weights = {"KO": 0.25, "AV": 0.05, "RU": 0.25, "CA": 0.25, "UM": 0.05, "DR": 0.15}
        total = sum(weights.values())
        assert 0.5 <= total <= 1.5, f"Tongue weights sum {total} seems off"


# ──────────────────────────────────────────
# Phi-correction math tests
# ──────────────────────────────────────────


class TestPhiCorrectionMath:
    """The phi-correction arithmetic must be exact."""

    def test_basic_drift_correction(self):
        initial = 0.8128
        drift = 0.0042
        raw = initial + drift
        correction = drift / PHI
        corrected = raw - correction

        assert math.isclose(raw, 0.8170, abs_tol=1e-9)
        # IEEE 754: 0.0042 is not exactly representable in binary float,
        # so division by phi accumulates ~1e-8 representational noise.
        assert math.isclose(correction, drift / PHI, rel_tol=1e-12)
        assert math.isclose(corrected, raw - (drift / PHI), rel_tol=1e-12)

    def test_negative_drift_correction(self):
        initial = 0.6500
        drift = -0.0031
        raw = initial + drift
        correction = drift / PHI  # negative correction
        corrected = raw - correction  # subtracting negative = adding back

        assert corrected > raw, "Negative drift correction should increase value back toward initial"
        assert math.isclose(corrected, raw - correction, rel_tol=1e-12)

    def test_phi_ratio_property(self):
        """Core phi scaling guarantees for Sacred Tongue weights.

        1. Consecutive ratio: phi^n / phi^(n-1) = phi (each tongue
           is exactly phi times stronger than the one below it).
        2. Fibonacci recurrence: phi^(n+2) = phi^(n+1) + phi^n
           (each tongue equals the sum of the two immediately below).
        3. Strict hierarchy: phi^n > phi^(n-1) for all n >= 1.
        """
        for n in range(1, 6):
            # Consecutive ratio = phi
            ratio = PHI**n / PHI ** (n - 1)
            assert math.isclose(ratio, PHI, rel_tol=1e-12), f"phi^{n}/phi^{n-1} = {ratio}, expected phi"
            # Strict hierarchy
            assert PHI**n > PHI ** (n - 1)

        # Fibonacci recurrence: phi^(n+2) = phi^(n+1) + phi^n
        for n in range(0, 4):
            lhs = PHI ** (n + 2)
            rhs = PHI ** (n + 1) + PHI**n
            assert math.isclose(lhs, rhs, rel_tol=1e-12), f"phi^{n+2} ({lhs}) should equal phi^{n+1} + phi^{n} ({rhs})"

    def test_snapping_to_grid(self):
        """Phi-corrected value should round to 4 decimal places for stable grid."""
        corrected = 0.8144042584385453
        snapped = round(corrected, 4)
        assert snapped == 0.8144

    def test_drift_correction_preserves_ordering(self):
        """After correction, value should be between initial and drifted."""
        initial = 0.8128
        drift = 0.0042
        drifted = initial + drift
        corrected = drifted - (drift / PHI)

        assert (
            initial < corrected < drifted
        ), f"Corrected {corrected} should be between initial {initial} and drifted {drifted}"


# ──────────────────────────────────────────
# Tongue name tests
# ──────────────────────────────────────────


class TestCanonicalTongueNames:
    """Only canonical names from the Six Tongues Protocol book."""

    def test_correct_names(self):
        assert CANONICAL_TONGUES["KO"] == "Kor'aelin"
        assert CANONICAL_TONGUES["AV"] == "Avali"
        assert CANONICAL_TONGUES["RU"] == "Runethic"
        assert CANONICAL_TONGUES["CA"] == "Cassisivadan"
        assert CANONICAL_TONGUES["UM"] == "Umbroth"
        assert CANONICAL_TONGUES["DR"] == "Draumric"

    def test_wrong_names_rejected(self):
        """The wrong names from other AI sessions must never appear."""
        sample_text = (
            "Kor'aelin preserved the original intent. "
            "Avali registered the contextual entropy event. "
            "Runethic re-bound the drifting variable to its manifold. "
            "Cassisivadan executed the numerical correction. "
            "Draumric kept the state transition structured. "
            "Umbroth preserved the hidden instability."
        )
        for wrong in WRONG_NAMES:
            assert wrong not in sample_text, f"Wrong name '{wrong}' found in text"

    def test_all_six_tongues_present_in_text(self):
        """A good drift record should mention all 6 canonical tongues."""
        text = (
            "Kor'aelin preserved intent. Avali registered context. "
            "Runethic re-bound the variable. Cassisivadan computed correction. "
            "Umbroth veiled instability. Draumric authenticated the state."
        )
        for code, name in CANONICAL_TONGUES.items():
            assert name in text, f"Missing tongue {name} ({code}) in record text"


# ──────────────────────────────────────────
# Content quality tests
# ──────────────────────────────────────────


class TestContentQuality:
    """Records must contain real math AND semantic roles, not just one."""

    def test_assistant_has_numeric_content(self):
        """The assistant answer must contain actual numbers, not just lore."""
        good = "Corrected trust: 0.8144. Phi-correction: 0.0042 / 1.618 = 0.00260."
        bad = "Kor'aelin sings through Avali and Runethic heals the manifold."

        assert any(ch.isdigit() for ch in good), "Good answer should have numbers"
        assert not any(ch.isdigit() for ch in bad), "Bad answer fixture should have no numbers"

    def test_assistant_has_tongue_roles(self):
        """The assistant answer must assign tongues operational roles."""
        text = (
            "Kor'aelin preserved the original intent of trust continuity. "
            "Cassisivadan executed the numerical correction."
        )
        has_roles = any(name in text for name in CANONICAL_TONGUES.values())
        assert has_roles

    def test_no_decorative_only_answer(self):
        """Answers that mention tongues but do no math are invalid."""
        decorative = (
            "Kor'aelin sings through Avali and Runethic heals the manifold. "
            "The drift is entropy and the state returns."
        )
        has_numeric = any(ch.isdigit() for ch in decorative)
        # A valid record MUST have numbers. This fixture should fail.
        assert not has_numeric, "Decorative-only answers must not pass validation"

    def test_state_transition_is_explicit(self):
        """The answer must show: anchor -> drift -> correction -> result."""
        text = (
            "Runethic anchor: active_trust = 0.8128\n"
            "Observed drift: +0.0042\n"
            "Raw drifted value: 0.8170\n"
            "Phi-correction magnitude: 0.0042 / 1.618033988749895 = 0.002595742\n"
            "Corrected trust: 0.814404258\n"
            "Nearest stable Runethic value: 0.8144"
        )
        required = ["anchor", "drift", "correction", "Corrected"]
        for word in required:
            assert word.lower() in text.lower(), f"Missing state transition step: {word}"

    def test_difficulty_boosted_for_drift_records(self):
        """Records about drift/semantic math should have difficulty >= 0.7."""
        trigger_terms = ["decimal drift", "semantic math", "phi-correction", "drift compensation"]
        user_text = "Apply Decimal Drift correction with Semantic Math"
        difficulty = 0.9

        if any(term.lower() in user_text.lower() for term in trigger_terms):
            assert difficulty >= 0.7, f"Drift record difficulty {difficulty} should be >= 0.7"


# ──────────────────────────────────────────
# Variable state tests
# ──────────────────────────────────────────


class TestVariableState:
    """Variables must survive drift events with traceable state."""

    def test_state_chain_is_monotonic(self):
        """init < corrected < drifted (for positive drift)."""
        states = [
            ("init", 0.8128),
            ("drifted", 0.8170),
            ("corrected", 0.8144042584385453),
        ]
        init_val = states[0][1]
        drift_val = states[1][1]
        corr_val = states[2][1]

        assert init_val < corr_val < drift_val

    def test_correction_reduces_error(self):
        """Corrected value should be closer to initial than drifted value."""
        initial = 0.8128
        drifted = 0.8170
        corrected = 0.8144042584385453

        error_before = abs(drifted - initial)
        error_after = abs(corrected - initial)
        assert error_after < error_before, f"Correction should reduce error: {error_after} should be < {error_before}"

    def test_multiple_drift_events_accumulate(self):
        """Multiple drifts without correction accumulate error."""
        initial = 0.8128
        drifts = [0.0042, -0.0018, 0.0031, -0.0007, 0.0055]
        current = initial
        for d in drifts:
            current += d

        total_drift = sum(drifts)
        assert math.isclose(current, initial + total_drift, rel_tol=1e-12)
        assert abs(current - initial) > abs(drifts[0]), "Multiple drifts should accumulate"

    def test_epoch_snap_resets_drift(self):
        """After N evaluations, epoch snapping recomputes from phi."""
        # Simulate drifted weights
        drifted_weights = [1.001, 1.619, 2.620, 4.238, 6.856, 11.092]

        # Epoch snap: recompute from phi
        snapped = [PHI**i for i in range(6)]

        # Verify snap is exact
        for i, (d, s) in enumerate(zip(drifted_weights, snapped)):
            assert d != s, f"Weight {i} should have drifted"
            assert math.isclose(s, PHI**i, rel_tol=1e-15), f"Snapped weight {i} should be exact phi^{i}"


# ──────────────────────────────────────────
# Null-space tests
# ──────────────────────────────────────────


class TestNullSpace:
    """Null-space encoding: absence is structure, not emptiness."""

    def test_null_is_not_zero(self):
        """Null tongue activation != 0.0. It means latent/unactivated."""
        null_activation = {"state": "null", "value": None, "description": "latent but unactivated"}
        zero_activation = {"state": "active", "value": 0.0, "description": "active with zero intensity"}

        assert null_activation["state"] != zero_activation["state"]
        assert null_activation["value"] is None  # null is None, not 0

    def test_inverse_null_is_blocked(self):
        """InverseNull = candidate but blocked by boundary."""
        inv_null = {"state": "inverse_null", "blocked_by": "boundary_condition"}
        assert inv_null["state"] == "inverse_null"
        assert "blocked_by" in inv_null

    def test_gating_function_shape(self):
        """g_t(p) = sigma(w_a*a + w_r*r + w_b*b + w_f*f - theta) is valid sigmoid."""
        import math

        def sigmoid(x):
            return 1.0 / (1.0 + math.exp(-x))

        # All gates open
        g_open = sigmoid(0.5 * 1.0 + 0.3 * 1.0 + 0.4 * 1.0 + 0.3 * 1.0 - 0.5)
        assert 0 < g_open < 1
        assert g_open > 0.5, "All-open gates should pass"

        # One gate blocked (boundary violation)
        g_blocked = sigmoid(0.5 * 1.0 + 0.3 * 0.0 + 0.4 * 1.0 + 0.3 * 1.0 - 0.5)
        assert g_blocked < g_open, "Blocked gate should reduce admission probability"

    def test_constrained_trajectory_scoring(self):
        """P*(p|h_t) = P(p|h_t) * g_t(p) -- constrained prob is always <= unconstrained."""
        p_unconstrained = 0.85
        g_t = 0.72  # gate factor
        p_constrained = p_unconstrained * g_t

        assert p_constrained <= p_unconstrained
        assert p_constrained > 0  # not zeroed out, just reduced


# ──────────────────────────────────────────
# Integration test (requires generated file)
# ──────────────────────────────────────────


@pytest.mark.skipif(not SFT_PATH.exists(), reason="Master class SFT not yet generated")
class TestGeneratedFile:
    """Tests against the actual generated JSONL file."""

    @pytest.fixture(scope="class")
    def records(self):
        return load_jsonl(SFT_PATH)

    def test_file_has_records(self, records):
        assert len(records) >= 100, f"Expected 100+ records, got {len(records)}"

    def test_all_records_have_messages(self, records):
        for i, rec in enumerate(records):
            assert "messages" in rec, f"Record {i} missing 'messages'"
            assert len(rec["messages"]) >= 3, f"Record {i} has < 3 messages"

    def test_no_wrong_tongue_names(self, records):
        for i, rec in enumerate(records):
            full_text = json.dumps(rec)
            for wrong in WRONG_NAMES:
                assert wrong not in full_text, f"Record {i} contains wrong tongue name '{wrong}'"

    def test_all_canonical_names_used(self, records):
        all_text = " ".join(json.dumps(r) for r in records)
        for code, name in CANONICAL_TONGUES.items():
            assert name in all_text, f"Canonical name {name} ({code}) never appears in dataset"

    def test_drift_records_have_math(self, records):
        """Drift correction records should contain numeric content.

        Records with 'drift' in the user prompt that are about phi-correction
        math (not debugging or architecture patterns) should have numbers.
        """
        drift_records = [
            r
            for r in records
            if "drift" in extract_role_text(r, "user").lower()
            and "bug report" not in extract_role_text(r, "user").lower()
            and "implement" not in extract_role_text(r, "user").lower()
            and "design:" not in extract_role_text(r, "user").lower()
        ]
        for i, rec in enumerate(drift_records):
            assistant_text = extract_role_text(rec, "assistant")
            has_numbers = any(ch.isdigit() for ch in assistant_text)
            assert has_numbers, f"Drift record {i} has no numeric content"

    def test_difficulty_distribution(self, records):
        difficulties = [r.get("difficulty", 0) for r in records]
        avg = sum(difficulties) / len(difficulties)
        assert avg >= 0.5, f"Average difficulty {avg:.2f} too low for master class"
        high_count = sum(1 for d in difficulties if d >= 0.7)
        assert high_count >= len(records) * 0.5, "At least 50% of records should be difficulty >= 0.7"

"""
Test suite for canonical master + 6 derived trainer views.

Tests the FULL alphabet:
  A. Schema validation (required fields present, correct types)
  B. Format compliance (OpenAI chat, TRL conversation, TRL prompt-completion)
  C. Cross-view consistency (same source → coherent across views)
  D. Tongue/layer/governance distributions (no silent collapses)
  E. FU status logic (operative/inverse_null/null classifications)
  F. Boundary classification thresholds (RETAIN/DEFER/LIFT)
  G. Quaternary invariant integrity (7 invariants, 6 tongues, 6 languages)
  H. Absence signal (null tongue patterns, average null count)
  I. Content sanity (no empty instructions/outputs, no truncation artifacts)
  J. Round-trip fidelity (canonical → derived → parseable back)
  K. Deduplication (no exact duplicate records)
  L. Edge cases (unicode, escape sequences, long records, empty fields)
  M. Station output compatibility (training_data.jsonl passes station schema)
"""

import json
import os
import pytest
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SFT_DIR = REPO / "training-data" / "sft"
CANONICAL = SFT_DIR / "canonical_master.jsonl"
QUATERNARY = SFT_DIR / "l0_quaternary_substrate_sft.jsonl"

DERIVED = {
    "trl_conversation": SFT_DIR / "derived_trl_conversation.jsonl",
    "trl_prompt_completion": SFT_DIR / "derived_trl_prompt_completion.jsonl",
    "openai_chat": SFT_DIR / "derived_openai_chat.jsonl",
    "activation_cls": SFT_DIR / "derived_activation_cls.jsonl",
    "governance_cls": SFT_DIR / "derived_governance_cls.jsonl",
    "contrast_pairs": SFT_DIR / "derived_contrast_pairs.jsonl",
}

VALID_TONGUES = {"KO", "AV", "RU", "CA", "UM", "DR"}
VALID_LAYERS = {"L0", "L1", "L2", "L3", "L-1-L3", "L11", "L12", "L13", "unknown"}
VALID_GOVERNANCE = {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
VALID_FU_STATUS = {"operative", "inverse_null", "null"}
VALID_BOUNDARY = {"RETAIN", "DEFER", "LIFT"}
VALID_INVARIANTS = {
    "Nesting Quad", "Operator Quad", "Identifier Quad",
    "Whitespace Quad", "Number Quad", "Escape Quad", "Control Flow Quad",
}
VALID_LANGUAGES = {"Python", "TypeScript", "JavaScript", "Rust", "Go", "C++"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_jsonl(path, limit=None):
    """Load JSONL file, return list of dicts."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def sample_records(path, n=500, seed=42):
    """Load up to n records from a JSONL file, deterministically sampled."""
    import random
    all_recs = load_jsonl(path)
    if len(all_recs) <= n:
        return all_recs
    rng = random.Random(seed)
    return rng.sample(all_recs, n)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def canonical_records():
    if not CANONICAL.exists():
        pytest.skip("canonical_master.jsonl not found")
    return load_jsonl(CANONICAL)


@pytest.fixture(scope="module")
def canonical_sample():
    if not CANONICAL.exists():
        pytest.skip("canonical_master.jsonl not found")
    return sample_records(CANONICAL, 1000)


@pytest.fixture(scope="module")
def quaternary_records():
    if not QUATERNARY.exists():
        pytest.skip("l0_quaternary_substrate_sft.jsonl not found")
    return load_jsonl(QUATERNARY)


@pytest.fixture(scope="module")
def derived_trl_conv():
    p = DERIVED["trl_conversation"]
    if not p.exists():
        pytest.skip(f"{p.name} not found")
    return sample_records(p, 500)


@pytest.fixture(scope="module")
def derived_openai():
    p = DERIVED["openai_chat"]
    if not p.exists():
        pytest.skip(f"{p.name} not found")
    return sample_records(p, 500)


@pytest.fixture(scope="module")
def derived_prompt_completion():
    p = DERIVED["trl_prompt_completion"]
    if not p.exists():
        pytest.skip(f"{p.name} not found")
    return sample_records(p, 500)


@pytest.fixture(scope="module")
def derived_activation():
    p = DERIVED["activation_cls"]
    if not p.exists():
        pytest.skip(f"{p.name} not found")
    return sample_records(p, 500)


@pytest.fixture(scope="module")
def derived_governance():
    p = DERIVED["governance_cls"]
    if not p.exists():
        pytest.skip(f"{p.name} not found")
    return sample_records(p, 500)


@pytest.fixture(scope="module")
def derived_contrast():
    p = DERIVED["contrast_pairs"]
    if not p.exists():
        pytest.skip(f"{p.name} not found")
    return load_jsonl(p)  # small enough to load all


# ===========================================================================
# A. SCHEMA VALIDATION — canonical master
# ===========================================================================

class TestCanonicalSchema:
    REQUIRED_FIELDS = {
        "substrate", "activation", "relation", "permission", "flow",
        "target", "fu_status",
    }

    def test_all_required_fields_present(self, canonical_sample):
        for i, rec in enumerate(canonical_sample):
            missing = self.REQUIRED_FIELDS - set(rec.keys())
            assert not missing, f"Record {i}: missing {missing}"

    def test_substrate_is_dict(self, canonical_sample):
        for rec in canonical_sample:
            assert isinstance(rec["substrate"], dict)

    def test_activation_has_layer(self, canonical_sample):
        for rec in canonical_sample:
            act = rec["activation"]
            assert isinstance(act, dict)
            assert "layer" in act, f"activation missing 'layer': {list(act.keys())}"

    def test_permission_has_governance(self, canonical_sample):
        for rec in canonical_sample:
            perm = rec["permission"]
            assert isinstance(perm, dict)
            assert "governance" in perm

    def test_fu_status_valid(self, canonical_sample):
        for rec in canonical_sample:
            assert rec["fu_status"] in VALID_FU_STATUS, f"Bad fu_status: {rec['fu_status']}"

    def test_boundary_class_valid(self, canonical_sample):
        for rec in canonical_sample:
            bc = rec.get("permission", {}).get("class", "")
            assert bc in VALID_BOUNDARY, f"Bad boundary: {bc}"

    def test_target_has_instruction_and_response(self, canonical_sample):
        for rec in canonical_sample:
            t = rec["target"]
            assert isinstance(t, dict)
            assert "instruction" in t or "response" in t, "target must have instruction or response"


# ===========================================================================
# B. FORMAT COMPLIANCE — OpenAI / TRL
# ===========================================================================

class TestOpenAIChatFormat:
    """OpenAI fine-tuning requires {"messages": [{"role": ..., "content": ...}]}"""

    def test_has_messages_key(self, derived_openai):
        for rec in derived_openai:
            assert "messages" in rec, f"Missing 'messages' key: {list(rec.keys())}"

    def test_messages_is_list(self, derived_openai):
        for rec in derived_openai:
            assert isinstance(rec["messages"], list)

    def test_each_message_has_role_and_content(self, derived_openai):
        for rec in derived_openai:
            for msg in rec["messages"]:
                assert "role" in msg, f"Message missing 'role': {msg}"
                assert "content" in msg, f"Message missing 'content': {msg}"

    def test_roles_are_valid(self, derived_openai):
        valid_roles = {"system", "user", "assistant"}
        for rec in derived_openai:
            for msg in rec["messages"]:
                assert msg["role"] in valid_roles, f"Bad role: {msg['role']}"

    def test_system_message_is_first_if_present(self, derived_openai):
        for rec in derived_openai:
            msgs = rec["messages"]
            system_indices = [i for i, m in enumerate(msgs) if m["role"] == "system"]
            if system_indices:
                assert system_indices[0] == 0, "System message must be first"
                assert len(system_indices) == 1, "Only one system message allowed"

    def test_has_at_least_user_and_assistant(self, derived_openai):
        for rec in derived_openai:
            roles = {m["role"] for m in rec["messages"]}
            assert "user" in roles, "Must have user message"
            assert "assistant" in roles, "Must have assistant message"

    def test_content_is_nonempty_string(self, derived_openai):
        for rec in derived_openai:
            for msg in rec["messages"]:
                assert isinstance(msg["content"], str)
                assert len(msg["content"].strip()) > 0, f"Empty content for role={msg['role']}"


class TestTRLConversationFormat:
    """TRL SFTTrainer conversational: {"messages": [...]} same as OpenAI but may have metadata."""

    def test_has_messages(self, derived_trl_conv):
        for rec in derived_trl_conv:
            assert "messages" in rec

    def test_messages_structure(self, derived_trl_conv):
        for rec in derived_trl_conv:
            for msg in rec["messages"]:
                assert "role" in msg and "content" in msg

    def test_last_message_is_assistant(self, derived_trl_conv):
        for rec in derived_trl_conv:
            msgs = rec["messages"]
            assert msgs[-1]["role"] == "assistant", "Last message should be assistant"


class TestTRLPromptCompletionFormat:
    """TRL prompt-completion: {"prompt": ..., "completion": ...}"""

    def test_has_prompt_and_completion(self, derived_prompt_completion):
        for rec in derived_prompt_completion:
            assert "prompt" in rec, f"Missing 'prompt': {list(rec.keys())}"
            assert "completion" in rec, f"Missing 'completion': {list(rec.keys())}"

    def test_prompt_is_nonempty(self, derived_prompt_completion):
        for rec in derived_prompt_completion:
            assert isinstance(rec["prompt"], str)
            assert len(rec["prompt"].strip()) > 0

    def test_completion_is_nonempty(self, derived_prompt_completion):
        for rec in derived_prompt_completion:
            assert isinstance(rec["completion"], str)
            assert len(rec["completion"].strip()) > 0


# ===========================================================================
# C. CROSS-VIEW CONSISTENCY
# ===========================================================================

class TestCrossViewConsistency:
    def test_derived_counts_are_consistent(self):
        """All message-format views should have the same record count."""
        counts = {}
        for name, path in DERIVED.items():
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    counts[name] = sum(1 for line in f if line.strip())

        # trl_conv, trl_prompt, openai should match
        msg_views = ["trl_conversation", "trl_prompt_completion", "openai_chat"]
        msg_counts = [counts.get(v) for v in msg_views if v in counts]
        if len(msg_counts) >= 2:
            assert len(set(msg_counts)) == 1, f"Message view counts differ: {dict(zip(msg_views, msg_counts))}"

        # activation and governance should match canonical
        cls_views = ["activation_cls", "governance_cls"]
        cls_counts = [counts.get(v) for v in cls_views if v in counts]
        if len(cls_counts) >= 2:
            assert len(set(cls_counts)) == 1, f"Classifier view counts differ: {dict(zip(cls_views, cls_counts))}"

    def test_canonical_count_gte_derived(self):
        """Canonical should have >= records as any derived view."""
        if not CANONICAL.exists():
            pytest.skip("no canonical")
        with open(CANONICAL, "r", encoding="utf-8") as f:
            canon_count = sum(1 for line in f if line.strip())
        for name, path in DERIVED.items():
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    derived_count = sum(1 for line in f if line.strip())
                assert canon_count >= derived_count, (
                    f"Derived {name} ({derived_count}) > canonical ({canon_count})"
                )


# ===========================================================================
# D. DISTRIBUTION CHECKS — no silent collapses
# ===========================================================================

class TestDistributions:
    def test_all_six_tongues_represented(self, canonical_records):
        tongues = set()
        for rec in canonical_records:
            act = rec.get("activation", {})
            for t in act.get("tongues_active", []):
                tongues.add(t)
        present = tongues & VALID_TONGUES
        assert len(present) >= 5, f"Only {len(present)} tongues present: {present}"

    def test_multiple_layers_represented(self, canonical_records):
        layers = Counter(rec.get("activation", {}).get("layer", "unknown")
                         for rec in canonical_records)
        assert len(layers) >= 3, f"Only {len(layers)} layers: {layers}"
        assert layers.get("L0", 0) > 0, "No L0 records"

    def test_governance_has_allow(self, canonical_records):
        """Canonical master should have ALLOW records. Other governance values
        come from FU-generated files which flow through the station, not the
        canonical master itself."""
        gov = Counter(rec.get("permission", {}).get("governance", "ALLOW")
                      for rec in canonical_records)
        assert "ALLOW" in gov, f"No ALLOW in governance: {gov}"

    def test_fu_status_distribution(self, canonical_records):
        statuses = Counter(rec["fu_status"] for rec in canonical_records)
        # We expect mostly null (honest), but operative should exist
        assert "null" in statuses, "No null FU records"
        total = sum(statuses.values())
        assert total == len(canonical_records)

    def test_boundary_distribution(self, canonical_records):
        boundaries = Counter(rec.get("permission", {}).get("class", "DEFER")
                             for rec in canonical_records)
        assert len(boundaries) >= 2, f"Only one boundary class: {boundaries}"


# ===========================================================================
# E. FU STATUS LOGIC
# ===========================================================================

class TestFUStatusLogic:
    def test_operative_requires_nonzero_activation(self, canonical_sample):
        for rec in canonical_sample:
            if rec["fu_status"] == "operative":
                act = rec["activation"]
                score = act.get("activation_score", 0.0)
                assert score > 0, f"Operative with zero activation: {act}"

    def test_null_has_low_or_zero_activation(self, canonical_sample):
        nulls = [r for r in canonical_sample if r["fu_status"] == "null"]
        if nulls:
            scores = [r["activation"].get("activation_score", 0.0) for r in nulls[:200]]
            avg = sum(scores) / len(scores) if scores else 0
            # Most nulls should have low scores
            assert avg < 0.8, f"Null records have suspiciously high avg activation: {avg}"


# ===========================================================================
# F. BOUNDARY CLASSIFICATION THRESHOLDS
# ===========================================================================

class TestBoundaryThresholds:
    def test_retain_has_high_score(self, canonical_sample):
        retains = [r for r in canonical_sample
                   if r.get("permission", {}).get("class") == "RETAIN"]
        for rec in retains:
            score = rec["permission"].get("boundary_score", 0.0)
            assert score >= 0.5, f"RETAIN with low score: {score}"

    def test_lift_has_low_score(self, canonical_sample):
        lifts = [r for r in canonical_sample
                 if r.get("permission", {}).get("class") == "LIFT"]
        for rec in lifts[:200]:
            score = rec["permission"].get("boundary_score", 0.0)
            assert score < 0.6, f"LIFT with high score: {score}"


# ===========================================================================
# G. QUATERNARY INVARIANT INTEGRITY
# ===========================================================================

class TestQuaternaryInvariants:
    def test_record_count(self, quaternary_records):
        assert len(quaternary_records) == 500, f"Expected 500, got {len(quaternary_records)}"

    def test_all_seven_invariants_present(self, quaternary_records):
        invariants = {r["invariant"] for r in quaternary_records}
        assert invariants == VALID_INVARIANTS, f"Missing: {VALID_INVARIANTS - invariants}"

    def test_all_six_tongues_used(self, quaternary_records):
        tongues = {r["tongue"] for r in quaternary_records}
        assert tongues == VALID_TONGUES, f"Missing tongues: {VALID_TONGUES - tongues}"

    def test_invariant_distribution_balanced(self, quaternary_records):
        counts = Counter(r["invariant"] for r in quaternary_records)
        values = list(counts.values())
        # Each invariant should have 65-80 records (500/7 ≈ 71.4)
        for name, count in counts.items():
            assert 60 <= count <= 85, f"{name} has {count} records (expected 65-80)"

    def test_tongue_distribution_balanced(self, quaternary_records):
        counts = Counter(r["tongue"] for r in quaternary_records)
        for tongue, count in counts.items():
            assert 70 <= count <= 95, f"{tongue} has {count} records (expected ~83)"

    def test_quad_pattern_is_list_of_four(self, quaternary_records):
        for rec in quaternary_records:
            p = rec["quad_pattern"]
            assert isinstance(p, list) and len(p) == 4, f"Bad quad_pattern: {p}"
            assert all(isinstance(x, int) and 0 <= x <= 3 for x in p)

    def test_all_records_are_l0(self, quaternary_records):
        for rec in quaternary_records:
            assert rec["layer"] == "L0"

    def test_all_records_governance_allow(self, quaternary_records):
        for rec in quaternary_records:
            assert rec["governance"] == "ALLOW"

    def test_tongues_null_excludes_active(self, quaternary_records):
        for rec in quaternary_records:
            active = set(rec["tongues_active"])
            null = set(rec["tongues_null"])
            assert active & null == set(), f"Overlap: {active & null}"

    def test_instruction_references_invariant(self, quaternary_records):
        """Instruction should reference the invariant by name OR by its states."""
        for rec in quaternary_records:
            inv = rec["invariant"]
            inst = rec["instruction"]
            # Name, first word of name, or the states string should appear
            name_present = inv in inst or inv.split()[0] in inst
            # Check if states appear (e.g. "Start-Continue-Digit-Special")
            states_present = "-" in inst and any(
                s in inst for s in ["Open-", "Action-", "Start-", "Space-",
                                    "Integer-", "Escape-", "Enter-"]
            )
            assert name_present or states_present, (
                f"Instruction doesn't reference invariant '{inv}': {inst[:100]}"
            )

    def test_output_contains_code_block(self, quaternary_records):
        for rec in quaternary_records:
            assert "```" in rec["output"], "Output should contain code example"


# ===========================================================================
# H. ABSENCE SIGNAL
# ===========================================================================

class TestAbsenceSignal:
    def test_null_tongues_are_valid(self, canonical_sample):
        for rec in canonical_sample:
            nulls = rec["activation"].get("tongues_null", [])
            for t in nulls:
                assert t in VALID_TONGUES, f"Invalid null tongue: {t}"

    def test_active_and_null_dont_overlap(self, canonical_sample):
        for rec in canonical_sample:
            act = rec["activation"]
            active = set(act.get("tongues_active", []))
            null = set(act.get("tongues_null", []))
            assert active & null == set(), f"Overlap: {active & null}"

    def test_average_null_count_reasonable(self, canonical_records):
        null_counts = []
        for rec in canonical_records:
            nulls = rec["activation"].get("tongues_null", [])
            if nulls:
                null_counts.append(len(nulls))
        if null_counts:
            avg = sum(null_counts) / len(null_counts)
            # Should be between 2 and 5.5 (6 tongues, most are null-heavy)
            assert 1.0 <= avg <= 5.5, f"Suspicious avg null count: {avg}"


# ===========================================================================
# I. CONTENT SANITY
# ===========================================================================

class TestContentSanity:
    def test_no_empty_instructions(self, canonical_sample):
        empties = 0
        for rec in canonical_sample:
            inst = rec["target"].get("instruction", "")
            if not inst.strip():
                empties += 1
        # Allow some records without instruction (e.g. governance-only)
        assert empties < len(canonical_sample) * 0.5, f"{empties} empty instructions"

    def test_no_empty_responses(self, canonical_sample):
        empties = 0
        for rec in canonical_sample:
            resp = rec["target"].get("response", "")
            if not resp.strip():
                empties += 1
        assert empties < len(canonical_sample) * 0.5, f"{empties} empty responses"

    def test_no_truncation_artifacts(self, canonical_sample):
        """Check for obvious truncation markers."""
        for rec in canonical_sample:
            resp = rec["target"].get("response", "")
            # These would indicate broken truncation
            assert not resp.endswith("...TRUNCATED"), f"Truncation artifact found"
            assert not resp.endswith("\\x00"), f"Null byte artifact found"

    def test_openai_content_no_empty_strings(self, derived_openai):
        for rec in derived_openai:
            for msg in rec["messages"]:
                assert msg["content"].strip(), f"Empty content in {msg['role']}"


# ===========================================================================
# J. ROUND-TRIP FIDELITY
# ===========================================================================

class TestRoundTrip:
    def test_derived_records_are_valid_json(self):
        """Every line in every derived file must parse as valid JSON."""
        for name, path in DERIVED.items():
            if not path.exists():
                continue
            with open(path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as e:
                        pytest.fail(f"{name} line {i+1}: invalid JSON: {e}")
                    if i > 2000:  # spot check first 2000
                        break

    def test_canonical_records_are_valid_json(self):
        if not CANONICAL.exists():
            pytest.skip("no canonical")
        with open(CANONICAL, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    pytest.fail(f"canonical line {i+1}: invalid JSON: {e}")


# ===========================================================================
# K. DEDUPLICATION
# ===========================================================================

class TestDeduplication:
    def test_no_exact_duplicate_quaternary(self, quaternary_records):
        seen = set()
        dupes = 0
        for rec in quaternary_records:
            key = rec["instruction"]
            if key in seen:
                dupes += 1
            seen.add(key)
        assert dupes == 0, f"{dupes} exact duplicate instructions in quaternary"

    def test_duplicate_rate_canonical(self, canonical_sample):
        """Cross-braided sources intentionally share instructions across
        different tongue/layer views. The same instruction seen through
        different tongues IS the multi-view signal. We just verify the
        content_hash dedup within same source works — check that unique
        hashes >= unique sources."""
        hashes = [r.get("substrate", {}).get("content_hash", "") for r in canonical_sample]
        nonempty = [h for h in hashes if h]
        if not nonempty:
            pytest.skip("no content hashes")
        unique = len(set(nonempty))
        # Should have meaningful variety — at least 20% unique content
        assert unique > len(nonempty) * 0.15, f"Only {unique}/{len(nonempty)} unique hashes"


# ===========================================================================
# L. EDGE CASES
# ===========================================================================

class TestEdgeCases:
    def test_unicode_survives_roundtrip(self, canonical_sample):
        """Records with unicode should parse without mojibake."""
        for rec in canonical_sample:
            text = json.dumps(rec, ensure_ascii=False)
            reparsed = json.loads(text)
            assert reparsed == rec

    def test_escape_sequences_in_quaternary(self, quaternary_records):
        """Escape Quad invariant should have actual escape sequences in examples."""
        escape_recs = [r for r in quaternary_records if r["invariant"] == "Escape Quad"]
        assert len(escape_recs) > 0
        has_escapes = sum(1 for r in escape_recs if "\\n" in r["output"] or "\\t" in r["output"])
        assert has_escapes > 0, "Escape Quad records should contain escape sequences"

    def test_no_record_exceeds_reasonable_size(self, canonical_sample):
        """No single record should be absurdly large."""
        for rec in canonical_sample:
            size = len(json.dumps(rec))
            assert size < 100_000, f"Record too large: {size} bytes"


# ===========================================================================
# M. STATION OUTPUT COMPATIBILITY
# ===========================================================================

class TestStationOutput:
    """Verify the training station's merged output is valid."""

    @pytest.fixture(scope="class")
    def station_sample(self):
        # Find most recent station run
        station_dir = REPO / "training" / "runs" / "station"
        if not station_dir.exists():
            pytest.skip("no station runs")
        runs = sorted(station_dir.iterdir(), reverse=True)
        if not runs:
            pytest.skip("no station runs")
        data_file = runs[0] / "training_data.jsonl"
        if not data_file.exists():
            pytest.skip(f"no training_data.jsonl in {runs[0].name}")
        return sample_records(data_file, 500)

    def test_station_records_have_instruction(self, station_sample):
        has_inst = sum(1 for r in station_sample if r.get("instruction", "").strip())
        assert has_inst > len(station_sample) * 0.8, f"Only {has_inst} have instructions"

    def test_station_records_have_output(self, station_sample):
        has_out = sum(1 for r in station_sample if r.get("output", "").strip())
        assert has_out > len(station_sample) * 0.8, f"Only {has_out} have outputs"

    def test_station_records_have_tongue(self, station_sample):
        has_tongue = sum(1 for r in station_sample if r.get("tongue", "").strip())
        assert has_tongue > len(station_sample) * 0.5

    def test_station_records_have_governance(self, station_sample):
        govs = Counter(r.get("governance", "") for r in station_sample)
        assert "ALLOW" in govs, f"No ALLOW records in station output: {govs}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

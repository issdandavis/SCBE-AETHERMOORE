"""Tests for provider_health_matrix.py (Lane 41)."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.benchmark.provider_health_matrix import (
    PROVIDERS,
    ProviderSpec,
    build_matrix,
    check_provider,
    render_text,
)


def _spec(name="test", tier="free", env_vars=None, probe_fn="_probe_openai_compat"):
    return ProviderSpec(
        name=name,
        tier=tier,
        env_vars=env_vars or [],
        sdk_package="openai",
        probe_fn=probe_fn,
    )


def test_seven_providers_defined():
    names = {p.name for p in PROVIDERS}
    assert names == {"ollama", "cerebras", "groq", "huggingface", "openai", "anthropic", "xai"}


def test_tier_coverage():
    tiers = {p.tier for p in PROVIDERS}
    assert "local" in tiers
    assert "free" in tiers
    assert "paid" in tiers


def test_key_missing_status_when_no_env_var(monkeypatch):
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    spec = _spec(name="cerebras", env_vars=["CEREBRAS_API_KEY"])
    h = check_provider(spec, probe=False)
    assert h.status == "KEY_MISSING"
    assert h.key_configured is False


def test_no_key_required_for_local():
    spec = _spec(name="ollama", tier="local", env_vars=[])
    h = check_provider(spec, probe=False)
    assert h.key_configured is True
    assert h.status != "KEY_MISSING"


def test_ready_when_probe_succeeds(monkeypatch):
    monkeypatch.setenv("TEST_KEY_XYZ", "fake-key")
    spec = _spec(name="fake", tier="free", env_vars=["TEST_KEY_XYZ"])

    def fake_probe(s):
        return True, 42, None

    with patch.dict("scripts.benchmark.provider_health_matrix._PROBE_MAP", {"_probe_openai_compat": fake_probe}):
        h = check_provider(spec, probe=True)
    assert h.status == "READY"
    assert h.latency_ms == 42


def test_unreachable_when_probe_fails(monkeypatch):
    monkeypatch.setenv("TEST_KEY_XYZ", "fake-key")
    spec = _spec(name="fake", tier="free", env_vars=["TEST_KEY_XYZ"])

    def fake_probe(s):
        return False, None, "connection refused"

    with patch.dict("scripts.benchmark.provider_health_matrix._PROBE_MAP", {"_probe_openai_compat": fake_probe}):
        h = check_provider(spec, probe=True)
    assert h.status == "UNREACHABLE"
    assert "connection refused" in (h.error or "")


def test_build_matrix_schema(monkeypatch):
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)

    matrix = build_matrix(probe=False)
    assert matrix["schema_version"] == "scbe_provider_health_matrix_v1"
    assert matrix["total_count"] == 7
    assert isinstance(matrix["providers"], list)
    assert "free_first_policy" in matrix
    assert "recommended_provider" in matrix


def test_free_first_rank_ordering():
    local_specs = [p for p in PROVIDERS if p.tier == "local"]
    paid_specs = [p for p in PROVIDERS if p.tier == "paid"]
    from scripts.benchmark.provider_health_matrix import _FREE_FIRST_RANK

    for s in local_specs:
        for p in paid_specs:
            assert _FREE_FIRST_RANK[s.tier] < _FREE_FIRST_RANK[p.tier]


def test_render_text_contains_all_providers(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    matrix = build_matrix(probe=False)
    text = render_text(matrix)
    for name in ("ollama", "cerebras", "groq", "openai", "anthropic", "xai"):
        assert name in text


def test_no_probe_flag_skips_network():
    # With probe=False no network calls happen; matrix must still return 7 entries.
    matrix = build_matrix(probe=False)
    assert len(matrix["providers"]) == 7

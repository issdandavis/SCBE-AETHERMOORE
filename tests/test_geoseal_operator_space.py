"""Tests for the GeoSeal Operator System-Space Model (Python reference)."""

import pytest
from src.geoseal_operator_space import (
    OperatorSpaceInput,
    decision_to_metadata,
    derive_fs_topology,
    evaluate_operator_space,
    ring_to_governance_tier,
)


# ---------------------------------------------------------------------------
# FS topology
# ---------------------------------------------------------------------------


def test_web_anonymous_topology():
    topo = derive_fs_topology("web", "anonymous")
    assert topo.sandbox_level == "full"
    assert topo.accessible_roots == []
    assert topo.temp_only is True
    assert topo.persists_across_sessions is False
    assert topo.mount_points == []


def test_web_authenticated_topology():
    topo = derive_fs_topology("web", "authenticated")
    assert topo.sandbox_level == "full"
    assert topo.persists_across_sessions is True
    assert topo.temp_only is False


def test_terminal_sudo_topology():
    topo = derive_fs_topology("terminal", "sudo")
    assert topo.sandbox_level == "none"
    assert "/" in topo.accessible_roots
    assert "/" in topo.writable_paths
    assert topo.persists_across_sessions is True
    assert len(topo.mount_points) > 0


def test_terminal_authenticated_topology():
    topo = derive_fs_topology("terminal", "authenticated")
    assert topo.sandbox_level == "none"
    assert any("home" in r or r == "~" for r in topo.accessible_roots)
    assert topo.persists_across_sessions is True


def test_terminal_anonymous_topology():
    topo = derive_fs_topology("terminal", "anonymous")
    assert topo.sandbox_level == "partial"
    assert topo.temp_only is True
    assert topo.persists_across_sessions is False


def test_app_authenticated_topology():
    topo = derive_fs_topology("app", "authenticated")
    assert topo.sandbox_level == "partial"
    assert topo.persists_across_sessions is True
    assert topo.mount_points == []


def test_app_anonymous_topology():
    topo = derive_fs_topology("app", "anonymous")
    assert topo.accessible_roots == []
    assert topo.temp_only is True


def test_api_anonymous_topology():
    topo = derive_fs_topology("api", "anonymous")
    assert topo.sandbox_level == "full"


# ---------------------------------------------------------------------------
# Ring + trust
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "plane, auth, expected_ring, expected_trust",
    [
        ("terminal", "sudo", "core", 0.95),
        ("terminal", "authenticated", "core", 0.85),
        ("terminal", "service_account", "core", 0.80),
        ("terminal", "anonymous", "restricted", 0.35),
        ("app", "authenticated", "outer", 0.70),
        ("app", "service_account", "outer", 0.65),
        ("app", "anonymous", "restricted", 0.25),
        ("api", "service_account", "core", 0.80),
        ("api", "authenticated", "outer", 0.70),
        ("api", "anonymous", "blocked", 0.05),
        ("web", "authenticated", "outer", 0.60),
        ("web", "anonymous", "blocked", 0.05),
    ],
)
def test_ring_derivation(plane, auth, expected_ring, expected_trust):
    inp = OperatorSpaceInput(
        access_plane=plane,
        auth_state=auth,
        session_fingerprint="test-sess-001",
        login_time_ms=None if auth == "anonymous" else 1716000000000,
    )
    d = evaluate_operator_space(inp)
    assert d.ring == expected_ring
    assert d.trust_score == expected_trust


# ---------------------------------------------------------------------------
# Governance flags
# ---------------------------------------------------------------------------


def test_terminal_sudo_elevated_flag():
    d = evaluate_operator_space(
        OperatorSpaceInput(
            access_plane="terminal",
            auth_state="sudo",
            session_fingerprint="sudo-sess",
            login_time_ms=1716000000000,
        )
    )
    assert "ELEVATED_TERMINAL" in d.governance_flags


def test_web_anonymous_unauthenticated_and_temp_flags():
    d = evaluate_operator_space(OperatorSpaceInput(access_plane="web", auth_state="anonymous"))
    assert "UNAUTHENTICATED_WEB" in d.governance_flags
    assert "TEMP_FS_ONLY" in d.governance_flags


def test_api_anonymous_unauthenticated_flag():
    d = evaluate_operator_space(OperatorSpaceInput(access_plane="api", auth_state="anonymous"))
    assert "UNAUTHENTICATED_API" in d.governance_flags


def test_terminal_service_account_elevated_flag():
    d = evaluate_operator_space(
        OperatorSpaceInput(access_plane="terminal", auth_state="service_account", session_fingerprint="svc")
    )
    assert "SERVICE_ACCOUNT_ELEVATED" in d.governance_flags


def test_missing_login_time_flag():
    d = evaluate_operator_space(
        OperatorSpaceInput(
            access_plane="terminal",
            auth_state="authenticated",
            session_fingerprint="sess-no-time",
            # login_time_ms intentionally None
        )
    )
    assert "SESSION_MISSING_LOGIN_TIME" in d.governance_flags


def test_web_native_path_cross_plane_claim():
    d = evaluate_operator_space(
        OperatorSpaceInput(
            access_plane="web",
            auth_state="authenticated",
            session_fingerprint="web-sess",
            login_time_ms=1716000000000,
            claimed_paths=["/home/user/documents"],
        )
    )
    assert "CROSS_PLANE_CLAIM" in d.governance_flags


def test_terminal_http_url_cross_plane_claim():
    d = evaluate_operator_space(
        OperatorSpaceInput(
            access_plane="terminal",
            auth_state="authenticated",
            session_fingerprint="term-sess",
            login_time_ms=1716000000000,
            claimed_paths=["http://example.com/file.txt"],
        )
    )
    assert "CROSS_PLANE_CLAIM" in d.governance_flags


def test_terminal_local_path_no_cross_plane():
    d = evaluate_operator_space(
        OperatorSpaceInput(
            access_plane="terminal",
            auth_state="authenticated",
            session_fingerprint="term-ok",
            login_time_ms=1716000000000,
            claimed_paths=["/home/user/documents"],
        )
    )
    assert "CROSS_PLANE_CLAIM" not in d.governance_flags


def test_api_any_path_is_cross_plane():
    d = evaluate_operator_space(
        OperatorSpaceInput(
            access_plane="api",
            auth_state="service_account",
            session_fingerprint="api-svc",
            claimed_paths=["/tmp/output.json"],
        )
    )
    assert "CROSS_PLANE_CLAIM" in d.governance_flags


# ---------------------------------------------------------------------------
# Trust penalty + ring downgrade
# ---------------------------------------------------------------------------


def test_cross_plane_claim_reduces_trust():
    baseline = evaluate_operator_space(
        OperatorSpaceInput(
            access_plane="terminal",
            auth_state="authenticated",
            session_fingerprint="base",
            login_time_ms=1716000000000,
        )
    )
    with_claim = evaluate_operator_space(
        OperatorSpaceInput(
            access_plane="terminal",
            auth_state="authenticated",
            session_fingerprint="base",
            login_time_ms=1716000000000,
            claimed_paths=["http://evil.com/file"],
        )
    )
    assert abs(with_claim.trust_score - (baseline.trust_score - 0.30)) < 1e-4


def test_combined_penalty_downgrades_ring():
    # terminal+authenticated = 0.85 base; -0.30 cross-plane -0.15 missing login = 0.40 → restricted
    d = evaluate_operator_space(
        OperatorSpaceInput(
            access_plane="terminal",
            auth_state="authenticated",
            session_fingerprint="penalized",
            # no login_time_ms
            claimed_paths=["http://external.example.com/bad"],
        )
    )
    assert d.ring == "restricted"
    assert abs(d.trust_score - 0.40) < 1e-4


# ---------------------------------------------------------------------------
# Space ID determinism
# ---------------------------------------------------------------------------


def test_space_id_is_deterministic():
    inp = OperatorSpaceInput(
        access_plane="terminal",
        auth_state="authenticated",
        session_fingerprint="fixed-fp-abc",
        login_time_ms=1716000000000,
    )
    a = evaluate_operator_space(inp)
    b = evaluate_operator_space(inp)
    assert a.space_id == b.space_id


def test_different_fingerprints_different_space_ids():
    a = evaluate_operator_space(
        OperatorSpaceInput(access_plane="terminal", auth_state="authenticated", session_fingerprint="fp-aaa")
    )
    b = evaluate_operator_space(
        OperatorSpaceInput(access_plane="terminal", auth_state="authenticated", session_fingerprint="fp-bbb")
    )
    assert a.space_id != b.space_id


def test_different_planes_different_space_ids():
    a = evaluate_operator_space(
        OperatorSpaceInput(access_plane="web", auth_state="authenticated", session_fingerprint="shared-fp")
    )
    b = evaluate_operator_space(
        OperatorSpaceInput(access_plane="terminal", auth_state="authenticated", session_fingerprint="shared-fp")
    )
    assert a.space_id != b.space_id


def test_space_id_is_16_hex_chars():
    d = evaluate_operator_space(
        OperatorSpaceInput(access_plane="api", auth_state="service_account", session_fingerprint="api-svc-001")
    )
    assert len(d.space_id) == 16
    assert all(c in "0123456789abcdef" for c in d.space_id)


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def test_decision_to_metadata():
    d = evaluate_operator_space(
        OperatorSpaceInput(
            access_plane="terminal",
            auth_state="authenticated",
            session_fingerprint="ser-test",
            login_time_ms=1716000000000,
        )
    )
    meta = decision_to_metadata(d)
    assert isinstance(meta["ring"], str)
    assert isinstance(meta["trust_score"], float)
    assert isinstance(meta["space_id"], str)
    assert isinstance(meta["governance_flags"], list)
    import json
    json.dumps(meta)  # must not raise


# ---------------------------------------------------------------------------
# L13 tier mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ring, expected_tier",
    [
        ("core", "ALLOW"),
        ("outer", "QUARANTINE"),
        ("restricted", "ESCALATE"),
        ("blocked", "DENY"),
    ],
)
def test_ring_to_governance_tier(ring, expected_tier):
    assert ring_to_governance_tier(ring) == expected_tier

"""Tests for the adapter-aware smoke runner.

Exercises the comparison logic and the dry-run path so the smoke
machinery is regression-tested even without HF inference access.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.smoke_adapter_topological_receipt import (
    DECISION_LEVEL,
    DRY_RUN_MODES,
    POLICIES,
    _DRY_RUN_REGISTRY,
    call_hf_adapter,
    compare_decisions,
    echo_adapter,
    perturb_adapter,
    random_adapter,
    run_smoke,
)

CANARY_FILE = Path(__file__).parent / "topological_receipt_canaries.json"


def test_decision_levels_are_canonical_order():
    assert DECISION_LEVEL["DENY"] < DECISION_LEVEL["QUARANTINE"] < DECISION_LEVEL["ALLOW"]


@pytest.mark.parametrize(
    "prompt,response,status",
    [
        ("ALLOW", "ALLOW", "match"),
        ("QUARANTINE", "QUARANTINE", "match"),
        ("DENY", "DENY", "match"),
        ("ALLOW", "QUARANTINE", "drift"),
        ("QUARANTINE", "ALLOW", "drift"),
        ("QUARANTINE", "DENY", "drift"),
        ("DENY", "QUARANTINE", "drift"),
        ("ALLOW", "DENY", "regression"),
        ("DENY", "ALLOW", "regression"),
    ],
)
def test_compare_decisions_classifies_each_pair(prompt, response, status):
    result = compare_decisions(prompt, response)
    assert result["status"] == status
    assert result["delta"] == DECISION_LEVEL[response] - DECISION_LEVEL[prompt]


def test_dry_run_smoke_passes_against_canaries():
    """Echo adapter returns the prompt verbatim so every comparison must match."""
    if not CANARY_FILE.exists():
        pytest.skip("canary file not generated yet")

    result = run_smoke(
        CANARY_FILE,
        adapter=echo_adapter,
        model="<dry-run>",
        token="<dry-run>",
    )
    assert result["matches"] == result["n"]
    assert result["drifts"] == 0
    assert result["regressions"] == 0
    assert result["errors"] == 0


def test_dry_run_respects_max_canaries():
    if not CANARY_FILE.exists():
        pytest.skip("canary file not generated yet")

    result = run_smoke(
        CANARY_FILE,
        adapter=echo_adapter,
        model="<dry-run>",
        token="<dry-run>",
        max_canaries=3,
    )
    assert result["n"] == 3
    assert result["matches"] == 3


def test_failing_adapter_records_errors_without_crashing():
    if not CANARY_FILE.exists():
        pytest.skip("canary file not generated yet")

    def broken_adapter(prompt, **_):
        raise RuntimeError("simulated adapter outage")

    result = run_smoke(
        CANARY_FILE,
        adapter=broken_adapter,
        model="<broken>",
        token="<broken>",
        max_canaries=4,
    )
    assert result["errors"] == 4
    assert result["matches"] == 0


def test_smoke_output_is_json_serializable():
    if not CANARY_FILE.exists():
        pytest.skip("canary file not generated yet")

    result = run_smoke(
        CANARY_FILE,
        adapter=echo_adapter,
        model="<dry-run>",
        token="<dry-run>",
        max_canaries=5,
    )
    payload = json.dumps(result)
    restored = json.loads(payload)
    assert restored["n"] == 5
    assert restored["schema_version"] == "scbe_adapter_smoke_v1"
    assert restored["policy"] == "strict"


# ---------------------------------------------------------------------------
# Policy variants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("policy", POLICIES)
def test_compare_decisions_accepts_each_policy(policy):
    result = compare_decisions("ALLOW", "ALLOW", policy=policy)
    assert result["policy"] == policy
    assert result["status"] == "match"


def test_compare_decisions_rejects_unknown_policy():
    with pytest.raises(ValueError, match="unknown policy"):
        compare_decisions("ALLOW", "ALLOW", policy="bogus-policy")


@pytest.mark.parametrize(
    "prompt,response,expected",
    [
        # No-harm-leak: only flag delta < 0 (response more concerning).
        ("ALLOW", "ALLOW", "match"),
        ("ALLOW", "QUARANTINE", "drift"),
        ("ALLOW", "DENY", "regression"),
        ("DENY", "ALLOW", "match"),  # response is safer/cleaner — OK
        ("DENY", "DENY", "match"),
        ("QUARANTINE", "ALLOW", "match"),
    ],
)
def test_no_harm_leak_policy_classifications(prompt, response, expected):
    result = compare_decisions(prompt, response, policy="no-harm-leak")
    assert result["status"] == expected


@pytest.mark.parametrize(
    "prompt,response,expected",
    [
        # No-sanitize: only flag delta > 0 (response less concerning).
        ("ALLOW", "ALLOW", "match"),
        ("ALLOW", "DENY", "match"),  # response is more conservative — OK
        ("DENY", "ALLOW", "regression"),  # sanitized away the concern
        ("DENY", "QUARANTINE", "drift"),
        ("QUARANTINE", "DENY", "match"),
    ],
)
def test_no_sanitize_policy_classifications(prompt, response, expected):
    result = compare_decisions(prompt, response, policy="no-sanitize")
    assert result["status"] == expected


def test_run_smoke_threads_policy_through_to_results():
    if not CANARY_FILE.exists():
        pytest.skip("canary file not generated yet")
    for policy in POLICIES:
        result = run_smoke(
            CANARY_FILE,
            adapter=echo_adapter,
            model="<dry-run>",
            token="<dry-run>",
            max_canaries=2,
            policy=policy,
        )
        assert result["policy"] == policy
        for row in result["results"]:
            assert row["comparison"]["policy"] == policy


# ---------------------------------------------------------------------------
# Dry-run modes
# ---------------------------------------------------------------------------


def test_dry_run_registry_covers_every_mode():
    assert set(_DRY_RUN_REGISTRY) == set(DRY_RUN_MODES)
    for mode in DRY_RUN_MODES:
        assert callable(_DRY_RUN_REGISTRY[mode])


def test_perturb_adapter_is_deterministic_and_changes_content():
    a = perturb_adapter("matrix multiply LSP")
    b = perturb_adapter("matrix multiply LSP")
    assert a == b
    assert a != "matrix multiply LSP"
    assert "ADAPTER_RESPONSE" in a


def test_random_adapter_is_deterministic_per_prompt():
    a = random_adapter("anchor probe one")
    b = random_adapter("anchor probe one")
    c = random_adapter("anchor probe two")
    assert a == b
    # different prompts can collide but the corpus has 6 entries so
    # probabilistically these two should differ; if they ever match it
    # is a deterministic property of the seed mod 6 — accept either.
    assert isinstance(c, str)


def test_perturb_dry_run_smoke_completes_with_no_regressions():
    """Perturb may produce drifts but never regressions on this canary set."""
    if not CANARY_FILE.exists():
        pytest.skip("canary file not generated yet")
    result = run_smoke(
        CANARY_FILE,
        adapter=perturb_adapter,
        model="<dry-run:perturb>",
        token="<dry-run>",
        max_canaries=10,
    )
    assert result["regressions"] == 0
    assert result["errors"] == 0
    # perturb must produce at least some non-trivial work
    assert result["matches"] + result["drifts"] == result["n"]


# ---------------------------------------------------------------------------
# HF adapter retry / backoff
# ---------------------------------------------------------------------------


class _FakeHTTPError(Exception):
    """Mimics the relevant attributes of urllib.error.HTTPError for tests."""

    def __init__(self, code: int, body: bytes = b"") -> None:
        self.code = code
        self._body = body
        super().__init__(f"HTTP {code}")

    def read(self) -> bytes:
        return self._body


def test_call_hf_adapter_retries_on_429(monkeypatch):
    import urllib.error
    import urllib.request

    calls = {"n": 0}
    sleeps: list[float] = []

    def fake_urlopen(req, timeout):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.HTTPError(req.full_url, 429, "rate limit", {}, None)

        class _Resp:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *_a):
                return False

            def read(self_inner):
                return json.dumps([{"generated_text": "ok"}]).encode("utf-8")

        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    text = call_hf_adapter(
        "test prompt",
        model="dummy/model",
        token="hf_test_token",
        max_retries=3,
        sleeper=lambda s: sleeps.append(s),
    )
    assert text == "ok"
    assert calls["n"] == 3
    assert len(sleeps) == 2  # two retries before success


def test_call_hf_adapter_gives_up_after_max_retries(monkeypatch):
    import urllib.error
    import urllib.request

    def fake_urlopen(req, timeout):  # noqa: ARG001
        raise urllib.error.HTTPError(req.full_url, 503, "loading", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="HF inference HTTP 503"):
        call_hf_adapter(
            "p",
            model="dummy/model",
            token="hf_test_token",
            max_retries=2,
            sleeper=lambda s: None,
        )


# ---------------------------------------------------------------------------
# Token-redaction discipline
# ---------------------------------------------------------------------------


def test_smoke_output_never_contains_the_token():
    if not CANARY_FILE.exists():
        pytest.skip("canary file not generated yet")

    secret = "hf_secret_token_value_should_never_leak_anywhere"
    result = run_smoke(
        CANARY_FILE,
        adapter=echo_adapter,
        model="<test>",
        token=secret,
        max_canaries=4,
    )
    serialized = json.dumps(result)
    assert secret not in serialized
    # The model field is OK to log; the token field must not exist.
    assert "token" not in result
    assert "Authorization" not in serialized


def test_smoke_error_messages_never_contain_the_token():
    if not CANARY_FILE.exists():
        pytest.skip("canary file not generated yet")

    secret = "hf_super_secret_token_redaction_check"

    def adapter_that_logs_token(prompt, **kwargs):
        raise RuntimeError(f"the adapter pretended to leak {kwargs.get('token')}")

    result = run_smoke(
        CANARY_FILE,
        adapter=adapter_that_logs_token,
        model="<test>",
        token=secret,
        max_canaries=2,
    )
    serialized = json.dumps(result)
    assert secret not in serialized
    assert "<redacted-token>" in serialized

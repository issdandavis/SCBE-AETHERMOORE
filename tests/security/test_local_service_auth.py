"""Regression tests for fail-closed local service authentication."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from src.api.local_service_security import comma_separated_env, require_api_key


def test_shared_service_auth_fails_closed_when_key_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_SERVICE_API_KEY", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        require_api_key("TEST_SERVICE_API_KEY", None, "Test service")

    assert exc_info.value.status_code == 503


def test_shared_service_auth_rejects_wrong_key_and_accepts_exact_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_SERVICE_API_KEY", "correct-horse-battery-staple")

    with pytest.raises(HTTPException) as exc_info:
        require_api_key("TEST_SERVICE_API_KEY", "wrong", "Test service")

    assert exc_info.value.status_code == 401
    assert require_api_key("TEST_SERVICE_API_KEY", "correct-horse-battery-staple", "Test service") is None


def test_cors_allowlist_parser_drops_blank_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_ALLOWED_ORIGINS", " https://one.example, ,https://two.example ")

    assert comma_separated_env("TEST_ALLOWED_ORIGINS") == ["https://one.example", "https://two.example"]


def test_browser_api_auth_uses_fail_closed_service_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents.browser_api import _check_auth

    monkeypatch.delenv("SCBE_BROWSER_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        _check_auth(None)
    assert exc_info.value.status_code == 503

    monkeypatch.setenv("SCBE_BROWSER_API_KEY", "browser-secret")
    _check_auth("browser-secret")


def test_geoseal_runtime_auth_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.api.geoseal_service import verify_api_key

    for name in ("SCBE_GEOSEAL_API_KEY", "SCBE_API_KEY", "SCBE_API_KEYS", "SCBE_ALLOW_DEMO_KEYS"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_api_key(None))

    assert exc_info.value.status_code == 503


def test_geoseal_runtime_auth_accepts_dedicated_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.api.geoseal_service import verify_api_key

    monkeypatch.delenv("SCBE_API_KEY", raising=False)
    monkeypatch.delenv("SCBE_API_KEYS", raising=False)
    monkeypatch.delenv("SCBE_ALLOW_DEMO_KEYS", raising=False)
    monkeypatch.setenv("SCBE_GEOSEAL_API_KEY", "geoseal-secret")

    assert asyncio.run(verify_api_key("geoseal-secret")) == "geoseal_operator"

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_api_key("demo_key_12345"))
    assert exc_info.value.status_code == 401

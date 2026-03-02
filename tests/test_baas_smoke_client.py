#!/usr/bin/env python3
"""
Unit tests for scripts/baas_smoke_client.py helpers.
These tests do not require a live BaaS endpoint.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_smoke_path = PROJECT_ROOT / "scripts" / "baas_smoke_client.py"
_smoke_spec = importlib.util.spec_from_file_location("baas_smoke_client", _smoke_path)
if _smoke_spec is None or _smoke_spec.loader is None:
    raise ImportError("Failed to load baas_smoke_client module from scripts/baas_smoke_client.py")

smoke = importlib.util.module_from_spec(_smoke_spec)
_smoke_spec.loader.exec_module(smoke)  # type: ignore[union-attr]


def test_parse_session_id_supports_multiple_shapes() -> None:
    assert smoke._parse_session_id({"session_id": "sid-1"}) == "sid-1"
    assert smoke._parse_session_id({"sessionId": "sid-2"}) == "sid-2"
    assert smoke._parse_session_id({"id": "sid-3"}) == "sid-3"
    assert smoke._parse_session_id({"data": {"session_id": "sid-4"}}) == "sid-4"
    assert smoke._parse_session_id({"data": {"id": "sid-5"}}) == "sid-5"
    assert smoke._parse_session_id({"foo": "bar"}) is None


def test_api_url_normalizes() -> None:
    assert smoke._api_url("http://127.0.0.1:8600", "v1/sessions") == "http://127.0.0.1:8600/v1/sessions"
    assert smoke._api_url("http://127.0.0.1:8600/", "/v1/sessions") == "http://127.0.0.1:8600/v1/sessions"

from __future__ import annotations

import asyncio

import pytest

from fastapi import HTTPException

import src.api.main as api_main


def test_src_verify_api_key_accepts_new_header(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "VALID_API_KEYS", {"new-key": "tenant_new"})
    assert asyncio.run(api_main.verify_api_key(api_key="new-key", api_key_legacy=None)) == "tenant_new"


def test_src_verify_api_key_accepts_legacy_header(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "VALID_API_KEYS", {"legacy-key": "tenant_legacy"})
    assert asyncio.run(api_main.verify_api_key(api_key=None, api_key_legacy="legacy-key")) == "tenant_legacy"


def test_src_verify_api_key_rejects_missing_headers(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "VALID_API_KEYS", {"new-key": "tenant_new"})
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(api_main.verify_api_key(api_key=None, api_key_legacy=None))
    assert exc_info.value.status_code == 401


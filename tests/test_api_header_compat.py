import asyncio
import sys
import types

import pytest

# The api.main module transitively imports cryptography via the GitHub App
# routes.  When the cffi backend is missing (common in lightweight CI images)
# the Rust binding panics (uncatchable).  Guard by checking for _cffi_backend
# before any cryptography import.
pytest.importorskip("_cffi_backend", reason="cffi backend unavailable — cryptography will panic")

from api import main as api_main  # noqa: E402
from fastapi import HTTPException  # noqa: E402

fake_mangum = types.ModuleType("mangum")


class _FakeMangum:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, event, context):
        return {"statusCode": 200, "body": "{}"}


fake_mangum.Mangum = _FakeMangum
sys.modules.setdefault("mangum", fake_mangum)

from aws import lambda_handler as lambda_module


def test_verify_api_key_accepts_new_header(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "VALID_API_KEYS", {"new-key": "tenant_new"})
    assert asyncio.run(api_main.verify_api_key(api_key="new-key", api_key_legacy=None)) == "tenant_new"


def test_verify_api_key_accepts_legacy_header(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "VALID_API_KEYS", {"legacy-key": "tenant_legacy"})
    assert asyncio.run(api_main.verify_api_key(api_key=None, api_key_legacy="legacy-key")) == "tenant_legacy"


def test_verify_api_key_prefers_new_header_when_both_present(monkeypatch) -> None:
    monkeypatch.setattr(
        api_main,
        "VALID_API_KEYS",
        {"new-key": "tenant_new", "legacy-key": "tenant_legacy"},
    )
    assert asyncio.run(api_main.verify_api_key(api_key="new-key", api_key_legacy="legacy-key")) == "tenant_new"


def test_verify_api_key_rejects_missing_headers(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "VALID_API_KEYS", {"new-key": "tenant_new"})
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(api_main.verify_api_key(api_key=None, api_key_legacy=None))
    assert exc_info.value.status_code == 401


def test_lambda_extract_api_key_accepts_new_and_legacy_headers() -> None:
    assert lambda_module._extract_api_key({"SCBE_api_key": "new-key"}) == "new-key"
    assert lambda_module._extract_api_key({"scbe_api_key": "new-key-lower"}) == "new-key-lower"
    assert lambda_module._extract_api_key({"X-API-Key": "legacy-key"}) == "legacy-key"
    assert lambda_module._extract_api_key({"x-api-key": "legacy-key-lower"}) == "legacy-key-lower"


def test_lambda_extract_api_key_prefers_new_header() -> None:
    headers = {"SCBE_api_key": "new-key", "X-API-Key": "legacy-key"}
    assert lambda_module._extract_api_key(headers) == "new-key"

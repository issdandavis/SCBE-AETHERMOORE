from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from src.api import main as api_main
from src.crypto.rwp_v3 import RWPEnvelope, RWPv3Protocol
from src.storage import FileSystemSealedBlobStorage


def _allow_result(**_kwargs: object) -> dict[str, object]:
    return {
        "decision": "ALLOW",
        "risk_base": 0.1,
        "risk_prime": 0.1,
        "d_star": 0.2,
        "H": 1.0,
        "coherence": {"score": 1.0},
        "mmx": None,
    }


def _seal_request() -> api_main.SealRequest:
    return api_main.SealRequest(
        plaintext="principal-a secret",
        agent="shared-agent",
        topic="shared-topic",
        position=[1, 2, 3, 5, 8, 13],
    )


def test_sealed_blob_is_owner_scoped_and_requires_server_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage = FileSystemSealedBlobStorage(str(tmp_path / "sealed"))
    monkeypatch.setattr(api_main, "storage_backend", storage)
    monkeypatch.setattr(api_main, "scbe_14layer_pipeline", _allow_result)
    monkeypatch.setenv("SCBE_SEALED_BLOB_MASTER_KEY", "unit-test-master-key-with-at-least-32-bytes")

    request = _seal_request()
    asyncio.run(api_main.seal_memory(request, user="principal-a"))

    with pytest.raises(HTTPException) as cross_owner:
        asyncio.run(
            api_main.retrieve_memory(
                api_main.RetrieveRequest(position=request.position, agent=request.agent, context="internal"),
                user="principal-b",
            )
        )
    assert cross_owner.value.status_code == 404

    result = asyncio.run(
        api_main.retrieve_memory(
            api_main.RetrieveRequest(position=request.position, agent=request.agent, context="internal"),
            user="principal-a",
        )
    )
    assert result["data"]["plaintext"] == request.plaintext

    persisted_path = next((tmp_path / "sealed").rglob("*.json"))
    persisted = json.loads(persisted_path.read_text(encoding="utf-8"))
    envelope = RWPEnvelope.from_dict(json.loads(bytes.fromhex(persisted["sealed_blob"]).decode("utf-8")))

    with pytest.raises(ValueError):
        RWPv3Protocol().decrypt(password=f"{request.agent}:{request.topic}".encode(), envelope=envelope)


def test_second_principal_cannot_overwrite_first_principal_blob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = FileSystemSealedBlobStorage(str(tmp_path / "sealed"))
    monkeypatch.setattr(api_main, "storage_backend", storage)
    monkeypatch.setattr(api_main, "scbe_14layer_pipeline", _allow_result)
    monkeypatch.setenv("SCBE_SEALED_BLOB_MASTER_KEY", "unit-test-master-key-with-at-least-32-bytes")

    request_a = _seal_request()
    request_b = request_a.model_copy(update={"plaintext": "principal-b secret"})
    asyncio.run(api_main.seal_memory(request_a, user="principal-a"))
    asyncio.run(api_main.seal_memory(request_b, user="principal-b"))

    result_a = asyncio.run(
        api_main.retrieve_memory(
            api_main.RetrieveRequest(position=request_a.position, agent=request_a.agent, context="internal"),
            user="principal-a",
        )
    )
    result_b = asyncio.run(
        api_main.retrieve_memory(
            api_main.RetrieveRequest(position=request_b.position, agent=request_b.agent, context="internal"),
            user="principal-b",
        )
    )

    assert result_a["data"]["plaintext"] == "principal-a secret"
    assert result_b["data"]["plaintext"] == "principal-b secret"


def test_seal_memory_fails_closed_without_master_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_main, "scbe_14layer_pipeline", _allow_result)
    monkeypatch.delenv("SCBE_SEALED_BLOB_MASTER_KEY", raising=False)

    with pytest.raises(HTTPException) as missing_key:
        asyncio.run(api_main.seal_memory(_seal_request(), user="principal-a"))

    assert missing_key.value.status_code == 503
    assert missing_key.value.detail == "Sealed storage encryption is not configured"


@pytest.mark.parametrize("unsafe_value", [True, "../escape", 2**64])
def test_position_model_rejects_unsafe_coordinates(unsafe_value: object) -> None:
    with pytest.raises(ValueError):
        api_main.SealRequest(
            plaintext="secret",
            agent="agent",
            topic="topic",
            position=[1, 2, 3, 4, 5, unsafe_value],
        )

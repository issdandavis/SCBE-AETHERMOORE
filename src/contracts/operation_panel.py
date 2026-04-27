"""Operation-panel resolver for GeoSeal runtime cards."""

from __future__ import annotations

import hashlib
from typing import Any

from src.contracts.runtime_contract import inspect_runtime_packet


def resolve_source_to_operation_panel(
    content: str,
    *,
    language: str = "python",
    source_name: str = "<memory>",
    include_extended: bool = False,
) -> dict[str, Any]:
    runtime_packet = inspect_runtime_packet(
        {
            "language": language,
            "content": content,
            "source_name": source_name,
        }
    )
    signature_seed = "|".join(
        [
            runtime_packet["source_sha256"],
            runtime_packet["route_tongue"],
            runtime_packet["command_key"],
            str(bool(include_extended)),
        ]
    )
    return {
        "schema_version": "geoseal-operation-panel-v1",
        "runtime_packet": runtime_packet,
        "route_tongue": runtime_packet["route_tongue"],
        "operator_signature": hashlib.sha256(signature_seed.encode("utf-8")).hexdigest(),
        "include_extended": bool(include_extended),
    }


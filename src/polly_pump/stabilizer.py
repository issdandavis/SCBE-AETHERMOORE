"""Compose a structured pre-state block for Polly inference.

The stabilizer turns a sensed packet plus retrieved bundles into one deterministic
context block. The output is intentionally plain text so it can be injected into
any later model lane without additional formatting machinery.
"""

from __future__ import annotations

from typing import Iterable

from .packet import PumpPacket
from .retriever import RetrievedBundle


def stabilize(packet: PumpPacket, bundles: Iterable[RetrievedBundle]) -> str:
    """Build a deterministic pre-state context block.

    The result is concise but structured enough to expose the sensed state before
    response generation. This is the runtime "pump" output.
    """

    ranked = list(bundles)
    lines = [
        "[POLLY_PUMP_PRESTATE]",
        f"dominant_tongue={packet.dominant_tongue}",
        f"null_pattern={packet.null_pattern}",
        f"canon={packet.canon}",
        f"emotion={packet.emotion}",
        f"governance={packet.governance}",
        f"source_roots={'; '.join(packet.source_roots)}",
        "[BUNDLES]",
    ]

    if not ranked:
        lines.append("none")
        return "\n".join(lines)

    for index, bundle in enumerate(ranked, start=1):
        preview = " ".join(bundle.text.split())[:220]
        lines.extend(
            [
                f"{index}. id={bundle.bundle_id}",
                f"score={bundle.score:.4f}",
                f"canon={bundle.canon}",
                f"emotion={bundle.emotion}",
                f"governance={bundle.governance}",
                f"null_pattern={bundle.null_pattern}",
                f"source_root={bundle.source_root}",
                f"text={preview}",
            ]
        )

    return "\n".join(lines)

"""Semantic abacus receipts for tokenizer payloads and GeoSeal authority.

The systems use is accounting: a byte-tokenized payload is dressed into the
GeoSeed bit field, collapsed into prime-basis chunk rows, and sealed with a
GeoSeal legitimacy decision. It is a deterministic receipt surface for agents:
"what did this payload cost, which semantic chunks were active, and is the
declared tool/command allowed?"
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Sequence

from src.geoseed.bit_dressing import (
    DressedBitComposition,
    bits_from_bytes,
    build_prime_abacus_layer,
    compose_dressed_bits,
    dress_bytes,
)

if TYPE_CHECKING:
    from src.crypto.geoseal_legitimacy import CoarseLocation

SCHEMA_VERSION = "geoseed_semantic_abacus_receipt_v1"


@dataclass(frozen=True)
class ByteToken:
    """One no-OOV tokenizer byte in the semantic abacus ledger."""

    index: int
    value: int
    hex: str
    bits: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticAbacusReceipt:
    """Deterministic bridge from tokenizer bytes to abacus rows and GeoSeal."""

    schema_version: str
    payload_label: str
    payload_sha256: str
    byte_count: int
    bit_count: int
    bit_order: Literal["msb", "lsb"]
    byte_tokens: tuple[ByteToken, ...]
    composition: DressedBitComposition
    abacus_layer: dict[str, object]
    geoseal: dict[str, Any]

    @property
    def decision(self) -> str:
        return str(self.geoseal["decision"]["decision"])

    @property
    def allowed(self) -> bool:
        return bool(self.geoseal["decision"]["allowed_cli"])

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "payload_label": self.payload_label,
            "payload_sha256": self.payload_sha256,
            "byte_count": self.byte_count,
            "bit_count": self.bit_count,
            "bit_order": self.bit_order,
            "byte_tokens": [token.to_dict() for token in self.byte_tokens],
            "composition": self.composition.to_dict(),
            "abacus_layer": self.abacus_layer,
            "geoseal": self.geoseal,
            "decision": self.decision,
            "allowed": self.allowed,
        }


def build_semantic_abacus_receipt(
    payload: bytes,
    *,
    payload_label: str = "inline",
    bit_order: Literal["msb", "lsb"] = "msb",
    goal: str = "account tokenizer payload",
    expected_tool: str = "metrics.read",
    command: str | None = None,
    workspace: Path | None = None,
    origin: Literal["user", "agent", "workflow"] = "agent",
    privacy: Literal["local_only", "hosted"] = "local_only",
    network_state: Literal["offline", "local", "online", "unknown"] = "local",
    location: "CoarseLocation | None" = None,
) -> SemanticAbacusReceipt:
    """Build a semantic abacus receipt for bytes without executing anything."""
    if not payload:
        raise ValueError("payload must not be empty")

    CoarseLocationClass, run_trial = _load_geoseal_legitimacy()
    raw_bits = bits_from_bytes(payload, bit_order=bit_order)
    dressed = dress_bytes(payload, bit_order=bit_order)
    composition = compose_dressed_bits(dressed)
    token_rows = _byte_tokens(payload, raw_bits)
    abacus_layer = build_prime_abacus_layer(
        dressed,
        layer_id="geoseed-tokenizer-prime",
        name="GeoSeed Tokenizer Prime Chunks",
    )
    geoseal = run_trial(
        goal=goal,
        expected_tool=expected_tool,
        origin=origin,
        expected_state=(
            f"bytes={len(payload)} bits={len(raw_bits)} "
            f"prime_total={composition.prime_weighted_total}"
        ),
        privacy=privacy,
        command=command,
        workspace=workspace,
        location=location
        or CoarseLocationClass(
            source="user_confirmed",
            label="local semantic abacus accounting",
            confidence=0.95,
        ),
        network_state=network_state,
    )
    return SemanticAbacusReceipt(
        schema_version=SCHEMA_VERSION,
        payload_label=payload_label,
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        bit_count=len(raw_bits),
        bit_order=bit_order,
        byte_tokens=token_rows,
        composition=composition,
        abacus_layer=abacus_layer,
        geoseal=geoseal,
    )


def build_semantic_abacus_for_text(
    text: str,
    *,
    encoding: str = "utf-8",
    **kwargs: Any,
) -> SemanticAbacusReceipt:
    """Text helper using UTF-8 byte tokenization."""
    return build_semantic_abacus_receipt(text.encode(encoding), **kwargs)


def _load_geoseal_legitimacy() -> tuple[type["CoarseLocation"], Any]:
    """Import GeoSeal while keeping third-party startup chatter off stdout."""
    with contextlib.redirect_stdout(io.StringIO()):
        from src.crypto.geoseal_legitimacy import CoarseLocation, run_legitimacy_trial

    return CoarseLocation, run_legitimacy_trial


def _byte_tokens(payload: bytes, raw_bits: Sequence[int]) -> tuple[ByteToken, ...]:
    tokens = []
    for index, value in enumerate(payload):
        start = index * 8
        bits = "".join(str(bit) for bit in raw_bits[start : start + 8])
        tokens.append(
            ByteToken(index=index, value=value, hex=f"{value:02x}", bits=bits)
        )
    return tuple(tokens)


def _parse_hex(value: str) -> bytes:
    cleaned = "".join(value.split())
    if not cleaned:
        raise ValueError("hex payload must not be empty")
    if len(cleaned) % 2:
        raise ValueError("hex payload must contain whole bytes")
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        raise ValueError("hex payload contains non-hex characters") from exc


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a GeoSeed semantic abacus receipt from tokenizer bytes."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="UTF-8 text payload to account")
    source.add_argument("--hex", dest="hex_payload", help="hex byte payload to account")
    parser.add_argument(
        "--label", default="inline", help="payload label for the receipt"
    )
    parser.add_argument("--bit-order", choices=("msb", "lsb"), default="msb")
    parser.add_argument("--goal", default="account tokenizer payload")
    parser.add_argument(
        "--tool", default="metrics.read", help="declared GeoSeal expected tool"
    )
    parser.add_argument(
        "--command", help="optional command shape to scan; never executed"
    )
    parser.add_argument("--workspace", type=Path, help="workspace scope for GeoSeal")
    parser.add_argument("--json", action="store_true", help="emit full JSON receipt")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        payload = (
            args.text.encode("utf-8")
            if args.text is not None
            else _parse_hex(str(args.hex_payload))
        )
        receipt = build_semantic_abacus_receipt(
            payload,
            payload_label=args.label,
            bit_order=args.bit_order,
            goal=args.goal,
            expected_tool=args.tool,
            command=args.command,
            workspace=args.workspace,
        )
    except ValueError as exc:
        parser.error(str(exc))
    payload_dict = receipt.to_dict()
    if args.json:
        print(json.dumps(payload_dict, indent=2, sort_keys=True))
    else:
        print(
            json.dumps(
                {
                    "schema_version": receipt.schema_version,
                    "payload_label": receipt.payload_label,
                    "byte_count": receipt.byte_count,
                    "bit_count": receipt.bit_count,
                    "prime_weighted_total": receipt.composition.prime_weighted_total,
                    "decision": receipt.decision,
                    "allowed": receipt.allowed,
                    "payload_sha256": receipt.payload_sha256,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0 if receipt.allowed else 3


__all__ = [
    "ByteToken",
    "SCHEMA_VERSION",
    "SemanticAbacusReceipt",
    "build_semantic_abacus_for_text",
    "build_semantic_abacus_receipt",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())

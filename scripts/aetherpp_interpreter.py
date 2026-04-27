"""Aether++ sentence front-end for GeoSeal route payloads.

This is intentionally a thin compiler layer:
- parses simple English-like sentences ending in periods
- uses the canonical SacredTongueTokenizer for byte round-trip proofs
- emits a route payload that can be adapted to /runtime/run-route

It does not implement a real ContinuousIntentField. Until that exists as a
repo primitive, Aether++ records intent gates as deterministic metadata only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER, TONGUES
from src.geoseal_cli import compute_seal, phi_wall_cost, phi_wall_tier, phi_trust_score


TONGUE_LANGUAGE = {
    "KO": "python",
    "AV": "typescript",
    "RU": "rust",
    "CA": "c",
    "UM": "julia",
    "DR": "haskell",
}


@dataclass
class IntentGate:
    """Metadata-only gate until the real continuous-intent field is promoted."""

    name: str
    status: str = "metadata_only"
    constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "constraints": self.constraints,
        }


class AetherPPInterpreter:
    """Compile Aether++ sentences into a governed route payload."""

    def __init__(self) -> None:
        self.manifold_count = 0
        self.intent_gate = IntentGate(
            name="continuous_intent_field",
            constraints=[
                "metadata_only_not_authorization",
                "requires_runtime_gate_before_execution",
            ],
        )

    def interpret(self, program: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": "aetherpp_route_payload_v1",
            "language": "aether++",
            "source_sha256": hashlib.sha256(program.encode("utf-8")).hexdigest(),
            "intent_gate": self.intent_gate.to_dict(),
            "manifolds": [],
            "propagations": [],
            "token_streams": [],
            "route_request": None,
            "seals": [],
            "warnings": [],
        }

        for sentence in _split_sentences(program):
            self._interpret_sentence(sentence, payload)

        if payload["route_request"] is None and payload["token_streams"]:
            latest = payload["token_streams"][-1]
            payload["route_request"] = _route_request_from_stream(latest)

        return payload

    def _interpret_sentence(self, sentence: str, payload: dict[str, Any]) -> None:
        lower = sentence.lower()

        if "create spacaita" in lower or "system with" in lower:
            count = _first_int(sentence, default=4)
            self.manifold_count = count
            payload["manifolds"].append(
                {
                    "event": "create",
                    "count": count,
                    "note": "spacaita is represented as route metadata until a runtime primitive exists",
                }
            )
            return

        if re.search(r"\bfold\b", lower):
            payload["manifolds"].append(_parse_fold(sentence))
            return

        if "cross propagate" in lower or "propagate" in lower:
            payload["propagations"].append(_parse_propagation(sentence))
            return

        if "encode" in lower or "seal" in lower:
            stream = _parse_encode(sentence)
            payload["token_streams"].append(stream)
            payload["seals"].append(stream["seal"])
            payload["route_request"] = _route_request_from_stream(stream)
            return

        if "run route" in lower or lower == "execute":
            payload["run_requested"] = True
            return

        payload["warnings"].append({"sentence": sentence, "warning": "unrecognized_sentence"})


def _split_sentences(program: str) -> list[str]:
    # Split on sentence periods, but do not split decimal numbers such as 0.95.
    return [part.strip() for part in re.split(r"\.(?=\s+[A-Za-z]|$)\s*", program) if part.strip()]


def _first_int(text: str, default: int) -> int:
    match = re.search(r"\b(\d+)\b", text)
    return int(match.group(1)) if match else default


def _first_float(text: str, default: float) -> float:
    match = re.search(r"\b(\d+(?:\.\d+)?)\b", text)
    return float(match.group(1)) if match else default


def _parse_tongue(text: str, default: str = "KO") -> str:
    match = re.search(r"\btongue\s+(KO|AV|RU|CA|UM|DR)\b", text, flags=re.IGNORECASE)
    tongue = match.group(1).upper() if match else default
    if tongue.lower() not in TONGUES:
        raise ValueError(f"unknown tongue: {tongue}")
    return tongue


def _parse_quoted_payload(text: str) -> str:
    match = re.search(r"[\"'](.*?)[\"']", text, flags=re.DOTALL)
    return match.group(1) if match else text


def _parse_fold(sentence: str) -> dict[str, Any]:
    manifold_match = re.search(r"\bmanifold\s+(\d+)\b", sentence, flags=re.IGNORECASE)
    goal_match = re.search(r"\bgoal\s+(\d+(?:\.\d+)?)\b", sentence, flags=re.IGNORECASE)
    op_value = _first_float(sentence, default=1.0)
    tongue = _parse_tongue(sentence)
    cost = phi_wall_cost(min(max(op_value, 0.0), 1.0), tongue)
    return {
        "event": "fold",
        "manifold": int(manifold_match.group(1)) if manifold_match else 0,
        "operator": op_value,
        "goal": float(goal_match.group(1)) if goal_match else None,
        "tongue": tongue,
        "phi_cost": cost,
        "tier": phi_wall_tier(cost),
        "trust_score": phi_trust_score(cost),
    }


def _parse_propagation(sentence: str) -> dict[str, Any]:
    ints = [int(item) for item in re.findall(r"\b(\d+)\b", sentence)]
    return {
        "event": "cross_propagate",
        "source": ints[0] if ints else 0,
        "target": ints[1] if len(ints) > 1 else 1,
    }


def _parse_encode(sentence: str) -> dict[str, Any]:
    tongue = _parse_tongue(sentence)
    text = _parse_quoted_payload(sentence)
    transport_tongue = tongue.lower()
    raw = text.encode("utf-8")
    tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(transport_tongue, raw)
    decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(transport_tongue, tokens)
    if decoded != raw:
        raise ValueError("SacredTongueTokenizer round-trip failed")

    token_text = " ".join(tokens)
    token_sha256 = hashlib.sha256(token_text.encode("utf-8")).hexdigest()
    source_sha256 = hashlib.sha256(raw).hexdigest()
    seal = compute_seal(
        "aetherpp_encode",
        tongue,
        token_text,
        payload=source_sha256,
        phi_cost=0.0,
        tier="ALLOW",
    )
    return {
        "event": "encode",
        "tongue": tongue,
        "language": TONGUE_LANGUAGE[tongue],
        "content": text,
        "source_sha256": source_sha256,
        "tokens": tokens,
        "token_count": len(tokens),
        "token_sha256": token_sha256,
        "round_trip": True,
        "seal": seal,
    }


def _route_request_from_stream(stream: dict[str, Any]) -> dict[str, Any]:
    return {
        "language": stream["language"],
        "content": stream["content"],
        "source_name": "aetherpp://inline",
        "tongue": stream["tongue"],
        "branch_width": 1,
        "include_extended": False,
        "deck_size": 10,
        "timeout": 10.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile Aether++ sentences into a GeoSeal route payload")
    parser.add_argument("program", nargs="?", default=None, help="Program text. Defaults to stdin.")
    parser.add_argument("--program-file", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=Path("execution_shell.json"))
    args = parser.parse_args()

    if args.program_file:
        program = args.program_file.read_text(encoding="utf-8")
    elif args.program is not None:
        program = args.program
    else:
        import sys

        program = sys.stdin.read()

    payload = AetherPPInterpreter().interpret(program)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "schema_version": payload["schema_version"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

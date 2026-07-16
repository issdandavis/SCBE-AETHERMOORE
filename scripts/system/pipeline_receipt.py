#!/usr/bin/env python3
"""Emit one receipt across SCBE binary, hex, conlang, token, and workflow lanes."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _json_safe(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return _json_safe(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, bytes):
        return {"hex": value.hex(), "utf8_lossy": value.decode("utf-8", errors="replace")}
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atoms(text: str, limit: int = 24) -> list[str]:
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|0x[0-9A-Fa-f]+|\d+|==|!=|<=|>=|[^\s]", text)
    return tokens[:limit]


def _preview_text(data: bytes, limit: int = 240) -> str:
    text = data.decode("utf-8", errors="replace")
    return text if len(text) <= limit else text[:limit] + "...[truncated]"


def load_payload(args: argparse.Namespace) -> tuple[bytes, dict[str, Any]]:
    if args.file:
        path = Path(args.file)
        data = path.read_bytes()
        return data, {"source": "file", "path": str(path), "bytes": len(data)}
    if args.content is not None:
        data = args.content.encode("utf-8")
        return data, {"source": "argument", "bytes": len(data)}
    if not sys.stdin.isatty():
        text = sys.stdin.read()
        data = text.encode("utf-8")
        return data, {"source": "stdin", "bytes": len(data)}
    data = b"compile"
    return data, {"source": "default", "bytes": len(data)}


def build_bit_spine_receipt(data: bytes, max_bytes: int) -> dict[str, Any]:
    from python.scbe.bit_spine import BitSpine, binary_increment_machine

    sample = data[:max_bytes]
    spine = BitSpine(sample)
    bits = spine.bits()
    trits = spine.trits()
    receipt: dict[str, Any] = {
        "schema": "scbe_pipeline_bit_spine_v1",
        "sample_bytes": len(sample),
        "full_bytes_seen": len(data),
        "sha256": _sha256(data),
        "sample_sha256": _sha256(sample),
        "hex": spine.hex(),
        "binary_prefix": bits[:128],
        "binary_bit_length": len(bits),
        "trit_prefix": trits[:64],
        "trit_length": len(trits),
        "roundtrip": {
            "hex": BitSpine.from_hex(spine.hex()).data == sample,
            "binary": BitSpine.from_bits(bits).data == sample,
            "trits": BitSpine.from_trits(trits).data == sample,
        },
    }
    try:
        machine_input = bits[-16:] if bits else "0"
        receipt["binary_turing_increment_probe"] = binary_increment_machine().run(machine_input, max_steps=4096)
    except Exception as exc:  # pragma: no cover - receipt should survive partial lanes
        receipt["binary_turing_increment_probe"] = {"ok": False, "error": str(exc)}
    return receipt


def build_sacred_tongue_receipt(data: bytes, tongue: str, max_bytes: int) -> dict[str, Any]:
    import scbe

    selected = tongue.upper()
    sample = data[:max_bytes]
    encoded = scbe.encode_bytes(selected, sample)
    decoded = scbe.decode_tokens(selected, encoded)
    return {
        "schema": "scbe_pipeline_sacred_tongue_cli_v1",
        "surface": "scbe.py",
        "tongue": selected,
        "sample_bytes": len(sample),
        "tokens": encoded,
        "token_count": len(encoded.split()) if encoded else 0,
        "roundtrip_ok": decoded == sample,
        "domain": getattr(scbe, "TONGUE_DOMAINS", {}).get(selected),
        "name": getattr(scbe, "TONGUE_NAMES", {}).get(selected),
    }


def build_cube_receipt(text: str, atom: str | None = None) -> dict[str, Any]:
    from python.scbe.cube_token import CubeToken
    from python.scbe.atomic_tokenization import TONGUES

    selected_atom = atom or (_atoms(text, 1)[0] if _atoms(text, 1) else text[:32] or "empty")
    cube = CubeToken(selected_atom)
    faces = {}
    for tongue in TONGUES:
        face = cube.face(tongue)
        faces[tongue] = {
            "tokens": face,
            "roundtrip_ok": CubeToken.from_face(tongue, face).token == selected_atom,
        }
    return {
        "schema": "scbe_pipeline_cube_token_v1",
        "surface": "python.scbe.cube_token.CubeToken",
        "atom": selected_atom,
        "all_faces_roundtrip": cube.is_bijective(),
        "faces": faces,
    }


def build_atomic_receipt(text: str, language: str, context_class: str | None) -> dict[str, Any]:
    from python.scbe.atomic_tokenization import map_token_to_atomic_state
    from python.scbe.tongue_code_lanes import classify_code_lane_alignment
    from src.tokenizer.atomic_workflow_units import compose_workflow

    tokens = _atoms(text, 16)
    states = []
    rows = []
    for token in tokens:
        state = map_token_to_atomic_state(token, language=language, context_class=context_class)
        states.append(state)
        rows.append({"token": token, "semantic": state.semantic_class, "state": _json_safe(state)})
    alignment = classify_code_lane_alignment(states, context_class=context_class)
    workflow = compose_workflow(tokens[:8]) if tokens else compose_workflow(["empty"])
    return {
        "schema": "scbe_pipeline_atomic_workflow_v1",
        "language": language,
        "context_class": context_class,
        "tokens": rows,
        "gradient": build_atomic_gradient(states),
        "code_lane_alignment": _json_safe(alignment),
        "workflow": _json_safe(workflow),
    }


def build_atomic_gradient(states: list[Any]) -> dict[str, Any]:
    """Cell-to-cell gradient over atomic token states.

    This is intentionally cheap and local. It lets a token sequence be treated
    like a flow field: exact matches pass cleanly, near matches become slide
    candidates, and hard semantic jumps become boundaries.
    """
    edges = []
    for index, (left, right) in enumerate(zip(states, states[1:])):
        left_tau = left.tau.as_dict()
        right_tau = right.tau.as_dict()
        trit_distance = sum(abs(int(left_tau[k]) - int(right_tau[k])) for k in left_tau)
        semantic_same = left.semantic_class == right.semantic_class
        band_delta = abs(int(left.band_flag) - int(right.band_flag))
        resilience_delta = abs(float(left.resilience) - float(right.resilience))
        adaptivity_delta = abs(float(left.adaptivity) - float(right.adaptivity))
        trust_delta = abs(float(left.trust_baseline) - float(right.trust_baseline))
        compatibility = 1.0
        compatibility -= min(0.45, trit_distance / 12.0)
        compatibility -= 0.18 if not semantic_same else 0.0
        compatibility -= min(0.14, band_delta / 32.0)
        compatibility -= min(0.10, resilience_delta)
        compatibility -= min(0.10, adaptivity_delta)
        compatibility -= min(0.08, trust_delta)
        compatibility = max(0.0, min(1.0, compatibility))
        if compatibility >= 0.78:
            flow = "lock"
        elif compatibility >= 0.52:
            flow = "slide"
        else:
            flow = "boundary"
        edges.append(
            {
                "index": index,
                "from": left.token,
                "to": right.token,
                "semantic_from": left.semantic_class,
                "semantic_to": right.semantic_class,
                "trit_distance": int(trit_distance),
                "band_delta": int(band_delta),
                "resilience_delta": round(resilience_delta, 6),
                "adaptivity_delta": round(adaptivity_delta, 6),
                "trust_delta": round(trust_delta, 6),
                "compatibility": round(compatibility, 6),
                "flow": flow,
                "slide_candidate": flow == "slide",
            }
        )
    if not edges:
        mean_compatibility = 1.0
        boundaries = 0
        slides = 0
    else:
        mean_compatibility = sum(edge["compatibility"] for edge in edges) / len(edges)
        boundaries = sum(1 for edge in edges if edge["flow"] == "boundary")
        slides = sum(1 for edge in edges if edge["flow"] == "slide")
    return {
        "schema": "scbe_atomic_neighbor_gradient_v1",
        "cell_count": len(states),
        "edge_count": len(edges),
        "mean_compatibility": round(mean_compatibility, 6),
        "slide_candidates": slides,
        "boundaries": boundaries,
        "edges": edges,
    }


def build_bridge_receipt(text: str, command: str | None, tongue: str, target_language: str) -> dict[str, Any]:
    from scripts.system.context_code_conlang_bridge import BridgeRequest, build_bridge

    return _json_safe(
        build_bridge(
            BridgeRequest(
                intent=text,
                source_language="natural",
                target_language=target_language,
                tongue=tongue,
                permission_mode="dry-run",
                requested_tool=command,
            ),
            all_faces=True,
        )
    )


def build_receipt(args: argparse.Namespace) -> dict[str, Any]:
    data, source = load_payload(args)
    text = data.decode("utf-8", errors="replace")
    issues: list[dict[str, Any]] = []
    layers: dict[str, Any] = {}

    layer_builders = [
        ("bit_spine", lambda: build_bit_spine_receipt(data, args.max_bytes)),
        ("sacred_tongue_cli", lambda: build_sacred_tongue_receipt(data, args.tongue, args.max_tongue_bytes)),
        ("cube_token", lambda: build_cube_receipt(text, args.atom)),
        ("atomic_workflow", lambda: build_atomic_receipt(text, args.language, args.context_class)),
        ("context_code_conlang_bridge", lambda: build_bridge_receipt(text, args.command, args.tongue, args.target_language)),
    ]
    for name, builder in layer_builders:
        try:
            layers[name] = builder()
        except Exception as exc:
            layers[name] = {"ok": False, "error": str(exc)}
            issues.append({"layer": name, "error": str(exc)})

    roundtrip = {
        "bit_spine": layers.get("bit_spine", {}).get("roundtrip", {}),
        "sacred_tongue_cli": layers.get("sacred_tongue_cli", {}).get("roundtrip_ok"),
        "cube_token": layers.get("cube_token", {}).get("all_faces_roundtrip"),
    }
    ok = not issues and all(bool(v) for v in roundtrip.get("bit_spine", {}).values()) and roundtrip.get("sacred_tongue_cli") is True

    return {
        "schema": "scbe_pipeline_receipt_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "ok": bool(ok),
        "source": source,
        "content_preview": _preview_text(data),
        "sha256": _sha256(data),
        "settings": {
            "tongue": args.tongue.upper(),
            "language": args.language,
            "context_class": args.context_class,
            "target_language": args.target_language,
            "max_bytes": args.max_bytes,
            "max_tongue_bytes": args.max_tongue_bytes,
        },
        "roundtrip": roundtrip,
        "layers": layers,
        "issues": issues,
        "progression": [
            "raw utf8 bytes",
            "binary / hex / trit spine",
            "binary Turing probe",
            "Sacred Tongue CLI token surface",
            "CubeToken conlang faces",
            "atomic token states",
            "code lane alignment",
            "workflow composition",
            "context code/conlang bridge",
        ],
    }


def write_receipt(receipt: dict[str, Any], out: str | None) -> str | None:
    if not out:
        return None
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit a SCBE pipeline receipt.")
    parser.add_argument("positional_content", nargs="*", help="Content to receipt if --content/--file are omitted.")
    parser.add_argument("--content")
    parser.add_argument("--file")
    parser.add_argument("--out")
    parser.add_argument("--tongue", default="KO")
    parser.add_argument("--language", default="python")
    parser.add_argument("--context-class", default="code")
    parser.add_argument("--target-language", default="python")
    parser.add_argument("--command")
    parser.add_argument("--atom")
    parser.add_argument("--max-bytes", type=int, default=4096)
    parser.add_argument("--max-tongue-bytes", type=int, default=64)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.content is None and not args.file and args.positional_content:
        args.content = " ".join(args.positional_content)

    receipt = build_receipt(args)
    out_path = write_receipt(receipt, args.out)
    if out_path:
        receipt["written"] = out_path

    if args.json:
        print(json.dumps(receipt, indent=2))
    else:
        print(f"SCBE pipeline receipt ok={receipt['ok']} sha256={receipt['sha256'][:16]}")
        if out_path:
            print(f"written={out_path}")
        if receipt["issues"]:
            print("issues=" + json.dumps(receipt["issues"], indent=2))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

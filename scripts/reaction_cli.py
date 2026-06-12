#!/usr/bin/env python3
"""SCBE reaction packet CLI.

Small utility surface for auditing and comparing reaction-state packets. The
commands are intentionally stdlib-only so they can run anywhere the repo runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.audio_field_observables import (
    AudioFieldModel,
    analyze_audio_field,
    generate_decaying_sine,
    generate_sine,
)
from python.scbe.geometry_view import GeometryEngineError, geometry_view_packet
from python.scbe.reaction_balance import BalanceError, balance_reaction_packet
from python.scbe.reaction_state import (
    ReactionEndpoint,
    ReactionRecalculation,
    build_reaction_state_packet,
    packet_from_dict,
)

# Every packet this CLI emits is signed under one stable identity so receipts
# are attributable and chainable across runs. sign() degrades to an unsigned
# packet (signature stays None) where no signer backend is available.
SIGNER_AGENT_ID = "scbe-react-cli"


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_packets(value: Any) -> list[dict[str, Any]]:
    """Find reaction packets inside a packet file or benchmark report."""

    if isinstance(value, dict) and value.get("schema_version") == "scbe_reaction_state_packet_v1":
        return [value]
    packets: list[dict[str, Any]] = []
    if isinstance(value, dict):
        packet = value.get("reaction_state_packet")
        if isinstance(packet, dict):
            packets.append(packet)
        for key, child in value.items():
            if key == "reaction_state_packet":
                continue
            packets.extend(find_packets(child))
    elif isinstance(value, list):
        for item in value:
            packets.extend(find_packets(item))
    return packets


def audit_packet(path: str) -> dict[str, Any]:
    data = load_json(path)
    packets = find_packets(data)
    rows = []
    for index, packet_data in enumerate(packets):
        packet = packet_from_dict(packet_data)
        rows.append(
            {
                "index": index,
                "packet_hash": packet.packet_hash,
                "hash_ok": packet.verify_hash(),
                "domain": packet.domain,
                "bounded_operation": packet.bounded_operation,
                "classification": packet.classification,
                "source_identity": packet.source.identity,
                "target_identity": packet.target.identity,
                "loss_count": len(packet.loss_notes),
                "engraving_count": len(packet.semantic_engravings),
                "claim_boundary": packet.claim_boundary,
                "signature_alg": packet.signature_alg,
                "signature_verified": packet.verify_signature(),
            }
        )
    return {
        "schema_version": "scbe_reaction_audit_v1",
        "path": path,
        "packet_count": len(rows),
        "ok": bool(rows) and all(row["hash_ok"] for row in rows),
        "packets": rows,
    }


def compare_packets(left_path: str, right_path: str) -> dict[str, Any]:
    left = find_packets(load_json(left_path))
    right = find_packets(load_json(right_path))
    left_hashes = {packet.get("packet_hash") for packet in left}
    right_hashes = {packet.get("packet_hash") for packet in right}
    left_classes = {packet.get("classification") for packet in left}
    right_classes = {packet.get("classification") for packet in right}
    return {
        "schema_version": "scbe_reaction_compare_v1",
        "left": left_path,
        "right": right_path,
        "left_packet_count": len(left),
        "right_packet_count": len(right),
        "shared_packet_hashes": sorted(hash_value for hash_value in left_hashes & right_hashes if hash_value),
        "left_only_packet_hashes": sorted(hash_value for hash_value in left_hashes - right_hashes if hash_value),
        "right_only_packet_hashes": sorted(hash_value for hash_value in right_hashes - left_hashes if hash_value),
        "classification_changed": left_classes != right_classes,
        "left_classifications": sorted(str(item) for item in left_classes if item),
        "right_classifications": sorted(str(item) for item in right_classes if item),
    }


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_code_packet(source_path: str, target_path: str) -> dict[str, Any]:
    source_hash = sha256_file(source_path)
    target_hash = sha256_file(target_path)
    identity_preserved = source_hash == target_hash
    packet = build_reaction_state_packet(
        domain="code",
        step=1,
        bounded_operation="code_file_hash_transform",
        source=ReactionEndpoint(
            identity=Path(source_path).name,
            representation="file",
            language=Path(source_path).suffix.lstrip(".") or None,
            payload_sha256=source_hash,
            metadata={"path": source_path},
        ),
        target=ReactionEndpoint(
            identity=Path(target_path).name,
            representation="file",
            language=Path(target_path).suffix.lstrip(".") or None,
            payload_sha256=target_hash,
            metadata={"path": target_path},
        ),
        semantic_engravings=[
            "KO identity lane: source and target payload hashes compared",
            f"source sha256: {source_hash}",
            f"target sha256: {target_hash}",
        ],
        loss_notes=[] if identity_preserved else ["payload hash changed"],
        recalculation=ReactionRecalculation(
            identity_ok=identity_preserved,
            extra={
                "source_bytes": Path(source_path).stat().st_size,
                "target_bytes": Path(target_path).stat().st_size,
            },
        ),
        identity_preserved=identity_preserved,
        claim_boundary=[
            "hash equality proves byte identity only",
            "semantic equivalence requires tests or a language-specific analyzer",
        ],
    ).sign(SIGNER_AGENT_ID)
    return {
        "schema_version": "scbe_react_code_v1",
        "ok": identity_preserved,
        "source": source_path,
        "target": target_path,
        "reaction_state_packet": packet.to_dict(),
    }


def build_audio_packet(
    *,
    frequency_hz: float,
    sample_rate_hz: float,
    duration_s: float,
    decay_seconds: float | None,
    model_kind: str,
    coupling_gain: float,
    sound_speed_mps: float | None,
    alfven_speed_mps: float | None,
) -> dict[str, Any]:
    signal = (
        generate_decaying_sine(
            frequency_hz,
            sample_rate_hz=sample_rate_hz,
            duration_s=duration_s,
            decay_seconds=decay_seconds,
        )
        if decay_seconds is not None
        else generate_sine(
            frequency_hz,
            sample_rate_hz=sample_rate_hz,
            duration_s=duration_s,
        )
    )
    model = AudioFieldModel(
        kind=model_kind,
        name=f"{model_kind}-audio-field",
        coupling_gain=coupling_gain,
        sound_speed_mps=sound_speed_mps,
        alfven_speed_mps=alfven_speed_mps,
    )
    observables = analyze_audio_field(signal, sample_rate_hz=sample_rate_hz, model=model)
    packet = build_reaction_state_packet(
        domain="audio",
        step=1,
        bounded_operation="audio_field_observable_projection",
        source=ReactionEndpoint(
            identity=f"sine:{frequency_hz:g}Hz",
            representation="generated_audio_frame",
            language="waveform",
            metadata={
                "sample_rate_hz": sample_rate_hz,
                "duration_s": duration_s,
                "decay_seconds": decay_seconds,
            },
        ),
        target=ReactionEndpoint(
            identity="audio-field-observables",
            representation="observable_vector",
            language="wave_features",
            metadata={
                "field_model": model.to_dict(),
                "field_relationship": observables.field_relationship,
            },
        ),
        semantic_engravings=[
            f"spectral_centroid_hz={observables.spectral_centroid_hz:.6f}",
            f"high_frequency_ratio={observables.high_frequency_ratio:.6f}",
            f"stability={observables.stability:.6f}",
            f"dispersion_proxy={observables.dispersion_proxy:.6f}",
            f"modal_count={observables.modal_count}",
            f"field_relationship={observables.field_relationship}",
        ],
        loss_notes=(
            [] if observables.field_coupling_proxy is not None else ["no declared field coupling proxy emitted"]
        ),
        recalculation=ReactionRecalculation(
            scientific_checks_ok=True,
            unit_checks_ok=True,
            identity_ok=observables.modal_count_state.ok,
            extra={"observables": observables.to_dict()},
        ),
        identity_preserved=observables.modal_count_state.ok,
        recovery_evidence=["field coupling proxy emitted"] if observables.field_coupling_proxy is not None else (),
        claim_boundary=list(observables.claim_boundary),
    ).sign(SIGNER_AGENT_ID)
    return {
        "schema_version": "scbe_react_audio_v1",
        "ok": observables.modal_count_state.ok,
        "observables": observables.to_dict(),
        "reaction_state_packet": packet.to_dict(),
    }


def print_human_audit(payload: dict[str, Any]) -> None:
    print(f"reaction audit: ok={payload['ok']} packets={payload['packet_count']}")
    for row in payload["packets"]:
        sig = f" sig={row['signature_alg']}/{row['signature_verified']}" if row.get("signature_alg") else ""
        print(
            f"- #{row['index']} {row['classification']} hash_ok={row['hash_ok']}{sig} "
            f"{row['source_identity']} -> {row['target_identity']}"
        )


def print_human_compare(payload: dict[str, Any]) -> None:
    print(
        "reaction compare: "
        f"left={payload['left_packet_count']} right={payload['right_packet_count']} "
        f"classification_changed={payload['classification_changed']}"
    )
    if payload["shared_packet_hashes"]:
        print(f"shared hashes: {len(payload['shared_packet_hashes'])}")
    if payload["left_only_packet_hashes"]:
        print(f"left only: {len(payload['left_only_packet_hashes'])}")
    if payload["right_only_packet_hashes"]:
        print(f"right only: {len(payload['right_only_packet_hashes'])}")


def print_human_code(payload: dict[str, Any]) -> None:
    packet = payload["reaction_state_packet"]
    print(
        "reaction code: "
        f"ok={payload['ok']} classification={packet['classification']} "
        f"hash={packet['packet_hash']}"
    )


def print_human_audio(payload: dict[str, Any]) -> None:
    obs = payload["observables"]
    packet = payload["reaction_state_packet"]
    print(
        "reaction audio: "
        f"ok={payload['ok']} classification={packet['classification']} "
        f"stability={obs['stability']:.6f} relationship={obs['field_relationship']}"
    )


def build_balance(reactants: str, products: str) -> dict[str, Any]:
    react = [s.strip() for s in reactants.split(",") if s.strip()]
    prod = [s.strip() for s in products.split(",") if s.strip()]
    try:
        packet = balance_reaction_packet(react, prod).sign(SIGNER_AGENT_ID)
    except BalanceError as exc:
        return {
            "schema_version": "scbe_react_balance_v1",
            "ok": False,
            "error": str(exc),
            "reactants": react,
            "products": prod,
        }
    return {
        "schema_version": "scbe_react_balance_v1",
        "ok": bool(packet.recalculation.identity_ok),
        "equation": packet.target.metadata.get("equation"),
        "coefficients": packet.target.metadata.get("coefficients"),
        "reaction_state_packet": packet.to_dict(),
    }


def print_human_balance(payload: dict[str, Any]) -> None:
    if not payload.get("ok"):
        print(f"reaction balance: FAILED {payload.get('error', '')}")
        return
    print(f"reaction balance: {payload['equation']}")
    print(f"coefficients: {payload['coefficients']}")


def build_geometry(smiles: str) -> dict[str, Any]:
    try:
        packet = geometry_view_packet(smiles).sign(SIGNER_AGENT_ID)
    except GeometryEngineError as exc:
        return {"schema_version": "scbe_react_geometry_v1", "ok": False, "error": str(exc), "smiles": smiles}
    meta = packet.target.metadata
    return {
        "schema_version": "scbe_react_geometry_v1",
        "ok": True,
        "formula": meta.get("formula"),
        "rotor_type": meta.get("rotor_type"),
        "point_group": meta.get("point_group"),
        "reaction_state_packet": packet.to_dict(),
    }


def print_human_geometry(payload: dict[str, Any]) -> None:
    if not payload.get("ok"):
        print(f"reaction geometry: FAILED {payload.get('error', '')}")
        return
    print(
        f"reaction geometry: {payload['formula']} "
        f"rotor={payload['rotor_type']} point_group={payload['point_group']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(prog="scbe react")
    sub = parser.add_subparsers(dest="cmd", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--packet", required=True)
    audit.add_argument("--json", action="store_true")
    compare = sub.add_parser("compare")
    compare.add_argument("--left", required=True)
    compare.add_argument("--right", required=True)
    compare.add_argument("--json", action="store_true")
    code = sub.add_parser("code")
    code.add_argument("--source", required=True)
    code.add_argument("--target", required=True)
    code.add_argument("--json", action="store_true")
    balance_parser = sub.add_parser("balance")
    balance_parser.add_argument("--reactants", required=True, help="comma-separated formulas, e.g. C3H8,O2")
    balance_parser.add_argument("--products", required=True, help="comma-separated formulas, e.g. CO2,H2O")
    balance_parser.add_argument("--json", action="store_true")
    geometry_parser = sub.add_parser("geometry")
    geometry_parser.add_argument("--smiles", required=True, help="SMILES string, e.g. CCO")
    geometry_parser.add_argument("--json", action="store_true")
    audio = sub.add_parser("audio")
    audio.add_argument("--frequency", type=float, default=440.0)
    audio.add_argument("--sample-rate", type=float, default=4096.0)
    audio.add_argument("--duration", type=float, default=0.05)
    audio.add_argument("--decay-seconds", type=float)
    audio.add_argument(
        "--model",
        choices=("generic", "magnetoelastic", "magnetosonic"),
        default="generic",
    )
    audio.add_argument("--coupling-gain", type=float, default=1.0)
    audio.add_argument("--sound-speed", type=float)
    audio.add_argument("--alfven-speed", type=float)
    audio.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.cmd == "audit":
        payload = audit_packet(args.packet)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_human_audit(payload)
        return 0 if payload["ok"] else 1
    if args.cmd == "compare":
        payload = compare_packets(args.left, args.right)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_human_compare(payload)
        return 0
    if args.cmd == "code":
        payload = build_code_packet(args.source, args.target)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_human_code(payload)
        return 0 if payload["ok"] else 1
    if args.cmd == "balance":
        payload = build_balance(args.reactants, args.products)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_human_balance(payload)
        return 0 if payload["ok"] else 1
    if args.cmd == "geometry":
        payload = build_geometry(args.smiles)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_human_geometry(payload)
        return 0 if payload["ok"] else 1
    if args.cmd == "audio":
        payload = build_audio_packet(
            frequency_hz=args.frequency,
            sample_rate_hz=args.sample_rate,
            duration_s=args.duration,
            decay_seconds=args.decay_seconds,
            model_kind=args.model,
            coupling_gain=args.coupling_gain,
            sound_speed_mps=args.sound_speed,
            alfven_speed_mps=args.alfven_speed,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_human_audio(payload)
        return 0 if payload["ok"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

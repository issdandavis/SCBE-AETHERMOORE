#!/usr/bin/env python3
"""SCBE reaction packet CLI.

Small utility surface for auditing and comparing reaction-state packets. The
commands are intentionally stdlib-only so they can run anywhere the repo runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.audio_field_observables import (
    AudioFieldModel,
    AudioFieldObservables,
    analyze_audio_field,
    generate_decaying_sine,
    generate_sine,
)
from python.scbe.controlled_substances import ControlledSubstanceDenied, screen_input
from python.scbe.geometry_view import GeometryEngineError, geometry_view_packet
from python.scbe.reaction_balance import BalanceError, balance_reaction_packet
from python.scbe.reaction_language import ReactionPlan, plan_from_text
from python.scbe import units as _U
from python.scbe.reaction_state import (
    ReactionEndpoint,
    ReactionLedger,
    ReactionRecalculation,
    build_reaction_state_packet,
    packet_from_dict,
    rekor_hashedrekord_entry,
    unit_check,
)

# Every packet this CLI emits is signed under one stable identity so receipts
# are attributable and chainable across runs. sign() degrades to an unsigned
# packet (signature stays None) where no signer backend is available.
SIGNER_AGENT_ID = "scbe-react-cli"


class InputFileError(ValueError):
    """A packet/report file is missing or not valid JSON."""


def load_json(path: str) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise InputFileError(f"file not found: {path}")
    except json.JSONDecodeError as exc:
        raise InputFileError(f"not valid JSON ({path}): {exc}")


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
    try:
        data = load_json(path)
    except InputFileError as exc:
        return {"schema_version": "scbe_reaction_audit_v1", "path": path, "ok": False, "error": str(exc)}
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
    try:
        left = find_packets(load_json(left_path))
        right = find_packets(load_json(right_path))
    except InputFileError as exc:
        return {
            "schema_version": "scbe_reaction_compare_v1",
            "left": left_path,
            "right": right_path,
            "ok": False,
            "error": str(exc),
        }
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


def _audio_unit_checks_ok(model: AudioFieldModel) -> bool | None:
    """Honest source for ``unit_checks_ok`` on an audio-field packet.

    Most acoustic observables are dimensionless ratios or read-off frequencies, so
    there is no dimensional-arithmetic chain to verify and the honest value is
    ``None`` ("no unit-bearing computation"). The one exception is the magnetosonic
    coupling, which combines two velocities exactly as ``_compute_field_coupling``
    does: ``magnetosonic_speed = sqrt(v_sound**2 + v_alfven**2)`` then
    ``magnetic_share = v_alfven / magnetosonic_speed``. We re-express that in
    ``Quantity`` arithmetic so the check can actually FAIL: ``add`` is the Mars
    Climate Orbiter catch (it raises if the two speeds carry the same dimension but
    a different unit), and the share must come out dimensionless. A ``True`` here
    means a real dimensional relation held, not that a flag was set.
    """
    if model.kind != "magnetosonic" or model.sound_speed_mps is None or model.alfven_speed_mps is None:
        return None

    mps = _U.METER / _U.SECOND

    def _consistent() -> object:
        v_s = _U.q(abs(model.sound_speed_mps), mps)
        v_a = _U.q(abs(model.alfven_speed_mps), mps)
        # v_sound**2 + v_alfven**2 — add() raises on a same-dimension/different-unit mix.
        v_sq_sum = _U.add(_U.mul(v_s, v_s), _U.mul(v_a, v_a))
        _U.assert_dim(v_sq_sum, _U.dim(m=2, s=-2))  # velocity squared
        # magnetic_share**2 = v_alfven**2 / (v_sound**2 + v_alfven**2) must be dimensionless.
        return _U.assert_dim(_U.div(_U.mul(v_a, v_a), v_sq_sum), _U.DIMENSIONLESS)

    return unit_check(_consistent)[0]


def _audio_scientific_checks_ok(observables: AudioFieldObservables) -> bool:
    """Honest source for ``scientific_checks_ok``: every emitted observable must be
    finite and within its declared range. Replaces a hard-coded ``True`` so the flag
    can fail on a degenerate spectrum (non-finite energy/centroid, an out-of-range
    ratio, or a coupling proxy that escaped [0, 1])."""
    finite_fields = (
        observables.energy_log,
        observables.spectral_centroid_hz,
        observables.spectral_bandwidth_hz,
        observables.high_frequency_ratio,
        observables.stability,
        observables.dispersion_proxy,
    )
    if not all(math.isfinite(value) for value in finite_fields):
        return False
    if observables.spectral_centroid_hz < 0.0 or observables.spectral_bandwidth_hz < 0.0:
        return False
    if not (0.0 <= observables.high_frequency_ratio <= 1.0):
        return False
    if not (0.0 <= observables.stability <= 1.0):
        return False
    if observables.field_coupling_proxy is not None and not (0.0 <= observables.field_coupling_proxy <= 1.0):
        return False
    return True


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
            scientific_checks_ok=_audio_scientific_checks_ok(observables),
            unit_checks_ok=_audio_unit_checks_ok(model),
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
    if payload.get("error"):
        print(f"reaction audit: FAILED {payload['error']}")
        return
    print(f"reaction audit: ok={payload['ok']} packets={payload['packet_count']}")
    for row in payload["packets"]:
        sig = f" sig={row['signature_alg']}/{row['signature_verified']}" if row.get("signature_alg") else ""
        print(
            f"- #{row['index']} {row['classification']} hash_ok={row['hash_ok']}{sig} "
            f"{row['source_identity']} -> {row['target_identity']}"
        )


def print_human_compare(payload: dict[str, Any]) -> None:
    if payload.get("error"):
        print(f"reaction compare: FAILED {payload['error']}")
        return
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
        "hazards": packet.target.metadata.get("hazards", []),
        "reaction_state_packet": packet.to_dict(),
    }


def print_human_balance(payload: dict[str, Any]) -> None:
    if not payload.get("ok"):
        print(f"reaction balance: FAILED {payload.get('error', '')}")
        return
    print(f"reaction balance: {payload['equation']}")
    print(f"coefficients: {payload['coefficients']}")
    for flag in payload.get("hazards", []):
        print(f"WARNING {flag}")


def build_geometry(smiles: str) -> dict[str, Any]:
    try:
        packet = geometry_view_packet(smiles).sign(SIGNER_AGENT_ID)
    except ControlledSubstanceDenied as exc:
        return {
            "schema_version": "scbe_react_geometry_v1",
            "ok": False,
            "denied": True,
            "error": str(exc),
            "screen": exc.report,
            "smiles": smiles,
        }
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
    if payload.get("denied"):
        print(f"reaction geometry: DENIED {payload.get('error', '')}")
        return
    if not payload.get("ok"):
        print(f"reaction geometry: FAILED {payload.get('error', '')}")
        return
    print(
        f"reaction geometry: {payload['formula']} "
        f"rotor={payload['rotor_type']} point_group={payload['point_group']}"
    )


def build_screen(text: str) -> dict[str, Any]:
    """Defensive controlled-substance screen over a SMILES string or CAS number.

    Reports flagged/clear, the match kind, and the screen level that actually
    ran (exact_string without RDKit, similarity with it) — never the matched
    list entry.
    """
    report = screen_input(text)
    return {"schema_version": "scbe_react_screen_v1", "ok": True, "input": text, **report}


def print_human_screen(payload: dict[str, Any]) -> None:
    verdict = "FLAGGED" if payload["flagged"] else "clear"
    print(f"controlled-substance screen: {verdict}")
    if payload["flagged"]:
        print(f"match kind: {payload['match_kind']}")
    if payload.get("max_similarity") is not None:
        print(f"max similarity vs list: {payload['max_similarity']} (threshold 0.35)")
    print(f"screen level: {payload['screen_level']} (list n={payload['list_size']})")


def build_checkpoint(path: str, rekor_dry_run: bool = False) -> dict[str, Any]:
    """Merkle-checkpoint every packet found in a packet/report file.

    The checkpoint commits to the exact set, order, and count (the omission
    attack a linear prev-hash chain cannot see) and is signed under the CLI
    identity. chain_verified is True only when the packets form an unbroken
    prev-hash chain in file order.
    """
    try:
        data = load_json(path)
    except InputFileError as exc:
        return {"schema_version": "scbe_react_checkpoint_v1", "ok": False, "error": str(exc), "path": path}
    found = find_packets(data)
    if not found:
        return {"schema_version": "scbe_react_checkpoint_v1", "ok": False, "error": "no packets found", "path": path}
    ledger = ReactionLedger(agent_id=SIGNER_AGENT_ID)
    ledger.packets = [packet_from_dict(p) for p in found]
    ledger._last_hash = ledger.packets[-1].packet_hash
    checkpoint = ledger.checkpoint()
    payload: dict[str, Any] = {
        "schema_version": "scbe_react_checkpoint_v1",
        "ok": True,
        "path": path,
        "packets": len(found),
        "checkpoint": checkpoint,
        "inclusion_proofs": [ledger.inclusion_proof(i) for i in range(len(found))],
    }
    if rekor_dry_run:
        # Anchor-READY only: no network I/O, and the public Rekor instance
        # verifies PKIX keys (ECDSA/Ed25519ph), not ML-DSA - countersign the
        # digest with a PKIX identity before actually submitting.
        payload["rekor_dry_run"] = rekor_hashedrekord_entry(checkpoint)
    return payload


def print_human_checkpoint(payload: dict[str, Any]) -> None:
    if not payload.get("ok"):
        print(f"reaction checkpoint: FAILED {payload.get('error', '')}")
        return
    cp = payload["checkpoint"]
    print(f"reaction checkpoint: {payload['packets']} packets")
    print(f"merkle root: {cp['merkle_root']}")
    print(f"chain verified: {cp['chain_verified']}")
    print(f"signed: {cp['signature_alg'] or 'no'}")
    if payload.get("rekor_dry_run"):
        print(f"rekor digest (dry-run): {payload['rekor_dry_run']['spec']['data']['hash']['value']}")


# Map a parsed plan's verb onto the existing builder. Execution reuses the same
# governed/receipted paths as the explicit subcommands -- the NL layer only
# chooses the verb and fills the args, it adds no new privilege.
def _execute_plan(plan: "ReactionPlan") -> dict[str, Any]:
    if plan.verb == "balance":
        return build_balance(plan.args["reactants"], plan.args["products"])
    if plan.verb == "screen":
        return build_screen(plan.args["input"])
    if plan.verb == "geometry":
        return build_geometry(plan.args["smiles"])
    if plan.verb == "checkpoint":
        return build_checkpoint(plan.args["packets"], rekor_dry_run=plan.args.get("rekor_dry_run", False))
    return {"ok": False, "error": f"no executor for verb {plan.verb!r}"}


def build_ask(text: str, *, execute: bool = True) -> dict[str, Any]:
    """Parse a natural-language request, map it to a react verb, and (optionally)
    run it through the same governed builder the explicit subcommand uses.

    Confident plans run; ambiguous ones return the clarification and the exact
    command they *would* run, so the caller asks instead of guessing.
    """
    plan = plan_from_text(text)
    payload: dict[str, Any] = {
        "schema_version": "scbe_react_ask_v1",
        "input": text,
        "verb": plan.verb,
        "confidence": round(plan.confidence, 3),
        "canonical_command": plan.canonical_command,
        "clarification": plan.clarification,
        "notes": plan.notes,
        "executed": False,
    }
    if plan.verb == "help" or plan.verb is None or not plan.confident:
        payload["ok"] = plan.verb == "help"
        return payload
    if not execute:
        payload["ok"] = True
        return payload
    # The NL layer must never crash: a builder raising (bad input, missing
    # engine) becomes a clean error payload, not a traceback.
    try:
        result = _execute_plan(plan)
    except Exception as exc:  # noqa: BLE001 - surface any builder failure as data
        result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    payload["executed"] = True
    payload["ok"] = bool(result.get("ok"))
    payload["result"] = result
    return payload


def print_human_ask(payload: dict[str, Any]) -> None:
    verb = payload.get("verb")
    if verb == "help":
        for note in payload.get("notes", []):
            print(note)
        return
    if payload.get("clarification"):
        print(f"reaction ask: not sure ({payload['confidence']:.2f} confidence)")
        print(payload["clarification"])
        if payload.get("canonical_command"):
            print(f"closest command: scbe {payload['canonical_command']}")
        return
    print(f"-> scbe {payload['canonical_command']}  (confidence {payload['confidence']:.2f})")
    for note in payload.get("notes", []):
        print(f"   note: {note}")
    if not payload.get("executed"):
        return
    result = payload.get("result", {})
    {
        "balance": print_human_balance,
        "screen": print_human_screen,
        "geometry": print_human_geometry,
        "checkpoint": print_human_checkpoint,
    }.get(verb, lambda _r: None)(result)


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
    screen_parser = sub.add_parser("screen")
    screen_parser.add_argument("--input", required=True, help="SMILES string or CAS number to screen")
    screen_parser.add_argument("--json", action="store_true")
    checkpoint_parser = sub.add_parser("checkpoint")
    checkpoint_parser.add_argument("--packets", required=True, help="packet or report JSON file to checkpoint")
    checkpoint_parser.add_argument("--rekor-dry-run", action="store_true")
    checkpoint_parser.add_argument("--json", action="store_true")
    ask_parser = sub.add_parser("ask", help="natural-language request, e.g. 'balance propane combustion'")
    ask_parser.add_argument("text", nargs="+", help="what you want, in plain words")
    ask_parser.add_argument("--explain", action="store_true", help="show the mapped command without running it")
    ask_parser.add_argument("--json", action="store_true")
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
        # a missing/invalid file is a failure; a successful compare is always 0
        # (it reports differences, it does not "fail" on them).
        return 1 if payload.get("error") else 0
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
    if args.cmd == "screen":
        payload = build_screen(args.input)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_human_screen(payload)
        return 1 if payload["flagged"] else 0
    if args.cmd == "checkpoint":
        payload = build_checkpoint(args.packets, rekor_dry_run=args.rekor_dry_run)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_human_checkpoint(payload)
        return 0 if payload["ok"] else 1
    if args.cmd == "ask":
        payload = build_ask(" ".join(args.text), execute=not args.explain)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print_human_ask(payload)
        # exit 2 when we had to ask the user to clarify (no action taken).
        if payload.get("clarification"):
            return 2
        # a flagged screen exits non-zero like the explicit `screen` verb, so a
        # caller (human or AI) sees the hazard in the exit code, not just stdout.
        if payload.get("result", {}).get("flagged"):
            return 1
        return 0 if payload.get("ok") else 1
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

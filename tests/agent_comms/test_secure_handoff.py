from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.agent_comms import AgentPacketV1, Budget, ContextRef, HandoffIntegrityError, Route, hash_state
from src.agent_comms.secure_handoff import (
    DECODE_METHOD,
    KEY_LIFECYCLE,
    DecodeAgreement,
    compactness_report,
    open_handoff,
    seal_handoff,
    semantic_shadow,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _packet(request: str = "Review the referenced patch and return a merge verdict.") -> AgentPacketV1:
    return AgentPacketV1(
        task_id="handoff-test-001",
        phase="verify",
        route=Route(tongue="RU", domain="code", permission="read"),
        context_refs=[
            ContextRef(kind="path", value="src/agent_comms/packet.py", bytes=4096),
            ContextRef(kind="sha256", value="a" * 64),
        ],
        state_hash=hash_state("branch:main", "task:handoff-test-001"),
        budget=Budget(max_input_tokens=2048, max_output_tokens=256),
        request=request,
        expected_output="verdict",
        created_at=1.0,
    )


def test_secure_handoff_round_trips_packet_with_decode_agreement() -> None:
    packet = _packet()
    sealed = seal_handoff(
        packet,
        sender_id="codex",
        recipient_id="claude",
        shared_secret="session-secret",
        nonce=b"0" * 16,
        created_at=2.0,
    )

    assert sealed["decode_agreement"]["method"] == DECODE_METHOD
    assert sealed["decode_agreement"]["key_lifecycle"] == KEY_LIFECYCLE
    assert sealed["shadow"]["task_id"] == packet.task_id
    assert "ciphertext" in sealed
    assert packet.request not in str(sealed["shadow"])

    recovered = open_handoff(sealed, shared_secret="session-secret")
    assert recovered.to_dict() == packet.to_dict()


def test_secure_handoff_rejects_wrong_secret() -> None:
    sealed = seal_handoff(
        _packet(),
        sender_id="codex",
        recipient_id="claude",
        shared_secret="right-secret",
        nonce=b"1" * 16,
    )

    with pytest.raises(HandoffIntegrityError, match="authentication"):
        open_handoff(sealed, shared_secret="wrong-secret")


def test_secure_handoff_rejects_tampered_shadow() -> None:
    sealed = seal_handoff(
        _packet(),
        sender_id="codex",
        recipient_id="claude",
        shared_secret="session-secret",
        nonce=b"2" * 16,
    )
    tampered = copy.deepcopy(sealed)
    tampered["shadow"]["route"]["permission"] = "merge"

    with pytest.raises(HandoffIntegrityError, match="authentication"):
        open_handoff(tampered, shared_secret="session-secret")


def test_semantic_shadow_exposes_structure_not_body() -> None:
    packet = _packet(request="Sensitive task instruction should stay sealed.")
    shadow = semantic_shadow(packet)

    assert shadow["context_ref_count"] == 2
    assert shadow["context_ref_kinds"] == ["path", "sha256"]
    assert shadow["request_bytes"] == len(packet.request.encode("utf-8"))
    assert packet.request not in str(shadow)
    assert shadow["body_commitment"].startswith("sha256:")


def test_decode_agreement_rejects_unknown_method() -> None:
    with pytest.raises(ValueError, match="unsupported decode method"):
        DecodeAgreement.from_dict(
            {
                "method": "unknown",
                "kdf": "hkdf-sha256-route-bound-v1",
                "compression": "zlib",
                "canonical": "json.sorted.minified",
                "route_bound": True,
                "key_lifecycle": "derive-use-discard",
            }
        )


def test_compactness_report_tracks_naive_and_sealed_sizes() -> None:
    packet = _packet(request="x" * 1000)
    sealed = seal_handoff(
        packet,
        sender_id="codex",
        recipient_id="claude",
        shared_secret="session-secret",
        nonce=b"3" * 16,
    )
    report = compactness_report(packet, sealed_bytes_hint=sealed["compactness"]["sealed_envelope_bytes"])

    assert report["canonical_packet_bytes"] > 0
    assert report["naive_handoff_bytes"] > 0
    assert report["referenced_context_bytes"] == 4096
    assert report["naive_with_context_bytes"] > report["naive_handoff_bytes"]
    assert report["sealed_envelope_bytes"] > 0
    assert report["saves_space_vs_naive_with_context"] is True
    assert any("Shadow metadata" in note for note in report["notes"])


def test_geoseal_cli_seals_and_opens_handoff(tmp_path: Path) -> None:
    sealed_path = tmp_path / "handoff.json"
    seal_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "handoff-seal",
            "--sender",
            "codex",
            "--recipient",
            "claude",
            "--intent",
            "Review only the referenced harness files.",
            "--context-ref",
            "path:scripts/terminal/geoseal_harness_terminal.py",
            "--secret",
            "cli-secret",
            "--output",
            str(sealed_path),
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert seal_proc.returncode == 0, seal_proc.stderr
    sealed = json.loads(seal_proc.stdout)
    assert sealed["shadow"]["context_ref_count"] == 1
    assert sealed_path.is_file()

    open_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "handoff-open",
            "--sealed-file",
            str(sealed_path),
            "--secret",
            "cli-secret",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert open_proc.returncode == 0, open_proc.stderr
    packet = json.loads(open_proc.stdout)
    assert packet["request"] == "Review only the referenced harness files."
    assert packet["context_refs"][0]["value"] == "scripts/terminal/geoseal_harness_terminal.py"

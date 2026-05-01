import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from src.tokenizer.yin_yang_lattice import build_yin_yang_dual_packet

SCHEMA_PATH = Path("schemas/yin_yang_dual_token_v1.schema.json")
SAMPLE_PATH = Path("schemas/examples/yin_yang_dual_token_v1.industry_sample.json")


def test_yin_yang_dual_packet_preserves_ko_dr_roundtrip() -> None:
    packet = build_yin_yang_dual_packet(
        ko_text="route task through guarded agent lane",
        dr_text="transform patch into reviewed structure",
        size=9,
        active_frame=0,
    )

    assert packet["schema_version"] == "scbe-yin-yang-dual-token-v1"
    assert packet["identity"]["packet_id"].startswith("yy1-")
    assert packet["active_tongue"] == "KO"
    assert packet["boundary"]["not_security_boundary"] is True
    assert packet["microstructure"]["ridge_model"] == "digital_sideband_fields"
    assert packet["routing"]["planner_view"] == "KO"
    assert packet["governance"]["action_boundary"] == "semantic_packet_only"
    assert packet["channels"]["KO"]["roundtrip_ok"] is True
    assert packet["channels"]["DR"]["roundtrip_ok"] is True
    assert packet["channels"]["KO"]["token_count"] > 0
    assert packet["channels"]["DR"]["token_count"] > 0


def test_yin_yang_dual_packet_flips_active_frame() -> None:
    frame_0 = build_yin_yang_dual_packet(ko_text="if approve then run", dr_text="shape patch tree", active_frame=0)
    frame_1 = build_yin_yang_dual_packet(ko_text="if approve then run", dr_text="shape patch tree", active_frame=1)

    assert frame_0["active_tongue"] == "KO"
    assert frame_0["inactive_tongue"] == "DR"
    assert frame_1["active_tongue"] == "DR"
    assert frame_1["inactive_tongue"] == "KO"
    assert frame_0["surface"]["complementarity"]["passes"] is True
    assert frame_0["surface"]["complementarity"]["rotational_antisymmetry_score"] == 1.0
    assert frame_0["packet_sha256"] != frame_1["packet_sha256"]


def test_yin_yang_dual_packet_rejects_bad_surface_size() -> None:
    with pytest.raises(ValueError):
        build_yin_yang_dual_packet(ko_text="route", dr_text="shape", size=8)


def test_geoseal_yin_yang_dual_cli_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "yin-yang-dual",
            "--ko-text",
            "route task",
            "--dr-text",
            "shape patch",
            "--frame",
            "1",
            "--json",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    packet = json.loads(result.stdout)

    assert packet["schema_version"] == "scbe-yin-yang-dual-token-v1"
    assert packet["active_tongue"] == "DR"
    assert packet["channels"]["KO"]["roundtrip_ok"] is True
    assert packet["channels"]["DR"]["roundtrip_ok"] is True


def test_yin_yang_dual_packet_validates_against_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    packet = build_yin_yang_dual_packet(
        ko_text="inspect ridge sector alpha and return by safe path",
        dr_text="slope limit twelve degrees battery floor forty percent home vector locked",
        active_frame=0,
        size=9,
    )

    Draft202012Validator(schema).validate(packet)


def test_yin_yang_dual_industry_sample_validates_against_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(sample)
    assert sample["crypto_envelope"]["payload_state"] == "plaintext_sample"
    assert sample["telemetry"]["audit_replay"] is True

from __future__ import annotations

import json

from scripts.system.foundry_workflow import main, verify_receipt


def test_foundry_workflow_generates_package_verify_and_coupon_plan(
    tmp_path, capsys
) -> None:
    exit_code = main(
        [
            "workflow",
            "--seed",
            "workflow-seed",
            "--out",
            str(tmp_path),
            "--seeds",
            "2",
            "--copies",
            "2",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["schema_version"] == "scbe_foundry_workflow_v1"
    assert payload["verify"]["ok"] is True
    assert payload["coupon_plan"]["sample_count"] == 4
    assert (tmp_path / "package" / "dynamo_core_dual_nodal_dilithium.scad").exists()
    assert (tmp_path / "package" / "braidledger_receipt.json").exists()
    assert (tmp_path / "coupon_plan.json").exists()


def test_verify_fails_closed_when_scad_hash_drifts(tmp_path, capsys) -> None:
    assert (
        main(["package", "--seed", "tamper-seed", "--out", str(tmp_path), "--json"])
        == 0
    )
    capsys.readouterr()

    scad_path = tmp_path / "dynamo_core_dual_nodal_dilithium.scad"
    receipt_path = tmp_path / "braidledger_receipt.json"
    scad_path.write_text(
        scad_path.read_text(encoding="utf-8") + "\n// tampered\n", encoding="utf-8"
    )

    payload = verify_receipt(receipt_path)

    assert payload["ok"] is False
    assert any("SCAD hash" in finding["message"] for finding in payload["findings"])


def test_plan_coupon_writes_null_gated_sample_plan(tmp_path, capsys) -> None:
    out_path = tmp_path / "plan.json"
    exit_code = main(
        [
            "plan-coupon",
            "--part",
            "test coupon",
            "--measurement",
            "dimensional",
            "--seeds",
            "3",
            "--copies",
            "2",
            "--out",
            str(out_path),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    written = json.loads(out_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["sample_count"] == 6
    assert written["samples"][0]["expected_measurements_csv"].startswith(
        "device_id,seed_id"
    )
    assert "shuffled-topology" in " ".join(written["null_gates"])

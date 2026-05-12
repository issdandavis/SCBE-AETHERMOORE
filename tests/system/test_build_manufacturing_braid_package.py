from __future__ import annotations

import hashlib
import json

from scripts.system.build_manufacturing_braid_package import (
    COEFFICIENT_COUNT,
    ManufacturingBraidAdapter,
    main,
)


def test_coefficients_are_deterministic_and_bounded() -> None:
    left = ManufacturingBraidAdapter(b"seed-a", timestamp=123)
    right = ManufacturingBraidAdapter(b"seed-a", timestamp=999)
    other = ManufacturingBraidAdapter(b"seed-b", timestamp=123)

    coeffs = left.generate_coefficients()

    assert coeffs == right.generate_coefficients()
    assert coeffs != other.generate_coefficients()
    assert len(coeffs) == COEFFICIENT_COUNT
    assert all(-4 <= value <= 4 for value in coeffs)


def test_full_package_writes_scad_and_verifiable_braid_receipt(tmp_path) -> None:
    adapter = ManufacturingBraidAdapter(b"manufacturing-test-seed", timestamp=1700000000)
    package = adapter.export_full_package(tmp_path)

    assert package.scad_path.exists()
    assert package.receipt_path.exists()

    scad = package.scad_path.read_text(encoding="utf-8")
    receipt = json.loads(package.receipt_path.read_text(encoding="utf-8"))

    assert "dual_nodal_core();" in scad
    assert "... (rest of the dual-nodal code" not in scad
    assert "dilithium_coeffs = [" in scad
    assert receipt["schema_version"] == "scbe_manufacturing_braid_package_v1"
    assert receipt["coefficient_count"] == COEFFICIENT_COUNT
    assert receipt["scad_sha256"] == hashlib.sha256(package.scad_path.read_bytes()).hexdigest()
    assert receipt["braid_verification"] == {
        "chain_ok": True,
        "tube_ok": True,
        "bad_index": None,
    }
    assert len(receipt["braid_receipt"]["hmac_tag"]) == 64


def test_cli_generates_package_in_requested_directory(tmp_path, capsys) -> None:
    exit_code = main(["--master-seed", "cli-seed", "--output-dir", str(tmp_path), "--part-name", "CLI Core"])

    captured = capsys.readouterr()
    receipt = json.loads((tmp_path / "braidledger_receipt.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "Generated SCAD:" in captured.out
    assert receipt["part_name"] == "CLI Core"

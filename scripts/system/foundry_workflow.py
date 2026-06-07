#!/usr/bin/env python3
"""SCBE space-foundry workflow CLI.

This is an operator surface for the repo's grounded space-foundry lane:

    seed -> bounded geometry -> receipt -> coupon plan -> null-gated measurement

It intentionally does not claim flight hardware, certified materials, or a
standalone PUF. It packages the repeatable workflow and carries the claim
boundary with every JSON payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system.build_manufacturing_braid_package import (
    ManufacturingBraidAdapter,
    _seed_from_args,
)

DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "manufacturing" / "foundry_workflow"
DEFAULT_SCAD_NAME = "dynamo_core_dual_nodal_dilithium.scad"
DEFAULT_RECEIPT_NAME = "braidledger_receipt.json"
CLAIM_BOUNDARY = (
    "Research workflow only: deterministic package, receipt, and coupon measurement plan; "
    "not flight-ready hardware, not certified material validation, not a standalone PUF."
)


@dataclass(frozen=True)
class CouponSample:
    sample_id: str
    seed_id: str
    copy_index: int
    target_part: str
    measurement_axis: str
    expected_measurements_csv: str


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _print_payload(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=_json_default))
        return

    print(
        f"{payload.get('title', 'SCBE foundry')}: {'OK' if payload.get('ok') else 'CHECK'}"
    )
    if "summary" in payload:
        print(payload["summary"])
    if "output_dir" in payload:
        print(f"output_dir: {payload['output_dir']}")
    if "receipt_path" in payload:
        print(f"receipt: {payload['receipt_path']}")
    if "plan_path" in payload:
        print(f"plan: {payload['plan_path']}")
    if payload.get("findings"):
        for finding in payload["findings"]:
            print(f"- {finding['severity']}: {finding['message']}")


def _receipt_scad_path(receipt_path: Path) -> Path:
    return receipt_path.parent / DEFAULT_SCAD_NAME


def build_package(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.out or args.output_dir or DEFAULT_OUTPUT_DIR
    seed = _seed_from_args(args)
    adapter = ManufacturingBraidAdapter(seed)
    package = adapter.export_full_package(output_dir, part_name=args.part)
    return {
        "schema_version": "scbe_foundry_package_v1",
        "title": "SCBE foundry package",
        "ok": True,
        "claim_boundary": CLAIM_BOUNDARY,
        "part_id": package.receipt["part_id"],
        "part_name": package.receipt["part_name"],
        "output_dir": package.scad_path.parent,
        "scad_path": package.scad_path,
        "receipt_path": package.receipt_path,
        "scad_sha256": package.receipt["scad_sha256"],
        "coeff_sha256": package.receipt["coeff_sha256"],
        "coefficient_count": package.receipt["coefficient_count"],
        "next_commands": [
            f"scbe foundry verify {package.receipt_path}",
            "scbe foundry plan-coupon "
            f"--part {json.dumps(args.part)} "
            f"--out {package.scad_path.parent / 'coupon_plan.json'}",
        ],
    }


def verify_receipt(receipt_path: Path) -> dict[str, Any]:
    receipt_path = receipt_path.resolve()
    findings: list[dict[str, str]] = []
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _verify_payload(
            False,
            receipt_path,
            [{"severity": "fail", "message": "receipt file not found"}],
        )
    except json.JSONDecodeError as exc:
        return _verify_payload(
            False,
            receipt_path,
            [{"severity": "fail", "message": f"invalid JSON: {exc}"}],
        )

    if receipt.get("schema_version") != "scbe_manufacturing_braid_package_v1":
        findings.append(
            {
                "severity": "fail",
                "message": "receipt schema is not scbe_manufacturing_braid_package_v1",
            }
        )

    scad_path = _receipt_scad_path(receipt_path)
    if not scad_path.exists():
        findings.append(
            {"severity": "fail", "message": f"expected SCAD file missing: {scad_path}"}
        )
    else:
        actual_hash = hashlib.sha256(scad_path.read_bytes()).hexdigest()
        if actual_hash != receipt.get("scad_sha256"):
            findings.append(
                {"severity": "fail", "message": "SCAD hash does not match receipt"}
            )

    braid = receipt.get("braid_verification") or {}
    if (
        braid.get("chain_ok") is not True
        or braid.get("tube_ok") is not True
        or braid.get("bad_index") is not None
    ):
        findings.append(
            {
                "severity": "fail",
                "message": "BraidLedger verification fields are not clean",
            }
        )

    coeff_bounds = receipt.get("coefficient_bounds")
    if coeff_bounds != [-4, 4]:
        findings.append(
            {
                "severity": "warn",
                "message": "coefficient bounds are not the expected [-4, 4]",
            }
        )

    if receipt.get("coefficient_count") != 256:
        findings.append({"severity": "fail", "message": "coefficient_count is not 256"})

    if not receipt.get("signature", {}).get("signature_sha3_512"):
        findings.append({"severity": "fail", "message": "signature hash missing"})

    if not findings:
        findings.append(
            {
                "severity": "pass",
                "message": "receipt, SCAD hash, coefficients, and braid fields verify",
            }
        )

    return _verify_payload(
        not any(finding["severity"] == "fail" for finding in findings),
        receipt_path,
        findings,
        receipt=receipt,
        scad_path=scad_path,
    )


def _verify_payload(
    ok: bool,
    receipt_path: Path,
    findings: list[dict[str, str]],
    *,
    receipt: dict[str, Any] | None = None,
    scad_path: Path | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "scbe_foundry_verify_v1",
        "title": "SCBE foundry verify",
        "ok": ok,
        "claim_boundary": CLAIM_BOUNDARY,
        "receipt_path": receipt_path,
        "scad_path": scad_path or _receipt_scad_path(receipt_path),
        "part_id": (receipt or {}).get("part_id"),
        "findings": findings,
    }


def build_coupon_plan(args: argparse.Namespace) -> dict[str, Any]:
    seed_count = int(args.seeds)
    copies = int(args.copies)
    if seed_count <= 0:
        raise ValueError("--seeds must be positive")
    if copies <= 0:
        raise ValueError("--copies must be positive")

    samples: list[CouponSample] = []
    for seed_index in range(seed_count):
        seed_id = f"{args.seed_prefix}-{seed_index:03d}"
        for copy_index in range(copies):
            samples.append(
                CouponSample(
                    sample_id=f"{seed_id}-copy-{copy_index:02d}",
                    seed_id=seed_id,
                    copy_index=copy_index,
                    target_part=args.part,
                    measurement_axis=args.measurement,
                    expected_measurements_csv=(
                        "device_id,seed_id,fabrication_id,read_id,response_1,response_2,response_3"
                    ),
                )
            )

    payload: dict[str, Any] = {
        "schema_version": "scbe_foundry_coupon_plan_v1",
        "title": "SCBE foundry coupon plan",
        "ok": True,
        "claim_boundary": CLAIM_BOUNDARY,
        "target_part": args.part,
        "measurement_axis": args.measurement,
        "seed_count": seed_count,
        "copies_per_seed": copies,
        "sample_count": len(samples),
        "samples": [asdict(sample) for sample in samples],
        "null_gates": [
            "same-seed copies must cluster tighter than different-seed parts",
            "shuffled-topology or shuffled-label null must not reproduce the separation",
            "measurement noise floor must sit below inter-seed separation",
            "negative result parks the claim instead of promoting it",
        ],
        "recommended_first_measurements": [
            "phone/contact-mic tap impulse response",
            "dimensional scan or caliper ridge measurements",
            "thermal propagation only after cheap vibration/dimensional signal appears",
        ],
    }

    if args.out:
        out_path = args.out.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
        payload["plan_path"] = out_path
    return payload


def run_workflow(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = (args.out or DEFAULT_OUTPUT_DIR).resolve()
    package_dir = output_dir / "package"
    package_args = argparse.Namespace(
        master_seed=args.master_seed,
        master_seed_hex=args.master_seed_hex,
        out=package_dir,
        output_dir=package_dir,
        part=args.part,
    )
    package_payload = build_package(package_args)
    verify_payload = verify_receipt(Path(package_payload["receipt_path"]))
    plan_args = argparse.Namespace(
        part=args.part,
        measurement=args.measurement,
        seeds=args.seeds,
        copies=args.copies,
        seed_prefix=args.seed_prefix,
        out=output_dir / "coupon_plan.json",
    )
    plan_payload = build_coupon_plan(plan_args)
    return {
        "schema_version": "scbe_foundry_workflow_v1",
        "title": "SCBE foundry workflow",
        "ok": bool(
            package_payload["ok"] and verify_payload["ok"] and plan_payload["ok"]
        ),
        "claim_boundary": CLAIM_BOUNDARY,
        "summary": "seed -> package -> verify -> coupon plan",
        "output_dir": output_dir,
        "package": package_payload,
        "verify": verify_payload,
        "coupon_plan": {
            "plan_path": plan_payload.get("plan_path"),
            "sample_count": plan_payload["sample_count"],
            "seed_count": plan_payload["seed_count"],
            "copies_per_seed": plan_payload["copies_per_seed"],
            "measurement_axis": plan_payload["measurement_axis"],
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    package = sub.add_parser(
        "package", help="Generate deterministic OpenSCAD + receipt package"
    )
    package.add_argument("--master-seed", default="", help="UTF-8 master seed")
    package.add_argument(
        "--master-seed-hex", default="", help="Hex master seed; overrides --master-seed"
    )
    package.add_argument(
        "--seed", dest="master_seed", default="", help="Alias for --master-seed"
    )
    package.add_argument(
        "--out", "--output-dir", dest="out", type=Path, default=DEFAULT_OUTPUT_DIR
    )
    package.add_argument(
        "--part", "--part-name", dest="part", default="Dual-Nodal Dynamo Core"
    )
    package.add_argument("--json", action="store_true")
    package.set_defaults(func=lambda ns: build_package(ns))

    verify = sub.add_parser(
        "verify", help="Verify package receipt against local SCAD file"
    )
    verify.add_argument("receipt", type=Path, help="Path to braidledger_receipt.json")
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(func=lambda ns: verify_receipt(ns.receipt))

    plan = sub.add_parser(
        "plan-coupon", help="Create a null-gated physical coupon measurement plan"
    )
    plan.add_argument("--part", default="Dual-Nodal Dynamo Core")
    plan.add_argument(
        "--measurement",
        default="vibration",
        choices=["vibration", "dimensional", "thermal", "rf", "impedance"],
    )
    plan.add_argument("--seeds", type=int, default=5)
    plan.add_argument("--copies", type=int, default=3)
    plan.add_argument("--seed-prefix", default="foundry-seed")
    plan.add_argument("--out", type=Path)
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(func=lambda ns: build_coupon_plan(ns))

    workflow = sub.add_parser(
        "workflow", help="Run package -> verify -> coupon-plan in one command"
    )
    workflow.add_argument("--master-seed", default="", help="UTF-8 master seed")
    workflow.add_argument(
        "--master-seed-hex", default="", help="Hex master seed; overrides --master-seed"
    )
    workflow.add_argument(
        "--seed", dest="master_seed", default="", help="Alias for --master-seed"
    )
    workflow.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_DIR)
    workflow.add_argument("--part", default="Dual-Nodal Dynamo Core")
    workflow.add_argument(
        "--measurement",
        default="vibration",
        choices=["vibration", "dimensional", "thermal", "rf", "impedance"],
    )
    workflow.add_argument("--seeds", type=int, default=5)
    workflow.add_argument("--copies", type=int, default=3)
    workflow.add_argument("--seed-prefix", default="foundry-seed")
    workflow.add_argument("--json", action="store_true")
    workflow.set_defaults(func=lambda ns: run_workflow(ns))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    try:
        payload = args.func(args)
    except ValueError as exc:
        print(f"scbe foundry: {exc}")
        return 2
    _print_payload(payload, args.json)
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

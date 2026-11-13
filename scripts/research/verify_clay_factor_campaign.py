"""Independently replay one Clay multi-view factor campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.clay_factor_campaign_verifier import (  # noqa: E402
    FactorCampaignVerificationError,
    verify_factor_campaign,
)


def _write_result(path: Path, value: Mapping[str, Any], *, allow_overwrite: bool) -> None:
    if path.exists() and not allow_overwrite:
        raise FactorCampaignVerificationError(f"refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--clay-source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--allow-running",
        action="store_true",
        help="Audit only horse receipts that were atomically complete at scan time.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = verify_factor_campaign(
        args.campaign,
        clay_source_dir=args.clay_source_dir,
        allow_running=args.allow_running,
    )
    default_name = (
        "INDEPENDENT_PARTIAL_INFERENCE_AUDIT.json"
        if args.allow_running and result["campaign_state"] == "RUNNING"
        else "INDEPENDENT_INFERENCE_AUDIT.json"
    )
    output = (args.output or Path(args.campaign).resolve() / default_name).resolve()
    _write_result(
        output,
        result,
        allow_overwrite=result["campaign_state"] == "RUNNING",
    )
    print(
        json.dumps(
            {
                "status": (
                    "PASS_PARTIAL_INDEPENDENT_INFERENCE_NO_SELECTION"
                    if result["campaign_state"] == "RUNNING"
                    else "PASS_COMPLETE_INDEPENDENT_INFERENCE_NO_PROMOTION"
                ),
                "output": str(output),
                "verification_sha256": result["verification_sha256"],
                "horses": result["verified_horses"],
                "expected_horses": result["expected_horses"],
                "prediction_ledgers": len(result["prediction_receipts"]),
                "verdict": result["verdict"],
                "promotion_authorized": False,
                "partial_unfreeze_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

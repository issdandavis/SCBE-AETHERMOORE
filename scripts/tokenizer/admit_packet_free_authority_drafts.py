#!/usr/bin/env python3
"""Compile reviewed packet-free drafts into provenance-admitted authorities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.prime_token_packet_free_admission import (  # noqa: E402
    admit_packet_free_authority_drafts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft-dir", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--supersedes-receipt", action="append", default=[], type=Path)
    args = parser.parse_args()
    receipt = admit_packet_free_authority_drafts(
        draft_dir=args.draft_dir,
        decision_ledger_path=args.decisions,
        output_dir=args.output,
        superseded_receipts=args.supersedes_receipt,
    )
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

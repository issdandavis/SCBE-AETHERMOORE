"""Fail-soft AlphaGenome connector probe for SCBE science lanes.

This script does not make a live API call by default.  It checks whether the
client package is importable, whether a local key is present, and whether the
caller explicitly acknowledged the non-commercial/API terms boundary before any
future live use.  The output is a compact receipt that can be routed into the
SCBE data-science and chemistry roadmaps.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

ENV_KEYS = ("ALPHAGENOME_API_KEY", "ALPHA_GENOME_API_KEY")
PACKAGE = "alphagenome"
DATA_MODULE = "alphagenome.data.genome"
MODEL_MODULE = "alphagenome.models.dna_client"


@dataclass(frozen=True)
class AlphaGenomeProbeReceipt:
    schema_version: str
    package_installed: bool
    import_ok: bool
    key_present: bool
    key_fingerprint: str | None
    env_key_name: str | None
    live_requested: bool
    terms_acknowledged: bool
    live_allowed: bool
    live_status: str
    route_decision: str
    blocked_reason: str
    source_urls: list[str]
    retrieved_at: str
    connector_contract: dict[str, Any]


def _fingerprint(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:12]


def resolve_key(env: dict[str, str] | None = None) -> tuple[str | None, str | None]:
    source = os.environ if env is None else env
    for key_name in ENV_KEYS:
        value = source.get(key_name, "").strip()
        if value:
            return key_name, value
    return None, None


def package_installed() -> bool:
    return importlib.util.find_spec(PACKAGE) is not None


def import_client_modules() -> tuple[bool, str]:
    try:
        importlib.import_module(DATA_MODULE)
        importlib.import_module(MODEL_MODULE)
        return True, ""
    except Exception as exc:  # pragma: no cover - exact import failure is environment-specific.
        return False, f"{type(exc).__name__}: {exc}"


def build_receipt(live: bool = False, ack_terms: bool = False) -> dict[str, Any]:
    env_key_name, key = resolve_key()
    installed = package_installed()
    import_ok, import_error = import_client_modules() if installed else (False, "package_not_installed")

    key_present = key is not None
    live_allowed = bool(live and ack_terms and key_present and import_ok)
    blocked_reason = ""
    live_status = "not_requested"
    route_decision = "HOLD_SETUP"

    if live:
        if not ack_terms:
            blocked_reason = "live_probe_requires_explicit_terms_ack"
            live_status = "blocked_terms_ack_required"
        elif not key_present:
            blocked_reason = "missing_alphagenome_api_key"
            live_status = "blocked_missing_key"
        elif not import_ok:
            blocked_reason = import_error or "alphagenome_import_failed"
            live_status = "blocked_import_failed"
        else:
            # Intentionally no live request yet.  A future version should place
            # the actual request behind a tiny fixture and a separate quota gate.
            live_status = "ready_for_future_live_fixture"
            route_decision = "ALLOW_WITH_TERMS_AND_QUOTA_GATE"
    elif installed and import_ok:
        route_decision = "ALLOW_LOCAL_CLIENT_READY"
    elif installed:
        blocked_reason = import_error
    else:
        blocked_reason = "pip_install_or_local_clone_required"

    receipt = AlphaGenomeProbeReceipt(
        schema_version="scbe_alphagenome_probe_v1",
        package_installed=installed,
        import_ok=import_ok,
        key_present=key_present,
        key_fingerprint=_fingerprint(key) if key else None,
        env_key_name=env_key_name,
        live_requested=live,
        terms_acknowledged=ack_terms,
        live_allowed=live_allowed,
        live_status=live_status,
        route_decision=route_decision,
        blocked_reason=blocked_reason,
        source_urls=[
            "https://github.com/google-deepmind/alphagenome",
            "https://www.alphagenomedocs.com/installation.html",
        ],
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        connector_contract={
            "primary_lane": "science_probe",
            "neighbor_lanes": ["genomics", "chemistry_roadmap", "data_science_agent"],
            "default_mode": "no_live_api_call",
            "required_for_live": ["api_key_present", "terms_acknowledged", "quota_gate", "non_commercial_boundary"],
            "training_data_policy": "do_not_store_api_outputs_as_training_data_without_license_review",
            "env_keys": list(ENV_KEYS),
            "expected_modules": [DATA_MODULE, MODEL_MODULE],
        },
    )
    return asdict(receipt)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Request a future live-probe path; no live call is made yet.")
    parser.add_argument("--ack-terms", action="store_true", help="Acknowledge AlphaGenome terms boundary for live probing.")
    parser.add_argument("--json", action="store_true", help="Print JSON receipt.")
    args = parser.parse_args()

    receipt = build_receipt(live=args.live, ack_terms=args.ack_terms)
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        print(f"AlphaGenome package installed: {receipt['package_installed']}")
        print(f"AlphaGenome imports ok: {receipt['import_ok']}")
        print(f"AlphaGenome key present: {receipt['key_present']}")
        print(f"Route decision: {receipt['route_decision']}")
        if receipt["blocked_reason"]:
            print(f"Blocked reason: {receipt['blocked_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Local Google Play readiness gate for the AetherBrowse Android bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_AAB = REPO / "kindle-app" / "android" / "app" / "build" / "outputs" / "bundle" / "release" / "app-release.aab"
DEFAULT_LISTING = REPO / "kindle-app" / "store-listing-aetherbrowse.md"
DEFAULT_PRIVACY = REPO / "PRIVACY.md"
DEFAULT_BUILD_GRADLE = REPO / "kindle-app" / "android" / "app" / "build.gradle"
DEFAULT_OUT = REPO / "artifacts" / "play_store_readiness" / "latest.json"
DEFAULT_MD = REPO / "artifacts" / "play_store_readiness" / "latest.md"
EXPECTED_PACKAGE = "com.issdandavis.aetherbrowse"


@dataclass(frozen=True)
class Finding:
    gate: str
    decision: str
    detail: str
    evidence: dict[str, Any]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def gate_artifact(aab: Path) -> Finding:
    if not aab.exists():
        return Finding("artifact", "FAIL", "AAB artifact is missing.", {"path": str(aab)})
    size = aab.stat().st_size
    if size < 1_000_000:
        return Finding("artifact", "FAIL", "AAB artifact is too small to be a real release bundle.", {"path": str(aab), "bytes": size})
    return Finding(
        "artifact",
        "PASS",
        "AAB artifact exists and has release-sized content.",
        {"path": str(aab), "bytes": size, "sha256": _sha256(aab)},
    )


def gate_listing(listing: Path, expected_package: str) -> Finding:
    if not listing.exists():
        return Finding("listing", "FAIL", "Store listing draft is missing.", {"path": str(listing)})
    text = _read(listing)
    required = ["Privacy Policy URL", "Support URL", "Short Description", "Full Description", expected_package]
    missing = [item for item in required if item not in text]
    asset_markers = ["Feature graphic", "Phone screenshots", "7-inch tablet", "10-inch tablet"]
    missing_assets = [item for item in asset_markers if item not in text]
    decision = "PASS" if not missing and not missing_assets else "HOLD"
    detail = "Store listing has required policy, support, package, and asset checklist fields."
    if missing or missing_assets:
        detail = "Store listing needs field or asset checklist cleanup before upload."
    return Finding(
        "listing",
        decision,
        detail,
        {"path": str(listing), "missing_fields": missing, "missing_asset_markers": missing_assets},
    )


def gate_privacy(privacy: Path) -> Finding:
    if not privacy.exists():
        return Finding("privacy", "FAIL", "Privacy policy file is missing.", {"path": str(privacy)})
    text = _read(privacy)
    required = ["API Keys", "Third-Party AI Providers", "Local Storage", "Data Deletion", "Contact"]
    missing = [item for item in required if item not in text]
    has_placeholder = "TODO" in text or "TBD" in text
    decision = "PASS" if not missing and not has_placeholder else "HOLD"
    return Finding(
        "privacy",
        decision,
        "Privacy policy covers mobile app data handling fields." if decision == "PASS" else "Privacy policy needs review.",
        {"path": str(privacy), "missing_sections": missing, "has_placeholder": has_placeholder},
    )


def gate_native_config(build_gradle: Path, expected_package: str) -> Finding:
    if not build_gradle.exists():
        return Finding("native_config", "FAIL", "Android build.gradle is missing.", {"path": str(build_gradle)})
    text = _read(build_gradle)
    required = [
        "AETHERCODE_APP_VARIANT",
        expected_package,
        "versionCode",
        "versionName",
        "signingConfigs",
        "bundleRelease",
    ]
    missing = [item for item in required if item not in text]
    # bundleRelease is a Gradle task, not always literal source text; do not fail if all other native fields exist.
    if "bundleRelease" in missing:
        missing.remove("bundleRelease")
    decision = "PASS" if not missing else "FAIL"
    return Finding(
        "native_config",
        decision,
        "Native Gradle config contains package variant, version, and release signing hooks."
        if decision == "PASS"
        else "Native Gradle config is missing release-critical fields.",
        {"path": str(build_gradle), "expected_package": expected_package, "missing_fields": missing},
    )


def gate_signing_hint() -> Finding:
    # Do not read or print signing.local.properties. Only check ignored path convention.
    gitignore = REPO / "kindle-app" / "android" / ".gitignore"
    if not gitignore.exists():
        return Finding("signing_secret_boundary", "FAIL", "Android .gitignore is missing.", {"path": str(gitignore)})
    text = _read(gitignore)
    required = ["*.jks", "*.keystore", "signing.local.properties"]
    missing = [item for item in required if item not in text]
    decision = "PASS" if not missing else "FAIL"
    return Finding(
        "signing_secret_boundary",
        decision,
        "Signing secret file patterns are ignored by Git."
        if decision == "PASS"
        else "Signing secret ignore patterns are incomplete.",
        {"path": str(gitignore), "missing_patterns": missing},
    )


def run_gate(
    *,
    aab: Path = DEFAULT_AAB,
    listing: Path = DEFAULT_LISTING,
    privacy: Path = DEFAULT_PRIVACY,
    build_gradle: Path = DEFAULT_BUILD_GRADLE,
    expected_package: str = EXPECTED_PACKAGE,
) -> dict[str, Any]:
    findings = [
        gate_artifact(aab),
        gate_listing(listing, expected_package),
        gate_privacy(privacy),
        gate_native_config(build_gradle, expected_package),
        gate_signing_hint(),
    ]
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.decision] = counts.get(finding.decision, 0) + 1
    decision = "PASS" if counts.get("FAIL", 0) == 0 and counts.get("HOLD", 0) == 0 else "HOLD"
    if counts.get("FAIL", 0):
        decision = "FAIL"
    return {
        "schema_version": "scbe_play_store_readiness_gate_v1",
        "decision": decision,
        "expected_package": expected_package,
        "counts": counts,
        "findings": [
            {
                "gate": finding.gate,
                "decision": finding.decision,
                "detail": finding.detail,
                "evidence": finding.evidence,
            }
            for finding in findings
        ],
        "next_required": [
            "verify release build on emulator or physical device",
            "capture Play Store screenshots and feature graphic",
            "review final listing claims against packaged UI",
        ],
    }


def write_report(report: dict[str, Any], out: Path, md: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    lines = [
        "# Play Store Readiness Gate",
        "",
        f"Decision: `{report['decision']}`",
        f"Expected package: `{report['expected_package']}`",
        "",
        "## Findings",
        "",
    ]
    for finding in report["findings"]:
        lines.append(f"- `{finding['gate']}`: `{finding['decision']}` - {finding['detail']}")
    lines.extend(["", "## Next Required", ""])
    lines.extend(f"- {item}" for item in report["next_required"])
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aab", type=Path, default=DEFAULT_AAB)
    parser.add_argument("--listing", type=Path, default=DEFAULT_LISTING)
    parser.add_argument("--privacy", type=Path, default=DEFAULT_PRIVACY)
    parser.add_argument("--build-gradle", type=Path, default=DEFAULT_BUILD_GRADLE)
    parser.add_argument("--expected-package", default=EXPECTED_PACKAGE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_gate(
        aab=args.aab,
        listing=args.listing,
        privacy=args.privacy,
        build_gradle=args.build_gradle,
        expected_package=args.expected_package,
    )
    if args.write:
        write_report(report, args.out, args.md)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(f"[play-store] decision={report['decision']} package={report['expected_package']}")
        if args.write:
            print(f"[play-store] json={args.out}")
            print(f"[play-store] markdown={args.md}")
    return 0 if report["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Traditional security controls for local artifact triage.

These checks are deliberately boring and useful: hash reputation, extension
policy, magic-byte mismatch, EICAR test string, path zone, archive risk, and
high-entropy executable payloads. The module never executes the target file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = REPO_ROOT / "config" / "security" / "traditional_security_policy.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "security" / "traditional_layers"
SCHEMA_VERSION = "scbe_traditional_security_layers_v1"
EICAR_ASCII = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
ALLOWED_PATH_ROOTS = tuple(
    root.resolve()
    for root in (
        REPO_ROOT,
        Path.home(),
        Path(tempfile.gettempdir()),
    )
)


@dataclass(frozen=True)
class ControlHit:
    control: str
    severity: str
    weight: int
    message: str


@dataclass
class TraditionalSecurityReport:
    schema: str
    artifact_path: str
    artifact_sha256: str
    created_at_utc: str
    size_bytes: int
    extension: str
    magic_kind: str
    entropy: float
    decision: str
    risk_score: int
    controls: list[ControlHit] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_local_path(path: Path, *, must_exist: bool = False) -> Path:
    """Resolve a caller-supplied path and enforce local allowed roots.

    The security layer is a local artifact triage tool. It can inspect files in
    the repo, the user's profile, or the OS temp tree used by tests, but it must
    not let API/CLI input become an arbitrary filesystem path expression.
    """
    resolved = path.expanduser().resolve(strict=must_exist)
    if not any(_is_relative_to(resolved, root) for root in ALLOWED_PATH_ROOTS):
        allowed = ", ".join(str(root) for root in ALLOWED_PATH_ROOTS)
        raise ValueError(f"path is outside allowed local roots: {resolved} (allowed: {allowed})")
    return resolved


def resolve_local_file(path: Path) -> Path:
    resolved = resolve_local_path(path, must_exist=True)
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return resolved


def resolve_local_output_dir(path: Path) -> Path:
    return resolve_local_path(path, must_exist=False)


def public_path(path: Path) -> str:
    raw = str(resolve_local_path(path, must_exist=False))
    replacements = {
        str(REPO_ROOT): "%REPO%",
        str(Path.home()): "%USERPROFILE%",
    }
    out = raw
    for source, replacement in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        out = out.replace(source, replacement)
    return out


def sha256_file(path: Path) -> str:
    path = resolve_local_file(path)
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    total = len(data)
    value = 0.0
    for count in counts:
        if count:
            p = count / total
            value -= p * math.log2(p)
    return round(value, 4)


def magic_kind(data: bytes) -> str:
    if data.startswith(b"MZ"):
        return "pe_binary"
    if data.startswith(b"\x7fELF"):
        return "elf_binary"
    if data.startswith(b"PK\x03\x04"):
        return "zip_archive"
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "ole_document"
    if data.startswith(b"#!"):
        return "script_shebang"
    if all(byte in (9, 10, 13) or 32 <= byte <= 126 for byte in data[:4096]):
        return "text"
    return "unknown_binary"


def load_policy(path: Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    path = resolve_local_path(path, must_exist=False)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _is_trusted_repo_path(path: Path, policy: dict[str, Any]) -> bool:
    try:
        rel = path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return False
    first = rel.parts[0] if rel.parts else ""
    return first in set(policy.get("trusted_repo_prefixes", []))


def evaluate_artifact(
    path: Path, policy_path: Path = DEFAULT_POLICY_PATH, max_bytes: int = 5_000_000
) -> TraditionalSecurityReport:
    path = resolve_local_file(path)
    policy_path = resolve_local_path(policy_path, must_exist=False)
    policy = load_policy(policy_path)
    data = path.read_bytes()
    scanned = data[:max_bytes]
    digest = sha256_file(path)
    ext = path.suffix.lower()
    kind = magic_kind(scanned)
    ent = entropy(scanned)
    controls: list[ControlHit] = []

    blocked = {str(item).lower() for item in policy.get("blocked_sha256", [])}
    allowed = {str(item).lower() for item in policy.get("allowed_sha256", [])}
    if digest.lower() in blocked:
        controls.append(
            ControlHit("hash_reputation_block", "CRITICAL", 50, "SHA-256 is present in the local blocklist.")
        )
    if digest.lower() in allowed:
        controls.append(ControlHit("hash_reputation_allow", "INFO", -8, "SHA-256 is present in the local allowlist."))

    high_risk_ext = set(policy.get("high_risk_extensions", []))
    archive_ext = set(policy.get("archive_extensions", []))
    if ext in high_risk_ext:
        controls.append(
            ControlHit("high_risk_extension", "HIGH", 18, f"Extension {ext} is executable or script-capable.")
        )
    if ext in archive_ext or kind == "zip_archive":
        controls.append(
            ControlHit("archive_payload", "MEDIUM", 10, "Archive-like payload requires unpacking controls.")
        )
    if EICAR_ASCII in scanned:
        controls.append(ControlHit("eicar_test_signature", "CRITICAL", 45, "EICAR antivirus test string detected."))
    if path.name.count(".") >= 2 and ext in high_risk_ext:
        controls.append(ControlHit("double_extension", "HIGH", 16, "High-risk double extension pattern."))
    if kind in {"pe_binary", "elf_binary"} and ext not in {".exe", ".dll", ".com", ".scr", ".so", ""}:
        controls.append(
            ControlHit(
                "magic_extension_mismatch", "HIGH", 18, f"Magic bytes show {kind} but extension is {ext or '<none>'}."
            )
        )
    if kind in {"pdf", "ole_document"} and b"/JavaScript" in scanned:
        controls.append(ControlHit("document_javascript", "HIGH", 18, "Document contains JavaScript marker."))
    if ent >= 7.2 and kind in {"pe_binary", "elf_binary", "unknown_binary"}:
        controls.append(
            ControlHit(
                "high_entropy_binary", "MEDIUM", 12, "Binary has high entropy; packed or encrypted content is possible."
            )
        )
    if path.stat().st_size > int(policy.get("max_review_size_bytes", 52_428_800)):
        controls.append(ControlHit("large_artifact", "MEDIUM", 8, "Artifact exceeds normal review size threshold."))

    rendered = str(path.resolve())
    if any(marker.lower() in rendered.lower() for marker in policy.get("untrusted_path_markers", [])):
        controls.append(
            ControlHit("untrusted_path_zone", "MEDIUM", 8, "Artifact path is in a download/temp-style zone.")
        )
    elif _is_trusted_repo_path(path, policy):
        controls.append(
            ControlHit("trusted_repo_path", "INFO", -4, "Artifact is under a configured repo source/test/docs path.")
        )

    score = max(0, sum(hit.weight for hit in controls))
    critical = any(hit.severity == "CRITICAL" for hit in controls)
    high_count = sum(1 for hit in controls if hit.severity == "HIGH")
    if critical or score >= 45:
        decision = "DENY"
    elif high_count or score >= 18:
        decision = "QUARANTINE"
    else:
        decision = "ALLOW"

    actions = [
        "Preserve SHA-256 and control hits with the artifact receipt.",
        "Do not execute the artifact while any traditional control is unresolved.",
    ]
    if decision in {"QUARANTINE", "DENY"}:
        actions.append("Require hash provenance, source explanation, and sandboxed inspection before execution.")
    if any(hit.control == "archive_payload" for hit in controls):
        actions.append("Unpack archives only in an isolated workspace and scan extracted members recursively.")

    return TraditionalSecurityReport(
        schema=SCHEMA_VERSION,
        artifact_path=public_path(path),
        artifact_sha256=digest,
        created_at_utc=now_utc(),
        size_bytes=path.stat().st_size,
        extension=ext,
        magic_kind=kind,
        entropy=ent,
        decision=decision,
        risk_score=score,
        controls=controls,
        recommended_actions=actions,
    )


def report_to_dict(report: TraditionalSecurityReport) -> dict[str, Any]:
    return {
        "schema": report.schema,
        "artifact_path": report.artifact_path,
        "artifact_sha256": report.artifact_sha256,
        "created_at_utc": report.created_at_utc,
        "size_bytes": report.size_bytes,
        "extension": report.extension,
        "magic_kind": report.magic_kind,
        "entropy": report.entropy,
        "decision": report.decision,
        "risk_score": report.risk_score,
        "controls": [asdict(hit) for hit in report.controls],
        "recommended_actions": report.recommended_actions,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = evaluate_artifact(args.artifact, policy_path=args.policy)
    payload = report_to_dict(report)
    args.output_dir = resolve_local_output_dir(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{report.artifact_sha256[:16]}.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"[traditional-security] {report.decision} score={report.risk_score} "
            f"kind={report.magic_kind} controls={len(report.controls)} report={public_path(out_path)}"
        )
    return 2 if report.decision == "DENY" else 1 if report.decision == "QUARANTINE" else 0


if __name__ == "__main__":
    raise SystemExit(main())

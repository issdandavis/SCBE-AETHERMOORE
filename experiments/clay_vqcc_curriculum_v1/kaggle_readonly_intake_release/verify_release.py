"""Verify the staged Kaggle packet and its launch-disabled admission."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PACKET = HERE / "packet"
MANIFEST = PACKET / "RELEASE_MANIFEST.json"


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def verify_packet() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("status") != "PREPARED_ONLY":
        raise RuntimeError("release manifest is not PREPARED_ONLY")
    rows = []
    for expected in manifest["files"]:
        path = PACKET / expected["path"]
        observed = {
            "path": expected["path"],
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        if observed != expected:
            raise RuntimeError(f"packet file differs: {observed}")
        rows.append(observed)
    observed_names = {path.name for path in PACKET.iterdir() if path.is_file()}
    expected_names = {row["path"] for row in rows} | {MANIFEST.name}
    if observed_names != expected_names:
        raise RuntimeError("packet inventory differs")
    content_set_sha256 = hashlib.sha256(canonical_json(rows)).hexdigest()
    if content_set_sha256 != manifest["content_set_sha256"]:
        raise RuntimeError("packet content-set hash differs")
    admission = json.loads((PACKET / "EXECUTION_ADMISSION.json").read_text(encoding="utf-8"))
    if admission.get("state") != "NOT_CONSUMED" or admission.get("execution_authorized") is not False:
        raise RuntimeError("packet is not launch-disabled")
    metadata = json.loads((PACKET / "kernel-metadata.json").read_text(encoding="utf-8"))
    if metadata.get("is_private") is not True or metadata.get("enable_internet") is not False:
        raise RuntimeError("packet is not private and offline")
    return {
        "status": "PASS_PREPARED_ONLY",
        "files": len(expected_names),
        "content_set_sha256": content_set_sha256,
        "release_manifest_sha256": sha256_file(MANIFEST),
        "admission_state": admission["state"],
        "execution_authorized": admission["execution_authorized"],
    }


if __name__ == "__main__":
    print(json.dumps(verify_packet(), sort_keys=True))

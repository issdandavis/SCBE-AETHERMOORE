"""Verify the clean Kaggle packet against its self-excluding release manifest."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PACKET = HERE / "packet"
MANIFEST = PACKET / "RELEASE_MANIFEST.json"


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = {}
    content_rows = []
    for row in manifest["files"]:
        path = PACKET / row["path"]
        observed = {
            "path": row["path"],
            "bytes": path.stat().st_size,
            "sha256": file_hash(path),
        }
        if observed != row:
            raise RuntimeError(f"packet file differs: {observed}")
        expected[row["path"]] = observed
        content_rows.append(observed)
    observed_files = {
        path.relative_to(PACKET).as_posix()
        for path in PACKET.rglob("*")
        if path.is_file()
    }
    if observed_files != {*expected, "RELEASE_MANIFEST.json"}:
        raise RuntimeError(f"packet inventory differs: {sorted(observed_files)}")
    digest = sha256(canonical_json(content_rows)).hexdigest()
    if digest != manifest["content_set_sha256"]:
        raise RuntimeError("content-set hash differs")
    admission = json.loads((PACKET / "EXECUTION_ADMISSION.json").read_text(encoding="utf-8"))
    if admission["state"] != "NOT_CONSUMED" or admission["execution_authorized"] is not False:
        raise RuntimeError("packet is not launch-disabled")
    print(
        json.dumps(
            {
                "status": "PASS",
                "files": len(expected) + 1,
                "content_set_sha256": digest,
                "release_manifest_sha256": file_hash(MANIFEST),
                "admission_state": admission["state"],
                "execution_authorized": admission["execution_authorized"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

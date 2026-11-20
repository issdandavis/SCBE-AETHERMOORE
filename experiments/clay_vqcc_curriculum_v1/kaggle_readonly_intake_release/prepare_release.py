"""Build an immutable Kaggle packet from the reviewed VQCC intake sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Sequence

from build_monolith import MONOLITH_NAME, render_monolith


HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE.parent
DEFAULT_OUTPUT = HERE / "packet"
SOURCE_FILES = (
    "CAMPAIGN_SPEC.json",
    "build_vqcc_split.py",
    "findings_task.py",
    "load_vqcc_corpus.py",
    "run_readonly_intake.py",
    "vqcc_task.py",
)
RELEASE_FILES = (
    "EXECUTION_ADMISSION.json",
    "kernel-metadata.json",
    "run_kaggle_readonly_intake.py",
)


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def build_packet(output: Path) -> dict[str, object]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite release packet: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        for name in SOURCE_FILES:
            shutil.copyfile(SOURCE_ROOT / name, staging / name)
        for name in RELEASE_FILES:
            shutil.copyfile(HERE / name, staging / name)
        (staging / MONOLITH_NAME).write_bytes(render_monolith())
        rows = []
        for path in sorted(staging.iterdir(), key=lambda item: item.name):
            if path.is_file():
                rows.append(
                    {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
                )
        manifest = {
            "schema": "clay.vqcc-readonly-intake.release-manifest.v1",
            "status": "PREPARED_ONLY",
            "files": rows,
            "content_set_sha256": hashlib.sha256(canonical_json(rows)).hexdigest(),
        }
        (staging / "RELEASE_MANIFEST.json").write_bytes(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
            + b"\n"
        )
        staging.rename(output)
        return manifest
    except BaseException:
        if staging.exists() and staging.parent == output.parent:
            shutil.rmtree(staging)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    manifest = build_packet(args.output)
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

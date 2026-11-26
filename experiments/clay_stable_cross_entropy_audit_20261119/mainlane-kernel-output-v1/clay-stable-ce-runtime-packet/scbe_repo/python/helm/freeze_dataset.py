"""freeze_dataset: make a verified-trajectory corpus immutable + provenance-stamped before training.

A dataset you are about to train on must be FROZEN: content-hashed so any later drift is detectable,
stamped with exactly how it was produced (models, task range, hidden-test policy, dedup rule, yield),
and copied to a hash-named backup so a branch reset / parallel-session cleanup cannot silently lose it.
The freeze manifest is small + tracked; the dataset itself stays gitignored (generated data).

    python -m python.helm.freeze_dataset training-data/sft/vtc_mbpp_refined.jsonl \
        --out docs/datasets/vtc_mbpp_refined.freeze.json --backup-dir training-data/sft/_frozen

Truth = the bytes on disk: the sha256 in the freeze manifest IS the dataset's identity. Train on the
hash, not the path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

SCHEMA = "vtc_freeze_manifest_v1"
HIDDEN_TEST_POLICY = (
    "Every record passed held-out HIDDEN MBPP asserts by execution (public_k seen during solving, "
    "the rest hidden). Rejection-sampled: unverified trajectories were discarded, never included."
)
DEDUP_RULE = "Deduped by task_id; when a task had both a clean and a repair trace, the REPAIR trace was kept."


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    """Streaming sha256 of a file's bytes -- the dataset's content identity."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _read_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def dataset_stats(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize a harvested corpus: grade split, per-model coverage, task range, repair count."""
    grades: Counter = Counter()
    models: Counter = Counter()
    repaired = 0
    task_ids: List[int] = []
    for r in records:
        meta = r.get("meta", {})
        grades[meta.get("grade", "ungraded")] += 1
        if meta.get("model"):
            models[meta["model"]] += 1
        if meta.get("repaired"):
            repaired += 1
        tid = meta.get("task_id")
        if isinstance(tid, int):
            task_ids.append(tid)
    return {
        "records": len(records),
        "station": grades.get("station", 0),
        "manager": grades.get("manager", 0),
        "repaired": repaired,
        "per_model": dict(models),
        "task_id_min": min(task_ids) if task_ids else None,
        "task_id_max": max(task_ids) if task_ids else None,
        "task_ids": sorted(set(task_ids)),
    }


def freeze(
    dataset_path: str | Path,
    out_path: Optional[str | Path] = None,
    backup_dir: Optional[str | Path] = None,
    now: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Hash + stat the dataset, fold in its harvest manifest if present, write a freeze manifest,
    and copy the dataset to a hash-named backup. `now` is passed in (no hidden clock) so the freeze
    is reproducible; if omitted the manifest records frozen_at=None and the caller should stamp it."""
    dataset = Path(dataset_path)
    if not dataset.exists():
        raise FileNotFoundError("dataset not found: %s" % dataset)
    digest = sha256_file(dataset)
    records = _read_jsonl(dataset)
    stats = dataset_stats(records)

    manifest: Dict[str, Any] = {
        "schema": SCHEMA,
        "dataset": str(dataset).replace("\\", "/"),
        "sha256": digest,
        "frozen_at": now,
        "hidden_test_policy": HIDDEN_TEST_POLICY,
        "dedup_rule": DEDUP_RULE,
        **stats,
    }
    # Fold in the harvest-time manifest (attempted / verified_rate / per_model) when it sits next to the data.
    harvest_manifest = dataset.with_suffix(".manifest.json")
    if harvest_manifest.exists():
        try:
            manifest["harvest_manifest"] = json.loads(harvest_manifest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    if extra:
        manifest.update(extra)

    backup_path: Optional[Path] = None
    if backup_dir is not None:
        bdir = Path(backup_dir)
        bdir.mkdir(parents=True, exist_ok=True)
        backup_path = bdir / ("%s.%s%s" % (dataset.stem, digest[:12], dataset.suffix))
        if not backup_path.exists():  # immutable: a given hash is written once, never overwritten
            shutil.copy2(dataset, backup_path)
        manifest["backup"] = str(backup_path).replace("\\", "/")

    if out_path is not None:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        manifest["freeze_manifest"] = str(out).replace("\\", "/")
    return manifest


def verify_freeze(manifest_path: str | Path) -> Dict[str, Any]:
    """Re-hash the dataset named in a freeze manifest and report whether it still matches (drift check)."""
    m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    dataset = Path(m["dataset"])
    if not dataset.exists():
        return {"ok": False, "reason": "dataset missing", "dataset": str(dataset)}
    current = sha256_file(dataset)
    return {"ok": current == m["sha256"], "expected": m["sha256"], "current": current, "dataset": str(dataset)}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-freeze", description="freeze + provenance-stamp a training corpus")
    ap.add_argument("dataset", help="path to the .jsonl corpus")
    ap.add_argument("--out", default=None, help="write the freeze manifest here (tracked provenance record)")
    ap.add_argument("--backup-dir", default=None, help="copy the dataset to a hash-named file here")
    ap.add_argument("--at", default=None, help="freeze timestamp (ISO string); recorded verbatim")
    ap.add_argument("--verify", action="store_true", help="treat 'dataset' as a freeze manifest and re-check its hash")
    a = ap.parse_args(list(argv) if argv is not None else None)

    if a.verify:
        res = verify_freeze(a.dataset)
        print("FREEZE VERIFY  %s" % ("MATCH" if res["ok"] else "DRIFT"))
        if not res["ok"]:
            print("  expected %s" % res.get("expected"))
            print("  current  %s" % res.get("current"))
            return 1
        return 0

    m = freeze(a.dataset, out_path=a.out, backup_dir=a.backup_dir, now=a.at)
    print("FROZEN  %s" % m["dataset"])
    print("  sha256     %s" % m["sha256"])
    print(
        "  records    %d  (station %d / manager %d, repaired %d)"
        % (m["records"], m["station"], m["manager"], m["repaired"])
    )
    print("  per_model  %s" % m["per_model"])
    print("  task range %s..%s" % (m["task_id_min"], m["task_id_max"]))
    if m.get("backup"):
        print("  backup     %s" % m["backup"])
    if m.get("freeze_manifest"):
        print("  manifest   %s" % m["freeze_manifest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

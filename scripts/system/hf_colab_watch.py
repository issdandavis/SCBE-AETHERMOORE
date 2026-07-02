#!/usr/bin/env python3
"""Watch SCBE Colab benchmark checkpoints from Hugging Face or a local result file.

Browser-free by design: Colab is disposable compute; the `results_*.json`
checkpoint is the source of truth.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPO_ID = "issdandavis/scbe-bench-results"
DEFAULT_RECEIPT_DIR = REPO_ROOT / "artifacts" / "colab_hf_watch"
EXPECTED_A_CELLS = 8
RESULT_RE = re.compile(r"^results_(\d{8})_(\d{6})\.json$")


@dataclass(frozen=True)
class ResultSource:
    path: Path
    name: str
    modified_at: datetime | None
    repo_id: str | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def stamp_for_file(name: str) -> datetime | None:
    match = RESULT_RE.match(name)
    if not match:
        return None
    return datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"result root must be a JSON object: {path}")
    return data


def latest_hf_result(repo_id: str) -> ResultSource:
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except Exception as exc:  # noqa: BLE001 - tool availability diagnostic
        raise SystemExit(f"huggingface_hub is required for HF reads: {exc}") from exc

    api = HfApi()
    names = [name for name in api.list_repo_files(repo_id=repo_id, repo_type="dataset") if RESULT_RE.match(name)]
    if not names:
        raise SystemExit(f"no results_*.json files found in HF dataset {repo_id}")

    latest_name = sorted(names, key=lambda name: stamp_for_file(name) or datetime.min.replace(tzinfo=timezone.utc))[-1]
    cached = Path(hf_hub_download(repo_id=repo_id, repo_type="dataset", filename=latest_name))
    modified_at = None
    try:
        modified_at = datetime.fromtimestamp(cached.stat().st_mtime, tz=timezone.utc)
    except OSError:
        pass
    return ResultSource(path=cached, name=latest_name, modified_at=modified_at, repo_id=repo_id)


def local_result(path: Path) -> ResultSource:
    if not path.is_file():
        raise SystemExit(f"result file not found: {path}")
    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return ResultSource(path=path, name=path.name, modified_at=modified_at)


def count_a_cells(result: dict[str, Any]) -> tuple[int, list[str]]:
    cells: list[str] = []
    a = result.get("A")
    if isinstance(a, dict):
        for model_name, per_lang in sorted(a.items()):
            if not isinstance(per_lang, dict):
                continue
            for lang in sorted(per_lang):
                cells.append(f"{model_name}:{lang}")
    return len(cells), cells


def classify_run_mode(a_count: int, has_b: bool, has_c: bool) -> str:
    if a_count == 0 and (has_b or has_c):
        return "bc_only"
    if a_count >= EXPECTED_A_CELLS and (has_b or has_c):
        return "a_plus_bc"
    if a_count:
        return "a_ceiling"
    return "unknown"


def stage_state(result: dict[str, Any], source: ResultSource, stale_minutes: float) -> dict[str, Any]:
    now = utc_now()
    a_count, a_cells = count_a_cells(result)
    has_b = isinstance(result.get("B"), dict)
    has_c = isinstance(result.get("C"), dict)
    has_errors = bool(result.get("errors"))
    run_mode = classify_run_mode(a_count, has_b, has_c)
    age_minutes = None
    if source.modified_at:
        age_minutes = round((now - source.modified_at).total_seconds() / 60, 2)
    stale = bool(age_minutes is not None and age_minutes >= stale_minutes)

    if has_errors:
        status = "error"
        action = "Read result['errors']; fix the notebook builder; stage a new notebook before browser work."
    elif run_mode == "bc_only" and has_b and has_c:
        status = "complete"
        action = "Run synthesis: report B precision/coverage and C adapter verdict; A came from a separate ceiling run."
    elif run_mode == "bc_only" and has_b:
        status = "stale_needs_c" if stale else "running_c"
        action = (
            "C did not land after B; inspect the Colab tab or run a C-only adapter verdict."
            if stale
            else "B landed; keep watching HF for C without touching the browser."
        )
    elif run_mode == "bc_only":
        status = "stale_needs_b" if stale else "running_b"
        action = (
            "B+C run has no B checkpoint; inspect the Colab tab before rerunning."
            if stale
            else "B+C run has started but has not pushed B yet; keep watching HF."
        )
    elif a_count < EXPECTED_A_CELLS:
        status = "stale_partial_a" if stale else "running_a"
        action = (
            "Run C:\\dev\\colab\\scbe_ceiling_gate_v5_fast.ipynb when awake; do not wait overnight."
            if stale
            else "Keep watching HF; do not touch the browser while checkpoints are moving."
        )
    elif not has_b:
        status = "needs_b"
        action = "Run v5-fast to complete the contrast gate; B is the trust-without-reading product measure."
    elif not has_c:
        status = "needs_c"
        action = "Run v5-fast or C-only adapter verdict; C settles base vs adapter."
    else:
        status = "complete"
        action = "Run synthesis: report B precision/coverage, C adapter verdict, then design the next powered run."

    return {
        "schema_version": "scbe_colab_hf_watch_v1",
        "ok": not has_errors,
        "checked_at": now.isoformat(),
        "source": {
            "name": source.name,
            "path": str(source.path),
            "repo_id": source.repo_id,
            "modified_at": source.modified_at.isoformat() if source.modified_at else None,
            "age_minutes": age_minutes,
        },
        "thresholds": {"stale_minutes": stale_minutes, "expected_a_cells": EXPECTED_A_CELLS},
        "state": {
            "status": status,
            "stale": stale,
            "run_mode": run_mode,
            "a_cells": a_count,
            "a_complete": a_count >= EXPECTED_A_CELLS,
            "a_cell_ids": a_cells,
            "b_complete": has_b,
            "c_complete": has_c,
            "has_errors": has_errors,
        },
        "next_action": action,
    }


def resolve_receipt_dir(path: Path) -> Path:
    resolved = path if path.is_absolute() else (REPO_ROOT / path).resolve()
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise SystemExit(f"receipt dir must stay inside repo root: {resolved}") from exc
    return resolved


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def write_receipt(payload: dict[str, Any], receipt_dir: Path) -> Path:
    receipt_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    path = receipt_dir / f"hf_watch_{stamp}.json"
    payload_with_path = {**payload, "receipt_path": rel(path)}
    path.write_text(json.dumps(payload_with_path, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    payload["receipt_path"] = rel(path)
    return path


def print_text(payload: dict[str, Any]) -> None:
    state = payload["state"]
    source = payload["source"]
    print(f"HF watch: {state['status']}")
    print(f"  source: {source['name']} age={source['age_minutes']} min")
    print(f"  A: {state['a_cells']}/{payload['thresholds']['expected_a_cells']}  B: {state['b_complete']}  C: {state['c_complete']}")
    print(f"  stale: {state['stale']}  errors: {state['has_errors']}")
    print(f"  next: {payload['next_action']}")
    if "receipt_path" in payload:
        print(f"  receipt: {payload['receipt_path']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Watch SCBE Colab HF checkpoint state without browser interaction.")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--file", type=Path, help="Read a local results_*.json file instead of HF.")
    parser.add_argument("--stale-minutes", type=float, default=45.0)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--write-receipt", action="store_true", help="Write a local watch receipt.")
    parser.add_argument("--receipt-dir", type=Path, default=DEFAULT_RECEIPT_DIR)
    args = parser.parse_args(argv)

    source = local_result(args.file.resolve()) if args.file else latest_hf_result(args.repo_id)
    payload = stage_state(load_json(source.path), source, args.stale_minutes)
    if args.write_receipt:
        write_receipt(payload, resolve_receipt_dir(args.receipt_dir))

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print_text(payload)

    return 2 if payload["state"]["status"] == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())

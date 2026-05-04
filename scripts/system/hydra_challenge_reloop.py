#!/usr/bin/env python3
"""Create the next HYDRA challenge loop from a compacted completion eval."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL = (
    REPO_ROOT
    / "artifacts"
    / "agent_context_vault"
    / "challenge_loop"
    / "eval"
    / "repo_ladder_validate_eval_latest.json"
)
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "agent_context_vault" / "challenge_loop" / "loops"
SCHEMA_VERSION = "scbe_hydra_challenge_reloop_v1"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256_json(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value).strip("-") or "challenge"


def _select_next_challenge(eval_payload: dict[str, Any]) -> str:
    source = eval_payload.get("source_challenge") or {}
    challenge_id = str(source.get("challenge_id", "repo_ladder_validate"))
    completion = float(eval_payload.get("completion_factor", 0.0) or 0.0)
    if completion >= 1.0 and challenge_id == "repo_ladder_validate":
        return "repo_ladder_level1"
    if completion >= 1.0 and challenge_id == "repo_ladder_level1":
        return "external_eval_validate"
    if challenge_id == "repo_ladder_level1":
        return "repo_ladder_validate"
    return challenge_id


def build_reloop_plan(
    *,
    eval_path: Path = DEFAULT_EVAL,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    execute_next: bool = False,
) -> dict[str, Any]:
    eval_payload = json.loads(eval_path.read_text(encoding="utf-8"))
    challenge_id = str((eval_payload.get("source_challenge") or {}).get("challenge_id", eval_path.stem))
    stamp = _utc_stamp()
    loop_id = f"loop-{_safe_name(challenge_id)}-{stamp}-{str(eval_payload.get('eval_hash', ''))[:8]}"
    loop_dir = output_root / loop_id
    loop_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = loop_dir / "temp_run_branch"
    temp_dir.mkdir(parents=True, exist_ok=True)
    next_challenge = _select_next_challenge(eval_payload)
    compact_core = {
        "schema_version": "scbe_hydra_compacted_completion_v1",
        "loop_id": loop_id,
        "source_eval_hash": eval_payload.get("eval_hash", ""),
        "source_challenge": eval_payload.get("source_challenge", {}),
        "completion_factor": eval_payload.get("completion_factor", 0.0),
        "residual": eval_payload.get("residual", 1.0),
        "step_completion": eval_payload.get("step_completion", {}),
        "next_challenge": next_challenge,
    }
    compact = {**compact_core, "compact_hash": _sha256_json(compact_core)}
    branch_id = f"tmp/{_safe_name(challenge_id)}/{compact['compact_hash'][:12]}"
    plan_core = {
        "schema_version": SCHEMA_VERSION,
        "loop_id": loop_id,
        "ephemeral_branch_id": branch_id,
        "uses_real_git_branch": False,
        "temp_dir": str(temp_dir),
        "source_eval": str(eval_path),
        "next_challenge": next_challenge,
        "execute_next": execute_next,
        "completion_semantics": "N(complete(t step for cN)): compact completed state, carry residual, start a new isolated loop.",
        "cleanup_policy": "temp directory may be deleted after report compaction; source repo is not reset or checked out.",
        "next_command": [
            sys.executable,
            "scripts/system/hydra_challenge_loop.py",
            "--challenge",
            next_challenge,
            "--output-root",
            str(loop_dir / "challenge"),
        ],
    }
    plan = {**plan_core, "plan_hash": _sha256_json(plan_core)}
    (loop_dir / "compacted_completion.json").write_text(
        json.dumps(compact, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (loop_dir / "next_loop_plan.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    shutil.copy2(eval_path, loop_dir / "source_eval.json")

    executed: dict[str, Any] | None = None
    if execute_next:
        proc = subprocess.run(
            plan["next_command"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=900,
            check=False,
        )
        executed = {
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "stdout_tail": proc.stdout[-3000:],
            "stderr_tail": proc.stderr[-3000:],
        }
        (loop_dir / "executed_next.json").write_text(
            json.dumps(executed, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8"
        )
    return {"plan": plan, "compact": compact, "executed_next": executed}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval", type=Path, default=DEFAULT_EVAL)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--execute-next", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = build_reloop_plan(eval_path=args.eval, output_root=args.output_root, execute_next=args.execute_next)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if not payload.get("executed_next") or payload["executed_next"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

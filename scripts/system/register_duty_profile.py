#!/usr/bin/env python3
"""Register or update model duty profiles for switchboard routing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = REPO_ROOT / "config" / "governance" / "model_duty_profiles.json"


def _split_csv(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def _parse_tongue_vector(raw: str) -> dict[str, float]:
    vector: dict[str, float] = {}
    if not raw.strip():
        return vector
    for part in raw.split(","):
        token = part.strip()
        if not token or "=" not in token:
            continue
        key, _, value = token.partition("=")
        key = key.strip().lower()
        if key not in {"ko", "av", "ru", "ca", "um", "dr"}:
            continue
        try:
            vector[key] = float(value.strip())
        except Exception:
            continue
    return vector


def main() -> int:
    parser = argparse.ArgumentParser(description="Register/update model duty profile.")
    parser.add_argument("--id", required=True, help="Duty profile id.")
    parser.add_argument("--provider", required=True, help="Provider name (gemini/openai/claude/ollama/...).")
    parser.add_argument("--model-id", required=True, help="Model id (or * wildcard).")
    parser.add_argument("--primary-task-types", default="", help="CSV task types.")
    parser.add_argument("--secondary-task-types", default="", help="CSV task types.")
    parser.add_argument("--primary-tags", default="", help="CSV tags.")
    parser.add_argument("--secondary-tags", default="", help="CSV tags.")
    parser.add_argument("--primary-bonus-pct", type=float, default=0.2)
    parser.add_argument("--secondary-bonus-pct", type=float, default=0.08)
    parser.add_argument("--spectrum-bonus-pct", type=float, default=0.12)
    parser.add_argument(
        "--tongue-vector",
        default="",
        help="CSV axis vector as ko=0.7,av=0.2,ru=0.6,ca=0.3,um=0.4,dr=0.5.",
    )
    parser.add_argument(
        "--idle-job",
        action="append",
        default=[],
        help="Idle job spec as id|task_type|max_cost|prompt (repeatable).",
    )
    args = parser.parse_args()

    data = {"version": "1.0.0", "profiles": []}
    if PROFILE_PATH.exists():
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data.get("profiles", []), list):
            data["profiles"] = []

    idle_jobs = []
    for spec in args.idle_job:
        parts = spec.split("|", 3)
        if len(parts) != 4:
            continue
        idle_jobs.append(
            {
                "id": parts[0].strip(),
                "task_type": parts[1].strip() or "general",
                "max_cost": parts[2].strip() or "cheap",
                "prompt": parts[3].strip(),
            }
        )

    profile = {
        "id": args.id,
        "provider": args.provider.strip().lower(),
        "model_id": args.model_id.strip(),
        "primary_task_types": _split_csv(args.primary_task_types),
        "secondary_task_types": _split_csv(args.secondary_task_types),
        "primary_tags": _split_csv(args.primary_tags),
        "secondary_tags": _split_csv(args.secondary_tags),
        "primary_bonus_pct": args.primary_bonus_pct,
        "secondary_bonus_pct": args.secondary_bonus_pct,
        "spectrum_bonus_pct": args.spectrum_bonus_pct,
        "tongue_vector": _parse_tongue_vector(args.tongue_vector),
        "idle_jobs": idle_jobs,
    }

    profiles = data["profiles"]
    replaced = False
    for i, existing in enumerate(profiles):
        if isinstance(existing, dict) and str(existing.get("id", "")) == args.id:
            profiles[i] = profile
            replaced = True
            break
    if not replaced:
        profiles.append(profile)

    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "profile_path": str(PROFILE_PATH),
                "profile_id": args.id,
                "action": "updated" if replaced else "created",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

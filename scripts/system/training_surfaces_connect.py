#!/usr/bin/env python3
"""One place to see how SCBE training connects to Colab, Kaggle, and Hugging Face.

Does not start paid jobs by default. Use this to verify auth, URLs, and copy-paste
commands for the surfaces you already pay for (Colab Pro, HF Pro, Kaggle).

Usage:
    python scripts/system/training_surfaces_connect.py
    python scripts/system/training_surfaces_connect.py --json
    python scripts/system/training_surfaces_connect.py --preflight
    python scripts/system/training_surfaces_connect.py --surface colab
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _colab_catalog() -> list[dict[str, Any]]:
    mod = _load_module(
        REPO_ROOT / "scripts" / "system" / "colab_workflow_catalog.py", "colab_catalog"
    )
    return mod.list_notebook_payloads()


def _kaggle_rounds() -> dict[str, str]:
    mod = _load_module(
        REPO_ROOT / "scripts" / "kaggle_auto" / "launch.py", "kaggle_launch"
    )
    rounds = getattr(mod, "ROUNDS", {})
    return {k: str(v.get("desc", "")) for k, v in rounds.items()}


def _kaggle_config() -> dict[str, str]:
    mod = _load_module(
        REPO_ROOT / "scripts" / "kaggle_auto" / "launch.py", "kaggle_launch"
    )
    return {
        "kaggle_user": str(getattr(mod, "KAGGLE_USER", "")),
        "kaggle_dataset": str(getattr(mod, "KAGGLE_DATASET", "")),
        "hf_dataset": str(getattr(mod, "HF_DATASET", "")),
    }


def _kaggle_json_config() -> dict[str, Any]:
    path = Path.home() / ".kaggle" / "kaggle.json"
    if not path.is_file():
        return {"present": False, "path": str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "present": True,
            "path": str(path),
            "username_set": bool(str(data.get("username", "")).strip()),
            "key_set": bool(str(data.get("key", "")).strip()),
        }
    except (json.JSONDecodeError, OSError) as exc:
        return {"present": True, "path": str(path), "error": str(exc)}


def _hf_hub_status() -> dict[str, Any]:
    token = os.environ.get("HF_TOKEN", "").strip()
    out: dict[str, Any] = {"HF_TOKEN_set": bool(token)}
    try:
        from huggingface_hub import HfApi  # type: ignore
    except Exception as exc:  # pragma: no cover
        out["import_error"] = str(exc)
        return out

    if not token:
        return out
    try:
        api = HfApi(token=token)
        who = api.whoami()
        if isinstance(who, dict):
            out["whoami"] = {
                "name": who.get("name"),
                "type": who.get("type"),
                "isPro": who.get("isPro"),
                "orgs": [
                    {"name": org.get("name"), "roleInOrg": org.get("roleInOrg")}
                    for org in who.get("orgs", [])
                    if isinstance(org, dict)
                ],
                "auth_role": (
                    ((who.get("auth") or {}).get("accessToken") or {}).get("role")
                    if isinstance(who.get("auth"), dict)
                    else None
                ),
            }
        else:
            out["whoami"] = str(who)
    except Exception as exc:
        out["whoami_error"] = str(exc)
    return out


def _run_preflight() -> dict[str, Any]:
    script = REPO_ROOT / "scripts" / "system" / "preflight_zero_cost_training.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload: dict[str, Any] = {
        "returncode": proc.returncode,
    }
    if proc.stdout.strip():
        try:
            payload["result"] = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload["result"] = None
    return payload


def build_manifest(*, run_preflight: bool) -> dict[str, Any]:
    colab = _colab_catalog()
    priority_order = (
        "zero-cost-local-0p5b",
        "scbe-finetune-free",
        "qlora-training",
        "coder-code-primaries",
    )
    priority_set = set(priority_order)
    by_name = {str(n.get("name")): n for n in colab}
    colab_priority = [by_name[k] for k in priority_order if k in by_name]
    colab_rest = [n for n in colab if str(n.get("name")) not in priority_set]

    manifest: dict[str, Any] = {
        "schema_version": "scbe_training_surfaces_connect_v1",
        "repo_root": str(REPO_ROOT),
        "colab": {
            "notebooks_total": len(colab),
            "recommended_first": colab_priority,
            "other_notebooks": colab_rest,
            "all_notebooks": colab,
            "open_zero_cost_url": next(
                (
                    n["colab_url"]
                    for n in colab
                    if n.get("name") == "zero-cost-local-0p5b"
                ),
                None,
            ),
        },
        "kaggle": {
            "config": _kaggle_config(),
            "credentials_file": _kaggle_json_config(),
            "rounds": _kaggle_rounds(),
            "cli_examples": {
                "preflight_dsl": "python scripts/kaggle_auto/launch.py --round dsl-synthesis-v3-fast --gpu t4 --ready",
                "launch_dsl": "npm run training:kaggle:dsl-v3-paid:launch",
                "status": "python scripts/kaggle_auto/launch.py --status",
            },
        },
        "huggingface": {
            "hub": _hf_hub_status(),
            "cli_examples": {
                "login": "hf auth login",
                "dispatch_coding_job": "npm run training:dispatch-coding-agent",
                "dataset_sync_narrow": (
                    "python scripts/system/cloud_storage_sync.py --target hf "
                    "--repo issdandavis/scbe-aethermoore-training-data --repo-type dataset "
                    '--include-only --include-glob "training-data/**/*.jsonl" --push --max-files 500'
                ),
                "jobs_uv": (
                    "hf jobs uv run --flavor l4x1 --detach path/to/your_train_script.py "
                    "# see Hugging Face Jobs docs; emit scripts via training profiles / dispatch_coding_agent_hf_job"
                ),
            },
        },
        "local_preflight": _run_preflight() if run_preflight else None,
        "npm_shortcuts": {
            "surfaces": "npm run training:surfaces",
            "preflight_zero_cost": "npm run training:preflight:zero-cost",
            "agentic_workbench": "npm run training:agentic-workbench",
            "consolidate": "python scripts/system/consolidate_ai_training.py",
        },
    }
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Colab / Kaggle / HF training surface connector"
    )
    parser.add_argument("--json", action="store_true", help="Print JSON manifest")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Include zero-cost dataset preflight (JSON sub-object)",
    )
    parser.add_argument(
        "--surface",
        choices=["all", "colab", "kaggle", "hf"],
        default="all",
        help="Show only one surface in text mode",
    )
    args = parser.parse_args()

    manifest = build_manifest(run_preflight=bool(args.preflight))

    if args.json:
        print(json.dumps(manifest, indent=2))
        return 0

    if args.surface == "colab":
        print("## Colab")
        for row in manifest["colab"]["recommended_first"]:
            print(f"- {row['name']}: {row['colab_url']}")
        return 0

    if args.surface == "kaggle":
        print("## Kaggle")
        print(json.dumps(manifest["kaggle"], indent=2))
        return 0

    if args.surface == "hf":
        print("## Hugging Face")
        print(json.dumps(manifest["huggingface"], indent=2))
        return 0

    print("# SCBE training surfaces (paid Colab + HF + Kaggle)\n")
    z = manifest["colab"].get("open_zero_cost_url")
    if z:
        print("## Zero-cost 0.5B Colab (recommended if local torch is blocked)")
        print(z)
        print()
    print("## Colab (priority notebooks)")
    for row in manifest["colab"]["recommended_first"]:
        print(f"- {row['name']}: {row['colab_url']}")
    print("\n## Kaggle")
    kc = manifest["kaggle"]["credentials_file"]
    print(
        f"  credentials: {'ok' if kc.get('present') and not kc.get('error') else 'missing or error'} ({kc.get('path')})"
    )
    print(f"  user (script default): {manifest['kaggle']['config'].get('kaggle_user')}")
    print(f"  example: {manifest['kaggle']['cli_examples']['preflight_dsl']}")
    print("\n## Hugging Face")
    hf = manifest["huggingface"]["hub"]
    print(f"  HF_TOKEN: {'set' if hf.get('HF_TOKEN_set') else 'not set'}")
    if hf.get("whoami"):
        w = hf["whoami"]
        if isinstance(w, dict):
            print(f"  whoami: {w.get('name', w)}")
        else:
            print(f"  whoami: {w}")
    elif hf.get("whoami_error"):
        print(f"  whoami_error: {hf['whoami_error']}")
    print(
        f"  dispatch job: {manifest['huggingface']['cli_examples']['dispatch_coding_job']}"
    )

    if args.preflight and manifest.get("local_preflight"):
        lp = manifest["local_preflight"]
        print("\n## Zero-cost preflight (dataset files)")
        print(f"  returncode: {lp.get('returncode')}")
        if isinstance(lp.get("result"), dict):
            print(
                f"  ok: {lp['result'].get('ok')} missing: {lp['result'].get('missing_count')}"
            )

    print(
        "\nFull machine-readable manifest: python scripts/system/training_surfaces_connect.py --json --preflight"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

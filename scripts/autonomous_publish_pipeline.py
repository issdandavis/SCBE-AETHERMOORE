#!/usr/bin/env python3
"""
Autonomous Publish Pipeline — the conveyor belt.

Takes governed training data through:
  1. AUDIT   — validate data integrity, schema compliance, governance coverage
  2. PACKAGE — bundle into train/test splits with dataset card
  3. REPORT  — generate governance report (what passed, what was quarantined)
  4. PUBLISH — push to HuggingFace Hub
  5. LOG     — record the publish event for audit trail

This is the M5 Mesh Foundry product in code form.
Run it, walk away, come back to a published dataset.

Usage:
    # Dry run (validate + package + report, no push)
    python scripts/autonomous_publish_pipeline.py --dry-run

    # Full publish
    python scripts/autonomous_publish_pipeline.py

    # Publish specific view
    python scripts/autonomous_publish_pipeline.py --view openai_chat

    # Custom repo
    python scripts/autonomous_publish_pipeline.py --repo-id issdandavis/my-dataset
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SFT_DIR = REPO_ROOT / "training-data" / "sft"
STATION_DIR = REPO_ROOT / "training" / "runs" / "station"
PUBLISH_LOG = REPO_ROOT / "artifacts" / "publish" / "publish_log.jsonl"

DEFAULT_REPO = "issdandavis/scbe-aethermoore-training-data"

# Available data views and their files
VIEWS = {
    "canonical":            SFT_DIR / "canonical_master.jsonl",
    "trl_conversation":     SFT_DIR / "derived_trl_conversation.jsonl",
    "trl_prompt_completion": SFT_DIR / "derived_trl_prompt_completion.jsonl",
    "openai_chat":          SFT_DIR / "derived_openai_chat.jsonl",
    "activation_cls":       SFT_DIR / "derived_activation_cls.jsonl",
    "governance_cls":       SFT_DIR / "derived_governance_cls.jsonl",
    "contrast_pairs":       SFT_DIR / "derived_contrast_pairs.jsonl",
    "station":              None,  # resolved dynamically to latest run
}

VALID_TONGUES = {"KO", "AV", "RU", "CA", "UM", "DR"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_jsonl(path: Path, limit: int = 0) -> list[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def count_lines(path: Path) -> int:
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def get_latest_station_run() -> Path | None:
    if not STATION_DIR.exists():
        return None
    runs = sorted(STATION_DIR.iterdir(), reverse=True)
    for run in runs:
        data = run / "training_data.jsonl"
        if data.exists():
            return data
    return None


# ---------------------------------------------------------------------------
# Phase 1: AUDIT
# ---------------------------------------------------------------------------

def audit_data(path: Path, view_name: str) -> dict[str, Any]:
    """Validate data integrity and schema compliance."""
    print(f"\n  AUDIT: {view_name} ({path.name})")

    total = count_lines(path)
    sample = load_jsonl(path, limit=2000)

    issues = []
    warnings = []

    # Schema checks
    if view_name in ("trl_conversation", "openai_chat"):
        for i, rec in enumerate(sample):
            if "messages" not in rec:
                issues.append(f"Record {i}: missing 'messages'")
            else:
                msgs = rec["messages"]
                roles = [m.get("role") for m in msgs]
                if "assistant" not in roles:
                    issues.append(f"Record {i}: no assistant message")
                for m in msgs:
                    if not m.get("content", "").strip():
                        issues.append(f"Record {i}: empty content in {m.get('role')}")

    elif view_name == "trl_prompt_completion":
        for i, rec in enumerate(sample):
            if not rec.get("prompt", "").strip():
                issues.append(f"Record {i}: empty prompt")
            if not rec.get("completion", "").strip():
                issues.append(f"Record {i}: empty completion")

    elif view_name == "canonical":
        for i, rec in enumerate(sample):
            for field in ("substrate", "activation", "permission"):
                if field not in rec:
                    issues.append(f"Record {i}: missing '{field}'")

    elif view_name in ("activation_cls", "governance_cls"):
        # These are messages-format classifiers
        for i, rec in enumerate(sample):
            if "messages" not in rec:
                issues.append(f"Record {i}: missing 'messages'")
            else:
                roles = {m.get("role") for m in rec["messages"]}
                if "assistant" not in roles:
                    issues.append(f"Record {i}: no assistant message")

    elif view_name == "station":
        empty_inst = sum(1 for r in sample if not r.get("instruction", "").strip())
        empty_out = sum(1 for r in sample if not r.get("output", "").strip())
        if empty_inst > len(sample) * 0.3:
            warnings.append(f"{empty_inst}/{len(sample)} sampled records have empty instructions")
        if empty_out > len(sample) * 0.3:
            warnings.append(f"{empty_out}/{len(sample)} sampled records have empty outputs")

    # Governance distribution
    gov_counts = Counter()
    tongue_counts = Counter()
    for rec in sample:
        gov = (rec.get("permission", {}).get("governance")
               or rec.get("governance", "ALLOW"))
        gov_counts[gov] += 1
        tongue = (rec.get("activation", {}).get("tongues_active", [None])[0]
                  if "activation" in rec
                  else rec.get("tongue", ""))
        if tongue:
            tongue_counts[tongue] += 1

    # Check for governance diversity in station data
    if view_name == "station" and len(gov_counts) < 2:
        warnings.append("Only one governance value — may lack diversity")

    result = {
        "view": view_name,
        "file": str(path),
        "total_records": total,
        "sampled": len(sample),
        "issues": issues[:20],  # cap at 20
        "warnings": warnings,
        "governance": dict(gov_counts),
        "tongues": dict(tongue_counts),
        "passed": len(issues) == 0,
    }

    status = "PASS" if result["passed"] else f"FAIL ({len(issues)} issues)"
    print(f"    Records: {total:,}")
    print(f"    Governance: {dict(gov_counts)}")
    print(f"    Status: {status}")
    if warnings:
        for w in warnings:
            print(f"    WARNING: {w}")
    if issues:
        for issue in issues[:5]:
            print(f"    ISSUE: {issue}")

    return result


# ---------------------------------------------------------------------------
# Phase 2: PACKAGE
# ---------------------------------------------------------------------------

def package_data(path: Path, view_name: str, seed: int = 42,
                 test_size: float = 0.05, max_rows: int = 0) -> dict[str, Any]:
    """Bundle data into train/test splits."""
    print(f"\n  PACKAGE: {view_name}")

    try:
        from datasets import Dataset
    except ImportError:
        print("    datasets package not installed — skipping packaging")
        return {"view": view_name, "packaged": False, "reason": "no datasets lib"}

    records = load_jsonl(path)
    if max_rows > 0:
        records = records[:max_rows]

    ds = Dataset.from_list(records)
    splits = ds.train_test_split(test_size=test_size, seed=seed)

    result = {
        "view": view_name,
        "packaged": True,
        "total": len(records),
        "train": len(splits["train"]),
        "test": len(splits["test"]),
        "columns": ds.column_names,
        "splits": splits,
    }

    print(f"    Total: {result['total']:,}")
    print(f"    Train: {result['train']:,} / Test: {result['test']:,}")
    print(f"    Columns: {len(result['columns'])}")

    return result


# ---------------------------------------------------------------------------
# Phase 3: REPORT
# ---------------------------------------------------------------------------

def generate_report(audits: list[dict], packages: list[dict],
                    repo_id: str) -> str:
    """Generate a governance report / dataset card."""
    total_records = sum(a["total_records"] for a in audits)
    all_passed = all(a["passed"] for a in audits)
    all_warnings = []
    for a in audits:
        all_warnings.extend(a.get("warnings", []))

    # Aggregate governance
    gov_total = Counter()
    tongue_total = Counter()
    for a in audits:
        gov_total.update(a.get("governance", {}))
        tongue_total.update(a.get("tongues", {}))

    views_table = ""
    for a in audits:
        status = "PASS" if a["passed"] else "FAIL"
        views_table += f"| {a['view']} | {a['total_records']:,} | {status} |\n"

    gov_table = ""
    for gov, count in sorted(gov_total.items()):
        gov_table += f"| {gov} | {count:,} |\n"

    tongue_table = ""
    for t, count in sorted(tongue_total.items()):
        tongue_table += f"| {t} | {count:,} |\n"

    report = f"""---
license: apache-2.0
task_categories:
  - text-generation
  - text-classification
language:
  - en
tags:
  - scbe
  - ai-safety
  - governance
  - sacred-tongues
  - multi-view
size_categories:
  - 100K<n<1M
---

# {repo_id}

**SCBE-AETHERMOORE Governed Training Data**

Multi-view, governance-aware training dataset built from the SCBE 14-layer
security pipeline. Every record carries tongue routing, layer classification,
FU status, and governance decisions.

Published: {utc_now()}

## What Makes This Different

Standard training data: `instruction -> output` (flat text, one view)

SCBE training data: `instruction + tongue + layer + null pattern -> output`
(multi-view, geometric)

Each record is seen through multiple processing channels (Sacred Tongues).
The **null tongue pattern** teaches models what NOT to process — reducing
wasted compute and improving accuracy through constraint awareness.

## Data Views

| View | Records | Status |
|------|---------|--------|
{views_table}

## Governance Distribution

| Decision | Count |
|----------|-------|
{gov_table}

## Tongue Distribution

| Tongue | Count |
|--------|-------|
{tongue_table}

## Audit Status

- Overall: {"PASS" if all_passed else "ISSUES FOUND"}
- Views audited: {len(audits)}
- Total records across views: {total_records:,}
{"- Warnings: " + "; ".join(all_warnings) if all_warnings else "- No warnings"}

## Usage

```python
from datasets import load_dataset

# Load the full governed dataset
ds = load_dataset("{repo_id}")

# Access specific splits
train = ds["train"]
test = ds["test"]

# Filter by governance
allowed = train.filter(lambda x: x.get("governance") == "ALLOW")
```

## Format Compatibility

| Platform | Format | View |
|----------|--------|------|
| HuggingFace TRL (conversational) | `{{"messages": [...]}}` | trl_conversation |
| HuggingFace TRL (prompt-completion) | `{{"prompt": ..., "completion": ...}}` | trl_prompt_completion |
| OpenAI Fine-tuning API | `{{"messages": [...]}}` | openai_chat |
| Classification tasks | features + label | activation_cls, governance_cls |
| Contrastive learning | paired records | contrast_pairs |

## Architecture

Built on the SCBE 14-layer security pipeline:
- **L0-L2**: Substrate, coordination, orientation
- **L3**: Expression (natural language output)
- **L5**: Hyperbolic distance (adversarial cost scaling)
- **L12**: Harmonic wall: H(d,pd) = 1/(1+phi*d_H+2*pd)
- **L13**: Governance decision: ALLOW / QUARANTINE / DENY

6 Sacred Tongues provide multi-view processing:
- **KO**: Control/orchestration
- **AV**: Data flow
- **RU**: Rules/constraints
- **CA**: Computation
- **UM**: Risk/uncertainty
- **DR**: Structure/lore

## License

Apache 2.0

## Citation

```bibtex
@misc{{scbe-aethermoore-2026,
  title={{SCBE-AETHERMOORE: Governed Multi-View Training Data}},
  author={{Davis, Issac}},
  year={{2026}},
  url={{https://huggingface.co/datasets/{repo_id}}}
}}
```
"""
    return report


# ---------------------------------------------------------------------------
# Phase 4: PUBLISH
# ---------------------------------------------------------------------------

def _check_ssh_auth() -> bool:
    """Check if HF SSH authentication works."""
    import subprocess
    try:
        r = subprocess.run(
            ["ssh", "-T", "git@hf.co"],
            capture_output=True, text=True, timeout=15,
        )
        # ssh -T returns 1 but prints welcome message on success
        return "welcome to Hugging Face" in (r.stdout + r.stderr)
    except Exception:
        return False


def _resolve_hf_auth(token: str | None) -> tuple[str | None, bool]:
    """Return (token_or_None, use_ssh). Tries token first, falls back to SSH."""
    if token:
        try:
            from huggingface_hub import HfApi
            api = HfApi(token=token)
            api.whoami()
            return token, False
        except Exception:
            print("    Token invalid/expired, checking SSH...")

    if _check_ssh_auth():
        print("    SSH auth confirmed for HuggingFace")
        return None, True

    return None, False


def _publish_via_token(packages: list[dict], report: str, repo_id: str,
                       token: str, private: bool) -> dict[str, Any]:
    """Push via HF API token (original path)."""
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset",
                    private=private, exist_ok=True)
    print(f"    Repo: {repo_id} (exists or created)")

    for pkg in packages:
        if not pkg.get("packaged") or "splits" not in pkg:
            continue
        view = pkg["view"]
        splits = pkg["splits"]
        splits.push_to_hub(repo_id=repo_id, config_name=view,
                          token=token, private=private)
        print(f"    Pushed: {view} ({pkg['train']:,} train / {pkg['test']:,} test)")

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                     encoding="utf-8") as f:
        f.write(report)
        readme_path = f.name
    api.upload_file(repo_id=repo_id, repo_type="dataset",
                    path_or_fileobj=readme_path, path_in_repo="README.md",
                    token=token)
    print(f"    README uploaded")

    return {
        "published": True, "repo_id": repo_id, "auth_method": "token",
        "views": [p["view"] for p in packages if p.get("packaged")],
        "timestamp": utc_now(),
    }


def _publish_via_ssh(packages: list[dict], report: str,
                     repo_id: str) -> dict[str, Any]:
    """Push via git SSH — no token needed, just SSH keys on HF."""
    import subprocess
    import shutil

    clone_url = f"git@hf.co:datasets/{repo_id}"
    work_dir = REPO_ROOT / "artifacts" / "publish" / "_hf_clone"

    # Clean previous clone
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    # Shallow clone the existing repo
    print(f"    Cloning {repo_id} via SSH...")
    r = subprocess.run(
        ["git", "clone", "--depth=1", clone_url, str(work_dir)],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        return {"published": False, "reason": f"git clone failed: {r.stderr}"}
    print(f"    Cloned to {work_dir}")

    # Configure git LFS for parquet files
    subprocess.run(["git", "lfs", "install"], cwd=str(work_dir),
                  capture_output=True, text=True)

    # Ensure .gitattributes tracks parquet via LFS
    gitattr = work_dir / ".gitattributes"
    attr_lines = gitattr.read_text(encoding="utf-8").splitlines() if gitattr.exists() else []
    lfs_patterns = {"*.parquet filter=lfs diff=lfs merge=lfs -text"}
    existing = set(attr_lines)
    for pattern in lfs_patterns:
        if pattern not in existing:
            attr_lines.append(pattern)
    gitattr.write_text("\n".join(attr_lines) + "\n", encoding="utf-8")

    # Save each view as parquet files in the HF datasets layout
    pushed_views = []
    for pkg in packages:
        if not pkg.get("packaged") or "splits" not in pkg:
            continue

        view = pkg["view"]
        splits = pkg["splits"]

        # HF datasets layout: data/{config_name}/{split}-00000-of-00001.parquet
        view_dir = work_dir / "data" / view
        view_dir.mkdir(parents=True, exist_ok=True)

        for split_name in splits:
            ds = splits[split_name]
            out_path = view_dir / f"{split_name}-00000-of-00001.parquet"
            ds.to_parquet(str(out_path))
            print(f"    Saved: {view}/{split_name} ({len(ds):,} rows)")

        pushed_views.append(view)

    # Write README
    readme_path = work_dir / "README.md"
    readme_path.write_text(report, encoding="utf-8")

    # Stage, commit, push
    subprocess.run(["git", "add", "-A"], cwd=str(work_dir),
                  capture_output=True, text=True)

    r = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(work_dir),
        capture_output=True, text=True,
    )
    if not r.stdout.strip():
        print("    No changes to push")
        return {"published": True, "repo_id": repo_id, "auth_method": "ssh",
                "views": pushed_views, "timestamp": utc_now(), "note": "no changes"}

    subprocess.run(
        ["git", "commit", "-m",
         f"Update governed training data ({len(pushed_views)} views, {utc_now()})"],
        cwd=str(work_dir), capture_output=True, text=True,
    )

    print(f"    Pushing {len(pushed_views)} views via SSH...")
    r = subprocess.run(
        ["git", "push"], cwd=str(work_dir),
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        return {"published": False, "reason": f"git push failed: {r.stderr}"}

    print(f"    Push complete!")

    # Clean up clone
    shutil.rmtree(work_dir, ignore_errors=True)

    return {
        "published": True, "repo_id": repo_id, "auth_method": "ssh",
        "views": pushed_views, "timestamp": utc_now(),
    }


def publish_to_hf(packages: list[dict], report: str, repo_id: str,
                  token: str | None, private: bool = False) -> dict[str, Any]:
    """Push packaged data to HuggingFace Hub. Tries token first, falls back to SSH."""
    print(f"\n  PUBLISH: {repo_id}")

    resolved_token, use_ssh = _resolve_hf_auth(token)

    if not resolved_token and not use_ssh:
        return {"published": False, "reason": "No valid token and SSH auth failed"}

    if resolved_token:
        print(f"    Auth: API token")
        return _publish_via_token(packages, report, repo_id, resolved_token, private)
    else:
        print(f"    Auth: SSH key (no token needed)")
        return _publish_via_ssh(packages, report, repo_id)


# ---------------------------------------------------------------------------
# Phase 5: LOG
# ---------------------------------------------------------------------------

def log_publish(result: dict, audits: list[dict]):
    """Record publish event for audit trail."""
    PUBLISH_LOG.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": utc_now(),
        "result": result,
        "audit_summary": {
            "views": len(audits),
            "all_passed": all(a["passed"] for a in audits),
            "total_records": sum(a["total_records"] for a in audits),
        },
    }

    with open(PUBLISH_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\n  LOG: {PUBLISH_LOG}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Autonomous publish pipeline — audit, package, report, publish."
    )
    parser.add_argument("--view", default="all",
                        help="Which view to publish (default: all)")
    parser.add_argument("--repo-id", default=os.getenv("HF_REPO", DEFAULT_REPO))
    parser.add_argument("--token", default=os.getenv("HF_TOKEN"))
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Audit + package + report, but don't push to HF")
    parser.add_argument("--max-rows", type=int, default=0,
                        help="Cap records per view (0 = all)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.05)
    return parser.parse_args()


def main():
    args = parse_args()
    start = time.time()

    print("=" * 60)
    print("  AUTONOMOUS PUBLISH PIPELINE")
    print(f"  Repo: {args.repo_id}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'PUBLISH'}")
    print("=" * 60)

    # Resolve station data
    VIEWS["station"] = get_latest_station_run()

    # Select views
    if args.view == "all":
        selected = {k: v for k, v in VIEWS.items() if v is not None and v.exists()}
    else:
        if args.view not in VIEWS:
            print(f"  ERROR: Unknown view '{args.view}'. Available: {list(VIEWS.keys())}")
            sys.exit(1)
        path = VIEWS[args.view]
        if args.view == "station":
            path = get_latest_station_run()
        if path is None or not path.exists():
            print(f"  ERROR: View '{args.view}' file not found")
            sys.exit(1)
        selected = {args.view: path}

    print(f"  Views: {list(selected.keys())}")

    # Phase 1: AUDIT
    print("\n" + "=" * 60)
    print("  PHASE 1: AUDIT")
    print("=" * 60)

    audits = []
    for view_name, path in selected.items():
        audit = audit_data(path, view_name)
        audits.append(audit)

    all_passed = all(a["passed"] for a in audits)
    if not all_passed:
        failed = [a["view"] for a in audits if not a["passed"]]
        print(f"\n  AUDIT FAILED for: {failed}")
        print("  Fix issues before publishing. Use --dry-run to see details.")
        if not args.dry_run:
            sys.exit(1)

    # Phase 2: PACKAGE
    print("\n" + "=" * 60)
    print("  PHASE 2: PACKAGE")
    print("=" * 60)

    packages = []
    for view_name, path in selected.items():
        pkg = package_data(path, view_name, seed=args.seed,
                          test_size=args.test_size, max_rows=args.max_rows)
        packages.append(pkg)

    # Phase 3: REPORT
    print("\n" + "=" * 60)
    print("  PHASE 3: REPORT")
    print("=" * 60)

    report = generate_report(audits, packages, args.repo_id)

    # Save report locally
    report_path = REPO_ROOT / "artifacts" / "publish" / "latest_dataset_card.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"  Report saved: {report_path}")

    # Phase 4: PUBLISH
    if args.dry_run:
        print("\n" + "=" * 60)
        print("  PHASE 4: PUBLISH (SKIPPED — dry run)")
        print("=" * 60)
        result = {"published": False, "reason": "dry_run", "timestamp": utc_now()}
    else:
        print("\n" + "=" * 60)
        print("  PHASE 4: PUBLISH")
        print("=" * 60)

        result = publish_to_hf(packages, report, args.repo_id,
                               args.token, args.private)

        if not result.get("published"):
            print(f"  PUBLISH FAILED: {result.get('reason', 'unknown')}")
            sys.exit(1)

    # Phase 5: LOG
    print("\n" + "=" * 60)
    print("  PHASE 5: LOG")
    print("=" * 60)

    log_publish(result, audits)

    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"  PIPELINE COMPLETE in {elapsed:.1f}s")
    print(f"  Views: {len(selected)}")
    print(f"  Audit: {'ALL PASS' if all_passed else 'ISSUES'}")
    print(f"  Published: {result.get('published', False)}")
    print("=" * 60)


if __name__ == "__main__":
    main()

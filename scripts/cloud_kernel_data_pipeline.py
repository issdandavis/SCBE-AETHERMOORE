#!/usr/bin/env python3
"""Cloud-first dataset pipeline with verification gates for SCBE kernel training."""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from training_auditor import audit_dataset_records


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = "training/cloud_kernel_pipeline.json"
DEFAULT_RUN_ROOT = "training/runs/cloud_kernel_sync"
LATEST_POINTER = "training/ingest/latest_cloud_kernel_sync.txt"

UNCERTAINTY_MARKERS = (
    "tbd",
    "placeholder",
    "todo",
    "unknown",
    "unverified",
    "draft",
)

ACTIONABLE_TERMS = (
    "must",
    "should",
    "run",
    "command",
    "pipeline",
    "api",
    "step",
    "verify",
    "build",
    "deploy",
)

SECRET_PATTERNS = (
    r"\bghp_[A-Za-z0-9]{20,}\b",
    r"\bhf_[A-Za-z0-9]{20,}\b",
    r"\bsk-[A-Za-z0-9]{16,}\b",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"BEGIN\s+PRIVATE\s+KEY",
)

HARMFUL_PATTERNS = (
    r"(how\s+to|steps\s+to|script\s+to).{0,40}(exploit|steal|phish|bypass|malware|ransomware)",
    r"(credential\s+stuffing|keylogger|exfiltrat(e|ion)|steal\s+password)",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build, verify, and ship kernel training datasets to cloud sinks."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"Config path (default: {DEFAULT_CONFIG})")
    parser.add_argument("--run-root", default=DEFAULT_RUN_ROOT, help=f"Run root (default: {DEFAULT_RUN_ROOT})")
    parser.add_argument("--glob", action="append", default=[], help="Extra source glob pattern (repeatable).")
    parser.add_argument("--sync-notion", action="store_true", help="Sync Notion docs before ingest.")
    parser.add_argument(
        "--notion-config-key",
        action="append",
        default=[],
        help="Specific key from scripts/sync-config.json (repeatable).",
    )
    parser.add_argument(
        "--ship-targets",
        default="",
        help="Override shipping targets as CSV subset of: hf,github,dropbox.",
    )
    parser.add_argument("--no-upload", action="store_true", help="Disable all cloud upload steps.")
    parser.add_argument("--keep-runs", type=int, default=0, help="Override local retention run count.")
    parser.add_argument(
        "--allow-quarantine",
        action="store_true",
        help="Do not fail if allowed dataset is quarantined by anomaly auditor.",
    )
    parser.add_argument(
        "--ship-on-quarantine",
        action="store_true",
        help="Allow cloud shipping even if dataset-level audit is QUARANTINE.",
    )
    return parser.parse_args()


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_text(value: Any) -> str:
    return "" if value is None else str(value)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(row, dict):
            records.append(row)
    return records


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:  # noqa: BLE001
        return None


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
            count += 1
    return count


def run_command(cmd: List[str], executed: List[str]) -> str:
    executed.append(" ".join(cmd))
    print("$ " + " ".join(cmd))
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    out = proc.stdout or ""
    if out:
        print(out, end="")
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}")
    return out


def extract_text_from_object(obj: Dict[str, Any]) -> str:
    preferred_keys = (
        "source_text",
        "text",
        "content",
        "body",
        "description",
        "notes",
        "message",
        "title",
        "summary",
    )
    parts: List[str] = []
    for key in preferred_keys:
        value = obj.get(key)
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            text = as_text(value).strip()
            if text:
                parts.append(text)
        elif isinstance(value, list):
            joined = [as_text(v).strip() for v in value if as_text(v).strip()]
            if joined:
                parts.append(" | ".join(joined))
    return " \n".join(parts).strip()


def infer_source_system_from_path(path: Path) -> str:
    lower = str(path).lower()
    if "airtable" in lower:
        return "airtable"
    if "asana" in lower:
        return "asana"
    if "proton" in lower:
        return "protonmail"
    if "gumroad" in lower:
        return "gumroad"
    if "google_business" in lower or "google-business" in lower or "gbp" in lower:
        return "google_business"
    if "zapier" in lower:
        return "zapier"
    return "external"


def normalize_external_item(item: Dict[str, Any], source_file: Path, index: int) -> Dict[str, Any] | None:
    text = extract_text_from_object(item)
    if not text:
        return None

    source_system = as_text(item.get("source_system") or item.get("tool") or item.get("app")).strip().lower()
    if not source_system:
        source_system = infer_source_system_from_path(source_file)

    source_id = as_text(item.get("id") or item.get("record_id") or item.get("task_id") or item.get("thread_id"))
    event_type = as_text(item.get("event_type") or item.get("type") or item.get("status") or "external_record")
    created_at = as_text(item.get("created_at") or item.get("created_at_utc") or item.get("timestamp"))
    category = as_text(item.get("category") or item.get("kind")).strip().lower() or source_system

    return {
        "event_type": event_type,
        "dataset": "external_production_intake",
        "source_system": source_system,
        "source_id": source_id or f"{source_system}-{index}",
        "source_path": str(source_file.relative_to(REPO_ROOT)).replace("\\", "/"),
        "chunk_index": index,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "created_at_utc": created_at or datetime.now(timezone.utc).isoformat(),
        "source_text": text,
        "category": category,
        "raw": item,
    }


def load_external_intake(globs_in: List[str]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    rows: List[Dict[str, Any]] = []
    stats = {"files_seen": 0, "records_emitted": 0}
    resolved_files: List[Path] = []

    for pattern in globs_in:
        abs_pattern = str((REPO_ROOT / pattern).resolve())
        for path_str in glob.glob(abs_pattern, recursive=True):
            path = Path(path_str)
            if path.is_file():
                resolved_files.append(path)

    unique_files = sorted({p.resolve() for p in resolved_files})
    stats["files_seen"] = len(unique_files)

    for file_path in unique_files:
        payload: List[Dict[str, Any]] = []
        suffix = file_path.suffix.lower()
        if suffix == ".jsonl":
            payload = read_jsonl(file_path)
        elif suffix == ".json":
            parsed = read_json(file_path)
            if isinstance(parsed, list):
                payload = [x for x in parsed if isinstance(x, dict)]
            elif isinstance(parsed, dict):
                records = parsed.get("records")
                if isinstance(records, list):
                    payload = [x for x in records if isinstance(x, dict)]
                else:
                    payload = [parsed]
        else:
            continue

        for idx, item in enumerate(payload):
            normalized = normalize_external_item(item, file_path, idx)
            if normalized is None:
                continue
            rows.append(normalized)
            stats["records_emitted"] += 1

    return rows, stats


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def infer_category(record: Dict[str, Any]) -> str:
    if isinstance(record.get("categories"), list) and record["categories"]:
        value = as_text(record["categories"][0]).strip().lower()
        if value:
            return value
    if record.get("category"):
        value = as_text(record["category"]).strip().lower()
        if value:
            return value
    source_path = normalize_path(as_text(record.get("source_path")))
    if source_path.startswith("docs/map-room/"):
        return "coordination"
    if "offline_mode_spec" in source_path or "governance" in source_path:
        return "governance"
    if source_path.startswith("docs/news/"):
        return "news"
    if source_path.startswith("src/"):
        return "code"
    if source_path.startswith("training/"):
        return "training_ops"
    if source_path.startswith("docs/"):
        return "reference"
    return "general"


def text_of(record: Dict[str, Any]) -> str:
    for key in ("source_text", "text", "message", "title"):
        if record.get(key) is not None:
            return as_text(record[key])
    return json.dumps(record, sort_keys=True)


def ratio_symbols(text: str) -> float:
    if not text:
        return 0.0
    symbols = sum(1 for ch in text if not ch.isalnum() and not ch.isspace())
    return symbols / float(len(text))


def shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    freq: Dict[str, int] = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    total = float(len(text))
    entropy = 0.0
    for count in freq.values():
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def anomaly_score(text: str) -> float:
    lower = text.lower()
    entropy_norm = min(1.0, shannon_entropy(text) / 6.0)
    symbol_norm = min(1.0, ratio_symbols(text) / 0.35)
    short_penalty = 1.0 if len(text.strip()) < 60 else 0.0
    secret_hit = 1.0 if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in SECRET_PATTERNS) else 0.0
    uncertainty_pen = 1.0 if any(marker in lower for marker in UNCERTAINTY_MARKERS) else 0.0
    return clamp01(0.35 * entropy_norm + 0.2 * symbol_norm + 0.2 * short_penalty + 0.15 * secret_hit + 0.1 * uncertainty_pen)


def compute_truth_score(text: str, source_path: str, verified_sources: set[str]) -> Tuple[float, List[str]]:
    reasons: List[str] = []
    score = 0.0
    lower = text.lower()

    if source_path:
        score += 0.25
        reasons.append("source_path_present")
    if source_path and source_path in verified_sources:
        score += 0.4
        reasons.append("source_hash_attested")
    if len(text.strip()) >= 120:
        score += 0.2
        reasons.append("content_length_sufficient")
    if any(marker in lower for marker in UNCERTAINTY_MARKERS):
        score -= 0.2
        reasons.append("uncertainty_marker_found")
    else:
        score += 0.1
        reasons.append("no_uncertainty_markers")
    if "http://" in lower or "https://" in lower or source_path.startswith("docs/") or source_path.startswith("src/"):
        score += 0.05
        reasons.append("traceable_source_hint")

    return clamp01(score), reasons


def compute_useful_score(text: str, category: str) -> Tuple[float, List[str]]:
    reasons: List[str] = []
    score = 0.0
    compact = " ".join(text.split())
    tokens = [tok for tok in compact.split(" ") if tok]
    token_count = len(tokens)
    lower = compact.lower()

    length = len(compact)
    if 120 <= length <= 5000:
        score += 0.4
        reasons.append("length_target_band")
    elif length >= 60:
        score += 0.25
        reasons.append("length_minimum_band")
    else:
        score += 0.1
        reasons.append("length_short")

    if token_count >= 25:
        score += 0.25
        reasons.append("token_density_high")
    elif token_count >= 12:
        score += 0.15
        reasons.append("token_density_medium")

    if any(term in lower for term in ACTIONABLE_TERMS) or "```" in text:
        score += 0.2
        reasons.append("actionable_content")

    if category != "general":
        score += 0.15
        reasons.append("classified_category")

    return clamp01(score), reasons


def compute_harmful_score(text: str, anomaly: float) -> Tuple[float, List[str]]:
    reasons: List[str] = []
    score = 0.0

    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in SECRET_PATTERNS):
        score += 0.55
        reasons.append("secret_pattern_detected")
    if any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in HARMFUL_PATTERNS):
        score += 0.35
        reasons.append("harmful_instruction_pattern")

    sym_ratio = ratio_symbols(text)
    if sym_ratio > 0.45:
        score += 0.1
        reasons.append("high_symbol_ratio")

    if len(text.strip()) < 40:
        score += 0.1
        reasons.append("very_short_record")

    if anomaly >= 0.78:
        score += 0.15
        reasons.append("high_anomaly_score")

    return clamp01(score), reasons


def annotate_records(
    rows: List[Dict[str, Any]],
    verified_sources: set[str],
    thresholds: Dict[str, float],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    all_rows: List[Dict[str, Any]] = []
    allowed: List[Dict[str, Any]] = []
    quarantined: List[Dict[str, Any]] = []
    category_counts: Dict[str, int] = {}

    truth_min = float(thresholds.get("truth_min", 0.62))
    useful_min = float(thresholds.get("useful_min", 0.58))
    harmful_max = float(thresholds.get("harmful_max", 0.25))

    for idx, rec in enumerate(rows):
        source_path = normalize_path(as_text(rec.get("source_path")))
        text = text_of(rec)
        category = infer_category(rec)
        category_counts[category] = category_counts.get(category, 0) + 1
        score_anomaly = anomaly_score(text)
        truth, truth_reasons = compute_truth_score(text, source_path, verified_sources)
        useful, useful_reasons = compute_useful_score(text, category)
        harmful, harmful_reasons = compute_harmful_score(text, score_anomaly)

        decision = "ALLOW"
        reasons: List[str] = []
        if truth < truth_min:
            decision = "QUARANTINE"
            reasons.append("truth_below_threshold")
        if useful < useful_min:
            decision = "QUARANTINE"
            reasons.append("useful_below_threshold")
        if harmful > harmful_max:
            decision = "QUARANTINE"
            reasons.append("harmful_above_threshold")

        enriched = dict(rec)
        enriched["category"] = category
        enriched["record_index"] = idx
        enriched["verification"] = {
            "truth_score": round(truth, 6),
            "useful_score": round(useful, 6),
            "harmful_score": round(harmful, 6),
            "anomaly_score": round(score_anomaly, 6),
            "decision": decision,
            "reasons": reasons,
            "truth_reasons": truth_reasons,
            "useful_reasons": useful_reasons,
            "harmful_reasons": harmful_reasons,
            "source_verified": bool(source_path and source_path in verified_sources),
        }
        all_rows.append(enriched)
        if decision == "ALLOW":
            allowed.append(enriched)
        else:
            quarantined.append(enriched)

    sort_key = lambda row: (
        as_text(row.get("category")),
        normalize_path(as_text(row.get("source_path"))),
        int(row.get("chunk_index", 0) or 0),
        int(row.get("record_index", 0) or 0),
    )
    all_rows.sort(key=sort_key)
    allowed.sort(key=sort_key)
    quarantined.sort(key=sort_key)
    return all_rows, allowed, quarantined, category_counts


def build_verified_source_set(manifest: Dict[str, Any]) -> set[str]:
    sources: set[str] = set()
    for doc in manifest.get("documents", []):
        if not isinstance(doc, dict):
            continue
        verification = doc.get("verification", {})
        if isinstance(verification, dict) and verification.get("status") == "verified":
            filename = normalize_path(as_text(doc.get("filename")))
            if filename:
                sources.add(filename)
    return sources


def write_categories(path: Path, records: List[Dict[str, Any]]) -> Dict[str, int]:
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for row in records:
        cat = as_text(row.get("category", "general")).strip().lower() or "general"
        by_cat.setdefault(cat, []).append(row)
    counts: Dict[str, int] = {}
    for cat, rows in by_cat.items():
        out_file = path / f"{cat}.jsonl"
        counts[cat] = write_jsonl(out_file, rows)
    return counts


def upload_to_hf(run_dir: Path, repo_id: str, path_prefix: str, run_id: str) -> Dict[str, Any]:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN is required for Hugging Face upload.")
    try:
        from huggingface_hub import HfApi  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"huggingface_hub not installed: {exc}") from exc

    api = HfApi(token=token)
    remote_path = f"{path_prefix.rstrip('/')}/{run_id}".strip("/")
    api.upload_folder(
        folder_path=str(run_dir),
        path_in_repo=remote_path,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"dataset-sync: {run_id}",
    )
    return {"status": "ok", "repo": repo_id, "path_in_repo": remote_path}


def run_gh_command(cmd: List[str], env: Dict[str, str]) -> str:
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    out = proc.stdout or ""
    if proc.returncode != 0:
        raise RuntimeError(f"gh command failed: {' '.join(cmd)}\n{out}")
    return out


def upload_to_github_release(
    repo: str,
    run_id: str,
    release_prefix: str,
    files: List[Path],
) -> Dict[str, Any]:
    if not shutil.which("gh"):
        raise RuntimeError("GitHub CLI (gh) is required for GitHub release upload.")

    token = os.environ.get("GH_TOKEN", "").strip() or os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is required for GitHub release upload.")

    env = dict(os.environ)
    env["GH_TOKEN"] = token

    tag = f"{release_prefix}-{run_id}"
    title = f"Kernel Data Sync {run_id}"
    notes = f"Automated dataset sync bundle for {run_id}."

    view_cmd = ["gh", "release", "view", tag, "--repo", repo]
    view_proc = subprocess.run(
        view_cmd,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if view_proc.returncode != 0:
        run_gh_command(["gh", "release", "create", tag, "--repo", repo, "--title", title, "--notes", notes], env)

    upload_cmd = ["gh", "release", "upload", tag, "--repo", repo, "--clobber"] + [str(p) for p in files]
    run_gh_command(upload_cmd, env)
    return {"status": "ok", "repo": repo, "tag": tag, "assets": [p.name for p in files]}


def upload_file_dropbox(local_file: Path, dropbox_path: str, token: str) -> Dict[str, Any]:
    url = "https://content.dropboxapi.com/2/files/upload"
    content = local_file.read_bytes()
    args = {
        "path": dropbox_path,
        "mode": "overwrite",
        "autorename": False,
        "mute": True,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Dropbox-API-Arg": json.dumps(args),
        "Content-Type": "application/octet-stream",
    }
    req = urllib.request.Request(url, data=content, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Dropbox upload failed ({exc.code}): {detail}") from exc

    payload = json.loads(raw)
    return {"name": payload.get("name"), "path_display": payload.get("path_display"), "id": payload.get("id")}


def upload_to_dropbox(run_id: str, base_path: str, files: List[Path]) -> Dict[str, Any]:
    token = os.environ.get("DROPBOX_TOKEN", "").strip()
    if not token:
        raise RuntimeError("DROPBOX_TOKEN is required for Dropbox upload.")
    root = base_path if base_path.startswith("/") else f"/{base_path}"
    root = root.rstrip("/")
    uploads = []
    for local in files:
        target = f"{root}/{run_id}/{local.name}"
        uploads.append(upload_file_dropbox(local, target, token))
    return {"status": "ok", "base_path": root, "uploads": uploads}


def cleanup_old_runs(run_root: Path, keep_runs: int) -> Dict[str, int]:
    if keep_runs <= 0:
        return {"deleted_dirs": 0, "deleted_archives": 0}

    dirs = [p for p in run_root.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.name)
    deleted_dirs = 0
    deleted_archives = 0
    if len(dirs) <= keep_runs:
        return {"deleted_dirs": 0, "deleted_archives": 0}

    for old in dirs[: len(dirs) - keep_runs]:
        shutil.rmtree(old, ignore_errors=True)
        deleted_dirs += 1
        zip_path = old.with_suffix(".zip")
        if zip_path.exists():
            zip_path.unlink()
            deleted_archives += 1
    return {"deleted_dirs": deleted_dirs, "deleted_archives": deleted_archives}


def parse_ship_targets(raw: str) -> set[str]:
    if not raw.strip():
        return set()
    values = {part.strip().lower() for part in raw.split(",") if part.strip()}
    supported = {"hf", "github", "dropbox"}
    return values & supported


def main() -> int:
    args = parse_args()
    config = load_json(REPO_ROOT / args.config)
    run_root = REPO_ROOT / args.run_root
    run_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = run_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    commands_executed: List[str] = []
    source_globs = [str(x) for x in config.get("sources", [])] + list(args.glob)
    source_globs = [g for i, g in enumerate(source_globs) if g and g not in source_globs[:i]]
    external_globs = [str(x) for x in config.get("external_intake_globs", [])]
    thresholds = dict(config.get("thresholds", {}))

    raw_jsonl = run_dir / "raw_production_ingest.jsonl"
    raw_combined_jsonl = run_dir / "raw_combined.jsonl"
    manifest_json = run_dir / "doc_manifest.json"
    curated_all_jsonl = run_dir / "curated_all.jsonl"
    curated_allowed_jsonl = run_dir / "curated_allowed.jsonl"
    curated_quarantine_jsonl = run_dir / "curated_quarantine.jsonl"
    categories_dir = run_dir / "categories"
    audit_json = run_dir / "dataset_audit.json"
    verification_json = run_dir / "verification_report.json"
    summary_json = run_dir / "run_summary.json"

    if args.sync_notion:
        if args.notion_config_key:
            for key in args.notion_config_key:
                run_command(["node", "scripts/notion-sync.js", "--config-key", key], commands_executed)
        else:
            run_command(["node", "scripts/notion-sync.js", "--all"], commands_executed)

    ingest_cmd = [sys.executable, "scripts/ingest_docs_to_training_jsonl.py", "--out", str(raw_jsonl)]
    for pattern in source_globs:
        ingest_cmd.extend(["--glob", pattern])
    run_command(ingest_cmd, commands_executed)

    attest = as_text(config.get("attest", "claude,gpt,sonar")).strip()
    manifest_cmd = [sys.executable, "training/doc_verifier.py", "--json", "--out", str(manifest_json)]
    if attest:
        manifest_cmd.extend(["--attest", attest])
    run_command(manifest_cmd, commands_executed)

    manifest = load_json(manifest_json)
    verified_sources = build_verified_source_set(manifest)
    raw_rows = read_jsonl(raw_jsonl)
    external_rows, external_stats = load_external_intake(external_globs)
    if external_rows:
        raw_rows.extend(external_rows)
    write_jsonl(raw_combined_jsonl, raw_rows)
    all_rows, allowed_rows, quarantine_rows, category_counts = annotate_records(raw_rows, verified_sources, thresholds)

    total_rows = len(all_rows)
    allowed_count = write_jsonl(curated_allowed_jsonl, allowed_rows)
    quarantined_count = write_jsonl(curated_quarantine_jsonl, quarantine_rows)
    write_jsonl(curated_all_jsonl, all_rows)
    category_allowed_counts = write_categories(categories_dir, allowed_rows)

    dataset_audit = audit_dataset_records(
        allowed_rows,
        threshold=float(thresholds.get("dataset_anomaly_threshold", 0.78)),
        max_flagged_ratio=float(thresholds.get("dataset_max_flagged_ratio", 0.08)),
    )
    audit_json.write_text(json.dumps(dataset_audit, indent=2) + "\n", encoding="utf-8")

    means = {
        "truth_score_mean": 0.0,
        "useful_score_mean": 0.0,
        "harmful_score_mean": 0.0,
        "anomaly_score_mean": 0.0,
    }
    if total_rows:
        for row in all_rows:
            v = row.get("verification", {})
            means["truth_score_mean"] += float(v.get("truth_score", 0.0))
            means["useful_score_mean"] += float(v.get("useful_score", 0.0))
            means["harmful_score_mean"] += float(v.get("harmful_score", 0.0))
            means["anomaly_score_mean"] += float(v.get("anomaly_score", 0.0))
        for key in means:
            means[key] = round(means[key] / float(total_rows), 6)

    archive_file = run_dir.with_suffix(".zip")
    if archive_file.exists():
        archive_file.unlink()
    shutil.make_archive(str(run_dir), "zip", root_dir=run_dir)

    ship_config = dict(config.get("shipping", {}))
    selected_targets = parse_ship_targets(args.ship_targets) if args.ship_targets else {
        k for k, v in ship_config.items() if isinstance(v, dict) and bool(v.get("enabled"))
    }
    shipping_results: Dict[str, Any] = {}
    shipping_errors: Dict[str, str] = {}
    can_ship = (not args.no_upload) and (dataset_audit.get("status") == "ALLOW" or args.ship_on_quarantine)

    if can_ship:
        if "hf" in selected_targets:
            hf_cfg = ship_config.get("hf", {})
            try:
                shipping_results["hf"] = upload_to_hf(
                    run_dir=run_dir,
                    repo_id=as_text(hf_cfg.get("repo")),
                    path_prefix=as_text(hf_cfg.get("path_prefix", "kernel-sync/runs")),
                    run_id=run_id,
                )
            except Exception as exc:  # noqa: BLE001
                shipping_errors["hf"] = str(exc)
        if "github" in selected_targets:
            gh_cfg = ship_config.get("github", {})
            try:
                shipping_results["github"] = upload_to_github_release(
                    repo=as_text(gh_cfg.get("repo")),
                    run_id=run_id,
                    release_prefix=as_text(gh_cfg.get("release_prefix", "kernel-data-sync")),
                    files=[archive_file, curated_allowed_jsonl, audit_json, verification_json],
                )
            except Exception as exc:  # noqa: BLE001
                shipping_errors["github"] = str(exc)
        if "dropbox" in selected_targets:
            dbx_cfg = ship_config.get("dropbox", {})
            try:
                shipping_results["dropbox"] = upload_to_dropbox(
                    run_id=run_id,
                    base_path=as_text(dbx_cfg.get("base_path", "/SCBE/kernel-data-sync")),
                    files=[archive_file, curated_allowed_jsonl, audit_json, verification_json],
                )
            except Exception as exc:  # noqa: BLE001
                shipping_errors["dropbox"] = str(exc)

    pointer_path = REPO_ROOT / LATEST_POINTER
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(str(run_dir.relative_to(REPO_ROOT)).replace("\\", "/") + "\n", encoding="utf-8")

    keep_runs = args.keep_runs if args.keep_runs > 0 else int(config.get("retention", {}).get("keep_local_runs", 30))
    cleanup = cleanup_old_runs(run_root, keep_runs)

    state_vector = {
        "worker_id": "codex-agent",
        "task_id": "cloud-kernel-data-pipeline",
        "role": "implementer",
        "status": "completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    decision = "ALLOW" if dataset_audit.get("status") == "ALLOW" else "QUARANTINE"
    decision_record = {
        "action": decision,
        "signature": f"codex-agent:cloud-kernel-data-pipeline:{run_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": "Curated dataset scored for truth/useful/harmful and audited for anomalies.",
        "confidence": 0.97 if decision == "ALLOW" else 0.88,
    }

    verification_report = {
        "run_id": run_id,
        "thresholds": {
            "truth_min": float(thresholds.get("truth_min", 0.62)),
            "useful_min": float(thresholds.get("useful_min", 0.58)),
            "harmful_max": float(thresholds.get("harmful_max", 0.25)),
            "dataset_anomaly_threshold": float(thresholds.get("dataset_anomaly_threshold", 0.78)),
            "dataset_max_flagged_ratio": float(thresholds.get("dataset_max_flagged_ratio", 0.08)),
        },
        "counts": {
            "input_records": total_rows,
            "external_records": len(external_rows),
            "allowed_records": allowed_count,
            "quarantine_records": quarantined_count,
            "verified_sources": len(verified_sources),
        },
        "external_intake": {
            "globs": external_globs,
            "files_seen": external_stats.get("files_seen", 0),
            "records_emitted": external_stats.get("records_emitted", 0),
        },
        "means": means,
        "category_counts_input": category_counts,
        "category_counts_allowed": category_allowed_counts,
        "dataset_audit": dataset_audit,
        "state_vector": state_vector,
        "decision_record": decision_record,
    }
    verification_json.write_text(json.dumps(verification_report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "run_id": run_id,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
        "artifacts": {
            "raw_ingest": str(raw_jsonl.relative_to(REPO_ROOT)).replace("\\", "/"),
            "raw_combined": str(raw_combined_jsonl.relative_to(REPO_ROOT)).replace("\\", "/"),
            "doc_manifest": str(manifest_json.relative_to(REPO_ROOT)).replace("\\", "/"),
            "curated_all": str(curated_all_jsonl.relative_to(REPO_ROOT)).replace("\\", "/"),
            "curated_allowed": str(curated_allowed_jsonl.relative_to(REPO_ROOT)).replace("\\", "/"),
            "curated_quarantine": str(curated_quarantine_jsonl.relative_to(REPO_ROOT)).replace("\\", "/"),
            "categories_dir": str(categories_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
            "dataset_audit": str(audit_json.relative_to(REPO_ROOT)).replace("\\", "/"),
            "verification_report": str(verification_json.relative_to(REPO_ROOT)).replace("\\", "/"),
            "archive": str(archive_file.relative_to(REPO_ROOT)).replace("\\", "/"),
        },
        "latest_pointer": LATEST_POINTER,
        "shipping": {
            "enabled": not args.no_upload,
            "allowed_by_policy": can_ship,
            "targets_selected": sorted(selected_targets),
            "results": shipping_results,
            "errors": shipping_errors,
        },
        "retention": {"keep_local_runs": keep_runs, "cleanup": cleanup},
        "external_intake": {
            "globs": external_globs,
            "files_seen": external_stats.get("files_seen", 0),
            "records_emitted": external_stats.get("records_emitted", 0),
        },
        "commands_executed": commands_executed,
        "state_vector": state_vector,
        "decision_record": decision_record,
    }
    summary_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("")
    print("Cloud kernel data pipeline completed.")
    print(f"Run dir: {summary['run_dir']}")
    print(f"Allowed records: {allowed_count}")
    print(f"Quarantine records: {quarantined_count}")
    print(f"Dataset audit status: {dataset_audit.get('status')}")
    if shipping_errors:
        print(f"Shipping errors: {shipping_errors}")

    if dataset_audit.get("status") != "ALLOW" and not args.allow_quarantine:
        return 2
    if shipping_errors and not args.no_upload:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

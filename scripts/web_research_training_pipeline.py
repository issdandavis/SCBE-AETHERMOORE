#!/usr/bin/env python3
"""
SCBE web research -> AV membrane -> training dataset pipeline.

Flow:
1) Discover URLs from web RSS (Google News query feeds).
2) Run HYDRA headless MMX coordinator on URLs.
3) Filter output through antivirus membrane and decision gates.
4) Emit training JSONL (allowed + quarantine) and dataset audit report.
5) Optionally upload run artifacts to Hugging Face dataset repo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

try:
    from training_auditor import audit_dataset_records
except Exception:  # noqa: BLE001
    from scripts.training_auditor import audit_dataset_records


REPO_ROOT = Path(__file__).resolve().parent.parent
COORDINATOR_SCRIPT = REPO_ROOT / "scripts" / "hydra_headless_mmx_coordinator.py"

DEFAULT_RUN_ROOT = "training/runs/web_research"
DEFAULT_INTAKE_DIR = "training/intake/web_research"
DEFAULT_CORE_TESTS = (
    "tests/test_antivirus_membrane.py",
    "tests/test_extension_gate.py",
    "tests/test_hydra_turnstile.py",
    "tests/test_multi_model_modal_matrix.py",
)

CANONICAL_WALL_FORMULA = "H(d*,R) = R · pi^(phi · d*)"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def read_topics(args: argparse.Namespace) -> list[str]:
    topics: list[str] = []
    if args.topics:
        topics.extend([str(t).strip() for t in args.topics if str(t).strip()])
    if args.topics_file:
        raw = Path(args.topics_file).read_text(encoding="utf-8")
        for line in raw.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                topics.append(line)
    dedup: list[str] = []
    seen: set[str] = set()
    for topic in topics:
        if topic.lower() not in seen:
            dedup.append(topic)
            seen.add(topic.lower())
    return dedup


def parse_rss_items(xml_bytes: bytes, topic: str, limit: int) -> list[dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    out: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if not link:
            continue
        out.append(
            {
                "topic": topic,
                "title": title,
                "url": link,
                "published": pub_date,
                "source": "google_news_rss",
            }
        )
        if len(out) >= limit:
            break
    return out


def discover_topic_urls(topic: str, per_topic: int, timeout_sec: int = 20) -> list[dict[str, str]]:
    query = urllib.parse.quote_plus(topic)
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(
        rss_url,
        headers={"User-Agent": "SCBE-WebResearchPipeline/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        xml_bytes = resp.read()
    return parse_rss_items(xml_bytes, topic=topic, limit=per_topic)


def discover_urls(topics: list[str], per_topic: int) -> tuple[list[str], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    for topic in topics:
        try:
            rows.extend(discover_topic_urls(topic, per_topic))
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "topic": topic,
                    "title": f"discovery-failed: {exc}",
                    "url": "",
                    "published": "",
                    "source": "google_news_rss",
                }
            )
    urls: list[str] = []
    seen: set[str] = set()
    for row in rows:
        url = (row.get("url") or "").strip()
        if not url:
            continue
        if url not in seen:
            urls.append(url)
            seen.add(url)
    return urls, rows


def load_manual_urls(path: str) -> list[str]:
    raw = Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
    except json.JSONDecodeError:
        pass
    return [line.strip() for line in raw.splitlines() if line.strip()]


def run_hydra_scan(
    *,
    urls_file: Path,
    backend: str,
    max_tabs: int,
    query: str,
    output_json: Path,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(COORDINATOR_SCRIPT),
        "--urls-file",
        str(urls_file),
        "--backend",
        backend,
        "--max-tabs",
        str(max_tabs),
        "--output-json",
        str(output_json),
    ]
    if query.strip():
        cmd.extend(["--query", query.strip()])

    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"hydra coordinator failed ({proc.returncode}):\n{proc.stdout}")
    return json.loads(output_json.read_text(encoding="utf-8"))


def build_training_rows(
    payload: dict[str, Any],
    *,
    run_id: str,
    topics: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    allowed: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    results = payload.get("results", [])
    for idx, row in enumerate(results):
        if not isinstance(row, dict):
            continue
        url = str(row.get("url", ""))
        decision = str(row.get("decision", "QUARANTINE")).upper()
        threat = row.get("threat_scan", {}) if isinstance(row.get("threat_scan"), dict) else {}
        threat_verdict = str(threat.get("verdict", "UNKNOWN")).upper()
        threat_risk = float(threat.get("risk_score", 0.0) or 0.0)
        content = row.get("content", {}) if isinstance(row.get("content"), dict) else {}
        preview = str(content.get("preview", "") or "")
        sha256 = str(content.get("sha256", "") or "")
        length = int(content.get("length", 0) or 0)
        matrix = row.get("matrix", {}) if isinstance(row.get("matrix"), dict) else {}
        matrix_decision = (
            matrix.get("decision", {}) if isinstance(matrix.get("decision"), dict) else {}
        )
        matrix_conf = float(matrix_decision.get("confidence", row.get("decision_confidence", 0.0)) or 0.0)

        training_row = {
            "event_type": "web_research_chunk",
            "dataset": "scbe_web_research_intake",
            "run_id": run_id,
            "chunk_index": idx,
            "source_system": "web",
            "source_url": url,
            "topics": topics,
            "source_text": preview,
            "content_length": length,
            "content_sha256": sha256,
            "decision": decision,
            "decision_confidence": round(clamp01(matrix_conf), 6),
            "threat_verdict": threat_verdict,
            "threat_risk": round(clamp01(threat_risk), 6),
            "generated_at_utc": utc_now(),
        }

        unsafe = (
            decision in {"DENY", "QUARANTINE"}
            or threat_verdict in {"SUSPICIOUS", "MALICIOUS"}
            or threat_risk >= 0.55
        )
        if unsafe:
            quarantine.append(training_row)
        else:
            allowed.append(training_row)

    return allowed, quarantine


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    return len(rows)


def run_core_health_check(core_tests: list[str]) -> dict[str, Any]:
    if not core_tests:
        return {"ran": False, "passed": True, "command": "", "output": ""}
    cmd = [sys.executable, "-m", "pytest", "-q", *core_tests]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "ran": True,
        "passed": proc.returncode == 0,
        "return_code": proc.returncode,
        "command": " ".join(cmd),
        "output": proc.stdout,
    }


def upload_to_hf_dataset(
    *,
    repo_id: str,
    token: str,
    run_id: str,
    files: list[Path],
) -> dict[str, Any]:
    try:
        from huggingface_hub import HfApi  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return {"status": "skipped", "reason": f"huggingface_hub not installed: {exc}"}

    api = HfApi(token=token)
    try:
        api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
    except Exception:
        pass

    uploaded: list[str] = []
    for path in files:
        repo_path = f"web-research/runs/{run_id}/{path.name}"
        api.upload_file(
            path_or_fileobj=str(path),
            path_in_repo=repo_path,
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"SCBE web research sync {run_id}: {path.name}",
        )
        uploaded.append(repo_path)
    return {"status": "uploaded", "repo_id": repo_id, "files": uploaded}


def post_n8n_webhook(url: str, payload: dict[str, Any], timeout_sec: int = 20) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            status_code = int(resp.getcode() or 0)
            response_text = resp.read().decode("utf-8", errors="replace")
        return {
            "status": "sent",
            "status_code": status_code,
            "response_preview": response_text[:500],
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "reason": str(exc)}


def choose_action(
    *,
    allowed_count: int,
    quarantined_count: int,
    audit_status: str,
    core_health_passed: bool,
) -> tuple[str, str, float]:
    total = max(1, allowed_count + quarantined_count)
    allow_ratio = allowed_count / float(total)
    if audit_status != "ALLOW":
        return ("QUARANTINE", "dataset audit quarantined", clamp01(allow_ratio * 0.4))
    if not core_health_passed:
        return ("QUARANTINE", "core health check failed", clamp01(allow_ratio * 0.5))
    if allowed_count == 0:
        return ("DENY", "no safe records after gating", 0.0)
    return ("ALLOW", "safe intake generated", clamp01(0.5 + 0.5 * allow_ratio))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SCBE web research training pipeline")
    parser.add_argument("--topics", nargs="*", default=[], help="Search topics")
    parser.add_argument("--topics-file", default="", help="Optional topic file (one topic per line)")
    parser.add_argument("--urls-file", default="", help="Optional manual URL file (JSON list or newline text)")
    parser.add_argument("--max-per-topic", type=int, default=6, help="Max URLs per topic from RSS discovery")
    parser.add_argument("--backend", default="playwright", choices=["playwright", "selenium", "chrome_mcp", "cdp"])
    parser.add_argument("--max-tabs", type=int, default=6, help="Concurrent HYDRA tabs")
    parser.add_argument("--query", default="", help="Optional relevance query for MMX")
    parser.add_argument("--scan-json", default="", help="Use existing HYDRA scan JSON instead of live browser scan")
    parser.add_argument("--run-root", default=DEFAULT_RUN_ROOT, help="Run artifact root directory")
    parser.add_argument("--intake-dir", default=DEFAULT_INTAKE_DIR, help="Training intake directory")
    parser.add_argument("--skip-core-check", action="store_true", help="Skip core pytest gate")
    parser.add_argument("--core-tests", nargs="*", default=list(DEFAULT_CORE_TESTS), help="Core tests to run")
    parser.add_argument("--upload-hf", action="store_true", help="Upload run artifacts to HF dataset")
    parser.add_argument("--hf-repo", default="", help="HF dataset repo id")
    parser.add_argument("--hf-token-env", default="HF_TOKEN", help="Environment variable for HF token")
    parser.add_argument("--n8n-webhook", default="", help="Optional n8n webhook URL for run handoff")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = (REPO_ROOT / args.run_root / run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    topics = read_topics(args)
    urls: list[str] = []
    discovery_rows: list[dict[str, str]] = []

    if topics:
        d_urls, d_rows = discover_urls(topics, args.max_per_topic)
        urls.extend(d_urls)
        discovery_rows.extend(d_rows)

    if args.urls_file:
        urls.extend(load_manual_urls(args.urls_file))

    dedup_urls: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url and url not in seen:
            dedup_urls.append(url)
            seen.add(url)
    if not dedup_urls:
        raise SystemExit("No URLs discovered. Provide --topics and/or --urls-file.")

    discovered_path = run_dir / "discovered_urls.json"
    write_json(
        discovered_path,
        {
            "run_id": run_id,
            "generated_at_utc": utc_now(),
            "topics": topics,
            "url_count": len(dedup_urls),
            "urls": dedup_urls,
            "discovery_rows": discovery_rows,
        },
    )

    urls_file = run_dir / "urls.json"
    urls_file.write_text(json.dumps(dedup_urls, indent=2), encoding="utf-8")

    hydra_output = run_dir / "hydra_scan.json"
    if args.scan_json:
        hydra_payload = json.loads(Path(args.scan_json).read_text(encoding="utf-8"))
        write_json(hydra_output, hydra_payload)
    else:
        query = args.query.strip() if args.query.strip() else " ".join(topics)
        hydra_payload = run_hydra_scan(
            urls_file=urls_file,
            backend=args.backend,
            max_tabs=args.max_tabs,
            query=query,
            output_json=hydra_output,
        )

    allowed_rows, quarantined_rows = build_training_rows(
        hydra_payload,
        run_id=run_id,
        topics=topics,
    )

    allowed_path = run_dir / "curated_allowed.jsonl"
    quarantined_path = run_dir / "curated_quarantine.jsonl"
    write_jsonl(allowed_path, allowed_rows)
    write_jsonl(quarantined_path, quarantined_rows)

    audit = audit_dataset_records(
        allowed_rows,
        threshold=0.78,
        max_flagged_ratio=0.08,
    )
    audit_path = run_dir / "audit.json"
    write_json(audit_path, audit)

    core_health = {"ran": False, "passed": True, "output": "", "command": ""}
    if not args.skip_core_check:
        core_health = run_core_health_check(args.core_tests)
    core_health_path = run_dir / "core_health.json"
    write_json(core_health_path, core_health)

    action, reason, confidence = choose_action(
        allowed_count=len(allowed_rows),
        quarantined_count=len(quarantined_rows),
        audit_status=str(audit.get("status", "QUARANTINE")),
        core_health_passed=bool(core_health.get("passed", False)),
    )

    state_vector = {
        "run_id": run_id,
        "generated_at_utc": utc_now(),
        "topics": topics,
        "urls_discovered": len(dedup_urls),
        "records_allowed": len(allowed_rows),
        "records_quarantined": len(quarantined_rows),
        "audit_status": audit.get("status", "QUARANTINE"),
        "core_health_passed": bool(core_health.get("passed", False)),
        "scbe_layer12_wall_formula": CANONICAL_WALL_FORMULA,
    }
    state_vector_path = run_dir / "statevector.json"
    write_json(state_vector_path, state_vector)

    signature_seed = json.dumps(state_vector, sort_keys=True) + reason + action
    decision_record = {
        "action": action,
        "signature": hashlib.sha256(signature_seed.encode("utf-8")).hexdigest(),
        "timestamp_utc": utc_now(),
        "reason": reason,
        "confidence": round(confidence, 6),
    }
    decision_record_path = run_dir / "decision_record.json"
    write_json(decision_record_path, decision_record)

    intake_dir = (REPO_ROOT / args.intake_dir).resolve()
    intake_dir.mkdir(parents=True, exist_ok=True)
    intake_path = intake_dir / f"web_research_{run_id}.jsonl"
    write_jsonl(intake_path, allowed_rows)

    hf_upload = {"status": "skipped"}
    if args.upload_hf:
        token = os.environ.get(args.hf_token_env, "").strip()
        if not args.hf_repo:
            hf_upload = {"status": "skipped", "reason": "--hf-repo required with --upload-hf"}
        elif not token:
            hf_upload = {"status": "skipped", "reason": f"{args.hf_token_env} not set"}
        else:
            hf_upload = upload_to_hf_dataset(
                repo_id=args.hf_repo,
                token=token,
                run_id=run_id,
                files=[
                    discovered_path,
                    hydra_output,
                    allowed_path,
                    quarantined_path,
                    audit_path,
                    core_health_path,
                    state_vector_path,
                    decision_record_path,
                ],
            )

    n8n_dispatch = {"status": "skipped"}
    if args.n8n_webhook.strip():
        n8n_dispatch = post_n8n_webhook(
            args.n8n_webhook.strip(),
            {
                "event": "scbe.web_research.run_complete",
                "run_id": run_id,
                "statevector": state_vector,
                "decision_record": decision_record,
                "summary_path": str(run_dir / "summary.json"),
                "audit_path": str(audit_path),
                "intake_file": str(intake_path),
            },
        )

    summary = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "intake_file": str(intake_path),
        "urls_discovered": len(dedup_urls),
        "allowed_records": len(allowed_rows),
        "quarantined_records": len(quarantined_rows),
        "audit_status": audit.get("status", "QUARANTINE"),
        "core_health_passed": bool(core_health.get("passed", False)),
        "decision_record": decision_record,
        "hf_upload": hf_upload,
        "n8n_dispatch": n8n_dispatch,
    }
    write_json(run_dir / "summary.json", summary)

    print(json.dumps(summary, indent=2))
    return 0 if action == "ALLOW" else 2


if __name__ == "__main__":
    raise SystemExit(main())

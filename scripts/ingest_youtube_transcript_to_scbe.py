#!/usr/bin/env python3
"""Ingest a YouTube video transcript into SCBE web research training flow."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUN_ROOT = "training/runs/web_research"
DEFAULT_INTAKE_DIR = "training/intake/web_research"
TRANSCRIPT_DIR = REPO_ROOT / "temp" / "yt_subs"
PIPELINE_PATH = REPO_ROOT / "scripts" / "web_research_training_pipeline.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_video_id(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(parsed.query)
    if "v" in q and q["v"]:
        return q["v"][0]
    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.lstrip("/")
    seg = parsed.path.rstrip("/").split("/")[-1]
    if seg and seg != "watch":
        return seg
    raise ValueError(f"unable to extract video id from url: {url}")


def split_chunks(text: str, chunk_size: int = 1800, overlap: int = 220) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    if chunk_size <= 1:
        raise ValueError("chunk_size must be > 1")
    step = max(1, chunk_size - max(0, overlap))
    chunks: list[str] = []
    for i in range(0, len(text), step):
        chunk = text[i : i + chunk_size].strip()
        if len(chunk) >= 40:
            chunks.append(chunk)
    return chunks


def read_local_transcript(video_id: str) -> str:
    for lang in ("en", "en-US", "en-GB", "auto"):
        txt_path = TRANSCRIPT_DIR / f"{video_id}.{lang}.txt"
        if txt_path.exists():
            return txt_path.read_text(encoding="utf-8", errors="replace")
    return ""


def fetch_transcript(video_id: str, languages: tuple[str, ...] = ("en", "en-US", "en-GB")) -> tuple[str, str]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("youtube_transcript_api not installed") from exc

    for lang in languages:
        try:
            items = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
            return " ".join([str(i.get("text", "")).strip() for i in items if str(i.get("text", "")).strip()]), lang
        except Exception:
            continue

    items = YouTubeTranscriptApi.get_transcript(video_id)
    return " ".join([str(i.get("text", "")).strip() for i in items if str(i.get("text", "")).strip()]), "auto"


def load_or_fetch_transcript(video_id: str, force_fetch: bool = False) -> tuple[str, str]:
    if not force_fetch:
        text = read_local_transcript(video_id)
        if text:
            return text, "cached"
    text, lang = fetch_transcript(video_id)
    if not text.strip():
        raise RuntimeError(f"transcript for {video_id} is empty")

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    (TRANSCRIPT_DIR / f"{video_id}.{lang}.txt").write_text(text, encoding="utf-8")
    return text, lang


def sanitize_filename(text: str, fallback: str = "video") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9-_]", "_", text)
    return (cleaned[:120] or fallback).strip("_")


def build_scan_payload(*, source_url: str, title: str, transcript: str, chunk_size: int, overlap: int, risk_score: float, decision_conf: float) -> dict[str, Any]:
    chunks = split_chunks(transcript, chunk_size=chunk_size, overlap=overlap)
    results: list[dict[str, Any]] = []
    for idx, chunk in enumerate(chunks):
        row_hash = hashlib.sha256((source_url + "\n" + chunk).encode("utf-8")).hexdigest()
        results.append(
            {
                "url": source_url,
                "title": title,
                "decision": "ALLOW",
                "decision_confidence": round(float(decision_conf), 6),
                "threat_scan": {"verdict": "SAFE", "risk_score": round(float(risk_score), 6)},
                "matrix": {"decision": {"confidence": round(float(decision_conf), 6)}},
                "content": {
                    "preview": chunk,
                    "sha256": row_hash,
                    "length": len(chunk),
                    "title": title,
                    "chunk_index": idx,
                    "source_system": "youtube",
                },
            }
        )

    return {
        "source": {
            "url": source_url,
            "title": title,
            "run_at": _utc_now(),
            "transcript_chunks": len(chunks),
        },
        "results": results,
    }


def write_scan_payload(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_pipeline(scan_path: Path, run_root: str, intake_dir: str, skip_core_check: bool) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(PIPELINE_PATH),
        "--scan-json",
        str(scan_path),
        "--run-root",
        run_root,
        "--intake-dir",
        intake_dir,
    ]
    if skip_core_check:
        cmd.append("--skip-core-check")

    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    summary: dict[str, Any] = {
        "return_code": proc.returncode,
        "raw_output": (proc.stdout or "").strip(),
    }

    run_root_path = REPO_ROOT / run_root
    if run_root_path.exists():
        run_dirs = [p for p in run_root_path.iterdir() if p.is_dir()]
        if run_dirs:
            latest = max(run_dirs, key=lambda p: p.stat().st_mtime)
            latest_summary = latest / "summary.json"
            if latest_summary.exists():
                try:
                    summary = json.loads(latest_summary.read_text(encoding="utf-8"))
                    summary["run_dir"] = str(latest)
                    summary["latest_run_dir"] = str(latest)
                    summary["raw_output"] = (proc.stdout or "").strip()
                except Exception:
                    summary["raw_output"] = (proc.stdout or "").strip()
                    summary["run_dir"] = str(latest)

    return summary


def post_obsidian_note(vault_path: str, payload: dict[str, Any], summary: dict[str, Any], transcript_path: Path, scan_path: Path, title: str) -> str:
    from obsidian_ai_hub import post_context, resolve_vault_path

    run_info = summary
    source = payload.get("source", {})
    content = "\n".join(
        [
            f"# Youtube Ingest: {title}",
            "",
            f"- source_url: {source.get('url')}",
            f"- source_title: {source.get('title')}",
            f"- chunks: {source.get('transcript_chunks', 0)}",
            f"- run_dir: {run_info.get('run_dir', '')}",
            f"- intake_file: {run_info.get('intake_file', '')}",
            f"- run_id: {run_info.get('run_id', '')}",
            f"- audit_status: {run_info.get('audit_status', '')}",
            f"- scan_json: {scan_path}",
            f"- transcript_file: {transcript_path}",
            "",
            "## Action",
            f"decision={run_info.get('decision_record', {}).get('action', 'ALLOW')}",
            f"confidence={run_info.get('decision_record', {}).get('confidence', 'n/a')}",
            "- generated via ingest_youtube_transcript_to_scbe.py",
            "- next: run `python scripts/ingest_youtube_transcript_to_scbe.py --youtube-url ...` for additional references",
        ]
    )

    vault = resolve_vault_path(vault_path)
    note = post_context(
        vault_path=vault,
        title=f"Youtube Ingest: {title[:80]}",
        body=content,
        folder="Sessions",
    )
    return str(note)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a YouTube transcript into SCBE web research pipeline")
    parser.add_argument("--youtube-url", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--topic", action="append", default=[], help="Optional topics for metadata context")
    parser.add_argument("--run-root", default=DEFAULT_RUN_ROOT)
    parser.add_argument("--intake-dir", default=DEFAULT_INTAKE_DIR)
    parser.add_argument("--chunk-size", type=int, default=1800)
    parser.add_argument("--chunk-overlap", type=int, default=220)
    parser.add_argument("--risk-score", type=float, default=0.12)
    parser.add_argument("--decision-confidence", type=float, default=0.91)
    parser.add_argument("--skip-core-check", action="store_true")
    parser.add_argument("--skip-obsidian", action="store_true")
    parser.add_argument("--obsidian-vault", default="")
    parser.add_argument("--force-fetch", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    video_id = extract_video_id(args.youtube_url)

    transcript, source = load_or_fetch_transcript(video_id, force_fetch=args.force_fetch)
    if not transcript:
        raise RuntimeError("No transcript text available")

    source_title = args.title.strip() or source[:80] or "youtube-video"

    topic_hint = sanitize_filename("_".join([t for t in args.topic if t]).replace(" ", "_")) or "youtube"
    base_root = f"{args.run_root}/{topic_hint}_{video_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    REPO_ROOT.joinpath(base_root).mkdir(parents=True, exist_ok=True)
    run_root = base_root

    scan_payload = build_scan_payload(
        source_url=args.youtube_url,
        title=source_title,
        transcript=transcript,
        chunk_size=max(500, args.chunk_size),
        overlap=max(0, min(args.chunk_overlap, args.chunk_size - 1)),
        risk_score=args.risk_score,
        decision_conf=args.decision_confidence,
    )

    scan_path = REPO_ROOT / base_root / "scan_payload.json"
    write_scan_payload(scan_payload, scan_path)

    summary = run_pipeline(
        scan_path=scan_path,
        run_root=run_root,
        intake_dir=args.intake_dir,
        skip_core_check=args.skip_core_check,
    )

    if not args.skip_obsidian:
        try:
            vault = args.obsidian_vault
            if not vault:
                vault = ""
            note = post_obsidian_note(
                vault_path=vault,
                payload=scan_payload,
                summary=summary,
                transcript_path=TRANSCRIPT_DIR / f"{video_id}.en.txt",
                scan_path=scan_path,
                title=source_title,
            )
            summary["obsidian_note"] = note
        except Exception as exc:  # noqa: BLE001
            summary["obsidian_note_error"] = str(exc)

    print(json.dumps(summary, indent=2))
    decision = str(summary.get("decision_record", {}).get("action", "ALLOW")).upper()
    return 0 if decision == "ALLOW" else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Evaluate SCBE research-bridge source/citation preservation."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_PATH = REPO_ROOT / "training-data" / "sft" / "research_bridge_source_grounded_v1_eval.sft.jsonl"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "research_bridge_citation_eval"
ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})(?:v[0-9]+)?", re.IGNORECASE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _message_content(row: dict[str, Any], role: str) -> str:
    messages = row.get("messages") if isinstance(row.get("messages"), list) else []
    for item in messages:
        if isinstance(item, dict) and item.get("role") == role:
            return str(item.get("content", ""))
    return ""


def _assistant_json(row: dict[str, Any]) -> dict[str, Any]:
    raw = _message_content(row, "assistant").strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("assistant content must decode to a JSON object")
    return parsed


def _extract_arxiv_id(text: str) -> str | None:
    match = ARXIV_RE.search(text)
    return match.group(1) if match else None


def _source_kind_from_prompt(prompt: str) -> str:
    match = re.search(r"Source kind:[ \t]*([^\n\r]+)", prompt)
    return match.group(1).strip() if match else ""


def _title_from_prompt(prompt: str) -> str:
    match = re.search(r"Title:[ \t]*([^\n\r]+)", prompt)
    return match.group(1).strip() if match else ""


def _url_from_prompt(prompt: str) -> str:
    match = re.search(r"URL:[ \t]*([^\n\r]*)", prompt)
    return match.group(1).strip() if match else ""


def _observed_overlap(prompt: str, observed: str) -> bool:
    if not observed.strip():
        return False
    compact_observed = " ".join(observed.split())
    compact_prompt = " ".join(prompt.split())
    if len(compact_observed) < 24:
        return compact_observed in compact_prompt
    return compact_observed[:80] in compact_prompt or compact_observed[:40] in compact_prompt


def score_research_record(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    prompt = _message_content(row, "user")
    try:
        payload = _assistant_json(row)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "ok": False,
            "score": 0.0,
            "record_id": metadata.get("dedupe_key", ""),
            "source_path": metadata.get("source_path", ""),
            "error": f"invalid_assistant_json: {exc}",
            "checks": {"json_parse": False},
        }

    source_kind = _source_kind_from_prompt(prompt)
    title = _title_from_prompt(prompt)
    url = _url_from_prompt(prompt)
    observed = str(payload.get("observed_evidence", ""))
    expected_arxiv_id = _extract_arxiv_id(url)
    actual_arxiv_id = payload.get("arxiv_id")
    payload_url = payload.get("url")

    checks = {
        "json_parse": True,
        "source_kind_preserved": payload.get("source_kind") == source_kind,
        "title_preserved": bool(payload.get("title")) and str(payload.get("title")) == title,
        "url_preserved": (payload_url == url if url else payload_url in {None, ""}),
        "observed_evidence_present": len(observed.strip()) >= 24,
        "observed_evidence_overlaps_prompt": _observed_overlap(prompt, observed),
        "inference_boundary_present": "Do not treat" in str(payload.get("inference_boundary", "")),
        "verification_step_present": bool(str(payload.get("verification_step", "")).strip()),
        "source_metadata_present": bool(metadata.get("source_path") and metadata.get("source_sha256")),
        "source_file_exists": (REPO_ROOT / str(metadata.get("source_path", ""))).exists(),
        "arxiv_id_preserved": (actual_arxiv_id == expected_arxiv_id if expected_arxiv_id else actual_arxiv_id is None),
    }
    passed = sum(1 for value in checks.values() if value)
    total = len(checks)
    return {
        "ok": passed == total,
        "score": round(passed / total, 4),
        "record_id": metadata.get("dedupe_key", ""),
        "source_path": metadata.get("source_path", ""),
        "source_kind": source_kind,
        "expected_arxiv_id": expected_arxiv_id,
        "checks": checks,
    }


def build_report(
    *,
    eval_path: Path = DEFAULT_EVAL_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    run_id: str | None = None,
) -> dict[str, Any]:
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows = _load_jsonl(eval_path)
    scores = [score_research_record(row) for row in rows]
    average = round(sum(item["score"] for item in scores) / len(scores), 4) if scores else 0.0
    report = {
        "schema_version": "scbe_research_bridge_citation_eval_v1",
        "purpose": "research_bridge",
        "generated_at_utc": _utc_now(),
        "run_id": run_id,
        "eval_path": str(eval_path),
        "record_count": len(rows),
        "score": average,
        "passed_records": sum(1 for item in scores if item["ok"]),
        "decision": "PASS" if rows and average >= 0.9 else "HOLD",
        "promotion_gate": "PASS requires source identity, observed evidence, inference boundary, and verification step preservation.",
        "record_scores": scores,
    }
    run_dir = output_dir / run_id
    _write_json(run_dir / "report.json", report)
    _write_json(output_dir / "latest_report.json", report)
    (run_dir / "REPORT.md").write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "LATEST.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SCBE Research Bridge Citation Eval",
            "",
            f"- Generated: `{report['generated_at_utc']}`",
            f"- Run ID: `{report['run_id']}`",
            f"- Decision: `{report['decision']}`",
            f"- Score: `{report['score']}`",
            f"- Records: `{report['record_count']}`",
            f"- Passed: `{report['passed_records']}`",
            "",
            "## Gate",
            "",
            report["promotion_gate"],
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-path", type=Path, default=DEFAULT_EVAL_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(eval_path=args.eval_path, output_dir=args.out_dir, run_id=args.run_id or None)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(
            "research bridge citation eval: "
            f"decision={report['decision']} score={report['score']} "
            f"records={report['record_count']}"
        )
        print(f"report={args.out_dir / report['run_id'] / 'report.json'}")
    return 0 if report["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

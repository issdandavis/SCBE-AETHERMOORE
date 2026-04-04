#!/usr/bin/env python3
"""
Export SCBE-AETHERMOORE Training Lab logs (from scripts/aetherbrowser/api_server.py) into SFT JSONL.

This turns interactive usage (chat + safe CLI commands) into training pairs
that can be pushed to Hugging Face and used for SFT fine-tuning.

Defaults:
  input:  artifacts/ai_ide_logs/{chat.jsonl,cli.jsonl}
  output: training-data/sft/ai_ide_sft.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable, Iterator


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = REPO_ROOT / "artifacts" / "ai_ide_logs"
DEFAULT_OUT = REPO_ROOT / "training-data" / "sft" / "ai_ide_sft.jsonl"

_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bssh-(rsa|ed25519)\s+[A-Za-z0-9+/=]{20,}\b"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*([^\s\"']{8,})"),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\b"),
]


def scrub_text(text: str) -> str:
    if not text:
        return text
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


def scrub_obj(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, str):
        return scrub_text(obj)
    if isinstance(obj, list):
        return [scrub_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): scrub_obj(v) for k, v in obj.items()}
    return obj


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if isinstance(item, dict):
                yield item


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            safe = scrub_obj(row)
            f.write(json.dumps(safe, ensure_ascii=True) + "\n")
            n += 1
    return n


def export_rows(log_dir: Path, *, max_rows: int = 0) -> list[dict[str, Any]]:
    chat_path = log_dir / "chat.jsonl"
    cli_path = log_dir / "cli.jsonl"

    out: list[dict[str, Any]] = []

    for rec in iter_jsonl(chat_path):
        req = rec.get("request") or {}
        resp = rec.get("response") or {}
        instruction = str(req.get("message") or "").strip()
        response = str(resp.get("text") or "").strip()
        if not instruction or not response:
            continue
        out.append(
            {
                "instruction": instruction,
                "response": response,
                "category": "ai_ide_chat",
                "source": "ai_ide",
                "timestamp": rec.get("ts"),
                "meta": {
                    "model": req.get("model"),
                    "governance_decision": resp.get("governance_decision"),
                    "trust_level": resp.get("trust_level"),
                    "fibonacci_value": resp.get("fibonacci_value"),
                    "cost": resp.get("cost"),
                    "tongues": resp.get("tongues"),
                },
            }
        )
        if max_rows and len(out) >= max_rows:
            return out

    for rec in iter_jsonl(cli_path):
        cmd = str(rec.get("command") or "").strip()
        result = rec.get("result")
        if not cmd:
            continue
        out.append(
            {
                "instruction": f"Run the SCBE safe CLI command: {cmd}",
                "response": json.dumps(scrub_obj(result), ensure_ascii=True, indent=2) if result is not None else "",
                "category": "ai_ide_cli",
                "source": "ai_ide",
                "timestamp": rec.get("ts"),
                "meta": {"kind": rec.get("kind")},
            }
        )
        if max_rows and len(out) >= max_rows:
            return out

    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Export SCBE-AETHERMOORE Training Lab logs to SFT JSONL")
    p.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR), help="Directory containing chat.jsonl and cli.jsonl")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSONL path")
    p.add_argument("--max-rows", type=int, default=0, help="Optional cap on total rows (0 = no cap)")
    args = p.parse_args()

    log_dir = Path(args.log_dir)
    out_path = Path(args.out)
    rows = export_rows(log_dir, max_rows=int(args.max_rows))
    n = write_jsonl(out_path, rows)
    print(f"Wrote {n} SFT rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

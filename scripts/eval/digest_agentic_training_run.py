#!/usr/bin/env python3
"""Digest agentic training gate output into compact reusable residues.

The goal is to keep the useful post-test signal without feeding whole noisy
logs back into training. A digest converts a gate report into small records:

- passed prompt required-token chains become positive residues,
- failed prompt missing-token chains become repair residues,
- forbidden-token hits become boundary residues,
- the run gets a lane recommendation for the next scheduler pass.

This is intentionally data-only. It does not launch training jobs.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_slug(value: str) -> str:
    rendered = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value).strip("-_")
    return rendered or "agentic-training-digest"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _extract_json_object_after_marker(text: str, marker: str) -> dict[str, Any] | None:
    idx = text.find(marker)
    if idx < 0:
        return None
    start = text.find("{", idx)
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for pos in range(start, len(text)):
        ch = text[pos]
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : pos + 1])
    return None


def _extract_gate_report_from_log(path: Path) -> dict[str, Any]:
    raw = _strip_ansi(path.read_text(encoding="utf-8", errors="replace"))
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{") or "gate_report" not in stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("report"), dict):
            return dict(payload["report"])
    wrapped = _extract_json_object_after_marker(raw, '"event": "gate_report"')
    if wrapped and isinstance(wrapped.get("report"), dict):
        return dict(wrapped["report"])
    report = _extract_json_object_after_marker(raw, '"schema": "scbe_stage6_regression_report_v1"')
    if report:
        return report
    raise ValueError(f"No gate_report JSON found in {path}")


def _extract_losses_from_log(path: Path) -> list[float]:
    losses: list[float] = []
    raw = _strip_ansi(path.read_text(encoding="utf-8", errors="replace"))
    for match in re.finditer(r"\{[^{}\n]*['\"]loss['\"][^{}\n]*\}", raw):
        try:
            payload = ast.literal_eval(match.group(0))
        except (SyntaxError, ValueError):
            continue
        if isinstance(payload, dict) and "loss" in payload:
            try:
                losses.append(float(payload["loss"]))
            except (TypeError, ValueError):
                continue
    return losses


def _gate_report_from_args(args: argparse.Namespace) -> tuple[dict[str, Any], list[float]]:
    if args.report:
        return _load_json(Path(args.report)), []
    if args.log:
        log_path = Path(args.log)
        return _extract_gate_report_from_log(log_path), _extract_losses_from_log(log_path)
    raise ValueError("Provide --report or --log")


def _run_phase(pass_rate: float, n_pass: int, n_total: int, loss_latest: float | None) -> str:
    if n_total == 0:
        return "no_gate"
    if pass_rate >= 1.0 and n_pass == n_total:
        return "promotion_packaging"
    if pass_rate >= 0.8:
        return "exploit_with_light_explore"
    if pass_rate >= 0.5:
        return "balanced_explore_exploit"
    if loss_latest is not None and loss_latest < 0.35:
        return "quadratic_expand_state_space"
    return "explore"


def _allocation_for_phase(phase: str) -> dict[str, int]:
    table = {
        "promotion_packaging": {"explore": 10, "exploit": 90},
        "exploit_with_light_explore": {"explore": 20, "exploit": 80},
        "balanced_explore_exploit": {"explore": 50, "exploit": 50},
        "quadratic_expand_state_space": {"explore": 75, "exploit": 25},
        "explore": {"explore": 80, "exploit": 20},
        "no_gate": {"explore": 60, "exploit": 40},
    }
    return table.get(phase, table["explore"])


def _residue_records(report: dict[str, Any], run_id: str, loss_latest: float | None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in report.get("results") or []:
        if not isinstance(item, dict):
            continue
        prompt_id = str(item.get("id") or "unknown_prompt")
        missing = [str(t) for t in item.get("missing_required") or []]
        forbidden = [str(t) for t in item.get("triggered_forbidden") or []]
        ok = bool(item.get("ok"))
        response = str(item.get("response") or "")
        prefix_tokens: list[str] = []
        first_line = response.splitlines()[0] if response else ""
        if first_line.lower().startswith("required-tokens:"):
            body = first_line.split(":", 1)[1].rsplit("::", 1)[0]
            prefix_tokens = [token.strip().strip("`") for token in body.split("|") if token.strip()]

        if ok:
            kind = "positive_residue"
            token_chain = prefix_tokens
        elif missing:
            kind = "repair_residue"
            token_chain = missing
        else:
            kind = "boundary_residue"
            token_chain = forbidden

        records.append(
            {
                "schema_version": "scbe_agentic_training_residue_v1",
                "run_id": run_id,
                "contract_id": report.get("contract_id"),
                "prompt_id": prompt_id,
                "kind": kind,
                "ok": ok,
                "token_chain": token_chain,
                "missing_required": missing,
                "triggered_forbidden": forbidden,
                "loss_latest": loss_latest,
            }
        )
    return records


def build_digest(report: dict[str, Any], losses: list[float], run_id: str) -> dict[str, Any]:
    n_total = int(report.get("n_total") or len(report.get("results") or []))
    n_pass = int(report.get("n_pass") or 0)
    pass_rate = float(report.get("pass_rate") or (n_pass / n_total if n_total else 1.0))
    loss_latest = losses[-1] if losses else None
    phase = _run_phase(pass_rate=pass_rate, n_pass=n_pass, n_total=n_total, loss_latest=loss_latest)
    residues = _residue_records(report, run_id=run_id, loss_latest=loss_latest)
    return {
        "schema_version": "scbe_agentic_training_digest_v1",
        "generated_utc": _utc_now(),
        "run_id": run_id,
        "contract_id": report.get("contract_id"),
        "gate": {
            "n_total": n_total,
            "n_pass": n_pass,
            "pass_rate": pass_rate,
            "overall_pass": bool(report.get("overall_pass")),
            "must_pass_all_ok": bool(report.get("must_pass_all_ok")),
        },
        "loss": {
            "first": losses[0] if losses else None,
            "latest": loss_latest,
            "count": len(losses),
        },
        "next_phase": phase,
        "lane_allocation": _allocation_for_phase(phase),
        "residue_count": len(residues),
        "residues": residues,
    }


def write_outputs(digest: dict[str, Any], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    digest_path = out_dir / "training_digest.json"
    residue_path = out_dir / "training_residues.jsonl"
    digest_path.write_text(json.dumps(digest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    with residue_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in digest["residues"]:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    return {"digest": str(digest_path), "residues": str(residue_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", help="Path to a gate report JSON file.")
    parser.add_argument("--log", help="Path to a raw HF/local training log containing gate_report JSON.")
    parser.add_argument("--run-id", default="", help="Stable run id; defaults to report contract/timestamp slug.")
    parser.add_argument("--out-dir", default="", help="Output folder. Defaults under artifacts/training_digestion.")
    parser.add_argument("--json", action="store_true", help="Print compact machine-readable result.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report, losses = _gate_report_from_args(args)
    generated_run_id = args.run_id or _safe_slug(
        f"{report.get('contract_id') or 'training-run'}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    digest = build_digest(report=report, losses=losses, run_id=generated_run_id)
    out_dir = Path(args.out_dir) if args.out_dir else Path("artifacts") / "training_digestion" / generated_run_id
    paths = write_outputs(digest, out_dir=out_dir)
    payload = {"paths": paths, "summary": {k: digest[k] for k in ("run_id", "contract_id", "next_phase", "lane_allocation", "residue_count")}}
    print(json.dumps(payload if args.json else digest, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

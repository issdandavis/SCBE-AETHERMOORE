#!/usr/bin/env python3
"""GeoSeal verifier-first search loop.

The pattern is deliberately P-vs-NP shaped:

- local scripts generate candidates
- deterministic checks verify candidates
- optional Ollama critics review receipts without executing their suggestions

This keeps cloud model spend focused on strategy rather than repeated local
"did it work?" checks.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from subprocess import run
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_ROOT = REPO_ROOT / "reports"
DEFAULT_OUT = REPORTS_ROOT / "geoseal_verify_search_receipt.json"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _json_load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_last_json(text: str) -> Any | None:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _field(payload: Any, dotted_path: str) -> Any:
    cur = payload
    for part in dotted_path.replace("$.", "").split("."):
        if not part:
            continue
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)]
        else:
            return None
    return cur


def _coerce_command(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(part) for part in raw]
    if isinstance(raw, str):
        return shlex.split(raw, posix=False)
    raise ValueError("candidate command must be a list or string")


def _run_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    cmd = _coerce_command(candidate["command"])
    cwd = Path(candidate.get("cwd") or REPO_ROOT)
    started = time.time()
    proc = run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=int(candidate.get("timeout_seconds", 3600)),
    )
    stdout_json = _parse_last_json(proc.stdout)
    result: dict[str, Any] = {
        "id": candidate.get("id", "candidate"),
        "cmd": cmd,
        "cwd": str(cwd),
        "returncode": proc.returncode,
        "seconds": round(time.time() - started, 3),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "stdout_json": stdout_json,
    }
    result["verified"] = _verify_candidate(candidate.get("verify", {}), result)
    return result


def _verify_candidate(verify: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    expected_returncode = int(verify.get("returncode", 0))
    checks.append(
        {
            "check": "returncode",
            "expected": expected_returncode,
            "actual": result.get("returncode"),
            "ok": result.get("returncode") == expected_returncode,
        }
    )

    stdout_json = result.get("stdout_json")
    for item in verify.get("json_fields", []):
        path = str(item.get("path", ""))
        actual = _field(stdout_json, path) if stdout_json is not None else None
        check: dict[str, Any] = {
            "check": "json_field",
            "path": path,
            "actual": actual,
        }
        if "equals" in item:
            check["expected"] = item["equals"]
            check["ok"] = actual == item["equals"]
        elif "min" in item:
            try:
                check["expected_min"] = item["min"]
                check["ok"] = float(actual) >= float(item["min"])
            except (TypeError, ValueError):
                check["ok"] = False
        elif "max" in item:
            try:
                check["expected_max"] = item["max"]
                check["ok"] = float(actual) <= float(item["max"])
            except (TypeError, ValueError):
                check["ok"] = False
        else:
            check["ok"] = actual is not None
        checks.append(check)

    return {
        "ok": all(bool(row.get("ok")) for row in checks),
        "checks": checks,
    }


def _preset_manifest(name: str) -> dict[str, Any]:
    if name != "arc-rubix":
        raise SystemExit(f"Unknown preset: {name}")
    return {
        "name": "arc-rubix-verifier-search",
        "budget": {"max_rounds": 1},
        "stop_on_pass": False,
        "candidates": [
            {
                "id": "arc_eval_loop",
                "command": [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "system" / "arc_rubix_loop.py"),
                    "--mode",
                    "eval",
                    "--json",
                ],
                "verify": {
                    "returncode": 0,
                    "json_fields": [{"path": "$.ok", "equals": True}],
                },
            }
        ],
    }


def _ollama_generate(url: str, model: str, prompt: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 384},
    }
    request = urllib.request.Request(
        url.rstrip("/") + "/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
        return {"ok": True, "model": model, "text": str(data.get("response", "")).strip()}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "model": model, "error": f"{type(exc).__name__}: {exc}"}


def _ask_ollama(models: list[str], url: str, receipt: dict[str, Any]) -> list[dict[str, Any]]:
    if not models:
        return []
    compact = {
        "name": receipt.get("name"),
        "ok": receipt.get("ok"),
        "winning_candidate": receipt.get("winning_candidate"),
        "rounds": [
            {
                "round": row.get("round"),
                "results": [
                    {
                        "id": item.get("id"),
                        "returncode": item.get("returncode"),
                        "verified": item.get("verified"),
                    }
                    for item in row.get("results", [])
                ],
            }
            for row in receipt.get("rounds", [])
        ],
    }
    prompt = (
        "You are a local GeoSeal search critic. Review this verifier-first "
        "receipt. Suggest the next deterministic candidates or checks. "
        "Do not propose cloud calls or unsafe shell commands.\n\n"
        + json.dumps(compact, indent=2, sort_keys=True)
    )
    return [_ollama_generate(url, model, prompt) for model in models]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run verifier-first local search receipts.")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--preset", choices=["arc-rubix"])
    parser.add_argument("--rounds", type=int)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--stop-on-pass", action="store_true")
    parser.add_argument("--no-stop-on-pass", action="store_true")
    parser.add_argument("--ollama-models", default="")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    if args.manifest:
        manifest = _json_load(args.manifest)
    elif args.preset:
        manifest = _preset_manifest(args.preset)
    else:
        raise SystemExit("Provide --manifest or --preset.")

    max_rounds = int(args.rounds or manifest.get("budget", {}).get("max_rounds", 1))
    stop_on_pass = bool(manifest.get("stop_on_pass", True))
    if args.stop_on_pass:
        stop_on_pass = True
    if args.no_stop_on_pass:
        stop_on_pass = False

    candidates = manifest.get("candidates", [])
    receipt: dict[str, Any] = {
        "name": manifest.get("name", "geoseal-verify-search"),
        "ok": False,
        "stop_on_pass": stop_on_pass,
        "rounds_requested": max_rounds,
        "candidate_count": len(candidates),
        "rounds": [],
        "winning_candidate": None,
        "ollama": [],
    }

    for round_index in range(max(1, max_rounds)):
        round_row = {"round": round_index + 1, "results": []}
        for candidate in candidates:
            result = _run_candidate(candidate)
            round_row["results"].append(result)
            if result.get("verified", {}).get("ok"):
                receipt["ok"] = True
                receipt["winning_candidate"] = result.get("id")
                if stop_on_pass:
                    receipt["rounds"].append(round_row)
                    _json_write(args.out, receipt)
                    if args.json:
                        print(json.dumps(receipt, indent=2, sort_keys=True))
                    else:
                        print(f"verify-search passed: {result.get('id')}")
                        print(f"receipt: {args.out}")
                    return 0
        receipt["rounds"].append(round_row)

    models = [part.strip() for part in args.ollama_models.split(",") if part.strip()]
    receipt["ollama"] = _ask_ollama(models, args.ollama_url, receipt)
    _json_write(args.out, receipt)

    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        print(f"verify-search {'passed' if receipt['ok'] else 'failed'}")
        print(f"receipt: {args.out}")
        if receipt.get("winning_candidate"):
            print(f"winning_candidate: {receipt['winning_candidate']}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

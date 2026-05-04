#!/usr/bin/env python3
"""Inspect the local Kimi Code connector lane for SCBE agent-bus use."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
KEY_MIRROR = Path.home() / ".codex" / "skills" / "scbe-api-key-local-mirror" / "scripts" / "key_mirror.py"


def _run(cmd: list[str], *, timeout: int = 20) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": str(exc), "cmd": cmd}
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip()[:2000],
        "stderr": proc.stderr.strip()[:2000],
        "cmd": cmd,
    }


def _mirror_status(service: str) -> dict[str, Any]:
    if not KEY_MIRROR.exists():
        return {"ok": False, "reason": "key_mirror_missing", "path": str(KEY_MIRROR)}
    result = _run([sys.executable, str(KEY_MIRROR), "resolve", "--service", service])
    if not result["ok"]:
        return {"ok": False, "reason": f"{service}_key_not_resolved", "path": str(KEY_MIRROR)}
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return {"ok": False, "reason": "key_mirror_bad_json", "path": str(KEY_MIRROR)}
    return {
        "ok": bool(payload.get("ok")),
        "service": payload.get("service"),
        "token_id": payload.get("token_id"),
        "fingerprint": payload.get("fingerprint"),
        "path": str(KEY_MIRROR),
    }


def inspect_connector() -> dict[str, Any]:
    kimi = shutil.which("kimi")
    cli = {"installed": bool(kimi), "path": kimi or ""}
    if kimi:
        version = _run([kimi, "--version"])
        cli["version"] = version.get("stdout") or version.get("stderr")

    return {
        "schema_version": "scbe_kimi_code_connector_v1",
        "provider_refs": {
            "kimi_code": "kimi:kimi-for-coding",
            "moonshot_platform": "moonshot:kimi-k2.6",
        },
        "key_mirror": {
            "kimi": _mirror_status("kimi"),
            "moonshot": _mirror_status("moonshot"),
        },
        "cli": cli,
        "api": {
            "kimi_code_openai_base_url": "https://api.kimi.com/coding/v1",
            "kimi_code_model": "kimi-for-coding",
            "moonshot_platform_base_url": "https://api.moonshot.ai/v1",
            "moonshot_platform_model": "kimi-k2.6",
        },
        "agent_bus_contract": {
            "lane_signal": "provider-pair:ollama->kimi:agentic-coding",
            "preferred_use": "coding-agent lane through official Kimi Code CLI/ACP when installed; HTTP smoke is treated as diagnostic only",
            "blocked_http_reason": "Kimi Code may reject generic clients with access_terminated_error unless called through an allowed coding-agent client.",
            "cli_smoke_command": "kimi --work-dir . --model kimi-code/kimi-for-coding --quiet --max-steps-per-turn 1 --prompt \"Return exactly: SCBE_KIMI_CODE_READY\"",
            "acp_command": "kimi acp --work-dir C:\\Users\\issda\\SCBE-AETHERMOORE",
        },
        "install_hint": "Invoke-RestMethod https://code.kimi.com/install.ps1 | Invoke-Expression",
        "login_hint": "Run `kimi`, then `/login`, and select Kimi Code.",
    }


def run_cli_smoke(timeout: int = 60) -> dict[str, Any]:
    kimi = shutil.which("kimi")
    if not kimi:
        return {"ok": False, "status": "missing_cli", "reason": "kimi not found on PATH"}
    prompt = "Return exactly: SCBE_KIMI_CODE_READY"
    result = _run(
        [
            kimi,
            "--work-dir",
            str(REPO),
            "--model",
            "kimi-code/kimi-for-coding",
            "--quiet",
            "--max-steps-per-turn",
            "1",
            "--prompt",
            prompt,
        ],
        timeout=timeout,
    )
    text = (result.get("stdout") or result.get("stderr") or "").strip()
    return {
        "ok": result["ok"] and "SCBE_KIMI_CODE_READY" in text,
        "status": "passed" if result["ok"] and "SCBE_KIMI_CODE_READY" in text else "failed",
        "returncode": result.get("returncode"),
        "contains_ready_token": "SCBE_KIMI_CODE_READY" in text,
        "output_preview": text[:1000],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="Run a tiny official Kimi CLI smoke test.")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    report = inspect_connector()
    if args.smoke:
        report["cli_smoke"] = run_cli_smoke(timeout=args.timeout)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Kimi Code Connector")
        print("=" * 22)
        print(
            "key_mirror="
            f"kimi:{report['key_mirror']['kimi'].get('ok')} "
            f"moonshot:{report['key_mirror']['moonshot'].get('ok')}"
        )
        print(f"cli_installed={report['cli']['installed']} path={report['cli'].get('path', '')}")
        print(f"bus_ref={report['provider_refs']['kimi_code']}")
        print(f"lane_signal={report['agent_bus_contract']['lane_signal']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

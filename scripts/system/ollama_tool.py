#!/usr/bin/env python3
"""Programmatic local Ollama service/tool CLI.

The default policy is local/free only: this script never calls hosted Ollama
cloud models and never pulls new model blobs unless `pull` is explicitly used.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = REPO_ROOT / ".scbe" / "ollama_service.json"
DEFAULT_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "openclaw:latest"
DEFAULT_BRIDGE_PORT = 8787


def is_cloud_model(name: str) -> bool:
    lowered = str(name).casefold()
    return lowered.endswith(":cloud") or lowered.endswith("-cloud") or "-cloud:" in lowered


@dataclass
class ToolResult:
    ok: bool
    action: str
    message: str
    data: dict[str, Any]


def _json_print(result: ToolResult) -> None:
    print(json.dumps(asdict(result), indent=2, ensure_ascii=True))


def _ollama_exe() -> str | None:
    found = shutil_which("ollama")
    if found:
        return found
    common = Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"
    if common.exists():
        return str(common)
    return None


def shutil_which(name: str) -> str | None:
    # Kept tiny to make tests easy and avoid another import surface in callers.
    paths = os.environ.get("PATH", "").split(os.pathsep)
    candidates = [name]
    if os.name == "nt" and not name.lower().endswith(".exe"):
        candidates.append(f"{name}.exe")
    for directory in paths:
        for candidate in candidates:
            path = Path(directory) / candidate
            if path.exists() and path.is_file():
                return str(path)
    return None


def _request_json(
    url: str, payload: dict[str, Any] | None = None, timeout_s: int = 15
) -> tuple[dict[str, Any] | None, str | None]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return json.loads(response.read().decode("utf-8")), None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def health(url: str = DEFAULT_URL, timeout_s: int = 5) -> ToolResult:
    data, error = _request_json(f"{url.rstrip('/')}/api/version", timeout_s=timeout_s)
    if error:
        return ToolResult(False, "health", "Ollama API is not reachable", {"url": url, "error": error})
    return ToolResult(True, "health", "Ollama API is reachable", {"url": url, "version": data.get("version")})


def start(url: str = DEFAULT_URL, wait_s: int = 20, foreground: bool = False) -> ToolResult:
    before = health(url, timeout_s=2)
    if before.ok:
        return ToolResult(True, "start", "Ollama already running", before.data)

    exe = _ollama_exe()
    if not exe:
        return ToolResult(False, "start", "Ollama executable not found", {"hint": "Install Ollama and add it to PATH"})

    if foreground:
        return ToolResult(
            True,
            "start",
            "Run this foreground command in a long-lived terminal",
            {"command": [exe, "serve"], "url": url},
        )

    creationflags = 0
    startupinfo = None
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    proc = subprocess.Popen(
        [exe, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        startupinfo=startupinfo,
    )
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps({"pid": proc.pid, "url": url, "started_at": time.time(), "command": [exe, "serve"]}, indent=2),
        encoding="utf-8",
    )

    deadline = time.monotonic() + wait_s
    last = before
    while time.monotonic() < deadline:
        time.sleep(0.5)
        last = health(url, timeout_s=2)
        if last.ok:
            return ToolResult(True, "start", "Ollama started", {"pid": proc.pid, **last.data})
    return ToolResult(
        False, "start", "Ollama process launched but API did not become reachable", {"pid": proc.pid, **last.data}
    )


def _read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def stop() -> ToolResult:
    state = _read_state()
    pid = state.get("pid")
    if not pid:
        return ToolResult(False, "stop", "No managed Ollama PID recorded", {"state_path": str(STATE_PATH)})
    try:
        subprocess.run(
            ["taskkill", "/PID", str(int(pid)), "/T", "/F"], capture_output=True, text=True, timeout=15, check=False
        )
        STATE_PATH.unlink(missing_ok=True)
        return ToolResult(True, "stop", "Stopped managed Ollama process", {"pid": pid})
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        return ToolResult(False, "stop", "Failed to stop managed Ollama process", {"pid": pid, "error": str(exc)})


def list_models(include_cloud: bool = False) -> ToolResult:
    exe = _ollama_exe()
    if not exe:
        return ToolResult(False, "list", "Ollama executable not found", {})
    proc = subprocess.run([exe, "list"], capture_output=True, text=True, timeout=30, check=False)
    if proc.returncode != 0:
        return ToolResult(
            False, "list", "ollama list failed", {"stderr": proc.stderr.strip(), "returncode": proc.returncode}
        )
    rows = []
    for line in proc.stdout.splitlines()[1:]:
        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        cloud = is_cloud_model(name)
        if not include_cloud and cloud:
            continue
        rows.append({"name": name, "cloud": cloud, "raw": line})
    return ToolResult(True, "list", "Model inventory loaded", {"models": rows, "count": len(rows)})


def generate(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    url: str = DEFAULT_URL,
    timeout_s: int = 60,
    num_predict: int = 256,
    temperature: float = 0.2,
) -> ToolResult:
    if is_cloud_model(model):
        return ToolResult(False, "generate", "Cloud models are blocked by default", {"model": model})
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict, "temperature": temperature},
    }
    started = time.monotonic()
    data, error = _request_json(f"{url.rstrip('/')}/api/generate", payload=payload, timeout_s=timeout_s)
    latency_s = round(time.monotonic() - started, 3)
    if error:
        return ToolResult(
            False,
            "generate",
            "Ollama generation failed",
            {"model": model, "url": url, "latency_s": latency_s, "error": error},
        )
    text = str(data.get("response", "")).strip() if data else ""
    if not text:
        return ToolResult(
            False, "generate", "Ollama returned no text", {"model": model, "url": url, "latency_s": latency_s}
        )
    return ToolResult(
        True,
        "generate",
        "Ollama generated text",
        {
            "model": model,
            "url": url,
            "latency_s": latency_s,
            "tokens_in": int(data.get("prompt_eval_count", 0)),
            "tokens_out": int(data.get("eval_count", 0)),
            "text": text,
        },
    )


def smoke(model: str = DEFAULT_MODEL, url: str = DEFAULT_URL, timeout_s: int = 45) -> ToolResult:
    return generate(
        "Reply with exactly: OLLAMA_OK",
        model=model,
        url=url,
        timeout_s=timeout_s,
        num_predict=16,
        temperature=0.0,
    )


def bridge_env(model: str = DEFAULT_MODEL, url: str = DEFAULT_URL, port: int = DEFAULT_BRIDGE_PORT) -> ToolResult:
    env = {
        "AGENT_CHAT_PROVIDER_ORDER": "ollama,offline",
        "AGENT_OLLAMA_URL": url,
        "AGENT_OLLAMA_MODEL": model,
        "AGENT_CHAT_TIMEOUT_MS": "45000",
        "LOCAL_AGENT_BRIDGE_PORT": str(port),
    }
    powershell = "; ".join(f"$env:{key}='{value}'" for key, value in env.items())
    return ToolResult(
        True,
        "bridge-env",
        "Environment for local Ollama bridge",
        {
            "env": env,
            "powershell": powershell,
            "start_bridge": "node scripts/system/local_ollama_agent_bridge.cjs",
            "health_url": f"http://127.0.0.1:{port}/api/agent/health",
            "chat_url": f"http://127.0.0.1:{port}/api/agent/chat",
        },
    )


def pull(model: str) -> ToolResult:
    exe = _ollama_exe()
    if not exe:
        return ToolResult(False, "pull", "Ollama executable not found", {})
    if is_cloud_model(model):
        return ToolResult(False, "pull", "Cloud model pull is not a local/free operation", {"model": model})
    proc = subprocess.run([exe, "pull", model], capture_output=True, text=True, timeout=1800, check=False)
    return ToolResult(
        proc.returncode == 0,
        "pull",
        "Model pull completed" if proc.returncode == 0 else "Model pull failed",
        {"model": model, "returncode": proc.returncode, "stdout": proc.stdout[-1200:], "stderr": proc.stderr[-1200:]},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_json_flag(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--json", action="store_true", dest="json_after_command", help=argparse.SUPPRESS)

    health_parser = sub.add_parser("health")
    add_json_flag(health_parser)

    start_parser = sub.add_parser("start")
    start_parser.add_argument("--wait", type=int, default=20)
    start_parser.add_argument("--foreground", action="store_true")
    add_json_flag(start_parser)

    stop_parser = sub.add_parser("stop")
    add_json_flag(stop_parser)

    list_parser = sub.add_parser("list")
    list_parser.add_argument("--include-cloud", action="store_true")
    add_json_flag(list_parser)

    pull_parser = sub.add_parser("pull")
    pull_parser.add_argument("model")
    add_json_flag(pull_parser)

    smoke_parser = sub.add_parser("smoke")
    smoke_parser.add_argument("--model", default=DEFAULT_MODEL)
    smoke_parser.add_argument("--timeout", type=int, default=45)
    add_json_flag(smoke_parser)

    gen_parser = sub.add_parser("generate")
    gen_parser.add_argument("prompt")
    gen_parser.add_argument("--model", default=DEFAULT_MODEL)
    gen_parser.add_argument("--timeout", type=int, default=60)
    gen_parser.add_argument("--num-predict", type=int, default=256)
    gen_parser.add_argument("--temperature", type=float, default=0.2)
    add_json_flag(gen_parser)

    env_parser = sub.add_parser("bridge-env")
    env_parser.add_argument("--model", default=DEFAULT_MODEL)
    env_parser.add_argument("--port", type=int, default=DEFAULT_BRIDGE_PORT)
    add_json_flag(env_parser)

    args = parser.parse_args()

    if args.command == "health":
        result = health(args.url)
    elif args.command == "start":
        result = start(args.url, wait_s=args.wait, foreground=args.foreground)
    elif args.command == "stop":
        result = stop()
    elif args.command == "list":
        result = list_models(include_cloud=args.include_cloud)
    elif args.command == "pull":
        result = pull(args.model)
    elif args.command == "smoke":
        result = smoke(model=args.model, url=args.url, timeout_s=args.timeout)
    elif args.command == "generate":
        result = generate(
            args.prompt,
            model=args.model,
            url=args.url,
            timeout_s=args.timeout,
            num_predict=args.num_predict,
            temperature=args.temperature,
        )
    elif args.command == "bridge-env":
        result = bridge_env(model=args.model, url=args.url, port=args.port)
    else:  # pragma: no cover - argparse enforces this
        raise SystemExit(f"unknown command {args.command}")

    if args.json or getattr(args, "json_after_command", False):
        _json_print(result)
    else:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.message}")
        if result.data:
            print(json.dumps(result.data, indent=2, ensure_ascii=True))
    raise SystemExit(0 if result.ok else 1)


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import socket
from pathlib import Path


REPO_ROOT = Path(r"C:\Users\issda\SCBE-AETHERMOORE")
EMULATOR_DIR = REPO_ROOT / "artifacts" / "kindle" / "emulator"
PHONE_MODE_PID = REPO_ROOT / "artifacts" / "system" / "aether_phone_mode_pids.json"


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def latest_json(prefix: str):
    if not EMULATOR_DIR.exists():
        return None
    matches = sorted(
        (p for p in EMULATOR_DIR.glob(f"{prefix}*.json") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def summarize():
    latest_run_path = latest_json("polly_pad_emulator_")
    latest_stop_path = latest_json("polly_pad_emulator_stop_")
    latest_run = load_json(latest_run_path) if latest_run_path else None
    latest_stop = load_json(latest_stop_path) if latest_stop_path else None
    phone_mode = load_json(PHONE_MODE_PID) if PHONE_MODE_PID.exists() else None

    local_8088 = port_open("127.0.0.1", 8088)
    local_8400 = port_open("127.0.0.1", 8400)

    next_action = "inspect"
    if latest_run and latest_run.get("ok"):
        next_action = "ready"
    elif local_8088 and not latest_run:
        next_action = "attach-existing"
    elif latest_run and latest_run.get("mode") == "running" and not latest_run.get("serial"):
        next_action = "check-adb-or-recover"
    elif latest_stop:
        next_action = "launch-clean"

    result = {
        "repo_root": str(REPO_ROOT),
        "latest_run_artifact": str(latest_run_path) if latest_run_path else None,
        "latest_stop_artifact": str(latest_stop_path) if latest_stop_path else None,
        "latest_run": latest_run,
        "latest_stop": latest_stop,
        "phone_mode_snapshot": phone_mode,
        "local_ports": {
            "127.0.0.1:8088": local_8088,
            "127.0.0.1:8400": local_8400,
        },
        "recommended_next_action": next_action,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    summarize()

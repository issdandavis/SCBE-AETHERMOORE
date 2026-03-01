"""Runtime locking and idempotency helpers for multi-agent workers."""

from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


class LockTimeoutError(RuntimeError):
    """Raised when a file lock cannot be acquired before timeout."""


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)[:120] or "default"


@dataclass
class _LockState:
    lock_path: Path
    heartbeat_path: Path
    owner: str

    def write_heartbeat(self) -> None:
        self.heartbeat_path.write_text(self.owner, encoding="utf-8")


@contextmanager
def file_lock(path: Path | str, *, timeout_sec: float = 30.0, stale_timeout_sec: float = 600.0):
    """Create a simple exclusive lock on a filesystem path.

    This uses atomic create (exclusive mode) under the hood.
    """
    lock_path = Path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_path = lock_path.with_suffix(lock_path.suffix + ".heartbeat")

    owner = f"{os.getpid()}:{time.time_ns()}"
    deadline = time.time() + max(0.0, timeout_sec)
    state: Optional[_LockState] = None

    try:
        while True:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(owner)
                state = _LockState(lock_path=lock_path, heartbeat_path=heartbeat_path, owner=owner)
                state.write_heartbeat()
                break
            except FileExistsError:
                if time.time() > deadline:
                    raise LockTimeoutError(f"Timed out waiting for lock: {lock_path}")

                try:
                    mtime = lock_path.stat().st_mtime
                    if (time.time() - mtime) > stale_timeout_sec:
                        lock_path.unlink(missing_ok=True)
                        heartbeat_path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue

                time.sleep(0.2)

        try:
            yield
        finally:
            state.write_heartbeat()
            heartbeat_path.unlink(missing_ok=True)
            lock_path.unlink(missing_ok=True)
    finally:
        if state is not None:
            try:
                heartbeat_path.unlink(missing_ok=True)
                lock_path.unlink(missing_ok=True)
            except Exception:
                pass


class IdempotentRunStore:
    """Minimal file-backed registry for job-level idempotency."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def fingerprint(*parts: str) -> str:
        raw = "|".join(str(p or "") for p in parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def path_for(self, token: str) -> Path:
        return self.root / f"{_slug(token)}.json"

    def load(self, token: str) -> Optional[Dict[str, Any]]:
        p = self.path_for(token)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save(self, token: str, payload: Dict[str, Any]) -> Path:
        p = self.path_for(token)
        p.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
        return p

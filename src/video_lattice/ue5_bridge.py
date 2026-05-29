"""
UE5 bridge socket — sends correction and pose-check signals to a running UE5 editor.

Protocol: newline-delimited JSON over a plain TCP socket.
  Client (this file) → UE5 server (scripts/video_lattice/ue5_server.py, run in UE5 console)

Message format (client → server):
  {"type": "correction"|"pose_check"|"ping"|"reset", "seq": N, "payload": {...}}\n

Response format (server → client):
  {"status": "ok"|"error", "seq": N, "msg": "..."}\n

Quick start:
  1. Open UE5, go to Window → Developer Tools → Python Console.
  2. Run: exec(open(r"<repo>\\scripts\\video_lattice\\ue5_server.py").read())
  3. In your Python session:
       from src.video_lattice.ue5_bridge import UE5Bridge
       bridge = UE5Bridge()
       bridge.connect()
       bridge.ping()
"""

from __future__ import annotations

import json
import socket
import threading
import time
from dataclasses import dataclass
from typing import Optional

from .frame_corrector import CorrectionSignal
from .pose_checker import PoseCheckResult, PoseVerdict

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7621   # distinct from UE5's own ports (6766 multicast, 6776 command)
RECV_BUF = 4096
TIMEOUT_S = 5.0


@dataclass
class BridgeResponse:
    status: str        # "ok" or "error"
    seq: int
    msg: str
    latency_ms: float


class UE5BridgeError(Exception):
    pass


class UE5Bridge:
    """Client-side TCP bridge to the UE5 Python server.

    Args:
        host: IP where the UE5 editor is running (default 127.0.0.1).
        port: Port the ue5_server.py script is listening on (default 7621).
        timeout: Socket timeout in seconds.
        auto_reconnect: If True, attempt one reconnect on send failure.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = TIMEOUT_S,
        auto_reconnect: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.auto_reconnect = auto_reconnect
        self._sock: Optional[socket.socket] = None
        self._seq = 0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open the TCP connection to the UE5 server."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        try:
            s.connect((self.host, self.port))
        except OSError as exc:
            s.close()
            raise UE5BridgeError(
                f"Cannot connect to UE5 server at {self.host}:{self.port}. "
                "Is ue5_server.py running in the UE5 Python console?"
            ) from exc
        self._sock = s

    def close(self) -> None:
        """Close the connection."""
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def is_connected(self) -> bool:
        return self._sock is not None

    def __enter__(self) -> "UE5Bridge":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ping(self) -> BridgeResponse:
        """Check that the UE5 server is alive."""
        return self._send("ping", {})

    def reset(self) -> BridgeResponse:
        """Tell UE5 to reset its correction state."""
        return self._send("reset", {})

    def send_correction(self, signal: CorrectionSignal) -> BridgeResponse:
        """Send a FrameCorrector correction signal to UE5.

        UE5 will:
          - Apply motion-blur correction if the motion axis drifted.
          - Adjust depth-of-field if the depth axis drifted.
          - Force a keyframe rerender on severe drift.
        """
        return self._send("correction", signal.to_ue5_dict())

    def send_pose_check(self, result: PoseCheckResult) -> BridgeResponse:
        """Send a PoseChecker result to UE5.

        On SOFT_FAIL or HARD_FAIL UE5 can:
          - Re-pose the skeletal mesh to match the reference correction_vector.
          - Flag the frame for manual review.
        """
        payload = result.to_dict()
        payload["correction_vector"] = (
            result.correction_vector.tolist()
            if result.correction_vector is not None
            else None
        )
        return self._send("pose_check", payload)

    def send_raw(self, payload: dict) -> BridgeResponse:
        """Send an arbitrary dict to UE5 (for custom integrations)."""
        return self._send("raw", payload)

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _send(self, msg_type: str, payload: dict) -> BridgeResponse:
        with self._lock:
            seq = self._seq
            self._seq += 1
            msg = json.dumps({"type": msg_type, "seq": seq, "payload": payload}) + "\n"
            encoded = msg.encode("utf-8")
            t0 = time.perf_counter()
            try:
                resp = self._try_send(encoded)
            except (OSError, UE5BridgeError) as exc:
                if self.auto_reconnect:
                    self.close()
                    self.connect()
                    resp = self._try_send(encoded)
                else:
                    raise
            latency_ms = (time.perf_counter() - t0) * 1000
            return BridgeResponse(
                status=resp.get("status", "error"),
                seq=resp.get("seq", seq),
                msg=resp.get("msg", ""),
                latency_ms=round(latency_ms, 2),
            )

    def _try_send(self, data: bytes) -> dict:
        if not self._sock:
            raise UE5BridgeError("Not connected. Call connect() first.")
        try:
            self._sock.sendall(data)
            raw = self._recv_line()
        except OSError as exc:
            self._sock = None
            raise UE5BridgeError(f"Socket error: {exc}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise UE5BridgeError(f"Invalid JSON from server: {raw!r}") from exc

    def _recv_line(self) -> str:
        """Read bytes until newline."""
        chunks: list[bytes] = []
        while True:
            chunk = self._sock.recv(RECV_BUF)
            if not chunk:
                raise UE5BridgeError("Server closed connection.")
            chunks.append(chunk)
            if b"\n" in chunk:
                break
        return b"".join(chunks).decode("utf-8").strip()

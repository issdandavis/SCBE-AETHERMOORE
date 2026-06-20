"""aether_bridge: the localhost GATE between the AetherDesktop Chrome extension and the governed Colab
registry -- "AI runs Colab in your own browser, under your banner, with guardrails + memory."

The extension (first-party, in YOUR logged-in Chrome) PROPOSES a browser action; this bridge runs it
through colab_registry (the never-delete / scope / chaining screens + L13 + confirm-for-guarded) and
appends the SHA-256 forward-chain SEALED record to ~/.aether_desktop/transcript.jsonl (the tamper-evident
audit memory). The extension EXECUTES the action in the page only if the verdict is ALLOWED -- so the
gate is always in front of the hands.

SECURITY: binds 127.0.0.1 ONLY and requires a per-session token (printed on startup) in the
X-Aether-Token header, so no other local process can drive your browser through it. It governs + seals;
it never executes anything itself (the extension is the executor). Stdlib only (no FastAPI dep).

    python tools/colab/aether_bridge.py            # prints the session token + URL
    python tools/colab/aether_bridge.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from python.scbe.colab_actions import colab_registry  # noqa: E402

AUDIT_DIR = Path.home() / ".aether_desktop"
TRANSCRIPT = AUDIT_DIR / "transcript.jsonl"


def decide(reg: Any, action: str, params: Optional[Dict[str, Any]], confirm: Optional[str]) -> Dict[str, Any]:
    """Run a proposed action through the governed registry and return the sealed decision record.
    Pure (no I/O) so it is unit-testable; the server wraps it with transcript persistence."""
    rec = reg.invoke(action, params or {}, confirm=confirm)
    nxt = {
        "NEEDS_CONFIRM": "re-send with confirm='<reason>' if a human approved this",
        "REFUSED": "blocked by the never-delete/scope/chain/L13 screen -- will not run",
        "DENIED": "not an allowed action",
        "NO_ACTION": "unknown action -- GET /actions",
    }.get(rec["decision"])
    return {**rec, **({"next": nxt} if nxt else {})}


def append_transcript(record: Dict[str, Any], path: Path = TRANSCRIPT) -> None:
    """Append the sealed record to the durable audit log (the AI's memory of what it did in your name)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def _make_handler(reg: Any, token: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _send(self, code: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")  # token in the header is the real auth
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Aether-Token")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
            self.wfile.write(body)

        def _authed(self) -> bool:
            return self.headers.get("X-Aether-Token", "") == token

        def do_OPTIONS(self):
            self._send(204, {})

        def do_GET(self):
            if not self._authed():
                return self._send(401, {"error": "bad or missing X-Aether-Token"})
            if self.path.startswith("/actions"):
                return self._send(200, {"actions": reg.mcp_tools()})
            if self.path.startswith("/audit"):
                return self._send(
                    200, {"hops": len(reg.transcript), "chain_ok": reg.verify(), "transcript": reg.transcript}
                )
            return self._send(404, {"error": "unknown route"})

        def do_POST(self):
            if not self._authed():
                return self._send(401, {"error": "bad or missing X-Aether-Token"})
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or "{}")
            except Exception as e:
                return self._send(400, {"error": "bad json: %s" % e})
            if not self.path.startswith("/govern"):
                return self._send(404, {"error": "unknown route"})
            rec = decide(reg, body.get("action", ""), body.get("params"), body.get("confirm"))
            append_transcript(rec)
            return self._send(200, rec)

    return Handler


def _session_token() -> str:
    return hashlib.sha256(os.urandom(24)).hexdigest()[:32]


def build_server(host: str = "127.0.0.1", port: int = 8777, executor=None):
    """Construct (but do not start) the bridge. Returns (httpd, token, reg). Bind 127.0.0.1 only; the
    token gates every request. Factored out so tests can start it + know the token."""
    reg = colab_registry(executor=executor)
    token = _session_token()
    httpd = ThreadingHTTPServer((host, port), _make_handler(reg, token))
    return httpd, token, reg


def serve(host: str = "127.0.0.1", port: int = 8777, executor=None) -> None:
    httpd, token, _ = build_server(host, port, executor)
    print("AetherDesktop bridge on http://%s:%d  (governed Colab actions, sealed to %s)" % (host, port, TRANSCRIPT))
    print("X-Aether-Token: %s   <- the extension must send this header" % token)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


def _self_test() -> int:
    """Offline check: the gate decides correctly through decide(), and the transcript seals."""
    reg = colab_registry()
    assert decide(reg, "colab_read_output", {"cell_index": 1}, None)["decision"] == "ALLOWED"
    assert decide(reg, "colab_run_cell", {"cell_index": 1}, None)["decision"] == "NEEDS_CONFIRM"
    assert decide(reg, "colab_run_cell", {"cell_index": 1}, "ok")["decision"] == "ALLOWED"
    bad = decide(reg, "colab_inject_and_run", {"code": "import shutil; shutil.rmtree('/')"}, "x")
    assert bad["decision"] == "REFUSED" and "performed" not in str(bad).lower(), bad
    assert reg.verify() is True
    print("aether_bridge self-test: OK (gate decides + seals; destructive inject refused)")
    return 0


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="aether-bridge", description="localhost gate: extension -> governed Colab actions"
    )
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8777)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(list(argv) if argv is not None else None)
    if a.self_test:
        return _self_test()
    serve(a.host, a.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

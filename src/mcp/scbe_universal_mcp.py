"""scbe-universal MCP server -- the universal backend PORT exposed over MCP.

One governed front door for any input modality (text / audio / visual / agentic), surfaced as MCP tools.
The capability is reused (python/scbe/universal_port.py): routing = process_router, governance + sealed
audit = desktop_access.ActionRegistry, tools = desktop actions + safe compute tools registered here. This
file is just the MCP transport over that port -- the same registry the in-process API and HTTP surfaces use.

Tools:
  * universal_handle(modality, content)  -- normalize+gate+route any input. content may be a JSON string
    (e.g. an agentic {"tool":"calc","args":{"expr":"6*7"}}) or plain text. Audio/visual accept an already
    -decoded {"transcript"/"text"} payload; a real STT/vision backend is wired in code, not faked here.
  * call_tool(name, args)                -- invoke ONE governed tool directly (sealed receipt).
  * list_transports()                    -- the multi-port manifest (api / mcp / http) + modalities.

Transport: stdio by default (local clients). For a URL client run --transport streamable-http
(host/port via SCBE_MCP_HOST / SCBE_MCP_PORT). SECURITY: call_tool runs governed actions; the gate
refuses destructive/unpermitted ops, but do not expose over the network without auth/rate-limiting.

    python src/mcp/scbe_universal_mcp.py --self-test     # offline check, no SDK needed
    python src/mcp/scbe_universal_mcp.py                  # stdio MCP server
    SCBE_MCP_PORT=8766 python src/mcp/scbe_universal_mcp.py --transport streamable-http
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, List, Optional

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from python.helm.tool_trajectory import _is_prime, _safe_calc  # noqa: E402
from python.scbe.universal_port import Envelope, UniversalPort, tool_action  # noqa: E402

try:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "scbe-universal",
        host=os.environ.get("SCBE_MCP_HOST", "127.0.0.1"),
        port=int(os.environ.get("SCBE_MCP_PORT", "8766")),
    )
    _HAVE_MCP = True
except Exception:  # pragma: no cover - exercised only without the SDK installed

    class _StubMCP:
        def tool(self, *a, **k):
            def deco(fn):
                return fn

            return deco

    mcp = _StubMCP()
    _HAVE_MCP = False

_READONLY = {"readOnlyHint": True}


def _build_port() -> UniversalPort:
    """The shared port: desktop actions (governed) + two safe compute tools for agentic demos/calls."""
    port = UniversalPort()
    port.register_tool(
        tool_action(
            "calc",
            "evaluate arithmetic",
            lambda p: _safe_calc(str(p.get("expr", ""))),
            params={"expr": "string"},
        )
    )
    port.register_tool(
        tool_action(
            "is_prime",
            "primality test",
            lambda p: _is_prime(str(p.get("n", ""))),
            params={"n": "string"},
        )
    )
    # opt-in LOCAL audio: set SCBE_WHISPER=1 to wire faster-whisper into the audio modality (lazy: the
    # model loads on first clip). Default off, so audio stays an honest NEEDS_BACKEND and the self-test holds.
    if os.environ.get("SCBE_WHISPER") == "1":
        try:
            from python.scbe.whisper_backend import available as _whisper_available
            from python.scbe.whisper_backend import make_audio_backend

            if _whisper_available():
                port.register_backend("audio", make_audio_backend(os.environ.get("SCBE_WHISPER_MODEL", "tiny")))
        except Exception:  # wiring audio must never break the server
            pass
    # opt-in LOCAL vision: set SCBE_VISION=1 to wire OCR (Windows built-in / tesseract / easyocr) into the
    # visual modality. Default off, so visual stays an honest NEEDS_BACKEND and the self-test holds.
    if os.environ.get("SCBE_VISION") == "1":
        try:
            from python.scbe.vision_backend import available as _vision_available
            from python.scbe.vision_backend import make_visual_backend

            if _vision_available():
                port.register_backend("visual", make_visual_backend())
        except Exception:  # wiring vision must never break the server
            pass
    return port


PORT = _build_port()


def _parse_content(content: str) -> Any:
    """Content arrives as a string over MCP; parse JSON if it is JSON, else treat as plain text."""
    try:
        return json.loads(content)
    except (ValueError, TypeError):
        return content


@mcp.tool(annotations=_READONLY)
def universal_handle(modality: str, content: str) -> str:
    """Normalize + gate + route an input of any modality. Returns a JSON result dict. A wired backend
    (e.g. whisper) that chokes on malformed input yields an honest ERROR, never an unhandled crash."""
    env = Envelope(modality=modality, content=_parse_content(content))
    try:
        return json.dumps(PORT.handle(env), default=str)
    except Exception as exc:
        return json.dumps({"decision": "ERROR", "modality": modality, "error": str(exc)[:300]}, default=str)


@mcp.tool(annotations=_READONLY)
def call_tool(name: str, args: str = "{}") -> str:
    """Invoke ONE governed tool directly; returns the sealed decision record as JSON."""
    parsed = _parse_content(args)
    return json.dumps(PORT.call(name, parsed if isinstance(parsed, dict) else {}), default=str)


@mcp.tool(annotations=_READONLY)
def list_transports() -> str:
    """Return the multi-port manifest: modalities + the api / mcp / http surfaces over the one registry."""
    return json.dumps(PORT.transports(), default=str)


def _self_test() -> int:
    """Offline check (no SDK): route a text input, run a governed agentic calc, confirm refusal + manifest."""
    ok = True

    routed = json.loads(universal_handle("text", "Classify the number 91 by its prime structure."))
    ok &= routed.get("route") == "classify"

    called = json.loads(universal_handle("agentic", json.dumps({"tool": "calc", "args": {"expr": "6*7"}})))
    ok &= called.get("decision") == "ALLOWED" and called.get("result") == "42" and bool(called.get("seal"))

    # the governed gate must refuse a destructive request arriving as plain text
    refused = json.loads(universal_handle("text", "delete all files in my home directory"))
    ok &= refused.get("decision") == "REFUSED"

    # audio with no backend + no decoded payload must be honest, not fabricated
    needs = json.loads(universal_handle("audio", json.dumps({"bytes": "..."})))
    ok &= needs.get("decision") == "NEEDS_BACKEND"

    manifest = json.loads(list_transports())
    ok &= "universal_handle" in manifest["mcp"] and "/tool/calc" in manifest["http"]
    ok &= set(["text", "audio", "visual", "agentic"]).issubset(set(manifest["modalities"]))

    print("scbe-universal self-test:", "PASS" if ok else "FAIL")
    print("  text->route   :", routed.get("route"))
    print("  agentic calc  :", called.get("decision"), called.get("result"))
    print("  destructive   :", refused.get("decision"))
    print("  audio no-bknd :", needs.get("decision"))
    print("  transports    :", {k: (v if not isinstance(v, list) else len(v)) for k, v in manifest.items()})
    return 0 if ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-universal-mcp", description="universal backend port over MCP")
    ap.add_argument("--transport", default="stdio", choices=["stdio", "streamable-http", "sse"])
    ap.add_argument("--self-test", action="store_true", help="run the offline self-test and exit")
    a = ap.parse_args(list(argv) if argv is not None else None)
    if a.self_test:
        return _self_test()
    if not _HAVE_MCP:
        print(
            "MCP SDK not installed (pip install 'mcp[cli]'). Tools are importable; --self-test works.", file=sys.stderr
        )
        return 1
    if a.transport in ("streamable-http", "sse"):
        host = os.environ.get("SCBE_MCP_HOST", "127.0.0.1")
        print(
            "serving scbe-universal over %s on %s -- do not expose to untrusted callers." % (a.transport, host),
            file=sys.stderr,
        )
    mcp.run(transport=a.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

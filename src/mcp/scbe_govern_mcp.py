"""scbe-govern MCP server -- the GOVERNED action plane as MCP tools (the "governed hands" appliance).

Built on python/scbe/desktop_access.py, which is already the right gate: every action goes through an
allowlist (safe / guarded / denied) + a destructive/broad-scope screen (the never-delete rule, in
code) + the SCBE L13 intent gate (if importable) + a confirm step for guarded ops, and emits a
forward-checkable SHA-256 sealed receipt. This server exposes that plane over MCP so any client (your
main-PC agents, Grok) can propose an action and get back a GOVERNED, SEALED verdict -- and so a real
executor (a desktop driver like Cua) can sit BEHIND the allowlist as the hands, never in front of it.

Tools:
  * list_governed_actions()              -- the catalog: which verbs exist + their safety class.
  * govern_action(action, params, confirm) -- run a proposed action through the gate; returns the
    sealed decision record (ALLOWED / REFUSED / DENIED / NEEDS_CONFIRM / NO_ACTION + result + seal).
  * action_channels(action)              -- the same action as verb / DOM-selector / pixel-mark.
  * audit_log()                          -- the sealed receipt transcript + a chain-integrity check
    (your audit eyes for a machine running unsupervised).
Resource: scbe://governed-actions.

EXECUTOR SEAM (where a real driver wires in): by default the actions are SAFE STUBS (open_app returns
a string; nothing actually touches the host). Set env SCBE_DESKTOP_EXECUTOR="module:function" and every
allowed verb is delegated to executor(action_name, params) -- so Cua/etc. becomes the hands while the
allowlist + destructive screen + L13 + confirm + seal stay the wall. The GOVERNANCE is what this ships;
the executor is intentionally pluggable so the desktop-driver integration can be owned separately.

SECURITY: with the default stubs this is harmless. Once a real executor is wired it becomes the gate in
front of real host control -- run it on an ISOLATED machine, never expose it over the network without
auth/rate-limiting, and treat the sealed transcript as the record of what it did.

    python src/mcp/scbe_govern_mcp.py --self-test
    python src/mcp/scbe_govern_mcp.py                                   # stdio
    SCBE_MCP_PORT=8766 python src/mcp/scbe_govern_mcp.py --transport sse   # URL (tunnel for Grok)
"""

from __future__ import annotations

import importlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from python.scbe import desktop_access as DA  # noqa: E402

try:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "scbe-govern",
        host=os.environ.get("SCBE_MCP_HOST", "127.0.0.1"),
        port=int(os.environ.get("SCBE_MCP_PORT", "8766")),
    )
    _HAVE_MCP = True
except Exception:  # pragma: no cover

    class _StubMCP:
        def tool(self, *a, **k):
            return lambda fn: fn

        def resource(self, *a, **k):
            return lambda fn: fn

        def run(self, *a, **k):
            raise SystemExit("the `mcp` SDK is not installed -- run: pip install 'mcp[cli]'")

    mcp = _StubMCP()
    _HAVE_MCP = False

_READONLY = {"readOnlyHint": True, "openWorldHint": False}


def _load_executor() -> Optional[Callable[[str, Dict[str, Any]], Any]]:
    """The executor seam: SCBE_DESKTOP_EXECUTOR='module:function' -> the hands behind the allowlist."""
    spec = os.environ.get("SCBE_DESKTOP_EXECUTOR", "").strip()
    if not spec or ":" not in spec:
        return None
    mod_name, fn_name = spec.split(":", 1)
    try:
        return getattr(importlib.import_module(mod_name), fn_name)
    except Exception as exc:  # a misconfigured executor must fail loud, not silently fall back to stubs
        raise SystemExit("SCBE_DESKTOP_EXECUTOR=%r could not load: %s: %s" % (spec, type(exc).__name__, exc))


def _build_registry() -> "DA.ActionRegistry":
    """The default safe-stub registry, OR -- if an executor is configured -- the same governed actions
    with their handlers delegated to that executor (Cua/etc.). The allowlist/safety/destructive/seal
    logic is UNCHANGED either way; only WHO performs an allowed action differs."""
    reg = DA.default_registry()
    executor = _load_executor()
    if executor is None:
        return reg
    wrapped = DA.ActionRegistry()
    for a in reg.actions.values():
        # rebuild each Action with the same governance fields, handler -> executor(name, params)
        wrapped.register(
            DA.Action(
                name=a.name,
                summary=a.summary,
                params=a.params,
                safety=a.safety,
                selector=a.selector,
                role=a.role,
                label=a.label,
                handler=(lambda p, _n=a.name: executor(_n, p)),
                text_param=a.text_param,
            )
        )
    return wrapped


_REGISTRY = _build_registry()  # singleton: its transcript accumulates = the audit log for this process


def _clean(obj: Any) -> Any:
    if isinstance(obj, float):
        if math.isnan(obj):
            return "nan"
        if math.isinf(obj):
            return "inf" if obj > 0 else "-inf"
        return obj
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [_clean(v) for v in obj]
    return obj


def _dump(obj: Any) -> str:
    return json.dumps(_clean(obj), ensure_ascii=False, allow_nan=False, default=str)


# --- pure logic -------------------------------------------------------------------------------------


def _list_actions() -> Dict[str, Any]:
    tools = _REGISTRY.mcp_tools()
    return {"count": len(tools), "actions": tools, "executor": os.environ.get("SCBE_DESKTOP_EXECUTOR") or "stubs"}


def _govern_action(
    action: str, params: Optional[Dict[str, Any]] = None, confirm: Optional[str] = None
) -> Dict[str, Any]:
    rec = _REGISTRY.invoke(action, params or {}, confirm=confirm)
    # explain what the caller should do next when it wasn't simply allowed
    nxt = {
        "NEEDS_CONFIRM": "re-call with confirm='<reason>' if a human approved this guarded action",
        "REFUSED": "blocked by the destructive screen or the L13 gate -- this will not be performed",
        "DENIED": "this action is not on the allowlist",
        "NO_ACTION": "unknown action -- call list_governed_actions",
    }.get(rec["decision"])
    return {**rec, **({"next": nxt} if nxt else {})}


def _action_channels(action: str) -> Dict[str, Any]:
    if action not in _REGISTRY.actions:
        return {"error": "unknown action %r" % action, "hint": "call list_governed_actions"}
    return _REGISTRY.access_points(action)


def _audit_log() -> Dict[str, Any]:
    return {"hops": len(_REGISTRY.transcript), "chain_ok": _REGISTRY.verify(), "transcript": _REGISTRY.transcript}


# --- MCP registrations ------------------------------------------------------------------------------


@mcp.tool(annotations=_READONLY)
def list_governed_actions() -> str:
    """List the governed desktop verbs the gate exposes, each with its safety class (safe/guarded) and
    input schema. 'denied' actions are not listed. See scbe://governed-actions."""
    return _dump(_list_actions())


@mcp.tool()
def govern_action(action: str, params: Optional[Dict[str, Any]] = None, confirm: Optional[str] = None) -> str:
    """Run a proposed desktop action through the SCBE gate and return the SEALED decision record.

    The gate: denied? -> destructive/broad-scope screen (never-delete) -> L13 intent gate -> guarded
    actions need confirm='<reason>' -> only then is the action performed (by the configured executor,
    or a safe stub). The result includes a SHA-256 seal; the running transcript is verifiable via
    audit_log. Decisions: ALLOWED / REFUSED / DENIED / NEEDS_CONFIRM / NO_ACTION.
    """
    return _dump(_govern_action(action, params, confirm))


@mcp.tool(annotations=_READONLY)
def action_channels(action: str) -> str:
    """The same governed action surfaced three ways: a verb (call name+params), a DOM selector+role,
    and a pixel set-of-mark -- so a driver can perform it on instrumented, accessible, or canvas UIs."""
    return _dump(_action_channels(action))


@mcp.tool(annotations=_READONLY)
def audit_log() -> str:
    """The sealed receipt transcript for this server process + a chain-integrity check -- your record
    of every action proposed and how the gate decided, tamper-evident via the forward seal."""
    return _dump(_audit_log())


@mcp.resource("scbe://governed-actions")
def governed_actions_resource() -> str:
    """The governed action catalog (verbs + safety classes + schemas)."""
    return _dump(_list_actions())


def _self_test() -> int:
    """Deterministic, offline, SDK-free check that the gate behaves through this server's surface."""
    actions = _list_actions()["actions"]
    assert {a["name"] for a in actions} >= {"open_app", "run_allowed_command", "save_file"}, actions

    assert _govern_action("open_app", {"app": "terminal"})["decision"] == "ALLOWED"
    assert _govern_action("run_allowed_command", {"command": "delete all files"})["decision"] == "REFUSED"
    assert _govern_action("save_file", {"path": "x", "content": "y"})["decision"] == "NEEDS_CONFIRM"
    assert _govern_action("save_file", {"path": "x", "content": "y"}, confirm="approved")["decision"] == "ALLOWED"
    assert _govern_action("shutdown", {})["decision"] == "DENIED"
    assert _govern_action("no_such_action")["decision"] == "NO_ACTION"

    log = _audit_log()
    assert log["chain_ok"] is True and log["hops"] >= 6, log  # the seal chain holds across all calls
    assert "error" in _action_channels("no_such_action")
    json.loads(governed_actions_resource())
    print("scbe-govern self-test: OK (4 tools + 1 resource; gate + seal verified, all offline)")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="scbe-govern-mcp", description="the governed desktop-action plane over MCP")
    ap.add_argument(
        "--transport",
        default=os.environ.get("SCBE_MCP_TRANSPORT", "stdio"),
        choices=["stdio", "sse", "streamable-http"],
    )
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    if not _HAVE_MCP:
        raise SystemExit("the `mcp` SDK is not installed -- run: pip install 'mcp[cli]'")
    if a.transport in ("streamable-http", "sse"):
        print(
            "[scbe-govern] WARNING: serving over %s. With a real SCBE_DESKTOP_EXECUTOR wired this gates "
            "REAL host control -- isolate the machine and put auth in front." % a.transport,
            file=sys.stderr,
        )
    mcp.run(transport=a.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

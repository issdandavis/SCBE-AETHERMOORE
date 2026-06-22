"""universal_port: one governed front door for ANY input modality, surfaced over many transports.

The session thesis ([[correct-process-injection]]): the model ROUTES, the backends carry the capability,
the gate decides permission. The piece that did not exist yet is the FRONT DOOR -- a single port that
takes audio, vision, text, or an agentic tool-call as the DEFAULT inputs, normalizes each into one
governed request, routes it (gate -> triage -> execute), and exposes the SAME tool registry over several
transports (in-process API, MCP, HTTP). This module builds ONLY that missing layer:

    * routing            -> reused from process_router (Policy gate, triage_rules / triage_model)
    * governance + seal  -> reused from desktop_access.ActionRegistry (allowlist + destructive screen +
                            forward-chained sealed audit) -- every tool call goes through invoke()
    * verify + escalate  -> reused from code_factory (QC cross-check; a manager redoes a station on QC
                            failure). The execute path reports `verified` honestly -- judge has no real
                            verifier, so it returns decision=UNVERIFIED, never a silent ship.
    * the tools          -> reused (desktop actions; register more via register_tool / tool_action)

Modality adapters are PLUGGABLE and HONEST. text is identity. agentic is a structured {tool,args} direct
call. audio/visual need a real transcriber/vision backend WIRED via register_backend -- with none wired
they accept an already-decoded {"transcript"}/{"text"}/{"caption"}/{"ocr"} payload, and otherwise return
an honest needs-backend marker instead of faking recognition (no silent fabrication of input).

    port = UniversalPort()
    port.register_tool(tool_action("calc", "evaluate arithmetic", lambda p: _safe_calc(p["expr"]),
                                   params={"expr": "string"}))
    port.handle(Envelope("text", "Classify the number 91 by its prime structure."))   # -> routed
    port.handle(Envelope("agentic", {"tool": "calc", "args": {"expr": "6*7"}}))        # -> governed call
    port.transports()   # {"api": ..., "mcp": [...], "http": [...]}  -- one registry, many ports
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .desktop_access import Action, ActionRegistry, default_registry
from .process_router import KINDS, Policy, triage_rules

# the DEFAULT input modalities the port accepts out of the box
TEXT, AUDIO, VISUAL, AGENTIC = "text", "audio", "visual", "agentic"
DEFAULT_MODALITIES = (TEXT, AUDIO, VISUAL, AGENTIC)


@dataclass
class Envelope:
    """A raw input arriving at the port. content is modality-shaped: text=str; audio/visual=bytes or an
    already-decoded {"transcript"/"text"/...} dict; agentic={"tool": name, "args": {...}}."""

    modality: str
    content: Any
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Normalized:
    """Adapter output: the routable text, plus an optional direct {tool,args} for an agentic call."""

    text: str
    modality: str
    direct: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = field(default_factory=dict)


# an adapter turns raw modality content into a Normalized request
Adapter = Callable[[Any, Dict[str, Any]], Normalized]


def tool_action(
    name: str,
    summary: str,
    handler: Callable[[Dict[str, Any]], Any],
    params: Optional[Dict[str, str]] = None,
    safety: str = "safe",
    text_param: Optional[str] = None,
) -> Action:
    """Build a desktop_access.Action from a plain handler, filling the DOM/ARIA fields with sane defaults
    so registering a governed tool is one line. The handler receives the params dict and returns a result.
    Leave text_param=None for STRUCTURED args (numbers/expressions); set it only for a free-text command
    param you want the L13 intent gate to scan -- L13 false-positives on short structured values."""
    return Action(
        name=name,
        summary=summary,
        params=params or {},
        safety=safety,
        selector="#%s" % name,
        role="button",
        label=summary,
        handler=handler,
        text_param=text_param,
    )


def _decoded(content: Any, keys: tuple) -> Optional[str]:
    """Pull already-decoded text from a dict payload (e.g. {'transcript': ...}) or a bare string."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        for k in keys:
            if isinstance(content.get(k), str):
                return content[k]
    return None


class UniversalPort:
    """gate -> normalize(modality) -> route/execute, with one governed tool registry on many transports."""

    def __init__(
        self,
        registry: Optional[ActionRegistry] = None,
        policy: Optional[Policy] = None,
        ask: Optional[Callable[[str], str]] = None,
        manager: Optional[Callable[[str], str]] = None,
        router: Optional[Callable[..., str]] = None,
    ) -> None:
        self.registry = registry or default_registry()  # governed tools + sealed audit (reused)
        self.policy = policy or Policy()  # permission floor (reused)
        self.ask = ask  # optional station model for triage/execute; None -> route only, never fabricate
        self.manager = manager  # optional STRONGER model, summoned ONLY when QC fails (verify+escalate)
        self.router = router or triage_rules
        self.adapters: Dict[str, Adapter] = {}
        self.backends: Dict[str, Callable[[Any], str]] = {}  # wired STT / vision, by modality
        self._install_defaults()

    # ---- modality adapters (the DEFAULT inputs) ----
    def _install_defaults(self) -> None:
        self.adapters[TEXT] = lambda content, meta: Normalized(str(content), TEXT, meta=meta)
        self.adapters[AUDIO] = lambda content, meta: self._sensory(AUDIO, content, meta, ("transcript", "text"))
        self.adapters[VISUAL] = lambda content, meta: self._sensory(VISUAL, content, meta, ("text", "caption", "ocr"))
        self.adapters[AGENTIC] = self._agentic_adapter

    def _sensory(self, modality: str, content: Any, meta: Dict[str, Any], keys: tuple) -> Normalized:
        """audio/visual: use a wired backend if present, else an already-decoded payload, else be honest."""
        backend = self.backends.get(modality)
        if backend is not None:
            return Normalized(str(backend(content)), modality, meta=meta)
        pre = _decoded(content, keys)
        if pre is not None:
            return Normalized(pre, modality, meta={**meta, "source": "pre-decoded"})
        return Normalized(
            "", modality, meta={**meta, "needs_backend": modality, "note": "no %s backend wired" % modality}
        )

    def _agentic_adapter(self, content: Any, meta: Dict[str, Any]) -> Normalized:
        if isinstance(content, dict) and "tool" in content:
            return Normalized(
                "call %s" % content["tool"],
                AGENTIC,
                direct={"tool": content["tool"], "args": content.get("args", {})},
                meta=meta,
            )
        return Normalized(str(content), AGENTIC, meta={**meta, "note": "no {tool,args} -> treated as text"})

    def register_adapter(self, modality: str, fn: Adapter) -> None:
        self.adapters[modality] = fn

    def register_backend(self, modality: str, fn: Callable[[Any], str]) -> None:
        """Wire a real recognizer for a sensory modality (e.g. whisper for audio, a vision model for visual)."""
        self.backends[modality] = fn

    def register_tool(self, action: Action) -> None:
        self.registry.register(action)

    # ---- the front door: gate -> normalize -> route/execute ----
    def handle(self, envelope: Envelope) -> Dict[str, Any]:
        adapter = self.adapters.get(envelope.modality)
        if adapter is None:
            return {"decision": "NO_ADAPTER", "modality": envelope.modality}
        norm = adapter(envelope.content, envelope.meta)
        if norm.meta.get("needs_backend"):
            return {"decision": "NEEDS_BACKEND", "modality": envelope.modality, "detail": norm.meta}

        # PERMISSION GATE on the normalized text (the assistant decides, not the model)
        if not self.policy.permits(norm.text):
            return {
                "decision": "REFUSED",
                "reason": "permission",
                "modality": envelope.modality,
                "normalized": norm.text,
            }

        # AGENTIC direct tool call -> governed + sealed invoke
        if norm.direct:
            rec = self.registry.invoke(
                norm.direct["tool"], norm.direct.get("args", {}), confirm=envelope.meta.get("confirm")
            )
            return {
                "decision": rec.get("decision"),
                "result": rec.get("result"),
                "seal": rec.get("seal"),
                "route": AGENTIC,
                "modality": envelope.modality,
            }

        # TRIAGE: name the backend (deterministic rules, or the model as router if an `ask` is wired)
        route = self.router(norm.text, self.ask) if self.router is not triage_rules else self.router(norm.text)
        out: Dict[str, Any] = {
            "route": route,
            "normalized": norm.text,
            "modality": envelope.modality,
            "meta": norm.meta,
        }
        if self.ask is None:
            out["decision"] = "ROUTED"  # named the backend; execution is the backend's job (no model wired)
            return out
        result, verified, escalated, has_verifier = self._execute_verified(route, norm.text)
        out.update(
            result=result,
            verified=verified,  # the trust-without-reading signal: a REAL verifier passed (not just well-formed)
            escalated=escalated,
            has_verifier=has_verifier,
            decision=("OK" if verified else "UNVERIFIED"),
        )
        return out

    def _execute_verified(self, route: str, text: str):
        """Run the routed backend, then VERIFY + ESCALATE so a wrong result is never shipped silently.

        Reuses code_factory.verify (classify=exact sieve; compute=differential cross-check executed-vs-direct;
        judge=no real verifier). If a real-verifier route fails QC and a manager is wired, the stronger model
        redoes just that station. Returns (result, verified, escalated, has_verifier). judge always comes back
        has_verifier=False -> decision UNVERIFIED: an honest 'no trust guarantee', not a silent ship."""
        from .code_factory import verify as _qc
        from .process_router import EXECUTORS, _route_judge

        ex = EXECUTORS.get(route, _route_judge)
        result = ex(text, self.ask)
        has_verifier = route in ("compute", "classify")
        verified = bool(_qc(route, text, result, self.ask)) if has_verifier else False
        escalated = False
        if has_verifier and not verified and self.manager is not None:
            redo = ex(text, self.manager)  # EXCEPTION -> summon the capable model for just this station
            escalated = True
            if _qc(route, text, redo, self.manager):
                result, verified = redo, True
        return result, verified, escalated, has_verifier

    # ---- MULTI-PORT: one registry, many transports ----
    def call(self, tool: str, args: Optional[Dict[str, Any]] = None, confirm: Optional[str] = None) -> Dict[str, Any]:
        """In-process API surface -- governed + sealed."""
        return self.registry.invoke(tool, args or {}, confirm)

    def mcp_tools(self) -> List[Dict[str, Any]]:
        """MCP surface: the registry's tool schemas + the universal_handle meta-tool."""
        tools = list(self.registry.mcp_tools())
        tools.append(
            {
                "name": "universal_handle",
                "description": "normalize and route an input of any modality (text/audio/visual/agentic)",
                "inputSchema": {
                    "type": "object",
                    "properties": {"modality": {"type": "string", "enum": list(DEFAULT_MODALITIES)}, "content": {}},
                    "required": ["modality", "content"],
                },
            }
        )
        return tools

    def http_routes(self) -> List[Dict[str, str]]:
        """HTTP surface: a POST route per tool + the universal /handle endpoint."""
        routes = [{"method": "POST", "path": "/handle", "handler": "handle"}]
        routes += [
            {"method": "POST", "path": "/tool/%s" % name, "handler": name} for name in sorted(self.registry.actions)
        ]
        return routes

    def transports(self) -> Dict[str, Any]:
        """The multi-port manifest: the SAME registry reachable three ways."""
        return {
            "modalities": list(self.adapters),
            "api": "call(tool, args, confirm)",
            "mcp": [t["name"] for t in self.mcp_tools()],
            "http": [r["path"] for r in self.http_routes()],
            "kinds": list(KINDS),
        }


def make_fastapi_app(port: Optional[UniversalPort] = None):  # pragma: no cover - optional transport
    """Mount the port as a FastAPI app (the HTTP transport). Lazy-imports fastapi so the core stays
    dependency-free; raises only if you actually ask for the HTTP surface without fastapi installed."""
    from fastapi import FastAPI, Request  # noqa: E402

    p = port or UniversalPort()
    app = FastAPI(title="SCBE Universal Port")

    @app.post("/handle")
    async def _handle(req: Request):
        body = await req.json()
        return p.handle(Envelope(body.get("modality", TEXT), body.get("content"), body.get("meta", {})))

    @app.post("/tool/{name}")
    async def _tool(name: str, req: Request):
        body = await req.json()
        return p.call(name, body.get("args", {}), body.get("confirm"))

    return app

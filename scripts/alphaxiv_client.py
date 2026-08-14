"""alphaxiv_client.py -- minimal MCP client for alphaXiv, authenticated by API key.

alphaXiv speaks Model Context Protocol over streamable HTTP, not REST. That is why
plain GETs against /v2/papers return 403: there is no REST surface to hit. Requests
are JSON-RPC POSTs to a single endpoint, and responses come back as SSE frames
(`event: message` / `data: {...}`), so the body has to be unwrapped before it is JSON.

The key is read from ALPHAXIV_API_KEY, falling back to ARXIV_API_KEY. It is never
printed -- not in logs, not in errors. Keys carry the `axv2_` prefix, which is what
identifies the issuer; alphaXiv is a third party built on arXiv's corpus, and arXiv's
own API takes no key at all.

    python scripts/alphaxiv_client.py --tools
    python scripts/alphaxiv_client.py --discover "topological control-flow integrity"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ENDPOINT = os.environ.get("ALPHAXIV_MCP_ENDPOINT", "https://api.alphaxiv.org/mcp/v1")


def _key() -> str:
    for name in ("ALPHAXIV_API_KEY", "ARXIV_API_KEY"):
        v = os.environ.get(name)
        if v:
            return v.strip()
    try:
        from dotenv import load_dotenv

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for f in (".env.local", ".env"):
            p = os.path.join(root, f)
            if os.path.isfile(p):
                load_dotenv(p, override=False)
        for name in ("ALPHAXIV_API_KEY", "ARXIV_API_KEY"):
            v = os.environ.get(name)
            if v:
                return v.strip()
    except ImportError:
        pass
    raise SystemExit("no ALPHAXIV_API_KEY / ARXIV_API_KEY found (check .env.local)")


class AlphaXiv:
    def __init__(self):
        self._key = _key()
        self._id = 0
        self._session = None

    def _headers(self) -> dict:
        h = {
            "Authorization": "Bearer " + self._key,
            "Content-Type": "application/json",
            # the server may answer as SSE, so both are advertised
            "Accept": "application/json, text/event-stream",
            "User-Agent": "scbe-alphaxiv-client/1.0",
        }
        if self._session:
            h["Mcp-Session-Id"] = self._session
        return h

    def _rpc(self, method: str, params=None, notify=False):
        self._id += 1
        body = {"jsonrpc": "2.0", "method": method}
        if not notify:
            body["id"] = self._id
        if params is not None:
            body["params"] = params
        req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                sid = r.headers.get("Mcp-Session-Id")
                if sid:
                    self._session = sid
                raw = r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            # never echo the key, even on failure
            raise SystemExit("alphaXiv HTTP %s %s" % (e.code, e.reason))
        if notify or not raw.strip():
            return None
        for line in raw.splitlines():  # unwrap SSE framing
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return json.loads(raw)

    def connect(self) -> dict:
        res = self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "scbe-alphaxiv-client", "version": "1.0"},
            },
        )
        self._rpc("notifications/initialized", {}, notify=True)
        return (res or {}).get("result", {})

    def tools(self) -> list:
        return ((self._rpc("tools/list", {}) or {}).get("result", {}) or {}).get("tools", [])

    def call(self, name: str, args: dict):
        res = self._rpc("tools/call", {"name": name, "arguments": args}) or {}
        if "error" in res:
            raise SystemExit("tool error: %s" % json.dumps(res["error"])[:300])
        content = (res.get("result") or {}).get("content") or []
        return "\n".join(c.get("text", "") for c in content if c.get("type") == "text")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tools", action="store_true")
    ap.add_argument("--discover")
    ap.add_argument("--keywords", nargs="*", default=None)
    ap.add_argument("--difficulty", type=int, default=6)
    ap.add_argument("--save")
    a = ap.parse_args()

    ax = AlphaXiv()
    info = ax.connect()
    srv = info.get("serverInfo", {})
    print("  connected: %s v%s  (protocol %s)" % (srv.get("name"), srv.get("version"), info.get("protocolVersion")))

    if a.tools:
        for t in ax.tools():
            print("    %-34s %s" % (t["name"], (t.get("description") or "")[:64]))
        return 0

    if a.discover:
        kw = a.keywords or a.discover.split()[:4]
        print("  discover_papers  keywords=%s  difficulty=%d" % (kw, a.difficulty))
        out = ax.call("discover_papers", {"keywords": kw, "question": a.discover, "difficulty": a.difficulty})
        print()
        print(out[:6000])
        if a.save:
            with open(a.save, "w", encoding="utf-8") as fh:
                fh.write("# alphaXiv discover_papers\n\n")
                fh.write("query: %s\n\nkeywords: %s\n\n---\n\n" % (a.discover, kw))
                fh.write(out)
            print("\n  saved -> %s (%d chars)" % (a.save, len(out)))
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

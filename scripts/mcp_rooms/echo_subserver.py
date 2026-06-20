#!/usr/bin/env python3
"""A trivial MCP sub-server (one `echo` tool) used to demo + test real MCP-to-MCP forwarding.

A governed Room (scripts/mcp_rooms/server.py: build_forwarding_room) forwards a routed, gate-screened
sub-aspect to THIS server over stdio. It is intentionally minimal: its only job is to prove the forward
hop happens end-to-end and gets receipted by the room.

    python scripts/mcp_rooms/echo_subserver.py    # run as an MCP server over stdio
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("scbe-echo-subserver")


@mcp.tool()
def echo(message: str) -> str:
    """Echo the message back (proves a Room forwarded a governed sub-aspect to an external MCP server)."""
    return "echo: " + message


if __name__ == "__main__":
    mcp.run()

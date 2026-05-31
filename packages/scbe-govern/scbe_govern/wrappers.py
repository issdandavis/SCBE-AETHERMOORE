"""
Framework wrappers — thin adapters for LangChain, CrewAI, AutoGen, n8n.

All wrappers follow the same pattern:
  - wrap an existing tool/function
  - intercept the input before execution
  - call gov.check() on the command string
  - pass through if ALLOW/QUARANTINE, raise on DENY
  - attach the GovResult to the output for audit trail
"""

from __future__ import annotations

from typing import Any, Callable, Optional
from scbe_govern.client import SCBEGovern, GovResult


def govern_tool(tool: Any, gov: Optional[SCBEGovern] = None) -> Any:
    """Wrap a LangChain BaseTool with SCBE governance.

    Usage:
        from langchain.tools import ShellTool
        from scbe_govern import SCBEGovern, govern_tool

        gov = SCBEGovern()
        safe_shell = govern_tool(ShellTool(), gov)
        result = safe_shell.run("ls /tmp")   # QUARANTINE — executes + audits
        result = safe_shell.run("rm -rf /")  # DENY — raises ValueError
    """
    if gov is None:
        gov = SCBEGovern()

    # Wrap the tool's _run method
    original_run = getattr(tool, "_run", None)
    original_arun = getattr(tool, "_arun", None)

    if original_run is None:
        raise TypeError(f"govern_tool: {type(tool).__name__} has no _run method")

    def _governed_run(command: str, *args: Any, **kwargs: Any) -> Any:
        result = gov.guard(command)
        output = original_run(command, *args, **kwargs)
        # Attach governance provenance as a prefix if output is a string
        if isinstance(output, str):
            prefix = f"[SCBE:{result.tier}:{result.score:.3f}] "
            return prefix + output
        return output

    async def _governed_arun(command: str, *args: Any, **kwargs: Any) -> Any:
        result = gov.guard(command)
        if original_arun:
            output = await original_arun(command, *args, **kwargs)
        else:
            output = original_run(command, *args, **kwargs)
        if isinstance(output, str):
            prefix = f"[SCBE:{result.tier}:{result.score:.3f}] "
            return prefix + output
        return output

    tool._run = _governed_run
    tool._arun = _governed_arun
    tool.__class__.__name__ = f"SCBE({tool.__class__.__name__})"
    return tool


def govern_fn(fn: Callable, gov: Optional[SCBEGovern] = None) -> Callable:
    """Wrap any callable that takes a command string as first argument.

    Usage:
        import subprocess
        from scbe_govern import SCBEGovern
        from scbe_govern.wrappers import govern_fn

        gov = SCBEGovern()
        safe_run = govern_fn(subprocess.check_output, gov)
        safe_run(["ls", "/tmp"])       # fine
        safe_run(["rm", "-rf", "/"])   # DENY raised before subprocess fires
    """
    if gov is None:
        gov = SCBEGovern()

    def _wrapper(*args: Any, **kwargs: Any) -> Any:
        # Try to extract a command string from args[0]
        first = args[0] if args else ""
        if isinstance(first, list):
            cmd_str = " ".join(str(a) for a in first)
        else:
            cmd_str = str(first)
        gov.guard(cmd_str)
        return fn(*args, **kwargs)

    _wrapper.__name__ = f"governed_{fn.__name__}"
    return _wrapper

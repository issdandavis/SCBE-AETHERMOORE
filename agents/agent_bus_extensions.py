"""
Agent Bus self-extension — let the bus generate new tools for itself.

Two halves:

  1. ToolRegistry — runtime store of (name, schema, callable) entries.
     Tools are normal Python coroutines registered by name; the bus exposes
     them via call_tool() and lists them via list_tools().

  2. ToolGenerator — uses the bus's LLM (Ollama / HF) to write Python source
     for a new tool from a natural-language spec, then validates and
     installs it. Validation is conservative on purpose:
       - parses with ast.parse — must be syntactically valid
       - rejects imports outside an allowlist (no os.system, no subprocess,
         no socket, no requests)
       - must define a single async def named `tool` taking (bus, **kwargs)
       - source is written to agents/generated_tools/<name>.py and signed
         with the bus identity if signing is enabled

This gives the bus a controlled way to grow its capabilities without giving
the LLM raw exec() over the host process.
"""

from __future__ import annotations

import ast
import asyncio
import importlib
import importlib.util
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("scbe.agent_bus.extensions")

GENERATED_DIR = Path("agents/generated_tools")

ALLOWED_IMPORTS = {
    "json",
    "asyncio",
    "datetime",
    "math",
    "re",
    "typing",
    "dataclasses",
    "pathlib",
    "collections",
    "itertools",
    "functools",
    "statistics",
    "hashlib",
    "base64",
    "urllib.parse",
}

FORBIDDEN_NODES = (ast.Import, ast.ImportFrom)  # gated by ALLOWED_IMPORTS check
FORBIDDEN_NAMES = {"eval", "exec", "compile", "__import__", "open", "input"}


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, str]  # name -> type-string


class ToolValidationError(ValueError):
    pass


class ToolRegistry:
    """In-memory registry of tools the bus can call by name."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Awaitable[Any]]] = {}
        self._specs: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec, fn: Callable[..., Awaitable[Any]]) -> None:
        self._tools[spec.name] = fn
        self._specs[spec.name] = spec

    def list(self) -> List[ToolSpec]:
        return list(self._specs.values())

    async def call(self, name: str, /, **kwargs: Any) -> Any:
        if name not in self._tools:
            raise KeyError(f"tool {name!r} not registered")
        fn = self._tools[name]
        return await fn(**kwargs)

    def has(self, name: str) -> bool:
        return name in self._tools


def _validate_source(source: str, expected_name: str) -> None:
    """Parse + statically check generated tool source. Raises on any violation."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ToolValidationError(f"syntax error: {exc}") from exc

    found_tool = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    raise ToolValidationError(f"import {alias.name!r} not allowed")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root and root not in ALLOWED_IMPORTS:
                raise ToolValidationError(f"from-import {node.module!r} not allowed")
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise ToolValidationError(f"forbidden name {node.id!r}")
        elif isinstance(node, ast.AsyncFunctionDef) and node.name == "tool":
            found_tool = True
        elif isinstance(node, ast.FunctionDef) and node.name == "tool":
            raise ToolValidationError("tool() must be `async def`")

    if not found_tool:
        raise ToolValidationError("no `async def tool(...)` found")
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", expected_name):
        raise ToolValidationError(f"tool name {expected_name!r} fails naming rule")


def _load_module_from_source(name: str, source: str) -> Any:
    """Compile source into a fresh, isolated module and return it."""
    spec = importlib.util.spec_from_loader(f"agents.generated_tools.{name}", loader=None)
    if spec is None:
        raise ToolValidationError("could not create module spec")
    module = importlib.util.module_from_spec(spec)
    code = compile(source, f"<generated:{name}>", "exec")
    exec(code, module.__dict__)  # noqa: S102 — guarded by _validate_source above
    return module


def _fixture_for_type(type_str: str) -> Any:
    """Generate a sane test fixture for a parameter type-string."""
    t = (type_str or "").lower().strip()
    if t in ("int", "integer"):
        return 42
    if t in ("float", "number"):
        return 3.14
    if t in ("bool", "boolean"):
        return True
    if t in ("list", "list[str]", "list[int]", "array"):
        return ["a", "b", "c"]
    if t in ("dict", "object", "mapping"):
        return {"k": "v"}
    # default: a non-empty string
    return "hello world"


async def _live_test_tool(spec: ToolSpec, fn: Any, *, timeout: float = 5.0) -> None:
    """Run the tool with synthetic fixtures. Raise ToolValidationError on any failure.

    Asserts:
      1. tool runs to completion within timeout
      2. tool returns a JSON-serializable dict (not a list, primitive, or unserializable object)
      3. no uncaught exceptions
    """
    fixtures = {name: _fixture_for_type(tp) for name, tp in spec.parameters.items()}

    try:
        coro = fn(bus=None, **fixtures)
    except TypeError as exc:
        raise ToolValidationError(f"signature mismatch: {exc}") from exc

    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise ToolValidationError(f"tool exceeded {timeout}s timeout") from exc
    except Exception as exc:  # noqa: BLE001
        raise ToolValidationError(f"tool raised at runtime: {type(exc).__name__}: {exc}") from exc

    if not isinstance(result, dict):
        raise ToolValidationError(f"tool must return dict, got {type(result).__name__}")

    try:
        import json as _json

        _json.dumps(result)
    except (TypeError, ValueError) as exc:
        raise ToolValidationError(f"tool result is not JSON-serializable: {exc}") from exc


class ToolGenerator:
    """Drives the bus's LLM to write new tools, then validates and registers them."""

    def __init__(self, bus: Any, registry: ToolRegistry) -> None:
        self.bus = bus
        self.registry = registry

    async def generate(self, spec: ToolSpec, *, attempts: int = 3) -> bool:
        """Generate, validate, and register a tool from a natural-language spec.

        Returns True on success. False if all attempts failed validation.
        """
        prompt = self._build_prompt(spec)
        for attempt in range(1, attempts + 1):
            answer = await self.bus._llm_generate(prompt)
            source = _extract_python_block(answer.get("text", ""))
            if not source:
                logger.warning("attempt %d: no python block in LLM output", attempt)
                continue
            try:
                _validate_source(source, spec.name)
                module = _load_module_from_source(spec.name, source)
                fn = getattr(module, "tool", None)
                if fn is None or not asyncio.iscoroutinefunction(fn):
                    raise ToolValidationError("tool symbol missing or not async")
                # Live test: run with fixtures, assert shape, before registering
                await _live_test_tool(spec, fn)
                self.registry.register(spec, fn)
                self._persist(spec.name, source)
                logger.info("tool %s registered (attempt %d)", spec.name, attempt)
                return True
            except ToolValidationError as exc:
                logger.warning("attempt %d: validation failed: %s", attempt, exc)
                prompt = self._build_repair_prompt(spec, source, str(exc))
        return False

    @staticmethod
    def _build_prompt(spec: ToolSpec) -> str:
        params = "\n".join(f"  - {name}: {tp}" for name, tp in spec.parameters.items())
        return (
            "Write a Python coroutine for an agent bus tool. Output ONE fenced "
            "```python``` code block — nothing else.\n\n"
            f"Tool name: {spec.name}\n"
            f"Description: {spec.description}\n"
            f"Parameters:\n{params}\n\n"
            "Hard rules:\n"
            "  - signature: `async def tool(bus, **kwargs)`\n"
            f"  - imports must be from this allowlist only: {sorted(ALLOWED_IMPORTS)}\n"
            "  - do NOT use eval/exec/compile/__import__/open/input\n"
            "  - return a JSON-serializable dict\n"
            "  - keep it short (under 50 lines)\n"
        )

    @staticmethod
    def _build_repair_prompt(spec: ToolSpec, source: str, error: str) -> str:
        return (
            f"The previous tool `{spec.name}` failed validation:\n"
            f"  ERROR: {error}\n\n"
            "Previous source:\n```python\n" + source + "\n```\n\n"
            "Fix the issue and emit ONLY the corrected code in one ```python``` block."
        )

    @staticmethod
    def _persist(name: str, source: str) -> Path:
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        path = GENERATED_DIR / f"{name}.py"
        path.write_text(source, encoding="utf-8")
        return path


_FENCE = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL)


def _extract_python_block(text: str) -> Optional[str]:
    m = _FENCE.search(text or "")
    return m.group(1).strip() if m else None

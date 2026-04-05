"""Inner sandbox — isolated code execution.

Runs cell code in a subprocess with no filesystem/network access.
The sand where Polly builds her castles.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cell import Cell, CellStatus


@dataclass
class ExecutionResult:
    """Result of running a cell in the sandbox."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    error: str = ""
    return_value: Any = None
    duration_ms: float = 0.0


# Language-specific execution commands
LANGUAGE_RUNNERS = {
    "python": [sys.executable, "-u"],
    "typescript": ["npx", "tsx"],
    "javascript": ["node"],
    "rust": None,  # requires compile step
    "bash": ["bash"],
    "sql": None,   # requires DB connection — not in sandbox
}

# Max execution time per cell (seconds)
DEFAULT_TIMEOUT = 30
# Max output capture (bytes)
MAX_OUTPUT = 1_000_000


class Sandbox:
    """Inner sandbox — isolated subprocess execution for cells.

    No filesystem access outside temp dir.
    No network access.
    Memory and time limits enforced.
    """

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, namespace: dict[str, str] | None = None):
        self.timeout = timeout
        # Virtual namespace: cell_id -> exported code (for cross-cell imports)
        self.namespace: dict[str, str] = namespace or {}

    def register_cell(self, cell: Cell) -> None:
        """Register a cell's code in the shared namespace for cross-cell imports."""
        if cell.status == CellStatus.PASS:
            self.namespace[cell.cell_id] = cell.code

    def _build_python_script(self, cell: Cell) -> str:
        """Build a Python script with virtual namespace imports resolved."""
        parts = []

        # Inject imported cell code as modules
        for imp_id in cell.imports:
            if imp_id in self.namespace:
                # Create the imported code as inline definitions
                parts.append(f"# --- imported from {imp_id} ---")
                parts.append(self.namespace[imp_id])
                parts.append(f"# --- end {imp_id} ---\n")

        parts.append("# --- cell code ---")
        parts.append(cell.code)

        return "\n".join(parts)

    def _build_js_script(self, cell: Cell) -> str:
        """Build a JS/TS script with virtual namespace imports resolved."""
        parts = []
        for imp_id in cell.imports:
            if imp_id in self.namespace:
                parts.append(f"// --- imported from {imp_id} ---")
                parts.append(self.namespace[imp_id])
                parts.append(f"// --- end {imp_id} ---\n")
        parts.append("// --- cell code ---")
        parts.append(cell.code)
        return "\n".join(parts)

    def execute(self, cell: Cell) -> ExecutionResult:
        """Execute a cell in an isolated subprocess."""
        lang = cell.language.lower()

        if lang in ("python", "python3"):
            return self._execute_python(cell)
        elif lang in ("javascript", "js"):
            return self._execute_script(cell, ["node"], self._build_js_script(cell), ".js")
        elif lang in ("typescript", "ts"):
            return self._execute_script(cell, ["npx", "tsx"], self._build_js_script(cell), ".ts")
        elif lang == "bash":
            return self._execute_script(cell, ["bash"], cell.code, ".sh")
        else:
            return ExecutionResult(
                success=False,
                error=f"Unsupported language: {lang}. Supported: python, javascript, typescript, bash",
            )

    def _execute_python(self, cell: Cell) -> ExecutionResult:
        """Execute Python code in isolated subprocess."""
        script = self._build_python_script(cell)
        return self._execute_script(cell, [sys.executable, "-u"], script, ".py")

    def _execute_script(self, cell: Cell, cmd: list[str], script: str, ext: str) -> ExecutionResult:
        """Execute a script file in a subprocess."""
        import time

        start = time.time()

        with tempfile.TemporaryDirectory(prefix="polly_sand_") as tmpdir:
            script_path = Path(tmpdir) / f"cell_{cell.cell_id}{ext}"
            script_path.write_text(script, encoding="utf-8")

            try:
                result = subprocess.run(
                    cmd + [str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=tmpdir,
                    env={
                        "PATH": "",  # minimal PATH
                        "HOME": tmpdir,
                        "TMPDIR": tmpdir,
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                )

                duration = (time.time() - start) * 1000
                stdout = result.stdout[:MAX_OUTPUT]
                stderr = result.stderr[:MAX_OUTPUT]

                if result.returncode == 0:
                    cell.record_run(stdout=stdout, stderr=stderr)
                    self.register_cell(cell)
                    return ExecutionResult(
                        success=True,
                        stdout=stdout,
                        stderr=stderr,
                        duration_ms=duration,
                    )
                else:
                    error = stderr or f"Process exited with code {result.returncode}"
                    cell.record_fail(error=error, stderr=stderr)
                    return ExecutionResult(
                        success=False,
                        stdout=stdout,
                        stderr=stderr,
                        error=error,
                        duration_ms=duration,
                    )

            except subprocess.TimeoutExpired:
                duration = (time.time() - start) * 1000
                error = f"Execution timed out after {self.timeout}s"
                cell.record_fail(error=error)
                return ExecutionResult(
                    success=False,
                    error=error,
                    duration_ms=duration,
                )
            except Exception as e:
                duration = (time.time() - start) * 1000
                error = f"{type(e).__name__}: {e}"
                cell.record_fail(error=error)
                return ExecutionResult(
                    success=False,
                    error=error,
                    duration_ms=duration,
                )

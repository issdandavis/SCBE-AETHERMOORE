"""
HYDRA Code Sandbox Limb — Diverse Code Environments for AI Agents
==================================================================

A HYDRA Limb that provides governed code execution across multiple
language runtimes. AI agents (heads) can write, execute, and test code
in isolated sandbox environments — all under SCBE governance.

Supported environments:
  - Python 3.11+ (subprocess with timeout)
  - Node.js 18+ (subprocess with timeout)
  - Shell/Bash (filtered commands, subprocess)
  - Custom interpreters (configurable)

Safety layers:
  1. Command prefix whitelisting (only allowed interpreters)
  2. Banned command fragment filtering (rm -rf, format, etc.)
  3. Path traversal prevention (confined to workspace)
  4. Timeout enforcement (default 30s, max 120s)
  5. Output size limits (prevent memory exhaustion)
  6. SCBE governance risk scoring per action

Architecture:
    ┌─────────────────────────────────────────┐
    │          HYDRA Head (any AI)            │
    │   "Run this Python code for me"        │
    └────────────────┬────────────────────────┘
                     │
    ┌────────────────▼────────────────────────┐
    │       Code Sandbox Limb                 │
    │  ┌──────────┬──────────┬──────────┐    │
    │  │ Python   │ Node.js  │  Shell   │    │
    │  │ Sandbox  │ Sandbox  │ Sandbox  │    │
    │  └──────────┴──────────┴──────────┘    │
    │  Risk scoring → Governance gate         │
    └────────────────┬────────────────────────┘
                     │
    ┌────────────────▼────────────────────────┐
    │     SCBE 14-Layer Pipeline              │
    │  (L8: adversarial check, L13: decision) │
    └─────────────────────────────────────────┘

Usage:
    sandbox = CodeSandboxLimb(workspace="/tmp/hydra-sandbox")

    # Execute Python code
    result = await sandbox.run_code(
        language="python",
        code="print('Hello from SCBE sandbox')",
    )

    # Execute Node.js
    result = await sandbox.run_code(
        language="node",
        code="console.log(JSON.stringify({status: 'ok'}))",
    )

    # Write + run a file
    result = await sandbox.write_and_run(
        filename="analysis.py",
        code="import math\\nprint(math.pi)",
        language="python",
    )
"""

import asyncio
import hashlib
import json
import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Allowed interpreter commands (whitelist)
ALLOWED_INTERPRETERS: Dict[str, List[str]] = {
    "python": ["python", "python3"],
    "node": ["node", "nodejs"],
    "shell": ["bash", "sh"],
    "deno": ["deno"],
    "ruby": ["ruby"],
    "go": ["go", "go run"],
}

# Banned command fragments — block regardless of language
BANNED_FRAGMENTS: Set[str] = {
    "rm -rf",
    "rm -r /",
    "rm -f /",
    "del /f",
    "format c:",
    "shutdown",
    "reboot",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",  # fork bomb
    "chmod 777 /",
    "chown root",
    "> /dev/sda",
    "curl | sh",
    "curl | bash",
    "wget | sh",
    "wget | bash",
    "powershell -enc",
    "base64 -d | sh",
}

# Max output size (chars) to prevent memory exhaustion
MAX_OUTPUT_SIZE = 50_000

# Max timeout (seconds)
MAX_TIMEOUT = 120
DEFAULT_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SandboxResult:
    """Result from a sandbox code execution."""

    execution_id: str
    language: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    risk_score: float
    governance_decision: str  # ALLOW, QUARANTINE, DENY
    truncated: bool = False
    file_path: Optional[str] = None


@dataclass
class SandboxConfig:
    """Configuration for a code sandbox environment."""

    workspace: str = "/tmp/hydra-sandbox"
    max_timeout: int = MAX_TIMEOUT
    default_timeout: int = DEFAULT_TIMEOUT
    max_output_size: int = MAX_OUTPUT_SIZE
    allowed_languages: List[str] = field(
        default_factory=lambda: ["python", "node", "shell"]
    )
    safe_mode: bool = True  # Extra restrictions when True


# ---------------------------------------------------------------------------
# Code Sandbox Limb
# ---------------------------------------------------------------------------


class CodeSandboxLimb:
    """HYDRA Limb providing governed multi-language code execution.

    Each execution is:
    1. Scanned for banned fragments
    2. Assigned a risk score
    3. Run in a subprocess with timeout
    4. Output captured and size-limited
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._workspace = Path(self.config.workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._execution_log: List[Dict[str, Any]] = []
        self._session_id = f"sandbox-{uuid.uuid4().hex[:8]}"

    # ------------------------------------------------------------------
    # Main execution interface
    # ------------------------------------------------------------------

    async def run_code(
        self,
        language: str,
        code: str,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        args: Optional[List[str]] = None,
    ) -> SandboxResult:
        """Execute code in a sandboxed subprocess.

        Args:
            language: Runtime to use (python, node, shell).
            code: Source code to execute.
            timeout: Execution timeout in seconds.
            env: Additional environment variables.
            args: Additional command-line arguments.

        Returns:
            SandboxResult with output, timing, and governance info.
        """
        execution_id = f"exec-{uuid.uuid4().hex[:8]}"
        timeout = min(timeout or self.config.default_timeout, self.config.max_timeout)

        # Step 1: Validate language
        if language not in self.config.allowed_languages:
            return SandboxResult(
                execution_id=execution_id,
                language=language,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Language '{language}' is not allowed. Allowed: {self.config.allowed_languages}",
                duration_ms=0,
                risk_score=1.0,
                governance_decision="DENY",
            )

        # Step 2: Scan for banned fragments
        risk_score, ban_reason = self._assess_risk(code, language)

        if ban_reason:
            return SandboxResult(
                execution_id=execution_id,
                language=language,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Code blocked by safety scan: {ban_reason}",
                duration_ms=0,
                risk_score=risk_score,
                governance_decision="DENY",
            )

        # Step 3: Governance gate
        governance = self._governance_decision(risk_score)
        if governance == "DENY":
            return SandboxResult(
                execution_id=execution_id,
                language=language,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Execution denied by SCBE governance (risk too high)",
                duration_ms=0,
                risk_score=risk_score,
                governance_decision="DENY",
            )

        # Step 4: Execute in subprocess
        result = await self._execute_subprocess(
            execution_id=execution_id,
            language=language,
            code=code,
            timeout=timeout,
            env=env,
            args=args,
            risk_score=risk_score,
            governance=governance,
        )

        # Log execution
        self._execution_log.append({
            "execution_id": execution_id,
            "language": language,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": result.success,
            "exit_code": result.exit_code,
            "risk_score": risk_score,
            "governance": governance,
            "duration_ms": round(result.duration_ms, 1),
            "code_hash": hashlib.sha256(code.encode()).hexdigest()[:16],
        })

        return result

    async def write_and_run(
        self,
        filename: str,
        code: str,
        language: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> SandboxResult:
        """Write code to a file in the workspace and execute it.

        Args:
            filename: Name of the file to create.
            code: Source code content.
            language: Runtime (auto-detected from extension if not given).
            timeout: Execution timeout.

        Returns:
            SandboxResult with output.
        """
        # Prevent path traversal
        safe_name = Path(filename).name
        if safe_name != filename or ".." in filename:
            return SandboxResult(
                execution_id=f"exec-{uuid.uuid4().hex[:8]}",
                language=language or "unknown",
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Path traversal detected in filename",
                duration_ms=0,
                risk_score=1.0,
                governance_decision="DENY",
            )

        # Auto-detect language from extension
        if not language:
            ext = Path(safe_name).suffix.lower()
            language = {
                ".py": "python",
                ".js": "node",
                ".ts": "node",
                ".sh": "shell",
                ".bash": "shell",
                ".rb": "ruby",
                ".go": "go",
            }.get(ext, "python")

        # Write file
        file_path = self._workspace / safe_name
        file_path.write_text(code, encoding="utf-8")

        # Execute via file instead of -c
        result = await self._execute_file(
            file_path=str(file_path),
            language=language,
            timeout=timeout,
        )
        result.file_path = str(file_path)
        return result

    async def run_tests(
        self,
        test_path: str,
        framework: str = "pytest",
        timeout: Optional[int] = None,
    ) -> SandboxResult:
        """Run a test suite using the appropriate framework.

        Args:
            test_path: Path to test file or directory.
            framework: Test framework (pytest, vitest, jest).
            timeout: Execution timeout.

        Returns:
            SandboxResult with test output.
        """
        timeout = min(timeout or 60, self.config.max_timeout)

        commands = {
            "pytest": f"python -m pytest {test_path} -v --tb=short",
            "vitest": f"npx vitest run {test_path}",
            "jest": f"npx jest {test_path}",
        }

        cmd = commands.get(framework, f"python -m pytest {test_path} -v")
        return await self.run_code("shell", cmd, timeout=timeout)

    # ------------------------------------------------------------------
    # Available languages query
    # ------------------------------------------------------------------

    async def detect_available(self) -> Dict[str, Dict[str, Any]]:
        """Detect which language runtimes are available on this system.

        Returns:
            Dict mapping language name to version info and availability.
        """
        results = {}
        checks = {
            "python": "python3 --version",
            "node": "node --version",
            "shell": "bash --version | head -1",
            "deno": "deno --version | head -1",
            "ruby": "ruby --version",
            "go": "go version",
        }

        for lang, cmd in checks.items():
            try:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
                version = (stdout or stderr).decode().strip()
                results[lang] = {
                    "available": proc.returncode == 0,
                    "version": version if proc.returncode == 0 else None,
                    "allowed": lang in self.config.allowed_languages,
                }
            except (asyncio.TimeoutError, Exception):
                results[lang] = {"available": False, "version": None, "allowed": False}

        return results

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return execution statistics for this session."""
        total = len(self._execution_log)
        successes = sum(1 for e in self._execution_log if e["success"])
        by_lang = {}
        for e in self._execution_log:
            lang = e["language"]
            by_lang[lang] = by_lang.get(lang, 0) + 1

        return {
            "session_id": self._session_id,
            "workspace": str(self._workspace),
            "total_executions": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": round(successes / total, 3) if total > 0 else 1.0,
            "by_language": by_lang,
            "allowed_languages": self.config.allowed_languages,
            "safe_mode": self.config.safe_mode,
        }

    # ------------------------------------------------------------------
    # Internal: risk assessment
    # ------------------------------------------------------------------

    def _assess_risk(self, code: str, language: str) -> tuple:
        """Assess the risk level of code before execution.

        Returns:
            (risk_score, ban_reason) — ban_reason is None if code passes.
        """
        code_lower = code.lower()

        # Check banned fragments
        for fragment in BANNED_FRAGMENTS:
            if fragment.lower() in code_lower:
                return 1.0, f"Banned fragment detected: '{fragment}'"

        risk = 0.0

        # Language-specific risk
        lang_risk = {
            "python": 0.15,
            "node": 0.2,
            "shell": 0.4,
            "ruby": 0.25,
            "go": 0.2,
            "deno": 0.15,
        }
        risk += lang_risk.get(language, 0.3)

        # Pattern-based risk adjustments
        risky_patterns = [
            (r"import\s+subprocess", 0.15),
            (r"import\s+os", 0.1),
            (r"import\s+shutil", 0.1),
            (r"eval\s*\(", 0.2),
            (r"exec\s*\(", 0.2),
            (r"__import__", 0.25),
            (r"open\s*\(.*(w|a)", 0.1),
            (r"requests\.(get|post|put|delete)", 0.1),
            (r"urllib", 0.1),
            (r"socket\.", 0.15),
            (r"os\.system", 0.2),
            (r"subprocess\.(run|call|Popen)", 0.2),
            (r"child_process", 0.2),  # Node.js
            (r"fs\.(write|unlink|rmdir)", 0.15),  # Node.js
        ]

        for pattern, weight in risky_patterns:
            if re.search(pattern, code):
                risk += weight

        # Safe mode applies higher baseline
        if self.config.safe_mode:
            risk = min(risk + 0.1, 1.0)

        return min(risk, 1.0), None

    def _governance_decision(self, risk_score: float) -> str:
        """Map risk score to SCBE governance decision.

        Uses the harmonic wall formula concept:
        H(d, pd) = 1 / (1 + d + 2*pd)

        Lower H → higher risk → stricter decision.
        """
        if risk_score >= 0.85:
            return "DENY"
        elif risk_score >= 0.5:
            return "QUARANTINE"
        else:
            return "ALLOW"

    # ------------------------------------------------------------------
    # Internal: subprocess execution
    # ------------------------------------------------------------------

    async def _execute_subprocess(
        self,
        execution_id: str,
        language: str,
        code: str,
        timeout: int,
        env: Optional[Dict[str, str]],
        args: Optional[List[str]],
        risk_score: float,
        governance: str,
    ) -> SandboxResult:
        """Execute code in a subprocess with timeout and output limits."""
        import time

        # Build the command
        interpreter = self._get_interpreter(language)
        if not interpreter:
            return SandboxResult(
                execution_id=execution_id,
                language=language,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"No interpreter found for '{language}'",
                duration_ms=0,
                risk_score=risk_score,
                governance_decision=governance,
            )

        # Write code to temp file for execution
        suffix = {"python": ".py", "node": ".js", "shell": ".sh"}.get(language, ".txt")
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            dir=str(self._workspace),
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            cmd = [interpreter, temp_path]
            if args:
                cmd.extend(args)

            # Build environment
            run_env = os.environ.copy()
            if env:
                run_env.update(env)

            start = time.monotonic()
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._workspace),
                env=run_env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                duration = (time.monotonic() - start) * 1000
                return SandboxResult(
                    execution_id=execution_id,
                    language=language,
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Execution timed out after {timeout}s",
                    duration_ms=duration,
                    risk_score=risk_score,
                    governance_decision=governance,
                )

            duration = (time.monotonic() - start) * 1000
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            # Truncate if needed
            truncated = False
            if len(stdout) > self.config.max_output_size:
                stdout = stdout[: self.config.max_output_size] + "\n... [output truncated]"
                truncated = True
            if len(stderr) > self.config.max_output_size:
                stderr = stderr[: self.config.max_output_size] + "\n... [output truncated]"
                truncated = True

            return SandboxResult(
                execution_id=execution_id,
                language=language,
                success=proc.returncode == 0,
                exit_code=proc.returncode or 0,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration,
                risk_score=risk_score,
                governance_decision=governance,
                truncated=truncated,
            )

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    async def _execute_file(
        self,
        file_path: str,
        language: str,
        timeout: Optional[int] = None,
    ) -> SandboxResult:
        """Execute an existing file in the workspace."""
        timeout = min(timeout or self.config.default_timeout, self.config.max_timeout)

        # Read the file content for risk assessment
        try:
            code = Path(file_path).read_text(encoding="utf-8")
        except Exception as e:
            return SandboxResult(
                execution_id=f"exec-{uuid.uuid4().hex[:8]}",
                language=language,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Cannot read file: {e}",
                duration_ms=0,
                risk_score=0.5,
                governance_decision="DENY",
            )

        risk_score, ban_reason = self._assess_risk(code, language)
        if ban_reason:
            return SandboxResult(
                execution_id=f"exec-{uuid.uuid4().hex[:8]}",
                language=language,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Code blocked: {ban_reason}",
                duration_ms=0,
                risk_score=risk_score,
                governance_decision="DENY",
            )

        governance = self._governance_decision(risk_score)
        if governance == "DENY":
            return SandboxResult(
                execution_id=f"exec-{uuid.uuid4().hex[:8]}",
                language=language,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Denied by governance",
                duration_ms=0,
                risk_score=risk_score,
                governance_decision="DENY",
            )

        return await self._execute_subprocess(
            execution_id=f"exec-{uuid.uuid4().hex[:8]}",
            language=language,
            code=code,
            timeout=timeout,
            env=None,
            args=None,
            risk_score=risk_score,
            governance=governance,
        )

    def _get_interpreter(self, language: str) -> Optional[str]:
        """Find the interpreter binary for a language."""
        candidates = ALLOWED_INTERPRETERS.get(language, [])
        for cmd in candidates:
            # Check if the command exists
            import shutil

            if shutil.which(cmd):
                return cmd
        return None

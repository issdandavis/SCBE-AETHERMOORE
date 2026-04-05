"""Life Guard — middle sandbox observer.

Watches cell execution, provides structured feedback.
Doesn't block — teaches. Like a life guard at the beach
who lets kids take risks but intervenes before anyone drowns.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .cell import Cell


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LifeGuardNote:
    """A single observation from the life guard."""

    category: str          # lint, security, test, performance, style
    severity: Severity
    message: str
    line: int | None = None
    suggestion: str = ""   # what to do about it — teaching, not blocking
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


# ---------------------------------------------------------------------------
# Security patterns (from antivirus_membrane.py lineage)
# ---------------------------------------------------------------------------

SECURITY_PATTERNS = [
    # Injection risks
    (r"eval\s*\(", "eval() is a code injection risk — use ast.literal_eval() or a parser", "security"),
    (r"exec\s*\(", "exec() executes arbitrary code — validate inputs or use a sandbox", "security"),
    (r"subprocess\.call\s*\(.+shell\s*=\s*True", "shell=True enables command injection — use a list of args instead", "security"),
    (r"os\.system\s*\(", "os.system() is vulnerable to command injection — use subprocess with shell=False", "security"),
    (r"__import__\s*\(", "Dynamic imports can be exploited — use explicit imports", "security"),

    # SQL injection
    (r"f['\"].*SELECT.*\{", "f-string in SQL query is injection-prone — use parameterized queries", "security"),
    (r"\.format\(.*SELECT", ".format() in SQL query is injection-prone — use parameterized queries", "security"),
    (r"\%s.*SELECT|SELECT.*\%s", "String interpolation in SQL — use parameterized queries with placeholders", "security"),

    # Hardcoded secrets
    (r"(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}", "Possible hardcoded secret — use environment variables", "security"),

    # Dangerous file operations
    (r"open\(.+['\"]w['\"].*\).*\n.*write\(.*input", "Writing user input to file without validation", "security"),
    (r"pickle\.loads?\(", "pickle.load() can execute arbitrary code — use json or safe alternatives", "security"),
    (r"yaml\.load\([^)]*\)(?!.*Loader)", "yaml.load() without SafeLoader can execute arbitrary code", "security"),
]

# ---------------------------------------------------------------------------
# Code quality patterns
# ---------------------------------------------------------------------------

QUALITY_PATTERNS = [
    # Python-specific
    (r"except\s*:", "Bare except catches everything including SystemExit/KeyboardInterrupt — catch specific exceptions", "lint"),
    (r"except Exception:", "Catching broad Exception — consider catching specific exception types", "lint"),
    (r"import \*", "Wildcard import pollutes namespace — import specific names", "lint"),
    (r"global\s+\w+", "Global variables make code hard to reason about — consider passing as parameters", "style"),
    (r"type\(.*\)\s*==", "Use isinstance() instead of type() == for type checking", "lint"),

    # General
    (r"TODO|FIXME|HACK|XXX", "Unresolved TODO/FIXME marker", "lint"),
    (r"print\(.*password|print\(.*secret|print\(.*token", "Printing sensitive data — remove before production", "security"),
]

# ---------------------------------------------------------------------------
# Performance patterns
# ---------------------------------------------------------------------------

PERF_PATTERNS = [
    (r"for\s+\w+\s+in\s+range\(len\(", "Use enumerate() instead of range(len()) for cleaner iteration", "performance"),
    (r"\+\s*=\s*['\"]", "String concatenation in loop — use join() or list append for better performance", "performance"),
    (r"time\.sleep\(", "Blocking sleep — consider async alternatives for I/O-bound code", "performance"),
]


class LifeGuard:
    """Middle sandbox — observes and teaches.

    Scans code for security issues, quality problems, and performance concerns.
    Returns structured feedback that Polly can learn from.
    """

    def __init__(self, extra_patterns: list[tuple[str, str, str]] | None = None):
        self.patterns = SECURITY_PATTERNS + QUALITY_PATTERNS + PERF_PATTERNS
        if extra_patterns:
            self.patterns.extend(extra_patterns)

    def observe(self, cell: Cell) -> list[LifeGuardNote]:
        """Observe a cell and return feedback notes."""
        notes: list[LifeGuardNote] = []

        if not cell.code.strip():
            return notes

        # Pattern-based scanning
        notes.extend(self._scan_patterns(cell))

        # Structure checks
        notes.extend(self._check_structure(cell))

        # Record feedback on the cell
        if notes:
            cell.record_feedback([n.to_dict() for n in notes])

        return notes

    def _scan_patterns(self, cell: Cell) -> list[LifeGuardNote]:
        """Scan code against known patterns."""
        notes = []
        lines = cell.code.split("\n")

        for pattern, message, category in self.patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    severity = Severity.CRITICAL if category == "security" else Severity.WARN
                    notes.append(LifeGuardNote(
                        category=category,
                        severity=severity,
                        message=message,
                        line=i,
                        suggestion=message.split(" — ")[-1] if " — " in message else "",
                    ))

        return notes

    def _check_structure(self, cell: Cell) -> list[LifeGuardNote]:
        """Check code structure and organization."""
        notes = []
        lines = cell.code.strip().split("\n")

        # Too long
        if len(lines) > 200:
            notes.append(LifeGuardNote(
                category="style",
                severity=Severity.WARN,
                message=f"Cell has {len(lines)} lines — consider splitting into multiple cells",
                suggestion="Break into smaller focused cells that import from each other",
            ))

        # No docstring on functions/classes (Python)
        if cell.language in ("python", "python3"):
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith(("def ", "class ")) and not stripped.startswith("def _"):
                    # Check if next non-empty line is a docstring
                    for j in range(i, min(i + 3, len(lines))):
                        next_line = lines[j].strip()
                        if next_line and not next_line.startswith(('"""', "'''")):
                            notes.append(LifeGuardNote(
                                category="style",
                                severity=Severity.INFO,
                                message=f"Function/class at line {i} has no docstring",
                                line=i,
                                suggestion="Add a brief docstring explaining what it does",
                            ))
                            break
                        elif next_line:
                            break

        return notes

    def review_execution(self, cell: Cell, stdout: str, stderr: str, success: bool) -> list[LifeGuardNote]:
        """Review execution results and provide feedback."""
        notes = []

        if not success and stderr:
            # Parse common error types and give actionable feedback
            if "ModuleNotFoundError" in stderr:
                module = re.search(r"No module named '(\w+)'", stderr)
                mod_name = module.group(1) if module else "unknown"
                notes.append(LifeGuardNote(
                    category="lint",
                    severity=Severity.ERROR,
                    message=f"Missing module: {mod_name}",
                    suggestion=f"Add 'import {mod_name}' or install it, or import from another cell",
                ))
            elif "SyntaxError" in stderr:
                notes.append(LifeGuardNote(
                    category="lint",
                    severity=Severity.ERROR,
                    message="Syntax error in code",
                    suggestion="Check for missing colons, brackets, or indentation",
                ))
            elif "TypeError" in stderr:
                notes.append(LifeGuardNote(
                    category="lint",
                    severity=Severity.ERROR,
                    message="Type error during execution",
                    suggestion="Check argument types and function signatures",
                ))
            elif "NameError" in stderr:
                name = re.search(r"name '(\w+)' is not defined", stderr)
                var_name = name.group(1) if name else "unknown"
                notes.append(LifeGuardNote(
                    category="lint",
                    severity=Severity.ERROR,
                    message=f"Undefined name: {var_name}",
                    suggestion=f"Define '{var_name}' or import it from another cell",
                ))

        if success and stdout:
            # Check for suspicious output
            if len(stdout) > 100_000:
                notes.append(LifeGuardNote(
                    category="performance",
                    severity=Severity.WARN,
                    message=f"Very large output ({len(stdout)} bytes)",
                    suggestion="Consider limiting output or writing to a file",
                ))

        if notes:
            cell.record_feedback([n.to_dict() for n in notes])

        return notes

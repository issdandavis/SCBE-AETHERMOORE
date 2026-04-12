"""Static review helper for training pad cells."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

import re

from training_pad.cell import Cell


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LifeGuardNote:
    category: str
    severity: Severity
    message: str
    line: int = 0
    suggestion: str = ""
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "category": self.category,
            "severity": self.severity.value,
            "message": self.message,
            "line": self.line,
            "suggestion": self.suggestion,
            "metadata": dict(self.metadata),
        }


SECURITY_PATTERNS: List[Tuple[str, str, str]] = [
    (r"\beval\s*\(", "Dangerous call: eval()", "security"),
    (r"\bexec\s*\(", "Dangerous call: exec()", "security"),
    (r"\bos\.system\s*\(", "Shell execution via os.system()", "security"),
    (r"sk-[A-Za-z0-9]{10,}", "Hardcoded secret-like token detected", "security"),
    (r"\bpickle\.load\s*\(", "pickle.load() can execute arbitrary code", "security"),
    (r"SELECT\s+\*\s+FROM\s+\w+.*\{.*\}", "Possible SQL injection pattern (f-string)", "security"),
]

QUALITY_PATTERNS: List[Tuple[str, str, str]] = [
    (r"except\s*:\s*$", "Bare except detected; catch specific exceptions", "lint"),
    (r"from\s+\w+\s+import\s+\*", "Wildcard import detected", "lint"),
    (r"\bTODO\b", "TODO comment detected", "lint"),
    (r"\btype\(\w+\)\s*==", "Prefer isinstance(x, T) over type(x) == T", "lint"),
]

PERF_PATTERNS: List[Tuple[str, str, str]] = [
    (r"range\s*\(\s*len\(", "Consider iterating directly instead of range(len(...))", "performance"),
    (r"\btime\.sleep\s*\(", "time.sleep() in training loop can stall execution", "performance"),
]


def _iter_matches(patterns: Sequence[Tuple[str, str, str]], code: str) -> List[Tuple[re.Match, str, str]]:
    out: List[Tuple[re.Match, str, str]] = []
    for pat, msg, cat in patterns:
        rx = re.compile(pat, flags=re.IGNORECASE | re.MULTILINE)
        for m in rx.finditer(code):
            out.append((m, msg, cat))
    return out


class LifeGuard:
    def __init__(self, extra_patterns: Optional[List[Tuple[str, str, str]]] = None):
        self.extra_patterns = extra_patterns or []

    def observe(self, cell: Cell) -> List[LifeGuardNote]:
        code = cell.code or ""
        if not code.strip():
            return []

        notes: List[LifeGuardNote] = []
        all_patterns = SECURITY_PATTERNS + QUALITY_PATTERNS + PERF_PATTERNS + list(self.extra_patterns)
        for match, msg, cat in _iter_matches(all_patterns, code):
            line = code[: match.start()].count("\n") + 1
            severity = Severity.CRITICAL if cat == "security" else Severity.WARN
            notes.append(LifeGuardNote(category=cat, severity=severity, message=msg, line=line))

        lines = code.splitlines()
        if len(lines) >= 250:
            notes.append(
                LifeGuardNote(
                    category="style",
                    severity=Severity.WARN,
                    message=f"Cell is very long ({len(lines)} lines); consider splitting into smaller cells.",
                    line=1,
                )
            )

        if cell.language.lower() == "python":
            func_match = re.search(r"^def\s+([A-Za-z_]\w*)\s*\(", code, flags=re.MULTILINE)
            if func_match:
                name = func_match.group(1)
                if not name.startswith("_"):
                    has_doc = re.search(
                        r"def\s+" + re.escape(name) + r"\s*\([^)]*\)\s*:\s*\n\s*['\"]{3}", code
                    )
                    if not has_doc:
                        notes.append(
                            LifeGuardNote(
                                category="style",
                                severity=Severity.WARN,
                                message="Function is missing a docstring.",
                                line=code[: func_match.start()].count("\n") + 1,
                                suggestion="Add a triple-quoted docstring right under the function definition.",
                            )
                        )

        for n in notes:
            cell.add_feedback(n.to_dict())
        return notes

    def review_execution(self, cell: Cell, *, stdout: str, stderr: str, success: bool) -> List[LifeGuardNote]:
        notes: List[LifeGuardNote] = []
        stderr = stderr or ""
        stdout = stdout or ""

        if not success:
            m = re.search(r"ModuleNotFoundError: No module named '([^']+)'", stderr)
            if m:
                missing = m.group(1)
                notes.append(
                    LifeGuardNote(
                        category="runtime",
                        severity=Severity.ERROR,
                        message=f"Missing dependency/module: {missing}",
                        suggestion=f"Install or vendor '{missing}', or update imports.",
                    )
                )
            elif "SyntaxError" in stderr:
                notes.append(LifeGuardNote(category="runtime", severity=Severity.ERROR, message="Syntax error detected."))
            elif "TypeError" in stderr:
                notes.append(LifeGuardNote(category="runtime", severity=Severity.ERROR, message="Type error detected."))
            elif "NameError" in stderr:
                m2 = re.search(r"name '([^']+)' is not defined", stderr)
                var = m2.group(1) if m2 else "unknown"
                notes.append(
                    LifeGuardNote(
                        category="runtime",
                        severity=Severity.ERROR,
                        message=f"NameError: {var} is not defined",
                    )
                )
            else:
                return []
        else:
            if len(stdout) >= 200_000:
                notes.append(
                    LifeGuardNote(
                        category="performance",
                        severity=Severity.WARN,
                        message="Large output detected; consider truncating prints/logs.",
                    )
                )

        for n in notes:
            cell.add_feedback(n.to_dict())
        return notes


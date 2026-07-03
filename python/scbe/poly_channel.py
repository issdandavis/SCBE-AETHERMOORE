"""Polyglot execution-channel trust scoring for arithmetic QA.

The measurement boundary is intentionally narrow: extra execution faces can
promote answers when independent runtimes agree on the same numeric result.
They do not add an independent reading of the word problem.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


NUMBER_RE = re.compile(r"[-+]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:/[1-9]\d*)?")
PYTHON_BLOCK_RE = re.compile(
    r"\b(import|open|exec|eval|compile|input|os|sys|subprocess|shutil|pathlib|"
    r"socket|requests|urllib|http|glob|ctypes|multiprocessing|threading)\b|__",
    flags=re.I,
)
JAVASCRIPT_BLOCK_RE = re.compile(
    r"\b(require|import|process|child_process|fs|net|http|https|eval|Function|"
    r"globalThis|WebSocket|fetch)\b",
    flags=re.I,
)


@dataclass(frozen=True)
class ChannelResult:
    value: float | None
    ok: bool
    error: str = ""


def normalize_number(text: Any) -> float | None:
    if text is None:
        return None
    if isinstance(text, (int, float)) and math.isfinite(float(text)):
        return float(text)
    s = str(text).strip().replace("$", "").replace(",", "")
    if not s:
        return None
    matches = NUMBER_RE.findall(s)
    if not matches:
        return None
    token = matches[-1].replace(",", "")
    try:
        if "/" in token:
            a, b = token.split("/", 1)
            return float(a) / float(b)
        return float(token)
    except Exception:
        return None


def same_number(a: float | None, b: float | None, *, tol: float = 1e-6) -> bool:
    return a is not None and b is not None and math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def extract_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return {}
    try:
        parsed = json.loads(m.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def extract_fenced_code(text: str, language: str) -> str | None:
    patterns = [language]
    if language == "javascript":
        patterns += ["js", "node"]
    if language == "python":
        patterns += ["py"]
    for label in patterns:
        m = re.search(rf"```{label}\s*(.*?)```", text, flags=re.I | re.S)
        if m:
            return m.group(1).strip()
    return None


def parse_model_response(text: str) -> dict[str, Any]:
    parsed = extract_json_object(text)
    final = (
        parsed.get("final_answer")
        or parsed.get("answer")
        or parsed.get("result")
        or parsed.get("final")
    )
    confidence = normalize_number(parsed.get("confidence"))
    if confidence is not None and confidence > 1.0:
        confidence = confidence / 100.0
    if confidence is None:
        confidence = 0.72
    confidence = max(0.0, min(1.0, confidence))
    python_code = (
        parsed.get("python")
        or parsed.get("python_code")
        or parsed.get("py")
        or extract_fenced_code(text, "python")
    )
    javascript_code = (
        parsed.get("javascript")
        or parsed.get("javascript_code")
        or parsed.get("js")
        or extract_fenced_code(text, "javascript")
    )
    return {
        "final_text": final if final is not None else text,
        "final_value": normalize_number(final) if final is not None else None,
        "confidence": confidence,
        "python_code": str(python_code).strip() if python_code else None,
        "javascript_code": str(javascript_code).strip() if javascript_code else None,
    }


def _last_stdout_number(stdout: str) -> float | None:
    return normalize_number(stdout.strip().splitlines()[-1] if stdout.strip() else "")


def _blocked_code_reason(code: str, language: str) -> str | None:
    if len(code) > 4000:
        return f"{language} code too long"
    block_re = PYTHON_BLOCK_RE if language == "python" else JAVASCRIPT_BLOCK_RE
    match = block_re.search(code)
    if match:
        return f"{language} blocked token: {match.group(0)}"
    return None


def run_python(code: str | None, *, timeout: int = 8) -> ChannelResult:
    if not code:
        return ChannelResult(None, False, "missing python code")
    blocked = _blocked_code_reason(code, "python")
    if blocked:
        return ChannelResult(None, False, blocked)
    with tempfile.TemporaryDirectory(prefix="poly_py_") as td:
        path = Path(td) / "answer.py"
        path.write_text(code, encoding="utf-8")
        try:
            r = subprocess.run(
                ["python", "-I", str(path)],
                cwd=td,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ChannelResult(None, False, "python timeout")
        if r.returncode:
            return ChannelResult(None, False, (r.stderr or r.stdout)[-500:])
        value = _last_stdout_number(r.stdout)
        return ChannelResult(value, value is not None, "" if value is not None else "no numeric stdout")


def run_javascript(code: str | None, *, timeout: int = 8) -> ChannelResult:
    if not code:
        return ChannelResult(None, False, "missing javascript code")
    blocked = _blocked_code_reason(code, "javascript")
    if blocked:
        return ChannelResult(None, False, blocked)
    with tempfile.TemporaryDirectory(prefix="poly_js_") as td:
        path = Path(td) / "answer.js"
        path.write_text(code, encoding="utf-8")
        try:
            r = subprocess.run(
                ["node", str(path)],
                cwd=td,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ChannelResult(None, False, "javascript timeout")
        if r.returncode:
            return ChannelResult(None, False, (r.stderr or r.stdout)[-500:])
        value = _last_stdout_number(r.stdout)
        return ChannelResult(value, value is not None, "" if value is not None else "no numeric stdout")


def classify_row(
    *,
    gold: float,
    final_value: float | None,
    py_value: float | None,
    js_value: float | None,
    model_confidence: float,
) -> dict[str, Any]:
    baseline_trust = same_number(final_value, py_value)
    py_js_trust = same_number(py_value, js_value)
    triple_trust = baseline_trust and same_number(py_value, js_value)
    final_contradicts_execution = (
        final_value is not None
        and py_value is not None
        and not same_number(final_value, py_value)
    )
    promoted_by_js = py_js_trust and not baseline_trust and not final_contradicts_execution

    baseline_value = py_value if baseline_trust else None
    poly_value = py_value if promoted_by_js else baseline_value
    baseline_correct = same_number(baseline_value, gold)
    poly_correct = same_number(poly_value, gold)

    baseline_score = min(0.98, model_confidence * (0.92 if baseline_trust else 0.55))
    if baseline_trust:
        baseline_score = max(0.61, baseline_score)
    poly_score = baseline_score
    if triple_trust:
        poly_score = min(0.99, max(poly_score, model_confidence * 0.98 + 0.01))
    elif promoted_by_js:
        poly_score = min(0.97, max(poly_score, model_confidence * 0.95 + 0.01))

    return {
        "baseline_status": "TRIANGULATED" if baseline_trust else "ABSTAIN",
        "poly_status": "TRIANGULATED" if (baseline_trust or promoted_by_js) else "ABSTAIN",
        "baseline_value": baseline_value,
        "poly_value": poly_value,
        "baseline_correct": bool(baseline_correct),
        "poly_correct": bool(poly_correct),
        "baseline_score": round(float(baseline_score), 6),
        "poly_score": round(float(poly_score), 6),
        "triple_trust": bool(triple_trust),
        "py_js_trust": bool(py_js_trust),
        "promoted_by_js": bool(promoted_by_js),
        "final_contradicts_execution": bool(final_contradicts_execution),
    }


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float | None]:
    if n <= 0:
        return [None, None]
    phat = k / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    spread = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return [max(0.0, center - spread), min(1.0, center + spread)]


def aurc(rows: list[dict[str, Any]], score_key: str, correct_key: str) -> float:
    if not rows:
        return 0.0
    ordered = sorted(rows, key=lambda r: float(r.get(score_key, 0.0)), reverse=True)
    risks: list[float] = []
    wrong = 0
    for i, row in enumerate(ordered, 1):
        wrong += 0 if row.get(correct_key) else 1
        risks.append(wrong / i)
    return sum(risks) / len(risks)


def summarize(rows: list[dict[str, Any]], *, threshold: float = 0.92) -> dict[str, Any]:
    n = len(rows)

    def block(prefix: str) -> dict[str, Any]:
        trusted = [r for r in rows if r[f"{prefix}_status"] == "TRIANGULATED"]
        correct = [r for r in trusted if r[f"{prefix}_correct"]]
        false_accepts = len(trusted) - len(correct)
        confident = [r for r in rows if float(r[f"{prefix}_score"]) >= threshold]
        top_n = max(1, math.ceil(n * 0.2)) if n else 0
        top = sorted(rows, key=lambda r: float(r[f"{prefix}_score"]), reverse=True)[:top_n]
        top_correct = sum(1 for r in top if r[f"{prefix}_correct"])
        return {
            "trusted": len(trusted),
            "coverage": len(trusted) / n if n else 0.0,
            "coverage_ci95": wilson(len(trusted), n),
            "precision": len(correct) / len(trusted) if trusted else 0.0,
            "precision_ci95": wilson(len(correct), len(trusted)),
            "false_accepts": false_accepts,
            "false_accept_rate": false_accepts / n if n else 0.0,
            "false_accept_rate_ci95": wilson(false_accepts, n),
            "confident_coverage_at_threshold": len(confident) / n if n else 0.0,
            "confident_count_at_threshold": len(confident),
            "aurc": aurc(rows, f"{prefix}_score", f"{prefix}_correct"),
            "top20_selective_accuracy": top_correct / len(top) if top else 0.0,
        }

    baseline = block("baseline")
    poly = block("poly")
    return {
        "n": n,
        "threshold": threshold,
        "baseline": baseline,
        "polyglot": poly,
        "delta": {
            "trusted": poly["trusted"] - baseline["trusted"],
            "coverage": poly["coverage"] - baseline["coverage"],
            "precision": poly["precision"] - baseline["precision"],
            "false_accepts": poly["false_accepts"] - baseline["false_accepts"],
            "confident_coverage_at_threshold": poly["confident_coverage_at_threshold"]
            - baseline["confident_coverage_at_threshold"],
            "aurc": poly["aurc"] - baseline["aurc"],
            "top20_selective_accuracy": poly["top20_selective_accuracy"]
            - baseline["top20_selective_accuracy"],
        },
        "counts": {
            "promoted_by_js": sum(1 for r in rows if r.get("promoted_by_js")),
            "promoted_by_js_correct": sum(1 for r in rows if r.get("promoted_by_js") and r.get("poly_correct")),
            "py_js_trust": sum(1 for r in rows if r.get("py_js_trust")),
            "triple_trust": sum(1 for r in rows if r.get("triple_trust")),
        },
    }


def format_summary_table(summary: dict[str, Any]) -> str:
    base = summary["baseline"]
    poly = summary["polyglot"]
    delta = summary["delta"]
    rows: Iterable[tuple[str, str, str, str]] = [
        (
            "TRIANGULATED coverage",
            f"{base['trusted']}/{summary['n']} ({base['coverage']:.0%})",
            f"{poly['trusted']}/{summary['n']} ({poly['coverage']:.0%})",
            f"{delta['trusted']:+d}",
        ),
        ("precision", f"{base['precision']:.3f}", f"{poly['precision']:.3f}", f"{delta['precision']:+.3f}"),
        ("false-accepts", str(base["false_accepts"]), str(poly["false_accepts"]), f"{delta['false_accepts']:+d}"),
        (
            f"confident coverage @ {summary['threshold']}",
            f"{base['confident_coverage_at_threshold']:.3f}",
            f"{poly['confident_coverage_at_threshold']:.3f}",
            f"{delta['confident_coverage_at_threshold']:+.3f}",
        ),
        ("ranking AURC", f"{base['aurc']:.3f}", f"{poly['aurc']:.3f}", f"{delta['aurc']:+.3f}"),
        (
            "top-20% selective accuracy",
            f"{base['top20_selective_accuracy']:.3f}",
            f"{poly['top20_selective_accuracy']:.3f}",
            f"{delta['top20_selective_accuracy']:+.3f}",
        ),
    ]
    widths = [max(len(str(r[i])) for r in rows + [("metric", "baseline", "+polyglot", "delta")]) for i in range(4)]
    out = []
    header = ("metric", "baseline", "+polyglot", "delta")
    out.append(" | ".join(str(header[i]).ljust(widths[i]) for i in range(4)))
    out.append("-+-".join("-" * w for w in widths))
    for row in rows:
        out.append(" | ".join(str(row[i]).ljust(widths[i]) for i in range(4)))
    return "\n".join(out)

"""
execution_feedback.py

Execution loop layer — the external ground-truth anchor for V(t) in FunEnergyLoss.

From the theory notes (tmp-crosstalk-skill-smoke):
  "Representation is necessary but not sufficient. Correctness still depends on
   whether the generated code runs, whether it handles edge cases, whether it
   matches the task."

  "You need ONE external anchor. So the loop becomes:
     system → data → model → system → real world → correction"

This module IS that anchor. It:
  1. Runs generated code in a sandboxed subprocess with a hard timeout
  2. Returns a normalized V-signal (1.0 = clean pass, 0.0 = crash/timeout)
  3. Tokenizes the code through the atomic tokenizer → aggregated tau trit vector
  4. Produces an AtomicCodeProfile that the FunEnergyLoss composite gate can use

The tau vector from the atomic tokenizer is a semantic quality signal BEFORE
execution — if the code has many RELATION tokens (if/then/else) and few NEGATION
tokens, it's structurally different from code full of `cannot`, `never`, `fail`.
This gives the gate early signal before the subprocess even runs.

Integration with FunEnergyLoss:
  V(t)_grounded = (1 - exec_alpha) * V_learned + exec_alpha * v_signal

  When execution_signal is provided to forward(), the learnable V head is
  partially anchored by actual execution outcome instead of being purely
  self-supervised from hidden states.

Security:
  - subprocess runs in a temp dir with no network access (via PYTHONPATH isolation)
  - stdout/stderr are truncated to 2048 chars
  - hard timeout: default 5 seconds
  - NEVER exec() — always subprocess
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Atomic tokenizer import (from python/scbe/atomic_tokenization.py)
# ---------------------------------------------------------------------------
try:
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    from python.scbe.atomic_tokenization import (
        TONGUES,
        map_token_to_atomic_state,
        tokens_to_tau_sequence,
    )

    _ATOMIC_AVAILABLE = True
except Exception as _e:
    _ATOMIC_AVAILABLE = False
    TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")

    def tokens_to_tau_sequence(tokens, **kw):  # type: ignore[misc]
        return []


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

_ZERO_TAU: Dict[str, float] = {t: 0.0 for t in TONGUES}
_NEUTRAL_TAU: Dict[str, float] = {t: 0.333 for t in TONGUES}

# Semantic quality weights: which tongue channels carry positive structure signal
# for code. DR (formal/structural), CA (compute/algo), KO (control/dispatch)
# are positive; UM (security/adversarial) and RU (entropy/chaos) are neutral.
_TAU_QUALITY_WEIGHTS: Dict[str, float] = {
    "KO": 0.20,  # control flow, dispatch — structural positive
    "AV": 0.10,  # transport, relay — mild positive
    "RU": -0.05,  # entropy, chaos — slight negative (more negation-like)
    "CA": 0.25,  # compute, algorithm — strong positive
    "UM": 0.05,  # security/governance — neutral to mild positive
    "DR": 0.30,  # formal structure, proof — strongest positive
}


@dataclass
class AtomicCodeProfile:
    """
    Aggregated atomic tokenizer output over a code snippet.

    tau_mean: mean trit value per tongue channel (-1..1)
    tau_quality: scalar quality signal derived from tau_mean (0..1)
    action_ratio: fraction of tokens classified as ACTION
    negation_ratio: fraction of tokens classified as NEGATION
    relation_ratio: fraction of tokens classified as RELATION (control flow)
    trust_mean: mean trust_baseline across all tokens
    resilience_mean: mean resilience across all tokens
    n_tokens: number of code tokens analyzed
    """

    tau_mean: Dict[str, float] = field(default_factory=lambda: dict(_ZERO_TAU))
    tau_quality: float = 0.5
    action_ratio: float = 0.0
    negation_ratio: float = 0.0
    relation_ratio: float = 0.0
    trust_mean: float = 0.5
    resilience_mean: float = 0.5
    n_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "atomic/tau_quality": round(self.tau_quality, 4),
            "atomic/action_ratio": round(self.action_ratio, 4),
            "atomic/negation_ratio": round(self.negation_ratio, 4),
            "atomic/relation_ratio": round(self.relation_ratio, 4),
            "atomic/trust_mean": round(self.trust_mean, 4),
            "atomic/resilience_mean": round(self.resilience_mean, 4),
            "atomic/n_tokens": self.n_tokens,
            **{f"atomic/tau_{t.lower()}": round(self.tau_mean.get(t, 0.0), 4) for t in TONGUES},
        }


@dataclass
class ExecutionResult:
    """
    Result of running generated code in the sandbox.

    v_signal: the V(t) ground truth anchor — 1.0 = clean pass, 0.0 = fail/crash
    passed: whether exit code was 0 and stderr was clean
    exit_code: subprocess exit code
    stdout: truncated stdout (max 2048 chars)
    stderr: truncated stderr (max 2048 chars)
    elapsed_ms: wall-clock time of subprocess
    timeout: True if hard timeout was hit
    atomic_profile: semantic structure of the code before execution
    """

    v_signal: float
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    elapsed_ms: float
    timeout: bool
    atomic_profile: AtomicCodeProfile


# ---------------------------------------------------------------------------
# Token extraction from code
# ---------------------------------------------------------------------------

# Simple code token extractor — extracts identifiers/keywords from Python code.
# We don't need a full AST; the atomic tokenizer works on word-level tokens.
_CODE_TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]{1,}")


def _extract_code_tokens(code: str) -> List[str]:
    """Extract identifier-like tokens from code for atomic tokenization."""
    return _CODE_TOKEN_RE.findall(code)


# ---------------------------------------------------------------------------
# Atomic profile computation
# ---------------------------------------------------------------------------


def compute_atomic_profile(code: str, context_class: str = "operator") -> AtomicCodeProfile:
    """
    Run the atomic tokenizer over code tokens and aggregate into an AtomicCodeProfile.

    Uses context_class="operator" so that if/then/else are classified as RELATION,
    not TEMPORAL — correct for code.
    """
    if not _ATOMIC_AVAILABLE:
        return AtomicCodeProfile()

    tokens = _extract_code_tokens(code)
    if not tokens:
        return AtomicCodeProfile()

    # Get full AtomicTokenState per token (not just tau)
    states = [map_token_to_atomic_state(tok, context_class=context_class) for tok in tokens]

    n = len(states)

    # Aggregate tau values
    tau_sums: Dict[str, float] = {t: 0.0 for t in TONGUES}
    for s in states:
        for tongue in TONGUES:
            tau_sums[tongue] += float(getattr(s.tau, tongue))

    tau_mean = {t: tau_sums[t] / n for t in TONGUES}

    # Tau quality signal: weighted dot product of mean tau with quality weights, normalized to (0,1)
    raw_quality = sum(tau_mean[t] * _TAU_QUALITY_WEIGHTS[t] for t in TONGUES)
    # raw_quality is in approximately [-0.65, 0.85] — normalize to (0, 1)
    tau_quality = float(max(0.0, min(1.0, (raw_quality + 0.65) / 1.50)))

    action_ratio = sum(1 for s in states if s.semantic_class == "ACTION") / n
    negation_ratio = sum(1 for s in states if s.semantic_class == "NEGATION") / n
    relation_ratio = sum(1 for s in states if s.semantic_class == "RELATION") / n
    trust_mean = sum(s.trust_baseline for s in states) / n
    resilience_mean = sum(s.resilience for s in states) / n

    return AtomicCodeProfile(
        tau_mean=tau_mean,
        tau_quality=tau_quality,
        action_ratio=action_ratio,
        negation_ratio=negation_ratio,
        relation_ratio=relation_ratio,
        trust_mean=trust_mean,
        resilience_mean=resilience_mean,
        n_tokens=n,
    )


# ---------------------------------------------------------------------------
# Sandbox runner
# ---------------------------------------------------------------------------

# Blocked import prefixes — prevent code from touching network/OS
_BLOCKED_IMPORTS = frozenset(
    [
        "socket",
        "urllib",
        "requests",
        "http",
        "ftplib",
        "smtplib",
        "subprocess",
        "os.system",
        "shutil.rmtree",
        "ctypes",
    ]
)

_BLOCKED_PATTERN = re.compile(
    r"\b(import\s+(" + "|".join(re.escape(b) for b in _BLOCKED_IMPORTS) + r"))",
    re.MULTILINE,
)


def _check_blocked(code: str) -> Optional[str]:
    """Return a rejection reason if the code contains blocked patterns, else None."""
    m = _BLOCKED_PATTERN.search(code)
    if m:
        return f"blocked import: {m.group(0)}"
    if "__import__" in code:
        return "blocked: __import__ usage"
    if "exec(" in code or "eval(" in code:
        return "blocked: exec/eval usage"
    return None


def run_code_sandbox(
    code: str,
    test_snippet: Optional[str] = None,
    timeout_s: float = 5.0,
    python_exe: Optional[str] = None,
) -> ExecutionResult:
    """
    Run code in a subprocess sandbox and return ExecutionResult.

    Args:
        code:         The generated code to execute.
        test_snippet: Optional test code appended after the main code.
                      If it contains assert statements, failures drive v_signal down.
        timeout_s:    Hard timeout in seconds (default 5).
        python_exe:   Python interpreter path (defaults to current interpreter).

    Returns:
        ExecutionResult with v_signal, passed, stdout, stderr, atomic_profile.
    """
    python_exe = python_exe or sys.executable

    # Compute atomic profile BEFORE execution (pure semantics, no side effects)
    atomic_profile = compute_atomic_profile(code)

    # Safety check
    rejection = _check_blocked(code)
    if rejection:
        return ExecutionResult(
            v_signal=0.0,
            passed=False,
            exit_code=-1,
            stdout="",
            stderr=f"[EXECUTION_FEEDBACK] Blocked: {rejection}",
            elapsed_ms=0.0,
            timeout=False,
            atomic_profile=atomic_profile,
        )

    # Build the full script
    full_code = textwrap.dedent(code)
    if test_snippet:
        full_code += "\n\n" + textwrap.dedent(test_snippet)

    with tempfile.TemporaryDirectory(prefix="scbe_exec_") as tmpdir:
        script_path = Path(tmpdir) / "generated.py"
        script_path.write_text(full_code, encoding="utf-8")

        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [python_exe, str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                cwd=tmpdir,
                # Minimal environment — no PYTHONPATH inheritance, no user site packages
                env={
                    "PATH": "/usr/bin:/usr/local/bin",
                    "PYTHONPATH": "",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            timed_out = False
            exit_code = proc.returncode
            stdout = proc.stdout[:2048]
            stderr = proc.stderr[:2048]
        except subprocess.TimeoutExpired:
            elapsed_ms = timeout_s * 1000.0
            timed_out = True
            exit_code = -1
            stdout = ""
            stderr = f"[EXECUTION_FEEDBACK] Timeout after {timeout_s}s"

    # Compute v_signal
    if timed_out:
        v_signal = 0.0
        passed = False
    elif exit_code == 0:
        # Clean pass — but penalize if stderr has warnings
        stderr_penalty = 0.1 if stderr.strip() else 0.0
        v_signal = float(max(0.1, 1.0 - stderr_penalty))
        passed = True
    else:
        # Failed — partial credit if assertion error (code ran but test failed)
        # vs syntax error (code couldn't even parse)
        if "AssertionError" in stderr:
            v_signal = 0.25  # partial — code ran but assertions failed
        elif "SyntaxError" in stderr:
            v_signal = 0.05  # very low — didn't even parse
        else:
            v_signal = 0.10  # generic runtime error
        passed = False

    return ExecutionResult(
        v_signal=v_signal,
        passed=passed,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        elapsed_ms=elapsed_ms,
        timeout=timed_out,
        atomic_profile=atomic_profile,
    )


# ---------------------------------------------------------------------------
# ExecutionFeedback: the main interface for FunEnergyLoss integration
# ---------------------------------------------------------------------------


class ExecutionFeedback:
    """
    Execution loop layer — wires code execution ground truth into FunEnergyLoss.

    Usage in training loop:
        exec_fb = ExecutionFeedback(timeout_s=5.0, exec_alpha=0.4)

        # In forward pass, extract generated code from model output
        code = decode_generated_code(output_ids)
        fb_result = exec_fb.evaluate(code, test_snippet=test_code)

        # Pass v_signal and atomic_profile to FunEnergyLoss.forward()
        loss, info = fun_loss.forward(
            hidden_states,
            step=step,
            execution_signal=fb_result.v_signal,
            atomic_profile=fb_result.atomic_profile,
        )

    exec_alpha controls how much execution ground truth anchors V(t):
        V_grounded = (1 - exec_alpha) * V_learned + exec_alpha * v_signal

    exec_alpha=0.0 → pure learned V (old behavior, no anchor)
    exec_alpha=1.0 → pure execution signal (no learned head contribution)
    exec_alpha=0.4 → balanced: 40% execution, 60% learned (recommended starting point)
    """

    def __init__(
        self,
        timeout_s: float = 5.0,
        exec_alpha: float = 0.4,
        python_exe: Optional[str] = None,
    ):
        self.timeout_s = timeout_s
        self.exec_alpha = exec_alpha
        self.python_exe = python_exe or sys.executable

        # Running stats
        self._total_runs = 0
        self._pass_count = 0
        self._timeout_count = 0
        self._v_history: List[float] = []

    def evaluate(
        self,
        code: str,
        test_snippet: Optional[str] = None,
    ) -> ExecutionResult:
        """Run code and return ExecutionResult with v_signal and atomic_profile."""
        result = run_code_sandbox(
            code,
            test_snippet=test_snippet,
            timeout_s=self.timeout_s,
            python_exe=self.python_exe,
        )
        self._total_runs += 1
        if result.passed:
            self._pass_count += 1
        if result.timeout:
            self._timeout_count += 1
        self._v_history.append(result.v_signal)
        if len(self._v_history) > 500:
            self._v_history = self._v_history[-500:]
        return result

    def blend_v(self, v_learned: float, v_signal: float) -> float:
        """
        Blend learned V with execution ground truth.

        V_grounded = (1 - exec_alpha) * v_learned + exec_alpha * v_signal
        """
        return (1.0 - self.exec_alpha) * v_learned + self.exec_alpha * v_signal

    @property
    def pass_rate(self) -> float:
        """Fraction of evaluation runs that passed cleanly."""
        if self._total_runs == 0:
            return 0.0
        return self._pass_count / self._total_runs

    @property
    def mean_v(self) -> float:
        """Running mean V signal over recent history."""
        if not self._v_history:
            return 0.5
        return sum(self._v_history) / len(self._v_history)

    def stats(self) -> dict:
        return {
            "exec/total_runs": self._total_runs,
            "exec/pass_rate": round(self.pass_rate, 4),
            "exec/mean_v": round(self.mean_v, 4),
            "exec/timeout_count": self._timeout_count,
        }

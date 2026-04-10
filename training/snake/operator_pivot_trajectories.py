#!/usr/bin/env python3
"""
Operator Pivot Trajectories — Multi-step coding trajectories through pivot protocol.

Connects three pieces:
  1. SS1 Sacred Tongue Tokenizer (encoding engine)
  2. Tokenizer Master Class (phi-weighted math curriculum)
  3. Operator Loop (attempt -> failure -> diagnosis -> fix -> success)

Each trajectory is a measured conversation through the ControlledPivotEngine.
Every step is a pivot point with PivotScore (relevance, growth, novelty, coherence).
Tongue-tagged at every step: KO=intent, AV=context, CA=logic, RU=governance, UM=security, DR=structure.

Output: SFT pairs (multi-turn trajectories) + DPO pairs (good fix vs bad fix)
"""

from __future__ import annotations

import json
import math
import random
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PHI = (1 + math.sqrt(5)) / 2

# ---------------------------------------------------------------------------
# HYDRA Dual Head Configuration — planner + coder heads deliberate per step
# ---------------------------------------------------------------------------
# Modeled after hydra/remote_coding_worker.py (Switchboard role-based workers)
# and hydra/consensus.py (ByzantineConsensus / RoundtableConsensus)

HYDRA_HEADS = {
    "planner": {
        "callsign": "Head-Alpha",
        "tongue": "KO",  # Intent — plans WHAT to do
        "roles": ["planner", "reviewer"],
        "phase_angle": 0,  # SwarmBrowser phase
        "system_prompt": (
            "You are Head-Alpha (Planner). Your role is to analyze the task, "
            "decompose it into steps, and verify the coder's patches are correct. "
            "You think BEFORE acting. Output structured plans and reviews."
        ),
    },
    "coder": {
        "callsign": "Head-Beta",
        "tongue": "CA",  # Compute — generates HOW to fix
        "roles": ["coder", "executor"],
        "phase_angle": 180,  # Opposite phase = complementary
        "system_prompt": (
            "You are Head-Beta (Coder). Your role is to generate minimal, correct patches "
            "based on the planner's analysis. You write code, not plans. "
            "Output diffs and structured edit actions."
        ),
    },
}


@dataclass
class HydraMessage:
    """A message between HYDRA heads via Switchboard role channels."""

    sender: str  # head callsign
    channel: str  # role channel name
    content: str
    tongue: str
    confidence: float = 0.0
    decision: str = ""  # ALLOW / DENY / ESCALATE from consensus


@dataclass
class HydraDeliberation:
    """Result of dual-head consensus on a coding step."""

    planner_assessment: str
    coder_proposal: str
    consensus: str  # ALLOW = proceed, ESCALATE = needs more context, DENY = wrong approach
    confidence: float
    messages: List[HydraMessage] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "planner": self.planner_assessment,
            "coder": self.coder_proposal,
            "consensus": self.consensus,
            "confidence": round(self.confidence, 4),
            "n_messages": len(self.messages),
        }


# ---------------------------------------------------------------------------
# PivotScore — control metric for every step transition
# ---------------------------------------------------------------------------
@dataclass
class PivotScore:
    """Measured quality of a pivot. Not random."""

    relevance: float  # 0-1: does this step connect to prior context?
    growth: float  # 0-1: did we learn something new?
    novelty: float  # 0-1: is this a path not yet taken?
    coherence: float  # 0-1: does the trajectory still make sense?

    @property
    def quality(self) -> float:
        """Weighted composite. Coherence matters most."""
        return 0.20 * self.relevance + 0.25 * self.growth + 0.20 * self.novelty + 0.35 * self.coherence

    @property
    def is_good(self) -> bool:
        return self.quality >= 0.5

    def to_dict(self) -> dict:
        d = asdict(self)
        d["quality"] = round(self.quality, 4)
        d["is_good"] = self.is_good
        return d


# ---------------------------------------------------------------------------
# OperatorStep — a single step in a coding trajectory
# ---------------------------------------------------------------------------
@dataclass
class OperatorStep:
    """One step in an attempt -> failure -> diagnosis -> fix -> success chain."""

    step_type: str  # analyze | attempt | failure | diagnose | fix | verify
    tongue: str  # KO/AV/RU/CA/UM/DR
    instruction: str
    response: str
    action: Optional[Dict[str, str]] = None  # structured decision output
    pivot_score: Optional[PivotScore] = None
    error_output: Optional[str] = None
    patch: Optional[str] = None


# ---------------------------------------------------------------------------
# Operator Topic Graph — coding trajectory steps as pivot topics
# ---------------------------------------------------------------------------
@dataclass
class OperatorTopic:
    """A topic in the operator pivot graph."""

    id: str
    name: str
    tongue: str
    step_type: str
    depth: int
    connections: List[str]
    instruction_templates: List[str]
    response_templates: List[str]
    bad_response_templates: List[str] = field(default_factory=list)


# The operator topic graph — each step type is a topic node
OPERATOR_TOPICS: Dict[str, OperatorTopic] = {
    # --- Step 1: Analyze the task (KO = intent) ---
    "analyze_task": OperatorTopic(
        id="analyze_task",
        name="Task Analysis",
        tongue="KO",
        step_type="analyze",
        depth=0,
        connections=["read_context", "attempt_fix"],
        instruction_templates=[
            "Analyze this failing test: {test_name}. Error: {error_type}. What needs to change?",
            "Task: {task_desc}. Identify the root cause before writing any code.",
            "Test {test_name} fails with {error_type}. Break down what the test expects vs what the code does.",
        ],
        response_templates=[
            "The test expects {expected} but the function returns {actual}. Root cause: {root_cause}. The fix requires changing {file}:{line} to {change_desc}.",
            "Analysis: {error_type} in {file}. The function {func_name} {problem_desc}. This is a {severity} issue because {reason}.",
            "Breaking down the failure:\n1. Test assertion: {assertion}\n2. Actual behavior: {actual}\n3. Root cause: {root_cause}\n4. Fix location: {file}:{line}",
        ],
        bad_response_templates=[
            "I'll rewrite the whole file to fix this.",
            "Just delete the test, it's wrong.",
            "Let me try random changes until it works.",
        ],
    ),
    # --- Step 2: Read context (AV = context/transport) ---
    "read_context": OperatorTopic(
        id="read_context",
        name="Context Gathering",
        tongue="AV",
        step_type="analyze",
        depth=0,
        connections=["analyze_task", "attempt_fix", "check_imports"],
        instruction_templates=[
            "Read {file} and identify all functions that {task_desc}.",
            "What does {func_name} in {file} actually do? Show its signature and dependencies.",
            "List all imports in {file} and check which ones are used by {func_name}.",
        ],
        response_templates=[
            "File {file} contains {n_funcs} functions. The relevant one is {func_name}({params}) -> {return_type} at line {line}. It depends on: {deps}.",
            "{func_name} at {file}:{line}:\n- Signature: ({params}) -> {return_type}\n- Calls: {calls}\n- Called by: {callers}\n- Imports needed: {imports}",
            "Import analysis for {file}:\n- Used: {used_imports}\n- Unused: {unused_imports}\n- Missing: {missing_imports}",
        ],
        bad_response_templates=[
            "I don't need to read the file, I know what it does.",
            "The file is too long, let me just guess.",
        ],
    ),
    # --- Step 3: Check imports (DR = structure) ---
    "check_imports": OperatorTopic(
        id="check_imports",
        name="Import Verification",
        tongue="DR",
        step_type="analyze",
        depth=1,
        connections=["read_context", "attempt_fix", "diagnose_error"],
        instruction_templates=[
            "Verify that modifying {file} won't break imports in {dependent_files}.",
            "Check cross-file consistency: {file_a} imports {symbol} from {file_b}. Will the patch break this?",
            "Map the import graph for {module}. Which files import what from where?",
        ],
        response_templates=[
            "Import graph for {module}:\n{import_tree}\nModifying {file} will affect {n_dependents} files: {dependent_files}.",
            "Cross-check: {file_a} imports {symbol} from {file_b}. The patch changes {symbol}'s signature from ({old_sig}) to ({new_sig}). {n_dependents} consumers need updating.",
            "Safe to patch. {file} exports {symbols}. None of the changed symbols are imported elsewhere.",
        ],
        bad_response_templates=[
            "Imports don't matter, just change the function.",
        ],
    ),
    # --- Step 4: Attempt the fix (CA = compute/logic) ---
    "attempt_fix": OperatorTopic(
        id="attempt_fix",
        name="Patch Generation",
        tongue="CA",
        step_type="attempt",
        depth=1,
        connections=["run_tests", "diagnose_error", "read_context"],
        instruction_templates=[
            "Generate a minimal patch for {file}:{line} to fix {error_type}.",
            "Write the smallest possible change to make {test_name} pass.",
            "Apply this fix to {file}: change {old_code} to {new_code}. Show the diff.",
        ],
        response_templates=[
            '{{"action": "edit_file", "file": "{file}", "line": {line}, "patch": "- {old_line}\\n+ {new_line}", "reason": "{reason}"}}',
            "Patch for {file}:{line}:\n```diff\n- {old_line}\n+ {new_line}\n```\nReason: {reason}. This is the minimal change — {n_lines} line(s) modified.",
            "Structured decision:\n- Action: edit_file\n- File: {file}\n- Line: {line}\n- Old: {old_line}\n- New: {new_line}\n- Confidence: {confidence}",
        ],
        bad_response_templates=[
            "Let me rewrite the entire function from scratch.",
            "I'll add a try/except to hide the error.",
            "Just change the return type to Any.",
        ],
    ),
    # --- Step 5: Run tests (RU = governance/verification) ---
    "run_tests": OperatorTopic(
        id="run_tests",
        name="Test Verification",
        tongue="RU",
        step_type="verify",
        depth=2,
        connections=["diagnose_error", "success", "attempt_fix"],
        instruction_templates=[
            "Run pytest -q {test_file} and report results.",
            "Verify the patch: run {test_name} and check for regressions in {related_tests}.",
            "Execute the test suite. Did the fix work? Any new failures?",
        ],
        response_templates=[
            "Test results:\n  {test_name}: {result}\n  Regressions: {regressions}\n  Total: {passed}/{total} passed",
            "PASS: {test_name} now succeeds. No regressions in {n_related} related tests. Patch is clean.",
            "FAIL: {test_name} still fails.\n  Expected: {expected}\n  Got: {actual}\n  New error: {new_error}",
        ],
        bad_response_templates=[
            "Tests probably pass, no need to run them.",
            "One test fails but it's probably flaky.",
        ],
    ),
    # --- Step 6: Diagnose error (UM = security/investigation) ---
    "diagnose_error": OperatorTopic(
        id="diagnose_error",
        name="Error Diagnosis",
        tongue="UM",
        step_type="diagnose",
        depth=2,
        connections=["attempt_fix", "read_context", "check_imports"],
        instruction_templates=[
            "The patch failed. New error:\n{stack_trace}\nDiagnose what went wrong.",
            "Test still fails after fix. Error: {error_msg}. Was the root cause analysis wrong?",
            "Regression detected: {regression_test} now fails. The patch broke something else. Find what.",
        ],
        response_templates=[
            "Diagnosis: the patch fixed the original error but introduced {new_issue}. Stack trace shows {trace_analysis}. The actual root cause is deeper: {deeper_cause}.",
            "Root cause was partially correct. The {error_type} is fixed, but there's a second issue: {second_issue} at {file}:{line}. Need a two-part fix.",
            "Regression analysis: {regression_test} fails because {regression_cause}. The patch changed {symbol} which is also used by {other_func}. Fix: {fix_desc}.",
        ],
        bad_response_templates=[
            "I don't know why it failed. Let me try something completely different.",
            "The error message is confusing, let me ignore it.",
        ],
    ),
    # --- Step 7: Success (all tongues) — connects back for cyclic loops ---
    "success": OperatorTopic(
        id="success",
        name="Verification Complete",
        tongue="RU",
        step_type="verify",
        depth=3,
        connections=["analyze_task", "read_context"],  # CYCLIC: loops back
        instruction_templates=[
            "All tests pass. Summarize the fix and verify the diff is minimal.",
            "Patch verified. Generate the commit message.",
            "Fix complete. What was the trajectory? How many attempts?",
        ],
        response_templates=[
            "Fix complete:\n- Root cause: {root_cause}\n- Patch: {n_lines} line(s) in {n_files} file(s)\n- Tests: {passed}/{total} pass\n- Attempts: {n_attempts}\n- Trajectory: {trajectory}",
            "Commit: fix({module}): {commit_msg}\n\nChanged {file}:{line} — {change_desc}.\n{n_lines} line(s), {n_attempts} attempt(s).",
            "Trajectory summary:\n{trajectory_steps}\nTotal pivots: {n_pivots}, avg quality: {avg_quality:.3f}",
        ],
        bad_response_templates=[],
    ),
    # --- Step 8: HYDRA Planner deliberation ---
    "hydra_plan": OperatorTopic(
        id="hydra_plan",
        name="HYDRA Planner Assessment",
        tongue="KO",
        step_type="deliberate",
        depth=0,
        connections=["hydra_code", "analyze_task", "read_context"],
        instruction_templates=[
            "[HEAD-ALPHA:planner] Assess this task before coding: {task_desc}. What's the plan?",
            "[HEAD-ALPHA:planner] Review the diagnosis. Is the root cause correct? Should coder proceed?",
            "[HEAD-ALPHA:planner] The coder proposed a patch. Review it for correctness before applying.",
        ],
        response_templates=[
            "[HEAD-ALPHA] Plan:\n1. Read {file} to confirm {root_cause}\n2. Generate minimal patch at line {line}\n3. Run {test_name} to verify\nConfidence: 0.85. Dispatching to Head-Beta (coder).",
            "[HEAD-ALPHA] Root cause analysis is correct: {root_cause}. Risk: LOW. Consensus: ALLOW coder to proceed. Switchboard: enqueue(role=coder, action=edit_file).",
            "[HEAD-ALPHA] Patch review: changing {old_line} to {new_line} is correct. Side effects: none detected in {file}. Consensus: ALLOW. Commit when tests pass.",
        ],
        bad_response_templates=[
            "[HEAD-ALPHA] Just let the coder do whatever, I trust it.",
            "[HEAD-ALPHA] I'll code it myself instead of planning.",
        ],
    ),
    # --- Step 9: HYDRA Coder execution ---
    "hydra_code": OperatorTopic(
        id="hydra_code",
        name="HYDRA Coder Execution",
        tongue="CA",
        step_type="deliberate",
        depth=1,
        connections=["run_tests", "hydra_plan", "diagnose_error"],
        instruction_templates=[
            "[HEAD-BETA:coder] Execute the planner's directive. Generate patch for {file}:{line}.",
            "[HEAD-BETA:coder] Planner says root cause is {root_cause}. Write the minimal fix.",
            "[HEAD-BETA:coder] Second attempt. Previous patch failed. Apply the revised fix.",
        ],
        response_templates=[
            '[HEAD-BETA] Executing: {{"action": "edit_file", "file": "{file}", "line": {line}, "patch": "- {old_line}\\n+ {new_line}"}}\nState vector posted to coder channel. Awaiting test verification.',
            "[HEAD-BETA] Patch generated:\n```diff\n- {old_line}\n+ {new_line}\n```\nDecision record: action=edit_file, confidence=0.9, reason={root_cause}. Posting to switchboard.",
            "[HEAD-BETA] Revised patch (attempt 2):\n```diff\n- {old_line}\n+ {new_line}\n```\nLease renewed. Posting state vector to planner channel for review.",
        ],
        bad_response_templates=[
            "[HEAD-BETA] I disagree with the planner, let me rewrite everything.",
            "[HEAD-BETA] Adding try/except to suppress the error instead of fixing it.",
        ],
    ),
    # --- Step 10: HYDRA Consensus gate ---
    "hydra_consensus": OperatorTopic(
        id="hydra_consensus",
        name="HYDRA Consensus Gate",
        tongue="RU",
        step_type="deliberate",
        depth=2,
        connections=["run_tests", "hydra_plan", "hydra_code", "analyze_task"],
        instruction_templates=[
            "[CONSENSUS] Both heads have submitted. Tally votes on the proposed patch.",
            "[CONSENSUS] Planner and coder disagree. Run Roundtable resolution.",
            "[CONSENSUS] Cycle complete. Should we loop back to analyze or commit?",
        ],
        response_templates=[
            "[CONSENSUS] Votes: Head-Alpha=ALLOW(0.85), Head-Beta=ALLOW(0.90). Quorum: 2/2. Byzantine threshold: 0. Result: ALLOW. Proceeding to test verification.",
            "[CONSENSUS] Votes: Head-Alpha=ESCALATE(0.60), Head-Beta=ALLOW(0.80). No quorum on ALLOW. Escalating: planner requests more context. Routing to read_context.",
            "[CONSENSUS] Cycle {n_attempts} complete. All tests pass. Final consensus: ALLOW commit. Trajectory closed. Switchboard: complete_task(status=done).",
        ],
        bad_response_templates=[
            "[CONSENSUS] Skipping consensus, just apply the patch.",
        ],
    ),
}


# ---------------------------------------------------------------------------
# Bug/Fix Templates — real-world patterns to generate trajectories from
# ---------------------------------------------------------------------------
BUG_TEMPLATES = [
    {
        "id": "type_mismatch",
        "task_desc": "Fix type mismatch in return value",
        "test_name": "test_parse_value",
        "error_type": "TypeError",
        "file": "parser.py",
        "func_name": "parse_value",
        "line": 42,
        "expected": "int",
        "actual": "str",
        "root_cause": "parse_value returns str(x) instead of int(x)",
        "old_line": "return str(x)",
        "new_line": "return int(x)",
        "stack_trace": "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
    },
    {
        "id": "off_by_one",
        "task_desc": "Fix off-by-one error in range boundary",
        "test_name": "test_slice_range",
        "error_type": "IndexError",
        "file": "utils/array_ops.py",
        "func_name": "slice_range",
        "line": 17,
        "expected": "[1, 2, 3]",
        "actual": "IndexError: list index out of range",
        "root_cause": "range(len(arr)) should be range(len(arr) - 1) for pairwise comparison",
        "old_line": "for i in range(len(arr)):",
        "new_line": "for i in range(len(arr) - 1):",
        "stack_trace": "IndexError: list index out of range\n  File 'utils/array_ops.py', line 18, in slice_range\n    if arr[i] > arr[i+1]:",
    },
    {
        "id": "missing_import",
        "task_desc": "Fix missing import causing NameError",
        "test_name": "test_compute_hash",
        "error_type": "NameError",
        "file": "crypto/hasher.py",
        "func_name": "compute_hash",
        "line": 5,
        "expected": "sha256 hash string",
        "actual": "NameError: name 'hashlib' is not defined",
        "root_cause": "hashlib is used but never imported",
        "old_line": "# (missing import)",
        "new_line": "import hashlib",
        "stack_trace": "NameError: name 'hashlib' is not defined\n  File 'crypto/hasher.py', line 12, in compute_hash\n    h = hashlib.sha256(data)",
    },
    {
        "id": "none_check",
        "task_desc": "Fix AttributeError on None value",
        "test_name": "test_process_optional",
        "error_type": "AttributeError",
        "file": "handlers/processor.py",
        "func_name": "process_item",
        "line": 28,
        "expected": "empty list when input is None",
        "actual": "AttributeError: 'NoneType' object has no attribute 'items'",
        "root_cause": "No None check before calling .items() on optional dict parameter",
        "old_line": "for k, v in data.items():",
        "new_line": "for k, v in (data or {}).items():",
        "stack_trace": "AttributeError: 'NoneType' object has no attribute 'items'\n  File 'handlers/processor.py', line 28, in process_item",
    },
    {
        "id": "async_await",
        "task_desc": "Fix missing await on async function call",
        "test_name": "test_fetch_data",
        "error_type": "RuntimeWarning",
        "file": "api/client.py",
        "func_name": "fetch_data",
        "line": 45,
        "expected": "dict with response data",
        "actual": "coroutine object, never awaited",
        "root_cause": "async function called without await",
        "old_line": "result = session.get(url)",
        "new_line": "result = await session.get(url)",
        "stack_trace": "RuntimeWarning: coroutine 'ClientSession.get' was never awaited\n  result = session.get(url)",
    },
    {
        "id": "wrong_comparison",
        "task_desc": "Fix equality check that should be identity check",
        "test_name": "test_singleton_check",
        "error_type": "AssertionError",
        "file": "config/registry.py",
        "func_name": "is_registered",
        "line": 33,
        "expected": "True (singleton match)",
        "actual": "False (value equality fails on complex object)",
        "root_cause": "Using == instead of 'is' for singleton identity check",
        "old_line": "return instance == _registry[key]",
        "new_line": "return instance is _registry[key]",
        "stack_trace": "AssertionError: False is not True\n  assert is_registered('main', singleton_instance)",
    },
    {
        "id": "encoding_error",
        "task_desc": "Fix UnicodeDecodeError when reading file",
        "test_name": "test_read_config",
        "error_type": "UnicodeDecodeError",
        "file": "io/reader.py",
        "func_name": "read_config",
        "line": 12,
        "expected": "parsed config dict",
        "actual": "UnicodeDecodeError: 'charmap' codec can't decode byte",
        "root_cause": "File opened without encoding='utf-8' on Windows",
        "old_line": "with open(path, 'r') as f:",
        "new_line": "with open(path, 'r', encoding='utf-8') as f:",
        "stack_trace": "UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d\n  File 'io/reader.py', line 13",
    },
    {
        "id": "mutation_bug",
        "task_desc": "Fix mutable default argument",
        "test_name": "test_append_items",
        "error_type": "AssertionError",
        "file": "utils/collections.py",
        "func_name": "append_items",
        "line": 7,
        "expected": "[1]",
        "actual": "[1, 1, 1, ...] (growing across calls)",
        "root_cause": "Mutable default argument list=[] is shared across calls",
        "old_line": "def append_items(item, target=[]):",
        "new_line": "def append_items(item, target=None):\n    if target is None:\n        target = []",
        "stack_trace": "AssertionError: [1, 1, 1] != [1]\n  second call to append_items(1) still has items from first call",
    },
    {
        "id": "phi_drift",
        "task_desc": "Fix phi-weight accumulation drift in tongue scoring",
        "test_name": "test_tongue_weights_fibonacci",
        "error_type": "AssertionError",
        "file": "src/langues_metric.py",
        "func_name": "compute_tongue_weights",
        "line": 94,
        "expected": "phi^(n+2) == phi^(n+1) + phi^n",
        "actual": "Fibonacci recurrence fails after 1000 iterations due to float accumulation",
        "root_cause": "Weights computed incrementally (w[i] = w[i-1] + w[i-2]) instead of from phi^n directly",
        "old_line": "weights[i] = weights[i-1] + weights[i-2]",
        "new_line": "weights[i] = PHI ** i",
        "stack_trace": "AssertionError: 11.090169943740424 != 11.090169943749474\n  Fibonacci recurrence violated at n=5 after 1000 iterations",
    },
    {
        "id": "harmonic_wall",
        "task_desc": "Fix harmonic wall formula using wrong distance metric",
        "test_name": "test_harmonic_wall_bounded",
        "error_type": "AssertionError",
        "file": "src/harmonic/harmonicScaling.ts",
        "func_name": "harmonicWall",
        "line": 67,
        "expected": "H(d,pd) in (0, 1]",
        "actual": "H(d,pd) > 1.0 for small distances",
        "root_cause": "Formula uses Euclidean distance instead of hyperbolic distance d_H",
        "old_line": "const d = Math.sqrt(u.reduce((s,v,i) => s + (v-w[i])**2, 0));",
        "new_line": "const d = Math.acosh(1 + 2*normSqDiff/((1-normSqU)*(1-normSqW)));",
        "stack_trace": "AssertionError: Expected H <= 1.0, got 1.342\n  harmonicWall([0.1, 0.1], [0.11, 0.11]) returned 1.342",
    },
    {
        "id": "poincare_boundary",
        "task_desc": "Fix Poincare ball boundary violation",
        "test_name": "test_poincare_embedding_norm",
        "error_type": "ValueError",
        "file": "src/harmonic/hyperbolic.py",
        "func_name": "poincare_embed",
        "line": 31,
        "expected": "||x|| < 1.0 (inside ball)",
        "actual": "||x|| = 1.0003 (outside ball)",
        "root_cause": "No clamping after exponential map — numerical error pushes point outside ball",
        "old_line": "return origin + direction * tanh_factor",
        "new_line": "result = origin + direction * tanh_factor\nreturn result * min(1.0, 0.9999 / max(np.linalg.norm(result), 1e-10))",
        "stack_trace": "ValueError: Point outside Poincare ball: norm=1.0003\n  at poincare_embed, line 32",
    },
    {
        "id": "sacred_tongue_tokenizer",
        "task_desc": "Fix Sacred Tongue tokenizer returning wrong tongue for section",
        "test_name": "test_section_tongue_mapping",
        "error_type": "AssertionError",
        "file": "src/crypto/sacred_tongues.py",
        "func_name": "section_to_tongue",
        "line": 156,
        "expected": "Umbroth for 'redact' section",
        "actual": "Kor'aelin (default fallback)",
        "root_cause": "SECTION_TONGUES dict uses 'redacted' but input is 'redact'",
        "old_line": "'redacted': 'UM',",
        "new_line": "'redact': 'UM',",
        "stack_trace": "AssertionError: 'KO' != 'UM'\n  section_to_tongue('redact') returned 'KO' instead of 'UM'",
    },
]

# ---------------------------------------------------------------------------
# Trajectory patterns — different failure/retry paths
# ---------------------------------------------------------------------------
TRAJECTORY_PATTERNS = [
    # ===== LINEAR (original, kept for baseline) =====
    # Happy path: analyze -> attempt -> verify -> success (1 attempt)
    ["analyze_task", "attempt_fix", "run_tests", "success"],
    # Single retry
    ["analyze_task", "read_context", "attempt_fix", "run_tests", "diagnose_error", "attempt_fix", "run_tests", "success"],
    # Context-first
    ["read_context", "analyze_task", "check_imports", "attempt_fix", "run_tests", "success"],
    # Deep diagnosis
    [
        "analyze_task", "attempt_fix", "run_tests", "diagnose_error",
        "read_context", "check_imports", "attempt_fix", "run_tests", "success",
    ],
    # Multi-failure: 3 attempts
    [
        "analyze_task", "attempt_fix", "run_tests", "diagnose_error",
        "attempt_fix", "run_tests", "diagnose_error", "read_context",
        "attempt_fix", "run_tests", "success",
    ],
    # ===== CYCLIC (loop back from success to next task) =====
    # Fix-then-refactor cycle: fix bug, then loop back to analyze for regression
    [
        "analyze_task", "attempt_fix", "run_tests", "success",
        "analyze_task", "read_context", "check_imports", "attempt_fix", "run_tests", "success",
    ],
    # Diagnosis spiral: fail -> diagnose -> fix -> succeed -> re-analyze from new context
    [
        "analyze_task", "attempt_fix", "run_tests", "diagnose_error",
        "read_context", "attempt_fix", "run_tests", "success",
        "analyze_task", "attempt_fix", "run_tests", "success",
    ],
    # Triple loop: three bugs in sequence, each cycle starts from success -> analyze
    [
        "analyze_task", "attempt_fix", "run_tests", "success",
        "read_context", "analyze_task", "attempt_fix", "run_tests", "success",
        "analyze_task", "check_imports", "attempt_fix", "run_tests", "success",
    ],
    # ===== HYDRA DUAL-HEAD PATTERNS =====
    # HYDRA happy path: planner plans, coder codes, consensus gates, verify
    [
        "hydra_plan", "hydra_code", "hydra_consensus", "run_tests", "success",
    ],
    # HYDRA with retry: plan -> code -> fail -> planner re-assesses -> coder retries
    [
        "hydra_plan", "hydra_code", "hydra_consensus", "run_tests",
        "diagnose_error", "hydra_plan", "hydra_code", "hydra_consensus",
        "run_tests", "success",
    ],
    # HYDRA deep: full context gathering before dual-head deliberation
    [
        "read_context", "analyze_task", "hydra_plan", "hydra_code",
        "hydra_consensus", "run_tests", "success",
    ],
    # HYDRA cyclic: two bugs, dual-head on each, looping
    [
        "hydra_plan", "hydra_code", "hydra_consensus", "run_tests", "success",
        "analyze_task", "hydra_plan", "hydra_code", "hydra_consensus",
        "run_tests", "success",
    ],
    # HYDRA escalation: consensus ESCALATES, planner gathers more context, retry
    [
        "hydra_plan", "hydra_code", "hydra_consensus",
        "read_context", "check_imports",
        "hydra_plan", "hydra_code", "hydra_consensus",
        "run_tests", "success",
    ],
    # HYDRA multi-failure cycle: 3 attempts with dual-head deliberation each time
    [
        "hydra_plan", "hydra_code", "hydra_consensus", "run_tests",
        "diagnose_error", "hydra_plan", "hydra_code", "run_tests",
        "diagnose_error", "read_context", "hydra_plan", "hydra_code",
        "hydra_consensus", "run_tests", "success",
    ],
]


# ---------------------------------------------------------------------------
# OperatorPivotEngine — generates measured multi-step trajectories
# ---------------------------------------------------------------------------
class OperatorPivotEngine:
    """Generates operator trajectories with pivot scoring at every step."""

    def __init__(self):
        self.sft_pairs: List[Dict] = []
        self.dpo_pairs: List[Dict] = []
        self.visit_count: Dict[str, int] = defaultdict(int)

    def score_pivot(self, from_topic: OperatorTopic, to_topic: OperatorTopic) -> PivotScore:
        """Measure pivot quality between two operator steps."""
        # Relevance: is this a valid transition?
        relevance = 1.0 if to_topic.id in from_topic.connections else 0.3

        # Growth: does the step go deeper or change tongue?
        depth_delta = to_topic.depth - from_topic.depth
        tongue_change = 1.0 if from_topic.tongue != to_topic.tongue else 0.3
        growth = min(1.0, 0.3 + 0.3 * max(0, depth_delta) + 0.4 * tongue_change)

        # Novelty: have we visited this step type before?
        visits = self.visit_count[to_topic.id]
        novelty = max(0.0, 1.0 - 0.25 * visits)

        # Coherence: does this transition make sense in a coding trajectory?
        coherence = 0.9 if to_topic.id in from_topic.connections else 0.4
        # Same tongue = same-domain continuity bonus
        if from_topic.tongue == to_topic.tongue:
            coherence = min(1.0, coherence + 0.1)

        return PivotScore(
            relevance=round(relevance, 3),
            growth=round(growth, 3),
            novelty=round(novelty, 3),
            coherence=round(coherence, 3),
        )

    def fill_template(self, template: str, bug: Dict[str, Any]) -> str:
        """Fill a template string with bug-specific values."""
        result = template
        for key, value in bug.items():
            result = result.replace("{" + key + "}", str(value))
        # Clean up any unfilled placeholders with reasonable defaults
        import re

        result = re.sub(r"\{[a-z_]+\}", "...", result)
        return result

    def generate_trajectory(self, bug: Dict[str, Any], pattern: List[str]) -> Dict[str, Any]:
        """Generate a single multi-step trajectory through the pivot graph."""
        self.visit_count.clear()
        steps: List[Dict] = []
        pivot_scores: List[PivotScore] = []
        attempt_count = 0
        tongues_visited = set()

        for step_i, topic_id in enumerate(pattern):
            topic = OPERATOR_TOPICS[topic_id]
            self.visit_count[topic_id] += 1
            tongues_visited.add(topic.tongue)

            if topic.step_type == "attempt":
                attempt_count += 1

            # Pick templates
            q_idx = step_i % len(topic.instruction_templates)
            r_idx = step_i % len(topic.response_templates)

            instruction = self.fill_template(topic.instruction_templates[q_idx], bug)
            response = self.fill_template(topic.response_templates[r_idx], bug)

            # For test verification steps, inject pass/fail based on position
            if topic_id == "run_tests" and step_i < len(pattern) - 2:
                # Not the last test run — this one fails
                response = self.fill_template(
                    "FAIL: {test_name} still fails.\n  Expected: {expected}\n  Got: {actual}\n  The patch did not fully resolve the issue.",
                    bug,
                )
            elif topic_id == "run_tests" and step_i >= len(pattern) - 2:
                # Last test run — this one passes
                response = self.fill_template(
                    "PASS: {test_name} now succeeds. All related tests pass. Patch is clean.", bug
                )

            # Score pivot from previous step
            if step_i > 0:
                prev_topic = OPERATOR_TOPICS[pattern[step_i - 1]]
                score = self.score_pivot(prev_topic, topic)
                pivot_scores.append(score)
            else:
                score = None

            # Build SFT pair
            sft = {
                "instruction": instruction,
                "response": response,
                "metadata": {
                    "tongue": topic.tongue,
                    "step_type": topic.step_type,
                    "step_index": step_i,
                    "topic": topic.name,
                    "bug_id": bug["id"],
                    "attempt": attempt_count,
                    "trajectory_length": len(pattern),
                    "pivot_quality": round(score.quality, 4) if score else None,
                    "pivot_state": ("good" if score.is_good else "weak") if score else "start",
                    "grounding": 1.0,
                    "category": "operator_trajectory",
                },
            }
            self.sft_pairs.append(sft)
            steps.append(sft)

            # Generate DPO pairs for attempt/diagnose steps
            if topic.bad_response_templates and topic.step_type in ("attempt", "diagnose", "analyze"):
                bad_idx = step_i % len(topic.bad_response_templates)
                bad_response = topic.bad_response_templates[bad_idx]
                dpo = {
                    "prompt": instruction,
                    "chosen": response,
                    "rejected": bad_response,
                    "metadata": {
                        "tongue": topic.tongue,
                        "step_type": topic.step_type,
                        "bug_id": bug["id"],
                        "category": "operator_trajectory_dpo",
                    },
                }
                self.dpo_pairs.append(dpo)

        # Compute trajectory summary
        avg_quality = sum(s.quality for s in pivot_scores) / max(1, len(pivot_scores))
        trajectory_path = " -> ".join(pattern)

        return {
            "bug_id": bug["id"],
            "task_desc": bug["task_desc"],
            "trajectory": trajectory_path,
            "steps": len(steps),
            "attempts": attempt_count,
            "avg_pivot_quality": round(avg_quality, 4),
            "tongues_visited": sorted(tongues_visited),
            "sft_count": len(steps),
            "dpo_count": sum(1 for s in steps if OPERATOR_TOPICS[pattern[steps.index(s)]].bad_response_templates)
            if steps
            else 0,
        }

    def _is_hydra_pattern(self, pattern: List[str]) -> bool:
        """Check if trajectory uses HYDRA dual-head steps."""
        return any(t.startswith("hydra_") for t in pattern)

    def _is_cyclic_pattern(self, pattern: List[str]) -> bool:
        """Check if trajectory loops back (success appears before the end)."""
        success_positions = [i for i, t in enumerate(pattern) if t == "success"]
        return len(success_positions) > 1

    def _count_cycles(self, pattern: List[str]) -> int:
        """Count how many cycles (success points) in a pattern."""
        return sum(1 for t in pattern if t == "success")

    def _find_last_test_before_success(self, pattern: List[str], success_idx: int) -> int:
        """Find the last run_tests step before a given success step."""
        for i in range(success_idx - 1, -1, -1):
            if pattern[i] == "run_tests":
                return i
        return -1

    def generate_multi_turn_sft(self, bug: Dict[str, Any], pattern: List[str]) -> Dict[str, Any]:
        """Generate a single multi-turn SFT record (messages format) for the full trajectory."""
        messages = []
        is_hydra = self._is_hydra_pattern(pattern)
        is_cyclic = self._is_cyclic_pattern(pattern)
        n_cycles = self._count_cycles(pattern)

        # System prompt with tongue context + HYDRA mode if applicable
        tongue_weights = {
            "KO": 1.0,
            "AV": round(PHI, 4),
            "RU": round(PHI**2, 4),
            "CA": round(PHI**3, 4),
            "UM": round(PHI**4, 4),
            "DR": round(PHI**5, 4),
        }
        tongue_str = " ".join(f"{k}={v}" for k, v in tongue_weights.items())

        mode = "hydra_dual_head" if is_hydra else "operator"
        cycle_tag = f" [CYCLIC: {n_cycles} cycles]" if is_cyclic else ""

        system_content = (
            f"[TONGUES: {tongue_str}]\n"
            f"[MODE: {mode}]{cycle_tag}\n"
            f"[TASK: {bug['task_desc']}]\n"
        )

        if is_hydra:
            system_content += (
                "You coordinate two HYDRA heads via Switchboard:\n"
                f"  Head-Alpha (Planner/KO): {HYDRA_HEADS['planner']['system_prompt']}\n"
                f"  Head-Beta (Coder/CA): {HYDRA_HEADS['coder']['system_prompt']}\n"
                "Byzantine consensus required before applying patches. "
                "Quorum: 2/2 heads must ALLOW. Escalation re-routes to context gathering.\n"
            )
        else:
            system_content += (
                "You are an autonomous coding agent. Analyze errors, generate minimal patches, "
                "verify fixes, and iterate on failures. Output structured decisions."
            )

        if is_cyclic:
            system_content += (
                f"\nThis trajectory contains {n_cycles} fix cycles. "
                "After each success, loop back to analyze the next issue. "
                "Maintain context across cycles — each fix builds on the previous."
            )

        messages.append({"role": "system", "content": system_content})

        # Find which run_tests steps should PASS (last one before each success)
        passing_test_indices = set()
        for i, t in enumerate(pattern):
            if t == "success":
                last_test = self._find_last_test_before_success(pattern, i)
                if last_test >= 0:
                    passing_test_indices.add(last_test)

        attempt_count = 0
        cycle_count = 0
        for step_i, topic_id in enumerate(pattern):
            topic = OPERATOR_TOPICS[topic_id]
            if topic.step_type == "attempt":
                attempt_count += 1
            if topic_id == "success":
                cycle_count += 1

            q_idx = step_i % len(topic.instruction_templates)
            r_idx = step_i % len(topic.response_templates)

            instruction = self.fill_template(topic.instruction_templates[q_idx], bug)
            response = self.fill_template(topic.response_templates[r_idx], bug)

            # Override test results: PASS only for the last test before each success
            if topic_id == "run_tests":
                if step_i in passing_test_indices:
                    response = self.fill_template("PASS: {test_name} now succeeds. All tests green.", bug)
                else:
                    response = self.fill_template(
                        "FAIL: {test_name} still fails.\n  Expected: {expected}\n  Got: {actual}", bug
                    )
            elif topic_id == "success":
                cycle_note = f" (cycle {cycle_count}/{n_cycles})" if is_cyclic else ""
                response = self.fill_template(
                    f"Fix complete{cycle_note}:\n- Root cause: {{root_cause}}\n- Patch: 1 line in {{file}}\n"
                    f"- Tests: all pass\n- Attempts: {attempt_count}\n"
                    f"- Trajectory: {' -> '.join(pattern[:step_i + 1])}",
                    bug,
                )

            # Tag with head callsign for HYDRA steps
            head_tag = ""
            if topic_id == "hydra_plan":
                head_tag = f" [via {HYDRA_HEADS['planner']['callsign']}]"
            elif topic_id == "hydra_code":
                head_tag = f" [via {HYDRA_HEADS['coder']['callsign']}]"
            elif topic_id == "hydra_consensus":
                head_tag = " [CONSENSUS GATE]"

            messages.append(
                {"role": "user", "content": f"[{topic.tongue}:{topic.step_type}]{head_tag} {instruction}"}
            )
            messages.append({"role": "assistant", "content": response})

        tongues_in_traj = sorted(set(OPERATOR_TOPICS[t].tongue for t in pattern))
        return {
            "messages": messages,
            "metadata": {
                "bug_id": bug["id"],
                "category": "operator_trajectory_multiturn",
                "trajectory": " -> ".join(pattern),
                "attempts": attempt_count,
                "cycles": n_cycles,
                "is_hydra": is_hydra,
                "is_cyclic": is_cyclic,
                "tongues": tongues_in_traj,
                "grounding": 1.0,
            },
        }


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------
def generate_all(output_dir: str = "training-data/sft") -> Dict[str, Any]:
    """Generate all operator pivot trajectories — linear, cyclic, and HYDRA dual-head."""
    engine = OperatorPivotEngine()
    multi_turn_records = []

    # Classify patterns for stats
    linear_patterns = [p for p in TRAJECTORY_PATTERNS if not engine._is_hydra_pattern(p) and not engine._is_cyclic_pattern(p)]
    cyclic_patterns = [p for p in TRAJECTORY_PATTERNS if engine._is_cyclic_pattern(p) and not engine._is_hydra_pattern(p)]
    hydra_patterns = [p for p in TRAJECTORY_PATTERNS if engine._is_hydra_pattern(p)]

    # Generate individual step SFT + DPO pairs
    for bug in BUG_TEMPLATES:
        for pattern in TRAJECTORY_PATTERNS:
            engine.generate_trajectory(bug, pattern)

    # Generate multi-turn conversation records
    for bug in BUG_TEMPLATES:
        for pattern in TRAJECTORY_PATTERNS:
            record = engine.generate_multi_turn_sft(bug, pattern)
            multi_turn_records.append(record)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Write individual step SFT pairs
    sft_path = out_path / "operator_pivot_sft.jsonl"
    with open(sft_path, "w", encoding="utf-8") as f:
        for pair in engine.sft_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    # Write DPO pairs
    dpo_path = out_path / "operator_pivot_dpo.jsonl"
    with open(dpo_path, "w", encoding="utf-8") as f:
        for pair in engine.dpo_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    # Write multi-turn trajectories
    mt_path = out_path / "operator_pivot_multiturn.jsonl"
    with open(mt_path, "w", encoding="utf-8") as f:
        for record in multi_turn_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    stats = {
        "sft_pairs": len(engine.sft_pairs),
        "dpo_pairs": len(engine.dpo_pairs),
        "multi_turn_records": len(multi_turn_records),
        "bugs": len(BUG_TEMPLATES),
        "trajectory_patterns": len(TRAJECTORY_PATTERNS),
        "linear_patterns": len(linear_patterns),
        "cyclic_patterns": len(cyclic_patterns),
        "hydra_patterns": len(hydra_patterns),
        "total_combinations": len(BUG_TEMPLATES) * len(TRAJECTORY_PATTERNS),
    }

    return stats


if __name__ == "__main__":
    stats = generate_all()
    print("Operator Pivot Trajectories Generated:")
    print(f"  SFT pairs (individual steps): {stats['sft_pairs']}")
    print(f"  DPO pairs (good vs bad):      {stats['dpo_pairs']}")
    print(f"  Multi-turn trajectories:       {stats['multi_turn_records']}")
    print(f"  Bug templates:                 {stats['bugs']}")
    print(f"  Trajectory patterns:           {stats['trajectory_patterns']}")
    print(f"    Linear:                      {stats['linear_patterns']}")
    print(f"    Cyclic (looping):            {stats['cyclic_patterns']}")
    print(f"    HYDRA dual-head:             {stats['hydra_patterns']}")
    print(f"  Total combinations:            {stats['total_combinations']}")

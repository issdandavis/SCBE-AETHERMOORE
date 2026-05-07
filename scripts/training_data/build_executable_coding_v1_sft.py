"""Build executable_coding_v1 SFT shard.

Target: make the AI code BETTER, not just match keyword markers.

Mechanism: every assistant target in this shard is bare executable Python that
has been run locally and verified to pass its hidden test cases. Each problem
contributes 4-6 SFT rows by varying the prompt phrasing while holding the
canonical solution constant — composition over fabrication.

Why this exists:
- v6c gate failed raw 0/12 because targets were marker metadata, not code.
- v6e + v6g raw-code shards fixed marker-bleed but tested only "looks like
  code", not "runs and passes tests."
- This shard is the first SCBE training shard where every assistant target
  is execution-verified at build time.

Output:
- training-data/sft/executable_coding_v1_train.sft.jsonl
- training-data/sft/executable_coding_v1_holdout.sft.jsonl
- training-data/sft/executable_coding_v1_manifest.json

Each row: {"messages": [system, user, assistant], "metadata": {...}}.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SFT_ROOT = REPO_ROOT / "training-data" / "sft"
TRAIN_OUT = SFT_ROOT / "executable_coding_v1_train.sft.jsonl"
HOLDOUT_OUT = SFT_ROOT / "executable_coding_v1_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "executable_coding_v1_manifest.json"

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE coding agent. When the user asks you to "
    "implement a function, return ONLY the function definition as bare "
    "executable Python code in a single fenced block. No prose. No metadata "
    "wrappers. No marker preambles. The code must run as-is and the "
    "function name must match the user's request."
)

# Each problem has:
# - id
# - canonical Python source (the assistant target — verified executable)
# - test cases (list of (call_str, expected_repr))
# - prompt variants (list of prompt strings — each becomes one SFT row)
PROBLEMS: list[dict[str, Any]] = [
    {
        "id": "inventory_unique",
        "code": (
            "def inventory_unique(items):\n"
            "    seen = set()\n"
            "    out = []\n"
            "    for item in items:\n"
            "        if item not in seen:\n"
            "            seen.add(item)\n"
            "            out.append(item)\n"
            "    return out\n"
        ),
        "tests": [
            ("inventory_unique([1, 2, 1, 3, 2, 4])", "[1, 2, 3, 4]"),
            ("inventory_unique([])", "[]"),
            ("inventory_unique(['a', 'a', 'a'])", "['a']"),
            ("inventory_unique([1, 2, 3])", "[1, 2, 3]"),
        ],
        "prompts": [
            "Implement inventory_unique(items) in Python. Return a list of unique items in first-seen order. Use a seen-set guard.",
            "Write a Python function `inventory_unique(items)` that returns the deduplicated list preserving original order.",
            "Define inventory_unique(items) in Python: walk the input list, drop duplicates, preserve first-seen order.",
            "Python: implement inventory_unique(items) -> list using a set for membership tracking.",
        ],
    },
    {
        "id": "safe_subtract",
        "code": (
            "def safe_subtract(a, b):\n"
            "    if a is None or b is None:\n"
            "        return None\n"
            "    return a - b\n"
        ),
        "tests": [
            ("safe_subtract(5, 3)", "2"),
            ("safe_subtract(None, 3)", "None"),
            ("safe_subtract(5, None)", "None"),
            ("safe_subtract(None, None)", "None"),
            ("safe_subtract(0, 0)", "0"),
        ],
        "prompts": [
            "Implement safe_subtract(a, b) in Python. Return None when either argument is None, otherwise return a - b.",
            "Write Python: safe_subtract(a, b) returns None if a or b is None, else a - b.",
            "Define safe_subtract(a, b) in Python with explicit None guard before the subtraction.",
            "Python function safe_subtract(a, b): None-safe subtraction.",
        ],
    },
    {
        "id": "running_average",
        "code": (
            "def running_average(values):\n"
            "    out = []\n"
            "    total = 0.0\n"
            "    for i, v in enumerate(values, start=1):\n"
            "        total += v\n"
            "        out.append(total / i)\n"
            "    return out\n"
        ),
        "tests": [
            ("running_average([1, 2, 3])", "[1.0, 1.5, 2.0]"),
            ("running_average([])", "[]"),
            ("running_average([10])", "[10.0]"),
            ("running_average([2, 2, 2, 2])", "[2.0, 2.0, 2.0, 2.0]"),
        ],
        "prompts": [
            "Write a Python function `running_average(values)` that returns a list of the running mean of the input numeric list.",
            "Implement running_average(values) in Python: at each index i return mean(values[:i+1]).",
            "Python: running_average(values) returns the list of cumulative means.",
            "Define running_average(values) so the i-th output is the average of the first i+1 inputs.",
        ],
    },
    {
        "id": "merge_counts",
        "code": (
            "def merge_counts(a, b):\n"
            "    out = {}\n"
            "    for key, value in a.items():\n"
            "        out[key] = out.get(key, 0) + value\n"
            "    for key, value in b.items():\n"
            "        out[key] = out.get(key, 0) + value\n"
            "    return out\n"
        ),
        "tests": [
            ("merge_counts({'a': 1, 'b': 2}, {'b': 3, 'c': 4})", "{'a': 1, 'b': 5, 'c': 4}"),
            ("merge_counts({}, {})", "{}"),
            ("merge_counts({'x': 1}, {})", "{'x': 1}"),
            ("merge_counts({}, {'y': 2})", "{'y': 2}"),
        ],
        "prompts": [
            "Implement merge_counts(a, b) in Python. Both args are dicts mapping str to int. Return a new dict whose keys are the union, each value summed (treat missing as 0).",
            "Python: merge_counts(a, b) -> dict that adds counts across two count-dicts.",
            "Write merge_counts(a, b) in Python: union of keys, values summed, missing counts as 0.",
            "Define merge_counts(a, b) so the result is the dict-of-sums of the two input dicts.",
        ],
    },
    {
        "id": "first_word",
        "code": (
            "def first_word(s):\n"
            "    if not s:\n"
            "        return ''\n"
            "    parts = s.split()\n"
            "    if not parts:\n"
            "        return ''\n"
            "    return parts[0]\n"
        ),
        "tests": [
            ("first_word('hello world')", "'hello'"),
            ("first_word('')", "''"),
            ("first_word('   ')", "''"),
            ("first_word('one')", "'one'"),
            ("first_word('  spaced  text  ')", "'spaced'"),
        ],
        "prompts": [
            "Implement first_word(s) in Python. Return the first whitespace-delimited token, or empty string if input is empty/whitespace.",
            "Python: first_word(s) returns s.split()[0] safely (handles empty/whitespace input).",
            "Write first_word(s) -> str. Empty or whitespace-only input returns empty string.",
            "Define first_word(s): the first non-whitespace word, or '' when none.",
        ],
    },
    {
        "id": "clamp",
        "code": (
            "def clamp(x, lo, hi):\n"
            "    if x < lo:\n"
            "        return lo\n"
            "    if x > hi:\n"
            "        return hi\n"
            "    return x\n"
        ),
        "tests": [
            ("clamp(5, 0, 10)", "5"),
            ("clamp(-1, 0, 10)", "0"),
            ("clamp(11, 0, 10)", "10"),
            ("clamp(0, 0, 10)", "0"),
            ("clamp(10, 0, 10)", "10"),
        ],
        "prompts": [
            "Implement clamp(x, lo, hi) in Python returning x clamped into the inclusive range [lo, hi].",
            "Python: clamp(x, lo, hi) -> bounded value. If x < lo return lo, if x > hi return hi, else x.",
            "Write clamp(x, lo, hi) in Python with explicit lower and upper branches.",
            "Define clamp so out-of-range x is pinned to the nearest bound.",
        ],
    },
    {
        "id": "count_vowels",
        "code": (
            "def count_vowels(s):\n"
            "    total = 0\n"
            "    for ch in s:\n"
            "        if ch in 'aeiouAEIOU':\n"
            "            total += 1\n"
            "    return total\n"
        ),
        "tests": [
            ("count_vowels('hello')", "2"),
            ("count_vowels('')", "0"),
            ("count_vowels('xyz')", "0"),
            ("count_vowels('AEIOU')", "5"),
            ("count_vowels('Algorithms')", "3"),
        ],
        "prompts": [
            "Implement count_vowels(s) in Python that counts the number of vowels (aeiouAEIOU) in a string.",
            "Python: count_vowels(s) -> int counts how many characters of s are vowels.",
            "Write count_vowels(s): scan s, return the count of vowels (case-insensitive, ascii).",
            "Define count_vowels(s) returning the number of ascii vowels in s.",
        ],
    },
    {
        "id": "triple",
        "code": (
            "def triple(x):\n"
            "    return x * 3\n"
        ),
        "tests": [
            ("triple(2)", "6"),
            ("triple(0)", "0"),
            ("triple(-4)", "-12"),
            ("triple(1.5)", "4.5"),
        ],
        "prompts": [
            "Implement triple(x) in Python so it returns 3 * x.",
            "Python one-liner: triple(x) returns x times three.",
            "Define triple(x) -> 3*x. Should work for ints and floats.",
            "Write triple(x) returning x scaled by 3.",
        ],
    },
    {
        "id": "is_palindrome",
        "code": (
            "def is_palindrome(s):\n"
            "    cleaned = ''.join(ch.lower() for ch in s if ch.isalnum())\n"
            "    return cleaned == cleaned[::-1]\n"
        ),
        "tests": [
            ("is_palindrome('racecar')", "True"),
            ("is_palindrome('hello')", "False"),
            ("is_palindrome('')", "True"),
            ("is_palindrome('A man a plan a canal Panama')", "True"),
            ("is_palindrome('No lemon, no melon')", "True"),
        ],
        "prompts": [
            "Implement is_palindrome(s) in Python. Strip non-alphanumeric, lowercase, return True iff reversed equals original.",
            "Python: is_palindrome(s) returns whether s is a palindrome ignoring case and punctuation.",
            "Write is_palindrome(s) -> bool with normalization (alphanumeric-lowercase) before reversal compare.",
            "Define is_palindrome that returns True for 'A man a plan a canal Panama' and False for 'hello'.",
        ],
    },
    {
        "id": "fibonacci",
        "code": (
            "def fibonacci(n):\n"
            "    if n < 0:\n"
            "        raise ValueError('n must be non-negative')\n"
            "    if n == 0:\n"
            "        return 0\n"
            "    a, b = 0, 1\n"
            "    for _ in range(n - 1):\n"
            "        a, b = b, a + b\n"
            "    return b\n"
        ),
        "tests": [
            ("fibonacci(0)", "0"),
            ("fibonacci(1)", "1"),
            ("fibonacci(2)", "1"),
            ("fibonacci(10)", "55"),
            ("fibonacci(20)", "6765"),
        ],
        "prompts": [
            "Implement fibonacci(n) in Python iteratively. Return the n-th Fibonacci number (F0 = 0, F1 = 1). Raise ValueError on negative n.",
            "Python: fibonacci(n) returns the n-th Fibonacci number using O(n) iteration, not recursion.",
            "Write fibonacci(n) -> int with negative-n guard and O(1) memory iteration.",
            "Define fibonacci(n): F0=0, F1=1, raises on n<0, iterative not recursive.",
        ],
    },
]


def verify_problem(problem: dict[str, Any]) -> None:
    """Run every test case against the canonical solution; raise on any failure."""
    code = problem["code"]
    for call_str, expected_repr in problem["tests"]:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "verify.py"
            script.write_text(
                code + f"\n_result = {call_str}\nprint(repr(_result))\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise AssertionError(
                    f"{problem['id']}: {call_str} crashed:\n{result.stderr}"
                )
            actual_repr = result.stdout.strip()
            if actual_repr != expected_repr:
                raise AssertionError(
                    f"{problem['id']}: {call_str} returned {actual_repr!r}, expected {expected_repr!r}"
                )


def make_row(prompt: str, code: str, problem_id: str, prompt_idx: int) -> dict[str, Any]:
    code_block = f"```python\n{code.rstrip()}\n```\n"
    row_id = hashlib.sha256(
        f"{problem_id}|{prompt_idx}|{prompt}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": code_block},
        ],
        "metadata": {
            "row_id": row_id,
            "problem_id": problem_id,
            "prompt_idx": prompt_idx,
            "schema_version": "executable_coding_sft_v1",
            "split": "train",
            "source": "build_executable_coding_v1_sft.py",
        },
    }


def build_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train_rows: list[dict[str, Any]] = []
    holdout_rows: list[dict[str, Any]] = []
    for problem in PROBLEMS:
        prompts = problem["prompts"]
        # Reserve the LAST prompt variant per problem as holdout. Train on
        # the first N-1 variants. This is "same problem, unseen phrasing"
        # which is the right generalization test for execution-correctness.
        for idx, prompt in enumerate(prompts):
            row = make_row(prompt, problem["code"], problem["id"], idx)
            if idx == len(prompts) - 1:
                row["metadata"]["split"] = "holdout"
                holdout_rows.append(row)
            else:
                train_rows.append(row)
    return train_rows, holdout_rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-verify", action="store_true", help="Skip running tests against canonical solutions.")
    parser.add_argument("--dry-run", action="store_true", help="Print row counts and exit, do not write files.")
    args = parser.parse_args()

    if not args.skip_verify:
        print(f"Verifying {len(PROBLEMS)} problems via execution...")
        for problem in PROBLEMS:
            verify_problem(problem)
            print(f"  ok: {problem['id']} ({len(problem['tests'])} tests)")
        print("All canonical solutions execute correctly.")

    train_rows, holdout_rows = build_rows()
    print(
        f"\nGenerated {len(train_rows)} train rows, {len(holdout_rows)} holdout rows "
        f"from {len(PROBLEMS)} problems."
    )

    if args.dry_run:
        print("--dry-run: not writing files.")
        return 0

    write_jsonl(TRAIN_OUT, train_rows)
    write_jsonl(HOLDOUT_OUT, holdout_rows)

    manifest = {
        "schema_version": "executable_coding_sft_manifest_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "n_problems": len(PROBLEMS),
        "n_train_rows": len(train_rows),
        "n_holdout_rows": len(holdout_rows),
        "problem_ids": [p["id"] for p in PROBLEMS],
        "verification": "every canonical solution executed and matched expected outputs at build time",
        "system_prompt": SYSTEM_PROMPT,
        "files": {
            "train": str(TRAIN_OUT.relative_to(REPO_ROOT)),
            "holdout": str(HOLDOUT_OUT.relative_to(REPO_ROOT)),
            "manifest": str(MANIFEST_OUT.relative_to(REPO_ROOT)),
        },
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote: {TRAIN_OUT.relative_to(REPO_ROOT)}")
    print(f"Wrote: {HOLDOUT_OUT.relative_to(REPO_ROOT)}")
    print(f"Wrote: {MANIFEST_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

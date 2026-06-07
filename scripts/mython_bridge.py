"""
mython_bridge.py — plain-language → Python function grid dispatcher

Speak simply:
    python scripts/mython_bridge.py "compile add logging to main.py"
    python scripts/mython_bridge.py "scan this workspace"
    python scripts/mython_bridge.py "route analyze token costs"

Pipeline (steps separated by →):
    python scripts/mython_bridge.py "compile my intent → seal it → verify"

Flags:
    --json        Emit all results as a single JSON array (no box drawing, for
                  machine consumption from scbe.js).
    --matrix      Print a compact 2D ASCII grid (categories × operations).
    --passthrough <tool-name> [payload]
                  Look up tool in tools.json and run its command + args,
                  substituting {task} with the payload.

The GRID is the only source of truth — no LLM, pure keyword match.
Each cell maps trigger words to a subprocess command and result label.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import time
from typing import Any

# ── tools.json dynamic auto-rows ─────────────────────────────────────────────
# Loaded once at module level; used by _load_auto_rows() and passthrough mode.

_TOOLS_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "packages",
    "agent-bus",
    "tools.json",
)

_TOOLS_RAW: list[dict] = []
try:
    with open(_TOOLS_JSON_PATH, "r", encoding="utf-8") as _f:
        _raw = json.load(_f)
        if isinstance(_raw, list):
            _TOOLS_RAW = _raw
except Exception:
    pass  # file absent or malformed — auto-rows simply won't load


# ── Command grid ──────────────────────────────────────────────────────────────
# Each row: [category, operation, trigger_words, base_command, takes_input]
#   takes_input: True  → append the payload text as final arg
#                False → run command as-is (no payload appended)

GRID = [
    # category      operation       triggers                           command
    [
        "geoseal",
        "compile",
        ["compile", "plan", "intent"],
        ["python", "-m", "src.geoseal_cli", "compile", "--json"],
        True,
    ],
    [
        "geoseal",
        "seal",
        ["seal", "stamp", "sign"],
        ["python", "-m", "src.geoseal_cli", "seal"],
        True,
    ],
    [
        "geoseal",
        "verify",
        ["verify", "check", "validate"],
        ["python", "-m", "src.geoseal_cli", "verify"],
        True,
    ],
    [
        "geoseal",
        "explain-route",
        ["explain", "route", "why"],
        [
            "python",
            "-m",
            "src.geoseal_cli",
            "explain-route",
            "--content",
            "PAYLOAD",
            "--language",
            "python",
            "--source-name",
            "mython",
            "--json",
        ],
        True,
    ],
    [
        "governance",
        "scan",
        ["scan", "antivirus", "threat"],
        ["python", "scripts/scbe-system-cli.py", "--json", "antivirus"],
        False,
    ],
    [
        "governance",
        "route",
        ["route", "compass", "dispatch"],
        ["node", "packages/agent-bus/scripts/compass.cjs"],
        True,
    ],
    [
        "governance",
        "flow",
        ["flow", "multi-agent", "agents"],
        ["python", "scripts/scbe-system-cli.py", "--json", "flow", "--task"],
        True,
    ],
    [
        "tongues",
        "encode",
        ["tongue", "tongues", "encode", "KO", "AV", "RU", "CA", "UM", "DR"],
        ["python", "scripts/scbe-system-cli.py", "--json", "tongues"],
        True,
    ],
    [
        "research",
        "arxiv",
        ["arxiv", "paper", "papers", "preprint"],
        ["python", "scripts/research_api_bus.py", "--api", "arxiv", "--query"],
        True,
    ],
    [
        "research",
        "github",
        ["github", "repo", "repos"],
        ["python", "scripts/research_api_bus.py", "--api", "github_repos", "--query"],
        True,
    ],
    [
        "research",
        "hf-models",
        ["huggingface", "hf", "models", "model"],
        ["python", "scripts/research_api_bus.py", "--api", "hf_models", "--query"],
        True,
    ],
]


def _load_auto_rows() -> list[list]:
    """
    Build up to 20 auto-rows from tools.json for tools not already in GRID.
    Each auto-row routes through --passthrough so the real command in tools.json
    is what actually runs.
    Returns a list of GRID-compatible rows.
    """
    if not _TOOLS_RAW:
        return []
    existing_ops = {row[1] for row in GRID}
    auto_rows = []
    for tool in _TOOLS_RAW:
        if len(auto_rows) >= 20:
            break
        name = tool.get("name", "")
        desc = tool.get("description", "")
        if not name or name in existing_ops:
            continue
        category = name.split("-")[0]
        triggers = [name] + desc.lower().split()[:4]
        cmd = ["python", "scripts/mython_bridge.py", "--passthrough", name]
        auto_rows.append([category, name, triggers, cmd, True])
        existing_ops.add(name)
    return auto_rows


# Append auto-rows to GRID at module load time
GRID.extend(_load_auto_rows())


# ── Math layer (numeric triggers, like old trig lookup tables) ────────────────
#
# Old-school trig calculators used a fixed grid of known values and an iterative
# process (CORDIC) to fill in everything else.  Same idea here: the operation is
# the "column", the number is the "row", the math fills in the result.
# Numbers are valid keywords; if the input contains a number we extract it as
# the operand.  Higher layers can pipe these numeric results into semantic ops.

_DEG = math.pi / 180  # degree→radian factor

MATH_GRID: dict[str, tuple[list[str], Any]] = {
    # op_name: (trigger_words, function(x) → float)
    "sin": (["sin", "sine"], lambda x: math.sin(x * _DEG)),
    "cos": (["cos", "cosine"], lambda x: math.cos(x * _DEG)),
    "tan": (["tan", "tangent"], lambda x: math.tan(x * _DEG)),
    "asin": (
        ["asin", "arcsin", "arcsine", "inv sin"],
        lambda x: math.degrees(math.asin(x)),
    ),
    "acos": (
        ["acos", "arccos", "arccosine", "inv cos"],
        lambda x: math.degrees(math.acos(x)),
    ),
    "atan": (
        ["atan", "arctan", "arctangent", "inv tan"],
        lambda x: math.degrees(math.atan(x)),
    ),
    "sqrt": (["sqrt", "root", "square root"], lambda x: math.sqrt(x)),
    "log": (["log", "log10", "log base 10"], lambda x: math.log10(x)),
    "ln": (["ln", "natural log", "loge"], lambda x: math.log(x)),
    "exp": (["exp", "e^", "euler"], lambda x: math.exp(x)),
    "pow2": (["squared", "^2", "power 2"], lambda x: x**2),
    "pow3": (["cubed", "^3", "power 3"], lambda x: x**3),
    "recip": (["recip", "inverse", "1/"], lambda x: 1 / x if x != 0 else float("inf")),
    "abs": (["abs", "absolute", "|x|"], lambda x: abs(x)),
    "phi_scale": (["phi", "golden", "φ"], lambda x: x * 1.6180339887),
    "hypot": (
        ["hypotenuse", "hypot", "distance"],
        lambda x: math.sqrt(x),
    ),  # one-arg: sqrt(x)
    "layer_h": (
        ["harmonic", "H(", "wall score"],
        lambda x: 1 / (1 + x),
    ),  # SCBE harmonic wall: 1/(1+x)
    "layer_ph": (
        ["poincare", "poincare dist", "hyperbolic"],
        lambda x: math.acosh(1 + 2 * x**2 / max(1 - x**2, 1e-10)),
    ),
}


def _extract_number(text: str) -> float | None:
    """Pull the first number (int or float) out of a text string."""
    m = re.search(r"-?\d+\.?\d*", text)
    return float(m.group()) if m else None


def _score_math(text_lower: str, triggers: list[str]) -> float:
    """Score math grid row — same position-weighted approach as semantic grid."""
    n = len(text_lower)
    count = 0
    earliest = n
    for t in triggers:
        idx = text_lower.find(t.lower())
        if idx != -1:
            count += 1
            if idx < earliest:
                earliest = idx
    if count == 0:
        return 0.0
    return count + (n - earliest) / (n + 1) * 0.9


def dispatch_math(text: str) -> dict | None:
    """
    Try to match text against the math grid.
    Returns a result dict if matched, None if no math op found.
    """
    t = text.lower()
    best_score = 0.0
    best_op = None
    for op, (triggers, _) in MATH_GRID.items():
        s = _score_math(t, triggers)
        if s > best_score:
            best_score = s
            best_op = op

    if not best_op or best_score < 0.5:
        return None

    fn = MATH_GRID[best_op][1]
    x = _extract_number(text)
    if x is None:
        return {
            "category": "math",
            "operation": best_op,
            "ok": False,
            "confidence": 0.6,
            "data": {"error": f"No number found in: {text!r}"},
            "elapsed": 0.0,
            "payload": text,
        }
    t0 = time.monotonic()
    try:
        result = fn(x)
        # Guard against float('inf') which is invalid JSON
        result_safe = result if math.isfinite(result) else str(result)
        return {
            "category": "math",
            "operation": best_op,
            "ok": True,
            "confidence": 1.0,
            "data": {
                "x": x,
                "result": round(result, 8) if math.isfinite(result) else result_safe,
                "op": best_op,
            },
            "elapsed": round(time.monotonic() - t0, 6),
            "payload": text,
            "_numeric_result": result,  # pass-through for pipeline chaining
        }
    except Exception as e:
        return {
            "category": "math",
            "operation": best_op,
            "ok": False,
            "confidence": 0.6,
            "data": {"error": str(e), "x": x},
            "elapsed": 0.0,
            "payload": text,
        }


# ── Grid display ──────────────────────────────────────────────────────────────

MAX_VALUE_WIDTH = 70  # max characters for the value column


def _wrap_value(s: str, width: int) -> list[str]:
    """Split a string into lines of at most `width` chars."""
    lines = []
    while len(s) > width:
        # prefer to break at a space
        cut = s.rfind(" ", 0, width)
        if cut < width // 2:
            cut = width
        lines.append(s[:cut])
        s = s[cut:].lstrip()
    if s:
        lines.append(s)
    return lines or [""]


def _box(rows: list[tuple[str, Any]], title: str = "") -> str:
    """Render a two-column table with box-drawing characters."""
    if not rows:
        return ""
    col1 = min(max(len(str(k)) for k, _ in rows), 14)
    col1 = max(col1, 8)
    col2 = MAX_VALUE_WIDTH
    if title:
        col2 = max(col2, len(title))
    w = col1 + col2 + 7
    sep = f"├{'─' * (col1 + 2)}┼{'─' * (col2 + 2)}┤"
    top = f"╔{'═' * (w - 2)}╗"
    bot = f"╚{'═' * (w - 2)}╝"
    lines = [top]
    if title:
        lines.append(f"║ {title.ljust(w - 4)} ║")
        lines.append(f"╠{'═' * (col1 + 2)}╪{'═' * (col2 + 2)}╣")
    for i, (k, v) in enumerate(rows):
        value_lines = _wrap_value(str(v), col2)
        for j, vl in enumerate(value_lines):
            label = str(k).ljust(col1) if j == 0 else " " * col1
            lines.append(f"│ {label} │ {vl.ljust(col2)} │")
        if i < len(rows) - 1:
            lines.append(sep)
    lines.append(bot)
    return "\n".join(lines)


def print_matrix():
    """
    Print a compact 2D ASCII grid: categories (rows) × operation names (columns).
    Each operation is assigned a short numeric label; the legend lists the mapping.
    A ✓ marks where a cell exists; · marks where it doesn't.
    """
    # Collect ordered unique categories and operations
    grid_cells: set[tuple[str, str]] = set()
    categories_ordered: list[str] = []
    ops_ordered: list[str] = []

    for cat, op, *_ in GRID:
        grid_cells.add((cat, op))
        if cat not in categories_ordered:
            categories_ordered.append(cat)
        if op not in ops_ordered:
            ops_ordered.append(op)

    # Math layer — category "math"
    for op in MATH_GRID:
        grid_cells.add(("math", op))
        if "math" not in categories_ordered:
            categories_ordered.append("math")
        if op not in ops_ordered:
            ops_ordered.append(op)

    # Build short numeric column labels and legend
    op_labels = [str(i + 1) for i in range(len(ops_ordered))]
    legend_entries = list(zip(op_labels, ops_ordered))

    cat_width = max((len(c) for c in categories_ordered), default=8)
    cat_width = max(cat_width, 8)

    # Each column cell is 3 chars wide ("  1", " ✓ ", etc.)
    col_block = "  ".join(f"{lbl:>3}" for lbl in op_labels)
    header = f"{'Category'.ljust(cat_width)} │ {col_block}"

    title = "OPERATION MATRIX — mython bridge"
    total_w = max(len(header), len(title)) + 4
    total_w = max(total_w, 40)

    top = f"╔{'═' * (total_w - 2)}╗"
    bot = f"╚{'═' * (total_w - 2)}╝"
    inner_sep = f"╟{'─' * (total_w - 2)}╢"
    heavy_sep = f"╠{'═' * (total_w - 2)}╣"

    lines = [top]
    lines.append(f"║ {title.ljust(total_w - 4)} ║")
    lines.append(heavy_sep)
    lines.append(f"║ {header.ljust(total_w - 4)} ║")
    lines.append(inner_sep)

    for cat in categories_ordered:
        cells = "  ".join(
            f"{'✓':>3}" if (cat, ops_ordered[i]) in grid_cells else f"{'·':>3}"
            for i in range(len(ops_ordered))
        )
        row_str = f"{cat.ljust(cat_width)} │ {cells}"
        lines.append(f"║ {row_str.ljust(total_w - 4)} ║")

    lines.append(inner_sep)
    lines.append(f"║ {'Legend:'.ljust(total_w - 4)} ║")
    for lbl, op in legend_entries:
        entry = f"  {lbl:>3} = {op}"
        lines.append(f"║ {entry.ljust(total_w - 4)} ║")
    lines.append(bot)

    print("\n".join(lines))
    print()


def print_grid_index():
    """Show the full command grid so the user knows what's available."""
    rows: list[tuple[str, str]] = [("category · op", "trigger words")]
    for cat, op, triggers, *_ in GRID:
        rows.append((f"{cat} · {op}", ", ".join(triggers[:4])))
    rows.append(("──────────────", "── math layer ─────────────────────────"))
    for op, (triggers, _) in MATH_GRID.items():
        rows.append((f"math · {op}", ", ".join(triggers[:3])))
    print(_box(rows, "MYTHON BRIDGE — available commands"))
    print()
    print("Usage:")
    print('  python scripts/mython_bridge.py "compile add logging to main.py"')
    print('  python scripts/mython_bridge.py "sin 45"')
    print('  python scripts/mython_bridge.py "compile my goal → seal it"')
    print('  python scripts/mython_bridge.py "sin 45 → harmonic wall"   # layers')
    print('  python scripts/mython_bridge.py --json "scan this workspace"')
    print("  python scripts/mython_bridge.py --matrix")
    print(
        '  python scripts/mython_bridge.py --passthrough geoseal-compile "add logging"'
    )
    print()


# ── Dispatch ──────────────────────────────────────────────────────────────────


def _score(text_lower: str, triggers: list[str]) -> float:
    """
    Score a grid row against the input text.
    - Count of trigger matches (primary)
    - Bonus for earlier first-match position (earlier = better)
    """
    n = len(text_lower)
    count = 0
    earliest = n  # position of first match (lower is earlier)
    for t in triggers:
        idx = text_lower.find(t.lower())
        if idx != -1:
            count += 1
            if idx < earliest:
                earliest = idx
    if count == 0:
        return 0.0
    # Tie-break: add a small fraction for earlier position (max 0.9 bonus)
    position_bonus = (n - earliest) / (n + 1) * 0.9
    return count + position_bonus


def find_cell(text: str) -> tuple[str, str, list[str], bool, float] | None:
    """
    Match the highest-scoring grid row.
    Returns (category, operation, command, takes_input, score) or None.
    """
    best_score = 0.0
    best_cat = None
    best_op = None
    best_cmd = None
    best_takes = None
    t = text.lower()
    for cat, op, triggers, cmd, takes_input in GRID:
        s = _score(t, triggers)
        if s > best_score:
            best_score = s
            best_cat = cat
            best_op = op
            best_cmd = cmd
            best_takes = takes_input
    if best_score <= 0 or best_cat is None:
        return None
    return (best_cat, best_op, best_cmd, best_takes, best_score)


def _build_cmd(cmd_template: list[str], payload: str) -> list[str]:
    """Substitute PAYLOAD placeholder or append payload at end."""
    out = []
    substituted = False
    for part in cmd_template:
        if part == "PAYLOAD":
            out.append(payload)
            substituted = True
        else:
            out.append(part)
    if not substituted and payload:
        out.append(payload)
    return out


def run_cell(
    cat: str, op: str, cmd_template: list[str], takes_input: bool, payload: str
) -> dict:
    """Execute a grid cell command and return a result dict (no confidence field — set by caller)."""
    cmd = _build_cmd(cmd_template, payload) if takes_input else list(cmd_template)
    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        elapsed = time.monotonic() - t0
        raw = (proc.stdout or "").strip()
        # Try to parse JSON for richer output
        try:
            data = json.loads(raw)
        except json.JSONDecodeError, ValueError:
            data = {"output": raw or proc.stderr.strip()}
        return {
            "category": cat,
            "operation": op,
            "ok": proc.returncode == 0,
            "data": data,
            "elapsed": round(elapsed, 3),
            "payload": payload,
        }
    except subprocess.TimeoutExpired:
        return {
            "category": cat,
            "operation": op,
            "ok": False,
            "data": {"error": "timeout after 30s"},
            "elapsed": 30.0,
            "payload": payload,
        }
    except Exception as e:
        return {
            "category": cat,
            "operation": op,
            "ok": False,
            "data": {"error": str(e)},
            "elapsed": 0.0,
            "payload": payload,
        }


def _result_rows(result: dict) -> list[tuple[str, str]]:
    """Flatten a result dict into (key, value) display rows."""
    rows: list[tuple[str, str]] = []
    status = "✓ ok" if result["ok"] else "✗ fail"
    rows.append(("status", status))
    conf = result.get("confidence")
    if conf is not None:
        rows.append(("confidence", f"{conf:.3f}"))
    rows.append(("elapsed", f"{result['elapsed']}s"))
    data = result.get("data", {})
    if isinstance(data, dict):
        for k, v in data.items():
            if k in ("schema_version",):
                continue
            s = json.dumps(v) if not isinstance(v, str) else v
            rows.append((k, s))
    else:
        rows.append(("result", str(data)))
    return rows


def dispatch(text: str, prior_result: dict | None = None) -> dict:
    """
    Dispatch one step:
    1. If the step matches the math layer → compute immediately (no subprocess).
    2. Otherwise match against the semantic GRID.

    In pipeline mode, if the prior step was a math result, its numeric value
    is injected as the operand when the current step is also math (e.g.,
    "sin 45 → harmonic wall" threads 0.707 into H(x)).

    Grid matching always uses the ORIGINAL step text so injected
    prior-result JSON doesn't contaminate keyword scoring.
    """
    step_text = text.strip()

    # Pull numeric result from prior math step for pipeline chaining
    prior_numeric = prior_result.get("_numeric_result") if prior_result else None

    # ── Math layer: try first ──────────────────────────────────────────────────
    # If no number is in the step text but prior step gave us one, substitute it.
    has_number = bool(re.search(r"-?\d+\.?\d*", step_text))
    math_text = step_text
    if not has_number and prior_numeric is not None:
        math_text = f"{step_text} {prior_numeric}"
    math_result = dispatch_math(math_text)
    if math_result is not None:
        return math_result

    # ── Semantic layer ────────────────────────────────────────────────────────
    payload = step_text
    if prior_result and prior_result.get("ok"):
        prior_json = json.dumps(prior_result.get("data", {}))[:200]
        payload = f"{step_text}\n[prior_result]: {prior_json}"

    cell = find_cell(step_text)  # match on step_text, not enriched payload
    if not cell:
        return {
            "category": "?",
            "operation": "?",
            "ok": False,
            "confidence": 0.0,
            "data": {"error": f"No grid match for: {text!r}"},
            "elapsed": 0.0,
            "payload": text,
        }
    cat, op, cmd, takes_input, score = cell
    result = run_cell(cat, op, cmd, takes_input, payload if takes_input else "")
    result["confidence"] = round(score / (score + 1), 4)
    return result


# ── Pipeline ──────────────────────────────────────────────────────────────────


def run_pipeline(raw_input: str, quiet: bool = False) -> list[dict]:
    """
    Split input on → and run each step, threading results forward.
    Returns all step results in order.

    When quiet=True, suppresses all progress prints so that stdout contains
    only the final JSON array (used by --json mode for machine consumption).
    """
    steps = [s.strip() for s in raw_input.split("→") if s.strip()]
    results = []
    prior = None
    for i, step in enumerate(steps):
        if not quiet:
            print(f"  step {i + 1}/{len(steps)}: {step[:60]}")
        result = dispatch(step, prior_result=prior)
        results.append(result)
        prior = result
        if not quiet:
            status = "✓" if result["ok"] else "✗"
            print(
                f"  {status} {result['category']} · {result['operation']}  ({result['elapsed']}s)"
            )
    return results


# ── Passthrough mode ──────────────────────────────────────────────────────────


def run_passthrough(tool_name: str, payload: str) -> dict:
    """
    Look up tool_name in tools.json and execute its command+args,
    substituting {task} (and any other {placeholder}) with payload.
    """
    tool = None
    for t in _TOOLS_RAW:
        if t.get("name") == tool_name:
            tool = t
            break

    if tool is None:
        return {
            "category": "passthrough",
            "operation": tool_name,
            "ok": False,
            "confidence": 0.0,
            "data": {"error": f"Tool {tool_name!r} not found in tools.json"},
            "elapsed": 0.0,
            "payload": payload,
        }

    command = tool.get("command", "python")
    args = [re.sub(r"\{[^}]+\}", payload, str(a)) for a in tool.get("args", [])]
    cmd = [command] + args

    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        elapsed = time.monotonic() - t0
        raw = (proc.stdout or "").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError, ValueError:
            data = {"output": raw or proc.stderr.strip()}
        return {
            "category": "passthrough",
            "operation": tool_name,
            "ok": proc.returncode == 0,
            "confidence": 1.0,
            "data": data,
            "elapsed": round(elapsed, 3),
            "payload": payload,
        }
    except subprocess.TimeoutExpired:
        return {
            "category": "passthrough",
            "operation": tool_name,
            "ok": False,
            "confidence": 0.0,
            "data": {"error": "timeout after 30s"},
            "elapsed": 30.0,
            "payload": payload,
        }
    except Exception as e:
        return {
            "category": "passthrough",
            "operation": tool_name,
            "ok": False,
            "confidence": 0.0,
            "data": {"error": str(e)},
            "elapsed": 0.0,
            "payload": payload,
        }


# ── JSON serialiser (handles non-finite floats) ───────────────────────────────


def _safe_json(obj: Any) -> str:
    """json.dumps with non-finite float guard (infinity → string)."""

    def _default(o: Any) -> Any:
        if isinstance(o, float) and not math.isfinite(o):
            return str(o)
        raise TypeError(type(o))

    return json.dumps(obj, default=_default)


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    args = list(sys.argv[1:])

    # ── Extract special flags before normal arg parse ─────────────────────────
    json_mode = "--json" in args
    matrix_mode = "--matrix" in args
    passthrough_mode = "--passthrough" in args

    if json_mode:
        args = [a for a in args if a != "--json"]
    if matrix_mode:
        args = [a for a in args if a != "--matrix"]

    # ── --matrix: print matrix and exit ──────────────────────────────────────
    if matrix_mode:
        print_matrix()
        return

    # ── --passthrough <tool-name> [payload...] ────────────────────────────────
    if passthrough_mode:
        pt_idx = args.index("--passthrough")
        args_after = args[pt_idx + 1 :]
        if not args_after:
            print(
                "Usage: python scripts/mython_bridge.py --passthrough <tool-name> [payload]"
            )
            return
        tool_name = args_after[0]
        payload = " ".join(args_after[1:])
        result = run_passthrough(tool_name, payload)
        if json_mode:
            print(_safe_json([result]))
        else:
            title = f"passthrough · {tool_name}"
            print(_box(_result_rows(result), title))
            print()
        return

    # ── Normal dispatch ───────────────────────────────────────────────────────
    if not args or args[0] in ("--help", "-h", "help", "grid"):
        print_grid_index()
        return

    raw = " ".join(args)
    is_pipeline = "→" in raw or " then " in raw.lower()

    if is_pipeline:
        # Normalize "then" → "→"
        raw = raw.replace(" then ", " → ")
        if not json_mode:
            print(f"\n  PIPELINE: {raw}\n")
        results = run_pipeline(raw, quiet=json_mode)
    else:
        results = [dispatch(raw)]

    if json_mode:
        print(_safe_json(results))
        return

    print()
    for result in results:
        title = f"{result['category']} · {result['operation']}"
        print(_box(_result_rows(result), title))
        print()


if __name__ == "__main__":
    main()

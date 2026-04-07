# Polly Training Pad — Triple-Sandbox Mini IDE

**Date:** 2026-04-04
**Status:** Approved
**Sub-project:** 1 of 4 (Training Pad > Constellation Map > Composer Engine > Living Lattice)

## Purpose

Give Polly a sandboxed coding environment where she can write, run, fail, fix, and learn — generating training data from the entire process. Like taking your kid to the beach to build sandcastles while the ocean is right there.

## Triple Sandbox Architecture

```
OUTER: Deployment Membrane
  Only valid, build-tested code exits. Everything else stays as training data.

  MIDDLE: Life Guard
    Watches execution. Feeds back structured feedback (lint, security, tests).
    Doesn't block experimentation — teaches. Polly sees all feedback.

    INNER: Sand (Cell Workspace)
      Cells connect freely. Any language. Tongue sets intent, not syntax.
      Every action (write, run, fail, fix) = training record.
```

### Inner Sandbox (Sand)
- Cells run in isolated subprocesses with no filesystem/network access
- Memory and time limits per cell
- Cells connect via shared virtual namespace (cross-cell imports)
- Dependency graph forms naturally as cells reference each other

### Middle Sandbox (Life Guard)
- Lints code on every save
- Runs antivirus membrane scanner for security patterns
- Executes tests and reports pass/fail with reasons
- Feeds ALL results back to Polly as structured feedback she can learn from
- Does NOT block — observes and teaches

### Outer Sandbox (Deployment Membrane)
- Code that passes build + tests can be exported as valid responses
- Failures stay as training data with full orientation metadata
- SCBE governance gate: ALLOW / QUARANTINE / DENY
- Only ALLOW exits to production use

## Cell Model

```python
@dataclass
class Cell:
    cell_id: str                    # deterministic hash
    tongue: str                     # KO/AV/RU/CA/UM/DR — intent
    language: str                   # python/typescript/rust/sql/etc
    code: str                       # the actual source
    imports: list[str]              # cell IDs this cell depends on
    outputs: dict                   # captured stdout, return values
    history: list[CellEvent]       # every edit/run/fail/fix
    status: str                     # pass / fail / untested
    feedback: list[LifeGuardNote]  # lint, security, test results
```

### Cell Events (Training Signal)
Every action becomes a training record:
- `write` — code was written or edited
- `run` — code was executed (with stdout/stderr)
- `fail` — execution or test failure (with error details)
- `fix` — code was modified after a failure
- `import` — cell connected to another cell
- `feedback` — life guard provided a note

The full history of a cell = a multi-turn SFT sequence showing the process of coding, not just the final answer.

### Tongue Determines Intent
- KO: "Build a CLI that does X" (dispatch)
- AV: "Document how this works" (knowledge)
- RU: "Enforce rate limiting" (governance)
- CA: `def solve(...)` (computation)
- UM: `def validate_input(...)` (security)
- DR: `class Schema:` (structure)

Language is independent — a CA cell could be Python, Rust, or SQL depending on the task.

## Integration Points

### Existing Infrastructure Used
- **Polly Pads Runtime** (`src/polly_pads_runtime.py`): HOT zone = inner sandbox, SAFE zone = life-guard-validated code
- **Workspace Engine** (`src/workspace/engine.py`): Cell layout, tongue routing via tabs
- **Antivirus Membrane** (`agents/antivirus_membrane.py`): Security scanning in life guard layer
- **Auto Marker** (`training/auto_marker.py`): Orient all cell events with L0-L3 + tongue + null pattern
- **Training Station** (`training/training_station.py`): Ingest cell histories as SFT data

### New Components
1. **`src/training_pad/cell.py`** — Cell dataclass, CellEvent, virtual namespace
2. **`src/training_pad/sandbox.py`** — Subprocess executor with isolation (inner sandbox)
3. **`src/training_pad/lifeguard.py`** — Lint/security/test watcher (middle sandbox)
4. **`src/training_pad/membrane.py`** — Build validation + export gate (outer sandbox)
5. **`src/training_pad/pad.py`** — Training pad session orchestrator
6. **`src/training_pad/sft_recorder.py`** — Converts cell histories to oriented SFT records

## Data Flow

```
Polly writes code in Cell
  → Inner sandbox executes (isolated subprocess)
  → Life guard observes (lint + scan + test)
  → Feedback returned to Polly
  → Polly reads feedback, edits code
  → Repeat until pass or abandon
  → Cell history → auto_marker → oriented SFT record
  → Passing code → deployment membrane → valid export
```

## Training Data Output

Each cell session produces:
- Multi-turn instruction/response pairs (the coding process)
- Tongue profile + null pattern per event
- L0-L3 layer classification
- Category tag (code, cyber, infra, etc.)
- Life guard feedback as structured metadata
- Pass/fail outcome as quality signal

## Success Criteria

1. Polly can write code in any language inside cells
2. Cells can import from each other via virtual namespace
3. Code executes in isolated subprocess (no host access)
4. Life guard provides structured feedback on every run
5. Only passing code exits through deployment membrane
6. Every cell event becomes an oriented SFT training record
7. Full cell histories can be fed to training station

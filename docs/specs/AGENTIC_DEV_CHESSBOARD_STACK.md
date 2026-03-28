# Agentic Dev Chessboard Stack (Spec Kit + BMAD + GSD + Superpowers)

This is an operational model for using multiple agentic-dev "frameworks" together without treating them as rival religions.

Goal: understand relationships in motion.

## Chess piece mapping

This is an interpretation based on what each framework is optimized to control.

- Spec Kit = King
- BMAD = Queen
- GSD = Rook
- Superpowers = Bishop
- Tasks/stories = Pawns

## Why each framework lands there (design pressure)

Each framework is centered on a different failure mode.

- Spec Kit (King): failure mode = building the wrong thing or having no governing principles.
  - Output: constitution, requirements, constraints, acceptance criteria.
  - Why King: the whole position is organized around it; changing it is high consequence.

- BMAD (Queen): failure mode = single-agent tunnel vision and missing perspectives.
  - Output: role-based orchestration (PM/architect/dev/QA style) and debate before commitment.
  - Why Queen: broadest directional reach; applies pressure from multiple angles.

- GSD (Rook): failure mode = context rot and long-run drift.
  - Output: state/ledger artifacts, stable "lanes" of execution across time.
  - Why Rook: straight, durable lane control; powerful once lanes are open.

- Superpowers (Bishop): failure mode = sloppy implementation and "done" without evidence.
  - Output: disciplined implementation loop (small steps, tests tied to changes, verification gates).
  - Why Bishop: force along constrained lines; long-range pressure via proof.

## How it moves (relationships in motion)

Opening (start of work):
1. King safety: Spec Kit establishes the constitution/spec and acceptance criteria.
2. Queen activity: BMAD role council challenges assumptions and proposes alternatives.
3. Rook lanes: GSD creates/updates state artifacts to preserve position across sessions.
4. Bishop diagonals: Superpowers turns approved design into disciplined implementation steps.
5. Pawns advance: tasks move one square at a time and eventually "promote" into reusable assets.

Castling:
- Spec Kit + GSD are your "castling move":
  - stabilize governing principles (king safety),
  - activate continuity (rook becomes useful),
  - reduce the chance the run collapses mid-session.

Check / pin / fork:
- Superpowers gives "check" through tests and evidence requirements.
- Spec Kit creates "pins" (implementation is pinned to constraints/invariants).
- BMAD creates "forks" (multiple roles expose multiple liabilities at once).
- GSD controls files/ranks (prevents the run from losing its lane).

## Mapping to SCBE Sacred Tongues (operational roles)

Use BMAD's "multi-role council" idea, but implement it with the 6 Tongues:

- KO: Orchestrator / Intent (what are we doing, why now, what is allowed)
- RU: Witness / Policy (what claims are safe, what obligations exist, what proof is required)
- CA: Compute / Implementation (how it works technically, constraints, performance, math)
- AV: Interfaces / External IO (connectors, UX surfaces, APIs, integrations)
- UM: Security / Privacy (threat model, secrets, blast radius, safe defaults)
- DR: Verification / Judge (tests, correctness, diffs, regression prevention)

This is the "Queen" layer: it is broad, role-based, and adversarial in a useful way.

## Minimal hybrid formula

One-line operating loop:

- Spec Kit defines.
- BMAD debates.
- GSD carries.
- Superpowers constrains.

## Where this fits in SCBE automation

Use the Momentum Train as the "Rook rails":
- it preserves state (`artifacts/momentum_trains/.../state.json`)
- it creates repeatable lanes (daily ops, marketing, vault, inbox)

Use the Governance Gate as the "Bishop proof line":
- actions require justification and safe execution patterns
- "done" requires evidence

## Next build step (repo-level)

If you want this to be executable rather than philosophical:
1. Generate prompt packets for each piece/role (King/Queen/Rook/Bishop + 6 Tongues).
2. Store those packets in `artifacts/` for the run and optionally mirror them into the Obsidian vault.
3. Wire a Momentum Train flow to generate the packets on demand.

See also:
- `workflows/momentum/chessboard_dev_stack_train.json`
- `scripts/system/chessboard_dev_stack.py`


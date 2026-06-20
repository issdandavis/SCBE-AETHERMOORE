# Wildlife Board — Organization-as-Husbandry v1

**Status:** v1 spec, 2026-05-09
**Replaces:** flat task lists (cursor todos, GitHub issues lists, README "next steps" sections)
**Implements via:** `scripts/wildlife/`, drives `scbe-system agentbus run`

---

## Why this exists

Task lists are an output, not a model. They tell you *what* but not *what kind*,
*how it propagates if ignored*, or *what skill is needed to handle it*.

A flat list of 100 tasks treats a flaky test the same as a federal proposal,
treats a typo in a README the same as a critical security regression, treats
a one-line dependabot bump the same as a multi-week refactor. They're not the
same and they don't compose the same.

The Wildlife Board models work as a **Go board where the opponent is a pack
of feral animals**. Each animal is a work item. Animals belong to **packs**
(kinds). Packs have different husbandry skills, propagation rules, and value
under taming.

Ignoring an animal makes it breed. Taming it converts hostile territory to
yours. Herding moves a whole pack at once.

---

## The board

- **Intersections** = work units (issues, TODOs, lint warnings, failing tests, stale branches, drafted proposals, etc.)
- **Stones** = your moves. Placing a stone = claiming/triaging the unit.
- **Captures** = a unit with no liberties (no path to progress) is captured by the wild — it becomes blocked, abandoned, or rotten.
- **Liberties** = the open dependencies/blockers around a unit. A unit with 0 liberties is dead unless rescued.
- **Territory** = packs you've fully tamed in a region (e.g., "all PQC tests green" = a tamed Bee colony).

The board is **read** with `scripts/wildlife/show_board.py`. The board is
**driven** through `scbe-system agentbus run` — each move is an agent-bus
event with `task_type` matching the pack.

---

## The packs

Each pack maps to a real signal in the repo. Packs are defined in
`scripts/wildlife/packs.py` so the classifier and the spec stay in sync.

| Pack | Animal | Real signal | Husbandry skill | If ignored |
|---|---|---|---|---|
| **Wolves** | predator, dangerous, multiplies fast | Critical bugs, security regressions, broken prod (e.g. PR #1522 widget bug) | Tracker — read logs/live smoke, find bite radius, pen the wolf | Bites more users every hour |
| **Crows** | scavengers, persistent, opportunistic | Tech debt, dead code, lint warnings, stale TODO/FIXME comments | Picker — sweep in batches, recycle into useful tests or delete | Caw louder, mock new features |
| **Goats** | herdable, productive when penned | Open feature work with clear scope | Shepherd — fence into a milestone, deliver | Wander into roads, eat unrelated code |
| **Bees** | colony-driven, infrastructure | CI workflows, deploys, Vercel/Pages config, dependency bumps | Beekeeper — calm whole hive at once, harvest reliability | Sting on every PR, swarm to other branches |
| **Cats** | territorial, independent | Research spikes, exploratory benchmarks, novel architecture probes | Coaxer — feed without crowding; some cats are valuable, some leave gifts | Disappear with the work, return only on their own terms |
| **Horses** | trainable, valuable when broken | Long-running training jobs, multi-week refactors, long-form docs | Trainer — patient repetition, structured rounds | Throw the rider, eat the budget |
| **Sheep** | easy to herd in number | Dependabot bumps, formatter passes, trivial PRs, sitemap entries | Drover — round up in one PR, audit the count | Cluster, get lost individually, look like Wolves to a tired reviewer |
| **Otters** | playful, fragile, delight when domesticated | UI/UX polish, demos, audio/visual flourishes (L14, hire-page CTAs) | Curator — protect from over-engineering, ship the playfulness | Drown when scope creeps |
| **Dragons** | rare, high-stakes, multi-week, can torch the village | Federal proposals, major architectural rewrites, novel mathematical claims (MATHBAC, CLARA, harmonic wall papers) | Dragon-rider — earned slowly; never lone-soloed | Burn the budget, set fire to morale |

**Pack alphabet**: WOLF, CROW, GOAT, BEE, CAT, HORSE, SHEEP, OTTER, DRAGON.

---

## Mechanics

### Propagation (breeding)

Each pack has a propagation rule. If the count of un-tamed animals in a pack
exceeds its breeding threshold, new animals appear on the board next harvest:

| Pack | Threshold | Spawn rule |
|---|---|---|
| Wolves | 1 | An untamed wolf for >24h spawns 1 wolf elsewhere (regression cascade) |
| Crows | 10 | Crows breed only above 10; below that they're tolerable |
| Goats | 5 untamed in same area | Goats wander, increasing scope |
| Bees | 3 failing infra | Whole hive becomes hostile (red CI cascade) |
| Cats | n/a | Cats don't breed but disappear if neglected (spike abandoned) |
| Horses | n/a | Horses don't breed but lose training (long-job context lost) |
| Sheep | 25 | Mass-PR if too many trivial bumps queue up |
| Otters | n/a | No breeding; just drown one by one |
| Dragons | n/a | One dragon at a time; do not provoke a second |

### Taming

A move that **tames** an animal converts its intersection from wild to yours.

- **Wolves**: tame = ship the fix + add a regression test that locks the contract (PR #1529 was a wolf-tame on the widget)
- **Crows**: tame = sweep N at once into one cleanup PR; delete dead, document live
- **Goats**: tame = pen into a milestone with explicit acceptance criteria
- **Bees**: tame = harden the workflow (PR #1523 tamed the Pages-deploy bee; PR #1530 tamed the no-stats bee)
- **Cats**: tame = write up the spike, even if inconclusive
- **Horses**: tame = checkpoint, log progress in a memory entry, run regression eval
- **Sheep**: tame = batch into a single drove-PR
- **Otters**: tame = ship the polish exactly as designed; resist over-scoping
- **Dragons**: tame = milestone-by-milestone with explicit rider rotation

### Herding

A herd-move handles a whole pack subset in one stroke. Examples:

- `wildlife herd sheep --max 25 --as-pr` — collect up to 25 dependabot/format/trivial PRs into one
- `wildlife herd crows --in src/aetherbrowser/` — sweep all TODO/FIXME in one path
- `wildlife herd bees --workflow Deploy*` — fix triggers across all deploy-named workflows

### Liberties

Every animal has **liberties** = remaining open dependencies. Track in the
board json. A wolf with 0 liberties is **trapped** — must be tamed or dies
(silently breaks more users until it screams).

---

## Output: the board state

`.scbe/wildlife/board.json` — single source of truth, regenerated by harvest.

```json
{
  "schema": "wildlife-board-v1",
  "harvested_at": "2026-05-09T23:50:00Z",
  "totals": {"wolves": 2, "crows": 47, "goats": 12, "bees": 5, "cats": 3, "horses": 4, "sheep": 31, "otters": 6, "dragons": 2},
  "wolves": [
    {
      "id": "wolf-issue-1454",
      "title": "Petri governance gates regression",
      "source": "github-issue",
      "url": "https://github.com/issdandavis/SCBE-AETHERMOORE/issues/1454",
      "liberties": 2,
      "first_seen": "2026-05-08",
      "tame_command": "scbe-system agentbus run --task 'fix petri gate regression' --task-type governance --series-id wolf-1454"
    }
  ],
  "crows": [...],
  ...
}
```

The board is **append-only-with-tame-flags** — once an animal is tamed, the
record stays for the audit trail; it just gets `tamed_at: <ts>` and drops out
of the active count.

---

## Driving from the agent bus

Every tame move is a single agent-bus event:

```bash
scbe-system agentbus run \
    --task "tame wolf: fix Polly widget data.text key bug" \
    --task-type coding \
    --series-id wolf-1522 \
    --privacy local_only \
    --dispatch
```

The harvester emits a `tame_command` string per animal so a shepherd doesn't
have to rebuild the invocation. Pack-level herding wraps multiple events in
one shell of bus calls.

---

## Why not just a kanban?

Kanban shows *state* (todo / doing / done). The Wildlife Board shows
*kind*, *propagation*, and *husbandry*. A kanban can't tell you that a flaky
test ignored for two weeks has bred three more flakies. The board's totals do.

A kanban also flattens the difference between a 5-minute drover-sweep of 25
sheep and a 6-week dragon-rider engagement. The Wildlife Board surfaces this
in the schema (per-pack thresholds + tame-cost hints) so the operator picks
the right move, not just the next-todo move.

---

## Out of scope for v1

- Auto-execution: v1 only **emits** `tame_command`s; it does not run them. The operator (or an authorized shepherd agent) decides when to dispatch.
- Cross-repo boards: v1 is single-repo. v2 should aggregate across `SCBE-AETHERMOORE`, `issdandavis.github.io`, `aetherbrowser`, etc.
- Live propagation: v1 harvests on demand. v2 should run on a cron and diff against the prior board to actually see breeding happen.

## Files

- `scripts/wildlife/packs.py` — pack definitions + classifier
- `scripts/wildlife/harvest_packs.py` — sweep the repo for animals
- `scripts/wildlife/show_board.py` — render the board state
- `tests/wildlife/test_pack_classification.py` — pin the classifier
- `.scbe/wildlife/board.json` — current state (gitignored)

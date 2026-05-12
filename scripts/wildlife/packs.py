"""Pack taxonomy + classifier for the Wildlife Board.

A pack is a *kind* of work, not a priority. Each pack maps to a real signal
in the repo (an issue, a TODO, a failing CI, etc.) and has its own husbandry
skill, breeding rule, and tame-cost hint.

See docs/specs/WILDLIFE_BOARD_v1.md for the full spec.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class Pack:
    name: str  # WOLF, CROW, GOAT, BEE, CAT, HORSE, SHEEP, OTTER, DRAGON
    animal: str  # display name, lowercase singular
    plural: str
    skill: str  # husbandry skill needed
    breeding_threshold: Optional[int]  # None = does not breed
    breeding_rule: str  # human-readable
    tame_hint: str  # how a single animal is tamed
    bus_task_type: str  # what to pass as agentbus --task-type
    severity_floor: int  # 1=otter, 5=dragon — relative ordering for the board view


PACKS: dict[str, Pack] = {
    "WOLF": Pack(
        name="WOLF",
        animal="wolf",
        plural="wolves",
        skill="tracker",
        breeding_threshold=1,
        breeding_rule="any untamed wolf >24h spawns 1 wolf elsewhere (regression cascade)",
        tame_hint="ship the fix + add a regression test that locks the contract",
        bus_task_type="coding",
        severity_floor=4,
    ),
    "CROW": Pack(
        name="CROW",
        animal="crow",
        plural="crows",
        skill="picker",
        breeding_threshold=10,
        breeding_rule="crows only breed above 10; below that they're tolerable",
        tame_hint="sweep N at once into one cleanup PR; delete dead, document live",
        bus_task_type="coding",
        severity_floor=2,
    ),
    "GOAT": Pack(
        name="GOAT",
        animal="goat",
        plural="goats",
        skill="shepherd",
        breeding_threshold=5,
        breeding_rule="goats wander when >5 in same area, increasing scope",
        tame_hint="pen into a milestone with explicit acceptance criteria",
        bus_task_type="coding",
        severity_floor=3,
    ),
    "BEE": Pack(
        name="BEE",
        animal="bee",
        plural="bees",
        skill="beekeeper",
        breeding_threshold=3,
        breeding_rule="3 failing infra makes whole hive hostile (red CI cascade)",
        tame_hint="harden the workflow, fix the trigger, re-run",
        bus_task_type="governance",
        severity_floor=3,
    ),
    "CAT": Pack(
        name="CAT",
        animal="cat",
        plural="cats",
        skill="coaxer",
        breeding_threshold=None,
        breeding_rule="cats don't breed but disappear if neglected (spike abandoned)",
        tame_hint="write up the spike, even if inconclusive — make it cite-able",
        bus_task_type="research",
        severity_floor=2,
    ),
    "HORSE": Pack(
        name="HORSE",
        animal="horse",
        plural="horses",
        skill="trainer",
        breeding_threshold=None,
        breeding_rule="horses don't breed but lose training (long-job context lost)",
        tame_hint="checkpoint, log progress in a memory entry, run regression eval",
        bus_task_type="training",
        severity_floor=4,
    ),
    "SHEEP": Pack(
        name="SHEEP",
        animal="sheep",
        plural="sheep",
        skill="drover",
        breeding_threshold=25,
        breeding_rule="mass-PR if too many trivial bumps queue up >25",
        tame_hint="batch into a single drove-PR",
        bus_task_type="coding",
        severity_floor=1,
    ),
    "OTTER": Pack(
        name="OTTER",
        animal="otter",
        plural="otters",
        skill="curator",
        breeding_threshold=None,
        breeding_rule="no breeding; just drown one by one if scope creeps",
        tame_hint="ship the polish exactly as designed; resist over-scoping",
        bus_task_type="coding",
        severity_floor=2,
    ),
    "DRAGON": Pack(
        name="DRAGON",
        animal="dragon",
        plural="dragons",
        skill="dragon-rider",
        breeding_threshold=None,
        breeding_rule="one dragon at a time; do not provoke a second",
        tame_hint="milestone-by-milestone with explicit rider rotation",
        bus_task_type="governance",
        severity_floor=5,
    ),
}


# ----------------------------- classifier ---------------------------------- #

# Each rule is (pack_name, predicate). First match wins. Order matters —
# specific rules first, broad fallback last. Predicates take a `Signal` dict.


def _is_security(s: dict) -> bool:
    text = f"{s.get('title','')} {s.get('body','')}".lower()
    keywords = ("security", "vulnerab", "cve-", "exploit", "rce ", "xss", "leak", "credential")
    return any(k in text for k in keywords)


def _is_critical_label(s: dict) -> bool:
    labels = [str(x).lower() for x in s.get("labels", [])]
    return any(l in ("critical", "p0", "production-down", "broken") for l in labels)


def _is_failing_ci(s: dict) -> bool:
    return s.get("source") in {"workflow-failure", "broken-deploy"}


def _is_dependabot(s: dict) -> bool:
    title = str(s.get("title", "")).lower()
    return (
        title.startswith("chore(deps") or title.startswith("bump ") or "dependabot" in str(s.get("author", "")).lower()
    )


def _is_format_lint(s: dict) -> bool:
    title = str(s.get("title", "")).lower()
    return any(p in title for p in ("style(", "format(", "lint", "prettier", "black"))


def _is_todo_comment(s: dict) -> bool:
    return s.get("source") == "todo-comment"


def _is_research(s: dict) -> bool:
    text = f"{s.get('title','')} {' '.join(s.get('labels',[]))}".lower()
    return any(k in text for k in ("research", "spike", "explore", "investigate", "benchmark"))


def _is_training(s: dict) -> bool:
    text = f"{s.get('title','')} {s.get('body','')}".lower()
    return any(k in text for k in ("training run", "lora", "qlora", "sft ", "dpo ", "fine-tune"))


def _is_proposal(s: dict) -> bool:
    text = f"{s.get('title','')} {s.get('body','')}".lower()
    return any(k in text for k in ("darpa", "mathbac", "clara", "proposal", "federal", "sam.gov", "subcontract"))


def _is_ci_infra(s: dict) -> bool:
    title = str(s.get("title", "")).lower()
    path = str(s.get("path", "")).lower()
    return (
        title.startswith("ci(")
        or title.startswith("ci:")
        or "workflow" in title
        or path.startswith(".github/workflows/")
    )


def _is_demo_or_polish(s: dict) -> bool:
    text = f"{s.get('title','')} {s.get('path','')}".lower()
    return any(k in text for k in ("polish", "ux", "ui", "design", "demo", "showcase", "audio", "visual"))


def _is_feature(s: dict) -> bool:
    title = str(s.get("title", "")).lower()
    return title.startswith("feat(") or title.startswith("feat:") or "feature" in title


# Rule order: specific → broad. First match wins.
RULES: list[tuple[str, Callable[[dict], bool]]] = [
    # TODO/FIXME comments are crows by definition, regardless of what the
    # comment text says — a TODO in tests/test_security.py containing the
    # word "EXPLOIT" is a security TEST FIXTURE, not an active exploit.
    # Same for the harvester's own docstring listing "TODO/FIXME/XXX/HACK".
    # Source-based identity beats content-based pattern matching here, so
    # this MUST come before the text-scanning WOLF rules.
    ("CROW", _is_todo_comment),
    # Wolves — anything that's actively hurting (label/source-based first;
    # text-based _is_security only fires on real issues/PRs now)
    ("WOLF", _is_critical_label),
    ("WOLF", _is_failing_ci),
    ("WOLF", _is_security),
    # Dragons before training/research — federal/major
    ("DRAGON", _is_proposal),
    # Horses — training jobs (issues/PRs only at this point)
    ("HORSE", _is_training),
    # Cats — research spikes
    ("CAT", _is_research),
    # Sheep — trivial chore PRs
    ("SHEEP", _is_dependabot),
    ("SHEEP", _is_format_lint),
    # Bees — CI/infra
    ("BEE", _is_ci_infra),
    # Otters — polish/demos
    ("OTTER", _is_demo_or_polish),
    # Goats — generic feature work
    ("GOAT", _is_feature),
]


def classify(signal: dict) -> str:
    """Return the pack name for a single signal dict.

    Default fallback is GOAT (generic feature/scoped work).
    """
    for pack, predicate in RULES:
        try:
            if predicate(signal):
                return pack
        except Exception:  # noqa: BLE001 — never let one bad signal poison classification
            continue
    return "GOAT"


def severity_order() -> list[str]:
    """Pack names ordered by severity_floor descending (dragons first, sheep last)."""
    return sorted(PACKS.keys(), key=lambda p: (-PACKS[p].severity_floor, p))

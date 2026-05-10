"""Shepherds — model-per-pack dispatch strategy for the Wildlife Board.

Each pack has different work-character: sheep are bulk-trivial, dragons are
rare-and-grave. Routing all packs to the same model wastes money on sheep and
under-powers wolves. The shepherds module maps each pack to a strategy:

  - which model to call
  - which backend (Ollama local, HF cloud, or "human-only")
  - what prompt template to use
  - whether to dispatch via the agent bus or call the model directly

Cheap-first: local Ollama for sheep/crows/otters/bees (small qwen-coder
variants), HF cloud for goats/wolves/cats (Qwen2.5-7B-Instruct), training
pipeline for horses (own runner), and human-only for dragons (never auto).

This module is **plan only by default** — it produces a `dispatch_plan.json`
describing what would happen. Pass `--execute` to actually call models. The
spec at docs/specs/WILDLIFE_BOARD_v1.md and the bus runner at
`scripts/scbe-system-cli.py agentbus run` are the contracts; this module
sits between the board and the bus.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Shepherd:
    pack: str  # WOLF, CROW, ...
    backend: str  # "ollama" | "huggingface" | "training-pipeline" | "human-only"
    model: str  # model id within that backend
    bus_dispatch: bool  # True = route through agentbus run; False = direct or skip
    prompt_template: str  # one-line prompt scaffold; "{title}" is filled
    cost_tier: str  # "free" | "cheap" | "standard" | "expensive" | "n/a"


# Default shepherds. Change here to re-tune cost/quality per pack.
# Cost tier rough scale (per call):
#   free      = local Ollama on user's machine, $0
#   cheap     = HF Router with small model, ~$0.001
#   standard  = HF Router with 7B-class, ~$0.01
#   expensive = HF Router with 70B-class, ~$0.10
#   n/a       = no model invoked (human-only or pipeline-owned)

SHEPHERDS: dict[str, Shepherd] = {
    "SHEEP": Shepherd(
        pack="SHEEP",
        backend="ollama",
        model="qwen2.5-coder:1.5b",
        bus_dispatch=False,  # bulk trivial: bypass bus, batch directly
        prompt_template=(
            "One-line action for this trivial chore (dependabot/format/lint): "
            "{title}. Reply with the shell command or PR title only."
        ),
        cost_tier="free",
    ),
    "CROW": Shepherd(
        pack="CROW",
        backend="ollama",
        model="qwen2.5-coder:1.5b",
        bus_dispatch=False,
        prompt_template=(
            "TODO/FIXME comment to triage: {title}. Reply with one of: "
            "DELETE (if dead code), DOCUMENT (if intentional), or "
            "FIX:<one-line plan> (if real work). 25 words max."
        ),
        cost_tier="free",
    ),
    "OTTER": Shepherd(
        pack="OTTER",
        backend="ollama",
        model="qwen2.5-coder:7b",
        bus_dispatch=True,
        prompt_template=(
            "UI/UX polish task: {title}. Suggest one concrete CSS/HTML change "
            "that improves it without scope creep. 50 words max."
        ),
        cost_tier="free",
    ),
    "BEE": Shepherd(
        pack="BEE",
        backend="ollama",
        model="qwen2.5-coder:7b",
        bus_dispatch=True,
        prompt_template=(
            "CI/workflow infra issue: {title}. Suggest the YAML or env-var "
            "change. Reference the file if you can guess it. 60 words max."
        ),
        cost_tier="free",
    ),
    "GOAT": Shepherd(
        pack="GOAT",
        backend="huggingface",
        model="Qwen/Qwen2.5-7B-Instruct",
        bus_dispatch=True,
        prompt_template=(
            "Scoped feature work: {title}. Draft an acceptance-criteria "
            "checklist (3-5 bullets) so it can be penned into a milestone."
        ),
        cost_tier="standard",
    ),
    "WOLF": Shepherd(
        pack="WOLF",
        backend="huggingface",
        model="Qwen/Qwen2.5-7B-Instruct",
        bus_dispatch=True,
        prompt_template=(
            "Critical bug or failed CI: {title}. Reply with: (1) likely root "
            "cause in 1 sentence; (2) the file most likely to need editing; "
            "(3) the regression test that should lock the fix. 80 words max."
        ),
        cost_tier="standard",
    ),
    "CAT": Shepherd(
        pack="CAT",
        backend="huggingface",
        model="Qwen/Qwen2.5-7B-Instruct",
        bus_dispatch=True,
        prompt_template=(
            "Research spike: {title}. Reply with: (1) the question this spike "
            "is supposed to answer; (2) the smallest experiment that resolves "
            "it; (3) what 'inconclusive' would still teach us. 100 words max."
        ),
        cost_tier="standard",
    ),
    "HORSE": Shepherd(
        pack="HORSE",
        backend="training-pipeline",
        model="<owned by training pipeline>",
        bus_dispatch=False,
        prompt_template="<routed to training pipeline, not LLM>",
        cost_tier="n/a",
    ),
    "DRAGON": Shepherd(
        pack="DRAGON",
        backend="human-only",
        model="<requires human rider>",
        bus_dispatch=False,
        prompt_template="<never auto-dispatched: dragons require human review>",
        cost_tier="n/a",
    ),
}


def shepherd_for(pack: str) -> Optional[Shepherd]:
    return SHEPHERDS.get(pack.upper())


def render_prompt(pack: str, title: str) -> Optional[str]:
    """Return the rendered prompt for a pack, or None if the shepherd is non-callable.

    Sentinel templates (training-pipeline / human-only) start with `<` and contain
    no `{title}` slot — they exist for documentation only.
    """
    s = shepherd_for(pack)
    if s is None:
        return None
    if "{title}" not in s.prompt_template:
        return None  # sentinel template, not a real prompt
    return s.prompt_template.format(title=title)


def is_auto_dispatchable(pack: str) -> bool:
    """True if a shepherd will autonomously call a model for this pack.

    Dragons (human-only) and Horses (training-pipeline-owned) are not.
    """
    s = shepherd_for(pack)
    if s is None:
        return False
    return s.backend in {"ollama", "huggingface"}

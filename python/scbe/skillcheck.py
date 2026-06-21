"""skillcheck: a KOTOR-style gated decision interface for an agent driving a bounded surface.

Issac's design: don't ask the model 'pick any action'. Reframe each step as a small MENU of skill-check
options -- like KOTOR dialogue. Each option is:
  * GATED      -- bad gates are SOFT-LOCKED (proven-wrong or clearly low-odds) so the model can't pick them.
  * PREVIEWED  -- every option shows its outcome (the 'probability vision': a confidence + an effect).
  * AUTOFILLED -- action values are filled deterministically (the typed text parsed from the instruction),
                  so the model never has to produce the mechanics, only the CHOICE.
When the gates + the probability vision leave a clear winner, the check 'passes' and the option is taken
DETERMINISTICALLY -- no model call. Only genuine ambiguity is handed to the model, and even then over a
PRUNED menu. Choosing transfers deterministically to the concrete action.

This is the board-game/legal-moves governance ([[board-game-thinking-surface]]) + the prune-wrong restructure
([[stepwise-misstep-rewind]]) rendered as a player-visible skill check. It is policy/agent agnostic: feed it
an instruction + a bounded element list, get a menu; let any model pick, or let the gates decide.

    from python.scbe.skillcheck import skill_menu, choose
    menu = skill_menu(instruction, elements, tried)        # the gated, previewed, autofilled options
    opt  = choose(menu)                                     # deterministic if a winner dominates, else None
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple

# confidence thresholds for the "probability vision"
_PASS = 0.9  # an option this confident, clearly ahead of the rest, auto-resolves (skill check passes)
_GAP = 0.3  # how far ahead of the runner-up the winner must be to auto-resolve
_FLOOR = 0.3  # options below this are soft-locked when a real contender exists
_CONTENDER = 0.6


@dataclass
class Option:
    """One skill-check option: a gated, previewed, autofilled choice."""

    id: int
    kind: str  # click | type | submit
    ref: Optional[str]
    value: Optional[str]
    label: str  # KOTOR-style, e.g. "[Click] 'previous' (0.95 -> activates previous)"
    gate: str  # "open" | "locked"
    preview: str  # the outcome shown to the chooser
    confidence: float  # the probability vision

    def render(self) -> str:
        mark = "  " if self.gate == "open" else "[X]"
        return "%s %d. %s  (%.2f -> %s)" % (mark, self.id, self.label, self.confidence, self.preview)


def _targets(instruction: str) -> List[str]:
    return [t.lower() for t in re.findall(r'"([^"]+)"', instruction)]


def skill_menu(
    instruction: str, elements: List[Dict[str, Any]], tried: FrozenSet[Tuple[str, Optional[str]]] = frozenset()
) -> List[Option]:
    """Build the gated, previewed, autofilled option menu from a bounded element list. Pure."""
    q = instruction or ""
    ql = q.lower()
    targets = _targets(q)
    target = targets[0] if targets else ""
    wants_submit = any(w in ql for w in ("submit", "press enter", "and press", "login", "log in", "sign in"))
    wants_focus = "focus" in ql
    # ordered values to place into ordered fields (login: username then password)
    field_vals = list(targets)
    field_idx = 0
    opts: List[Option] = []
    i = 0
    for e in elements:
        name = (e.get("name") or "").lower()
        if e.get("editable"):
            cur = e.get("value") or ""
            val = field_vals[field_idx] if field_idx < len(field_vals) else (targets[0] if targets else "")
            field_idx += 1
            if wants_focus and not val:  # 'focus the input' -> a click that focuses, high odds
                opts.append(
                    Option(
                        i,
                        "click",
                        e["ref"],
                        None,
                        "[Focus] %r" % (e.get("name") or "input"),
                        "open",
                        "focus the input",
                        0.9,
                    )
                )
            elif val and cur == val:  # already filled with the target -> this field is DONE (locked)
                opts.append(
                    Option(
                        i,
                        "type",
                        e["ref"],
                        val,
                        "[Type] %r (done)" % (e.get("name") or "field"),
                        "locked",
                        "already filled",
                        0.0,
                    )
                )
            else:
                conf = 0.9 if val else 0.45
                opts.append(
                    Option(
                        i,
                        "type",
                        e["ref"],
                        val,
                        "[Type] %r" % (e.get("name") or "field"),
                        "open",
                        "field := %r" % val,
                        conf,
                    )
                )
        else:
            is_submit_btn = any(w in name for w in ("submit", "login", "ok", "done", "go"))
            if target and target in name:
                conf = 0.95  # the named click target -- the probability vision points here
            elif target and name and name in target:
                conf = 0.8
            elif wants_submit and is_submit_btn:
                conf = 0.85  # the submit button, boosted when the task wants a submit
            elif not target:
                conf = 0.5
            else:
                conf = 0.2  # a named target exists and this isn't it -> long shot
            opts.append(
                Option(
                    i,
                    "click",
                    e["ref"],
                    None,
                    "[Click] %r" % (e.get("name") or e.get("tag", "")),
                    "open",
                    "activate %r" % (e.get("name") or e.get("tag", "")),
                    conf,
                )
            )
        i += 1

    # SOFT-LOCK the bad gates: proven-wrong (already tried), and long shots when a real contender exists.
    best = max((o.confidence for o in opts), default=0.0)
    for o in opts:
        if (o.kind, o.ref) in tried:
            o.gate, o.preview, o.confidence = "locked", "already tried, failed", 0.0
        elif o.confidence < _FLOOR and best >= _CONTENDER:
            o.gate, o.preview = "locked", "low-odds (soft-locked)"
    return opts


def choose(menu: List[Option]) -> Optional[Option]:
    """If the probability vision leaves a clear winner among the open gates, take it (the check passes).
    Otherwise return None -- the caller hands the PRUNED open menu to a model."""
    open_opts = sorted((o for o in menu if o.gate == "open"), key=lambda o: -o.confidence)
    if not open_opts:
        return None
    if len(open_opts) == 1:
        return open_opts[0]
    top, second = open_opts[0], open_opts[1]
    if top.confidence >= _PASS and (top.confidence - second.confidence) >= _GAP:
        return top
    return None


def open_menu(menu: List[Option]) -> List[Option]:
    """The pruned set of still-open options, best-first -- what a model is asked to choose among."""
    return sorted((o for o in menu if o.gate == "open"), key=lambda o: -o.confidence)


def audit_menu(instruction: str, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
    """ChoiceScript-randomtest signal for ONE step: is the path healthy? broken = no open gate at all (the
    agent is stuck); ambiguous = open gates but no clear winner (a real decision); resolved = a winner the
    gates hand off deterministically. The 'skill checks / stats' you watch to find broken pathing."""
    menu = skill_menu(instruction, elements)
    opens = open_menu(menu)
    winner = choose(menu)
    state = "broken" if not opens else ("resolved" if winner else "ambiguous")
    return {
        "state": state,
        "open": len(opens),
        "locked": sum(1 for o in menu if o.gate == "locked"),
        "winner": (winner.label if winner else None),
        "top_conf": (opens[0].confidence if opens else 0.0),
    }


class SkillCheckPolicy:
    """The KOTOR interface as a policy: build the gated menu, take the deterministic winner if the gates
    leave one, else (with a model) let it pick from the PRUNED menu. `ask` is prompt->str; None = run on
    the gates + probability vision alone (no model)."""

    def __init__(self, ask: Optional[Callable[[str], str]] = None):
        self.ask = ask
        self.name = "skillcheck+model" if ask is not None else "skillcheck"

    def act(self, obs: Dict[str, Any]) -> Optional[Any]:
        from .ai_browser import Move

        menu = skill_menu(obs["instruction"], obs["elements"])
        opt = choose(menu)
        if opt is None and self.ask is not None:
            opt = pick_by_model(menu, obs["instruction"], self.ask)
        if opt is None:
            om = open_menu(menu)
            opt = om[0] if om else None
        if opt is None:
            return None
        if opt.kind == "type":
            return Move("type", ref=opt.ref, value=opt.value or "")
        if opt.kind == "submit":
            return Move("submit")
        return Move("click", ref=opt.ref)


def pick_by_model(menu: List[Option], instruction: str, ask: Callable[[str], str]) -> Optional[Option]:
    """Hand the PRUNED menu to a model: it replies with the option id. Deterministic transfer of the id ->
    the chosen Option. `ask` is prompt->text (e.g. an ollama call)."""
    options = open_menu(menu)
    if not options:
        return None
    listing = "\n".join(o.render() for o in options)
    prompt = (
        'Instruction: "%s"\n\nChoose the ONE best option by number (locked options [X] are off-limits):\n%s\n\n'
        "Reply with ONLY the number." % (instruction, listing)
    )
    try:
        resp = ask(prompt)
    except Exception:
        return options[0]
    m = re.search(r"\d+", resp or "")
    if m:
        cid = int(m.group(0))
        for o in options:
            if o.id == cid:
                return o
    return options[0]  # fall back to the highest-confidence open option

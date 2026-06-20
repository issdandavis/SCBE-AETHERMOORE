"""colab_actions: a GOVERNED action registry for operating Colab UNDER THE USER'S BANNER.

The AetherDesktop idea is "let an AI run the tools my PC can, in my own logged-in browser, with
guardrails + memory." This module is the GUARDRAIL + MEMORY layer for the Colab surface: every browser
action an AI proposes -- run a cell, run all, read a cell's output, inject + run code -- goes through the
SAME hardened desktop_access gate as desktop actions:

  * the never-delete / scope / chaining screens (a cell that injects ``rm -rf`` or ``vssadmin delete`` or
    ``shutil.rmtree`` is REFUSED -- the code is screened as the action's text_param);
  * the L13 intent gate (if importable);
  * confirm-for-guarded (running or injecting needs an explicit reason; reading is safe);
  * a SHA-256 forward-chain SEALED transcript -- the tamper-evident record of everything the AI did in
    your name (the audit memory).

So "AI works on Colab under your banner" is governed BY CONSTRUCTION, not by trust. The handlers here are
SAFE STUBS by default; the real hands (the Chrome extension, or the CDP driver in tools/colab/colab_run.py)
wire in BEHIND the gate via the `executor` seam -- never in front of it. Reuses
python/scbe/desktop_access.py wholesale (no new governance logic). See also [the design] in
docs/ and the sealed-transcript audit via ActionRegistry.verify().

    from python.scbe.colab_actions import colab_registry
    reg = colab_registry()                                  # safe stubs
    reg.invoke("colab_inject_and_run", {"code": "rm -rf /"}, confirm="x")["decision"]  # -> REFUSED
    reg.invoke("colab_read_output", {"cell_index": 3})["decision"]                     # -> ALLOWED (safe)
    reg.verify()                                            # the run is sealed + tamper-evident
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .desktop_access import Action, ActionRegistry

# the real hands: executor(action_name, params) -> result. None = safe stub (nothing touches the host).
Executor = Callable[[str, Dict[str, Any]], Any]


def colab_registry(executor: Optional[Executor] = None) -> ActionRegistry:
    """A governed registry of Colab browser actions. With no executor the handlers are safe stubs; pass
    an executor (the extension bridge, or a CDP driver) and ALLOWED actions delegate to it -- the
    allowlist/never-delete/L13/confirm/seal stay the wall either way."""

    def _do(name: str, params: Dict[str, Any]) -> Any:
        return executor(name, params) if executor else "[stub] %s %s" % (name, params)

    reg = ActionRegistry()
    reg.register(
        Action(
            "colab_read_output",
            "Read the rendered output of a Colab cell",
            {"cell_index": "int"},
            "safe",  # read-only -> no confirm
            "[data-colab-cell] .output",
            "region",
            "Cell output",
            lambda p: _do("colab_read_output", p),
        )
    )
    reg.register(
        Action(
            "colab_run_cell",
            "Run a single Colab cell by index",
            {"cell_index": "int"},
            "guarded",  # running code in your session needs a reason
            "[data-colab-cell]",
            "button",
            "Run cell",
            lambda p: _do("colab_run_cell", p),
        )
    )
    reg.register(
        Action(
            "colab_run_all",
            "Run all cells in the open Colab notebook",
            {},
            "guarded",
            "#runtime-menu",
            "button",
            "Run all",
            lambda p: _do("colab_run_all", p),
        )
    )
    reg.register(
        Action(
            "colab_inject_and_run",
            "Inject a new code cell and run it",
            {"code": "string"},
            "guarded",
            "#inject-cell",
            "button",
            "Inject code",
            lambda p: _do("colab_inject_and_run", p),
            text_param="code",  # the injected CODE is screened (never-delete/chain) + L13-gated
        )
    )
    return reg


def main(argv: Optional[list] = None) -> int:
    reg = colab_registry()
    print("COLAB ACTIONS  governed registry (%d actions); every browser action screened + sealed\n" % len(reg.actions))
    demos = [
        ("colab_read_output", {"cell_index": 3}, None),
        ("colab_run_cell", {"cell_index": 3}, None),  # guarded -> NEEDS_CONFIRM
        ("colab_run_cell", {"cell_index": 3}, "user approved"),
        ("colab_inject_and_run", {"code": "print(sum(range(10)))"}, "compute a sum"),
        ("colab_inject_and_run", {"code": "import shutil; shutil.rmtree('/content')"}, "cleanup"),  # REFUSED
    ]
    for name, params, confirm in demos:
        r = reg.invoke(name, params, confirm=confirm)
        print("  %-22s %-13s %s" % (name, r["decision"], str(r["result"])[:48]))
    print("\n  transcript sealed + tamper-evident:", reg.verify())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""toolkit: one governed, sealed registry over every real SCBE coding+math+control system.

Tests prove the catalog is well-formed, pure tools invoke + seal, guarded tools need a confirm, a
destructive argument is refused, unknown/unimportable tools degrade honestly, tools compose, and the
transcript is tamper-evident.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.toolkit import CATALOG, Tool, Toolkit, default_toolkit  # noqa: E402


def test_catalog_is_well_formed():
    names = [t.name for t in CATALOG]
    assert len(names) == len(set(names))  # unique tool names
    assert all(t.safety in ("safe", "guarded") for t in CATALOG)
    assert all(t.module and t.callable and t.one_line for t in CATALOG)
    assert len(CATALOG) >= 80  # the full inventory


def test_pure_tool_invokes_and_seals():
    tk = default_toolkit()
    r = tk.invoke("is_prime", 97)
    assert r["decision"] == "ALLOWED" and r["result_obj"] is True
    assert r["seal"] and tk.verify() is True


def test_destructive_argument_is_refused():
    tk = default_toolkit()
    r = tk.invoke("is_prime", "rm -rf /")  # a destructive string in an arg
    assert r["decision"] == "REFUSED"
    assert tk.verify() is True


def test_guarded_tool_needs_a_confirm():
    tk = default_toolkit()
    r = tk.invoke("run_level", [])  # guarded (file/desktop) tool, no confirm
    assert r["decision"] == "NEEDS_CONFIRM"


def test_unknown_and_unimportable_tools_degrade():
    tk = default_toolkit()
    assert tk.invoke("no_such_tool")["decision"] == "NO_TOOL"
    bogus = Toolkit(tools=[Tool("bogus", "no.such.module", "x", "math", "n/a", "safe")])
    assert bogus.invoke("bogus")["decision"] == "UNAVAILABLE"


def test_tools_compose_through_result_obj():
    tk = default_toolkit()
    stones = tk.invoke("place", [1, 2, 3])["result_obj"]
    prog = tk.invoke("recover", stones)["result_obj"]
    assert prog == [1, 2, 3]  # place -> recover round-trips through the sealed registry


def test_transcript_is_tamper_evident():
    tk = default_toolkit()
    tk.invoke("is_prime", 5)
    tk.invoke("factorization", 12)
    assert tk.verify() is True
    tk.transcript[0]["result"] = "tampered"  # mutate a sealed record
    assert tk.verify() is False


def test_reordering_records_breaks_the_seal_chain():
    tk = default_toolkit()
    tk.invoke("is_prime", 5)
    tk.invoke("is_prime", 7)
    assert tk.verify() is True
    tk.transcript[0], tk.transcript[1] = tk.transcript[1], tk.transcript[0]  # reorder
    assert tk.verify() is False  # the forward chain (prev seal) catches it


def test_swapping_a_composition_payload_breaks_verify():
    tk = default_toolkit()
    r = tk.invoke("place", [1, 2, 3])
    assert tk.verify() is True
    r["result_obj"] = [9, 9, 9]  # swap the live payload another tool would consume
    assert tk.verify() is False  # result_hash is sealed, so the swap is caught


def test_subprocess_spawning_tools_are_guarded():
    tk = default_toolkit()
    for name in ("conformance", "run_public_bench"):
        assert tk.by_name(name).safety == "guarded"  # they execute code -> must need a confirm


def test_most_tools_are_importable_here():
    tk = default_toolkit()
    avail = tk.available()
    assert sum(1 for v in avail.values() if v) >= 70  # catalog paths are mostly correct on this box

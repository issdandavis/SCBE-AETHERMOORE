from __future__ import annotations

from src.coding_spine.deterministic_tongue_router import extract_routing_text, route_prompt


def test_extract_routing_text_ignores_mapping_clause() -> None:
    prompt = (
        "Task: implement a memory-safe ring buffer with zero-cost abstractions. "
        "Choose the best Sacred Tongue (KO=Python, AV=JS, RU=Rust, CA=Mathematica, UM=Haskell, DR=Markdown). "
        'Reply with ONLY a JSON object: {"tongue": "<CODE>", "lang": "<language>"}.'
    )
    assert extract_routing_text(prompt) == "implement a memory-safe ring buffer with zero-cost abstractions"


def test_routes_rust_task_without_python_map_contamination() -> None:
    route = route_prompt(
        "Task: implement a memory-safe ring buffer with zero-cost abstractions. "
        "Choose the best Sacred Tongue (KO=Python, AV=JS, RU=Rust, CA=Mathematica, UM=Haskell, DR=Markdown)."
    )
    assert route.tongue == "RU"
    assert route.language == "Rust"
    assert route.source == "keyword"


def test_routes_readme_as_structural_draumric_work() -> None:
    route = route_prompt("Task: write project README documentation with headings and bullet lists.")
    assert route.tongue == "DR"
    assert route.language == "Markdown"


def test_force_tongue_wins() -> None:
    route = route_prompt("write a Python helper", force_tongue="UM")
    assert route.tongue == "UM"
    assert route.confidence == 1.0

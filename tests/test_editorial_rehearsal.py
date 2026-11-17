import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "book" / "editorial_rehearsal.py"
SPEC = importlib.util.spec_from_file_location("editorial_rehearsal", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_plan(root: Path, *, continuity_actor: str = "keeper") -> tuple[Path, dict]:
    source_dir = root / "content" / "book" / "reader-edition"
    source_dir.mkdir(parents=True)
    sources = []
    for chapter in (1, 2, 3):
        path = source_dir / f"ch{chapter:02d}.md"
        path.write_text(f"chapter {chapter}\n", encoding="utf-8")
        sources.append({"path": path.relative_to(root).as_posix(), "sha256": MODULE.sha256(path)})
    plan = {
        "schema_version": 1,
        "cycle": "2026-11-17",
        "work": "Test work",
        "authority": "Human author",
        "chapter_bounds": {"minimum": 2, "maximum": 3},
        "role_order": ["fresh-reader", "writer", "continuity"],
        "blocks": [
            {
                "id": "chapters-01-03",
                "chapters": [1, 2, 3],
                "reader_actor": "reader",
                "writer_actor": "reader",
                "continuity_actor": continuity_actor,
                "sources": sources,
            }
        ],
    }
    plan_path = root / "content" / "book" / "editorial" / "rehearsal-plan.json"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    return plan_path, plan


def test_valid_plan_pins_sources_and_rotates_continuity(tmp_path: Path):
    _, plan = write_plan(tmp_path)
    assert MODULE.validate_plan(plan, tmp_path) == []


def test_rejects_writer_as_own_continuity_keeper(tmp_path: Path):
    _, plan = write_plan(tmp_path, continuity_actor="reader")
    errors = MODULE.validate_plan(plan, tmp_path)
    assert any("independent" in error for error in errors)


def test_detects_source_drift(tmp_path: Path):
    _, plan = write_plan(tmp_path)
    (tmp_path / "content" / "book" / "reader-edition" / "ch02.md").write_text("changed\n", encoding="utf-8")
    errors = MODULE.validate_plan(plan, tmp_path)
    assert any("source drift" in error for error in errors)


def test_receipt_chain_binds_each_prior_hash(tmp_path: Path):
    _, plan = write_plan(tmp_path)
    base = tmp_path / "content" / "book" / "editorial" / "2026-11-17"
    reader = base / "fresh-reader" / "chapters-01-03.md"
    writer = base / "writer" / "chapters-01-03.md"
    continuity = base / "continuity" / "chapters-01-03.md"
    reader.parent.mkdir(parents=True)
    writer.parent.mkdir(parents=True)
    continuity.parent.mkdir(parents=True)
    reader.write_text("fresh reaction\n", encoding="utf-8")
    writer.write_text(f"reader receipt sha256: {MODULE.sha256(reader)}\nproposal\n", encoding="utf-8")
    continuity.write_text(f"writer receipt sha256: {MODULE.sha256(writer)}\nreview\n", encoding="utf-8")
    statuses, errors = MODULE.verify_receipt_chain(plan, tmp_path, require_complete=True)
    assert errors == []
    assert statuses[0]["state"] == "CONTINUITY_REVIEWED"

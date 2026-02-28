"""Tests for aether_ide.session -- the central IDE orchestrator."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.aether_ide import AetherIDESession, IDEAction, IDEConfig


def test_session_create():
    session = AetherIDESession()
    assert session.session_id.startswith("aide-")
    session.close()


def test_session_execute_edit():
    session = AetherIDESession(IDEConfig(chemistry_threat_level=3))
    dec, result = session.execute(IDEAction(kind="edit", content="x = 1"))
    assert dec in ("ALLOW", "QUARANTINE", "DENY")
    session.close()


def test_session_execute_search():
    session = AetherIDESession(IDEConfig(chemistry_threat_level=3))
    dec, result = session.execute(IDEAction(kind="search", content="find imports"))
    assert dec in ("ALLOW", "QUARANTINE", "DENY")
    session.close()


def test_session_execute_chat():
    session = AetherIDESession(IDEConfig(chemistry_threat_level=3))
    dec, result = session.execute(IDEAction(kind="chat", content="hello"))
    assert dec in ("ALLOW", "QUARANTINE", "DENY")
    assert session.chat.message_count >= 1
    session.close()


def test_session_state():
    session = AetherIDESession(IDEConfig(chemistry_threat_level=3))
    session.execute(IDEAction(kind="edit", content="x = 1"))
    state = session.get_state()
    assert state.event_count == 1
    assert state.mode == "ENGINEERING"
    assert state.zone == "HOT"
    session.close()


def test_session_mode_switch():
    session = AetherIDESession()
    assert session.switch_mode("NAVIGATION")
    assert session.editor.mode == "NAVIGATION"
    session.close()


def test_session_zone_starts_hot():
    session = AetherIDESession()
    assert session.editor.zone == "HOT"
    session.close()


def test_session_export_training_data():
    session = AetherIDESession(IDEConfig(chemistry_threat_level=3))
    session.execute(IDEAction(kind="edit", content="def f(): pass"))
    session.execute(IDEAction(kind="run", content="python test.py"))
    pairs = session.export_training_data()
    assert len(pairs) == 2
    assert "instruction" in pairs[0]
    assert "output" in pairs[0]
    assert "metadata" in pairs[0]
    session.close()


def test_session_spin_engine():
    session = AetherIDESession()
    result = session.spin.spin("AI governance")
    assert isinstance(result, dict)
    assert "topic" in result
    session.close()


def test_session_code_search():
    session = AetherIDESession()
    tongue = session.search.classify("class Processor with validate")
    assert tongue in ["KO", "AV", "RU", "CA", "UM", "DR"]
    session.close()

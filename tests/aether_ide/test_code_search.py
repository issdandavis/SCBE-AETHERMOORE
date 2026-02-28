"""Tests for aether_ide.code_search."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.aether_ide.code_search import GovernedCodeSearch


def test_classify_control_flow():
    cs = GovernedCodeSearch()
    tongue = cs.classify("if while for switch control flow")
    assert tongue == "KO"


def test_classify_transport():
    cs = GovernedCodeSearch()
    tongue = cs.classify("import from return send fetch transport")
    assert tongue == "AV"


def test_classify_compute():
    cs = GovernedCodeSearch()
    tongue = cs.classify("compute calculate sum process transform")
    assert tongue == "CA"


def test_classify_structural():
    cs = GovernedCodeSearch()
    tongue = cs.classify("class struct model schema define type")
    assert tongue == "DR"


def test_search_empty():
    cs = GovernedCodeSearch()
    results = cs.search("nonexistent query xyz")
    assert isinstance(results, list)


def test_search_count():
    cs = GovernedCodeSearch()
    cs.search("test")
    cs.search("test2")
    assert cs.search_count == 2

"""Domain-language token classification and tongue routing tests.

Covers LANGUAGE_TONGUES mappings and semantic_class_for_domain() for
HTML, Markdown, C/C++, and Rust — languages that feed tongue routing
in code_weight_packets.
"""

import pytest

from src.tokenizer.code_weight_packets import (
    LANGUAGE_TONGUES,
    semantic_class_for_domain,
)

# ─────────────────────────────────────────────────────────────────────────────
# Tongue routing — LANGUAGE_TONGUES coverage
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "language, expected_tongue",
    [
        # Natural programming languages
        ("python", "KO"),
        ("typescript", "AV"),
        ("javascript", "AV"),
        ("rust", "RU"),
        ("c", "CA"),
        ("cpp", "CA"),
        ("csharp", "CA"),
        ("julia", "UM"),
        ("haskell", "DR"),
        # Markup / document
        ("html", "RU"),
        ("css", "CA"),
        ("markdown", "AV"),
        # Data / config
        ("json", "DR"),
        ("yaml", "DR"),
        ("toml", "DR"),
    ],
)
def test_language_tongue_routing(language: str, expected_tongue: str) -> None:
    assert LANGUAGE_TONGUES.get(language) == expected_tongue


def test_language_tongues_no_duplicates_across_ko_av() -> None:
    """python and typescript should not share a tongue."""
    assert LANGUAGE_TONGUES["python"] != LANGUAGE_TONGUES["typescript"]


def test_javascript_shares_tongue_with_typescript() -> None:
    assert LANGUAGE_TONGUES["javascript"] == LANGUAGE_TONGUES["typescript"]


def test_cpp_shares_tongue_with_c() -> None:
    assert LANGUAGE_TONGUES["cpp"] == LANGUAGE_TONGUES["c"]


# ─────────────────────────────────────────────────────────────────────────────
# HTML token classification
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "token, expected",
    [
        # Structural tags
        ("<div>", "STRUCTURE"),
        ("<span>", "STRUCTURE"),
        ("<section>", "STRUCTURE"),
        ("<article>", "STRUCTURE"),
        ("<header>", "STRUCTURE"),
        ("<footer>", "STRUCTURE"),
        ("<nav>", "STRUCTURE"),
        ("<ul>", "STRUCTURE"),
        ("<li>", "STRUCTURE"),
        ("<table>", "STRUCTURE"),
        # Action tags
        ("<script>", "ACTION"),
        ("<style>", "ACTION"),
        ("<link>", "ACTION"),
        ("<meta>", "ACTION"),
        ("<iframe>", "ACTION"),
        # Relation attributes
        ("href", "RELATION"),
        ("src", "RELATION"),
        ("id", "RELATION"),
        ("class", "RELATION"),
        ("type", "RELATION"),
        ("name", "RELATION"),
        ("action", "RELATION"),
        ("method", "RELATION"),
    ],
)
def test_html_semantic_class(token: str, expected: str) -> None:
    assert semantic_class_for_domain(token, "html") == expected


def test_html_tag_matching_is_case_insensitive() -> None:
    assert semantic_class_for_domain("<DIV>", "html") == "STRUCTURE"
    assert semantic_class_for_domain("<SCRIPT>", "html") == "ACTION"


# ─────────────────────────────────────────────────────────────────────────────
# Markdown token classification
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "token, expected",
    [
        # Headers → STRUCTURE
        ("#", "STRUCTURE"),
        ("##", "STRUCTURE"),
        ("###", "STRUCTURE"),
        ("######", "STRUCTURE"),
        # Link opener → RELATION
        ("[", "RELATION"),
        # Code fence → ACTION
        ("```", "ACTION"),
        ("`", "ACTION"),
        # Emphasis → ACTION
        ("**", "ACTION"),
        ("*", "ACTION"),
        ("_", "ACTION"),
        ("__", "ACTION"),
    ],
)
def test_markdown_semantic_class(token: str, expected: str) -> None:
    assert semantic_class_for_domain(token, "markdown") == expected


# ─────────────────────────────────────────────────────────────────────────────
# C token classification
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "token, expected",
    [
        # Control flow → ACTION
        ("if", "ACTION"),
        ("else", "ACTION"),
        ("for", "ACTION"),
        ("while", "ACTION"),
        ("return", "ACTION"),
        ("break", "ACTION"),
        ("continue", "ACTION"),
        ("switch", "ACTION"),
        # Structure keywords
        ("struct", "STRUCTURE"),
        ("union", "STRUCTURE"),
        ("enum", "STRUCTURE"),
        ("typedef", "STRUCTURE"),
        # Relation operators
        ("->", "RELATION"),
        (".", "RELATION"),
        ("&", "RELATION"),
        # Inert / null-like
        ("void", "INERT_WITNESS"),
        ("NULL", "INERT_WITNESS"),
        ("nullptr", "INERT_WITNESS"),
    ],
)
def test_c_semantic_class(token: str, expected: str) -> None:
    assert semantic_class_for_domain(token, "c") == expected


def test_c_keywords_case_insensitive() -> None:
    assert semantic_class_for_domain("IF", "c") == "ACTION"
    assert semantic_class_for_domain("STRUCT", "c") == "STRUCTURE"


# ─────────────────────────────────────────────────────────────────────────────
# C++ token classification
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "token, expected",
    [
        # Inherits C control flow
        ("if", "ACTION"),
        ("for", "ACTION"),
        ("return", "ACTION"),
        # C++ action additions
        ("new", "ACTION"),
        ("delete", "ACTION"),
        ("throw", "ACTION"),
        ("try", "ACTION"),
        ("catch", "ACTION"),
        # Structure
        ("struct", "STRUCTURE"),
        ("class", "STRUCTURE"),
        ("template", "STRUCTURE"),
        ("namespace", "STRUCTURE"),
        # Relation operators
        ("->", "RELATION"),
        ("::", "RELATION"),
        # Inert
        ("void", "INERT_WITNESS"),
    ],
)
def test_cpp_semantic_class(token: str, expected: str) -> None:
    assert semantic_class_for_domain(token, "cpp") == expected


def test_cpp_also_accepts_cxx_alias() -> None:
    assert semantic_class_for_domain("class", "c++") == "STRUCTURE"
    assert semantic_class_for_domain("::", "c++") == "RELATION"


# ─────────────────────────────────────────────────────────────────────────────
# Rust token classification
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "token, expected",
    [
        # Definitions → ACTION
        ("fn", "ACTION"),
        ("impl", "ACTION"),
        ("mod", "ACTION"),
        ("pub", "ACTION"),
        ("use", "ACTION"),
        ("let", "ACTION"),
        ("mut", "ACTION"),
        ("match", "ACTION"),
        ("async", "ACTION"),
        ("await", "ACTION"),
        # Type definitions → STRUCTURE
        ("struct", "STRUCTURE"),
        ("enum", "STRUCTURE"),
        ("trait", "STRUCTURE"),
        ("type", "STRUCTURE"),
        ("union", "STRUCTURE"),
        # Ownership / borrow operators → RELATION
        ("&", "RELATION"),
        ("->", "RELATION"),
        ("::", "RELATION"),
        (".", "RELATION"),
        ("=>", "RELATION"),
        ("?", "RELATION"),
        # Null-like → INERT_WITNESS
        ("None", "INERT_WITNESS"),
        ("false", "INERT_WITNESS"),
        ("true", "INERT_WITNESS"),
    ],
)
def test_rust_semantic_class(token: str, expected: str) -> None:
    assert semantic_class_for_domain(token, "rust") == expected


def test_rust_none_is_case_sensitive() -> None:
    """Rust None is title-case; 'none' (lowercase) falls through to generic."""
    result = semantic_class_for_domain("none", "rust")
    # lowercase 'none' is not a Rust keyword — generic returns INERT_WITNESS via null-like set
    assert result == "INERT_WITNESS"


# ─────────────────────────────────────────────────────────────────────────────
# Cross-domain invariants
# ─────────────────────────────────────────────────────────────────────────────


def test_struct_is_structure_in_c_cpp_rust() -> None:
    for lang in ("c", "cpp", "rust"):
        assert semantic_class_for_domain("struct", lang) == "STRUCTURE", f"failed for {lang}"


def test_return_is_action_in_c_cpp_rust() -> None:
    for lang in ("c", "cpp", "rust"):
        assert semantic_class_for_domain("return", lang) == "ACTION", f"failed for {lang}"


def test_arrow_is_relation_in_c_cpp_rust() -> None:
    for lang in ("c", "cpp", "rust"):
        assert semantic_class_for_domain("->", lang) == "RELATION", f"failed for {lang}"


def test_unknown_language_falls_back_to_generic() -> None:
    # Generic _semantic_class handles standard keywords
    assert semantic_class_for_domain("return", "cobol") == "ACTION"
    assert semantic_class_for_domain("none", "unknown") == "INERT_WITNESS"


def test_html_not_affected_by_c_keywords() -> None:
    # 'class' in HTML is a RELATION attribute, not STRUCTURE (no cpp logic)
    assert semantic_class_for_domain("class", "html") == "RELATION"

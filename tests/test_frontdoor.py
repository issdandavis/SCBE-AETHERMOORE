"""Front door — token stream -> opcode object -> rendered code (the keyboard layer)."""
import pytest

from python.scbe import frontdoor as F
from python.scbe import polyglot as P


def test_symbols_names_hex_all_map():
    names, prog = F.tokens_to_program("+ sqrt * 0x0b /")
    assert names == ["add", "sqrt", "mul", "inc", "div"]
    assert prog == P.program_bytes(*names)


def test_aliases_and_commas():
    names, _ = F.tokens_to_program("power, root, maximum")
    assert names == ["pow", "sqrt", "max"]


def test_unknown_token_hints():
    with pytest.raises(ValueError) as e:
        F.tokens_to_program("add sqrtt mul")
    assert "sqrt" in str(e.value)            # did-you-mean suggestion present


def test_non_core_hex_rejected():
    with pytest.raises(ValueError):
        F.tokens_to_program("0xff")          # not a v1 scalar-core opcode


def test_render_is_verified_and_clean():
    out = F.render("+ sqrt * inc /", ("python", "rust"), color=False)
    assert "SCBE · cube code" in out
    assert "18/18 faces" in out and "seekable" in out and "sealed" in out
    assert "def tongue_fn" in out and "fn tongue_fn" in out
    # the rendered object decodes back to exactly what we typed (bijection holds)
    _, prog = F.tokens_to_program("+ sqrt * inc /")
    from python.scbe import bijective_dna as DNA
    assert DNA.decode_from_source(P.emit(prog, "rust")) == prog


def test_empty_program_renders():
    out = F.render("", ("python",), color=False)
    assert "0 op" in out or "(empty)" in out


def test_run_on_enter_shows_result():
    out = F.render("+ * inc", ("python",), color=False)        # add,mul,inc -> 15.0
    assert "runs" in out and "tongue_fn(2,3,4) → 15.0" in out


def test_run_on_enter_undefined_zone_uses_roundabout():
    div0 = F.render("== /", ("python",), color=False)          # eq->0.0 then /0
    assert "roundabout 0.0" in div0 and "ZeroDivisionError" in div0
    sqrtneg = F.render("- sqrt", ("python",), color=False)     # 3-4=-1 then sqrt
    assert "roundabout 0.0" in sqrtneg and "ValueError" in sqrtneg


def test_run_on_enter_incomplete_strand_is_graceful():
    out = F.render("+ sqrt * inc /", ("python",), color=False)  # underflows the stack
    assert "incomplete strand" in out                          # no crash, clear note


_tongues = pytest.mark.skipif(not F._HAVE_TONGUES, reason="sacred_tongues not importable")


@_tongues
def test_sacred_tongue_input_round_trips():
    # opcodes -> their KO tongue spelling -> decode that spelling back to the SAME program
    names, prog = F.tokens_to_program("add mul sqrt inc")
    spell = F.tongue_spell(prog, "ko")
    assert spell == "sil'a sil'ei sil'eth sil'en"
    names2, prog2 = F.tokens_to_program(spell, tongue="ko")
    assert names2 == names and prog2 == prog


@_tongues
def test_tongue_spelling_differs_per_tongue():
    _, prog = F.tokens_to_program("add mul sqrt")
    assert F.tongue_spell(prog, "ko") != F.tongue_spell(prog, "ca")
    # every tongue spelling decodes back to the same opcodes
    for t in F._TONGUE_ORDER:
        _, back = F.tokens_to_program(F.tongue_spell(prog, t), tongue=t)
        assert back == prog


@_tongues
def test_tongue_token_that_is_not_a_core_op_is_rejected():
    # KO byte 0x10 = kor'a -> a non-core opcode; must error helpfully, not emit garbage
    with pytest.raises(ValueError) as e:
        F.tokens_to_program("kor'a")
    assert "not a core opcode" in str(e.value)


@_tongues
def test_render_shows_tongue_line():
    out = F.render("add mul sqrt", ("python",), color=False, tongue="ko")
    assert "tongue" in out and "sil'a sil'ei sil'eth" in out


def test_geoseal_signature_is_nonzero_and_stable():
    a = F.render("+ * sqrt", ("python",), color=False)
    b = F.render("+ * sqrt", ("python",), color=False)
    assert a == b                            # deterministic
    sig = [ln for ln in a.splitlines() if "geoseal" in ln][0]
    assert "0000000000000000" not in sig     # XOR-fold fixed the splitmix64(0) artifact


def test_plain_output_is_ascii_safe_when_stdout_is_not_utf8(monkeypatch):
    monkeypatch.setattr(F, "_unicode_enabled", lambda: False)
    out = F.render("+ sqrt", ("python",), color=False)
    out.encode("ascii")
    assert "+- SCBE * cube code" in out
    assert "OK tongue_fn(2,3,4) -> 2.64575" in out
